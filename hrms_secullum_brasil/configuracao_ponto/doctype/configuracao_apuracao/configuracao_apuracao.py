import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguracaoApuracao(Document):
	def validate(self):
		self.validar_destinatarios_do_termo()
		self.validar_unidades_whatsapp()

	def validar_unidades_whatsapp(self):
		"""RH, 11/11/2026: o envio automático é liberado por unidade, uma por vez (nunca todas de uma vez)."""
		from frappe.utils import now_datetime

		from hrms_secullum_brasil.engine.whatsapp_envio import liberacoes_novas

		linhas = self.get("whatsapp_unidades_liberadas") or []
		vistas = set()
		for linha in linhas:
			if linha.company in vistas:
				frappe.throw(_("A unidade {0} está duas vezes na lista do WhatsApp.").format(linha.company))
			vistas.add(linha.company)
		antes = self.get_doc_before_save()
		anteriores = [x.company for x in (antes.get("whatsapp_unidades_liberadas") or [])] if antes else []
		novas = liberacoes_novas(anteriores, [x.company for x in linhas])
		if len(novas) > 1:
			frappe.throw(
				_("Libere uma unidade por vez no envio automático do WhatsApp (nesta gravação: {0}).").format(
					", ".join(novas)
				),
				title=_("Uma unidade por vez"),
			)
		for linha in linhas:
			if linha.company in novas or not linha.liberada_em:
				linha.liberada_em = linha.liberada_em or now_datetime()
				linha.liberada_por = linha.liberada_por or frappe.session.user

	def on_update(self):
		self.dar_papel_aos_gestores()

	def dar_papel_aos_gestores(self):
		"""Gestor da unidade (pedido do RH, 30/10/2026): quem foi marcado ganha o papel Gestor Ponto."""
		from hrms_secullum_brasil.configuracao_ponto.gestores import garantir_papel, usuario_da_linha

		ganharam = garantir_papel(self.get("termo_destinatarios") or [])
		if ganharam:
			frappe.msgprint(
				_("Papel Gestor Ponto dado a: {0}.").format(", ".join(ganharam)), indicator="green"
			)
		sem_usuario = [
			linha.nome
			for linha in self.get("termo_destinatarios") or []
			if linha.ve_ponto and not usuario_da_linha(linha)
		]
		if sem_usuario:
			frappe.msgprint(
				_(
					"Sem usuário de acesso (ligue o usuário no cadastro do colaborador): {0}. Não vão ver o ponto."
				).format(", ".join(sem_usuario)),
				indicator="orange",
			)

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
			if not linha.email and not linha.celular and (linha.recebe_email or linha.recebe_whatsapp):
				frappe.msgprint(
					_("{0} não tem e-mail nem celular: não vai receber o termo.").format(linha.nome),
					indicator="orange",
				)
