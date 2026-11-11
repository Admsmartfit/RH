"""Turno padrão do cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-02 e DE-1). Python puro.

Um turno é entrada, saída e uma pausa opcional (minutos e, se informado, o horário em que começa; vazio = no meio do
turno). As horas trabalhadas não incluem a pausa: T1 08:00-14:15 com 15 min de pausa = 6h de trabalho. Saída menor
que a entrada = termina no dia seguinte.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from itertools import pairwise

from hrms_secullum_brasil.engine.jornada_prevista import Periodo


@dataclass(frozen=True)
class TurnoPadrao:
	nome: str
	entrada: int  # minutos do dia
	saida: int
	pausa: int = 0
	pausa_inicio: int | None = None


def periodos_do_turno(turno: TurnoPadrao) -> tuple[tuple[Periodo, ...], list[str]]:
	"""Períodos do turno na linha do tempo do dia e os erros de cadastro."""
	if turno.saida == turno.entrada:
		return (), [f"{turno.nome}: a saída precisa ser diferente da entrada."]
	fim = turno.saida if turno.saida > turno.entrada else turno.saida + 1440
	duracao = fim - turno.entrada
	if turno.pausa < 0:
		return (), [f"{turno.nome}: a pausa não pode ser negativa."]
	if not turno.pausa:
		return (Periodo(turno.entrada, fim),), []
	if turno.pausa_inicio is None:
		inicio_pausa = turno.entrada + (duracao - turno.pausa) // 2
	else:
		inicio_pausa = (
			turno.pausa_inicio if turno.pausa_inicio >= turno.entrada else turno.pausa_inicio + 1440
		)
	fim_pausa = inicio_pausa + turno.pausa
	if not (turno.entrada < inicio_pausa and fim_pausa < fim):
		return (), [f"{turno.nome}: a pausa precisa ficar dentro do turno, com trabalho antes e depois."]
	return (Periodo(turno.entrada, inicio_pausa), Periodo(fim_pausa, fim)), []


# ------------------------------------------------------------------ turnos sugeridos pelo histórico (pedido de 03/11/2026)

DIA_UTIL, SABADO, DOMINGO, FERIADO = "Dia útil", "Sábado", "Domingo", "Feriado"
TIPOS_DIA = (DIA_UTIL, SABADO, DOMINGO, FERIADO)
_SIGLAS = {DIA_UTIL: "Útil", SABADO: "Sáb", DOMINGO: "Dom", FERIADO: "Fer"}
_DIAS_CURTOS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def tipo_do_dia(dia: date, feriados: Iterable[date] = ()) -> str:
	"""Feriado vence o dia da semana, menos o domingo: feriado que cai no domingo é domingo (turnos e horário de
	funcionamento do domingo; RH, 11/11/2026)."""
	if dia.weekday() == 6:
		return DOMINGO
	if dia in set(feriados):
		return FERIADO
	return {5: SABADO}.get(dia.weekday(), DIA_UTIL)


def serve_no_dia(tipo_turno: str | None, dia: date, feriados: Iterable[date] = ()) -> bool:
	"""Turno sem tipo vale em qualquer dia; com tipo, só no tipo do dia."""
	return not tipo_turno or tipo_turno == tipo_do_dia(dia, feriados)


@dataclass(frozen=True)
class TurnoSugerido:
	tipo: str
	turno: TurnoPadrao
	ocorrencias: int  # dias em que alguém fez o turno (já arredondado)
	pessoas: int
	dias_semana: str  # "seg, qua, sex"


def _arredondar(minutos: int, passo: int) -> int:
	return int((minutos + passo / 2) // passo * passo)


def turno_do_dia(periodos: Sequence[Periodo], passo: int = 30, passo_pausa: int = 15) -> TurnoPadrao | None:
	"""Batidas do dia em forma de turno: entrada e saída no `passo` mais próximo, uma pausa (a maior lacuna) no
	`passo_pausa`. Dia com mais de uma lacuna usa só a maior; sem período válido, None."""
	pares = sorted((p for p in periodos if p.fim > p.inicio), key=lambda p: p.inicio)
	if not pares:
		return None
	entrada, saida = _arredondar(pares[0].inicio, passo), _arredondar(pares[-1].fim, passo)
	if saida <= entrada:
		return None
	pausa, pausa_inicio = 0, None
	if len(pares) > 1:
		lacuna, anterior = max((b.inicio - a.fim, a) for a, b in pairwise(pares))
		pausa = _arredondar(lacuna, passo_pausa)
		pausa_inicio = _arredondar(anterior.fim, passo_pausa) if pausa else None
		if pausa and not (entrada < pausa_inicio and pausa_inicio + pausa < saida):
			pausa, pausa_inicio = 0, None
	return TurnoPadrao(
		"", entrada % 1440, saida % 1440, pausa, None if pausa_inicio is None else pausa_inicio % 1440
	)


def _hhmm(minutos: int) -> str:
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def nome_do_turno(tipo: str, turno: TurnoPadrao) -> str:
	"""Curto, porque a tela mostra o horário ao lado: "Sáb manhã", "Útil tarde", "Fer noite"."""
	parte = "manhã" if turno.entrada < 12 * 60 else "tarde" if turno.entrada < 18 * 60 else "noite"
	return f"{_SIGLAS.get(tipo, tipo)} {parte}"


def sugerir_turnos(
	registros: Iterable[tuple[str, date, Sequence[Periodo]]],
	feriados: Iterable[date] = (),
	minimo: int = 2,
	maximo_por_tipo: int = 4,
	passo: int = 30,
) -> list[TurnoSugerido]:
	"""Turnos mais frequentes de cada tipo de dia (dia útil, sábado, domingo, feriado) nas batidas reais.

	`registros`: (colaborador, dia, períodos trabalhados). Turnos com a mesma entrada, saída e pausa são um só (a
	pausa começa no horário mais comum). Um turno entra se apareceu em pelo menos `minimo` dias; por tipo, os
	`maximo_por_tipo` mais frequentes (empate: o que começa mais cedo), em ordem de entrada."""
	feriados = frozenset(feriados)
	contagem: dict[tuple[str, int, int, int], list[tuple[str, date, int | None]]] = defaultdict(list)
	for pessoa, dia, periodos in registros:
		turno = turno_do_dia(periodos, passo)
		if turno:
			chave = (tipo_do_dia(dia, feriados), turno.entrada, turno.saida, turno.pausa)
			contagem[chave].append((pessoa, dia, turno.pausa_inicio))
	saida = []
	for tipo in TIPOS_DIA:
		candidatos = []
		for (tp, entrada, saida_turno, pausa), ocorr in contagem.items():
			if tp != tipo or len(ocorr) < minimo:
				continue
			inicios = Counter(i for _p, _d, i in ocorr)
			pausa_inicio = min(inicios, key=lambda i: (-inicios[i], i if i is not None else -1))
			candidatos.append((TurnoPadrao("", entrada, saida_turno, pausa, pausa_inicio), ocorr))
		candidatos.sort(key=lambda x: (-len(x[1]), x[0].entrada, x[0].saida))
		usados: dict[str, int] = defaultdict(int)
		for turno, ocorr in sorted(candidatos[:maximo_por_tipo], key=lambda x: (x[0].entrada, x[0].saida)):
			semana = sorted({d.weekday() for _p, d, _i in ocorr})
			nome = nome_do_turno(tipo, turno)
			usados[nome] += 1
			saida.append(
				TurnoSugerido(
					tipo,
					replace(turno, nome=nome if usados[nome] == 1 else f"{nome} {usados[nome]}"),
					len(ocorr),
					len({p for p, _d, _i in ocorr}),
					", ".join(_DIAS_CURTOS[i] for i in semana),
				)
			)
	return saida


def periodos_das_marcacoes(texto: str | None, dia: date) -> tuple[Periodo, ...]:
	"""Pares de batidas do texto da Apuração Diária ("02/11 07:37, 02/11 11:12, ...") em minutos do `dia` (batida de
	outra data = dia seguinte, +1440). Batida ímpar sobrando fica de fora."""
	minutos = []
	for parte in str(texto or "").split(","):
		try:
			data, hora = parte.split()
			dd, mm = (int(x) for x in data.split("/"))
			hh, mi = (int(x) for x in hora.split(":"))
		except ValueError:
			continue
		minutos.append(hh * 60 + mi + (0 if (dd, mm) == (dia.day, dia.month) else 1440))
	minutos.sort()
	return tuple(Periodo(a, b) for a, b in zip(minutos[::2], minutos[1::2], strict=False) if b > a)
