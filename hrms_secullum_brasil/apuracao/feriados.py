"""Módulo de feriados (AJ-11 do docs/PRD-alteracoes.md).

- `gerar_feriados(ano)`: inclui na lista de feriados de cada empresa os nacionais (fonte pública), os estaduais e
  municipais cadastrados em Feriado Regional e os pontos facultativos que a empresa adotou. Nunca apaga nem
  duplica; não inclui datas que o RH removeu à mão nem datas de período fechado.
- Holiday List: o RH pode incluir ou remover feriados a qualquer momento. Remoções ficam registradas (a
  importação não as traz de volta); mudanças em período fechado são recusadas; dias alterados são reapurados.
"""

import json
import unicodedata
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_years, getdate, today

from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.engine.feriados import (
	FERIADO,
	RegraFeriado,
	classificar_da_fonte,
	feriados_novos,
)
from hrms_secullum_brasil.integrations.feriados.client import (
	FeriadosClient,
	HttpFeriadosClient,
	MockFeriadosClient,
)


def get_client() -> FeriadosClient:
	if frappe.flags.in_test or frappe.db.get_single_value("Configuracao Apuracao", "feriados_modo_mock"):
		return MockFeriadosClient()
	return HttpFeriadosClient()


def _normalizar(texto: str | None) -> str:
	sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
	return sem_acento.strip().lower()


def _regra(doc) -> RegraFeriado:
	return RegraFeriado(
		doc.descricao, doc.tipo_data, int(doc.dia or 0), int(doc.mes or 0), int(doc.dias_apos_pascoa or 0)
	)


def regionais_da_empresa(company: str, ano: int) -> list[tuple[date, str]]:
	"""Feriados estaduais/municipais da UF e do município da empresa + pontos facultativos adotados."""
	empresa = frappe.get_doc("Company", company)
	adotados = {linha.feriado for linha in empresa.get("pontos_facultativos") or []}
	resultado = []
	for f in frappe.get_all("Feriado Regional", filters={"ativo": 1}, fields=["*"]):
		if f.categoria != FERIADO:
			if f.name in adotados:
				resultado.append((_regra(f).data(ano), f.descricao))
			continue
		mesma_uf = f.uf and f.uf == empresa.get("uf")
		if (f.abrangencia == "Estadual" and mesma_uf) or (
			f.abrangencia == "Municipal"
			and mesma_uf
			and _normalizar(f.municipio) == _normalizar(empresa.get("municipio"))
		):
			resultado.append((_regra(f).data(ano), f.descricao))
	return resultado


def _lista_da_empresa(company: str, ano: int):
	nome = frappe.db.get_value("Company", company, "holiday_list_ponto")
	if nome:
		return frappe.get_doc("Holiday List", nome)
	padrao = f"Feriados - {company}"
	if frappe.db.exists("Holiday List", padrao):
		frappe.db.set_value("Company", company, "holiday_list_ponto", padrao)
		return frappe.get_doc("Holiday List", padrao)
	lista = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": padrao,
			"from_date": date(ano, 1, 1),
			"to_date": date(ano, 12, 31),
		}
	)
	lista.insert(ignore_permissions=True)
	frappe.db.set_value("Company", company, "holiday_list_ponto", lista.name)
	return lista


def _fechado_ate(company: str) -> date | None:
	valor = frappe.db.get_value("Company", company, "ponto_fechado_ate")
	return getdate(valor) if valor else None


@frappe.whitelist()
def gerar_feriados(ano: int, company: str | None = None) -> dict:
	"""Inclui os feriados do ano na lista de cada empresa (ou só de `company`). Devolve quantos por empresa."""
	frappe.only_for(("System Manager", "RH Ponto"))
	ano = int(ano)
	nacionais = [
		(f.data, f.nome)
		for f in get_client().feriados_nacionais(ano)
		if classificar_da_fonte(f.nome) == FERIADO
	]
	empresas = [company] if company else frappe.get_all("Company", pluck="name")
	resumo = {}
	for empresa in empresas:
		lista = _lista_da_empresa(empresa, ano)
		fechado = _fechado_ate(empresa)
		existentes = [getdate(h.holiday_date) for h in lista.holidays]
		removidas = [getdate(d) for d in json.loads(lista.get("datas_removidas") or "[]")]
		novos = [
			(dia, descricao)
			for dia, descricao in feriados_novos(
				nacionais, regionais_da_empresa(empresa, ano), existentes, removidas
			)
			if not fechado or dia > fechado  # não mexe em meses fechados
		]
		for dia, descricao in novos:
			lista.append("holidays", {"holiday_date": dia, "description": descricao})
		lista.from_date = min(getdate(lista.from_date), date(ano, 1, 1))
		lista.to_date = max(getdate(lista.to_date), date(ano, 12, 31))
		lista.flags.ignore_permissions = True
		lista.flags.importacao_de_feriados = True
		lista.save()
		garantir_lista_no_hrms(empresa, lista)
		resumo[empresa] = len(novos)
	return resumo


