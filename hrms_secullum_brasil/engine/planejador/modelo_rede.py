"""Modelo de escala da rede (docs/PRD-modelo-rede.md): encaixar os instrutores da unidade nas vagas do modelo
(ex.: o da Smart, 7 professores e folgas num ciclo de 3 semanas) e mostrar o que muda para cada um.

Puro: recebe o modelo e o plano (o mesmo formato de `montagem.py`) e devolve a grade no modelo e a comparação. Só
simulação: quem grava (uma nova simulação) é `apuracao/modelo_rede.py`.

Modelo: {"nome", "inicio_ciclo": "AAAA-MM-DD" (a segunda-feira da semana 1), "vagas": [{"vaga": "Prof. 1",
"inicio": 300, "fim": 540, "folgas": [[5, 6], [4, 6], [5, 6]]}]} — `folgas[n]` são os dias de folga (0 = segunda) na
semana n+1 do ciclo; todas as vagas têm o mesmo número de semanas.
"""

import re
import unicodedata
from datetime import date, timedelta

from hrms_secullum_brasil.engine.planejador import montagem as mo

CODIGOS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}
NOMES = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
SEM_VAGA = 10**6  # custo de deixar alguém sem vaga: encaixar o máximo de pessoas vem antes da menor mudança

# os slides "Análise de cenários" da Smart (semanas 01 a 03, 7 professores)
MODELO_SMART = {
	"nome": "Modelo Smart (3 semanas)",
	"inicio_ciclo": "2026-12-14",
	"vagas": [
		{"vaga": "Prof. 1", "inicio": 300, "fim": 540, "folgas": [[5, 6], [4, 6], [5, 6]]},
		{"vaga": "Prof. 2", "inicio": 360, "fim": 600, "folgas": [[4, 6], [5, 6], [4, 5]]},
		{"vaga": "Prof. 3", "inicio": 600, "fim": 840, "folgas": [[5, 6], [5, 6], [5, 6]]},
		{"vaga": "Prof. 4", "inicio": 840, "fim": 1080, "folgas": [[5, 6], [5, 6], [5, 6]]},
		{"vaga": "Prof. 5", "inicio": 1020, "fim": 1260, "folgas": [[4, 6], [4, 5], [4, 6]]},
		{"vaga": "Prof. 6", "inicio": 1080, "fim": 1320, "folgas": [[5, 6], [4, 6], [5, 6]]},
		{"vaga": "Prof. 7", "inicio": 1140, "fim": 1380, "folgas": [[4, 5], [5, 6], [4, 6]]},
	],
}


# ------------------------------------------------------------------ o modelo


def ler_dias(texto: str) -> list[int]:
	"""'sex, sáb' → [4, 5]. Aceita vírgula, espaço, barra ou 'e'; sem acento e sem diferença de maiúsculas."""
	limpo = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
	dias = []
	for parte in re.split(r"[\s,;/]+|\be\b", limpo):
		parte = parte.strip()[:3]
		if not parte:
			continue
		if parte not in CODIGOS:
			raise ValueError(f"Dia desconhecido: {parte!r} (use seg, ter, qua, qui, sex, sáb, dom).")
		if CODIGOS[parte] not in dias:
			dias.append(CODIGOS[parte])
	return sorted(dias)


def texto_dias(dias: list[int]) -> str:
	return ", ".join(NOMES[d] for d in sorted(dias))


def ciclo(modelo: dict) -> int:
	return max((len(v["folgas"]) for v in modelo["vagas"]), default=0)


