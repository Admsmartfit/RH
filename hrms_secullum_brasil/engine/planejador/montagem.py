"""Montagem manual da escala 5x2 dos instrutores (docs/PRD-planejador-instrutores.md). Python puro.

É **só simulação** (DI-7): nada daqui grava escala. O plano é um dicionário (o mesmo JSON que a tela edita):

	{"ano": 2026, "mes": 12,
	 "parametros": {...PADROES...},
	 "equipe": [{"id", "nome", "tipo" (instrutor|estagiario), "employee", "prevista", "base": [ini, fim],
	             "contrato": [ini, fim] | None, "valor_hora", "retirado"}],
	 "grade": {id: {"AAAA-MM-DD": {"i": ini, "f": fim, "p": início da pausa | None} | None (folga)}}}

Horários em minutos do dia (05:00 = 300). A semana vai de segunda a domingo; o mês é o do calendário (Q-4).
"""

import re
import unicodedata
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import defaults_legais as d

INSTRUTOR, ESTAGIARIO = "instrutor", "estagiario"
BLOQUEANTE, ALTO, MEDIO, BAIXO = "Bloqueante", "Alto", "Médio", "Baixo"
GRAVIDADES = (BLOQUEANTE, ALTO, MEDIO, BAIXO)
HORAS = tuple(range(5, 23))  # 05h ... 22h (a hora das 22h às 23h), como nos slides
DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
FORA, DESCOBERTA, PARCIAL, UM, VARIOS = "fora", "descoberta", "parcial", "um", "varios"

PADROES = {
	# funcionamento por dia da semana (0 = segunda); feriado segue o sábado (DI-11)
	"funcionamento": {str(i): [300, 1380] for i in range(5)} | {"5": [480, 1020], "6": [480, 840]},
	# turnos do fim de semana e do feriado (RH, 10/11/2026), editáveis na simulação
	"turnos_fds": {"sabado": [[480, 780], [720, 1020]], "domingo": [[480, 840]]},
	"pico": [0, 1, 2],  # segunda, terça e quarta (C-8)
	"teto_aviso": 240,  # mais de 4 h no dia é aviso (DI-5)
	"movimento": [[360, 660], [1020, 1320]],  # maior movimento para os estagiários (DI-14)
	"estagio_minutos": 300,  # 5 h por dia, de segunda a sexta
	"bolsa": 0,  # bolsa mensal de referência do estagiário (custo); 0 = sem custo
	"repousos": 2,  # 5x2: repousos remunerados por semana (DSR do horista)
	"feriados": [],
	# não mudar muito o horário de quem já trabalha (RH, 10/11/2026): a entrada anda no máximo isto do horário de hoje
	"mudanca_max": 60,
	# 4 h por dia é o normal; até 6 h (pausa de 15 min) só para quem foi liberado ("liberados") ou para quem tapa
	# hora descoberta ("cobrir") — opção da simulação
	"regra_6h": "liberados",
	"teto_dia": 360,
	# instruções do gestor em texto (`instrucoes.py`) e o que foi entendido delas, por pessoa
	"instrucoes": "",
	"restricoes": {},
}


def hhmm(minutos: int) -> str:
	minutos %= 24 * 60
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def duracao(minutos: int) -> str:
	if minutos < 60:
		return f"{minutos} min"
	return f"{minutos // 60} h" if minutos % 60 == 0 else f"{minutos // 60}h{minutos % 60:02d}"


def parametros(plano: dict) -> dict:
	return {**PADROES, **(plano.get("parametros") or {})}


# ------------------------------------------------------------------ calendário