def garantir_lista_no_hrms(company: str, lista) -> None:
	"""HRMS v16: férias e atestados (Leave Application) só são aceitos com a lista de feriados atribuída à empresa
	(Holiday List Assignment). A mesma lista do ponto passa a valer para o HRMS, se ele ainda não tiver uma."""
	if not frappe.db.get_value("Company", company, "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", lista.name)
	if not frappe.db.exists("DocType", "Holiday List Assignment") or frappe.db.exists(
		"Holiday List Assignment", {"assigned_to": company, "docstatus": 1}
	):
		return
	atribuicao = frappe.get_doc(
		{
			"doctype": "Holiday List Assignment",
			"applicable_for": "Company",
			"assigned_to": company,
			"holiday_list": lista.name,
			"from_date": lista.from_date,
		}
	)
	atribuicao.insert(ignore_permissions=True)
	atribuicao.submit()


@frappe.whitelist()
def atribuir_listas_ao_hrms() -> dict:
	"""Uma vez, para as empresas que já têm a lista do ponto: registra a lista também para o HRMS."""
	frappe.only_for(("System Manager", "RH Ponto"))
	feitas = {}
	for company, nome in frappe.get_all("Company", fields=["name", "holiday_list_ponto"], as_list=True):
		if nome:
			garantir_lista_no_hrms(company, frappe.get_doc("Holiday List", nome))
			feitas[company] = nome
	return feitas


def gerar_ano_seguinte():
	"""Job anual (1º de dezembro): feriados do ano seguinte e aviso ao RH para revisar antes de 1º de janeiro."""
	ano = getdate(add_years(today(), 1)).year
	try:
		resumo = gerar_feriados(ano)
	except Exception:
		frappe.log_error(title=_("Feriados de {0}").format(ano))
		return
	assunto = _("Revise os feriados de {0} antes de 1º de janeiro").format(ano)
	detalhe = ", ".join(f"{empresa}: {qtd} novo(s)" for empresa, qtd in resumo.items())
	for usuario in frappe.get_all(
		"Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent"
	):
		if usuario in ("Administrator", "Guest"):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"subject": assunto,
				"email_content": _(
					"Inclua os feriados municipais e remova o que não vale para a sua cidade. {0}"
				).format(detalhe),
			}
		).insert(ignore_permissions=True)


# ------------------------------------------------------------------ Holiday List (doc_events)


def _datas(doc) -> dict[date, str]:
	return {getdate(h.holiday_date): h.description for h in doc.holidays if not h.get("weekly_off")}


def _empresas_da_lista(lista: str) -> list[str]:
	return sorted(
		set(frappe.get_all("Company", filters={"holiday_list_ponto": lista}, pluck="name"))
		| set(frappe.get_all("Company", filters={"default_holiday_list": lista}, pluck="name"))
	)


def _alteradas(doc) -> tuple[set[date], set[date]]:
	"""(datas incluídas, datas removidas) em relação à versão gravada."""
	antes = doc.get_doc_before_save()
	anteriores = set(_datas(antes)) if antes else set()
	atuais = set(_datas(doc))
	return atuais - anteriores, anteriores - atuais


def validate_holiday_list(doc, method=None):
	if doc.is_new():
		return
	incluidas, removidas = _alteradas(doc)
	if not incluidas and not removidas:
		return
	limites = [f for f in (_fechado_ate(e) for e in _empresas_da_lista(doc.name)) if f]
	fechado = max(limites) if limites else None
	if fechado:
		bloqueadas = sorted(d for d in incluidas | removidas if d <= fechado)
		if bloqueadas:
			frappe.throw(
				_("O ponto está fechado até {0}. Reabra o fechamento para mudar os feriados de: {1}.").format(
					frappe.utils.formatdate(fechado),
					", ".join(frappe.utils.formatdate(d) for d in bloqueadas),
				),
				title=_("Período fechado"),
			)
	if doc.flags.importacao_de_feriados:
		return
	registradas = {getdate(d) for d in json.loads(doc.get("datas_removidas") or "[]")}
	registradas = (registradas | removidas) - incluidas
	doc.datas_removidas = json.dumps(sorted(d.isoformat() for d in registradas)) if registradas else None


def on_update_holiday_list(doc, method=None):
	"""Feriado incluído ou removido: reapura esses dias (até hoje) dos colaboradores que usam a lista."""
	incluidas, removidas = _alteradas(doc)
	dias = sorted(d for d in incluidas | removidas if d <= getdate(today()))
	if not dias:
		return
	empresas = _empresas_da_lista(doc.name)
	filtros = {"status": "Active", "perfil_jornada": ["is", "set"]}
	colaboradores = set(
		frappe.get_all("Employee", filters={**filtros, "company": ["in", empresas or [""]]}, pluck="name")
	)
	colaboradores |= set(
		frappe.get_all("Employee", filters={**filtros, "holiday_list": doc.name}, pluck="name")
	)
	for employee in sorted(colaboradores):
		for dia in dias:
			marcar_para_reapuracao(employee, dia, _("Feriado alterado na lista {0}.").format(doc.name))