def erros_do_modelo(modelo: dict) -> list[str]:
	"""O que impede usar o modelo: sem vagas, horário invertido, semanas faltando, folga repetida."""
	erros = []
	if not modelo.get("vagas"):
		return ["O modelo precisa de pelo menos uma vaga."]
	semanas = ciclo(modelo)
	if not semanas:
		erros.append("Informe as folgas de pelo menos uma semana.")
	for v in modelo["vagas"]:
		if not 0 <= v["inicio"] < v["fim"] <= 24 * 60:
			erros.append(f"{v['vaga']}: a saída precisa ser depois da entrada.")
		if len(v["folgas"]) != semanas:
			erros.append(f"{v['vaga']}: preencha as folgas das {semanas} semanas do ciclo.")
	nomes = [v["vaga"] for v in modelo["vagas"]]
	for nome in sorted({n for n in nomes if nomes.count(n) > 1}):
		erros.append(f"Vaga repetida: {nome}.")
	return erros


def avisos_do_modelo(modelo: dict) -> list[str]:
	"""Não impede: semana do modelo com folga diferente de 2 (5x2) e dia da semana sem ninguém."""
	avisos = []
	for v in modelo["vagas"]:
		for n, folgas in enumerate(v["folgas"]):
			if len(folgas) != 2:
				avisos.append(f"{v['vaga']}: {len(folgas)} folga(s) na semana {n + 1} (no 5x2 são 2).")
	for n in range(ciclo(modelo)):
		for d in range(7):
			if all(d in (v["folgas"][n] if n < len(v["folgas"]) else []) for v in modelo["vagas"]):
				avisos.append(f"Semana {n + 1}: ninguém trabalha {NOMES[d]}.")
	return avisos


