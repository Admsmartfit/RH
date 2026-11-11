"""Instruções do gestor em texto para refazer a simulação (RH, 10/11/2026). Python puro.

Cada linha tem **quem** e **o que fazer**. O programa entende um conjunto de frases comuns e mostra como entendeu cada
linha; o que não entender, avisa (nunca adivinha). Exemplos:

	o que trabalha às 5:00 folga sempre sábado e domingo
	quem abre a academia folga no fim de semana
	Marcela não muda o horário
	Yago pode fazer 6 h
	Pedro trabalha todo sábado
	Hugo pode mudar até 2 h
	Enzo horário 17:00 às 21:00
	todos podem fazer 6 h

Quem: nome (ou parte dele), "quem entra/trabalha/começa às 5:00", "quem abre a academia" (entra na abertura), "quem
fecha" (sai no fechamento), "quem sai às 22:00", "todos" e "estagiário(s)". O resultado são as restrições por pessoa
(`montagem.restricao`), que o rodízio e os avisos respeitam.
"""

import re

from hrms_secullum_brasil.engine.planejador import montagem as mo

_DIAS = (
	(r"seg(?:unda)?(?:-feira)?s?", 0),
	(r"ter(?:ca|ça)?(?:-feira)?s?", 1),
	(r"qua(?:rta)?(?:-feira)?s?", 2),
	(r"qui(?:nta)?(?:-feira)?s?", 3),
	(r"sex(?:ta)?(?:-feira)?s?", 4),
	(r"sab(?:ado)?s?", 5),
	(r"dom(?:ingo)?s?", 6),
)
_HORA = r"(\d{1,2})(?:[:h](\d{2}))?(?:\s*h(?:s|oras)?)?"
_VERBOS_QUEM = r"(?:entra|trabalha|comeca|chega|abre|inicia)"
_QUEM_ENTRA = re.compile(
	rf"\b(?:quem|o que|a que|os que|as que|aquele que|aquela que|o professor que|a professora que|o instrutor que|"
	rf"a instrutora que|o prof que)\s+{_VERBOS_QUEM}\s+(?:a|as|às|de|das)?\s*{_HORA}"
)
_QUEM_SAI = re.compile(
	rf"\b(?:quem|o que|a que|os que|as que|aquele que|aquela que)\s+(?:sai|termina|fecha)\s+(?:a|as|às)?\s*{_HORA}"
)
_QUEM_ABRE = re.compile(
	r"\b(?:quem|o que|a que|aquele que|aquela que)\s+abre(?:\s+a\s+(?:academia|unidade))?\b"
)
_QUEM_FECHA = re.compile(
	r"\b(?:quem|o que|a que|aquele que|aquela que)\s+fecha(?:\s+a\s+(?:academia|unidade))?\b"
)
_TODOS = re.compile(r"\b(?:todos|todas|todo mundo|toda a equipe|todos os instrutores)\b")
_ESTAGIO = re.compile(r"\bestagiari[oa]s?\b")
_INTERVALO = re.compile(rf"{_HORA}\s*(?:as|às|a|ate|até|-)\s*{_HORA}")


def _limpo(texto: str) -> str:
	return mo.sem_acento(texto or "").lower()


def _minutos(h, m) -> int:
	return int(h) * 60 + int(m or 0)


def _dias(texto: str) -> list[int]:
	dias = set()
	if re.search(r"\bfim de semana\b|\bfins de semana\b|\bfds\b", texto):
		dias |= {5, 6}
	for padrao, n in _DIAS:
		if re.search(rf"\b{padrao}\b", texto):
			dias.add(n)
	return sorted(dias)


def _quem(texto: str, plano: dict) -> tuple[list[dict], str, str]:
	"""(pessoas, como foram achadas, o resto da linha sem o "quem")."""
	instrutores = [m for m in mo.membros_ativos(plano) if m["tipo"] == mo.INSTRUTOR]
	abre = min(
		(mo.funcionamento(plano, dia)[0] for dia in mo.datas_do_plano(plano) if dia.weekday() < 5),
		default=300,
	)
	fecha = max(
		(mo.funcionamento(plano, dia)[1] for dia in mo.datas_do_plano(plano) if dia.weekday() < 5),
		default=1380,
	)
	if achado := _QUEM_ENTRA.search(texto):
		hora = _minutos(achado.group(1), achado.group(2))
		pessoas = [m for m in instrutores if mo.hoje_de(m)[0] == hora]
		return pessoas, f"quem entra às {mo.hhmm(hora)}", texto[: achado.start()] + texto[achado.end() :]
	if achado := _QUEM_SAI.search(texto):
		hora = _minutos(achado.group(1), achado.group(2))
		pessoas = [m for m in instrutores if mo.hoje_de(m)[1] == hora]
		return pessoas, f"quem sai às {mo.hhmm(hora)}", texto[: achado.start()] + texto[achado.end() :]
	if achado := _QUEM_ABRE.search(texto):
		pessoas = [m for m in instrutores if mo.hoje_de(m)[0] == abre]
		return pessoas, f"quem abre ({mo.hhmm(abre)})", texto[: achado.start()] + texto[achado.end() :]
	if achado := _QUEM_FECHA.search(texto):
		pessoas = [m for m in instrutores if mo.hoje_de(m)[1] == fecha]
		return pessoas, f"quem fecha ({mo.hhmm(fecha)})", texto[: achado.start()] + texto[achado.end() :]
	if achado := _TODOS.search(texto):
		return instrutores, "todos os instrutores", texto[: achado.start()] + texto[achado.end() :]
	if achado := _ESTAGIO.search(texto):
		estagiarios = [m for m in mo.membros_ativos(plano) if m["tipo"] == mo.ESTAGIARIO]
		return estagiarios, "os estagiários", texto[: achado.start()] + texto[achado.end() :]
	# pelo nome: quantas palavras do começo do nome estão na linha ("Pedro Henrique" acha o PEDRO HENRIQUE LIMA);
	# vale quem tiver mais, se for uma pessoa só
	palavras = set(re.findall(r"[a-z]+", texto))
	pontos = {}
	for m in mo.membros_ativos(plano):
		n = 0
		for parte in _limpo(m["nome"]).split():
			if parte not in palavras:
				break
			n += 1
		if n:
			pontos[m["id"]] = (n, m)
	if pontos:
		maior = max(n for n, _m in pontos.values())
		achados = [m for n, m in pontos.values() if n == maior]
		if len(achados) == 1:
			return achados, achados[0]["nome"], _sem_nome(texto, achados[0])
		return [], "mais de uma pessoa com esse nome: escreva o sobrenome", texto
	return [], "", texto


