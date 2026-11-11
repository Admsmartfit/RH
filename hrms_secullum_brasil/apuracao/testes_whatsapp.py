"""Para os testes Frappe que enviam WhatsApp (mock da Evolution): o envio sai na hora, sem o ritmo (intervalo e limite
do dia, CW-11 a CW-13) e sem exigir o aceite do colaborador (CW-05). Os testes desses dois ficam em
`apuracao/test_whatsapp_envio.py`."""

import frappe

CONFIG = "Configuracao Apuracao"


def ligar(modo: str = "Ligado", todas_unidades: bool = True, **extra) -> None:
	"""`todas_unidades`: no teste, o envio automático vale em todas as unidades (na operação, uma por vez)."""
	frappe.flags.whatsapp_todas_unidades = todas_unidades
	for campo, valor in {
		"whatsapp_envio": modo,
		"whatsapp_intervalo_min": 0,
		"whatsapp_intervalo_max": 0,
		"whatsapp_limite_dia": 1_000_000,
		"whatsapp_chip_desde": None,
		"whatsapp_exigir_aceite": 0,
		**extra,
	}.items():
		frappe.db.set_single_value(CONFIG, campo, valor)
