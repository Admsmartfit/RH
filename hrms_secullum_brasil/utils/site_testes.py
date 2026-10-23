"""Preparação do site de testes (docker/site_testes.sh). Nunca rode no site de operação.

No v16 a preparação do HRMS (`hrms.tests.test_utils.before_tests`) supõe que roda dentro do executor de testes
(`frappe.in_test`): fora dele, a conta de e-mail de teste exige senha. Aqui o aviso é ligado como o
`bench run-tests` faz.
"""

import frappe


def preparar(registros: bool = False) -> None:
	"""Preparação do HRMS e, com `registros`, os registros de teste de Employee (o `make_test_records` também importa
	os módulos de teste do HRMS, que no v16 criam dados na importação e exigem o frappe.in_test)."""
	from frappe.tests.utils import make_test_records
	from hrms.tests.test_utils import before_tests

	if not frappe.conf.get("allow_tests"):
		frappe.throw("Este site não é de testes (allow_tests desligado).")
	frappe.in_test = frappe.flags.in_test = True  # v16: frappe.in_test; o flags fica para código antigo
	try:
		before_tests()
		if registros:
			make_test_records("Employee")
	finally:
		frappe.in_test = frappe.flags.in_test = False
	frappe.db.commit()
