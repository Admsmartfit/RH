"""Horas da academia sem ninguém na escala do dia (tela Escalas, pedido do RH de 11/11/2026). Python puro.

A tela mostra só um sinal por dia na linha "Cobertura" do rodapé da grade; o detalhe (quais horas e de quem é a
pausa) abre num balão. Regras:

- o horário de funcionamento é o mesmo do planejador (`planejador.montagem.PADROES["funcionamento"]`): de segunda
  a sexta 05h-23h, sábado 08h-17h, domingo 08h-14h; feriado segue o sábado;
- conta quem está na grade filtrada (o cargo escolhido na tela); minutos sem ninguém viram faixas "sem ninguém";
- minuto sem ninguém só porque a pessoa está na pausa (entre dois períodos dela) não é furo: vira o aviso leve
  "só pausa", como no planejador (DI-8).

Horários em minutos do dia.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from hrms_secullum_brasil.engine.planejador.montagem import PADROES
from hrms_secullum_brasil.engine.turno_padrao import DOMINGO, FERIADO, SABADO

SEM_NINGUEM, SO_PAUSA, OK = "sem_ninguem", "so_pausa", "ok"


@dataclass(frozen=True)
class Faixa:
	inicio: int
	fim: int
	pausa_de: tuple[str, ...] = ()  # só nas faixas "só pausa": de quem é a pausa

	@property
	def minutos(self) -> int:
		return self.fim - self.inicio


@dataclass(frozen=True)
class CoberturaDia:
	abre: int
	fecha: int
	sem_ninguem: tuple[Faixa, ...] = ()
	so_pausa: tuple[Faixa, ...] = ()
	pessoas: int = 0
	situacao: str = OK

	@property
	def minutos_sem_ninguem(self) -> int:
		return sum(f.minutos for f in self.sem_ninguem)


def funcionamento(tipo_dia: str, weekday: int, tabela: dict | None = None) -> tuple[int, int]:
	"""(abre, fecha) do dia. Feriado segue o sábado; `tabela` por dia da semana ("0" = segunda)."""
	tabela = tabela or PADROES["funcionamento"]
	if tipo_dia in (FERIADO, SABADO):
		chave = "5"
	elif tipo_dia == DOMINGO:
		chave = "6"
	else:
		chave = str(weekday)
	ini, fim = tabela.get(chave) or tabela.get("0") or (300, 1380)
	return int(ini), int(fim)


def _faixas(minutos: Iterable[int]) -> list[tuple[int, int]]:
	saida: list[list[int]] = []
	for m in sorted(minutos):
		if saida and saida[-1][1] == m:
			saida[-1][1] = m + 1
		else:
			saida.append([m, m + 1])
	return [(a, b) for a, b in saida]


def cobertura_do_dia(
	pessoas: Iterable[tuple[str, Iterable[tuple[int, int]]]], abre: int, fecha: int
) -> CoberturaDia:
	"""`pessoas`: (nome, períodos de trabalho do dia). Períodos que passam da meia-noite valem até 24h."""
	lista = [
		(nome, sorted((int(a), int(b) if b > a else 1440) for a, b in periodos)) for nome, periodos in pessoas
	]
	lista = [(nome, p) for nome, p in lista if p]
	trabalho: set[int] = set()
	pausas: dict[int, list[str]] = {}
	for nome, periodos in lista:
		for a, b in periodos:
			trabalho.update(range(max(a, abre), min(b, fecha)))
		for (_, fim1), (ini2, _) in pairwise(periodos):
			for m in range(max(fim1, abre), min(ini2, fecha)):
				pausas.setdefault(m, []).append(nome)
	vazios = [m for m in range(abre, fecha) if m not in trabalho]
	sem, pausa = [], []
	for a, b in _faixas(m for m in vazios if m not in pausas):
		sem.append(Faixa(a, b))
	for a, b in _faixas(m for m in vazios if m in pausas):
		nomes = sorted({n for m in range(a, b) for n in pausas[m]})
		pausa.append(Faixa(a, b, tuple(nomes)))
	situacao = SEM_NINGUEM if sem else SO_PAUSA if pausa else OK
	return CoberturaDia(abre, fecha, tuple(sem), tuple(pausa), len(lista), situacao)


def _hhmm(minutos: int) -> str:
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _duracao(minutos: int) -> str:
	h, m = divmod(minutos, 60)
	if not h:
		return f"{m} min"
	return f"{h}h{m:02d}" if m else f"{h}h"


def resumo(c: CoberturaDia) -> str:
	"""O texto curto do sinal do dia (rodapé da grade)."""
	if c.situacao == SEM_NINGUEM:
		return f"{_duracao(c.minutos_sem_ninguem)} sem ninguém"
	if c.situacao == SO_PAUSA:
		return "só pausa"
	return "coberto"


def como_dict(c: CoberturaDia) -> dict:
	return {
		"situacao": c.situacao,
		"resumo": resumo(c),
		"funcionamento": f"{_hhmm(c.abre)}-{_hhmm(c.fecha)}",
		"pessoas": c.pessoas,
		"minutos_sem_ninguem": c.minutos_sem_ninguem,
		"sem_ninguem": [
			{"de": _hhmm(f.inicio), "ate": _hhmm(f.fim), "duracao": _duracao(f.minutos)}
			for f in c.sem_ninguem
		],
		"so_pausa": [
			{
				"de": _hhmm(f.inicio),
				"ate": _hhmm(f.fim),
				"duracao": _duracao(f.minutos),
				"pausa_de": list(f.pausa_de),
			}
			for f in c.so_pausa
		],
	}
