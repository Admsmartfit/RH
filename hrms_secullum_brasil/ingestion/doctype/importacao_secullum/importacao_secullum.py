"""Assistente de importação do Secullum (docs/PRD-importacao-secullum.md, IS-11): conectar, conferir, importar e
revisar. As credenciais ficam só na Configuracao Secullum (campo Password); o assistente só as grava lá."""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from hrms_secullum_brasil.ingestion import carga_batidas
from hrms_secullum_brasil.ingestion import importacao_secullum as importador

ASSISTENTE = "Importacao Secullum"
CONFIG = "Configuracao Secullum"
PAPEIS = ("System Manager", "RH Ponto")
METODO_IMPORTAR = (
	"hrms_secullum_brasil.ingestion.doctype.importacao_secullum.importacao_secullum.executar_importacao"
)
JOB_ID = "secullum-importacao-completa"

# o que fazer com cada problema (Conferir)
ORIENTACOES = (
	("CPF inválido", "Corrija o CPF no Secullum e confira de novo."),
	("sem CPF", "Informe o CPF no Secullum."),
	("sem horário", "Defina o horário do funcionário no Secullum."),
	("sem data de admissão", "Informe a admissão no Secullum."),
	("sem empresa", "Vincule o funcionário a uma empresa no Secullum."),
	("Justificativa", "Confira a justificativa no Secullum."),
	("CNPJ", "Corrija o CNPJ da empresa no Secullum."),
)


class ImportacaoSecullum(Document):
	def onload(self):
		from hrms_secullum_brasil.ingestion.revisao_importacao import TIPOS, html_revisao

		self.set_onload("conexao", estado_conexao())
		self.set_onload("revisao_html", html_revisao())
		self.set_onload(
			"cargos",
			sorted(
				set(frappe.get_all("Employee", filters={"id_secullum": ["is", "set"]}, pluck="designation"))
				- {None}
			),
		)
		self.set_onload("tipos", TIPOS)
		if not self.batidas_desde:
			self.batidas_desde = carga_batidas.data_inicial_padrao()


def _orientacao(mensagem: str) -> str:
	return next(
		(o for chave, o in ORIENTACOES if chave.lower() in (mensagem or "").lower()), "Corrija no Secullum."
	)


@frappe.whitelist()
def estado_conexao() -> dict:
	frappe.only_for(PAPEIS)
	cfg = frappe.get_single(CONFIG)
	return {
		"usuario": cfg.usuario,
		"tem_senha": bool(cfg.get_password("senha", raise_exception=False)),
		"id_banco": cfg.id_banco,
		"modo_mock": cfg.modo_mock,
		"ativo": cfg.ativo,
		"origem": cfg.origem_cadastros or "Secullum",
		"sincronizar": cfg.sincronizar_cadastros,
	}


@frappe.whitelist()
def conectar(usuario: str, senha: str | None = None, id_banco: str | None = None) -> dict:
	"""Grava usuário/senha/banco na Configuracao Secullum e lista os bancos da conta. Um banco só: escolhido."""
	from hrms_secullum_brasil.ingestion.secullum import get_client
	from hrms_secullum_brasil.integrations.secullum.erros import SecullumError

	frappe.only_for(PAPEIS)
	cfg = frappe.get_single(CONFIG)
	cfg.usuario = (usuario or "").strip()
	if senha:
		cfg.senha = senha
	if id_banco:
		cfg.id_banco = id_banco
	cfg.origem_cadastros = cfg.origem_cadastros or "Secullum"
	cfg.save()
	try:
		bancos = [
			{"nome": b.get("nome"), "id_banco": b.get("id_banco")} for b in get_client().listar_bancos()
		]
	except SecullumError as exc:
		frappe.throw(_("Falha na conexão com o Secullum: {0}").format(exc), title=_("Secullum"))
	if not cfg.id_banco and len(bancos) == 1:
		frappe.db.set_single_value(CONFIG, "id_banco", bancos[0]["id_banco"])
	return {"bancos": bancos, "conexao": estado_conexao()}


