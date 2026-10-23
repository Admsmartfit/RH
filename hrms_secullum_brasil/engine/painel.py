"""Regras puras do Painel de Ponto (docs/PRD-frontend.md, FE-01 e decisões D-2, D-4 e D-5).

A tela /ponto só desenha o que o servidor manda: taxa de conformidade do mês, horas extras por faixa, segmentos
da linha do tempo do dia, sugestão de horário para a marcação ímpar e documentos mascarados.

Horários de entrada em minutos a partir das 00:00 do dia de trabalho (podem passar de 1440 quando a jornada
atravessa a meia-noite, como em engine/models.py). Os segmentos saem em minutos a partir da hora de virada do
perfil, entre 0 e 1440.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.jornada_prevista import MINUTOS_DIA

# Status da Apuracao Diaria (D-2)
OK = "Ok"
TRATADO = "Tratado"
INCONSISTENTE = "Inconsistente"
NAO_APURADO = "Nao Apurado"

# Tipos de segmento da linha do tempo
PREVISTO = "previsto"
TOLERANCIA = "tolerancia"
TRABALHADO = "trabalhado"
EXTRA = "extra"
ATRASO = "atraso"
FALTA = "falta"
INTERVALO = "intervalo"
NOTURNO = "noturno"

NOTURNO_INICIO = 22 * 60
NOTURNO_FIM = 5 * 60

Par = tuple[int, int]


# ------------------------------------------------------------------ D-2: conformidade


@dataclass(frozen=True)
class Conformidade:
	percentual: Decimal | None  # None quando não há dia apurado
	conformes: int
	apurados: int
	nao_apurados: int


def taxa_conformidade(contagem_por_status: dict[str, int]) -> Conformidade:
	"""Dias Ok ou Tratado ÷ dias apurados (Ok + Tratado + Inconsistente). "Não Apurado" fica de fora."""
	conformes = contagem_por_status.get(OK, 0) + contagem_por_status.get(TRATADO, 0)
	apurados = conformes + contagem_por_status.get(INCONSISTENTE, 0)
	percentual = (
		(Decimal(conformes) * 100 / apurados).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
		if apurados
		else None
	)
	return Conformidade(percentual, conformes, apurados, contagem_por_status.get(NAO_APURADO, 0))


# ------------------------------------------------------------------ horas extras por faixa


@dataclass(frozen=True)
class TotalFaixa:
	minutos: int
	colaboradores: int
	banco: int  # dos minutos, quantos foram para o banco de horas


def somar_he_por_faixa(linhas: Iterable[tuple[str, float, int, bool]]) -> dict[str, TotalFaixa]:
	"""Linhas (employee, percentual, minutos, vai_para_banco) → {"50": ..., "100": ...}.

	Mesmo corte das rubricas (valoracao.py): abaixo de 100% é a faixa de 50%; 100% ou mais, a de 100%.
	"""
	minutos = {"50": 0, "100": 0}
	banco = {"50": 0, "100": 0}
	pessoas: dict[str, set[str]] = {"50": set(), "100": set()}
	for employee, percentual, valor, vai_para_banco in linhas:
		if not valor:
			continue
		faixa = "100" if float(percentual) >= 100 else "50"
		minutos[faixa] += int(valor)
		if vai_para_banco:
			banco[faixa] += int(valor)
		pessoas[faixa].add(employee)
	return {f: TotalFaixa(minutos[f], len(pessoas[f]), banco[f]) for f in minutos}


# ------------------------------------------------------------------ linha do tempo do dia


@dataclass(frozen=True)
class Tolerancias:
	por_marcacao: int = 5
	noturno_inicio: int = NOTURNO_INICIO
	noturno_fim: int = NOTURNO_FIM


@dataclass(frozen=True)
class Segmento:
	inicio: int  # minutos a partir da virada (0 a 1440)
	fim: int
	tipo: str


def _intersecao(a: Sequence[Par], b: Sequence[Par]) -> list[Par]:
	saida = []
	for ai, af in a:
		for bi, bf in b:
			inicio, fim = max(ai, bi), min(af, bf)
			if fim > inicio:
				saida.append((inicio, fim))
	return sorted(saida)


def _diferenca(a: Sequence[Par], b: Sequence[Par]) -> list[Par]:
	"""Partes de `a` fora de `b`."""
	saida = []
	for ai, af in a:
		pedacos = [(ai, af)]
		for bi, bf in b:
			novos = []
			for pi, pf in pedacos:
				if bf <= pi or bi >= pf:
					novos.append((pi, pf))
					continue
				if bi > pi:
					novos.append((pi, bi))
				if bf < pf:
					novos.append((bf, pf))
			pedacos = novos
		saida += pedacos
	return sorted(saida)


def _janelas_noturnas(de: int, ate: int, tol: Tolerancias) -> list[Par]:
	janelas = []
	for dia in range(de // MINUTOS_DIA - 1, ate // MINUTOS_DIA + 1):
		inicio = dia * MINUTOS_DIA + tol.noturno_inicio
		fim = dia * MINUTOS_DIA + tol.noturno_fim
		if tol.noturno_fim <= tol.noturno_inicio:
			fim += MINUTOS_DIA
		janelas.append((inicio, fim))
	return janelas


def _na_linha(minuto: int, virada: int) -> int:
	"""Minuto do dia de trabalho → posição na faixa de 24 h que começa na virada."""
	posicao = minuto - virada
	while posicao < 0:
		posicao += MINUTOS_DIA
	return posicao


def posicao_na_linha(minuto: int, hora_virada: int = 0) -> int:
	"""Posição (0 a 1440) de uma marcação na faixa de 24 h da linha do tempo; a tela só desenha."""
	return min(MINUTOS_DIA, _na_linha(int(minuto), int(hora_virada) * 60))


def segmentos_do_dia(
	jornada_prevista: Sequence[Par],
	marcacoes: Sequence[int],
	hora_virada: int = 0,
	tolerancias: Tolerancias | None = None,
) -> list[Segmento]:
	"""Segmentos da linha do tempo de um dia.

	- previsto: cada período da jornada; tolerancia: ± tolerância por marcação em cada ponta do previsto;
	- trabalhado: o que foi trabalhado dentro do previsto (ou tudo, sem jornada prevista);
	- extra / atraso: trabalhado fora do previsto / previsto não trabalhado, quando passa da tolerância;
	- falta: o previsto inteiro, num dia sem nenhuma marcação; intervalo: entre dois pares trabalhados;
	- noturno: parte trabalhada no horário noturno (sobreposto aos outros).
	Marcações ímpares não formam pares: só aparecem o previsto e a tolerância.
	"""
	tol = tolerancias or Tolerancias()
	previsto = sorted((int(i), int(f)) for i, f in jornada_prevista)
	marcas = sorted(int(m) for m in marcacoes)
	pares = [(marcas[i], marcas[i + 1]) for i in range(0, len(marcas) - 1, 2)] if len(marcas) % 2 == 0 else []
	brutos: list[tuple[int, int, str]] = [(i, f, PREVISTO) for i, f in previsto]
	for inicio, fim in previsto:
		for ponta in (inicio, fim):
			brutos.append((ponta - tol.por_marcacao, ponta + tol.por_marcacao, TOLERANCIA))

	if not marcas and previsto:
		brutos += [(i, f, FALTA) for i, f in previsto]
	elif pares:
		if previsto:
			brutos += [(i, f, TRABALHADO) for i, f in _intersecao(pares, previsto)]
			for i, f in _diferenca(pares, previsto):
				brutos.append((i, f, EXTRA if f - i > tol.por_marcacao else TRABALHADO))
			for i, f in _diferenca(previsto, pares):
				if f - i > tol.por_marcacao:
					brutos.append((i, f, ATRASO))
		else:
			brutos += [(i, f, TRABALHADO) for i, f in pares]
		brutos += [(pares[n][1], pares[n + 1][0], INTERVALO) for n in range(len(pares) - 1)]
		noturnas = _janelas_noturnas(pares[0][0], pares[-1][1], tol)
		brutos += [(i, f, NOTURNO) for i, f in _intersecao(pares, noturnas)]

	virada = int(hora_virada) * 60
	segmentos = []
	for inicio, fim, tipo in brutos:
		pos_inicio = _na_linha(inicio, virada)
		pos_fim = pos_inicio + (fim - inicio)
		segmentos.append(Segmento(max(0, pos_inicio), min(MINUTOS_DIA, pos_fim), tipo))
	ordem = {
		t: n
		for n, t in enumerate((PREVISTO, TOLERANCIA, FALTA, ATRASO, INTERVALO, TRABALHADO, EXTRA, NOTURNO))
	}
	return sorted((s for s in segmentos if s.fim > s.inicio), key=lambda s: (ordem[s.tipo], s.inicio))


# ------------------------------------------------------------------ D-4: sugestão para a marcação ímpar


def sugerir_horario(jornada_prevista: Sequence[Par], marcacoes: Sequence[int]) -> int | None:
	"""Horário previsto (minutos do dia de trabalho) mais provável para a marcação que falta.

	Cada marcação é ligada à ponta prevista mais próxima ainda livre; a sugestão é a outra ponta do período que
	ficou com uma só marcação. Sem jornada prevista ou com número par de marcações: None (só pré-preenche).
	"""
	marcas = sorted(int(m) for m in marcacoes)
	if not jornada_prevista or len(marcas) % 2 == 0:
		return None
	pontas = [p for i, f in sorted(jornada_prevista) for p in (int(i), int(f))]
	usadas: set[int] = set()
	for marca in marcas:
		livres = [n for n in range(len(pontas)) if n not in usadas]
		if not livres:
			break
		usadas.add(min(livres, key=lambda n: (abs(pontas[n] - marca), n)))
	for n in range(0, len(pontas), 2):
		entrada, saida = n in usadas, n + 1 in usadas
		if entrada != saida:
			return pontas[n + 1] if entrada else pontas[n]
	livres = [n for n in range(len(pontas)) if n not in usadas]
	return pontas[livres[0]] if livres else None


# ------------------------------------------------------------------ D-5: documentos mascarados


def mascarar_documento(numero: str | None, tipo: str = "cpf") -> str:
	"""Só os 4 últimos dígitos à mostra: CPF ***.***.*89-01; PIS ***.****9.01-2; outros: * e os 4 últimos."""
	digitos = "".join(c for c in str(numero or "") if c.isdigit())
	if not digitos:
		return ""
	if len(digitos) != 11:
		return "*" * max(0, len(digitos) - 4) + digitos[-4:]
	m = "*" * 7 + digitos[7:]
	if tipo == "pis":
		return f"{m[:3]}.{m[3:8]}.{m[8:10]}-{m[10]}"
	return f"{m[:3]}.{m[3:6]}.{m[6:9]}-{m[9:]}"
