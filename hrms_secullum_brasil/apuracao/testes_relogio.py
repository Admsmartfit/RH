"""Para os testes Frappe da escala: "hoje" e "agora" fixos.

O cockpit troca a escala pelas batidas reais nos dias passados (CE-04) e a publicação e o convite aplicam a regra das
48h com a hora real. Teste com data fixa (ex.: sábado 07/11/2026) quebra quando o calendário real passa dela. Este
ajudante congela o relógio dos módulos da escala no momento escolhido.
"""

from datetime import datetime
from unittest.mock import patch

import frappe

MODULOS = (
	"hrms_secullum_brasil.apuracao.cockpit_escala",
	"hrms_secullum_brasil.apuracao.convite_turno",
	"hrms_secullum_brasil.apuracao.whatsapp_escala",
	"hrms_secullum_brasil.apuracao.cobertura",
	"hrms_secullum_brasil.apuracao.banco_talentos",
)


def congelar(caso, agora: datetime, modulos=MODULOS) -> None:
	"""Fixa `getdate()` (sem argumento), `today()` e `now_datetime()` nos módulos; desfeito no fim do teste."""
	getdate, hoje = frappe.utils.getdate, agora.date()

	def data(valor=None, *args, **kwargs):
		return hoje if valor is None else getdate(valor, *args, **kwargs)

	trocas = {"getdate": data, "now_datetime": lambda: agora, "today": lambda: str(hoje)}
	for nome in modulos:
		modulo = frappe.get_module(nome)
		for funcao, falsa in trocas.items():
			if hasattr(modulo, funcao):
				relogio = patch.object(modulo, funcao, falsa)
				relogio.start()
				caso.addCleanup(relogio.stop)
