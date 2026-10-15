"""Revisão de permissões de todas as Roles (PRD Seção 10 e 3.7), a partir dos JSONs dos DocTypes e do hooks.py.

- Colaborador: só leitura (e impressão do próprio espelho), sempre com filtro por colaborador.
- Gestor Ponto: lê a equipe, cria/edita tratamentos e inconsistências; nunca submete nem cancela; não vê
  saúde (atestados, alertas), folha (fechamentos), configurações nem logs de integração.
- RH Saúde: único papel de negócio com permlevel 1 (CID, anexos, dados do médico).
- Todo DocType com campo `employee` visível a Gestor/Colaborador tem filtro de linha (permission_query_conditions
  e has_permission).
"""

import json
from pathlib import Path

import pytest

from hrms_secullum_brasil import hooks

APP = Path(__file__).resolve().parents[2]
RESTRITOS = {"Gestor Ponto", "Colaborador"}
SO_RH = {
	"Atestado Medico",
	"Alerta Previdenciario",
	"Fechamento de Ponto",
	"Fechamento Banco de Horas",
	"Configuracao Secullum",
	"Configuracao Apuracao",
	"Secullum Sync Log",
	"Divergencia Cadastro Secullum",
	"Divergencia Totais Secullum",
	"Regra de Beneficio",
	"Regra de Premiacao",
}


def doctypes():
	resultado = {}
	for caminho in APP.rglob("doctype/*/*.json"):
		d = json.loads(caminho.read_text(encoding="utf-8"))
		if d.get("doctype") == "DocType" and not d.get("istable"):
			resultado[d["name"]] = d
	return resultado


DOCTYPES = doctypes()


def permissoes(nome, papel):
	return [p for p in DOCTYPES[nome].get("permissions", []) if p["role"] == papel]


def test_todos_os_doctypes_tem_permissoes():
	sem = [n for n, d in DOCTYPES.items() if not d.get("permissions")]
	assert sem == []


@pytest.mark.parametrize("nome", sorted(DOCTYPES))
def test_colaborador_so_le(nome):
	for p in permissoes(nome, "Colaborador"):
		assert not any(p.get(acao) for acao in ("write", "create", "delete", "submit", "cancel", "amend")), (
			nome
		)


@pytest.mark.parametrize("nome", sorted(DOCTYPES))
def test_gestor_nunca_submete_nem_cancela(nome):
	for p in permissoes(nome, "Gestor Ponto"):
		assert not p.get("submit") and not p.get("cancel") and not p.get("amend"), nome


@pytest.mark.parametrize("nome", sorted(SO_RH))
def test_dados_de_saude_folha_e_configuracao_so_para_rh(nome):
	assert not [p for p in DOCTYPES[nome]["permissions"] if p["role"] in RESTRITOS], nome


def test_permlevel_1_so_para_rh_saude_e_system_manager():
	for nome, d in DOCTYPES.items():
		nivel_1 = [f["fieldname"] for f in d["fields"] if f.get("permlevel")]
		papeis = {p["role"] for p in d["permissions"] if p.get("permlevel")}
		if nivel_1:
			assert papeis == {"RH Saúde", "System Manager"}, nome
		else:
			assert not papeis, nome


def test_cid_e_anexo_do_atestado_em_permlevel_1():
	campos = {f["fieldname"]: f for f in DOCTYPES["Atestado Medico"]["fields"]}
	for campo in ("cid", "grupo_cid", "anexo", "correlacionado_com", "medico_nome", "medico_numero"):
		assert campos[campo].get("permlevel") == 1, campo


def test_submit_de_fechamentos_e_tratamentos_so_para_rh():
	for nome in (
		"Fechamento de Ponto",
		"Fechamento Banco de Horas",
		"Tratamento de Ponto",
		"Atestado Medico",
	):
		papeis = {p["role"] for p in DOCTYPES[nome]["permissions"] if p.get("submit")}
		assert papeis <= {"System Manager", "RH Ponto", "RH Saúde"}, nome


@pytest.mark.parametrize("nome", sorted(DOCTYPES))
def test_doctype_por_colaborador_visivel_a_restritos_tem_filtro_de_linha(nome):
	d = DOCTYPES[nome]
	tem_employee = any(f["fieldname"] == "employee" for f in d["fields"])
	visivel = any(p["role"] in RESTRITOS and p.get("read") for p in d["permissions"])
	if tem_employee and visivel:
		assert nome in hooks.permission_query_conditions, nome
		assert nome in hooks.has_permission, nome


def test_configuracoes_sao_single_e_so_rh():
	for nome in ("Configuracao Secullum", "Configuracao Apuracao"):
		assert DOCTYPES[nome].get("issingle") == 1
		assert {p["role"] for p in DOCTYPES[nome]["permissions"]} == {"System Manager", "RH Ponto"}
