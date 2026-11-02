"""Gestores da unidade (pedido do RH, 30/10/2026).

Um único cadastro por empresa (Configuração Apuração → tabela "Gestores e responsáveis da unidade", DocType
Destinatario do Termo): cada linha é um colaborador ou um usuário que não é funcionário (gerente terceirizado,
contabilidade). As marcações dizem o que a pessoa faz:

- `ve_ponto`: é gestor da unidade — vê e trata o ponto de todos da empresa (inclusive quem entrar depois) e é o
  responsável das pendências e dos alertas do banco de horas;
- `recebe_avisos`: recebe os avisos de WhatsApp dirigidos ao gestor (regras de WhatsApp, monitoramento de horistas);
- `recebe_email` / `recebe_whatsapp`: termo de ocorrências (apuracao/termo_ocorrencias.py).

Empresa sem ninguém marcado: vale o Reporta a do colaborador, como antes.
"""

import frappe
from frappe.utils import cint

CONFIG = "Configuracao Apuracao"
PAPEL = "Gestor Ponto"
PRIVILEGIADOS = {"System Manager", "RH Ponto", PAPEL}


def linhas(company: str | None = None, marcacao: str | None = None) -> list:
	saida = []
	for linha in frappe.get_cached_doc(CONFIG).get("termo_destinatarios") or []:
		if company and linha.company != company:
			continue
		if marcacao and not cint(linha.get(marcacao)):
			continue
		saida.append(linha)
	return saida


def usuario_da_linha(linha) -> str | None:
	"""Colaborador: o usuário do cadastro dele (lido na hora, pode ter sido ligado depois)."""
	if linha.get("tipo") == "Usuário":
		return linha.get("user")
	return frappe.db.get_value("Employee", linha.employee, "user_id") if linha.get("employee") else None


def empresas_do_gestor(user: str) -> list[str]:
	"""Empresas em que o usuário é gestor da unidade (pelo usuário ou pelo cadastro de colaborador dele)."""
	proprios = set(frappe.get_all("Employee", filters={"user_id": user}, pluck="name"))
	return sorted(
		{
			linha.company
			for linha in linhas(marcacao="ve_ponto")
			if (linha.get("tipo") == "Usuário" and linha.get("user") == user)
			or (linha.get("tipo") != "Usuário" and linha.get("employee") in proprios)
		}
	)


def _reporta_a(employee: str) -> str | None:
	return frappe.db.get_value("Employee", employee, "reports_to")


def usuarios_gestores(employee: str) -> list[str]:
	"""Usuários gestores do colaborador: os da unidade; sem nenhum, o usuário do Reporta a."""
	company = frappe.db.get_value("Employee", employee, "company")
	usuarios = [u for u in (usuario_da_linha(x) for x in linhas(company, "ve_ponto")) if u]
	if usuarios:
		return list(dict.fromkeys(usuarios))
	gestor = _reporta_a(employee)
	usuario = frappe.db.get_value("Employee", gestor, "user_id") if gestor else None
	return [usuario] if usuario else []


def contatos_de_aviso(emp) -> list[dict]:
	"""Quem recebe os avisos de WhatsApp do gestor: os marcados na unidade; sem nenhum, o Reporta a.
	Cada contato: nome, primeiro_nome, celular e `chave` (distingue os gestores na mesma mensagem)."""
	from hrms_secullum_brasil.apuracao.termo_ocorrencias import contato_do_destinatario, gestor_de

	saida = []
	for linha in linhas(emp.company, "recebe_avisos"):
		contato = contato_do_destinatario(linha)
		saida.append({**contato, "chave": f"Gestor {linha.get('user') or linha.get('employee')}"})
	if saida:
		return saida
	gestor = gestor_de(frappe._dict(reports_to=emp.get("reports_to") or _reporta_a(emp.name)))
	return [{**gestor, "chave": "Gestor"}] if gestor else []


def tem_gestor_na_unidade(company: str) -> bool:
	return bool(linhas(company, "ve_ponto") or linhas(company, "recebe_avisos"))


def garantir_papel(linhas_da_config) -> list[str]:
	"""Dá o papel Gestor Ponto a quem foi marcado como gestor da unidade e ainda não tem acesso ao ponto.
	Devolve os usuários que ganharam o papel."""
	ganharam = []
	for linha in linhas_da_config:
		if not cint(linha.get("ve_ponto")):
			continue
		usuario = usuario_da_linha(linha)
		if not usuario or usuario in ("Administrator", "Guest") or not frappe.db.exists("User", usuario):
			continue
		if PRIVILEGIADOS & set(frappe.get_roles(usuario)):
			continue
		frappe.get_doc("User", usuario).add_roles(PAPEL)
		ganharam.append(usuario)
	return ganharam
