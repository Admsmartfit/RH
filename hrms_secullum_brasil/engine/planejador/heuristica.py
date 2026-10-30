"""Heurística de reserva do planejador (DP-4): busca local determinística, em Python puro, quando o OR-Tools não está
instalado. Parte da escala de hoje e troca, um dia de cada vez, o turno de uma pessoa pelo candidato que mais reduz
o objetivo (déficit, ideal, custo, mudanças), sem nunca quebrar uma restrição dura. Boa, não ótima: o resultado vem
marcado como heurística."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from hrms_secullum_brasil.engine.planejador.avaliacao import Perfil
from hrms_secullum_brasil.engine.planejador.custo import custo_minuto_centavos
from hrms_secullum_brasil.engine.planejador.modelos import (
	FAIXA_MIN,
	FAIXAS,
	Demanda,
	Escala,
	Horizonte,
	Pessoa,
	Premissas,
	Regras,
	Turno,
	diaria_permitida,
)
from hrms_secullum_brasil.engine.planejador.turnos import candidatos

CUSTO_VAGA = 50_000_00  # centavos-equivalentes: abrir uma vaga só quando o déficit justifica


@dataclass
class _Estado:
	escala: dict[str, list[Turno | None]]
	cob: dict[tuple[int, int], int]


def _pena_dia(i: int, cob, horizonte: Horizonte, demanda: Demanda, perfil: Perfil) -> int:
	data = horizonte.datas[i]
	total = 0
	for faixa in FAIXAS:
		minimo, ideal = demanda.de(data, faixa)
		n = cob.get((i, faixa), 0)
		total += perfil.peso_deficit * max(0, minimo - n) * FAIXA_MIN
		total += perfil.peso_ideal * max(0, ideal - n) * FAIXA_MIN
		if ideal:
			total += perfil.peso_sobra * max(0, n - ideal) * FAIXA_MIN
	return total


def _viavel_pessoa(p: Pessoa, turnos: list, horizonte: Horizonte, regras: Regras, limite_dia: int) -> bool:
	teto = min(regras.teto_semanal, p.semanal_max)
	for i, t in enumerate(turnos):
		if t is None:
			continue
		if t.minutos > limite_dia:
			return False
		if any(ind.dia == i and t.inicio < ind.fim and ind.inicio < t.fim for ind in p.indisponivel):
			return False
		if (
			i + 1 < len(turnos)
			and turnos[i + 1] is not None
			and turnos[i + 1].inicio + 1440 - t.fim < regras.interjornada
		):
			return False
	for semana in range(horizonte.n_semanas):
		dias = [turnos[i] for i in horizonte.dias_da_semana(semana)]
		if sum(t.minutos for t in dias if t) > teto or sum(1 for t in dias if t) > 7 - regras.folgas_semana:
			return False
	seguidos = 0
	for t in turnos:
		seguidos = seguidos + 1 if t else 0
		if seguidos >= 7:
			return False
	domingos = p.domingos_seguidos_antes
	for i in horizonte.domingos():
		domingos = domingos + 1 if turnos[i] else 0
		if domingos > p.limite_domingos:
			return False
	return True


def _custo_pessoa(p: Pessoa, turnos: list, horizonte: Horizonte, regras: Regras, centavos: int) -> int:
	teto = min(regras.teto_semanal, p.semanal_max)
	total = 0
	for semana in range(horizonte.n_semanas):
		minutos = min(teto, sum(t.minutos for i in horizonte.dias_da_semana(semana) if (t := turnos[i])))
		if not p.vaga:
			minutos = max(minutos, min(p.semanal_min, teto))
		total += minutos * centavos
	if p.vaga and any(turnos):
		total += CUSTO_VAGA
	return total


def _supervisao_ok(i: int, estado: _Estado, por_id: dict[str, Pessoa], premissas: Premissas) -> bool:
	presentes: dict[int, list[Pessoa]] = {}
	for pid, turnos in estado.escala.items():
		if turnos[i]:
			for faixa in turnos[i].faixas():
				presentes.setdefault(faixa, []).append(por_id[pid])
	for quem in presentes.values():
		estagiarios = sum(1 for p in quem if p.estagiario)
		if estagiarios and (
			not any(p.cref and not p.estagiario for p in quem)
			or estagiarios * 100 > premissas.cota_estagiario_pct * len(quem)
		):
			return False
	return True


def resolver(
	pessoas: Iterable[Pessoa],
	horizonte: Horizonte,
	regras: Regras,
	demanda: Demanda,
	premissas: Premissas,
	perfil: Perfil,
	padroes: Iterable[Turno] = (),
	passos: int = 4,
	parar: Callable[[], bool] | None = None,
) -> Escala:
	pessoas = [p for p in pessoas if perfil.contratar or not p.vaga]
	pessoas = [p for p in pessoas if perfil.estagiarios or not p.estagiario]
	por_id = {p.id: p for p in pessoas}
	padroes = tuple(padroes)
	travas = {(pid, dia): turno for pid, dia, turno in premissas.travas}
	n = len(horizonte.datas)
	escala = {p.id: list(p.atual) if p.atual else [None] * n for p in pessoas}
	limites = {p.id: diaria_permitida(p, regras, premissas, perfil.ampliar) for p in pessoas}
	extras = (regras.diaria_compensada,) if premissas.usar_compensacao and regras.diaria_compensada else ()
	cands = {
		p.id: (None, *candidatos(limites[p.id], p.atual, padroes, extras=extras))
		for p in pessoas
		if not p.fixa
	}
	for (pid, dia), turno in travas.items():
		if pid in escala:
			escala[pid][dia] = turno
	centavos = {p.id: custo_minuto_centavos(p, regras) or 1 for p in pessoas}
	for p in pessoas:  # o ponto de partida também precisa ser viável
		if not p.fixa and not _viavel_pessoa(p, escala[p.id], horizonte, regras, limites[p.id]):
			escala[p.id] = [travas.get((p.id, i)) for i in range(n)]
	cob: dict[tuple[int, int], int] = {}
	for turnos in escala.values():
		for i, t in enumerate(turnos):
			if t:
				for f in t.faixas():
					cob[(i, f)] = cob.get((i, f), 0) + 1
	estado = _Estado(escala, cob)
	for _passo in range(passos):
		melhorou = False
		for i in range(n):
			if parar and parar():
				return {k: tuple(v) for k, v in escala.items()}
			for p in pessoas:
				if p.fixa or (p.id, i) in travas:
					continue
				atual_t = escala[p.id][i]
				base_dia = _pena_dia(i, cob, horizonte, demanda, perfil)
				base_custo = _custo_pessoa(p, escala[p.id], horizonte, regras, centavos[p.id])
				melhor, melhor_ganho = None, 0
				for c in cands[p.id]:
					if c == atual_t:
						continue
					escala[p.id][i] = c
					if not _viavel_pessoa(p, escala[p.id], horizonte, regras, limites[p.id]):
						continue
					for f in atual_t.faixas() if atual_t else ():
						cob[(i, f)] -= 1
					for f in c.faixas() if c else ():
						cob[(i, f)] = cob.get((i, f), 0) + 1
					ganho = base_dia - _pena_dia(i, cob, horizonte, demanda, perfil)
					ganho += perfil.peso_custo * (
						base_custo - _custo_pessoa(p, escala[p.id], horizonte, regras, centavos[p.id])
					)
					original = p.atual[i] if p.atual else None
					ganho -= perfil.peso_mudanca * ((c != original) - (atual_t != original))
					if (
						c
						and c.minutos > p.diaria_atual
						and not any(t and t.minutos > p.diaria_atual for t in p.atual)
					):
						ganho -= perfil.peso_ampliacao // 10
					if ganho > melhor_ganho and (
						not any(x.estagiario for x in pessoas) or _supervisao_ok(i, estado, por_id, premissas)
					):
						melhor, melhor_ganho = c, ganho
					for f in c.faixas() if c else ():
						cob[(i, f)] -= 1
					for f in atual_t.faixas() if atual_t else ():
						cob[(i, f)] += 1
				escala[p.id][i] = atual_t
				if melhor_ganho > 0:
					for f in atual_t.faixas() if atual_t else ():
						cob[(i, f)] -= 1
					for f in melhor.faixas() if melhor else ():
						cob[(i, f)] = cob.get((i, f), 0) + 1
					escala[p.id][i] = melhor
					melhorou = True
		if not melhorou:
			break
	return {k: tuple(v) for k, v in escala.items()}
