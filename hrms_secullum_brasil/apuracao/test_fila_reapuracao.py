"""Limpeza diária da fila de reapuração (auditoria de 02/11/2026): só as linhas processadas antigas saem."""

from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from hrms_secullum_brasil.apuracao.reapuracao import limpar_fila_processada

FILA = "Reapuracao Pendente"


class TestFilaReapuracao(FrappeTestCase):
	def linha(self, status: str, dias_atras: int) -> str:
		nome = (
			frappe.get_doc(
				{
					"doctype": FILA,
					"employee": frappe.get_all("Employee", limit=1, pluck="name")[0],
					"data": date(2026, 1, 1),
					"status": status,
					"motivo": "teste",
					"ultima_solicitacao": now_datetime(),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value(
			FILA, nome, "modified", add_days(now_datetime(), -dias_atras), update_modified=False
		)
		return nome

	def test_apaga_so_processada_antiga(self):
		antiga = self.linha("Processada", 40)
		recente = self.linha("Processada", 5)
		pendente_antiga = self.linha("Pendente", 90)  # um dia nunca reapurado não some
		self.assertGreaterEqual(limpar_fila_processada(), 1)
		self.assertFalse(frappe.db.exists(FILA, antiga))
		self.assertTrue(frappe.db.exists(FILA, recente))
		self.assertTrue(frappe.db.exists(FILA, pendente_antiga))
