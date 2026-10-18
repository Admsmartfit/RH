"""Resolução de regras vigentes (PRD, Seção 3.6) — adaptador Frappe sobre engine/vigencia.py.

Escopos de versionamento:
- Regra Sindical CCT: (empresa, sindicato). Versões do mesmo escopo não podem ter vigências
  sobrepostas para cargos em comum (tabela de cargos vazia = todos os cargos).
- Perfil de Jornada: código. Versões do mesmo código não podem ter vigências sobrepostas.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

from hrms_secullum_brasil.apuracao.lote import documento, memo
from hrms_secullum_brasil.engine.vigencia import (
	RegraComVigencia,
	Vigencia,
	conflitos_de_vigencia,
	selecionar_vigentes,
)


class VigenciaSobrepostaError(frappe.ValidationError):
	pass


class RegraAmbiguaError(frappe.ValidationError):
	pass


def vigencia_do_doc(doc) -> Vigencia:
	return Vigencia(getdate(doc.vigencia_inicio), getdate(doc.vigencia_fim) if doc.vigencia_fim else None)


def validar_datas_vigencia(doc: Document) -> None:
	if doc.vigencia_fim and getdate(doc.vigencia_fim) < getdate(doc.vigencia_inicio):
		frappe.throw(_("A vigência não pode terminar antes de começar."), title=_("Vigência inválida"))


def validar_sem_sobreposicao(
	doc: Document, existentes: list[RegraComVigencia], escopo: str, cargos: frozenset[str] = frozenset()
) -> None:
	nova = RegraComVigencia(doc.name, vigencia_do_doc(doc), cargos)
	conflitos = conflitos_de_vigencia(nova, existentes)
	if conflitos:
		frappe.throw(
			_(
				"Vigência sobreposta com {0} no mesmo escopo ({1}). "
				"Encerre a vigência da versão anterior antes de criar a nova."
			).format(", ".join(conflitos), escopo),
			exc=VigenciaSobrepostaError,
			title=_("Vigência sobreposta"),
		)


def titulo_com_vigencia(nome: str, inicio, fim) -> str:
	fim_texto = formatdate(fim) if fim else _("em aberto")
	return f"{nome} ({formatdate(inicio)} a {fim_texto})"


# ------------------------------------------------------------------ carregamento


def carregar_regras_cct(filtros: dict) -> list[RegraComVigencia]:
	linhas = frappe.get_all(
		"Regra Sindical CCT", filters=filtros, fields=["name", "vigencia_inicio", "vigencia_fim"]
	)
	if not linhas:
		return []
	cargos: dict[str, set[str]] = defaultdict(set)
	for c in frappe.get_all(
		"Regra CCT Cargo",
		filters={"parenttype": "Regra Sindical CCT", "parent": ["in", [linha.name for linha in linhas]]},
		fields=["parent", "designation"],
	):
		cargos[c.parent].add(c.designation)
	return [
		RegraComVigencia(linha.name, vigencia_do_doc(linha), frozenset(cargos[linha.name]))
		for linha in linhas
	]


def carregar_perfis(filtros: dict) -> list[RegraComVigencia]:
	return [
		RegraComVigencia(linha.name, vigencia_do_doc(linha))
		for linha in frappe.get_all(
			"Perfil de Jornada", filters=filtros, fields=["name", "vigencia_inicio", "vigencia_fim"]
		)
	]


# ------------------------------------------------------------------ API


def _dados_colaborador(employee: str):
	emp = memo(
		("emp_regras", employee),
		lambda: frappe.db.get_value(
			"Employee",
			employee,
			["name", "company", "designation", "regra_cct", "perfil_jornada"],
			as_dict=True,
		),
	)
	if not emp:
		frappe.throw(_("Colaborador {0} não encontrado.").format(employee), exc=frappe.DoesNotExistError)
	return emp


def get_regra_vigente(employee: str, data) -> Document | None:
	"""Regra Sindical CCT vigente na data para o colaborador, ou None se não houver.

	Com `regra_cct` no cadastro: busca a versão vigente do mesmo escopo (empresa + sindicato)
	da regra informada. Sem `regra_cct`: busca entre todas as CCTs da empresa do colaborador.
	Em ambos os casos a regra precisa valer para o cargo (designation) do colaborador.
	"""
	return regra_vigente_para(_dados_colaborador(employee), data)


def regra_vigente_para(emp, data) -> Document | None:
	"""Como `get_regra_vigente`, a partir dos dados do cadastro (name, company, designation, regra_cct): serve
	também para um Employee em edição, antes de salvar (ex.: troca de cargo)."""
	data = getdate(data)
	employee = emp.name
	if emp.regra_cct:
		escopo = memo(
			("cct_escopo", emp.regra_cct),
			lambda: frappe.db.get_value(
				"Regra Sindical CCT", emp.regra_cct, ["company", "sindicato"], as_dict=True
			),
		)
		filtros = {"company": escopo.company, "sindicato": escopo.sindicato}
	else:
		filtros = {"company": emp.company}

	candidatas = memo(("ccts", tuple(sorted(filtros.items()))), lambda: carregar_regras_cct(filtros))
	vigentes = selecionar_vigentes(candidatas, data, emp.designation)
	if not vigentes:
		return None
	if len(vigentes) > 1:
		frappe.throw(
			_(
				"Mais de uma Regra Sindical CCT vigente em {0} para o colaborador {1}: {2}. "
				"Informe a Regra CCT no cadastro do colaborador."
			).format(formatdate(data), employee, ", ".join(r.nome for r in vigentes)),
			exc=RegraAmbiguaError,
			title=_("Regra CCT ambígua"),
		)
	return documento("Regra Sindical CCT", vigentes[0].nome)


def get_perfil_vigente(employee: str, data) -> Document | None:
	"""Versão do Perfil de Jornada do colaborador (mesmo código) vigente na data, ou None."""
	data = getdate(data)
	emp = _dados_colaborador(employee)
	if not emp.perfil_jornada:
		return None
	codigo = memo(
		("perfil_codigo", emp.perfil_jornada),
		lambda: frappe.db.get_value("Perfil de Jornada", emp.perfil_jornada, "codigo"),
	)
	candidatos = memo(("perfis", codigo), lambda: carregar_perfis({"codigo": codigo}))
	vigentes = selecionar_vigentes(candidatos, data)
	return documento("Perfil de Jornada", vigentes[0].nome) if vigentes else None


# ------------------------------------------------------------------ regra usada em período fechado (PRD 3.6)

CAMPOS_IGNORADOS = {
	"modified",
	"modified_by",
	"titulo",
	"vigencia_fim",
	"idx",
	"_comments",
	"_assign",
	"_liked_by",
	"_user_tags",
}


def _conteudo(doc) -> dict:
	dados = {k: v for k, v in doc.as_dict(no_default_fields=True).items() if k not in CAMPOS_IGNORADOS}
	for chave, valor in list(dados.items()):
		if isinstance(valor, list):
			dados[chave] = [
				{
					k: v
					for k, v in linha.items()
					if k not in CAMPOS_IGNORADOS and k not in ("name", "parent", "creation", "owner")
				}
				for linha in valor
			]
	return frappe.parse_json(frappe.as_json(dados))


def validar_edicao_em_periodo_fechado(doc, companies: list[str] | None = None) -> None:
	"""Regra cuja vigência já alcançou um período fechado não pode mudar: só encerrar a vigência depois do
	último dia fechado. Mudanças de conteúdo exigem nova versão (nova vigência)."""
	if doc.is_new():
		return
	antes = doc.get_doc_before_save()
	if not antes:
		return
	filtros = {"ponto_fechado_ate": ["is", "set"]}
	if companies:
		filtros["name"] = ["in", companies]
	limites = [getdate(c) for c in frappe.get_all("Company", filters=filtros, pluck="ponto_fechado_ate")]
	if not limites:
		return
	limite = max(limites)
	if getdate(doc.vigencia_inicio) > limite:
		return
	if _conteudo(doc) != _conteudo(antes):
		frappe.throw(
			_(
				"Esta regra já foi usada em período fechado (até {0}). Para alterá-la, encerre a vigência e crie "
				"uma nova versão."
			).format(formatdate(limite)),
			title=_("Regra usada em período fechado"),
		)
	if doc.vigencia_fim and getdate(doc.vigencia_fim) < limite:
		frappe.throw(
			_("A vigência só pode terminar depois do último dia fechado ({0}).").format(formatdate(limite)),
			title=_("Regra usada em período fechado"),
		)
