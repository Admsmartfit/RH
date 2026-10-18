"""Etapa 0 do docs/PRD-alteracoes.md: cadastros da ES Fitness (Vila Velha/ES), sem programar.

    bench --site <site> execute hrms_secullum_brasil.utils.config_es_fitness.aplicar
    bench --site <site> execute hrms_secullum_brasil.utils.config_es_fitness.aplicar --kwargs "{'valor_dia_vr': 25}"

- C-07: empresa ES Fitness Ltda (Vila Velha/ES) e lista de feriados nacionais + estadual de 2026 e 2027.
  Os feriados **municipais** de Vila Velha são incluídos à mão pelo RH (decisão de 15/10/2026).
- C-01 e C-04: Regra Sindical CCT SENALBA-ES x SINDELIVRE-ES 2026/2027 (adicional noturno 25%, banco anual,
  sem redução do intervalo).
- C-03: Regra de Benefício VR proporcional por dia trabalhado (só se `valor_dia_vr` for informado).

Idempotente. O passo a passo para o RH conferir nas telas está em docs/etapa0_rh.md.
"""

from datetime import date

import frappe

from hrms_secullum_brasil.utils.seeds import ACADEMIA, NACIONAIS, _get_or_insert

EMPRESA = "ES Fitness Ltda"
ABREVIACAO = "ESF"
CNPJ = "23.620.822/0002-51"
SINDICATO = "SENALBA-ES × SINDELIVRE-ES 2026/2027"  # noqa: RUF001 (nome oficial)
VIGENCIA_CCT = (date(2026, 5, 1), date(2027, 4, 30))
LISTA = "Feriados 2026-2027 - Vila Velha"

# Datas móveis: Sexta-feira Santa (Páscoa - 2) e Nossa Senhora da Penha (Páscoa + 8, segunda-feira).
MOVEIS = {
	2026: {"Sexta-feira Santa": "04-03", "Nossa Senhora da Penha (estadual)": "04-13"},
	2027: {"Sexta-feira Santa": "03-26", "Nossa Senhora da Penha (estadual)": "04-05"},
}

# C-03: ausências que tiram o dia do VR (resposta do RH de 15/10/2026).
DESCONTOS_VR = {
	"desconta_falta": 1,
	"desconta_atestado": 1,
	"desconta_ferias": 1,
	"desconta_afastamento": 1,
	"desconta_abono": 1,
}
# C-01 e C-04: o que muda na CCT da academia.
CAMPOS_CCT = {
	"percentual_adicional_noturno": 25,  # CCT cl. 12ª
	"banco_modalidade": "Anual",  # CCT cl. 22ª
	"banco_prazo_meses": 12,
	"permite_reducao_intrajornada": 0,  # a CCT não tem cláusula de redução (art. 71 e 611-A, III)
	"dsr_horista_modo": "Mensal",  # AJ-12 / C-06: DSR do horista calculado no mês
	# AJ-08: custeio do benefício social (CCT cl. 14ª)
	"custeio_valor_trabalhador": 26,
	"custeio_dia_vencimento": 10,
	"custeio_inicio": date(2026, 8, 10),
}


def _feriados() -> list[dict]:
	linhas = []
	for ano, moveis in MOVEIS.items():
		fixos = [(dia, nome) for dia, nome in NACIONAIS if nome != "Sexta-feira Santa"]
		for dia, nome in fixos + [(dia, nome) for nome, dia in moveis.items()]:
			linhas.append({"holiday_date": f"{ano}-{dia}", "description": nome})
	return sorted(linhas, key=lambda h: h["holiday_date"])


def _empresa() -> None:
	if not frappe.db.exists("Company", EMPRESA):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": EMPRESA,
				"abbr": ABREVIACAO,
				"default_currency": "BRL",
				"country": "Brazil",
				"tax_id": CNPJ,
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	lista = _get_or_insert(
		"Holiday List",
		{"holiday_list_name": LISTA},
		{
			"holiday_list_name": LISTA,
			"from_date": date(2026, 1, 1),
			"to_date": date(2027, 12, 31),
			"holidays": _feriados(),
		},
	)
	frappe.db.set_value(
		"Company",
		EMPRESA,
		{
			"tax_id": CNPJ,
			"uf": "ES",
			"municipio": "Vila Velha",
			"holiday_list_ponto": lista.name,
			"default_holiday_list": lista.name,
		},
	)


def _cct() -> str:
	nome = frappe.db.get_value("Regra Sindical CCT", {"company": EMPRESA, "sindicato": SINDICATO}, "name")
	doc = frappe.get_doc("Regra Sindical CCT", nome) if nome else frappe.new_doc("Regra Sindical CCT")
	doc.update(
		{
			"company": EMPRESA,
			"sindicato": SINDICATO,
			"uf": "ES",
			"vigencia_inicio": VIGENCIA_CCT[0],
			"vigencia_fim": VIGENCIA_CCT[1],
			**CAMPOS_CCT,
		}
	)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def _vr(valor_dia: float) -> str:
	nome = frappe.db.get_value("Regra de Beneficio", {"company": EMPRESA, "tipo": "VR"}, "name")
	doc = frappe.get_doc("Regra de Beneficio", nome) if nome else frappe.new_doc("Regra de Beneficio")
	doc.update(
		{
			"company": EMPRESA,
			"tipo": "VR",
			"descricao": "Vale-refeição por dia trabalhado",
			"vigencia_inicio": VIGENCIA_CCT[0],
			"modo": "Proporcional",
			"valor_dia": valor_dia,
			**DESCONTOS_VR,
		}
	)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def _corrigir_exemplo() -> list[str]:
	"""C-01/C-04/C-03 também na academia de exemplo (seeds), se ela existir no site."""
	feitos = []
	empresa = ACADEMIA["company_name"]
	for nome in frappe.get_all("Regra Sindical CCT", filters={"company": empresa}, pluck="name"):
		doc = frappe.get_doc("Regra Sindical CCT", nome)
		doc.update(CAMPOS_CCT)
		doc.flags.ignore_permissions = True
		doc.save()
		feitos.append(nome)
	for nome in frappe.get_all(
		"Regra de Beneficio", filters={"company": empresa, "tipo": "VR"}, pluck="name"
	):
		doc = frappe.get_doc("Regra de Beneficio", nome)
		doc.update({"modo": "Proporcional", "valor_dia": doc.valor_dia or 25, **DESCONTOS_VR})
		doc.flags.ignore_permissions = True
		doc.save()
		feitos.append(nome)
	return feitos


def aplicar(valor_dia_vr: float | None = None) -> dict:
	_empresa()
	resumo = {"empresa": EMPRESA, "feriados": LISTA, "cct": _cct()}
	if valor_dia_vr:
		resumo["vr"] = _vr(valor_dia_vr)
	else:
		resumo["vr"] = "não criado: informe valor_dia_vr ou cadastre pela tela (docs/etapa0_rh.md)"
	resumo["exemplo_corrigido"] = _corrigir_exemplo()
	frappe.db.commit()
	print(resumo)
	return resumo
