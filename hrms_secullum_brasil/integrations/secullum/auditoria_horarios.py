"""Auditoria da configuração dos horários do Secullum (docs/PRD-sincronizacao-secullum.md, seção 9). Python puro.

A API não altera horário: cada diferença vira um Achado com o passo a passo para o RH fazer na tela do Secullum e os
`esperados` (caminho no JSON do GET Horarios → valor) que o programa confere depois ("Marquei como feita").

Grupos de faixas de extra (FaixasExtras[].DiaSemana): 0 Úteis, 1 Sábado, 2 Domingo, 3 Feriado, 4 Folga.
Dias (Dias[].DiaSemana): 0 segunda … 6 domingo.
"""

import re
from dataclasses import dataclass, field

DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
GRUPOS = {0: "Úteis", 1: "Sábado", 2: "Domingo", 3: "Feriado", 4: "Folga"}
FAIXA_MINIMA = {0: 50, 1: 50, 2: 100, 3: 100, 4: 100}


@dataclass(frozen=True)
class Esperado:
	"""Parâmetros da CCT/lei para o horário (vêm do programa)."""

	tolerancia_marcacao: int = 5
	tolerancia_diaria: int = 10
	interjornada: str = "11:00"
	teto_semanal: int = 2640
	horista: bool = False
	dsr_desconta_atraso: bool = False


@dataclass
class Achado:
	codigo: str  # estável por horário (chave da Tarefa Secullum)
	titulo: str
	atual: str
	esperado: str
	passos: list[str]
	esperados: list[dict] = field(default_factory=list)  # [{"campo": caminho, "valor": valor}]
	bloqueia_fechamento: bool = True
	verificavel: bool = True


def _min(h: str | None) -> int | None:
	if not h:
		return None
	a, b = str(h).split(":")[:2]
	return int(a) * 60 + int(b)


def _minutos_do_dia(d: dict) -> int:
	if d.get("Neutro"):
		return 0
	if d.get("Compensado") and d.get("Carga"):
		return int(d["Carga"])
	total = 0
	for n in range(1, 6):
		e, s = _min(d.get(f"Entrada{n}")), _min(d.get(f"Saida{n}"))
		if e is not None and s is not None:
			total += (s - e) % 1440
	return total


def semana_prevista(h: dict) -> int:
	return sum(_minutos_do_dia(d) for d in h.get("Dias") or [])


def _abrir(h: dict) -> str:
	return f'Secullum → Cadastros → Horários → clique no nº {h.get("Numero")} ("{h.get("Descricao")}") para editar.'


FECHAR = 'Salve. No programa, abra esta tarefa e clique em "Marquei como feita": o programa relê o horário e confirma.'


