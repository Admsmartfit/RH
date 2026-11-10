"""Intervalos intrajornada (Art. 71 CLT) e interjornada (Art. 66 CLT) — PRD, 5.5 e 5.6."""

from collections.abc import Iterable
from datetime import datetime
from itertools import pairwise

from hrms_secullum_brasil.engine.models import ALTA, MEDIA, Inconsistencia, RegraApuracao

Par = tuple[int, int]


def intervalo_exigido(trabalhado: int, regra: RegraApuracao) -> int:
	"""Até 4h: nenhum; de 4h a 6h: 15 min; acima de 6h: 1h (ou o reduzido permitido pela CCT). Os limites têm a
	tolerância do art. 58, § 1º (`tolerancia_jornada_intervalo`, 10 min): 4h06 sem pausa não exige os 15 min."""
	folga = regra.tolerancia_jornada_intervalo
	if trabalhado <= regra.jornada_sem_intervalo_ate + folga:
		return 0
	if trabalhado <= regra.jornada_intervalo_curto_ate + folga:
		return regra.intervalo_curto
	return regra.intervalo_reduzido if regra.permite_reducao_intrajornada else regra.intervalo_minimo


def intrajornada(
	pares: list[Par], regra: RegraApuracao, *, permite_estendido: bool
) -> tuple[int, list[Inconsistencia]]:
	"""(minutos suprimidos, inconsistências). Considera o maior intervalo do dia.

	O tempo suprimido é indenizado com acréscimo (Art. 71, §4º) — o percentual é aplicado na valoração. Redução de até
	`tolerancia_intervalo` min no total (variação de marcação) não é supressão: nem pendência, nem indenização.
	"""
	trabalhado = sum(saida - entrada for entrada, saida in pares)
	maior = max((b[0] - a[1] for a, b in pairwise(pares)), default=0)
	avisos = []
	suprimida = max(intervalo_exigido(trabalhado, regra) - maior, 0)
	if suprimida <= regra.tolerancia_intervalo:
		suprimida = 0
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


def posicao_do_intervalo(pares: list[Par], regra: RegraApuracao) -> Inconsistencia | None:
	"""Intervalo colado ao fim (ou ao começo) do expediente: o maior intervalo do dia precisa de pelo menos
	`trabalho_minimo_apos_intervalo` de trabalho depois da volta e antes da saída. Só quando o dia exige intervalo;
	jornada em dois turnos (intervalo acima do máximo) fica de fora."""
	minimo = regra.trabalho_minimo_apos_intervalo
	trabalhado = sum(saida - entrada for entrada, saida in pares)
	if not minimo or len(pares) < 2 or not intervalo_exigido(trabalhado, regra):
		return None
	lacunas = [b[0] - a[1] for a, b in pairwise(pares)]
	maior = max(lacunas)
	if maior > regra.intervalo_maximo:
		return None
	i = lacunas.index(maior)
	antes = sum(s - e for e, s in pares[: i + 1])
	depois = sum(s - e for e, s in pares[i + 1 :])
	if depois < minimo:
		onde, trabalho = "no fim do expediente: depois da volta", depois
	elif antes < minimo:
		onde, trabalho = "no começo do expediente: antes da saída", antes
	else:
		return None
	return Inconsistencia(
		"intervalo_fora_de_hora",
		MEDIA,
		f"Intervalo {onde}, só {trabalho} min de trabalho (mínimo {minimo}). O descanso precisa ficar no meio da "
		"jornada, mesmo a pedido do empregado.",
	)


def interjornada_suprimida(
	primeira_entrada: datetime, marcacoes_anteriores: Iterable[datetime], minimo: int
) -> int:
	"""Minutos que faltaram para o descanso mínimo entre jornadas (pagos como extra, OJ 355 SDI-1)."""
	anteriores = [m for m in marcacoes_anteriores if m < primeira_entrada]
	if not anteriores:
		return 0
	descanso = int((primeira_entrada - max(anteriores)).total_seconds() // 60)
	return max(minimo - descanso, 0)