def semana_do_ciclo(modelo: dict, segunda: date) -> int:
	"""Qual semana do ciclo (0, 1, 2...) vale na semana que começa nesta segunda; o ciclo continua de um mês para o
	outro, contado a partir de `inicio_ciclo`."""
	inicio = date.fromisoformat(modelo.get("inicio_ciclo") or "2026-12-14")
	inicio -= timedelta(days=inicio.weekday())
	return ((segunda - inicio).days // 7) % max(1, ciclo(modelo))


# ------------------------------------------------------------------ encaixe (pelo horário mais perto)


def mudanca_de_horario(base: list[int], vaga: dict) -> int:
	"""Minutos que a entrada e a saída andam: de 09-13 para 10-14 são 120."""
	return abs(base[0] - vaga["inicio"]) + abs(base[1] - vaga["fim"])


def encaixar(modelo: dict, equipe: list[dict], fixos: dict | None = None) -> dict:
	"""{id do instrutor: índice da vaga ou None (reforço)}: o máximo de pessoas nas vagas e, entre esses jeitos, a menor
	mudança de horário somada. `fixos` = o que o gestor escolheu à mão ({id: índice ou None}) e não muda. Só os
	instrutores ativos; estagiários não ocupam vaga."""
	fixos = {k: v for k, v in (fixos or {}).items() if v is None or 0 <= int(v) < len(modelo["vagas"])}
	pessoas = [m for m in mo.membros_ativos({"equipe": equipe}) if m["tipo"] == mo.INSTRUTOR]
	presos = {int(v) for k, v in fixos.items() if v is not None and any(p["id"] == k for p in pessoas)}
	livres = [p for p in pessoas if p["id"] not in fixos]
	vagas = [n for n in range(len(modelo["vagas"])) if n not in presos]
	# programação dinâmica: pessoa a pessoa, o conjunto de vagas já usadas (no máximo algumas dezenas de vagas)
	melhor: dict[int, tuple[int, list]] = {0: (0, [])}
	for p in livres:
		proximo: dict[int, tuple[int, list]] = {}
		for usadas, (custo, escolhas) in melhor.items():
			opcoes = [(SEM_VAGA, None)] + [
				(mudanca_de_horario(p["base"], modelo["vagas"][v]), v) for v in vagas if not usadas >> v & 1
			]
			for extra, v in opcoes:
				chave = usadas | (1 << v) if v is not None else usadas
				total = custo + extra
				if chave not in proximo or total < proximo[chave][0]:
					proximo[chave] = (total, [*escolhas, v])
		melhor = proximo
	_custo, escolhas = min(melhor.values(), key=lambda x: x[0])
	saida = {p["id"]: v for p, v in zip(livres, escolhas, strict=True)}
	for k, v in fixos.items():
		if any(p["id"] == k for p in pessoas):
			saida[k] = None if v is None else int(v)
	return saida


# ------------------------------------------------------------------ a grade no modelo


def aplicar(plano: dict, modelo: dict, encaixe: dict, vagas_previstas: bool = False) -> dict:
	"""O plano com a escala do modelo: quem tem vaga passa ao horário da vaga e às folgas da semana do ciclo; no fim de
	semana e no feriado, quem trabalha pega os turnos do dia (o de entrada mais perto da vaga). Reforço (sem vaga) e
	estagiário ficam com a escala de antes; o estagiário vai para a janela com instrutor presente. Vaga sem ninguém fica
	vazia (as horas dela aparecem com X) ou, com `vagas_previstas`, vira pessoa prevista (a contratar)."""
	equipe = [dict(m) for m in plano.get("equipe") or []]
	ocupadas = {v for v in encaixe.values() if v is not None}
	if vagas_previstas:
		valores = [m.get("valor_hora") or 0 for m in equipe if m.get("employee") and m.get("valor_hora")]
		media = round(sum(valores) / len(valores), 2) if valores else 0
		for n, v in enumerate(modelo["vagas"]):
			if n not in ocupadas:
				novo = mo.membro(
					f"vaga-{n + 1}",
					f"{v['vaga']} (a contratar)",
					[v["inicio"], v["fim"]],
					prevista=True,
					valor_hora=media,
				)
				equipe.append(novo)
				encaixe = {**encaixe, novo["id"]: n}
	novo_plano = {
		**plano,
		"equipe": equipe,
		"grade": {k: dict(v) for k, v in (plano.get("grade") or {}).items()},
	}
	grade = novo_plano["grade"]
	com_vaga = {mid: n for mid, n in encaixe.items() if n is not None}
	for m in equipe:
		if m["id"] in com_vaga:
			v = modelo["vagas"][com_vaga[m["id"]]]
			m["base"] = [v["inicio"], v["fim"]]
			grade[m["id"]] = {}
	for semana in mo.semanas_do_mes(plano["ano"], plano["mes"]):
		n = semana_do_ciclo(modelo, semana[0])
		for dia in semana:
			trabalham = []
			for mid, vaga in com_vaga.items():
				v = modelo["vagas"][vaga]
				folgas = v["folgas"][n] if n < len(v["folgas"]) else []
				if dia.weekday() in folgas:
					grade[mid][dia.isoformat()] = None
				else:
					trabalham.append((mid, v))
			turnos = mo.turnos_do_dia(novo_plano, dia)
			if not turnos:
				for mid, v in trabalham:
					grade[mid][dia.isoformat()] = mo.celula(v["inicio"], v["fim"])
				continue
			# fim de semana ou feriado: cada turno para quem tem a vaga com entrada mais perto; quem sobra folga
			restantes = list(trabalham)
			for mid, _v in trabalham:
				grade[mid][dia.isoformat()] = None
			for ini, fim in turnos:
				if not restantes:
					break
				mid, v = min(restantes, key=lambda x: (abs(x[1]["inicio"] - ini), x[1]["inicio"]))
				restantes.remove((mid, v))
				grade[mid][dia.isoformat()] = mo.celula(ini, fim)
	for m in mo.membros_ativos(novo_plano):
		if m["tipo"] != mo.ESTAGIARIO:
			continue
		for iso, t in (grade.get(m["id"]) or {}).items():
			if t and mo.tipo_do_dia(novo_plano, date.fromisoformat(iso)) == "util":
				grade[m["id"]][iso] = mo.encaixar_estagiario(novo_plano, date.fromisoformat(iso), t)
	return novo_plano


# ------------------------------------------------------------------ comparação (o que muda para cada um)


def _par(t: dict | None) -> list[int] | None:
	return [t["i"], t["f"]] if t else None


def _texto(par) -> str:
	return f"{mo.hhmm(par[0])} às {mo.hhmm(par[1])}" if par else "Folga"


def comparar(atual: dict, no_modelo: dict, modelo: dict, encaixe: dict) -> dict:
	"""Atual contra o modelo: por pessoa (vaga, horário de antes e depois, dias que mudam), a lista dia a dia e os totais dos
	dois (horas descobertas, 2 ou mais, bloqueantes, custo)."""
	dias = [dia for dia in mo.datas_do_plano(atual) if dia.month == atual["mes"]]
	antes = {m["id"]: m for m in atual.get("equipe") or []}
	encaixe = {**encaixe} | {
		m["id"]: int(m["id"].split("-")[1]) - 1
		for m in no_modelo.get("equipe") or []
		if m["id"].startswith("vaga-") and m["id"] not in encaixe
	}
	pessoas, mudancas = [], []
	for m in mo.membros_ativos(no_modelo):
		vaga = encaixe.get(m["id"])
		anterior = antes.get(m["id"])
		dias_mudados = 0
		for dia in dias:
			de = _par(mo.turno_de(atual, m["id"], dia)) if anterior else None
			para = _par(mo.turno_de(no_modelo, m["id"], dia))
			if de != para:
				dias_mudados += 1
				mudancas.append(
					{
						"pessoa": m["nome"],
						"id": m["id"],
						"data": dia.isoformat(),
						"de": _texto(de),
						"para": _texto(para),
						"folga_nova": de is not None and para is None,
						"trabalho_novo": de is None and para is not None,
					}
				)
		if m["tipo"] == mo.ESTAGIARIO:
			situacao = "estagiario"
		elif vaga is None:
			situacao = "reforco"
		elif not anterior:
			situacao = "a_contratar"
		else:
			situacao = "vaga"
		base_antes = anterior["base"] if anterior else None
		pessoas.append(
			{
				"id": m["id"],
				"nome": m["nome"],
				"situacao": situacao,
				"vaga": modelo["vagas"][vaga]["vaga"] if vaga is not None else None,
				"indice_vaga": vaga,
				"horario_antes": _texto(base_antes) if base_antes else "",
				"horario_modelo": _texto(m["base"]),
				"muda_horario": bool(base_antes) and list(base_antes) != list(m["base"]),
				"mudanca_minutos": mudanca_de_horario(base_antes, modelo["vagas"][vaga])
				if base_antes and vaga is not None
				else 0,
				"dias_mudados": dias_mudados,
			}
		)
	ocupadas = {v for v in encaixe.values() if v is not None}
	vazias = [
		{"vaga": v["vaga"], "horario": _texto([v["inicio"], v["fim"]])}
		for n, v in enumerate(modelo["vagas"])
		if n not in ocupadas
	]
	aval_atual, aval_modelo = mo.avaliar(atual), mo.avaliar(no_modelo)
	ordem = {"vaga": 0, "a_contratar": 1, "reforco": 2, "estagiario": 3}
	pessoas.sort(
		key=lambda p: (ordem[p["situacao"]], p["indice_vaga"] if p["indice_vaga"] is not None else 99)
	)
	return {
		"pessoas": pessoas,
		"vagas_vazias": vazias,
		"mudancas": mudancas,
		"totais": {
			"atual": mo.resumo_para_comparar(aval_atual),
			"modelo": mo.resumo_para_comparar(aval_modelo),
			"dias_mudados": len(mudancas),
			"pessoas_com_horario_novo": sum(1 for p in pessoas if p["muda_horario"]),
		},
		"avaliacao_atual": aval_atual,
		"avaliacao_modelo": aval_modelo,
	}


def ciclo_no_mes(modelo: dict, ano: int, mes: int) -> list[dict]:
	"""Para a tela: cada semana do mês e qual semana do modelo vale nela."""
	return [
		{"inicio": semana[0].isoformat(), "semana_modelo": semana_do_ciclo(modelo, semana[0]) + 1}
		for semana in mo.semanas_do_mes(ano, mes)
	]
