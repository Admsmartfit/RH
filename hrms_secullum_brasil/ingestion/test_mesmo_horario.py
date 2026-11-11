"""Importação do Secullum: o perfil individual criado pelo RH (mesmo horário do Secullum) não é desfeito."""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.ingestion.importacao_secullum import mesmo_horario_do_secullum

EMPRESA = "_Test Company"


def perfil(codigo: str, numero: int | None, inicio="07:00", fim="11:00") -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": codigo,
				"tipo": "Horista",
				"company": EMPRESA,
				"vigencia_inicio": "2026-01-01",
				"numero_horario_secullum": numero,
				"dias": [{"dia_semana": d, "entrada1": inicio, "saida1": fim} for d in DIAS_UTEIS],
			}
		)
		.insert()
		.name
	)


class TestMesmoHorario(FrappeTestCase):
	def test_codigo_copia_horista_e_perfil_individual(self):
		h = hash_curto()[:5].upper()
		do_secullum = perfil(f"SEC-{h}-X", 2)
		copia = perfil(f"SEC-{h}-X-H", 2)
		individual = perfil(f"SEC-{h}-X-H-ALVARO", 2, "05:00", "09:00")
		outro = perfil(f"SEC-{h}-Y", 3)
		sem_numero = perfil(f"MANUAL-{h}", None)
		self.assertTrue(mesmo_horario_do_secullum(do_secullum, do_secullum))
		self.assertTrue(mesmo_horario_do_secullum(copia, do_secullum))  # cópia Horista da revisão
		self.assertTrue(mesmo_horario_do_secullum(individual, do_secullum))  # horário de cada pessoa (RH)
		self.assertFalse(mesmo_horario_do_secullum(individual, outro))  # trocou de horário no Secullum
		self.assertFalse(mesmo_horario_do_secullum(sem_numero, do_secullum))
		self.assertFalse(mesmo_horario_do_secullum(None, do_secullum))