def semanas_do_mes(ano: int, mes: int) -> list[list[date]]:
	"""As semanas (segunda a domingo) que tocam o mês do calendário."""
	primeiro = date(ano, mes, 1)
	ultimo = (date(ano + mes // 12, mes % 12 + 1, 1)) - timedelta(days=1)
	inicio = primeiro - timedelta(days=primeiro.weekday())
	semanas = []
	while inicio <= ultimo:
		semanas.append([inicio + timedelta(days=i) for i in range(7)])
		inicio += timedelta(days=7)
	return semanas


def datas_do_plano(plano: dict) -> list[date]:
	return [dia for semana in semanas_do_mes(plano["ano"], plano["mes"]) for dia in semana]


def e_feriado(plano: dict, dia: date) -> bool:
	return dia.isoformat() in set(parametros(plano)["feriados"])


def tipo_do_dia(plano: dict, dia: date) -> str:
	"""util, sabado (também o feriado) ou domingo."""
	if dia.weekday() == 6:
		return "domingo"
	if dia.weekday() == 5 or e_feriado(plano, dia):
		return "sabado"
	return "util"


def funcionamento(plano: dict, dia: date) -> tuple[int, int]:
	p = parametros(plano)["funcionamento"]
	chave = "5" if tipo_do_dia(plano, dia) == "sabado" and dia.weekday() < 5 else str(dia.weekday())
	ini, fim = p.get(chave) or [300, 1380]
	return int(ini), int(fim)


def turnos_do_dia(plano: dict, dia: date) -> list[tuple[int, int]]:
	tipo = tipo_do_dia(plano, dia)
	if tipo == "util":
		return []
	return [(int(a), int(b)) for a, b in parametros(plano)["turnos_fds"].get(tipo, [])]


# ------------------------------------------------------------------ turno e pausa


def pausa_exigida(minutos: int) -> int:
	"""Acima de 4 h, 15 min; acima de 6 h, 1 h (CLT, art. 71). A pausa não é paga."""
	if minutos > d.JORNADA_INTERVALO_CURTO_ATE_MIN:
		return d.INTERVALO_MINIMO_MIN
	if minutos > d.JORNADA_SEM_INTERVALO_ATE_MIN:
		return d.INTERVALO_CURTO_MIN
	return 0


def celula(inicio: int, fim: int, pausa: int | None = None) -> dict:
	"""Um turno com a pausa no lugar certo: no meio, se não foi escolhida; dentro do turno, se foi."""
	inicio, fim = int(inicio), int(fim)
	if fim <= inicio:
		fim += 24 * 60
	exigida = pausa_exigida(fim - inicio)
	if not exigida:
		return {"i": inicio, "f": fim, "p": None}
	if pausa is None:
		pausa = (
			(inicio + (fim - inicio - exigida) // 2) // 15 * 15
		)  # no meio, em hora "redonda" (de 15 em 15)
	pausa = max(inicio + 15, min(int(pausa), fim - exigida - 15))
	return {"i": inicio, "f": fim, "p": pausa}


def minutos_pagos(c: dict | None) -> int:
	if not c:
		return 0
	return c["f"] - c["i"] - pausa_exigida(c["f"] - c["i"])


def inicio_da_pausa(c: dict | None) -> int | None:
	"""Onde a pausa está: a escolhida (dentro do turno) ou, sem escolha (a tela mudou o horário), no meio."""
	if not c or not pausa_exigida(c["f"] - c["i"]):
		return None
	return celula(c["i"], c["f"], c.get("p"))["p"]


def _presenca(c: dict, minuto: int) -> str | None:
	"""'trabalho', 'pausa' ou None naquele minuto do dia."""
	if not c["i"] <= minuto < c["f"]:
		return None
	pausa = inicio_da_pausa(c)
	if pausa is not None and pausa <= minuto < pausa + pausa_exigida(c["f"] - c["i"]):
		return "pausa"
	return "trabalho"


# ------------------------------------------------------------------ cobertura por hora (PI-04)


def membros_ativos(plano: dict) -> list[dict]:
	return [m for m in plano.get("equipe") or [] if not m.get("retirado")]


def turno_de(plano: dict, membro_id: str, dia: date) -> dict | None:
	return ((plano.get("grade") or {}).get(membro_id) or {}).get(dia.isoformat())


def hoje_de(m: dict) -> list[int]:
	"""O horário de hoje da pessoa (simulações antigas não têm: vale o base)."""
	return list(m.get("hoje") or m["base"])


def restricao(plano: dict, membro_id: str) -> dict:
	"""O que as instruções do gestor dizem da pessoa: folgas_fixas, trabalha, nao_mudar, libera_6h, mudanca_max, base."""
	return (parametros(plano).get("restricoes") or {}).get(membro_id) or {}


def limite_de_mudanca(plano: dict, m: dict) -> int:
	r = restricao(plano, m["id"])
	if r.get("nao_mudar"):
		return 0
	if r.get("mudanca_max") is not None:
		return int(r["mudanca_max"])
	return int(parametros(plano)["mudanca_max"])


def pode_passar_de_4h(plano: dict, m: dict) -> bool:
	"""Até 6 h num dia de semana: quem foi liberado ou, na regra "cobrir", qualquer instrutor (para tapar buraco)."""
	return bool(restricao(plano, m["id"]).get("libera_6h")) or parametros(plano)["regra_6h"] == "cobrir"


def ja_trabalha(m: dict) -> bool:
	"""Quem está na unidade hoje (o horário dele não deve mudar muito); pessoa prevista e estagiário não contam."""
	return m["tipo"] == INSTRUTOR and not m.get("prevista")


def cobertura_do_dia(plano: dict, dia: date) -> list[dict]:
	"""Cada hora das 05h às 22h: quantos instrutores (mínimo e máximo na hora), estagiários, quem está e a situação:
	fora do funcionamento, descoberta (X), parcial (parte da hora sem ninguém), um ou vários (2 ou mais). Minuto sem
	ninguém só porque o instrutor está na pausa não é furo: vira o aviso "pausa sem outro instrutor" (DI-8)."""
	abre, fecha = funcionamento(plano, dia)
	turnos = [(m, t) for m in membros_ativos(plano) if (t := turno_de(plano, m["id"], dia))]
	saida = []
	for hora in HORAS:
		ini, fim = hora * 60, hora * 60 + 60
		if ini < abre or fim > fecha:
			saida.append(
				{
					"hora": hora,
					"situacao": FORA,
					"minimo": 0,
					"maximo": 0,
					"estagiarios": 0,
					"minutos_sem_ninguem": 0,
					"pausa_sem_cobertura": False,
					"quem": [],
				}
			)
			continue
		contagens, sem_ninguem, so_pausa = [], 0, 0
		estagiarios = 0
		for minuto in range(ini, fim):
			presentes = em_pausa = 0
			for m, t in turnos:
				estado = _presenca(t, minuto)
				if m["tipo"] == ESTAGIARIO:
					continue
				if estado == "trabalho":
					presentes += 1
				elif estado == "pausa":
					em_pausa += 1
			contagens.append(presentes)
			if not presentes:
				if em_pausa:
					so_pausa += 1
				else:
					sem_ninguem += 1
		for m, t in turnos:
			if m["tipo"] == ESTAGIARIO and t["i"] < fim and t["f"] > ini:
				estagiarios += 1
		minimo, maximo = min(contagens), max(contagens)
		if sem_ninguem == 60:
			situacao = DESCOBERTA
		elif sem_ninguem:
			situacao = PARCIAL
		elif maximo >= 2:
			situacao = VARIOS
		else:
			situacao = UM
		quem = [m["nome"] for m, t in turnos if t["i"] < fim and t["f"] > ini]
		saida.append(
			{
				"hora": hora,
				"situacao": situacao,
				"minimo": minimo,
				"maximo": maximo,
				"estagiarios": estagiarios,
				"minutos_sem_ninguem": sem_ninguem,
				"pausa_sem_cobertura": so_pausa > 0,
				"quem": quem,
			}
		)
	return saida


def resumo_do_dia(cobertura: list[dict]) -> dict:
	return {
		"horas_descobertas": sum(1 for h in cobertura if h["situacao"] in (DESCOBERTA, PARCIAL)),
		"horas_varios": sum(1 for h in cobertura if h["situacao"] == VARIOS),
		"pausas_sem_cobertura": sum(1 for h in cobertura if h.get("pausa_sem_cobertura")),
	}


# ------------------------------------------------------------------ pendências e avisos (PI-03)


def _p(gravidade: str, tipo: str, mensagem: str, pessoa: str | None = None, dia: date | None = None) -> dict:
	return {
		"gravidade": gravidade,
		"tipo": tipo,
		"mensagem": mensagem,
		"pessoa": pessoa,
		"data": dia.isoformat() if dia else None,
	}


def _dia_br(dia: date) -> str:
	return f"{DIAS[dia.weekday()]} {dia:%d/%m}"


def _lista_horas(horas: list[int]) -> str:
	partes = [f"{h:02d}h" for h in horas]
	return ", ".join(partes[:-1]) + f" e {partes[-1]}" if len(partes) > 1 else partes[0]


def pendencias(plano: dict, coberturas: dict | None = None) -> list[dict]:
	"""Bloqueantes e avisos do DI-4, na ordem de gravidade."""
	p = parametros(plano)
	saida = []
	semanas = semanas_do_mes(plano["ano"], plano["mes"])
	coberturas = coberturas or {dia: cobertura_do_dia(plano, dia) for semana in semanas for dia in semana}
	for m in membros_ativos(plano):
		nome = m["nome"]
		anterior = None
		for semana in semanas:
			folgas = sum(1 for dia in semana if not turno_de(plano, m["id"], dia))
			if folgas < 2:
				saida.append(
					_p(
						BLOQUEANTE,
						"folgas",
						f"{nome}: {folgas} folga(s) na semana de {semana[0]:%d/%m} (5x2 exige 2).",
						m["id"],
						semana[0],
					)
				)
			for dia in semana:
				t = turno_de(plano, m["id"], dia)
				if t:
					total = t["f"] - t["i"]
					if total > d.JORNADA_DIARIA_MAXIMA_MIN:
						saida.append(
							_p(
								BLOQUEANTE,
								"jornada",
								f"{nome}: {duracao(total)} em {_dia_br(dia)} (máximo 8 h).",
								m["id"],
								dia,
							)
						)
					elif (
						total > int(p["teto_aviso"])
						and m["tipo"] == INSTRUTOR
						and tipo_do_dia(plano, dia) == "util"  # o turno do fim de semana já é de 5 h ou 6 h
					):
						saida.append(_aviso_de_horas(plano, m, dia, total))
					if anterior and t["i"] + 1440 - anterior["f"] < d.INTERJORNADA_MIN:
						saida.append(
							_p(
								BLOQUEANTE,
								"interjornada",
								f"{nome}: descanso de {duracao(t['i'] + 1440 - anterior['f'])} antes de {_dia_br(dia)} "
								"(mínimo 11 h).",
								m["id"],
								dia,
							)
						)
				elif dia.weekday() in p["pico"] and dia.month == plano["mes"] and m["tipo"] == INSTRUTOR:
					saida.append(
						_p(
							MEDIO,
							"folga_pico",
							f"{nome}: folga em dia de pico ({_dia_br(dia)}).",
							m["id"],
							dia,
						)
					)
				anterior = t
	_pendencias_do_mes(plano, saida)
	_pendencias_das_pessoas(plano, saida)
	for dia, cobertura in coberturas.items():
		if dia.month != plano["mes"]:
			continue
		descobertas = [h["hora"] for h in cobertura if h["situacao"] in (DESCOBERTA, PARCIAL)]
		if descobertas:
			saida.append(
				_p(
					ALTO,
					"hora_descoberta",
					f"{_dia_br(dia)}: {_lista_horas(descobertas)} sem instrutor.",
					None,
					dia,
				)
			)
		pausas = [h["hora"] for h in cobertura if h.get("pausa_sem_cobertura")]
		if pausas:
			saida.append(
				_p(
					MEDIO,
					"pausa_sem_cobertura",
					f"{_dia_br(dia)}: pausa sem outro instrutor às {_lista_horas(pausas)}.",
					None,
					dia,
				)
			)
		for ini, fim in turnos_do_dia(plano, dia):
			if not any(
				(t := turno_de(plano, m["id"], dia))
				and t["i"] <= ini
				and t["f"] >= fim
				and m["tipo"] == INSTRUTOR
				for m in membros_ativos(plano)
			):
				saida.append(
					_p(
						ALTO,
						"turno_fds",
						f"{_dia_br(dia)}: turno das {hhmm(ini)} às {hhmm(fim)} sem ninguém.",
						None,
						dia,
					)
				)
		_estagiario_sozinho(plano, dia, saida)
	return sorted(saida, key=lambda x: (GRAVIDADES.index(x["gravidade"]), x["data"] or "", x["mensagem"]))


def _estagiario_sozinho(plano: dict, dia: date, saida: list) -> None:
	instrutores = [
		t for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR and (t := turno_de(plano, m["id"], dia))
	]
	for m in membros_ativos(plano):
		t = turno_de(plano, m["id"], dia)
		if m["tipo"] != ESTAGIARIO or not t:
			continue
		sozinho = [
			minuto for minuto in range(t["i"], t["f"]) if not any(_presenca(i, minuto) for i in instrutores)
		]
		if sozinho:
			saida.append(
				_p(
					BLOQUEANTE,
					"estagiario_sozinho",
					f"{m['nome']}: estagiário sem instrutor de CREF a partir de {hhmm(sozinho[0])} em {_dia_br(dia)}.",
					m["id"],
					dia,
				)
			)


def fins_de_semana(plano: dict) -> list[tuple[date, date]]:
	"""Os sábados e domingos (pares) dentro do mês do calendário."""
	return [
		(dia, dia + timedelta(days=1))
		for dia in datas_do_plano(plano)
		if dia.weekday() == 5
		and dia.month == plano["mes"]
		and (dia + timedelta(days=1)).month == plano["mes"]
	]


def contadores(plano: dict) -> dict:
	"""Por pessoa, no mês: folgas, fins de semana livres e trabalhados, sábados e domingos trabalhados, horas pagas."""
	saida = {}
	fds = fins_de_semana(plano)
	for m in membros_ativos(plano):
		dias_mes = [dia for dia in datas_do_plano(plano) if dia.month == plano["mes"]]
		turnos = {dia: turno_de(plano, m["id"], dia) for dia in dias_mes}
		saida[m["id"]] = {
			"folgas": sum(1 for t in turnos.values() if not t),
			"fds_livres": sum(1 for sab, dom in fds if not turnos.get(sab) and not turnos.get(dom)),
			"fds_trabalhados": sum(1 for sab, dom in fds if turnos.get(sab) or turnos.get(dom)),
			"sabados": sum(1 for dia, t in turnos.items() if t and dia.weekday() == 5),
			"domingos": sum(1 for dia, t in turnos.items() if t and dia.weekday() == 6),
			"minutos_pagos": sum(minutos_pagos(t) for t in turnos.values()),
		}
	return saida


def _aviso_de_horas(plano: dict, m: dict, dia: date, total: int) -> dict:
	p = parametros(plano)
	nome = m["nome"]
	if total > int(p["teto_dia"]):
		return _p(
			ALTO,
			"acima_de_6h",
			f"{nome}: {duracao(total)} em {_dia_br(dia)} (no dia de semana o máximo é {duracao(int(p['teto_dia']))}).",
			m["id"],
			dia,
		)
	if not pode_passar_de_4h(plano, m):
		return _p(
			ALTO,
			"sem_liberacao_6h",
			f"{nome}: {duracao(total)} em {_dia_br(dia)}, sem estar liberado para passar de "
			f"{duracao(int(p['teto_aviso']))}.",
			m["id"],
			dia,
		)
	return _p(
		MEDIO,
		"acima_de_4h",
		f"{nome}: {duracao(total)} em {_dia_br(dia)} (passa de {duracao(int(p['teto_aviso']))}; "
		f"pausa de {pausa_exigida(total)} min não paga).",
		m["id"],
		dia,
	)


def _pendencias_das_pessoas(plano: dict, saida: list) -> None:
	"""Por pessoa, no mês: entrada longe da de hoje, horas da semana muito diferentes das de hoje e instrução do gestor
	não cumprida (um aviso por pessoa, com a quantidade de dias)."""
	dias = [dia for semana in semanas_do_mes(plano["ano"], plano["mes"]) for dia in semana]
	semanas = semanas_do_mes(plano["ano"], plano["mes"])
	for m in membros_ativos(plano):
		r = restricao(plano, m["id"])
		hoje = hoje_de(m)
		limite = limite_de_mudanca(plano, m)
		longe, fora_da_instrucao = [], []
		for dia in dias:
			t = turno_de(plano, m["id"], dia)
			util = tipo_do_dia(plano, dia) == "util"
			if ja_trabalha(m) and t and util and abs(t["i"] - hoje[0]) > limite:
				longe.append((dia, abs(t["i"] - hoje[0])))
			if t and dia.weekday() in (r.get("folgas_fixas") or []):
				fora_da_instrucao.append(dia)
			elif not t and dia.weekday() in (r.get("trabalha") or []):
				fora_da_instrucao.append(dia)
			elif r.get("nao_mudar") and t and util and [t["i"], t["f"]] != hoje:
				fora_da_instrucao.append(dia)
		if longe:
			maior = max(x[1] for x in longe)
			saida.append(
				_p(
					MEDIO,
					"mudanca_horario",
					f"{m['nome']}: entrada até {duracao(maior)} longe da de hoje ({hhmm(hoje[0])}) em "
					f"{len(longe)} dia(s) (limite {duracao(limite) if limite else 'não mudar'}).",
					m["id"],
					longe[0][0],
				)
			)
		if fora_da_instrucao:
			saida.append(
				_p(
					ALTO,
					"instrucao",
					f"{m['nome']}: não cumpre a instrução do gestor ({texto_da_restricao(r)}) em "
					f"{len(fora_da_instrucao)} dia(s).",
					m["id"],
					fora_da_instrucao[0],
				)
			)
		if ja_trabalha(m):
			semanal_hoje = 5 * minutos_pagos(celula(*hoje))
			pagos = [
				sum(minutos_pagos(turno_de(plano, m["id"], dia)) for dia in semana) for semana in semanas
			]
			media = sum(pagos) // len(pagos)
			if abs(media - semanal_hoje) >= 120:
				mais = media > semanal_hoje
				saida.append(
					_p(
						MEDIO,
						"horas_desiguais",
						f"{m['nome']}: {duracao(abs(media - semanal_hoje))} {'a mais' if mais else 'a menos'} por semana "
						f"que hoje (média {duracao(media)}; hoje {duracao(semanal_hoje)}).",
						m["id"],
						None,
					)
				)


def texto_da_restricao(r: dict) -> str:
	partes = []
	if r.get("folgas_fixas"):
		partes.append("folga fixa " + ", ".join(DIAS[x] for x in sorted(r["folgas_fixas"])))
	if r.get("trabalha"):
		partes.append("trabalha " + ", ".join(DIAS[x] for x in sorted(r["trabalha"])))
	if r.get("nao_mudar"):
		partes.append("não mudar o horário")
	if r.get("base"):
		partes.append(f"horário {hhmm(r['base'][0])} às {hhmm(r['base'][1])}")
	if r.get("libera_6h"):
		partes.append("pode fazer 6 h")
	if r.get("mudanca_max") is not None and not r.get("nao_mudar"):
		partes.append(f"entrada pode andar até {duracao(int(r['mudanca_max']))}")
	return "; ".join(partes)


def _pendencias_do_mes(plano: dict, saida: list) -> None:
	cont = contadores(plano)
	instrutores = [m for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR]
	if fins_de_semana(plano):
		for m in instrutores:
			if not cont[m["id"]]["fds_livres"]:
				saida.append(
					_p(
						ALTO,
						"fds_livre",
						f"{m['nome']}: nenhum fim de semana inteiro de folga no mês.",
						m["id"],
					)
				)
	trabalhados = [cont[m["id"]]["fds_trabalhados"] for m in instrutores]
	if trabalhados and max(trabalhados) - min(trabalhados) > 1:
		saida.append(
			_p(
				BAIXO,
				"equidade",
				f"Fins de semana trabalhados desiguais: de {min(trabalhados)} a {max(trabalhados)} por pessoa.",
			)
		)


# ------------------------------------------------------------------ custo e DSR (PI-08)


def _reais(valor: Decimal) -> Decimal:
	return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def custo(plano: dict) -> dict:
	"""Previsão (não é folha). Instrutor horista: horas pagas x valor-hora + DSR (horas da semana / dias úteis x
	repousos; os repousos são os do regime mais os feriados da semana fora do domingo). "Como era" usa 1 repouso
	(6x1) nas mesmas horas. Estagiário: a bolsa de referência. Só os dias do mês entram."""
	p = parametros(plano)
	repousos_regime = int(p["repousos"])
	horas = dsr = dsr_antes = bolsas = Decimal(0)
	por_pessoa = {}
	for m in membros_ativos(plano):
		if m["tipo"] == ESTAGIARIO:
			bolsa = Decimal(str(p["bolsa"] or 0))
			bolsas += bolsa
			por_pessoa[m["id"]] = _reais(bolsa)
			continue
		valor_hora = Decimal(str(m.get("valor_hora") or 0))
		total_pessoa = Decimal(0)
		for semana in semanas_do_mes(plano["ano"], plano["mes"]):
			dias = [dia for dia in semana if dia.month == plano["mes"]]
			if not dias:
				continue
			minutos = sum(minutos_pagos(turno_de(plano, m["id"], dia)) for dia in dias)
			valor = Decimal(minutos) / 60 * valor_hora
			feriados = sum(1 for dia in semana if e_feriado(plano, dia) and dia.weekday() != 6)
			proporcao = Decimal(len(dias)) / 7
			for repousos, alvo in ((repousos_regime, "dsr"), (1, "antes")):
				r = repousos + feriados
				parte = valor / Decimal(7 - r) * r * proporcao if 7 - r > 0 else Decimal(0)
				if alvo == "dsr":
					dsr += parte
					total_pessoa += valor + parte
				else:
					dsr_antes += parte
			horas += valor
		por_pessoa[m["id"]] = _reais(total_pessoa)
	return {
		"horas": _reais(horas),
		"dsr": _reais(dsr),
		"bolsas": _reais(bolsas),
		"total": _reais(horas + dsr + bolsas),
		"indice_dsr": float(_reais(dsr / horas * 100)) if horas else 0.0,
		"dsr_6x1": _reais(dsr_antes),
		"indice_dsr_6x1": float(_reais(dsr_antes / horas * 100)) if horas else 0.0,
		"por_pessoa": por_pessoa,
	}


# ------------------------------------------------------------------ avaliação completa (o que a tela mostra)


def avaliar(plano: dict) -> dict:
	semanas = semanas_do_mes(plano["ano"], plano["mes"])
	coberturas = {dia: cobertura_do_dia(plano, dia) for semana in semanas for dia in semana}
	dias = {}
	for dia, cobertura in coberturas.items():
		dias[dia.isoformat()] = {
			"cobertura": cobertura,
			"tipo": tipo_do_dia(plano, dia),
			"pico": dia.weekday() in parametros(plano)["pico"],
			**resumo_do_dia(cobertura),
		}
	no_mes = [v for k, v in dias.items() if date.fromisoformat(k).month == plano["mes"]]
	# onde a tela desenha a pausa de cada turno (a posição é regra: escolhida ou no meio)
	pausas = {
		m["id"]: {
			dia.isoformat(): [inicio_da_pausa(t), pausa_exigida(t["f"] - t["i"])]
			for dia in coberturas
			if (t := turno_de(plano, m["id"], dia)) and inicio_da_pausa(t) is not None
		}
		for m in membros_ativos(plano)
	}
	lista = pendencias(plano, coberturas)
	c = custo(plano)
	return {
		"semanas": [[dia.isoformat() for dia in semana] for semana in semanas],
		"dias": dias,
		"pendencias": lista,
		"pausas": pausas,
		"contadores": contadores(plano),
		"custo": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in c.items() if k != "por_pessoa"}
		| {"por_pessoa": {k: str(v) for k, v in c["por_pessoa"].items()}},
		"totais": {
			"horas_descobertas": sum(v["horas_descobertas"] for v in no_mes),
			"horas_varios": sum(v["horas_varios"] for v in no_mes),
			"pausas_sem_cobertura": sum(v["pausas_sem_cobertura"] for v in no_mes),
			"bloqueantes": sum(1 for x in lista if x["gravidade"] == BLOQUEANTE),
			"avisos": sum(1 for x in lista if x["gravidade"] != BLOQUEANTE),
			"instrutores": sum(1 for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR),
			"estagiarios": sum(1 for m in membros_ativos(plano) if m["tipo"] == ESTAGIARIO),
		},
	}


def resumo_para_comparar(avaliacao: dict) -> dict:
	"""Uma linha da aba Propostas (PI-08)."""
	return {
		**avaliacao["totais"],
		"custo_total": avaliacao["custo"]["total"],
		"indice_dsr": avaliacao["custo"]["indice_dsr"],
	}


# ------------------------------------------------------------------ grade inicial e rodízio sugerido (PI-05)


def grade_padrao(plano: dict, membro: dict) -> dict:
	"""Segunda a sexta no horário base (o estagiário, 5 h no maior movimento); sábado e domingo de folga."""
	saida = {}
	for dia in datas_do_plano(plano):
		if dia.weekday() >= 5 or tipo_do_dia(plano, dia) != "util":
			saida[dia.isoformat()] = None
		else:
			ini, fim = membro["base"]
			saida[dia.isoformat()] = celula(ini, fim)
	return saida


def base_do_estagiario(plano: dict, ordem: int) -> list[int]:
	"""A janela de maior movimento da vez (manhã, noite, manhã...), com a duração do estágio."""
	p = parametros(plano)
	janelas = p["movimento"] or [[360, 660]]
	ini, fim = janelas[ordem % len(janelas)]
	duracao_min = int(p["estagio_minutos"])
	meio = (int(ini) + int(fim)) // 2
	inicio = max(int(ini), meio - duracao_min // 2)
	return [inicio, inicio + duracao_min]


def _descobertas_se(plano: dict, membro_id: str, dia: date, turno: dict | None) -> int:
	grade = plano["grade"].setdefault(membro_id, {})
	antes = grade.get(dia.isoformat())
	grade[dia.isoformat()] = turno
	total = resumo_do_dia(cobertura_do_dia(plano, dia))["horas_descobertas"]
	grade[dia.isoformat()] = antes
	return total


def sugerir_rodizio(plano: dict) -> dict:
	"""Folgas e fins de semana do mês, nesta ordem: as instruções do gestor (folga fixa, dia de trabalho, horário); 2
	folgas por pessoa; os turnos do fim de semana preenchidos; 1 fim de semana livre por pessoa; menos horas
	descobertas; menos folga nos dias de pico; equidade. Depois tapa o que der das horas descobertas mexendo pouco no
	horário (`tapar_buracos`) e põe o estagiário onde há instrutor. Devolve a grade nova."""
	p = parametros(plano)
	instrutores = [m for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR]
	grade = {}
	plano = {**plano, "grade": grade}
	for n, m in enumerate(membros_ativos(plano)):
		if m["tipo"] == ESTAGIARIO and not m.get("base"):
			m = {**m, "base": base_do_estagiario(plano, n)}
		r = restricao(plano, m["id"])
		base = (r.get("base") or hoje_de(m)) if m["tipo"] == INSTRUTOR else m["base"]
		grade[m["id"]] = grade_padrao(plano, {**m, "base": base})
		for dia in datas_do_plano(plano):
			if dia.weekday() in (r.get("folgas_fixas") or []):
				grade[m["id"]][dia.isoformat()] = None
	fds_trab = {m["id"]: 0 for m in instrutores}
	folgas_no_dia: dict[date, int] = {}
	for semana in semanas_do_mes(plano["ano"], plano["mes"]):
		escalados_semana: dict[str, int] = {}
		for dia in [dia for dia in semana if tipo_do_dia(plano, dia) != "util"]:
			usados = set()
			for ini, fim in turnos_do_dia(plano, dia):
				candidatos = [
					m
					for m in instrutores
					if m["id"] not in usados
					and dia.weekday() not in (restricao(plano, m["id"]).get("folgas_fixas") or [])
				]
				if not candidatos:
					break
				# quem tem instrução de trabalhar neste dia; depois quem menos trabalhou fim de semana; quem já está
				# escalado nesta semana vem antes (o mesmo grupo cobre o fim de semana e os outros ficam com ele inteiro
				# livre); depois o horário de hoje mais perto do turno
				escolhido = min(
					candidatos,
					key=lambda m: (
						0 if dia.weekday() in (restricao(plano, m["id"]).get("trabalha") or []) else 1,
						fds_trab[m["id"]] - (1 if m["id"] in escalados_semana else 0),
						abs(hoje_de(m)[0] - ini),
						m["nome"],
					),
				)
				usados.add(escolhido["id"])
				grade[escolhido["id"]][dia.isoformat()] = celula(ini, fim)
				escalados_semana[escolhido["id"]] = escalados_semana.get(escolhido["id"], 0) + 1
		for mid in escalados_semana:
			fds_trab[mid] += 1
		# quem trabalhou no fim de semana folga no meio da semana: fora do pico e onde abre menos furo
		for m in instrutores:
			trabalha = restricao(plano, m["id"]).get("trabalha") or []
			while sum(1 for dia in semana if not grade[m["id"]].get(dia.isoformat())) < 2:
				opcoes = [
					dia
					for dia in semana
					if grade[m["id"]].get(dia.isoformat())
					and tipo_do_dia(plano, dia) == "util"
					and dia.weekday() not in trabalha
				]
				if not opcoes:
					break
				dia = min(
					opcoes,
					key=lambda dia: (
						_descobertas_se(plano, m["id"], dia, None)
						- _descobertas_se(plano, m["id"], dia, grade[m["id"]][dia.isoformat()]),
						1 if dia.weekday() in p["pico"] else 0,
						folgas_no_dia.get(dia, 0),
						-dia.weekday(),
					),
				)
				grade[m["id"]][dia.isoformat()] = None
				folgas_no_dia[dia] = folgas_no_dia.get(dia, 0) + 1
	tapar_buracos(plano)
	for m in membros_ativos(plano):
		if m["tipo"] != ESTAGIARIO:
			continue
		for iso, t in grade[m["id"]].items():
			if t:
				grade[m["id"]][iso] = encaixar_estagiario(plano, date.fromisoformat(iso), t)
	return grade


# ------------------------------------------------------------------ tapar buracos e sugestões (RH, 10/11/2026)


def _sem_ninguem(plano: dict, dia: date, trocas: dict | None = None) -> int:
	"""Minutos do funcionamento sem nenhum instrutor (a pausa conta como presença, como em `cobertura_do_dia`).
	`trocas` = {id: turno ou None} para medir sem gravar."""
	abre, fecha = funcionamento(plano, dia)
	trocas = trocas or {}
	coberto = bytearray(fecha - abre)
	for m in membros_ativos(plano):
		if m["tipo"] != INSTRUTOR:
			continue
		t = trocas[m["id"]] if m["id"] in trocas else turno_de(plano, m["id"], dia)
		if t:
			ini, fim = max(t["i"], abre) - abre, min(t["f"], fecha) - abre
			if fim > ini:
				coberto[ini:fim] = b"\x01" * (fim - ini)
	return len(coberto) - sum(coberto)


def _opcoes_de_horario(plano: dict, m: dict, dia: date, t: dict) -> list[tuple[str, dict]]:
	"""Os horários que a pessoa pode ter no dia sem mudar muito: a entrada anda até o limite (mesma duração) e, se ela
	pode passar de 4 h, o turno cresce até o teto do dia."""
	p = parametros(plano)
	abre, fecha = funcionamento(plano, dia)
	hoje = hoje_de(m)
	limite = limite_de_mudanca(plano, m)
	duracao_t = t["f"] - t["i"]
	saida = []
	for inicio in range(hoje[0] - limite, hoje[0] + limite + 1, 15):
		if inicio != t["i"] and abre <= inicio and inicio + duracao_t <= fecha:
			saida.append(("mover", celula(inicio, inicio + duracao_t)))
	if pode_passar_de_4h(plano, m):
		teto = int(p["teto_dia"])
		for antes in (0, 60, 120):
			for depois in (0, 60, 120):
				i, f = t["i"] - antes, t["f"] + depois
				if (
					(antes or depois)
					and f - i <= teto
					and abre <= i
					and f <= fecha
					and abs(i - hoje[0]) <= limite
				):
					saida.append(("estender", celula(i, f)))
	return saida


def _mexe_no_horario(plano: dict, m: dict) -> bool:
	r = restricao(plano, m["id"])
	return m["tipo"] == INSTRUTOR and not r.get("nao_mudar") and not r.get("base")


def tapar_buracos(plano: dict) -> None:
	"""Nos dias de semana com hora descoberta, move a entrada de quem trabalha (até o limite) ou estende o turno (até
	6 h, para quem pode) enquanto isso diminuir os minutos sem ninguém. Prefere mover a estender e, para estender,
	quem tem menos horas a mais no mês (para não sobrecarregar um só). Muda a grade do plano."""
	extra: dict[str, int] = {}
	for dia in datas_do_plano(plano):
		if dia.month != plano["mes"] or tipo_do_dia(plano, dia) != "util":
			continue
		for _rodada in range(6):
			agora = _sem_ninguem(plano, dia)
			if not agora:
				break
			melhor = None
			for m in membros_ativos(plano):
				t = turno_de(plano, m["id"], dia)
				if not t or not _mexe_no_horario(plano, m):
					continue
				for tipo, novo in _opcoes_de_horario(plano, m, dia, t):
					ganho = agora - _sem_ninguem(plano, dia, {m["id"]: novo})
					if ganho <= 0:
						continue
					acrescimo = (novo["f"] - novo["i"]) - (t["f"] - t["i"])
					chave = (
						-ganho,
						tipo != "mover",
						extra.get(m["id"], 0) + acrescimo,
						abs(novo["i"] - hoje_de(m)[0]),
					)
					if melhor is None or chave < melhor[0]:
						melhor = (chave, m["id"], novo, acrescimo)
			if not melhor:
				break
			_chave, mid, novo, acrescimo = melhor
			plano["grade"][mid][dia.isoformat()] = novo
			extra[mid] = extra.get(mid, 0) + max(0, acrescimo)


def sugestoes(plano: dict, limite: int = 15) -> list[dict]:
	"""Ideias para a simulação aberta, cada uma com o ganho (minutos sem instrutor a menos) e as alterações para o botão
	"Aplicar": mover a entrada (até o limite), estender o turno (quem pode passar de 4 h) e mudar a folga de dia na
	mesma semana. Respeita as instruções do gestor."""
	saida = []
	instrutores = [m for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR]
	pico = parametros(plano)["pico"]
	for semana in semanas_do_mes(plano["ano"], plano["mes"]):
		uteis = [dia for dia in semana if tipo_do_dia(plano, dia) == "util" and dia.month == plano["mes"]]
		for dia in uteis:
			agora = _sem_ninguem(plano, dia)
			if not agora:
				continue
			for m in instrutores:
				t = turno_de(plano, m["id"], dia)
				if not t or not _mexe_no_horario(plano, m):
					continue
				melhores: dict[str, tuple] = {}
				for tipo, novo in _opcoes_de_horario(plano, m, dia, t):
					ganho = agora - _sem_ninguem(plano, dia, {m["id"]: novo})
					if ganho > 0 and (tipo not in melhores or ganho > melhores[tipo][0]):
						melhores[tipo] = (ganho, novo)
				for tipo, (ganho, novo) in melhores.items():
					verbo = "Mudar" if tipo == "mover" else "Estender"
					saida.append(
						{
							"tipo": tipo,
							"texto": f"{verbo} {m['nome']} em {_dia_br(dia)}: {hhmm(t['i'])} às {hhmm(t['f'])} para "
							f"{hhmm(novo['i'])} às {hhmm(novo['f'])}.",
							"ganho": ganho,
							"alteracoes": [{"pessoa": m["id"], "dia": dia.isoformat(), "turno": novo}],
						}
					)
		# a folga para outro dia da mesma semana
		for m in instrutores:
			r = restricao(plano, m["id"])
			fixas, trabalha = r.get("folgas_fixas") or [], r.get("trabalha") or []
			folgas = [
				dia for dia in uteis if not turno_de(plano, m["id"], dia) and dia.weekday() not in fixas
			]
			trabalho = [
				dia for dia in uteis if turno_de(plano, m["id"], dia) and dia.weekday() not in trabalha
			]
			volta = celula(*(r.get("base") or hoje_de(m)))
			for a in folgas:
				for b in trabalho:
					antes = _sem_ninguem(plano, a) + _sem_ninguem(plano, b)
					depois = _sem_ninguem(plano, a, {m["id"]: volta}) + _sem_ninguem(
						plano, b, {m["id"]: None}
					)
					if antes > depois:
						saida.append(
							{
								"tipo": "folga",
								"texto": f"Mudar a folga de {m['nome']} de {_dia_br(a)} para {_dia_br(b)}"
								+ (" (dia de pico)." if b.weekday() in pico else "."),
								"ganho": antes - depois,
								"alteracoes": [
									{"pessoa": m["id"], "dia": a.isoformat(), "turno": volta},
									{"pessoa": m["id"], "dia": b.isoformat(), "turno": None},
								],
							}
						)
	ordem = {"folga": 0, "mover": 1, "estender": 2}
	saida.sort(key=lambda x: (-x["ganho"], ordem[x["tipo"]], x["texto"]))
	for x in saida:
		x["ganho_texto"] = f"tapa {duracao(x['ganho'])} sem instrutor"
	return saida[:limite]


def encaixar_estagiario(plano: dict, dia: date, turno: dict) -> dict:
	"""O estágio do dia (mesma duração) onde há instrutor o tempo todo: com as folgas já postas, a janela base pode
	ficar sem ninguém de CREF. Entre as janelas cobertas, a de mais movimento e a mais perto da base."""
	instrutores = [
		t for m in membros_ativos(plano) if m["tipo"] == INSTRUTOR and (t := turno_de(plano, m["id"], dia))
	]
	ini, fim = funcionamento(plano, dia)
	duracao = turno["f"] - turno["i"]
	coberto = [any(_presenca(t, minuto) for t in instrutores) for minuto in range(ini, fim)]
	movimento = parametros(plano)["movimento"]

	def nota(inicio: int) -> tuple:
		sozinho = sum(1 for minuto in range(inicio, inicio + duracao) if not coberto[minuto - ini])
		no_movimento = sum(max(0, min(inicio + duracao, int(f)) - max(inicio, int(i))) for i, f in movimento)
		return (sozinho, -no_movimento, abs(inicio - turno["i"]))

	opcoes = range(ini, max(ini, fim - duracao) + 1, 15)
	melhor = min(opcoes, key=nota)
	return celula(melhor, melhor + duracao)


# ------------------------------------------------------------------ equipe (DI-13)


def membro(id_: str, nome: str, base: list[int], **campos) -> dict:
	return {
		"id": id_,
		"nome": nome,
		"tipo": campos.get("tipo", INSTRUTOR),
		"employee": campos.get("employee"),
		"prevista": bool(campos.get("prevista")),
		"base": [int(base[0]), int(base[1])],
		"contrato": campos.get("contrato"),
		"valor_hora": campos.get("valor_hora") or 0,
		"retirado": False,
		"hoje": [int(x) for x in (campos.get("hoje") or base)],  # o horário de hoje (para medir a mudança)
	}


def retirar(plano: dict, membro_id: str) -> dict:
	equipe = [{**m, "retirado": True} if m["id"] == membro_id else m for m in plano["equipe"]]
	return {**plano, "equipe": equipe}


def voltar(plano: dict, membro_id: str) -> dict:
	equipe = [{**m, "retirado": False} if m["id"] == membro_id else m for m in plano["equipe"]]
	return {**plano, "equipe": equipe}


def incluir(plano: dict, novo: dict) -> dict:
	if any(m["id"] == novo["id"] for m in plano["equipe"]):
		raise ValueError(f"{novo['nome']} já está na simulação.")
	grade = {**plano["grade"], novo["id"]: grade_padrao(plano, novo)}
	return {**plano, "equipe": [*plano["equipe"], novo], "grade": grade}


def substituir(plano: dict, sai: str, novo: dict, herdar: bool = True) -> dict:
	"""Quem entra fica com os dias e o horário de quem sai (herdar) ou com o horário base dele (os mesmos dias)."""
	antigo = next(m for m in plano["equipe"] if m["id"] == sai)
	dias = plano["grade"].get(sai) or {}
	if herdar:
		grade_nova = dict(dias)
		novo = {**novo, "base": antigo["base"]}
	else:
		grade_nova = {k: (celula(*novo["base"]) if v else None) for k, v in dias.items()}
	plano = retirar(plano, sai)
	if any(m["id"] == novo["id"] for m in plano["equipe"]):
		raise ValueError(f"{novo['nome']} já está na simulação.")
	return {**plano, "equipe": [*plano["equipe"], novo], "grade": {**plano["grade"], novo["id"]: grade_nova}}


# ------------------------------------------------------------------ lista de horários do RH (PI-01)

_HORARIO = re.compile(
	r"^\s*(?P<nome>[^\d]+?)\s*[:\-\u2013]?\s*(?P<i>\d{1,2})(?:[:h](?P<im>\d{2}))?\s*h?\s*(?:às|as|a|ate|até|-|\u2013)\s*"
	r"(?P<f>\d{1,2})(?:[:h](?P<fm>\d{2}))?\s*h?\s*s?\s*$",
	re.IGNORECASE,
)


def sem_acento(texto: str) -> str:
	return "".join(
		c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
	).upper()


def ler_lista(texto: str) -> list[dict]:
	"""A lista que o RH cola ("Álvaro 05:00 às 09:00", "Mayara 05h as 09h", "Marcela - 5 a 9", "Lucio: 7 as 10"),
	com o nome da unidade em linhas de título ("*Vila Velha*:"). Devolve [{"unidade", "nome", "base": [ini, fim]}]."""
	saida, unidade = [], ""
	for linha in re.sub(r"\.{2,}", "\n", texto or "").splitlines():
		linha = linha.strip().strip("•").strip()
		if not linha:
			continue
		achado = _HORARIO.match(linha.replace("*", ""))
		if achado:
			ini = int(achado["i"]) * 60 + int(achado["im"] or 0)
			fim = int(achado["f"]) * 60 + int(achado["fm"] or 0)
			saida.append(
				{"unidade": unidade, "nome": achado["nome"].strip(" :-*" + chr(0x2013)), "base": [ini, fim]}
			)
		elif re.search(r"[A-Za-zÀ-ú]", linha):
			unidade = linha.strip("*: ").split("*")[0].strip(" :")
	return saida


def casar_nome(nome: str, cadastro: list[dict]) -> list[dict]:
	"""Quem do cadastro ({"name", "employee_name"}) tem um nome que começa com o nome da lista."""
	alvo = sem_acento(nome).split()
	if not alvo:
		return []
	return [
		e
		for e in cadastro
		if all(any(p.startswith(a) for p in sem_acento(e["employee_name"]).split()) for a in alvo)
	]
