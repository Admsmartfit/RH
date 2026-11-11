"""Modelo CP-SAT do planejador (docs/PRD-planejador-5x2.md, PE-07, DP-4). Importa só o OR-Tools e o engine.

Variável: pessoa x dia x turno candidato. Duras: um turno por dia, teto diário (contrato/premissa), teto semanal do
regime, folgas da semana, 7º dia, interjornada, domingos seguidos, indisponibilidade, travas, supervisão e cota de
estagiário, rodízio de folgas (proposta C). Suaves (objetivo): déficit e ideal de cobertura, sobra, custo (com o
mínimo semanal do horista e o DSR), mudanças, ampliações de carga, vagas, equidade de fins de semana e budget.
"""

import math
from collections.abc import Callable, Iterable

from ortools.sat.python import cp_model

from hrms_secullum_brasil.engine.planejador.avaliacao import Perfil
from hrms_secullum_brasil.engine.planejador.custo import custo_minuto_centavos
from hrms_secullum_brasil.engine.planejador.heuristica import CUSTO_VAGA
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
from hrms_secullum_brasil.engine.planejador.turnos import candidatos, perto_de_hoje

PARES_RODIZIO = ((1, 2), (3, 4), (5, 6))  # ter/qua, qui/sex, sáb/dom
PESO_BUDGET = 10  # por centavo acima do budget


class _Parada(cp_model.CpSolverSolutionCallback):
	def __init__(self, parar: Callable[[], bool] | None):
		super().__init__()
		self._parar = parar

	def on_solution_callback(self):
		if self._parar and self._parar():
			self.StopSearch()