def auditar(h: dict, esp: Esperado) -> list[Achado]:
	op, ex, desc = h.get("Opcoes") or {}, h.get("Extras") or {}, h.get("Descanso") or {}
	numero = h.get("Numero")
	achados: list[Achado] = []

	def novo(codigo, titulo, atual, esperado, passo, esperados, bloqueia=True, verificavel=True):
		achados.append(
			Achado(
				f"H{numero}-{codigo}",
				titulo,
				str(atual),
				str(esperado),
				[_abrir(h), *passo, FECHAR],
				esperados,
				bloqueia,
				verificavel,
			)
		)

	if not op.get("ToleranciaArtigo58"):
		novo(
			"A58",
			"Ligar a tolerância do art. 58",
			"desligada",
			"ligada (5 min por marcação, 10 no dia)",
			['Na aba "Opções", marque "Tolerância Artigo 58".'],
			[{"campo": "Opcoes.ToleranciaArtigo58", "valor": True}],
		)

	dias_trabalho = [d for d in h.get("Dias") or [] if _minutos_do_dia(d) and not d.get("Neutro")]
	errados = [
		d
		for d in dias_trabalho
		if (d.get("ToleranciaExtra"), d.get("ToleranciaFalta"))
		!= (esp.tolerancia_marcacao, esp.tolerancia_marcacao)
	]
	if errados:
		t = esp.tolerancia_marcacao
		novo(
			"TOL",
			"Tolerância do dia = 5/5",
			", ".join(
				f"{DIAS[d['DiaSemana']]} {d.get('ToleranciaExtra')}/{d.get('ToleranciaFalta')}"
				for d in errados
			),
			f"{t}/{t} em todos os dias de trabalho",
			[
				f"No quadro dos dias da semana, em cada dia de trabalho ({', '.join(DIAS[d['DiaSemana']] for d in errados)}), "
				f'informe "Tolerância Extra" = {t} e "Tolerância Falta" = {t}.'
			],
			[
				{"campo": f"Dias[DiaSemana={d['DiaSemana']}].{c}", "valor": t}
				for d in errados
				for c in ("ToleranciaExtra", "ToleranciaFalta")
			],
		)

	for codigo, chave, rotulo in (
		("LIMEX", "LimiteMinimoDeExtrasNoDiaMinutos", "Limite mínimo de extras no dia"),
		("LIMFA", "LimiteMinimoDeFaltasNoDiaMinutos", "Limite mínimo de faltas no dia"),
	):
		valor = int(op.get(chave) or 0)
		if valor > esp.tolerancia_diaria:
			novo(
				codigo,
				f"{rotulo} até {esp.tolerancia_diaria} min",
				f"{valor} min",
				f"até {esp.tolerancia_diaria} min",
				[f'Na aba "Opções", informe "{rotulo}" = {esp.tolerancia_diaria}.'],
				[{"campo": f"Opcoes.{chave}", "valor": esp.tolerancia_diaria}],
			)

	if op.get("QualquerMinutoAdiantadoComoExtra"):
		novo(
			"ADIANT",
			'Desligar "qualquer minuto adiantado como extra"',
			"ligado",
			"desligado (vale a tolerância)",
			['Na aba "Opções", desmarque "Qualquer minuto adiantado como extra".'],
			[{"campo": "Opcoes.QualquerMinutoAdiantadoComoExtra", "valor": False}],
			bloqueia=not esp.horista,
		)
	if op.get("QualquerMinutoAtrasadoComoFalta"):
		novo(
			"ATRAS",
			'Desligar "qualquer minuto atrasado como falta"',
			"ligado",
			"desligado (o art. 58 proíbe descontar até 5 min)",
			['Na aba "Opções", desmarque "Qualquer minuto atrasado como falta".'],
			[{"campo": "Opcoes.QualquerMinutoAtrasadoComoFalta", "valor": False}],
		)

	if not ex.get("UsarInterjornada") or str(ex.get("Interjornada") or "")[:5] != esp.interjornada:
		novo(
			"INTER",
			"Interjornada de 11h",
			ex.get("Interjornada") if ex.get("UsarInterjornada") else "desligada",
			esp.interjornada,
			[f'Na aba "Extras", marque "Usar interjornada" e informe {esp.interjornada}.'],
			[
				{"campo": "Extras.UsarInterjornada", "valor": True},
				{"campo": "Extras.Interjornada", "valor": esp.interjornada},
			],
		)

	for grupo, minimo in FAIXA_MINIMA.items():
		faixas = next(
			(g.get("Faixas") for g in h.get("FaixasExtras") or [] if g.get("DiaSemana") == grupo), None
		)
		if not faixas:
			continue
		coluna = float(faixas[0].get("Coluna") or 0)
		if esp.horista and coluna == 1 and grupo != 3:
			continue  # coluna simples: horas acima da carga como hora normal (horista em escala)
		if coluna < minimo:
			novo(
				f"FX{grupo}",
				f"Extra de {GRUPOS[grupo]} = {minimo}%",
				f"{coluna:g}%",
				f"{minimo}%",
				[f'Na aba "Extras", no grupo "{GRUPOS[grupo]}", faixa 1: coluna = {minimo}.'],
				[{"campo": f"FaixasExtras[DiaSemana={grupo}].Faixas[0].Coluna", "valor": float(minimo)}],
			)
	if esp.horista:
		util = (
			next((g.get("Faixas") for g in h.get("FaixasExtras") or [] if g.get("DiaSemana") == 0), None)
			or []
		)
		if len(util) < 2:
			novo(
				"FX-8H",
				"Horista: acima de 8h no dia, extra de 50%",
				"uma faixa só (coluna simples)",
				"2ª faixa a 50% a partir de 8h no dia",
				[
					'Na aba "Extras", grupo "Úteis": acrescente a faixa 2 a partir das horas que completam 8h no '
					"dia, coluna 50. Se o Secullum não permitir faixa pelo total do dia, deixe como está: o programa "
					"calcula a extra acima de 8h e avisa na conferência."
				],
				[],
				bloqueia=False,
				verificavel=False,
			)

	if op.get("NaoCalcularNenhumaHoraNoturna"):
		novo(
			"NOT",
			"Calcular a hora noturna",
			"não calcula",
			"calcula (22h-5h, hora reduzida)",
			['Na aba "Opções", desmarque "Não calcular nenhuma hora noturna".'],
			[{"campo": "Opcoes.NaoCalcularNenhumaHoraNoturna", "valor": False}],
		)

	if desc.get("DescontarAtrasosEFaltasDSR") and not esp.dsr_desconta_atraso:
		novo(
			"DSR",
			"DSR: não descontar atrasos",
			"desconta atrasos",
			"só faltas",
			['Na aba "Descanso" (DSR), desmarque "Descontar atrasos e faltas do DSR".'],
			[{"campo": "Descanso.DescontarAtrasosEFaltasDSR", "valor": False}],
		)

	semana = semana_prevista(h)
	if semana > esp.teto_semanal:
		novo(
			"44H",
			"Jornada acima de 44h por semana",
			f"{semana // 60}:{semana % 60:02d}",
			f"até {esp.teto_semanal // 60}h",
			[
				"Crie um horário novo com no máximo 44h na semana (ex.: 8h48 por dia de segunda a sexta) em "
				"Cadastros → Horários → Incluir.",
				"No programa, troque o horário de cada colaborador pela Alteração de Jornada (com o termo assinado).",
			],
			[],
			verificavel=False,
		)
	return achados


