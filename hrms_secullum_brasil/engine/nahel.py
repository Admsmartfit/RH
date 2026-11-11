"""Ajuda Nahel: guias passo a passo e busca sem IA (docs/PRD-ajuda-nahel.md, NH-E1). Python puro.

- Um guia é um arquivo Markdown em `nahel/guias/` com cabeçalho (`id`, `titulo`, `publico`, `tema`,
  `palavras_chave`, `manual`, `telas`) e quatro seções: Objetivo, Pré-requisitos, Passo a passo (`### nome` com
  "O que fazer" e "Onde acessar") e Como testar ("Ação" e "Resultado esperado").
- Marcações no texto: `[[painel:escalas|Escalas]]`, `[[desk:Configuracao Secullum]]`,
  `[[desk-lista:Regra Envio WhatsApp]]`, `{{verificar:chave}}` e `**negrito**`. A tela recebe os trechos já
  separados (nada de interpretar texto no frontend).
- Busca: normalização (minúsculas, sem acento, sem palavras vazias), sinônimos do domínio, vários assuntos numa
  frase, pontuação por título > palavras-chave > tema > texto; nada acima do mínimo = fora do escopo; muitos guias
  parecidos do mesmo tema = tema amplo (lista para escolher). Nenhuma IA.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

PUBLICOS = ("RH", "Gestor", "TI")
SECOES = ("Objetivo", "Pré-requisitos", "Passo a passo", "Como testar")
DESTINOS = ("painel", "desk", "desk-lista")
NOTA_MINIMA = 4
MAX_POR_TOPICO = 3
MENSAGEM_FORA = (
	"Minha especialidade é o sistema de RH e ponto (Secullum, escalas, WhatsApp, termo, folha, estágio e segurança "
	"do trabalho). Não encontrei um guia para isso: reformule a pergunta com o nome da tela ou da tarefa, ou veja as "
	"sugestões abaixo."
)
AVISO_JURIDICO = (
	"As regras trabalhistas descritas são as que o sistema aplica; não substituem a orientação do jurídico."
)

# o que cada verificação automática confere (a implementação, só leitura, fica em apuracao/nahel.py; há teste)
VERIFICACOES = {
	"secullum_ativo": "Integração com o Secullum ligada e com as credenciais",
	"secullum_ultima_coleta": "A última coleta de batidas deu certo",
	"secullum_conferencia": "Conferência recente com o Secullum",
	"whatsapp_conexao": "Evolution API configurada (URL, chave e instância)",
	"whatsapp_modo": "Posição do envio de WhatsApp (Desligado, Teste, Ligado)",
	"whatsapp_numero_teste": "Número de teste do WhatsApp preenchido",
	"whatsapp_unidade_liberada": "Alguma unidade liberada para o envio automático",
	"whatsapp_aceites": "Colaboradores que aceitaram receber WhatsApp",
	"gestor_da_unidade": "Gestor da unidade cadastrado",
	"fechamento_folha": "Dia de fechamento da folha nas empresas",
	"cct_vigente": "Regra Sindical (CCT) vigente",
	"regime_jornada": "Regime de jornada em vigor hoje",
	"email_padrao": "Conta de e-mail padrão para envio",
	"termo_credenciamento": "Termo de credenciamento de prestador vigente",
	"cobertura_regras": "Regras de WhatsApp da cobertura de faltas ligadas",
	"fila_reapuracao": "Fila de reapuração andando",
	"feriados_do_ano": "Feriados do ano cadastrados",
}

PALAVRAS_VAZIAS = {
	"a",
	"o",
	"as",
	"os",
	"um",
	"uma",
	"de",
	"da",
	"do",
	"das",
	"dos",
	"em",
	"no",
	"na",
	"nos",
	"nas",
	"para",
	"pra",
	"por",
	"com",
	"como",
	"que",
	"eu",
	"meu",
	"minha",
	"se",
	"ao",
	"aos",
	"e",
	"ou",
	"onde",
	"qual",
	"quais",
	"faco",
	"fazer",
	"posso",
	"quero",
	"preciso",
	"ajuda",
	"sobre",
	"isso",
	"este",
	"esta",
	"nahel",
	"sistema",
	"tela",
}
# sinônimo → termo do catálogo
SINONIMOS = {
	"zap": "whatsapp",
	"whats": "whatsapp",
	"wpp": "whatsapp",
	"evolution": "whatsapp",
	"mensagem": "whatsapp",
	"mensagens": "whatsapp",
	"relogio": "ponto",
	"batida": "ponto",
	"batidas": "ponto",
	"marcacao": "ponto",
	"marcacoes": "ponto",
	"payroll": "folha",
	"salario": "folha",
	"pagamento": "folha",
	"convencao": "cct",
	"sindicato": "cct",
	"sindical": "cct",
	"instrutor": "horista",
	"instrutores": "horista",
	"personal": "talentos",
	"pj": "talentos",
	"prestador": "talentos",
	"prestadores": "talentos",
	"substituto": "cobertura",
	"substituicao": "cobertura",
	"falta": "cobertura",
	"turnos": "escala",
	"turno": "escala",
	"escalas": "escala",
	"5x2": "regime",
	"ec": "regime",
	"jornada": "jornada",
	"horario": "jornada",
	"horarios": "jornada",
	"estagiario": "estagio",
	"estagiaria": "estagio",
	"tce": "estagio",
	"epis": "epi",
	"uniforme": "epi",
	"exame": "aso",
	"admissional": "aso",
	"periodico": "aso",
	"docker": "ambiente",
	"bench": "ambiente",
	"servidor": "ambiente",
	"integracao": "secullum",
	"api": "secullum",
	"erro": "inconsistencia",
	"erros": "inconsistencia",
	"pendencia": "inconsistencia",
	"pendencias": "inconsistencia",
	"inconsistencias": "inconsistencia",
	"ocorrencia": "termo",
	"ocorrencias": "termo",
	"fechar": "fechamento",
	"fecha": "fechamento",
	"mes": "fechamento",
	"atestados": "atestado",
	"ferias": "licenca",
	"licencas": "licenca",
	"afastamento": "licenca",
	"teste": "testar",
	"testes": "testar",
	"liberar": "liberar",
	"unidade": "unidade",
	"unidades": "unidade",
	"empresa": "unidade",
	"empresas": "unidade",
	"loja": "unidade",
	"filial": "unidade",
}
_DIVISORES = re.compile(r"\s+e\s+|[,;]|\s+depois\s+|\s+tamb[eé]m\s+|\s+mais\s+", re.IGNORECASE)
_MARCAS = re.compile(
	r"\[\[(painel|desk|desk-lista):([^\]|]+)(?:\|([^\]]+))?\]\]|\{\{verificar:([a-z0-9_]+)\}\}|\*\*(.+?)\*\*"
)


# ------------------------------------------------------------------ modelo


@dataclass(frozen=True)
class Trecho:
	tipo: str  # texto | negrito | link | verificacao
	valor: str
	destino: str = ""  # painel | desk | desk-lista (link)
	alvo: str = ""  # rota do painel ou nome do DocType (link); chave (verificação)


@dataclass(frozen=True)
class Item:
	trechos: tuple[Trecho, ...]


@dataclass(frozen=True)
class Passo:
	chave: str
	nome: str
	o_que_fazer: tuple[Trecho, ...]
	onde: tuple[Trecho, ...]


@dataclass(frozen=True)
class Guia:
	id: str
	titulo: str
	publico: tuple[str, ...]
	tema: str
	palavras_chave: tuple[str, ...]
	manual: str
	telas: tuple[str, ...]
	objetivo: tuple[Trecho, ...]
	prerequisitos: tuple[Item, ...]
	passos: tuple[Passo, ...]
	teste_acao: tuple[Trecho, ...]
	teste_resultado: tuple[Trecho, ...]
	_texto: str = field(default="", repr=False, compare=False)

	def trechos(self) -> list[Trecho]:
		saida = [*self.objetivo, *self.teste_acao, *self.teste_resultado]
		for item in self.prerequisitos:
			saida.extend(item.trechos)
		for passo in self.passos:
			saida.extend((*passo.o_que_fazer, *passo.onde))
		return saida

	def links(self) -> list[Trecho]:
		return [t for t in self.trechos() if t.tipo == "link"]

	def verificacoes(self) -> list[str]:
		return list(dict.fromkeys(t.alvo for t in self.trechos() if t.tipo == "verificacao"))


# ------------------------------------------------------------------ leitura do arquivo


def slug(texto: str) -> str:
	return re.sub(r"[^a-z0-9]+", "-", sem_acento(texto).lower()).strip("-")


def sem_acento(texto: str) -> str:
	return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()


def trechos(texto: str) -> tuple[Trecho, ...]:
	"""Texto com marcações → trechos (texto, negrito, link, verificação)."""
	saida: list[Trecho] = []
	pos = 0
	for m in _MARCAS.finditer(texto or ""):
		if m.start() > pos:
			saida.append(Trecho("texto", texto[pos : m.start()]))
		destino, alvo, rotulo, chave, negrito = m.groups()
		if destino:
			alvo = alvo.strip()
			saida.append(Trecho("link", (rotulo or alvo).strip(), destino, alvo))
		elif chave:
			saida.append(Trecho("verificacao", VERIFICACOES.get(chave, chave), alvo=chave))
		else:
			saida.append(Trecho("negrito", negrito))
		pos = m.end()
	if pos < len(texto or ""):
		saida.append(Trecho("texto", texto[pos:]))
	return tuple(saida)


def _lista(valor: str) -> tuple[str, ...]:
	return tuple(x.strip() for x in (valor or "").split(",") if x.strip())


def _campo(linhas: list[str], rotulo: str) -> str:
	"""Valor de "- Rótulo: texto" (o texto pode continuar nas linhas seguintes, com recuo)."""
	alvo = sem_acento(rotulo).lower()
	coletando, partes = False, []
	for linha in linhas:
		m = re.match(r"^- ([^:]+):\s*(.*)$", linha)
		if m:
			if coletando:
				break
			if sem_acento(m.group(1)).lower().strip() == alvo:
				coletando, partes = True, [m.group(2).strip()]
		elif coletando and linha.strip():
			partes.append(linha.strip())
	return " ".join(partes)


def ler_guia(conteudo: str, origem: str = "") -> Guia:
	"""Lê o arquivo do guia. Erro de formato → ValueError com o arquivo e o motivo (o teste de integridade cobra)."""

	def erro(motivo: str):
		raise ValueError(f"{origem or 'guia'}: {motivo}")

	partes = conteudo.replace("\r\n", "\n").split("\n")
	if not partes or partes[0].strip() != "---":
		erro("falta o cabeçalho (--- no início)")
	try:
		fim = partes.index("---", 1)
	except ValueError:
		erro("cabeçalho sem o --- de fechamento")
	cabecalho = {}
	for linha in partes[1:fim]:
		if ":" in linha:
			chave, valor = linha.split(":", 1)
			cabecalho[chave.strip()] = valor.strip()
	for obrigatorio in ("id", "titulo", "publico", "tema"):
		if not cabecalho.get(obrigatorio):
			erro(f"cabeçalho sem {obrigatorio}")
	publico = _lista(cabecalho["publico"])
	if not publico or any(p not in PUBLICOS for p in publico):
		erro(f"público inválido: {cabecalho['publico']} (use {', '.join(PUBLICOS)})")
	secoes: dict[str, list[str]] = {}
	atual = None
	for linha in partes[fim + 1 :]:
		m = re.match(r"^## (.+)$", linha)
		if m:
			atual = m.group(1).strip()
			secoes[atual] = []
		elif atual:
			secoes[atual].append(linha)
	for secao in SECOES:
		if secao not in secoes:
			erro(f"falta a seção {secao}")
	objetivo = " ".join(x.strip() for x in secoes["Objetivo"] if x.strip())
	if not objetivo:
		erro("objetivo vazio")
	prerequisitos = tuple(
		Item(trechos(x.strip()[2:])) for x in secoes["Pré-requisitos"] if x.strip().startswith("- ")
	)
	passos, bloco, nome = [], [], None
	for linha in [*secoes["Passo a passo"], "### "]:
		m = re.match(r"^### (.*)$", linha)
		if m:
			if nome:
				fazer, onde = _campo(bloco, "O que fazer"), _campo(bloco, "Onde acessar")
				if not fazer:
					erro(f'passo "{nome}" sem "O que fazer"')
				passos.append(Passo(slug(nome), nome, trechos(fazer), trechos(onde)))
			nome, bloco = m.group(1).strip(), []
		else:
			bloco.append(linha)
	if not passos:
		erro("nenhum passo")
	if len({p.chave for p in passos}) != len(passos):
		erro("dois passos com o mesmo nome")
	acao, resultado = (
		_campo(secoes["Como testar"], "Ação"),
		_campo(secoes["Como testar"], "Resultado esperado"),
	)
	if not acao or not resultado:
		erro("Como testar precisa de Ação e Resultado esperado")
	for t in trechos(conteudo):
		if t.tipo == "verificacao" and t.alvo not in VERIFICACOES:
			erro(f"verificação desconhecida: {t.alvo}")
	return Guia(
		id=cabecalho["id"],
		titulo=cabecalho["titulo"],
		publico=publico,
		tema=cabecalho["tema"],
		palavras_chave=_lista(cabecalho.get("palavras_chave", "")),
		manual=cabecalho.get("manual", ""),
		telas=_lista(cabecalho.get("telas", "")),
		objetivo=trechos(objetivo),
		prerequisitos=prerequisitos,
		passos=tuple(passos),
		teste_acao=trechos(acao),
		teste_resultado=trechos(resultado),
		_texto=conteudo,
	)


def carregar(pasta: str | Path) -> list[Guia]:
	guias = [ler_guia(p.read_text(encoding="utf8"), p.name) for p in sorted(Path(pasta).glob("*.md"))]
	repetidos = [i for i, n in Counter(g.id for g in guias).items() if n > 1]
	if repetidos:
		raise ValueError(f"ids repetidos: {', '.join(repetidos)}")
	return guias


# ------------------------------------------------------------------ busca


def _raiz(termo: str) -> str:
	if len(termo) > 4 and termo.endswith("s"):
		termo = termo[:-1]
	return termo[:6]


def termos(texto: str) -> list[str]:
	palavras = re.findall(r"[a-z0-9]+", sem_acento(texto).lower())
	saida = []
	for p in palavras:
		if p in PALAVRAS_VAZIAS or len(p) < 2:
			continue
		saida.append(_raiz(SINONIMOS.get(p, p)))
	return list(dict.fromkeys(saida))


def dividir_topicos(texto: str) -> list[str]:
	"""'configurar risco e testar whatsapp' → dois assuntos; pedaço sem termo nenhum junta no anterior."""
	pedacos = [p.strip() for p in _DIVISORES.split(texto or "") if p and p.strip()]
	saida: list[str] = []
	for p in pedacos:
		if saida and len(termos(p)) == 0:
			saida[-1] = f"{saida[-1]} {p}"
		elif saida and len(termos(p)) == 1 and termos(p)[0] in ("testar", "libera", "config"):
			saida[-1] = f"{saida[-1]} {p}"
		else:
			saida.append(p)
	return saida or ([texto.strip()] if texto and texto.strip() else [])


@dataclass
class _Indice:
	titulo: set
	palavras: set
	tema: set
	corpo: set


def _indice(g: Guia) -> _Indice:
	corpo = " ".join(t.valor for t in g.trechos()) + " " + " ".join(p.nome for p in g.passos)
	return _Indice(
		set(termos(g.titulo)),
		set(termos(" ".join(g.palavras_chave))),
		set(termos(g.tema)),
		set(termos(corpo)),
	)


def nota(g: Guia, consulta: list[str], indice: _Indice | None = None) -> int:
	ind = indice or _indice(g)
	total = 0
	for t in consulta:
		if t in ind.titulo:
			total += 5
		elif t in ind.palavras:
			total += 4
		elif t in ind.tema:
			total += 2
		elif t in ind.corpo:
			total += 1
	return total


def visiveis(guias: list[Guia], publicos) -> list[Guia]:
	pub = set(publicos)
	return [g for g in guias if pub & set(g.publico)]


def da_tela(guias: list[Guia], tela: str | None) -> list[Guia]:
	return [g for g in guias if tela and tela in g.telas]


def _por_tema(guias: list[Guia]) -> list[Guia]:
	return sorted(guias, key=lambda g: (g.tema, g.titulo))


def buscar(guias: list[Guia], texto: str, publicos) -> dict:
	"""Resultado: cada assunto com os guias (até 3) ou, se amplo, a lista do tema; nada achado = fora do escopo."""
	vis = visiveis(guias, publicos)
	indices = {g.id: _indice(g) for g in vis}
	topicos = []
	for assunto in dividir_topicos(texto):
		consulta = termos(assunto)
		notas = sorted(
			((nota(g, consulta, indices[g.id]), g) for g in vis), key=lambda x: (-x[0], x[1].titulo)
		)
		bons = [(n, g) for n, g in notas if n >= NOTA_MINIMA]
		if not bons:
			topicos.append({"texto": assunto, "guias": [], "amplo": False, "tema": ""})
			continue
		topo = bons[0][0]
		parecidos = [(n, g) for n, g in bons if n >= topo * 0.75]
		tema, qtd = Counter(g.tema for _n, g in parecidos).most_common(1)[0]
		if len(parecidos) >= 4 and qtd >= 4:
			lista = _por_tema([g for g in vis if g.tema == tema])
			topicos.append({"texto": assunto, "guias": [g.id for g in lista], "amplo": True, "tema": tema})
			continue
		escolhidos = [g.id for n, g in bons if n >= topo * 0.5][:MAX_POR_TOPICO]
		topicos.append({"texto": assunto, "guias": escolhidos, "amplo": False, "tema": ""})
	fora = bool(topicos) and not any(t["guias"] for t in topicos)
	return {
		"topicos": topicos,
		"fora_do_escopo": fora,
		"mensagem": MENSAGEM_FORA if fora else "",
		"sugestoes": [g.id for g in _por_tema(vis)[:3]] if fora else [],
	}


# ------------------------------------------------------------------ resposta e progresso


def trechos_dict(lista) -> list[dict]:
	return [{"tipo": t.tipo, "valor": t.valor, "destino": t.destino, "alvo": t.alvo} for t in lista]


def como_dict(g: Guia, feitos=(), resumo: bool = False) -> dict:
	feitos = set(feitos)
	base = {
		"id": g.id,
		"titulo": g.titulo,
		"tema": g.tema,
		"publico": list(g.publico),
		"total": len(g.passos),
		"feitos": sum(1 for p in g.passos if p.chave in feitos),
	}
	if resumo:
		return base
	return base | {
		"manual": g.manual,
		"objetivo": trechos_dict(g.objetivo),
		"prerequisitos": [trechos_dict(i.trechos) for i in g.prerequisitos],
		"passos": [
			{
				"chave": p.chave,
				"nome": p.nome,
				"o_que_fazer": trechos_dict(p.o_que_fazer),
				"onde": trechos_dict(p.onde),
				"feito": p.chave in feitos,
			}
			for p in g.passos
		],
		"teste": {"acao": trechos_dict(g.teste_acao), "resultado": trechos_dict(g.teste_resultado)},
		"verificacoes": g.verificacoes(),
		"aviso": AVISO_JURIDICO,
	}


def proximo_passo(g: Guia, feitos) -> int:
	"""Índice do primeiro passo não feito (o guia reabre nele); todos feitos → o último."""
	feitos = set(feitos)
	for i, p in enumerate(g.passos):
		if p.chave not in feitos:
			return i
	return len(g.passos) - 1


def concluido(g: Guia, feitos) -> bool:
	return all(p.chave in set(feitos) for p in g.passos)


def publicos_dos_papeis(papeis) -> list[str]:
	"""Papéis do Frappe → públicos do Nahel. O administrador vê todos."""
	papeis = set(papeis)
	if "System Manager" in papeis:
		return list(PUBLICOS)
	saida = []
	if papeis & {"RH Ponto", "RH Saúde"}:
		saida.append("RH")
	if "Gestor Ponto" in papeis:
		saida.append("Gestor")
	return saida


_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_FONE = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b")


def dados_pessoais(texto: str) -> list[str]:
	"""CPF ou telefone no texto de um guia (o teste de integridade recusa)."""
	return _CPF.findall(texto or "") + _FONE.findall(texto or "")
