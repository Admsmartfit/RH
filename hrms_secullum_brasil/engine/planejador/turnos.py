"""Turnos candidatos de cada pessoa (PE-07): os de hoje, os Turnos Padrão e turnos gerados a cada hora das 06h às
23h com 4h, 6h ou 8h (com a pausa legal: 15 min acima de 4h, 1h acima de 6h — CLT art. 71)."""

from collections.abc import Iterable

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.planejador.modelos import ABRE, FECHA, Turno

DURACOES = (240, 360, 480)  # minutos de trabalho


def pausa_legal(minutos: int) -> int:
	if minutos > d.JORNADA_INTERVALO_CURTO_ATE_MIN:
		return d.INTERVALO_MINIMO_MIN
	if minutos > d.JORNADA_SEM_INTERVALO_ATE_MIN:
		return d.INTERVALO_CURTO_MIN
	return 0


def turno_de(inicio: int, minutos: int) -> Turno:
	pausa = pausa_legal(minutos)
	return Turno(inicio, inicio + minutos + pausa, pausa)


def candidatos(
	diaria: int,
	atuais: Iterable[Turno | None] = (),
	padroes: Iterable[Turno] = (),
	passo: int = 60,
	extras: Iterable[int] = (),
) -> tuple[Turno, ...]:
	"""Turnos de até `diaria` minutos de trabalho dentro do horário da academia. `extras`: durações a mais (ex.: a
	jornada compensada de 8h24)."""
	saida = {
		t for t in (*atuais, *padroes) if t and t.minutos <= diaria and ABRE <= t.inicio and t.fim <= FECHA
	}
	for minutos in sorted({*DURACOES, *extras}):
		if minutos > diaria:
			continue
		inicio = ABRE
		while True:
			turno = turno_de(inicio, minutos)
			if turno.fim > FECHA:
				break
			saida.add(turno)
			inicio += passo
	return tuple(sorted(saida))
