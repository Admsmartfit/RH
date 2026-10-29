import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguracaoApuracao(Document):
	def validate(self):
		self.validar_destinatarios_do_termo()

	def validar_destinatarios_do_termo(self):
		"""docs/PRD-termo-ocorrencias.md (DO-2): quem recebe o termo por empresa, colaborador ou usuário (que pode não
		ser funcionário). Nome, e-mail e celular vêm do cadastro quando não informados."""
		from hrms_secullum_brasil.apuracao.termo_ocorrencias import contato_do_destinatario

		for linha in self.get("termo_destinatarios") or []:
			if linha.tipo == "Colaborador" and not linha.employee:
				frappe.throw(
					_("Linha {0} dos destinatários do termo: escolha o colaborador.").format(linha.idx)
				)
			if linha.tipo == "Usuário" and not linha.user:
				frappe.throw(_("Linha {0} dos destinatários do termo: escolha o usuário.").format(linha.idx))
			if linha.tipo == "Colaborador":
				linha.user = None
			else:
				linha.employee = linha.designation = None
			contato = contato_do_destinatario(linha)
			linha.nome = contato["nome"]
			linha.email = linha.email or contato["email"]
			linha.celular = linha.celular or contato["celular"]
			if not linha.email and not linha.celular:
				frappe.msgprint(
					_("{0} não tem e-mail nem celular: não vai receber o termo.").format(linha.nome),
					indicator="orange",
				)
