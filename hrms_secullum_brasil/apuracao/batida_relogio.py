"""Trava da batida do relógio (pedido do RH, 04/11/2026): nenhuma batida feita pelo colaborador num aparelho (relógio,
tablet, app, Central do Funcionário) sai do dia sem confirmação dupla de quem corrige.

- No programa, tirar uma batida é sempre o Tratamento de Ponto "Desconsiderar marcação": o submit exige
  `confirmou_apagar_relogio` (cartão, central, Desk e aprovação da resposta do WhatsApp perguntam duas vezes). O
  colaborador nunca confirma: a assinatura do termo que tiraria uma batida do relógio devolve o dia ao RH.
- No Secullum, o envio do cartão só apaga um horário que o programa tirou com tratamento (`horas_que_podem_sair`); as
  filas de justificativa nunca apagam uma coluna com horário (`integrations/secullum/sincronizacao.sem_apagar_batida`).
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

RAW = "Secullum Checkin Raw"
TRATAMENTO = "Tratamento de Ponto"
# batida lançada à mão (no Secullum ou pelo próprio programa) não é do relógio
ORIGENS_MANUAIS = ("IncluidoManualmente", "PreAssinalado", "IntegracaoExterna")


def e_do_relogio(raw: dict | None) -> bool:
	return bool(raw) and raw.get("tipo_fonte") == "Original" and raw.get("tipo_origem") not in ORIGENS_MANUAIS


def do_relogio(marcacoes: list[str]) -> list[dict]:
	"""As marcações (Secullum Checkin Raw) que são batidas do relógio, com a hora."""
	nomes = [m for m in marcacoes if m]
	if not nomes:
		return []
	return [
		r
		for r in frappe.get_all(
			RAW,
			filters={"name": ["in", nomes]},
			fields=["name", "data_hora", "tipo_fonte", "tipo_origem"],
			order_by="data_hora",
		)
		if e_do_relogio(r)
	]


def rotulos(raws: list[dict]) -> list[str]:
	return [get_datetime(r.data_hora).strftime("%H:%M de %d/%m") for r in raws]


def exigir_confirmacao(tratamento) -> None:
	"""Tratamento de Ponto.before_submit: desconsiderar batida do relógio só com a confirmação dupla registrada."""
	if tratamento.tipo != "Desconsiderar marcacao" or tratamento.get("confirmou_apagar_relogio"):
		return
	raws = do_relogio([tratamento.marcacao])
	if raws:
		frappe.throw(
			_(
				"A batida {0} foi feita pelo colaborador no relógio: para desconsiderá-la, confirme duas vezes "
				"(nenhuma batida do relógio sai do dia sem essa confirmação)."
			).format(rotulos(raws)[0]),
			title=_("Batida do relógio"),
		)


def horas_que_podem_sair(employee: str, data) -> set[str]:
	"""Horários (HH:MM) que o programa tirou do dia com tratamento: batida desconsiderada (a do relógio só com a
	confirmação dupla, pelo before_submit) ou inclusão do programa cancelada. Só esses o envio apaga no Secullum."""
	data = getdate(data)
	saida = set()
	for t in frappe.get_all(
		TRATAMENTO,
		filters={"employee": employee, "data": data, "tipo": "Desconsiderar marcacao", "docstatus": 1},
		pluck="marcacao",
	):
		hora = frappe.db.get_value(RAW, t, "data_hora")
		if hora:
			saida.add(get_datetime(hora).strftime("%H:%M"))
	for hora in frappe.get_all(
		TRATAMENTO,
		filters={"employee": employee, "data": data, "tipo": "Inclusao de marcacao", "docstatus": 2},
		pluck="data_hora",
	):
		saida.add(get_datetime(hora).strftime("%H:%M"))
	return saida
