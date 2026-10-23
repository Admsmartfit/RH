"""Envio das correções do cartão ponto ao Secullum (docs/PRD-cartao-ponto.md, CP-10 e DC-1).

Trava em Configuracao Secullum.envio_correcoes (Bloqueado por padrão). Correção aprovada com "enviar" vira um
Envio Cartao Secullum do dia, processado numa fila: lê o cartão do Secullum no dia (GET Batidas), calcula as
operações (integrations/secullum/edicao_cartao.py) para ficar igual ao programa e envia uma a uma. Falha no envio
nunca desfaz a correção do programa: vira inconsistência operacional com Reenviar. O tratamento do gestor só é
enviado quando o RH aprova (Tratamento de Ponto.on_submit).
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.ingestion.secullum import get_client, id_banco_da_empresa
from hrms_secullum_brasil.integrations.secullum.edicao_cartao import (
	colunas_do_registro,
	com_identificador,
	operacoes,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError

ENVIO = "Envio Cartao Secullum"
CONFIG = "Configuracao Secullum"
BLOQUEADO, PERGUNTAR, SEMPRE = "Bloqueado", "Perguntar ao salvar", "Sempre enviar"
TIPO = "envio_cartao_secullum"
METODO = "hrms_secullum_brasil.ingestion.envio_cartao.processar"
PAPEIS = ("System Manager", "RH Ponto")


def modo() -> str:
	return frappe.db.get_single_value(CONFIG, "envio_correcoes") or BLOQUEADO


def deve_enviar(escolha) -> bool:
	"""Com "Perguntar ao salvar", vale a caixa do Salvar; "Sempre enviar" ignora a caixa; "Bloqueado", nada."""
	atual = modo()
	if atual == SEMPRE:
		return True
	return atual == PERGUNTAR and bool(cint(escolha))


def agendar(
	employee: str, data, *, motivo: str = "", justificativa=None, justificativa_retirada=None
) -> str | None:
	"""Envio do dia na fila (um por colaborador e dia enquanto não sai). None se a trava estiver em Bloqueado."""
	if modo() == BLOQUEADO:
		return None
	data = getdate(data)
	nome = frappe.db.get_value(
		ENVIO, {"employee": employee, "data": data, "situacao": ["in", ["Na fila", "Erro"]]}
	)
	doc = frappe.get_doc(ENVIO, nome) if nome else frappe.new_doc(ENVIO)
	doc.update({"employee": employee, "data": data, "situacao": "Na fila", "usuario": frappe.session.user})
	if motivo:
		doc.motivo = motivo
	if justificativa:
		doc.justificativa, doc.justificativa_retirada = justificativa, None
	if justificativa_retirada:
		doc.justificativa_retirada, doc.justificativa = justificativa_retirada, None
	doc.save(ignore_permissions=True)
	frappe.enqueue(
		METODO,
		queue="short",
		nome=doc.name,
		job_id=f"envio-cartao-{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	return doc.name


def horarios_do_programa(employee: str, data) -> tuple[list[str], int]:
	"""Batidas que contam no programa no dia (sem as pendentes), em "HH:MM", e quantos períodos estão previstos."""
	from hrms_secullum_brasil.apuracao.adaptador import montar_entrada
	from hrms_secullum_brasil.apuracao.cartao_ponto import _carregar, batidas_do_dia
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
	from hrms_secullum_brasil.engine.cartao_edicao import hhmm

	data = getdate(data)
	perfil = get_perfil_vigente(employee, data)
	virada = cint(perfil.hora_virada_dia) if perfil else 0
	grade = batidas_do_dia(data, virada, _carregar(employee, data, data))
	ctx = montar_entrada(employee, data)
	periodos = len(ctx.entrada.jornada.periodos) if ctx and ctx.entrada else 1
	return [hhmm(b["minuto"]) for b in grade["batidas"] if not b.get("pendente")], periodos


def processar(nome: str) -> str | None:
	if not frappe.db.exists(ENVIO, nome):  # o salvar do dia foi desfeito depois de enfileirar
		return None
	doc = frappe.get_doc(ENVIO, nome)
	if doc.situacao == "Enviado":
		return doc.situacao
	if modo() == BLOQUEADO:
		doc.db_set({"situacao": "Bloqueado", "resposta": _("Trava em Bloqueado na Configuração Secullum.")})
		return doc.situacao
	emp = frappe.db.get_value("Employee", doc.employee, ["cpf", "company", "id_secullum"], as_dict=True)
	data = getdate(doc.data)
	ops = []
	try:
		if not emp.cpf:
			raise ValueError(_("O colaborador não tem CPF: o Secullum identifica o funcionário pelo CPF."))
		client = get_client(id_banco_da_empresa(emp.company))
		cpf = "".join(c for c in emp.cpf if c.isdigit())
		registros = client.listar_cartao(data, data, cpf)
		registro = next(
			(
				r
				for r in registros
				if "".join(c for c in str(r.get("FuncionarioCpf") or "") if c.isdigit()) == cpf
				or (emp.id_secullum and str(r.get("FuncionarioId")) == str(emp.id_secullum))
			),
			None,
		)
		horarios, periodos = horarios_do_programa(doc.employee, data)
		ops = operacoes(
			data,
			colunas_do_registro(registro),
			horarios,
			doc.motivo,
			justificativa=doc.justificativa,
			grupos_abono=periodos,
			justificativa_retirada=doc.justificativa_retirada,
		)
		for op in ops:
			client.editar_cartao(op.metodo, op.rota, com_identificador(op, cpf))
	except (SecullumError, ValueError, NotImplementedError) as exc:
		mensagem = str(exc) or type(exc).__name__
		doc.update({"situacao": "Erro", "resposta": mensagem[:1000]})
		registrar_inconsistencia(
			doc.employee,
			TIPO,
			_("Correção do cartão de {0} não enviada ao Secullum: {1}").format(
				frappe.utils.formatdate(data), mensagem
			),
			"Média",
			data,
			ENVIO,
			doc.name,
		)
	else:
		doc.update(
			{
				"situacao": "Enviado",
				"enviado_em": now_datetime(),
				"resposta": _("{0} operação(ões) no cartão do Secullum.").format(len(ops))
				if ops
				else _("Já estava igual."),
			}
		)
		resolver_inconsistencias(doc.employee, TIPO, data)
	doc.operacoes = json.dumps(
		[{"descricao": o.descricao(), **o.corpo} for o in ops], ensure_ascii=False, indent=1
	)
	doc.tentativas = cint(doc.tentativas) + 1
	doc.save(ignore_permissions=True)
	return doc.situacao


@frappe.whitelist()
def reenviar(nome: str | None = None, inconsistencia: str | None = None) -> str:
	"""Reenvia agora (RH Ponto): pelo envio ou pela inconsistência "correção não enviada"."""
	frappe.only_for(PAPEIS)
	if inconsistencia and not nome:
		nome = frappe.db.get_value("Inconsistencia de Ponto", inconsistencia, "referencia_name")
	if not nome or not frappe.db.exists(ENVIO, nome):
		frappe.throw(_("Envio ao Secullum não encontrado."))
	frappe.db.set_value(ENVIO, nome, "situacao", "Na fila")
	return processar(nome)
