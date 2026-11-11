"""Plantões eventuais a pagar (docs/PRD-substituicoes.md, 6.4): por unidade e prestador, os plantões realizados no
período, com CNPJ, conta, horas, valor e a NFS-e informada. O pagamento é do financeiro, fora do programa."""

import frappe
from frappe import _


def colunas() -> list[dict]:
	return [
		{
			"fieldname": "company",
			"label": _("Unidade"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 170,
		},
		{
			"fieldname": "prestador",
			"label": _("Prestador"),
			"fieldtype": "Link",
			"options": "Prestador Eventual",
			"width": 110,
		},
		{"fieldname": "nome", "label": _("Nome"), "fieldtype": "Data", "width": 170},
		{"fieldname": "razao_social", "label": _("Razão social"), "fieldtype": "Data", "width": 170},
		{"fieldname": "cnpj", "label": _("CNPJ"), "fieldtype": "Data", "width": 130},
		{"fieldname": "conta", "label": _("Conta / PIX"), "fieldtype": "Data", "width": 170},
		{"fieldname": "plantoes", "label": _("Plantões"), "fieldtype": "Int", "width": 80},
		{"fieldname": "horas", "label": _("Horas"), "fieldtype": "Float", "precision": 2, "width": 80},
		{"fieldname": "valor", "label": _("Valor"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "nfse", "label": _("NFS-e"), "fieldtype": "Data", "width": 140},
	]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	condicoes = {"situacao": "Realizado", "data": ["between", [filters.de, filters.ate]]}
	if filters.company:
		condicoes["company"] = filters.company
	if filters.so_sem_nfse:
		condicoes["nfse_recebida"] = 0
	linhas: dict[tuple, dict] = {}
	for p in frappe.get_list(
		"Plantao Eventual",
		filters=condicoes,
		fields=["company", "prestador", "minutos", "valor", "nfse_numero"],
		order_by="company asc, prestador asc",
	):
		chave = (p.company, p.prestador)
		if chave not in linhas:
			pr = frappe.db.get_value(
				"Prestador Eventual",
				p.prestador,
				["nome", "razao_social", "cnpj", "pix", "banco", "agencia", "conta"],
				as_dict=True,
			)
			conta = pr.pix or " / ".join(x for x in (pr.banco, pr.agencia, pr.conta) if x)
			linhas[chave] = {
				"company": p.company,
				"prestador": p.prestador,
				"nome": pr.nome,
				"razao_social": pr.razao_social,
				"cnpj": pr.cnpj,
				"conta": conta,
				"plantoes": 0,
				"horas": 0.0,
				"valor": 0.0,
				"notas": [],
			}
		linha = linhas[chave]
		linha["plantoes"] += 1
		linha["horas"] += (p.minutos or 0) / 60
		linha["valor"] += float(p.valor or 0)
		if p.nfse_numero:
			linha["notas"].append(p.nfse_numero)
	dados = []
	for linha in linhas.values():
		notas = linha.pop("notas")
		linha["nfse"] = ", ".join(notas) if notas else _("pendente")
		dados.append(linha)
	return colunas(), dados
