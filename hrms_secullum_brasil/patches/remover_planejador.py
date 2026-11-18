"""Retirada do planejador de escalas (docs/PRD-quadro-tarefas.md, seção 6; RH, 18/11/2026): apaga os DocTypes de
simulação e os dados deles (o atualizador do servidor faz o backup antes de migrar)."""

import frappe

DOCTYPES = (
	"Vaga do Modelo de Escala",
	"Modelo de Escala da Rede",
	"Planejamento de Escala",
	"Simulacao de Escala",
)


def execute():
	for nome in DOCTYPES:
		if frappe.db.exists("DocType", nome):
			frappe.delete_doc("DocType", nome, force=True, ignore_permissions=True, ignore_missing=True)
		frappe.db.sql_ddl(f"drop table if exists `tab{nome}`")
	# o atalho "/ponto/planejador" sai junto com o workspace, que é recriado a partir do arquivo (ponto.json)
	frappe.db.delete("Workspace Link", {"link_to": ["in", DOCTYPES]})
