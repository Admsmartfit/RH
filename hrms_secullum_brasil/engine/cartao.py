"""Efeito do cartão do Secullum na jornada do dia (folga, neutro e justificativas lançadas pelo RH no Secullum).

- Folga lançada → o dia é folga (sem jornada prevista, sem falta).
- Neutro → dia neutro (rodízio: sem falta, horas normais se trabalhar).
- Justificativa que abona em todos os períodos previstos → dia abonado (as horas previstas contam como normais).
- Justificativa que abona só em parte dos períodos (grupo n = n-ésimo período previsto) → esses períodos saem da
  jornada prevista (nem falta, nem atraso neles).
- Justificativa com efeito "Falta" não muda nada (o dia segue com falta).
"""

from dataclasses import replace

from hrms_secullum_brasil.engine.models import JornadaPrevista


def jornada_com_cartao(
	jornada: JornadaPrevista,
	*,
	folga: bool = False,
	neutro: bool = False,
	grupos_abonados: frozenset[int] | set[int] = frozenset(),
) -> tuple[JornadaPrevista, bool]:
	"""(jornada do dia, dia inteiro abonado?)."""
	if folga:
		return JornadaPrevista((), jornada.permite_intervalo_estendido), False
	if neutro and not jornada.folga:
		return JornadaPrevista((), jornada.permite_intervalo_estendido, neutro=True), False
	if not grupos_abonados or not jornada.periodos:
		return jornada, False
	restantes = tuple(p for i, p in enumerate(jornada.periodos, start=1) if i not in grupos_abonados)
	if not restantes:
		return jornada, True
	return replace(jornada, periodos=restantes), False
