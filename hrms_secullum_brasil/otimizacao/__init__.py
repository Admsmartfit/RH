"""Otimizador do planejador de escalas (docs/PRD-planejador-5x2.md, DP-4). Pacote puro: importa o OR-Tools (se
instalado) e o engine; nunca o Frappe. Sem OR-Tools, usa a heurística do engine e marca a proposta.

`gerar_propostas` monta as propostas A a E, confere cada uma com as restrições do engine (DP-5) e devolve os
indicadores, o mapa de calor e a lista do que mudar (é só simulação, DP-9)."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from decimal import Decimal
from time import monotonic

from hrms_secullum_brasil.engine.planejador import avaliacao as av
from hrms_secullum_brasil.engine.planejador import heuristica
from hrms_secullum_brasil.engine.planejador.custo import custo_mensal, custo_minuto_centavos
from hrms_secullum_brasil.engine.planejador.modelos import (
	HORISTA,
	Demanda,
	Escala,
	Horizonte,
	Pessoa,
	Premissas,
	Regras,
	Turno,
)
from hrms_secullum_brasil.engine.planejador.restricoes import violacoes

try:  # o OR-Tools é opcional: sem ele, a heurística (DP-4)
	from hrms_secullum_brasil.otimizacao import cpsat
except ImportError:  # pragma: no cover - depende do ambiente
	cpsat = None


def tem_otimizador() -> bool:
	return cpsat is not None


def vagas(premissas: Premissas, horizonte: Horizonte, regras: Regras) -> list[Pessoa]:
	"""Contratações possíveis (proposta D): horistas com o custo de referência da vaga."""
	return [
		Pessoa(
			id=f"VAGA-{n + 1}",
			nome=f"Vaga {n + 1} (contratar)",
			tipo=HORISTA,
			custo_hora=premissas.custo_vaga_hora,
			diaria_atual=premissas.teto_horista,
			semanal_max=regras.teto_semanal,
			atual=(None,) * len(horizonte.datas),
			vaga=True,
		)
		for n in range(max(0, premissas.max_vagas))
	]


def _sem_vagas_vazias(escala: Escala, pessoas: dict[str, Pessoa]) -> Escala:
	return {pid: t for pid, t in escala.items() if not pessoas[pid].vaga or any(t)}


def _horas(turnos) -> float:
	return round(sum(t.minutos for t in turnos if t) / 60, 1)


def gerar_propostas(
	pessoas: Iterable[Pessoa],
	horizonte: Horizonte,
	regras: Regras,
	demanda: Demanda,
	premissas: Premissas,
	padroes: Iterable[Turno] = (),
	limite_s: float = 30,
	parar: Callable[[], bool] | None = None,
	progresso: Callable[[int, int, str], None] | None = None,
	usar_otimizador: bool = True,
) -> dict:
	pessoas = list(pessoas)
	padroes = tuple(padroes)
	reais = [p for p in pessoas if not p.vaga]
	atual: Escala = {p.id: p.atual for p in reais}
	custo_atual = custo_mensal(atual, reais, horizonte, regras)["total"]
	budget = None
	if premissas.budget_pct is not None:
		fator = Decimal(len(horizonte.datas)) / 30
		budget = int(custo_atual * (1 + Decimal(str(premissas.budget_pct)) / 100) * fator * 100)
	todos = pessoas + (vagas(premissas, horizonte, regras) if premissas.contratar else [])
	por_id = {p.id: p for p in todos}
	nomes = {p.id: p.nome for p in todos}
	lista = av.perfis(premissas)
	saida = []
	for n, perfil in enumerate(lista):
		if parar and parar():
			break
		if progresso:
			progresso(n, len(lista), perfil.titulo)
		inicio = monotonic()
		motor = "otimizador" if (usar_otimizador and cpsat) else "heurística"
		situacao = ""
		if motor == "otimizador":
			escala, situacao = cpsat.resolver(
				todos, horizonte, regras, demanda, premissas, perfil, padroes, limite_s, parar, budget
			)
			if not escala:
				motor = "heurística"
		if motor == "heurística":
			escala = heuristica.resolver(
				todos, horizonte, regras, demanda, premissas, perfil, padroes, parar=parar
			)
			situacao = "boa (heurística)"
		escala = _sem_vagas_vazias(escala, por_id)
		usadas = [por_id[pid] for pid in escala]
		vs = violacoes(escala, usadas, horizonte, regras, premissas, perfil.ampliar)
		ind = av.indicadores(escala, usadas, horizonte, regras, demanda, premissas, atual, custo_atual)
		completo = {**{pid: atual.get(pid) or (None,) * len(horizonte.datas) for pid in atual}, **escala}
		saida.append(
			{
				"codigo": perfil.codigo,
				"titulo": perfil.titulo,
				"descricao": perfil.descricao,
				"motor": motor,
				"situacao": situacao,
				"segundos": round(monotonic() - inicio, 1),
				"valida": not any(v.dura for v in vs),
				"violacoes": [
					{
						"tipo": v.tipo,
						"pessoa": nomes.get(v.pessoa, v.pessoa),
						"mensagem": v.mensagem,
						"dura": v.dura,
					}
					for v in vs
				],
				"indicadores": _ind_dict(ind, nomes),
				"resumo": av.resumo_texto(ind, nomes),
				"escala": escala_json(completo),
				"horas": {pid: _horas(t) for pid, t in completo.items()},
				"mapa": av.mapa(completo, horizonte, demanda),
				"mudancas": av.lista_de_mudancas(
					av.mudancas(atual, completo, horizonte, demanda), todos, horizonte
				),
			}
		)
	if progresso:
		progresso(len(lista), len(lista), "")
	ind_atual = av.indicadores(atual, reais, horizonte, regras, demanda, premissas, atual, custo_atual)
	return {
		"atual": {
			"indicadores": _ind_dict(ind_atual, nomes),
			"escala": escala_json(atual),
			"horas": {pid: _horas(t) for pid, t in atual.items()},
			"mapa": av.mapa(atual, horizonte, demanda),
			"violacoes": [
				{
					"tipo": v.tipo,
					"pessoa": nomes.get(v.pessoa, v.pessoa),
					"mensagem": v.mensagem,
					"dura": v.dura,
				}
				for v in violacoes(
					atual, reais, horizonte, regras, replace(premissas, teto_horista=24 * 60), True
				)
			],
		},
		"propostas": saida,
		"pessoas": [
			{
				"id": p.id,
				"nome": p.nome,
				"tipo": p.tipo,
				"indice": p.indice,
				"custo_minuto_centavos": custo_minuto_centavos(p, regras),
				"vaga": p.vaga,
				"fixa": p.fixa,
			}
			for p in todos
		],
		"datas": [str(d) for d in horizonte.datas],
		"custo_atual": float(custo_atual),
		"otimizador": bool(usar_otimizador and cpsat),
	}


def _ind_dict(ind: av.Indicadores, nomes: dict[str, str]) -> dict:
	return {
		"custo_mensal": float(ind.custo_mensal),
		"delta": float(ind.delta),
		"delta_pct": ind.delta_pct,
		"deficit_horas": round(ind.deficit_minutos / 60, 1),
		"cobertura_pct": ind.cobertura_pct,
		"pior_faixa": ind.pior_faixa,
		"violacoes_duras": ind.violacoes_duras,
		"violacoes_suaves": ind.violacoes_suaves,
		"mudancas": ind.mudancas,
		"ampliacoes": [nomes.get(x, x) for x in ind.ampliacoes],
		"vagas": [nomes.get(x, x) for x in ind.vagas],
		"fins_de_semana": {nomes.get(k, k): v for k, v in ind.fins_de_semana.items()},
		"acima_do_budget": ind.acima_do_budget,
	}


def escala_json(escala: Escala) -> dict[str, list]:
	return {
		pid: [[t.inicio, t.fim, t.pausa] if t else None for t in turnos] for pid, turnos in escala.items()
	}
