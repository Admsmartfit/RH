"""Jornada legal com vigência no Frappe (docs/PRD-planejador-5x2.md, PE-01; EC nº 141/2026).

Os regimes da emenda ficam **Preparados** e não valem até o RH clicar em "Ativar regime" com a data de início (DP-1:
a troca não está garantida). A apuração, o DSR, a folha e as validações leem o regime ativo na data por aqui; a regra
pura está em `engine/regime_jornada.py`.
"""

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.lote import memo
from hrms_secullum_brasil.engine import regime_jornada as rj

DOCTYPE = "Regime de Jornada Legal"
PREPARADO, ATIVO = "Preparado", "Ativo"
PAPEIS = ("System Manager", "RH Ponto")
DIAS_DE_AVISO = 30

# EC nº 141/2026 (promulgada em 16/10/2026): datas previstas, a confirmar no DOU; só valem quando ativadas
REGIMES_EC141 = (
	{
		"nome_regime": "EC 141/2026 — 42h",
		"inicio_previsto": "2026-12-15",
		"carga_semanal_horas": 42,
		"divisor": 210,
		"folgas_semana": 2,
		"repousos_remunerados": 2,
		"jornada_diaria_horas": 8,
		"base_legal": "EC nº 141/2026: 42h semanais 60 dias após a publicação, 2 repousos remunerados por semana "
		"(um preferencialmente no domingo), sem redução salarial.",
	},
	{
		"nome_regime": "EC 141/2026 — 40h",
		"inicio_previsto": "2027-12-15",
		"carga_semanal_horas": 40,
		"divisor": 200,
		"folgas_semana": 2,
		"repousos_remunerados": 2,
		"jornada_diaria_horas": 8,
		"base_legal": "EC nº 141/2026: 40h semanais um ano após a etapa de 42h.",
	},
)


def criar_regimes_ec141() -> int:
	criados = 0
	for dados in REGIMES_EC141:
		if not frappe.db.exists(DOCTYPE, dados["nome_regime"]):
			frappe.get_doc({"doctype": DOCTYPE, "situacao": PREPARADO, **dados}).insert(
				ignore_permissions=True
			)
			criados += 1
	return criados


def _para_engine(doc) -> rj.RegimeJornada:
	return rj.RegimeJornada(
		nome=doc.nome_regime,
		inicio=getdate(doc.inicio) if doc.inicio else None,
		semanal_min=round(flt(doc.carga_semanal_horas) * 60),
		divisor=cint(doc.divisor),
		folgas_semana=cint(doc.folgas_semana) or 1,
		repousos_remunerados=cint(doc.repousos_remunerados) or 1,
		diaria_min=round(flt(doc.jornada_diaria_horas or 8) * 60),
	)


def regimes_ativos() -> list[rj.RegimeJornada]:
	"""Os regimes ativos (no modo lote, lidos uma vez). Sem tabela ainda (antes do migrate): nenhum."""

	def ler():
		if not frappe.db.table_exists(DOCTYPE):
			return []
		return [
			_para_engine(r)
			for r in frappe.get_all(
				DOCTYPE,
				filters={"situacao": ATIVO, "inicio": ["is", "set"]},
				fields=[
					"nome_regime",
					"inicio",
					"carga_semanal_horas",
					"divisor",
					"folgas_semana",
					"repousos_remunerados",
					"jornada_diaria_horas",
				],
			)
		]

	return memo(("regimes_ativos",), ler)


def regime_na_data(data) -> rj.RegimeJornada:
	return rj.regime_na_data(getdate(data), regimes_ativos())


def teto_semanal(segunda) -> int:
	return rj.teto_semanal(getdate(segunda), regimes_ativos())


def divisor_padrao(data) -> int:
	return rj.divisor_na_data(getdate(data), regimes_ativos())


def divisor_efetivo(divisor_contrato: int, data) -> int:
	return rj.divisor_efetivo(cint(divisor_contrato), getdate(data), regimes_ativos())


def divisor_do_periodo(divisor_contrato: int, inicio, fim):
	return rj.divisor_do_periodo(cint(divisor_contrato), getdate(inicio), getdate(fim), regimes_ativos())


def contar_dias(dias, feriados) -> tuple[int, int]:
	return rj.contar_dias(dias, feriados, regimes_ativos())


def folgas_faltando(segunda, dias_trabalhados) -> int:
	return rj.folgas_insuficientes(getdate(segunda), dias_trabalhados, regimes_ativos())


def validar_regime(doc) -> None:
	if flt(doc.carga_semanal_horas) <= 0 or cint(doc.divisor) <= 0:
		frappe.throw(_("Informe a jornada semanal e o divisor."))
	if not 1 <= cint(doc.folgas_semana) <= 2 or not 1 <= cint(doc.repousos_remunerados) <= 2:
		frappe.throw(_("Folgas e repousos remunerados por semana: 1 ou 2."))
	if doc.situacao == ATIVO and not doc.inicio:
		frappe.throw(_("Regime ativo precisa da data de início."))
	if not doc.is_new() and doc.situacao == ATIVO and doc.has_value_changed("carga_semanal_horas"):
		frappe.throw(_("Regime já ativo: para mudar as regras, crie outro regime."))


def _ultimo_fechamento() -> date | None:
	datas = [getdate(x) for x in frappe.get_all("Company", pluck="ponto_fechado_ate") if x]
	return max(datas) if datas else None


