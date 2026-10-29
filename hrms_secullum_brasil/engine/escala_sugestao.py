"""Copiar, modelos e distribuição justa da escala (docs/PRD-cockpit-escalas.md, CE-13). Python puro.

- Copiar: a semana anterior (mesmo dia da semana, 7 dias antes) ou o mês anterior (mesmo dia da semana na mesma
  semana do mês: 4 ou 5 semanas antes). Só fim de semana/feriado ou o mês completo.
- Modelo: colaborador x dia da semana x turno; aplicado num período, gera os dias.
- Distribuição justa: para cada turno a cobrir (em ordem de data), o colaborador sem nenhuma quebra com a menor carga
  (fins de semana/feriados nos 3 meses + os já distribuídos); o resultado é só sugestão (vira rascunho se aceito).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta

from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import NEUTRO, TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.jornada_prevista import Periodo


def flexivel(dia: date, feriados: Iterable[date] = ()) -> bool:
	return dia.weekday() >= 5 or dia in set(feriados)


def origem_da_copia(alvo: date, modo: str) -> date:
	"""Dia de onde copiar: "semana" = 7 dias antes; "mes" = mesmo dia da semana no mês anterior (4 ou 5 semanas)."""
	if modo == "semana":
		return alvo - timedelta(days=7)
	primeiro = alvo.replace(day=1)
	anterior = (primeiro - timedelta(days=1)).replace(day=1)
	quatro = alvo - timedelta(weeks=4)
	return quatro if quatro >= anterior and quatro < primeiro else alvo - timedelta(weeks=5)


def copiar(
	dias_origem: Mapping[date, DiaEscala],
	alvos: Iterable[date],
	modo: str,
	*,
	so_fds: bool = True,
	feriados: Iterable[date] = (),
) -> list[DiaEscala]:
	"""Dias do período alvo copiados da origem (só os que têm origem conhecida)."""
	feriados = set(feriados)
	resultado = []
	for alvo in alvos:
		if so_fds and not flexivel(alvo, feriados):
			continue
		fonte = dias_origem.get(origem_da_copia(alvo, modo))
		if fonte is None:
			continue
		resultado.append(replace(fonte, data=alvo) if fonte.trabalho else DiaEscala(alvo, NEUTRO))
	return resultado


@dataclass(frozen=True)
class LinhaModelo:
	employee: str
	dia_semana: int  # 0 = segunda
	periodos: tuple[Periodo, ...]


def modelo_do_periodo(
	dias_por_pessoa: Mapping[str, Iterable[DiaEscala]], *, so_fds: bool = True, feriados=()
) -> list[LinhaModelo]:
	"""Modelo a partir de um período: para cada pessoa e dia da semana, o turno mais frequente (empate: o primeiro)."""
	feriados = set(feriados)
	linhas = []
	for employee, dias in dias_por_pessoa.items():
		por_dia: dict[int, list[tuple[Periodo, ...]]] = {}
		for dia in dias:
			if not dia.trabalho or (so_fds and not flexivel(dia.data, feriados)):
				continue
			por_dia.setdefault(dia.data.weekday(), []).append(dia.periodos)
		for dia_semana, turnos in sorted(por_dia.items()):
			escolhido = max(turnos, key=turnos.count)
			linhas.append(LinhaModelo(employee, dia_semana, escolhido))
	return linhas


def aplicar_modelo(
	linhas: Iterable[LinhaModelo], alvos: Iterable[date], *, so_fds: bool = True, feriados=()
) -> dict[str, list[DiaEscala]]:
	feriados = set(feriados)
	por_pessoa: dict[str, list[DiaEscala]] = {}
	linhas = list(linhas)
	for alvo in alvos:
		if so_fds and not flexivel(alvo, feriados):
			continue
		for linha in linhas:
			if linha.dia_semana == alvo.weekday():
				por_pessoa.setdefault(linha.employee, []).append(DiaEscala(alvo, TRABALHO, linha.periodos))
	return por_pessoa


@dataclass(frozen=True)
class Candidato:
	colega: ev.Colega
	carga: int  # turnos de fim de semana/feriado no mês + nos 3 meses anteriores


@dataclass(frozen=True)
class Sugestao:
	data: date
	periodos: tuple[Periodo, ...]
	atual: str | None  # quem está hoje
	sugerido: str | None  # None = ninguém pode sem quebra


def distribuir(
	turnos: Sequence[tuple[date, tuple[Periodo, ...], str | None]], candidatos: Sequence[Candidato]
) -> list[Sugestao]:
	"""Turnos (data, períodos, quem está hoje) → quem cobre cada um sem quebra, com a menor carga acumulada.

	Cada pessoa recebe primeiro a retirada de todos os turnos a distribuir (o plano começa do zero) e depois cada
	turno atribuído entra no plano dela, para as quebras de sequência (7º dia, domingos, interjornada) valerem."""
	datas = {d for d, _p, _a in turnos}
	carga = {c.colega.employee: c.carga for c in candidatos}
	plano: dict[str, list[DiaEscala]] = {
		c.colega.employee: [
			DiaEscala(x.data, NEUTRO) if x.data in datas and x.trabalho else x for x in c.colega.dias
		]
		for c in candidatos
	}
	resultado = []
	for data, periodos, atual in sorted(turnos, key=lambda t: (t[0], [(p.inicio, p.fim) for p in t[1]])):
		turno = DiaEscala(data, TRABALHO, periodos)
		livres = []
		for c in candidatos:
			employee = c.colega.employee
			if any(x.data == data and x.trabalho for x in plano[employee]):
				continue
			if ev.validar(plano[employee], [turno], c.colega.parametros, realizados=c.colega.realizados):
				continue
			livres.append((carga[employee], employee != atual, c.colega.nome, employee))
		if not livres:
			resultado.append(Sugestao(data, periodos, atual, None))
			continue
		escolhido = min(livres)[3]
		carga[escolhido] += 1
		plano[escolhido] = ev.combinar(plano[escolhido], [turno])
		resultado.append(Sugestao(data, periodos, atual, escolhido))
	return resultado
