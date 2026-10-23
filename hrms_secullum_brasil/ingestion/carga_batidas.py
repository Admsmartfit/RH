"""Carga inicial das batidas do Secullum (docs/PRD-importacao-secullum.md, IS-09; Etapa 10).

    bench --site ponto.localhost execute hrms_secullum_brasil.ingestion.carga_batidas.carregar \\
        --kwargs "{'desde': '2026-09-01'}"

Depois dos cadastros, lê as marcações originais desde a data escolhida (DI-3) até hoje, um dia por chamada, com a
mesma coleta do dia a dia (`ingestion/coleta_batidas.py`: idempotente, nunca mexe em período fechado). Em seguida
marca para apuração todos os dias de cada vínculo importado no período — inclusive os sem batida, que são as
faltas — e processa a fila `Reapuracao Pendente`. O progresso fica no single `Importacao Secullum` (o cache do
Frappe é limpo quando a importação grava empresas e cargos), para o assistente.
"""

import json
from dataclasses import asdict
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes
from hrms_secullum_brasil.ingestion.cartao_secullum import sincronizar_cartao
from hrms_secullum_brasil.ingestion.coleta_batidas import Resumo, _Coleta, bancos_configurados
from hrms_secullum_brasil.ingestion.secullum import get_client

LOG = "Log de Importacao Secullum"
ASSISTENTE = "Importacao Secullum"
METODO = "hrms_secullum_brasil.ingestion.carga_batidas.carregar"
JOB_ID = "secullum-carga-inicial-batidas"
MOTIVO = "Carga inicial das batidas do Secullum."
LOTE_APURACAO = 2000


def data_inicial_padrao(hoje: date | None = None) -> date:
	"""DI-3: 1º dia do mês anterior."""
	hoje = getdate(hoje or today())
	return (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)


CAMPOS = ("status", "desde", "etapa", "percentual", "atualizado_em")


def progresso() -> dict:
	valores = {campo: frappe.db.get_single_value(ASSISTENTE, f"carga_{campo}") for campo in CAMPOS}
	resultado = frappe.db.get_single_value(ASSISTENTE, "carga_resultado")
	return {**valores, "resultado": json.loads(resultado) if resultado else None}


def _publicar(resultado: dict | None = None, **valores) -> None:
	valores["atualizado_em"] = now_datetime()
	gravar = {f"carga_{campo}": valor for campo, valor in valores.items() if campo in CAMPOS}
	if resultado is not None:
		gravar["carga_resultado"] = json.dumps(resultado, ensure_ascii=False, indent=1, default=str)
	frappe.db.set_single_value(ASSISTENTE, gravar)
	_commit()
	frappe.publish_realtime(
		"importacao_secullum_carga", {**valores, "resultado": resultado}, after_commit=False
	)


def _commit() -> None:
	if not frappe.flags.in_test:
		frappe.db.commit()  # cada dia/colaborador é independente: um erro não desfaz o que já entrou


@frappe.whitelist()
def iniciar(desde=None, ativar=0) -> dict:
	"""Assistente: enfileira a carga em segundo plano. `ativar` liga a coleta automática no fim."""
	frappe.only_for(("System Manager", "RH Ponto"))
	desde = getdate(desde) if desde else data_inicial_padrao()
	if desde > getdate(today()):
		frappe.throw(_("A data inicial das batidas não pode ser futura."))
	_publicar(status="Na fila", desde=desde, etapa=_("Aguardando o início"), percentual=0, resultado={})
	frappe.enqueue(
		METODO,
		queue="long",
		timeout=6 * 3600,
		job_id=JOB_ID,
		deduplicate=True,
		desde=desde,
		ativar=int(ativar),
	)
	return progresso()


