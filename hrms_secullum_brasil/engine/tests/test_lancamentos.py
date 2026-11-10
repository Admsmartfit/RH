from datetime import date

from hrms_secullum_brasil.engine import lancamentos as la


def _dia(**campos):
	base = {"data": date(2026, 11, 3), "situacao": "Trabalho", "batidas": 0, "abonado": False}
	return la.DiaDaFalta(**{**base, **campos})


def test_periodo():
	assert la.erros_do_periodo(None, date(2026, 11, 3)) == ["Informe o início e o fim."]
	assert la.erros_do_periodo(date(2026, 11, 3), date(2026, 11, 2)) == [
		"O fim não pode ser antes do início."
	]
	assert la.erros_do_periodo(date(2026, 1, 1), date(2027, 1, 2)) == [
		"Um lançamento cobre no máximo 366 dias."
	]
	assert la.erros_do_periodo(date(2026, 11, 3), date(2026, 11, 3)) == []


def test_dias_e_dias_a_reapurar():
	assert la.dias(date(2026, 10, 30), date(2026, 11, 2)) == [
		date(2026, 10, 30),
		date(2026, 10, 31),
		date(2026, 11, 1),
		date(2026, 11, 2),
	]
	hoje = date(2026, 11, 8)
	assert la.dias_a_reapurar(date(2026, 11, 7), date(2026, 11, 20), hoje) == [
		date(2026, 11, 7),
		date(2026, 11, 8),
	]
	assert la.dias_a_reapurar(date(2026, 12, 1), date(2026, 12, 30), hoje) == []  # férias futuras: nada agora


def test_falta_so_em_dia_de_trabalho_sem_batida_e_sem_abono():
	assert la.motivo_da_falta(_dia()) is None
	assert la.motivo_da_falta(_dia(fechado=True)) == "03/11/2026: período fechado."
	assert la.motivo_da_falta(_dia(futuro=True)) == "03/11/2026: dia que ainda não chegou."
	assert la.motivo_mantida("FT", "TRP-1") == "Falta justificada (FT) — TRP-1"
	assert la.motivo_da_falta(_dia(situacao="Folga")) == "03/11/2026: não é dia de trabalho (folga)."
	assert la.motivo_da_falta(_dia(falta_lancada=True)) == "03/11/2026: a falta já está lançada."
	assert "tire o abono" in la.motivo_da_falta(_dia(abonado=True))
	assert "desconsidere-as" in la.motivo_da_falta(_dia(batidas=2))


def test_separar_faltas_de_um_periodo():
	entram, avisos = la.separar_faltas(
		[
			_dia(data=date(2026, 11, 3)),
			_dia(data=date(2026, 11, 4), batidas=1),
			_dia(data=date(2026, 11, 8), situacao="Repouso"),
		]
	)
	assert entram == [date(2026, 11, 3)]
	assert len(avisos) == 2


def test_justificativa_da_falta_precisa_do_efeito_falta():
	assert la.erro_da_justificativa(None) == "Escolha a justificativa da falta."
	assert "efeito" in la.erro_da_justificativa("Abona o dia")
	assert la.erro_da_justificativa("Falta") is None


def test_tipos_de_licenca_sem_atestado_e_sem_nao_remunerada():
	tipos = [
		{"name": "Férias"},
		{"name": "Atestado Médico"},
		{"name": "Licença não remunerada", "is_lwp": 1},
		{"name": "Casamento"},
		{"name": "Antigo", "disabled": 1},
	]
	assert la.tipos_de_licenca(tipos) == ["Casamento", "Férias"]


def test_texto_do_abono():
	assert la.texto_do_abono("Atestado Medico") == "Atestado"
	assert la.texto_do_abono("Leave Application", "Férias") == "Férias"
	assert la.texto_do_abono("Leave Application") == "Licença"
	assert la.texto_do_abono("Afastamento Secullum") == "Afastamento"
	assert la.texto_do_abono(None) == "Abonado"