# ------------------------------------------------------------------ verificação ("Marquei como feita")

_PASSO = re.compile(r"(\w+)(?:\[(?:(\w+)=)?([^\]]+)\])?")


def ler(h: dict, caminho: str):
	"""Lê "Opcoes.X", "Dias[DiaSemana=0].ToleranciaFalta", "FaixasExtras[DiaSemana=4].Faixas[0].Coluna"."""
	atual = h
	for parte in caminho.split("."):
		m = _PASSO.fullmatch(parte)
		if not m or atual is None:
			return None
		nome, chave, indice = m.groups()
		atual = atual.get(nome) if isinstance(atual, dict) else None
		if indice is not None:
			if not isinstance(atual, list):
				return None
			if chave:
				atual = next((x for x in atual if str(x.get(chave)) == indice), None)
			else:
				i = int(indice)
				atual = atual[i] if i < len(atual) else None
	return atual


def _igual(atual, esperado) -> bool:
	if isinstance(esperado, bool):
		return bool(atual) is esperado
	if isinstance(esperado, int | float):
		try:
			return float(atual) == float(esperado)
		except (TypeError, ValueError):
			return False
	return str(atual or "")[: len(str(esperado))] == str(esperado)


def divergencias(h: dict | None, esperados: list[dict]) -> list[str]:
	"""O que ainda está diferente (vazio = verificado)."""
	if not h:
		return ["horário não encontrado no Secullum"]
	return [
		f"{e['campo']}: está {ler(h, e['campo'])!r}, esperado {e['valor']!r}"
		for e in esperados
		if not _igual(ler(h, e["campo"]), e["valor"])
	]
