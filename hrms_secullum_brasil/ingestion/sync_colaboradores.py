"""Sincronização de colaboradores Frappe -> Secullum e reconciliação diária (PRD, 6.2).

O Frappe é a fonte da verdade. O que seria enviado ao Secullum (payload) tem um hash guardado em
Employee.secullum_hash após cada envio bem-sucedido; o job só é enfileirado quando esse hash muda,
então alterar um campo irrelevante (ex.: telefone) não dispara sincronização.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.ingestion.secullum import (
	get_client,
	id_banco_da_empresa,
	integracao_ativa,
	registrar_evento,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError, SecullumValidacaoError
from hrms_secullum_brasil.integrations.secullum.mapeamento import (
	DadosColaborador,
	campos_faltantes,
	comparar_cadastros,
	hash_payload,
	montar_payload_funcionario,
)

METODO_SYNC = "hrms_secullum_brasil.ingestion.sync_colaboradores.sincronizar_colaborador"
TIPO_INCONSISTENCIA = "erro_sync_cadastro"
DIVERGENCIA = "Divergencia Cadastro Secullum"
CACHE_AUXILIARES_SEGUNDOS = 24 * 3600


# ------------------------------------------------------------------ payload


def dados_do_colaborador(emp) -> DadosColaborador:
	perfil = get_perfil_vigente(emp.name, today()) if emp.get("perfil_jornada") else None
	return DadosColaborador(
		nome=emp.employee_name,
		cpf=emp.get("cpf"),
		pis=emp.get("pis"),
		numero_folha=emp.get("matricula_secullum") or emp.name,
		admissao=getdate(emp.date_of_joining) if emp.date_of_joining else None,
		demissao=getdate(emp.relieving_date) if emp.relieving_date else None,
		empresa_documento=frappe.get_cached_value("Company", emp.company, "tax_id"),
		horario_numero=cint(perfil.numero_horario_secullum) if perfil else None,
		departamento=frappe.get_cached_value("Department", emp.department, "department_name")
		if emp.department
		else None,
		funcao=emp.designation,
	)


def payload_do_colaborador(emp) -> dict:
	return montar_payload_funcionario(dados_do_colaborador(emp))


# ------------------------------------------------------------------ doc_events


def on_update_employee(doc, method=None):
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if not integracao_ativa():
		return
	if hash_payload(payload_do_colaborador(doc)) == doc.get("secullum_hash"):
		return
	enfileirar(doc.name)


def enfileirar(employee: str) -> None:
	frappe.enqueue(
		METODO_SYNC,
		queue="long",
		job_id=f"secullum-funcionario-{employee}",
		deduplicate=True,
		enqueue_after_commit=True,
		employee=employee,
	)


# ------------------------------------------------------------------ job


def vinculos_ativos_no_mesmo_banco(emp, id_banco: str) -> list[str]:
	"""O Secullum identifica o funcionário pelo CPF: dois vínculos ativos no mesmo banco se sobrescreveriam."""
	outros = frappe.get_all(
		"Employee",
		filters={"cpf": emp.cpf, "name": ["!=", emp.name], "status": "Active"},
		fields=["name", "company"],
	)
	return sorted(o.name for o in outros if id_banco_da_empresa(o.company) == id_banco)


def _registrar_erro(emp, descricao: str, severidade: str = "Média") -> None:
	registrar_inconsistencia(
		emp.name,
		TIPO_INCONSISTENCIA,
		descricao,
		severidade=severidade,
		referencia_doctype="Employee",
		referencia_name=emp.name,
	)
	registrar_evento(
		"Cadastro Funcionario",
		"Erro",
		erro=descricao,
		referencia_doctype="Employee",
		referencia_name=emp.name,
	)


def _garantir_auxiliar(client, id_banco: str, tipo: str, descricao: str) -> None:
	"""Departamento e Função precisam existir no Secullum; o POST é idempotente (chave = descrição)."""
	chave = f"secullum_aux:{id_banco}:{tipo}:{descricao}"
	if frappe.cache().get_value(chave):
		return
	if tipo == "departamento":
		client.salvar_departamento(descricao)
	else:
		client.salvar_funcao(descricao)
	frappe.cache().set_value(chave, 1, expires_in_sec=CACHE_AUXILIARES_SEGUNDOS)


def sincronizar_colaborador(employee: str) -> bool:
	"""Envia o colaborador ao Secullum. Erros viram Inconsistencia de Ponto; nunca levanta exceção."""
	emp = frappe.get_doc("Employee", employee)
	payload = payload_do_colaborador(emp)

	faltando = campos_faltantes(payload)
	if faltando:
		_registrar_erro(
			emp, _("Campos obrigatórios para o Secullum não preenchidos: {0}.").format(", ".join(faltando))
		)
		return False

	id_banco = id_banco_da_empresa(emp.company)
	conflitos = vinculos_ativos_no_mesmo_banco(emp, id_banco)
	if conflitos:
		_registrar_erro(
			emp,
			_(
				"Outro vínculo ativo com o mesmo CPF usa o mesmo banco Secullum: {0}. O Secullum identifica "
				"o funcionário pelo CPF e um cadastro sobrescreveria o outro. Use bancos diferentes por "
				"empresa (Company > Banco Secullum da empresa) ou encerre o vínculo anterior."
			).format(", ".join(conflitos)),
			severidade="Alta",
		)
		return False

	client = get_client(id_banco)
	try:
		_garantir_auxiliar(client, id_banco, "departamento", payload["DepartamentoDescricao"])
		_garantir_auxiliar(client, id_banco, "funcao", payload["FuncaoDescricao"])
		client.salvar_funcionario(payload)
		remoto = client.buscar_funcionario_por_cpf(payload["Cpf"])
	except SecullumValidacaoError as exc:
		_registrar_erro(emp, _("O Secullum recusou o cadastro: {0}").format(exc))
		return False
	except SecullumError as exc:
		_registrar_erro(emp, _("Falha ao comunicar com o Secullum: {0}").format(exc))
		return False

	id_remoto = (remoto or {}).get("Id")
	frappe.db.set_value(
		"Employee",
		emp.name,
		{
			"secullum_hash": hash_payload(payload),
			"secullum_sincronizado_em": now_datetime(),
			"id_secullum": str(id_remoto) if id_remoto is not None else emp.get("id_secullum"),
		},
		update_modified=False,
	)
	resolver_inconsistencias(emp.name, TIPO_INCONSISTENCIA)
	registrar_evento(
		"Cadastro Funcionario",
		"Sucesso",
		registros=1,
		id_banco=id_banco,
		referencia_doctype="Employee",
		referencia_name=emp.name,
	)
	return True


@frappe.whitelist()
def enfileirar_todos() -> int:
	"""Carga inicial: enfileira todos os colaboradores ativos com CPF."""
	frappe.only_for(("System Manager", "RH Ponto"))
	if not integracao_ativa():
		frappe.throw(_("Ative a integração na Configuracao Secullum antes de enviar os colaboradores."))
	nomes = frappe.get_all("Employee", filters={"status": "Active", "cpf": ["is", "set"]}, pluck="name")
	for nome in nomes:
		enfileirar(nome)
	return len(nomes)


# ------------------------------------------------------------------ reconciliação


def reconciliar_cadastros() -> int:
	"""Job diário: compara Secullum x Frappe por banco e grava o retrato em Divergencia Cadastro Secullum.

	Não altera nada no Secullum nem no Frappe (PRD, 6.2). Cada execução substitui as divergências
	anteriores do mesmo banco.
	"""
	if not integracao_ativa():
		return 0

	execucao = now_datetime()
	locais: dict[str, dict[str, tuple[str, dict]]] = defaultdict(dict)
	locais.setdefault(id_banco_da_empresa(None), {})  # o banco padrão é sempre conferido
	for nome in frappe.get_all("Employee", filters={"status": "Active", "cpf": ["is", "set"]}, pluck="name"):
		emp = frappe.get_doc("Employee", nome)
		payload = payload_do_colaborador(emp)
		locais[id_banco_da_empresa(emp.company)][payload["Cpf"]] = (emp.name, payload)

	total = 0
	for id_banco, por_cpf in locais.items():
		try:
			remotos = get_client(id_banco).listar_funcionarios()
		except SecullumError as exc:
			registrar_evento("Reconciliacao", "Erro", erro=str(exc), id_banco=id_banco)
			continue

		divergencias = comparar_cadastros({cpf: payload for cpf, (_, payload) in por_cpf.items()}, remotos)
		frappe.db.delete(DIVERGENCIA, {"id_banco": id_banco})
		for d in divergencias:
			frappe.get_doc(
				{
					"doctype": DIVERGENCIA,
					"execucao": execucao,
					"id_banco": id_banco,
					"tipo": d.tipo,
					"employee": por_cpf[d.cpf][0] if d.cpf in por_cpf else None,
					"cpf": d.cpf,
					"nome_secullum": d.nome_secullum,
					"campo": d.campo,
					"valor_frappe": d.valor_frappe,
					"valor_secullum": d.valor_secullum,
				}
			).insert(ignore_permissions=True)
		total += len(divergencias)
		registrar_evento("Reconciliacao", "Sucesso", registros=len(divergencias), id_banco=id_banco)
	return total