@frappe.whitelist()
def ativar(regime: str, inicio: str) -> dict:
	"""RH: o regime passa a valer a partir de `inicio` (nunca antes do último fechamento). Os dias já apurados desde
	a data entram na fila de reapuração (DSR, HE semanal, folgas e folha passam a seguir o regime)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(DOCTYPE, regime)
	if doc.situacao == ATIVO:
		frappe.throw(
			_("O regime {0} já está ativo desde {1}.").format(regime, frappe.utils.formatdate(doc.inicio))
		)
	inicio_d = getdate(inicio)
	fechado = _ultimo_fechamento()
	if fechado and inicio_d <= fechado:
		frappe.throw(
			_("O ponto está fechado até {0}: escolha uma data de início depois disso.").format(
				frappe.utils.formatdate(fechado)
			)
		)
	doc.db_set(
		{
			"situacao": ATIVO,
			"inicio": inicio_d,
			"ativado_por": frappe.session.user,
			"ativado_em": now_datetime(),
			"lembrar_depois_de": None,
		}
	)
	doc.add_comment("Info", _("Regime ativado a partir de {0}.").format(frappe.utils.formatdate(inicio_d)))
	# a semana da troca também muda (teto proporcional): reapura desde a segunda da semana do início
	desde = inicio_d - timedelta(days=inicio_d.weekday())
	frappe.enqueue(
		"hrms_secullum_brasil.configuracao_ponto.regime_jornada.reapurar_desde",
		queue="long",
		timeout=3600,
		now=bool(frappe.in_test),
		desde=desde,
		motivo=_("Regime de jornada {0} ativado").format(regime),
	)
	return {"regime": regime, "inicio": str(inicio_d)}


def reapurar_desde(desde, motivo: str) -> int:
	"""Marca para reapuração os dias já apurados a partir de `desde` (a fila respeita o período fechado)."""
	from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
	from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao

	marcados = 0
	for linha in frappe.get_all(
		"Apuracao Diaria", filters={"data": [">=", getdate(desde)]}, fields=["employee", "data"]
	):
		if not periodo_fechado(linha.employee, linha.data):
			marcar_para_reapuracao(linha.employee, linha.data, motivo)
			marcados += 1
	return marcados


@frappe.whitelist()
def lembrar_depois(regime: str, dias: int | str = 7) -> str:
	frappe.only_for(PAPEIS)
	data = add_days(getdate(today()), max(1, cint(dias)))
	frappe.db.set_value(DOCTYPE, regime, "lembrar_depois_de", data)
	return str(data)


def proximo_preparado(hoje: date | None = None) -> dict | None:
	"""O regime preparado a lembrar: até DIAS_DE_AVISO antes do início previsto e fora do "lembrar depois"."""
	hoje = getdate(hoje or today())
	if not frappe.db.table_exists(DOCTYPE):
		return None
	for r in frappe.get_all(
		DOCTYPE,
		filters={"situacao": PREPARADO, "inicio_previsto": ["is", "set"]},
		fields=["name", "nome_regime", "inicio_previsto", "carga_semanal_horas", "lembrar_depois_de"],
		order_by="inicio_previsto asc",
	):
		previsto = getdate(r.inicio_previsto)
		if hoje < previsto - timedelta(days=DIAS_DE_AVISO):
			return None
		if r.lembrar_depois_de and hoje < getdate(r.lembrar_depois_de):
			return None
		return {
			"name": r.name,
			"nome": r.nome_regime,
			"inicio_previsto": str(previsto),
			"horas": flt(r.carga_semanal_horas),
			"dias": (previsto - hoje).days,
		}
	return None


def lembrar(hoje: date | None = None) -> str | None:
	"""Job diário: uma vez por semana, WhatsApp ao RH perguntando se ativa o regime preparado (DP-1)."""
	from hrms_secullum_brasil.apuracao import whatsapp

	hoje = getdate(hoje or today())
	pendente = proximo_preparado(hoje)
	celular = frappe.get_cached_doc("Configuracao Apuracao").get("termo_celular_rh")
	if not pendente or not celular:
		return None
	ano, semana, _dia = hoje.isocalendar()
	chave = f"REG:{pendente['name']}:{ano}-{semana}"
	if frappe.db.exists("Notificacao WhatsApp", {"chave": chave}):
		return None
	texto = _(
		'RH: o regime de jornada "{0}" ({1}h semanais, 2 folgas) está previsto para {2}. Ele só vale quando for '
		"ativado: abra o cockpit do painel de ponto para ativar ou pedir para lembrar depois."
	).format(pendente["nome"], f"{pendente['horas']:g}", frappe.utils.formatdate(pendente["inicio_previsto"]))
	nome = whatsapp.criar(None, "RH", celular, texto, chave=chave)
	situacao = whatsapp.enviar(nome)
	frappe.db.commit()
	return situacao


def resumo_do_cockpit() -> dict:
	"""O regime em vigor hoje e o preparado a lembrar (cartão do cockpit)."""
	atual = regime_na_data(today())
	proximo = proximo_preparado()
	perfis_acima = 0
	if proximo:
		perfis_acima = frappe.db.count(
			"Perfil de Jornada", {"carga_semanal_minutos": [">", round(proximo["horas"] * 60)]}
		)
	return {
		"atual": atual.nome,
		"teto_horas": round(atual.semanal_min / 60, 2),
		"folgas": atual.folgas_semana,
		"proximo": proximo,
		"perfis_acima_do_teto": perfis_acima,  # precisarão de outro horário (no Secullum) ao ativar
		"pode_ativar": bool(set(PAPEIS) & set(frappe.get_roles())) or frappe.session.user == "Administrator",
	}
