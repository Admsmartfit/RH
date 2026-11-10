from datetime import date

from hrms_secullum_brasil.engine import intervalo_horista as ih


def test_intervalo_no_meio_da_jornada():
	assert ih.intervalo_no_meio(16 * 60 + 55, 21 * 60 + 27, 15) == (1143, 1158)  # 19:03 às 19:18
	assert ih.intervalo_no_meio(600, 610, 15) is None
	assert ih.intervalo_no_meio(600, 900, 0) is None
	assert [ih.hhmm(m) for m in ih.intervalo_no_meio(*ih.minutos_em_ordem(["22:00", "02:30"]), 15)] == [
		"00:07",
		"00:22",
	]


def test_minutos_em_ordem_passa_da_meia_noite():
	assert ih.minutos_em_ordem(["16:55", "21:27"]) == [1015, 1287]
	assert ih.minutos_em_ordem(["21:30", "01:10"]) == [1290, 1510]
	assert ih.hhmm(1510) == "01:10"


def test_mensagem_do_rh_um_por_dia_com_todos():
	itens = [
		ih.ItemRH("Enzo Teixeira", date(2026, 10, 26), 272, "https://x/ponto/cartao/E1?dia=2026-10-26"),
		ih.ItemRH("Ana Lima", date(2026, 10, 26), 258, "https://x/ponto/cartao/E2?dia=2026-10-26"),
	]
	texto = ih.mensagem_rh(date(2026, 10, 27), itens, 3, "https://x/ponto/inconsistencias")
	assert texto.startswith("Instrutores horistas que passaram de 4h15 sem marcar o intervalo (27/10):")
	assert (
		"• Enzo Teixeira: 4h32 em 26/10. Lançar o intervalo: https://x/ponto/cartao/E1?dia=2026-10-26"
		in texto
	)
	assert "não é pago" in texto
	assert texto.endswith(
		"Ainda sem o intervalo, de dias anteriores: 3. Central: https://x/ponto/inconsistencias"
	)
	muitos = [ih.ItemRH(f"P{n}", date(2026, 10, 26), 260, "l") for n in range(ih.LIMITE_LINHAS + 2)]
	assert "• e mais 2: veja na central." in ih.mensagem_rh(date(2026, 10, 27), muitos, 0, "c")
	assert "dias anteriores" not in ih.mensagem_rh(date(2026, 10, 27), itens, 0, "c")