@frappe.whitelist()
def conferir() -> dict:
	"""Pré-visualização (simulação, nada é gravado): contagens, ativos/demitidos e problemas com o que fazer."""
	frappe.only_for(PAPEIS)
	importacao = importador.ImportacaoSecullum(simular=True)
	resultado = importacao.executar()
	funcionarios = importacao.client.listar_funcionarios()
	selecionados = importacao.colaboradores
	dados = {
		"secullum": {
			"Empresas": len(importacao.client.listar_empresas()),
			"Horários": len(importacao.client.listar_horarios()),
			"Funcionários ativos": sum(1 for f in funcionarios if not f.get("Demissao")),
			"Funcionários (todos os cadastros)": len(funcionarios),
		},
		"importar": {
			"Ativos": sum(1 for c in selecionados if c.status == "Active" and not c.problemas),
			"Demitidos nos últimos 12 meses": sum(
				1 for c in selecionados if c.status == "Left" and not c.problemas
			),
			"Sem data de nascimento (entram com 01/01/1900)": sum(
				1 for c in selecionados if c.nascimento_ausente
			),
		},
		"contagem": resultado["contagem"],
		"problemas": [
			{**linha, "orientacao": _orientacao(linha["mensagem"])}
			for linha in resultado["linhas"]
			if linha["resultado"] == importador.ERRO
		],
		"avisos": [linha for linha in resultado["linhas"] if linha["resultado"] == importador.AVISO],
	}
	frappe.db.set_single_value(
		ASSISTENTE,
		{"conferencia": json.dumps(dados, ensure_ascii=False, default=str), "conferencia_em": now_datetime()},
	)
	return dados


@frappe.whitelist()
def importar(batidas_desde=None, ativar_coleta=1) -> dict:
	"""Enfileira a importação completa: cadastros e, depois, a carga das batidas (IS-09)."""
	frappe.only_for(PAPEIS)
	desde = getdate(batidas_desde) if batidas_desde else carga_batidas.data_inicial_padrao()
	frappe.db.set_single_value(ASSISTENTE, {"batidas_desde": desde, "ativar_coleta": int(ativar_coleta)})
	carga_batidas._publicar(
		status="Na fila", desde=desde, etapa=_("Aguardando o início"), percentual=0, resultado={}
	)
	frappe.enqueue(
		METODO_IMPORTAR,
		queue="long",
		timeout=6 * 3600,
		job_id=JOB_ID,
		deduplicate=True,
		desde=desde,
		ativar=int(ativar_coleta),
	)
	return carga_batidas.progresso()


def executar_importacao(desde=None, ativar=1, batidas=True) -> dict:
	"""Job: cadastros (com log) e a carga das batidas. Um erro nos cadastros para tudo e fica no progresso."""
	carga_batidas._publicar(
		status="Em andamento", etapa=_("Importando os cadastros"), percentual=0, resultado={}
	)
	try:
		resultado = importador.ImportacaoSecullum().executar()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(title=_("Importação do Secullum"))
		carga_batidas._publicar(status="Erro", etapa=str(exc)[:140])
		raise
	frappe.db.set_single_value(
		ASSISTENTE, {"importacao_em": now_datetime(), "importacao_execucao": resultado["execucao"]}
	)
	carga_batidas._commit()
	if not batidas:
		carga_batidas._publicar(
			status="Concluída",
			etapa=_("Cadastros importados"),
			percentual=100,
			resultado=resultado["contagem"],
		)
		return resultado
	return carga_batidas.carregar(desde, ativar=ativar)


@frappe.whitelist()
def repetir_cadastros() -> dict:
	"""Repete só a importação dos cadastros (sem batidas), em segundo plano."""
	frappe.only_for(PAPEIS)
	carga_batidas._publicar(status="Na fila", etapa=_("Aguardando o início"), percentual=0, resultado={})
	frappe.enqueue(
		METODO_IMPORTAR, queue="long", timeout=3600, job_id=JOB_ID, deduplicate=True, batidas=False
	)
	return carga_batidas.progresso()


@frappe.whitelist()
def ligar_sincronizacao(ligar=1) -> dict:
	"""Liga/desliga a sincronização diária dos cadastros (IS-08)."""
	frappe.only_for(PAPEIS)
	frappe.db.set_single_value(CONFIG, "sincronizar_cadastros", int(bool(int(ligar))))
	return estado_conexao()
