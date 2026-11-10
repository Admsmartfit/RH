"""Pausa paga por liberalidade do instrutor e horas não autorizadas (pedido do RH, 04/11/2026); instrutor horista que
passa de 4h15 sem marcar o intervalo (RH, 09/11/2026)."""

from datetime import date, datetime

from hrms_secullum_brasil.engine.apuracao_dia import INTERVALO_NAO_MARCADO, apurar_dia
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

DIA = date(2026, 10, 27)
EXCESSO = "excesso_jornada_nao_autorizada"


def hora(h):
	return datetime(2026, 10, 27, *(int(x) for x in h.split(":")))


def dia(*horas, incluidas=(), pausa=15, previsto=(17 * 60, 21 * 60), horista=True):
	return apurar_dia(
		EntradaDia(
			DIA,
			tuple(hora(h) for h in horas),
			JornadaPrevista((Periodo(*previsto),)),
			horista=horista,
			horista_escalado=horista,
			pausa_paga_min=pausa,
			marcacoes_incluidas=frozenset(hora(h) for h in incluidas),
		)
	)


def tipos(r):
	return r.tipos_inconsistencia()


# ------------------------------------------------------------------ instrutor horista (RH, 09/11/2026)


def test_horista_ate_4h15_sem_pausa_nao_abre_nada():
	r = dia("17:45", "22:00")  # 4h15 exatas
	assert r.trabalhado == 255 and r.pausa_paga == 0
	assert INTERVALO_NAO_MARCADO not in tipos(r) and EXCESSO not in tipos(r)


def test_horista_4h18_sem_pausa_vai_para_o_rh_e_nao_para_o_instrutor():
	r = dia("17:45", "22:03")
	assert r.trabalhado == 258 and r.pausa_paga == 0
	assert tipos(r) == [INTERVALO_NAO_MARCADO]  # nem "intrajornada" nem horas não autorizadas (WhatsApp)
	[inc] = r.inconsistencias
	assert inc.mensagem.startswith("Trabalhou 4h18 sem marcar o intervalo (passou de 4h15). O RH lança")


def test_horista_intervalo_lancado_pelo_rh_desconta_e_nao_e_pago():
	r = dia("16:55", "19:03", "19:18", "21:27", incluidas=("19:03", "19:18"))
	assert (r.trabalhado, r.pausa_paga) == (257, 0)  # 4h32 no dia: o intervalo sai e não é pago
	[inc] = [i for i in r.inconsistencias if i.tipo == INTERVALO_NAO_MARCADO]
	assert "Intervalo de 15 min lançado pelo RH, sem remuneração" in inc.mensagem  # continua para o termo
	assert "intrajornada" not in tipos(r) and EXCESSO not in tipos(r)


def test_horista_ate_4h15_com_a_pausa_incluida_continua_paga():
	r = dia("17:45", "19:30", "19:45", "21:59", incluidas=("19:30", "19:45"))
	assert (r.trabalhado, r.pausa_paga) == (239, 15)  # 4h14 no dia
	assert INTERVALO_NAO_MARCADO not in tipos(r)


def test_horista_que_marcou_o_intervalo_nao_entra():
	r = dia("17:00", "19:00", "19:20", "21:52")  # pausa batida de 20 min, 4h32 trabalhadas
	assert r.pausa_paga == 0
	assert INTERVALO_NAO_MARCADO not in tipos(r) and EXCESSO not in tipos(r)  # horas pagas, sem WhatsApp


def test_horista_feriado_ou_sem_pausa_no_cargo_nao_entra():
	assert INTERVALO_NAO_MARCADO not in tipos(dia("17:45", "22:30", pausa=0))


# ------------------------------------------------------------------ instrutor mensalista (regra de 04/11/2026)


def test_4h18_com_a_pausa_incluida_fica_4h03_e_paga_15_a_parte():
	r = dia("17:45", "19:54", "20:09", "22:03", incluidas=("19:54", "20:09"), horista=False)
	assert (r.trabalhado, r.pausa_paga) == (243, 15)  # a pausa não é trabalho
	assert EXCESSO not in tipos(r)
	assert "intrajornada" not in tipos(r)


def test_pausa_batida_no_relogio_e_so_trabalho():
	r = dia("17:45", "19:54", "20:09", "22:03", horista=False)  # as quatro batidas vieram do relógio
	assert (r.trabalhado, r.pausa_paga) == (243, 0)
	assert EXCESSO not in tipos(r)


def test_pausa_batida_conta_o_excesso_sobre_o_trabalhado():
	r = dia("17:00", "19:00", "19:20", "21:52", horista=False)  # pausa batida de 20 min, 4h32 trabalhadas
	[inc] = [i for i in r.inconsistencias if i.tipo == EXCESSO]
	assert inc.mensagem.startswith("32 min além da jornada contratada (4h00), já com a pausa feita")
	assert EXCESSO not in tipos(dia("17:00", "19:00", "19:20", "21:30", horista=False))  # 10 min


def test_4h52_mesmo_com_a_pausa_tem_37_min_nao_autorizados():
	r = dia(
		"12:08",
		"14:34",
		"14:49",
		"17:00",
		incluidas=("14:34", "14:49"),
		previsto=(7 * 60, 11 * 60),
		horista=False,
	)
	assert (r.trabalhado, r.pausa_paga) == (277, 15)
	[inc] = [i for i in r.inconsistencias if i.tipo == EXCESSO]
	assert inc.mensagem.startswith("37 min além da jornada contratada (4h00)")


def test_4h52_sem_pausa_ja_avisa_o_excesso():
	r = dia("12:08", "17:00", previsto=(7 * 60, 11 * 60), horista=False)
	assert EXCESSO in tipos(r)  # 52 - 15 = 37 > 10
	assert INTERVALO_NAO_MARCADO not in tipos(r)  # só o instrutor horista


def test_pausa_incluida_maior_paga_so_o_limite_e_sem_parametro_nada_muda():
	r = dia("17:00", "19:00", "19:40", "21:00", incluidas=("19:00", "19:40"), horista=False)
	assert r.pausa_paga == 15
	sem = dia("17:45", "19:54", "20:09", "22:03", incluidas=("19:54", "20:09"), pausa=0, horista=False)
	assert sem.pausa_paga == 0
	assert EXCESSO not in tipos(sem)