def _sem_nome(texto: str, m: dict) -> str:
	for parte in _limpo(m["nome"]).split():
		texto = re.sub(rf"\b{re.escape(parte)}\b", " ", texto)
	return texto


def _acao(resto: str) -> tuple[dict, list[str]]:
	"""(restrição, o que foi entendido) do resto da linha."""
	r, entendido = {}, []
	nega = re.search(r"\bnao\s+(?:pode\s+)?trabalha[rm]?\b|\bnunca\s+trabalha", resto)
	if re.search(r"\bfolga", resto) or nega:
		dias = _dias(resto)
		if dias:
			r["folgas_fixas"] = dias
			entendido.append("folga fixa " + ", ".join(mo.DIAS[d] for d in dias))
	elif re.search(r"\btrabalha[rm]?\b", resto):
		dias = _dias(resto)
		if dias:
			r["trabalha"] = dias
			entendido.append("trabalha " + ", ".join(mo.DIAS[d] for d in dias))
	if re.search(r"\bnao\s+(?:pode\s+)?muda[r]?\b|\bmante[mr]\b|\bmesmo horario\b|\bnao\s+mexe[r]?\b", resto):
		r["nao_mudar"] = True
		entendido.append("não mudar o horário")
	elif achado := re.search(r"\bmudar?\s+(?:ate|no maximo)\s+(\d{1,2})\s*h", resto):
		r["mudanca_max"] = int(achado.group(1)) * 60
		entendido.append(f"entrada pode andar até {achado.group(1)} h")
	if re.search(r"\b(?:6|seis)\s*(?:h|hs|horas)\b", resto) and re.search(r"\bpode", resto):
		r["libera_6h"] = True
		entendido.append("pode fazer 6 h")
	if "nao_mudar" not in r and (
		achado := re.search(rf"\bhorario\s+(?:de\s+|das\s+)?{_INTERVALO.pattern}", resto)
	):
		ini, fim = _minutos(achado.group(1), achado.group(2)), _minutos(achado.group(3), achado.group(4))
		if fim > ini:
			r["base"] = [ini, fim]
			entendido.append(f"horário {mo.hhmm(ini)} às {mo.hhmm(fim)}")
	return r, entendido


def ler(texto: str, plano: dict) -> dict:
	"""{"linhas": [{"linha", "ok", "quem", "pessoas", "entendido"}], "restricoes": {id: {...}}}. Linha que não diz
	quem ou o que fazer volta com `ok` falso e o motivo."""
	linhas, restricoes = [], {}
	for original in (texto or "").splitlines():
		if not original.strip():
			continue
		limpo = _limpo(original)
		pessoas, quem, resto = _quem(limpo, plano)
		r, entendido = _acao(resto)
		ok = bool(pessoas and entendido)
		if not pessoas:
			motivo = quem or "não achei de quem é: escreva o nome ou 'quem entra às 05:00'"
		elif not entendido:
			motivo = "não entendi o que fazer (folga, trabalha, não mudar, pode fazer 6 h, horário…)"
		else:
			motivo = ""
		linhas.append(
			{
				"linha": original.strip(),
				"ok": ok,
				"quem": quem if pessoas else "",
				"pessoas": [m["nome"] for m in pessoas],
				"entendido": "; ".join(entendido) if ok else motivo,
			}
		)
		if ok:
			for m in pessoas:
				atual = restricoes.setdefault(m["id"], {})
				for chave, valor in r.items():
					if chave in ("folgas_fixas", "trabalha"):
						atual[chave] = sorted(set(atual.get(chave) or []) | set(valor))
					else:
						atual[chave] = valor
	return {"linhas": linhas, "restricoes": restricoes}
