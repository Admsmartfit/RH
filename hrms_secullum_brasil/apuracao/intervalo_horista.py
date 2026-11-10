"""Instrutor horista que passou de 4h15 sem marcar o intervalo (RH, 09/11/2026). Regra pura em
`engine/intervalo_horista.py`; a pendência nasce na apuração (`engine/apuracao_dia.intervalo_nao_marcado`).

- O instrutor não recebe WhatsApp (o tipo não é cobrável e não abre "intrajornada" nem horas não autorizadas).
- O RH recebe um WhatsApp por dia (`avisar_rh`, 8h30) com os dias novos e o link do cartão de cada um.
- No cartão, "Lançar o intervalo" (`lancar`) põe 15 min no meio da jornada pelo `cartao_ponto.salvar`, com o motivo
  próprio. O intervalo desconta das horas e não é pago. A pendência continua até o termo do mês, que registra que ele
  excedeu o horário de trabalho de 4 h e deveria ter marcado o intervalo.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_url, getdate, today

from hrms_secullum_brasil.engine import intervalo_horista as ih

INCONSISTENCIA = "Inconsistencia de Ponto"
CONFIG = "Configuracao Apuracao"
PAPEIS = ("System Manager", "RH Ponto")
JA_LANCADO = (
	"lançado pelo RH"  # trecho da descrição da pendência depois do lançamento (engine/apuracao_dia.py)
)


def link_do_dia(employee: str, data, company: str | None = None) -> str:
	"""Cartão do colaborador aberto no dia, na competência da folha."""
	from hrms_secullum_brasil.apuracao.competencia import dia_de_fechamento
	from hrms_secullum_brasil.engine.competencia import competencia_da_data

	data = getdate(data)
	ano, mes = competencia_da_data(data, dia_de_fechamento(company))
	return get_url(f"/ponto/cartao/{employee}?competencia={ano}-{mes:02d}&dia={data}")


def lancar(inconsistencia: str) -> dict:
	"""Lança o intervalo do dia (só RH): 15 min (a pausa do cargo) no meio da jornada, como inclusão de batidas."""
	from hrms_secullum_brasil.apuracao.adaptador import montar_entrada
	from hrms_secullum_brasil.apuracao.cartao_ponto import batidas_atuais, salvar

	frappe.only_for(PAPEIS)
	inc = frappe.get_doc(INCONSISTENCIA, inconsistencia)
	if inc.tipo != ih.TIPO or not inc.data:
		frappe.throw(_("Esta pendência não é de intervalo não marcado do instrutor horista."))
	data = getdate(inc.data)
	horas = batidas_atuais(inc.employee, data)
	if len(horas) != 2:
		frappe.throw(
			_("O dia já tem intervalo ou tem batidas a corrigir ({0}): confira no cartão.").format(
				", ".join(horas) or _("sem batidas")
			)
		)
	ctx = montar_entrada(inc.employee, data)
	duracao = (ctx.entrada.pausa_paga_min if ctx and ctx.entrada else 0) or 15
	intervalo = ih.intervalo_no_meio(*ih.minutos_em_ordem(horas), duracao)
	if not intervalo:
		frappe.throw(_("A jornada do dia é curta demais para o intervalo."))
	horarios = [horas[0], ih.hhmm(intervalo[0]), ih.hhmm(intervalo[1]), horas[1]]
	r = salvar(inc.employee, [{"data": str(data), "horarios": horarios}], ih.MOTIVO, False, data, data)
	erros = r["dias"].get(str(data), {}).get("erros")
	if erros:
		frappe.throw("; ".join(erros))
	return {"data": str(data), "intervalo": horarios[1:3]}


def _numeros() -> list[str]:
	texto = frappe.db.get_single_value(CONFIG, "whatsapp_rh_intervalo") or ""
	return [n.strip() for n in texto.replace(",", "\n").splitlines() if n.strip()]


def avisar_rh(hoje=None) -> int:
	"""Cron das 8h30: um WhatsApp ao RH com os dias de ontem; os de antes, ainda sem o intervalo, só contados."""
	from hrms_secullum_brasil.apuracao import whatsapp

	numeros = _numeros()
	if not numeros:
		return 0
	hoje = getdate(hoje or today())
	ontem = add_days(hoje, -1)
	pendentes = [
		p
		for p in frappe.get_all(
			INCONSISTENCIA,
			filters={"tipo": ih.TIPO, "status": "Aberta"},
			fields=["name", "employee", "employee_name", "company", "data", "descricao"],
			order_by="data asc, employee_name asc",
		)
		if JA_LANCADO not in (p.descricao or "")
	]
	novos = [p for p in pendentes if getdate(p.data) == getdate(ontem)]
	if not novos:
		return 0
	itens = [
		ih.ItemRH(
			p.employee_name or p.employee,
			getdate(p.data),
			_trabalhado(p.employee, p.data),
			link_do_dia(p.employee, p.data, p.company),
		)
		for p in novos
	]
	texto = ih.mensagem_rh(
		hoje, itens, len(pendentes) - len(novos), get_url(f"/ponto/inconsistencias?tipo={ih.TIPO}")
	)
	enviadas = 0
	for numero in numeros:
		chave = f"intervalo-horista|{ontem}|{numero}"
		if frappe.db.exists(whatsapp.NOTIFICACAO, {"chave": chave}):
			continue
		whatsapp.enviar(whatsapp.criar(None, "RH", numero, texto, chave=chave))
		enviadas += 1
	return enviadas


def _trabalhado(employee: str, data) -> int:
	"""Minutos do dia (sem intervalo), da apuração."""
	return int(
		frappe.db.get_value("Apuracao Diaria", {"employee": employee, "data": getdate(data)}, "trabalhado")
		or 0
	)
