"""WhatsApp do cockpit e do cartão (docs/PRD-cockpit-escalas.md CE-08; docs/PRD-tratamento-inconsistencias.md TI-08).

- Publicação de escala: uma mensagem por pessoa com o resumo do que mudou para ela, pela regra ativa do evento
  "Escala: turno incluído/alterado/removido" que alcança a empresa e o cargo. Sem regra, ninguém recebe (o registro
  da publicação fica sem WhatsApp).
- Cobrança de inconsistência: o gestor/RH envia do balão do cartão, com o texto da regra "Cobrança de inconsistência"
  (ou o padrão) editado na hora. Unidirecional; nunca leva CID ou dado de saúde.

As duas passam pela trava geral, pelo horário (8h-20h) e pela homologação da regra (CE-09) de `whatsapp.enviar`.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.regras_whatsapp import _filtros, regras_ativas
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")


def _regra_que_alcanca(evento: str, emp):
	for regra in regras_ativas(evento):
		doc = frappe.get_doc("Regra Envio WhatsApp", regra.name)
		empresas, cargos = _filtros(doc)
		if com.alcanca(emp.company, emp.designation, empresas, cargos):
			return doc
	return None


def _nome_da_empresa(company: str) -> str:
	return frappe.get_cached_value("Company", company, "company_name") or company


def avisar_publicacao(publicacao: str) -> list[str]:
	"""CE-08: cada pessoa da publicação recebe o resumo dos dias que mudaram para ela."""
	doc = frappe.get_doc("Publicacao de Escala", publicacao)
	por_pessoa: dict[str, list] = {}
	for linha in doc.linhas:
		por_pessoa.setdefault(linha.employee, []).append(linha)
	nomes = []
	for employee, linhas in por_pessoa.items():
		emp = frappe.get_cached_doc("Employee", employee)
		regra = _regra_que_alcanca(com.ESCALA, emp)
		if not regra or not regra.para_colaborador:
			continue
		texto = montar_mensagem(
			regra.mensagem_colaborador or com.texto_padrao(com.ESCALA, "Colaborador"),
			primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
			empresa=_nome_da_empresa(emp.company),
			mudancas=com.linhas_de_mudanca((getdate(x.data), x.antes or "", x.depois or "") for x in linhas),
		)
		nome = whatsapp.criar(
			employee,
			"Colaborador",
			emp.cell_number,
			texto,
			regra=regra.name,
			chave=f"ESC:{publicacao}:{employee}",
			publicacao=publicacao,
		)
		whatsapp.enviar(nome)
		for linha in linhas:
			frappe.db.set_value(linha.doctype, linha.name, "notificacao", nome, update_modified=False)
		nomes.append(nome)
	return nomes


# ------------------------------------------------------------------ cobrança de inconsistência (TI-08)


def _inconsistencia_para_cobrar(nome: str):
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc("Inconsistencia de Ponto", nome)
	doc.check_permission("read")
	if not doc.data:
		frappe.throw(_("A inconsistência {0} não é de um dia específico.").format(nome))
	return doc


@frappe.whitelist()
def texto_cobranca(inconsistencia: str) -> dict:
	"""Texto pronto (editável) da cobrança, pela regra do evento ou o padrão."""
	inc = _inconsistencia_para_cobrar(inconsistencia)
	emp = frappe.get_cached_doc("Employee", inc.employee)
	regra = _regra_que_alcanca(com.COBRANCA, emp)
	modelo = (regra.mensagem_colaborador if regra else None) or com.texto_padrao(com.COBRANCA, "Colaborador")
	data = getdate(inc.data)
	texto = montar_mensagem(
		modelo,
		primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
		nome=com.nome_proprio(emp.employee_name),
		data=com.data_curta(data),
		dia_semana=com.dia_da_semana(data),
		descricao=motivo_da_cobranca(inc),
		empresa=_nome_da_empresa(emp.company),
	)
	return {
		"texto": texto,
		"tem_celular": bool(emp.cell_number),
		"regra": regra.name if regra else None,
		# atalho para o RH ajustar o texto padrão (marcadores {primeiro_nome}, {data}, {dia_semana}, {descricao})
		"editar_modelo": f"/app/regra-envio-whatsapp/{regra.name}" if regra else "/app/regra-envio-whatsapp",
		"em_teste": bool(regra and com.aguarda_envio_manual(regra.situacao)),
	}


@frappe.whitelist()
def cobrar_inconsistencia(inconsistencia: str, texto: str) -> dict:
	"""Envia a cobrança com o texto editado; fica registrada na Notificacao WhatsApp ligada à inconsistência."""
	inc = _inconsistencia_para_cobrar(inconsistencia)
	texto = (texto or "").strip()
	if not texto:
		frappe.throw(_("Escreva a mensagem."))
	emp = frappe.get_cached_doc("Employee", inc.employee)
	if not emp.cell_number:
		frappe.throw(_("{0} não tem celular no cadastro.").format(emp.employee_name))
	regra = _regra_que_alcanca(com.COBRANCA, emp)
	nome = whatsapp.criar(
		inc.employee,
		"Colaborador",
		emp.cell_number,
		texto,
		regra=regra.name if regra else None,
		inconsistencia=inc.name,
	)
	return {"notificacao": nome, "situacao": whatsapp.enviar(nome)}


def motivo_da_cobranca(inc) -> str:
	"""O motivo em linguagem de RH (a explicação do tipo) com o detalhe do dia, sem dado de saúde."""
	from hrms_secullum_brasil.engine.sugestoes import orientar

	explicacao = orientar(inc.tipo).explicacao.rstrip(".")
	detalhe = (inc.descricao or "").strip().rstrip(".")
	return (
		f"{explicacao} ({detalhe})."
		if detalhe and detalhe.lower() not in explicacao.lower()
		else f"{explicacao}."
	)
