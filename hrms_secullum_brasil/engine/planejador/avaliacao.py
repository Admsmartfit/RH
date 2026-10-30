"""Avaliação e comparação das propostas (PE-07, PE-09, PE-10): cobertura por faixa, mapa de calor, indicadores,
mudanças pessoa a pessoa com o motivo e os perfis das propostas A a E. É só simulação (DP-9): a lista de mudanças é
o que o gestor lança à mão na tela Escalas."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from hrms_secullum_brasil.engine.planejador.custo import custo_mensal
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
	faixa_texto,
)
from hrms_secullum_brasil.engine.planejador.restricoes import violacoes

DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


# ------------------------------------------------------------------ perfis das propostas (PE-07)


@dataclass(frozen=True)
class Perfil:
	codigo: str
	titulo: str
	descricao: str
	peso_deficit: int = 1000  # por minuto-pessoa abaixo do mínimo
	peso_ideal: int = 100  # por minuto-pessoa abaixo do ideal
	peso_sobra: int = 5  # por minuto-pessoa acima do ideal
	peso_custo: int = 1  # por centavo
	peso_mudanca: int = 2000  # por dia mudado em relação à escala de hoje
	peso_ampliacao: int = 20000  # por pessoa com carga ampliada
	peso_equidade: int = 500  # por fim de semana acima da média
	ampliar: bool = False
	estagiarios: bool = True
	rodizio: bool = False
	contratar: bool = False


def perfis(premissas: Premissas) -> list[Perfil]:
	"""As propostas geradas (DP-4): cada uma com um objetivo; a E usa só os pesos do gestor."""
	cobertura = max(1, premissas.peso_cobertura)
	custo = max(1, premissas.peso_custo)
	mudanca = 400 * premissas.peso_estabilidade
	saida = [
		Perfil(
			"A",
			"Menor custo",
			"Mantém a carga de hoje (horistas de 4h), cobre os fins de semana e os picos com quem já está na equipe e "
			"com estagiários (sempre com um profissional de CREF).",
			peso_deficit=600,
			peso_ideal=20,
			peso_custo=3,
			peso_mudanca=mudanca,
			estagiarios=premissas.usar_estagiarios,
		),
		Perfil(
			"B",
			"Qualidade técnica",
			"Amplia a carga de horistas de índice alto (até o teto escolhido) para cobrir os picos com instrutores "
			"experientes; mostra o custo extra e o DSR.",
			peso_deficit=1500,
			peso_ideal=200,
			peso_custo=1,
			peso_mudanca=mudanca,
			ampliar=True,
			estagiarios=False,
		),
		Perfil(
			"C",
			"Cobertura uniforme (rodízio)",
			"Folgas em rodízio por turmas (ter/qua, qui/sex, sáb/dom), respeitando a regra de domingos; espalha a "
			"cobertura pela semana com equidade nos fins de semana.",
			peso_deficit=1200,
			peso_ideal=150,
			peso_custo=1,
			peso_mudanca=mudanca // 2,
			peso_equidade=2000,
			ampliar=True,
			estagiarios=premissas.usar_estagiarios,
			rodizio=True,
		),
	]
	if premissas.contratar:
		saida.append(
			Perfil(
				"D",
				"Contratar",
				"Quantas contratações (e em que horários) fecham o déficit, com o custo de cada vaga.",
				peso_deficit=3000,
				peso_ideal=300,
				peso_custo=1,
				peso_mudanca=mudanca,
				ampliar=True,
				estagiarios=premissas.usar_estagiarios,
				contratar=True,
			)
		)
	saida.append(
		Perfil(
			"E",
			"Personalizada",
			"Só as premissas e os pesos que você escolheu.",
			peso_deficit=200 * cobertura,
			peso_ideal=20 * cobertura,
			peso_custo=custo,
			peso_mudanca=mudanca,
			ampliar=premissas.ampliar != "nenhum",
			estagiarios=premissas.usar_estagiarios,
			contratar=premissas.contratar,
		)
	)
	return saida


# ------------------------------------------------------------------ cobertura e mapa de calor (PE-08)


def cobertura(escala: Escala, horizonte: Horizonte) -> dict[tuple[int, int], int]:
	saida: dict[tuple[int, int], int] = {}
	for turnos in escala.values():
		for i, t in enumerate(turnos):
			if t:
				for faixa in t.faixas():
					saida[(i, faixa)] = saida.get((i, faixa), 0) + 1
	return saida


def deficits(escala: Escala, horizonte: Horizonte, demanda: Demanda) -> dict[tuple[int, int], int]:
	"""Pessoas faltando abaixo do mínimo, por (dia, faixa)."""
	cob = cobertura(escala, horizonte)
	saida = {}
	for i, data in enumerate(horizonte.datas):
		for faixa in FAIXAS:
			minimo, _ideal = demanda.de(data, faixa)
			falta = minimo - cob.get((i, faixa), 0)
			if falta > 0:
				saida[(i, faixa)] = falta
	return saida


def mapa(escala: Escala, horizonte: Horizonte, demanda: Demanda) -> list[dict]:
	"""Por dia: as faixas com mínimo, ideal, cobertura e a situação (deficit, limite, ok, sobra) — sempre com número."""
	cob = cobertura(escala, horizonte)
	dias = []
	for i, data in enumerate(horizonte.datas):
		faixas = []
		for faixa in FAIXAS:
			minimo, ideal = demanda.de(data, faixa)
			n = cob.get((i, faixa), 0)
			if n < minimo:
				situacao = "deficit"
			elif n < ideal:
				situacao = "limite"
			elif ideal and n > ideal + 1:
				situacao = "sobra"
			else:
				situacao = "ok" if (minimo or n) else "vazio"
			faixas.append(
				{
					"faixa": faixa,
					"texto": faixa_texto(faixa),
					"minimo": minimo,
					"ideal": ideal,
					"cobertura": n,
					"situacao": situacao,
				}
			)
		dias.append({"data": str(data), "dia_semana": DIAS[data.weekday()], "faixas": faixas})
	return dias


# ------------------------------------------------------------------ indicadores e comparação (PE-09)


@dataclass
class Indicadores:
	custo_mensal: Decimal
	delta: Decimal = Decimal(0)
	delta_pct: float | None = None
	deficit_minutos: int = 0  # pessoa-minutos abaixo do mínimo no horizonte
	cobertura_pct: float = 100.0  # faixas com o mínimo atendido / faixas com mínimo
	pior_faixa: str = ""
	violacoes_duras: int = 0
	violacoes_suaves: int = 0
	mudancas: int = 0
	ampliacoes: list[str] = field(default_factory=list)
	vagas: list[str] = field(default_factory=list)
	fins_de_semana: dict[str, int] = field(default_factory=dict)
	acima_do_budget: bool = False


def indicadores(
	escala: Escala,
	pessoas: Iterable[Pessoa],
	horizonte: Horizonte,
	regras: Regras,
	demanda: Demanda,
	premissas: Premissas,
	atual: Escala | None = None,
	custo_atual: Decimal | None = None,
) -> Indicadores:
	pessoas = list(pessoas)
	por_id = {p.id: p for p in pessoas}
	custo = custo_mensal(escala, pessoas, horizonte, regras)["total"]
	cob = cobertura(escala, horizonte)
	com_minimo = atendidas = deficit = 0
	pior, pior_falta = "", 0
	for i, data in enumerate(horizonte.datas):
		for faixa in FAIXAS:
			minimo, _ideal = demanda.de(data, faixa)
			if not minimo:
				continue
			com_minimo += 1
			falta = max(0, minimo - cob.get((i, faixa), 0))
			deficit += falta * FAIXA_MIN
			atendidas += not falta
			if falta > pior_falta:
				pior, pior_falta = (
					f"{DIAS[data.weekday()]} {data:%d/%m} {faixa_texto(faixa)} (faltam {falta})",
					falta,
				)
	vs = violacoes(escala, pessoas, horizonte, regras, premissas)
	mudancas = 0
	ampliacoes, vagas = [], []
	for pid, turnos in escala.items():
		p = por_id[pid]
		if p.vaga:
			if any(turnos):
				vagas.append(pid)
			continue
		if atual and pid in atual:
			mudancas += sum(1 for a, b in zip(atual[pid], turnos, strict=False) if a != b)
		if any(t and t.minutos > p.diaria_atual for t in turnos):
			ampliacoes.append(pid)
	fds = {
		pid: sum(1 for i, t in enumerate(turnos) if t and horizonte.datas[i].weekday() >= 5)
		for pid, turnos in escala.items()
		if not por_id[pid].vaga
	}
	ind = Indicadores(
		custo_mensal=custo,
		deficit_minutos=deficit,
		cobertura_pct=round(100 * atendidas / com_minimo, 1) if com_minimo else 100.0,
		pior_faixa=pior,
		violacoes_duras=sum(1 for v in vs if v.dura),
		violacoes_suaves=sum(1 for v in vs if not v.dura),
		mudancas=mudancas,
		ampliacoes=ampliacoes,
		vagas=vagas,
		fins_de_semana=fds,
	)
	if custo_atual is not None:
		ind.delta = custo - custo_atual
		ind.delta_pct = round(float(ind.delta / custo_atual * 100), 1) if custo_atual else None
		if premissas.budget_pct is not None and custo_atual:
			ind.acima_do_budget = custo > custo_atual * (1 + Decimal(str(premissas.budget_pct)) / 100)
	return ind


# ------------------------------------------------------------------ o que mudar (PE-10, manual)


@dataclass(frozen=True)
class Mudanca:
	pessoa: str
	dia: int
	de: Turno | None
	para: Turno | None
	motivo: str


def _texto(t: Turno | None) -> str:
	return t.texto if t else "folga"


def mudancas(atual: Escala, proposta: Escala, horizonte: Horizonte, demanda: Demanda) -> list[Mudanca]:
	"""Cada dia que muda, com o motivo em linguagem simples (as faixas em déficit que passa a cobrir)."""
	faltas = deficits(atual, horizonte, demanda)
	saida = []
	for pid, turnos in proposta.items():
		antes = atual.get(pid) or (None,) * len(turnos)
		for i, (a, b) in enumerate(zip(antes, turnos, strict=False)):
			if a == b:
				continue
			novas = set(b.faixas()) - set(a.faixas() if a else ()) if b else set()
			cobre = sorted(f for f in novas if faltas.get((i, f)))
			data = horizonte.datas[i]
			if cobre:
				motivo = f"cobre {faixa_texto(cobre[0])[:5]}-{faixa_texto(cobre[-1])[-5:]} de {DIAS[data.weekday()]}, onde faltavam instrutores"
			elif b is None:
				motivo = "folga: cumpre as folgas da semana ou libera horário com sobra"
			elif a is None:
				motivo = "novo turno para chegar mais perto do ideal"
			else:
				motivo = "ajuste de horário para equilibrar a cobertura"
			saida.append(Mudanca(pid, i, a, b, motivo))
	return saida


def lista_de_mudancas(
	itens: Iterable[Mudanca], pessoas: Iterable[Pessoa], horizonte: Horizonte
) -> list[dict]:
	nomes = {p.id: p.nome for p in pessoas}
	return [
		{
			"chave": f"{m.pessoa}|{horizonte.datas[m.dia]}",
			"pessoa": m.pessoa,
			"nome": nomes.get(m.pessoa, m.pessoa),
			"data": str(horizonte.datas[m.dia]),
			"dia_semana": DIAS[horizonte.datas[m.dia].weekday()],
			"de": _texto(m.de),
			"para": _texto(m.para),
			"motivo": m.motivo,
		}
		for m in sorted(itens, key=lambda m: (nomes.get(m.pessoa, ""), m.dia))
	]


def resumo_texto(ind: Indicadores, nomes: dict[str, str]) -> str:
	partes = [
		f"Custo {'+' if ind.delta >= 0 else '-'}R$ {abs(ind.delta):.2f}/mês"
		+ (f" ({ind.delta_pct:+.1f}%)" if ind.delta_pct is not None else "")
	]
	partes.append(f"cobertura do mínimo em {ind.cobertura_pct:.0f}% das faixas")
	if ind.ampliacoes:
		partes.append("amplia a carga de " + ", ".join(nomes.get(x, x) for x in ind.ampliacoes))
	if ind.vagas:
		partes.append(f"{len(ind.vagas)} contratação(ões)")
	partes.append(f"{ind.mudancas} dia(s) mudam")
	return "; ".join(partes) + "."