def carregar(desde=None, hoje=None, ativar=0) -> dict:
	"""Coleta as batidas de `desde` até `hoje` e apura todos os dias dos vínculos importados."""
	hoje = getdate(hoje or today())
	desde = getdate(desde) if desde else data_inicial_padrao(hoje)
	dias = (hoje - desde).days + 1
	resumo = Resumo()
	_publicar(status="Em andamento", desde=desde, etapa=_("Lendo as batidas"), percentual=0, resultado={})
	try:
		for i in range(dias):
			dia = add_days(desde, i)
			for banco in bancos_configurados():
				frappe.db.savepoint("carga_dia")
				try:
					_Coleta(banco, getdate(dia), getdate(dia), resumo).executar()
				except Exception as exc:
					# um dia com erro não para a carga: fica no resumo e no Error Log
					frappe.db.rollback(save_point="carga_dia")
					frappe.log_error(title=_("Carga das batidas de {0}").format(dia))
					resumo.erros.append(f"{getdate(dia):%d/%m/%Y}: {exc}")
			_commit()
			_publicar(
				etapa=_("Lendo as batidas de {0}").format(getdate(dia).strftime("%d/%m/%Y")),
				percentual=round(60 * (i + 1) / dias),
			)
		_publicar(etapa=_("Lendo o cartão do Secullum (folgas e justificativas)"))
		for banco in bancos_configurados():
			cartao = sincronizar_cartao(get_client(banco), desde, hoje)
			resumo.erros += cartao["erros"]
		_commit()
		marcados = marcar_dias(desde, add_days(hoje, -1))
		_commit()
		apurados = 0
		pendentes = frappe.db.count("Reapuracao Pendente", {"status": "Pendente"})
		while pendentes:
			_publicar(etapa=_("Apurando os dias ({0} de {1})").format(apurados, marcados))
			processar_reapuracoes_pendentes(limite=LOTE_APURACAO)
			restantes = frappe.db.count("Reapuracao Pendente", {"status": "Pendente"})
			apurados += pendentes - restantes
			_publicar(percentual=60 + round(40 * min(apurados, marcados) / max(marcados, 1)))
			if restantes >= pendentes:
				break  # só sobraram dias que falharam (ficam no Error Log e na fila)
			pendentes = restantes
		if int(ativar):
			frappe.db.set_single_value("Configuracao Secullum", "ativo", 1)
		status = "Concluída com erros" if resumo.erros else "Concluída"
		resultado = {**asdict(resumo), "dias_marcados": marcados, "dias_apurados": apurados}
		_registrar_log(status, desde, hoje, resultado)
		_publicar(status=status, etapa=_("Fim"), percentual=100, resultado=resultado)
		_commit()
		return resultado
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(title=_("Carga inicial das batidas"))
		_publicar(status="Erro", etapa=str(exc)[:140])
		raise


def marcar_dias(desde, ate) -> int:
	"""Todos os dias de cada vínculo importado entre `desde` e `ate`, dentro do contrato (admissão a demissão)."""
	desde, ate = getdate(desde), getdate(ate)
	total = 0
	for e in frappe.get_all(
		"Employee",
		filters={"id_secullum": ["is", "set"], "perfil_jornada": ["is", "set"]},
		fields=["name", "date_of_joining", "relieving_date"],
	):
		inicio = max(desde, getdate(e.date_of_joining)) if e.date_of_joining else desde
		fim = min(ate, getdate(e.relieving_date)) if e.relieving_date else ate
		dia = inicio
		while dia <= fim:
			marcar_para_reapuracao(e.name, dia, MOTIVO)
			total += 1
			dia += timedelta(days=1)
	return total


def _registrar_log(status: str, desde, hoje, resultado: dict) -> None:
	mensagem = (
		f"{status}: de {getdate(desde):%d/%m/%Y} a {getdate(hoje):%d/%m/%Y}. Batidas novas: {resultado['novas']}, "
		f"inalteradas: {resultado['inalteradas']}, sem colaborador: {resultado['sem_colaborador']}, período "
		f"fechado: {resultado['bloqueadas_periodo_fechado']}. Dias apurados: {resultado['dias_apurados']}."
	)
	if resultado["erros"]:
		mensagem += " Erros: " + "; ".join(resultado["erros"][:20])
	frappe.get_doc(
		{
			"doctype": LOG,
			"execucao": f"BATIDAS-{now_datetime():%Y%m%d-%H%M%S}",
			"passo": "Batidas",
			"resultado": "Erro" if resultado["erros"] else "Criado",
			"chave": f"{getdate(desde):%d/%m/%Y} a {getdate(hoje):%d/%m/%Y}",
			"mensagem": mensagem[:5000],
		}
	).insert(ignore_permissions=True)
