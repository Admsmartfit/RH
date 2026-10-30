"""Cumprimento da escala: quem faz o que foi escalado (pedido do RH, 30/10/2026). Python puro.

Compara, dia a dia, a escala (Escala Mensal ou o perfil) com o que a pessoa fez no ponto — vale para o horista, que
recebe só as horas trabalhadas e por isso não tem "atraso" na apuração, mas precisa cumprir a escala:

- **falta**: escalado e sem nenhuma batida;
- **atraso** / **saída antecipada**: a primeira entrada depois do início escalado (ou a última saída antes do fim),
  além da tolerância;
- **minutos não cumpridos**: minutos escalados sem a pessoa presente (falta inteira, atrasos, saídas e pausas longas);
- **horário diferente**: trabalhou, mas em menos da metade do horário escalado (ex.: escalado de manhã e veio à
  noite) — conta como dia não cumprido, sem virar "atraso" de horas;
- **fora da escala**: dia trabalhado sem estar escalado (informativo).

O **cumprimento** é a parte dos minutos escalados em que a pessoa estava presente; o ranking vai do menor cumprimento
(mais problema) ao maior.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

TOLERANCIA_PADRAO = 10  # minutos por evento (CLT art. 58, § 1º: até 10 min no dia não contam)
METADE = 0.5  # presente em menos da metade do escalado = horário diferente


@dataclass(frozen=True)
class DiaComparado:
	planejado: Sequence[tuple[int, int]]  # períodos escalados (minutos do dia); vazio = folga
	realizado: Sequence[tuple[int, int]]  # períodos das batidas


@dataclass
class Cumprimento:
	dias_escalados: int = 0
	dias_cumpridos: int = 0  # sem falta, atraso nem saída antecipada
	faltas: int = 0
	atrasos: int = 0
	minutos_atraso: int = 0
	saidas_antecipadas: int = 0
	minutos_saida: int = 0
	minutos_escalados: int = 0
	minutos_nao_cumpridos: int = 0
	dias_horario_diferente: int = 0
	dias_fora_da_escala: int = 0
	minutos_fora_da_escala: int = 0
	datas_com_problema: list = field(default_factory=list)

	@property
	def cumprimento_pct(self) -> float:
		if not self.minutos_escalados:
			return 100.0
		return round(100 * (self.minutos_escalados - self.minutos_nao_cumpridos) / self.minutos_escalados, 1)


def _intersecao(a: Iterable[tuple[int, int]], b: Iterable[tuple[int, int]]) -> int:
	b = list(b)
	return sum(max(0, min(f1, f2) - max(i1, i2)) for i1, f1 in a for i2, f2 in b)


def comparar_dia(dia: DiaComparado, tolerancia: int = TOLERANCIA_PADRAO) -> dict:
	plan = sorted(dia.planejado)
	real = sorted(dia.realizado)
	escalado = sum(f - i for i, f in plan)
	if not plan:
		fora = sum(f - i for i, f in real)
		return {
			"escalado": 0,
			"nao_cumprido": 0,
			"falta": False,
			"atraso": 0,
			"saida": 0,
			"fora": fora,
			"diferente": False,
		}
	if not real:
		return {
			"escalado": escalado,
			"nao_cumprido": escalado,
			"falta": True,
			"atraso": 0,
			"saida": 0,
			"fora": 0,
			"diferente": False,
		}
	presente = _intersecao(plan, real)
	diferente = presente < escalado * METADE
	atraso = 0 if diferente else real[0][0] - plan[0][0]
	saida = 0 if diferente else plan[-1][1] - real[-1][1]
	return {
		"escalado": escalado,
		"nao_cumprido": max(0, escalado - presente),
		"falta": False,
		"atraso": atraso if atraso > tolerancia else 0,
		"saida": saida if saida > tolerancia else 0,
		"fora": max(0, sum(f - i for i, f in real) - presente),
		"diferente": diferente,
	}


def cumprimento(
	dias: Iterable[tuple[object, DiaComparado]], tolerancia: int = TOLERANCIA_PADRAO
) -> Cumprimento:
	"""`dias`: (data, DiaComparado) de uma pessoa no período."""
	c = Cumprimento()
	for data, dia in dias:
		r = comparar_dia(dia, tolerancia)
		if r["escalado"]:
			c.dias_escalados += 1
			c.minutos_escalados += r["escalado"]
			c.minutos_nao_cumpridos += r["nao_cumprido"]
			c.faltas += r["falta"]
			c.atrasos += bool(r["atraso"])
			c.minutos_atraso += r["atraso"]
			c.saidas_antecipadas += bool(r["saida"])
			c.minutos_saida += r["saida"]
			c.dias_horario_diferente += r["diferente"]
			if r["falta"] or r["atraso"] or r["saida"] or r["diferente"]:
				c.datas_com_problema.append(data)
			else:
				c.dias_cumpridos += 1
		elif r["fora"]:
			c.dias_fora_da_escala += 1
			c.minutos_fora_da_escala += r["fora"]
	return c


def ranking(por_pessoa: dict[str, Cumprimento]) -> list[tuple[str, Cumprimento]]:
	"""Do menor cumprimento (mais problema) ao maior; empate: mais faltas, depois mais minutos não cumpridos."""
	return sorted(
		por_pessoa.items(),
		key=lambda x: (x[1].cumprimento_pct, -x[1].faltas, -x[1].minutos_nao_cumpridos, x[0]),
	)


# ------------------------------------------------------------------ padrão habitual (horista, RH 30/10/2026)

FREQUENCIA_HABITUAL = 0.5  # trabalha em pelo menos metade dos dias daquele dia da semana


def _mediana(valores: list[int]) -> int:
	ordenados = sorted(valores)
	meio = len(ordenados) // 2
	return ordenados[meio] if len(ordenados) % 2 else (ordenados[meio - 1] + ordenados[meio]) // 2


def padrao_habitual(
	historico: Iterable[tuple[object, Sequence[tuple[int, int]]]],
) -> dict[int, tuple[int, int]]:
	"""O horário de costume por dia da semana (0 = segunda): a mediana da entrada e da saída nos dias em que trabalhou,
	se trabalhou em pelo menos metade das vezes daquele dia. O horista não tem escala fixa no Secullum; o costume é a
	referência para ver quem falta no dia de sempre ou chega bem depois do horário de sempre. Os dias antes da
	primeira batida não contam (sem dado não é falta: o ponto pode ter começado depois)."""
	historico = sorted(historico, key=lambda x: x[0])
	primeiro = next((n for n, (_d, periodos) in enumerate(historico) if periodos), len(historico))
	por_dia: dict[int, list] = {}
	for data, periodos in historico[primeiro:]:
		por_dia.setdefault(data.weekday(), []).append(sorted(periodos))
	padrao = {}
	for dia, ocorrencias in por_dia.items():
		trabalhados = [p for p in ocorrencias if p]
		if trabalhados and len(trabalhados) >= FREQUENCIA_HABITUAL * len(ocorrencias):
			padrao[dia] = (
				_mediana([p[0][0] for p in trabalhados]),
				_mediana([p[-1][1] for p in trabalhados]),
			)
	return padrao