def resolver(
	pessoas: Iterable[Pessoa],
	horizonte: Horizonte,
	regras: Regras,
	demanda: Demanda,
	premissas: Premissas,
	perfil: Perfil,
	padroes: Iterable[Turno] = (),
	limite_s: float = 30,
	parar: Callable[[], bool] | None = None,
	budget_centavos: int | None = None,
) -> tuple[Escala, str]:
	pessoas = [
		p for p in pessoas if (perfil.contratar or not p.vaga) and (perfil.estagiarios or not p.estagiario)
	]
	padroes = tuple(padroes)
	dias = list(horizonte.dias)
	travas = {(pid, dia): turno for pid, dia, turno in premissas.travas}
	m = cp_model.CpModel()
	x: dict[tuple[str, int, Turno], cp_model.IntVar] = {}
	trabalho: dict[tuple[str, int], cp_model.LinearExpr] = {}
	extras = (regras.diaria_compensada,) if premissas.usar_compensacao and regras.diaria_compensada else ()

	for p in pessoas:
		limite = diaria_permitida(p, regras, premissas, perfil.ampliar)
		cands = perto_de_hoje(
			candidatos(limite, p.atual, padroes, extras=extras), p.atual, premissas.mudanca_max_entrada
		)
		for i in dias:
			if p.fixa or (p.id, i) in travas:
				fixo = (p.atual[i] if p.atual else None) if p.fixa else travas[(p.id, i)]
				opcoes = [fixo] if fixo else []
			else:
				opcoes = [
					c
					for c in cands
					if not any(
						ind.dia == i and c.inicio < ind.fim and ind.inicio < c.fim for ind in p.indisponivel
					)
				]
			for c in opcoes:
				x[(p.id, i, c)] = m.NewBoolVar(f"x_{p.id}_{i}_{c.inicio}_{c.fim}")
			vars_dia = [x[(p.id, i, c)] for c in opcoes]
			if vars_dia:
				m.Add(sum(vars_dia) <= 1)
				if p.fixa or (p.id, i) in travas:
					m.Add(sum(vars_dia) == 1)
			trabalho[(p.id, i)] = sum(vars_dia) if vars_dia else 0

	por_pessoa_dia: dict[tuple[str, int], list[tuple[Turno, cp_model.IntVar]]] = {}
	for (pid, i, c), v in x.items():
		por_pessoa_dia.setdefault((pid, i), []).append((c, v))

	objetivo = []
	amp_vars = []
	custo_pago = []  # centavos x minutos pagos (com o mínimo semanal): o mesmo custo do budget
	for p in pessoas:
		teto = min(regras.teto_semanal, p.semanal_max)
		# interjornada: o turno de hoje e os de amanhã que começam cedo demais
		for i in dias[:-1]:
			amanha = por_pessoa_dia.get((p.id, i + 1), [])
			for c, v in por_pessoa_dia.get((p.id, i), []):
				conflito = [w for d, w in amanha if d.inicio + 1440 - c.fim < regras.interjornada]
				if conflito:
					m.Add(v + sum(conflito) <= 1)
		centavos = custo_minuto_centavos(p, regras)
		for semana in range(horizonte.n_semanas):
			dias_semana = list(horizonte.dias_da_semana(semana))
			minutos = sum(c.minutos * v for i in dias_semana for c, v in por_pessoa_dia.get((p.id, i), []))
			m.Add(minutos <= teto)
			m.Add(sum(trabalho[(p.id, i)] for i in dias_semana) <= 7 - regras.folgas_semana)
			if centavos:
				pago = m.NewIntVar(0, 7 * 24 * 60, f"pago_{p.id}_{semana}")
				m.Add(pago >= minutos)
				if not p.vaga and p.semanal_min:
					m.Add(pago >= min(p.semanal_min, teto))
				objetivo.append(perfil.peso_custo * centavos * pago)
				custo_pago.append(centavos * pago)
		for inicio in range(len(dias) - 6):  # 7º dia seguido
			m.Add(sum(trabalho[(p.id, i)] for i in range(inicio, inicio + 7)) <= 6)
		sequencia = [1] * p.domingos_seguidos_antes + [trabalho[(p.id, i)] for i in horizonte.domingos()]
		janela = p.limite_domingos + 1
		for fim in range(max(janela, p.domingos_seguidos_antes + 1), len(sequencia) + 1):
			m.Add(sum(sequencia[fim - janela : fim]) <= p.limite_domingos)
		# mudanças em relação à escala de hoje (estabilidade)
		if p.atual and not p.vaga:
			for i in dias:
				original = p.atual[i]
				var = next((v for c, v in por_pessoa_dia.get((p.id, i), []) if c == original), None)
				muda = m.NewBoolVar(f"muda_{p.id}_{i}")
				if original is None:
					m.Add(muda >= trabalho[(p.id, i)])
				elif var is not None:
					m.Add(muda >= 1 - var)
				else:
					m.Add(muda == 1)
				objetivo.append(perfil.peso_mudanca * muda)
		ampliados = [
			v for i in dias for c, v in por_pessoa_dia.get((p.id, i), []) if c.minutos > p.diaria_atual
		]
		if ampliados and not p.vaga:
			amp = m.NewBoolVar(f"amp_{p.id}")
			for v in ampliados:
				m.Add(amp >= v)
			objetivo.append(perfil.peso_ampliacao * amp)
			amp_vars.append(amp)
		if p.vaga:
			usada = m.NewBoolVar(f"vaga_{p.id}")
			for i in dias:
				for _c, v in por_pessoa_dia.get((p.id, i), []):
					m.Add(usada >= v)
			objetivo.append(CUSTO_VAGA * usada)
	if amp_vars:
		m.Add(sum(amp_vars) <= premissas.max_ampliacoes)

	# rodízio de folgas por turmas (proposta C)
	if perfil.rodizio:
		rodam = [p for p in pessoas if not p.fixa and not p.vaga and not p.estagiario]
		if rodam:
			grupos = {(p.id, g): m.NewBoolVar(f"g_{p.id}_{g}") for p in rodam for g in range(3)}
			for p in rodam:
				m.AddExactlyOne(grupos[(p.id, g)] for g in range(3))
				for i in dias:
					semana, dia_semana = divmod(i, 7)
					folga = [
						grupos[(p.id, g)] for g in range(3) if dia_semana in PARES_RODIZIO[(g + semana) % 3]
					]
					if folga:
						m.Add(trabalho[(p.id, i)] <= 1 - sum(folga))
			for g in range(3):
				m.Add(sum(grupos[(p.id, g)] for p in rodam) <= math.ceil(len(rodam) / 3))

	# cobertura, estagiários e equidade
	cobre: dict[tuple[int, int], list] = {}
	for (pid, i, c), v in x.items():
		for f in c.faixas():
			cobre.setdefault((i, f), []).append((pid, v))
	por_id = {p.id: p for p in pessoas}
	for i, data in enumerate(horizonte.datas):
		for f in FAIXAS:
			minimo, ideal = demanda.de(data, f)
			quem = cobre.get((i, f), [])
			cov = sum(v for _pid, v in quem)
			if minimo:
				falta = m.NewIntVar(0, minimo, f"def_{i}_{f}")
				m.Add(falta >= minimo - cov)
				objetivo.append(perfil.peso_deficit * FAIXA_MIN * falta)
			if ideal:
				abaixo = m.NewIntVar(0, ideal, f"ide_{i}_{f}")
				m.Add(abaixo >= ideal - cov)
				objetivo.append(perfil.peso_ideal * FAIXA_MIN * abaixo)
				sobra = m.NewIntVar(0, len(pessoas), f"sob_{i}_{f}")
				m.Add(sobra >= cov - ideal)
				objetivo.append(perfil.peso_sobra * FAIXA_MIN * sobra)
			estagiarios = [v for pid, v in quem if por_id[pid].estagiario]
			if estagiarios:
				supervisores = [v for pid, v in quem if por_id[pid].cref and not por_id[pid].estagiario]
				for v in estagiarios:
					m.Add(v <= sum(supervisores) if supervisores else v == 0)
				m.Add(100 * sum(estagiarios) <= premissas.cota_estagiario_pct * cov)
	if perfil.peso_equidade:
		fds = [p for p in pessoas if not p.vaga and not p.fixa]
		if fds:
			maior = m.NewIntVar(0, len(dias), "fds_max")
			for p in fds:
				m.Add(maior >= sum(trabalho[(p.id, i)] for i in dias if horizonte.datas[i].weekday() >= 5))
			objetivo.append(perfil.peso_equidade * maior)
	if budget_centavos is not None and custo_pago:
		acima = m.NewIntVar(0, 10**12, "acima_budget")
		m.Add(acima >= sum(custo_pago) - budget_centavos)
		objetivo.append(PESO_BUDGET * acima)

	m.Minimize(sum(objetivo))
	solver = cp_model.CpSolver()
	solver.parameters.max_time_in_seconds = float(limite_s)
	solver.parameters.num_workers = 8
	solver.parameters.interleave_search = False  # o paralelo comum acha soluções bem melhores no mesmo tempo
	solver.parameters.random_seed = 141
	status = solver.Solve(m, _Parada(parar))
	if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
		return {}, "sem solução"
	escala: Escala = {}
	for p in pessoas:
		escala[p.id] = tuple(
			next((c for c, v in por_pessoa_dia.get((p.id, i), []) if solver.Value(v)), None) for i in dias
		)
	return escala, "ótima" if status == cp_model.OPTIMAL else "viável"
