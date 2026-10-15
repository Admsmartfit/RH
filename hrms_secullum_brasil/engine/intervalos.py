"""Intervalos intrajornada (Art. 71 CLT) e interjornada (Art. 66 CLT) — PRD, 5.5 e 5.6."""

from collections.abc import Iterable
from datetime import datetime
from itertools import pairwise

from hrms_secullum_brasil.engine.models import ALTA, MEDIA, Inconsistencia, RegraApuracao

Par = tuple[int, int]


def intervalo_exigido(trabalhado: int, regra: RegraApuracao) -> int:
	"""Até 4h: nenhum; de 4h a 6h: 15 min; acima de 6h: 1h (ou o reduzido permitido pela CCT)."""
	if trabalhado <= regra.jornada_sem_intervalo_ate:
		return 0
	if trabalhado <= regra.jornada_intervalo_curto_ate:
		return regra.intervalo_curto
	return regra.intervalo_reduzido if regra.permite_reducao_intrajornada else regra.intervalo_minimo


def intrajornada(
	pares: list[Par], regra: RegraApuracao, *, permite_estendido: bool
) -> tuple[int, list[Inconsistencia]]:
	"""(minutos suprimidos, inconsistências). Considera o maior intervalo do dia.

	O tempo suprimido é indenizado com acréscimo (Art. 71, §4º) — o percentual é aplicado na valoração.
	"""
	trabalhado = sum(saida - entrada for entrada, saida in pares)
	maior = max((b[0] - a[1] for a, b in pairwise(pares)), default=0)
	avisos = []
	suprimida = max(intervalo_exigido(trabalhado, regra) - maior, 0)
	if suprimida:
		avisos.append(
			Inconsistencia(
				"intrajornada",
				MEDIA,
				f"Intervalo de {maior} min; exigido {intervalo_exigido(trabalhado, regra)} min.",
			)
		)
	if maior > regra.intervalo_maximo and not permite_estendido:
		avisos.append(
			Inconsistencia(
				"intervalo_superior_2h",
				ALTA,
				f"Intervalo de {maior} min acima de {regra.intervalo_maximo} min sem acordo escrito ou CCT.",
			)
		)
	return suprimida, avisos


def interjornada_suprimida(
	primeira_entrada: datetime, marcacoes_anteriores: Iterable[datetime], minimo: int
) -> int:
	"""Minutos que faltaram para o descanso mínimo entre jornadas (pagos como extra, OJ 355 SDI-1)."""
	anteriores = [m for m in marcacoes_anteriores if m < primeira_entrada]
	if not anteriores:
		return 0
	descanso = int((primeira_entrada - max(anteriores)).total_seconds() // 60)
	return max(minimo - descanso, 0)
