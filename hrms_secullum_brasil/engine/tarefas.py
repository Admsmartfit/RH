"""Quadro de tarefas (docs/PRD-quadro-tarefas.md). Python puro: colunas, ordem, atraso, atalhos do título, pilhas,
ocultos, repetição e os textos dos avisos. O Frappe (`apuracao/tarefas.py`) só lê, grava e avisa."""

import calendar
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

A_FAZER, FAZENDO, AGUARDANDO, FEITO, DESCARTADO = "A fazer", "Fazendo", "Aguardando", "Feito", "Descartado"
COLUNAS = (A_FAZER, FAZENDO, AGUARDANDO, FEITO)
ABERTAS = (A_FAZER, FAZENDO, AGUARDANDO)
URGENTE, ALTA, NORMAL = "Urgente", "Alta", "Normal"
PRIORIDADES = (URGENTE, ALTA, NORMAL)
PESSOA, GRUPO_RH, GRUPO_GESTORES, COLABORADOR = "Pessoa", "RH", "Gestores da unidade", "Colaborador"
MANUAL, AUTOMATICA = "Manual", "Automática"
SEMANAL, MENSAL = "Semanal", "Mensal"
DIAS_NO_FEITO = 14  # o Feito mostra só os últimos 14 dias (depois arquiva)
DIAS_UTEIS_PARA_AVISAR_RH = 2  # atrasou 2 dias úteis: o RH também é avisado
MINIMO_DA_PILHA = 2  # cartões automáticos iguais (tipo + unidade + coluna) viram uma pilha a partir de 2

# tipos de cartão automático (seção 3.5): nome curto para a pilha e para o "Silenciar este tipo"
TIPOS_AUTOMATICOS = {
	"tarefa_secullum": "Tarefas no Secullum",
	"fechamento_bloqueado": "Fechamento bloqueado",
	"inconsistencia_alta": "Inconsistências Alta",
}
SILENCIAR_DIAS = (1, 7, 30)

_DIAS_SEMANA = {
	"segunda": 0,
	"seg": 0,
	"terca": 1,
	"ter": 1,
	"quarta": 2,
	"qua": 2,
	"quinta": 3,
	"qui": 3,
	"sexta": 4,
	"sex": 4,
	"sabado": 5,
	"sab": 5,
	"domingo": 6,
	"dom": 6,
}
_PRIORIDADE_DO_ATALHO = {"!urgente": URGENTE, "!alta": ALTA, "!normal": NORMAL}


def normalizar(texto: str) -> str:
	sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
	return sem_acento.lower().strip()


# ------------------------------------------------------------------ prazo e atraso


def dias_uteis_entre(inicio: date, fim: date) -> int:
	"""Dias úteis (segunda a sexta) depois de `inicio` até `fim`, inclusive. 0 se `fim` <= `inicio`."""
	if fim <= inicio:
		return 0
	dias, dia = 0, inicio
	while dia < fim:
		dia += timedelta(days=1)
		if dia.weekday() < 5:
			dias += 1
	return dias


def atrasado(prazo: date | None, coluna: str, hoje: date) -> bool:
	return bool(prazo) and coluna in ABERTAS and prazo < hoje


def vence_hoje(prazo: date | None, coluna: str, hoje: date) -> bool:
	return bool(prazo) and coluna in ABERTAS and prazo == hoje


def avisar_rh_do_atraso(prazo: date | None, coluna: str, hoje: date, ja_avisado: bool) -> bool:
	"""Atrasou 2 dias úteis e o RH ainda não foi avisado."""
	return (
		not ja_avisado
		and atrasado(prazo, coluna, hoje)
		and dias_uteis_entre(prazo, hoje) >= DIAS_UTEIS_PARA_AVISAR_RH
	)


def no_feito(concluida_em: datetime | date | None, hoje: date, dias: int = DIAS_NO_FEITO) -> bool:
	"""O cartão Feito aparece no quadro só nos últimos `dias` dias (depois só na busca)."""
	if not concluida_em:
		return True
	dia = concluida_em.date() if isinstance(concluida_em, datetime) else concluida_em
	return (hoje - dia).days <= dias


# ------------------------------------------------------------------ ordem e pilhas


@dataclass(frozen=True)
class Cartao:
	nome: str
	coluna: str = A_FAZER
	prioridade: str = NORMAL
	prazo: date | None = None
	criado: datetime | None = None
	origem: str = MANUAL
	origem_tipo: str | None = None
	company: str | None = None


def chave_de_ordem(c: Cartao, hoje: date) -> tuple:
	"""Atrasados primeiro, depois a prioridade, o prazo mais perto (sem prazo por último) e o mais antigo."""
	prioridade = PRIORIDADES.index(c.prioridade) if c.prioridade in PRIORIDADES else len(PRIORIDADES)
	return (
		0 if atrasado(c.prazo, c.coluna, hoje) else 1,
		prioridade,
		c.prazo or date.max,
		c.criado or datetime.max,
		c.nome,
	)


def ordenar(cartoes: Iterable[Cartao], hoje: date) -> list[Cartao]:
	return sorted(cartoes, key=lambda c: chave_de_ordem(c, hoje))


@dataclass(frozen=True)
class Pilha:
	origem_tipo: str
	company: str | None
	cartoes: tuple[Cartao, ...]

	@property
	def chave(self) -> str:
		return f"{self.origem_tipo}|{self.company or ''}"

	@property
	def titulo(self) -> str:
		nome = TIPOS_AUTOMATICOS.get(self.origem_tipo, self.origem_tipo)
		return f"{nome}{f' — {self.company}' if self.company else ''}: {len(self.cartoes)}"


def empilhar(cartoes: Iterable[Cartao], hoje: date, minimo: int = MINIMO_DA_PILHA) -> list[Cartao | Pilha]:
	"""Cartões automáticos do mesmo tipo, unidade e coluna viram uma pilha (a partir de `minimo`), no lugar do primeiro
	deles; o resto fica como está. A ordem segue `ordenar`."""
	ordenados = ordenar(cartoes, hoje)
	grupos: dict[tuple, list[Cartao]] = {}
	for c in ordenados:
		if c.origem == AUTOMATICA and c.origem_tipo:
			grupos.setdefault((c.coluna, c.origem_tipo, c.company), []).append(c)
	saida: list[Cartao | Pilha] = []
	vistos: set[tuple] = set()
	for c in ordenados:
		chave = (c.coluna, c.origem_tipo, c.company)
		grupo = grupos.get(chave) if c.origem == AUTOMATICA and c.origem_tipo else None
		if grupo and len(grupo) >= minimo:
			if chave not in vistos:
				vistos.add(chave)
				saida.append(Pilha(c.origem_tipo, c.company, tuple(grupo)))
			continue
		saida.append(c)
	return saida


# ------------------------------------------------------------------ ocultos e silenciados


@dataclass(frozen=True)
class Ocultacao:
	ate: date
	cartao: str | None = None  # "Ocultar até…" de um cartão
	origem_tipo: str | None = None  # "Silenciar este tipo por…"


def oculto(c: Cartao, ocultacoes: Iterable[Ocultacao], hoje: date) -> bool:
	"""Some da tela de quem ocultou (o cartão ou o tipo) até a data; no dia `ate` ele volta."""
	for o in ocultacoes:
		if o.ate <= hoje:
			continue
		if o.cartao and o.cartao == c.nome:
			return True
		if o.origem_tipo and c.origem == AUTOMATICA and o.origem_tipo == c.origem_tipo:
			return True
	return False


def data_para_ocultar(opcao: str, hoje: date, prazo: date | None = None, data: date | None = None) -> date:
	"""Opções do "Ocultar até…": amanha, segunda, prazo (o próprio prazo, ou amanhã sem prazo) ou data."""
	if opcao == "amanha":
		return hoje + timedelta(days=1)
	if opcao == "segunda":
		return hoje + timedelta(days=7 - hoje.weekday())
	if opcao == "prazo":
		return prazo if prazo and prazo > hoje else hoje + timedelta(days=1)
	if opcao == "data" and data and data > hoje:
		return data
	raise ValueError("Escolha uma data depois de hoje.")


# ------------------------------------------------------------------ atalhos do título


@dataclass(frozen=True)
class Pessoa:
	chave: str  # usuário (e-mail) ou Employee
	nome: str
	tipo: str = PESSOA  # Pessoa (usuário do painel) ou Colaborador


@dataclass(frozen=True)
class Interpretacao:
	titulo: str
	prioridade: str | None = None
	prazo: date | None = None
	responsavel: Pessoa | None = None
	avisos: tuple[str, ...] = field(default_factory=tuple)


def _data_do_texto(palavra: str, hoje: date) -> date | None:
	p = normalizar(palavra).rstrip(".,;")
	if p == "hoje":
		return hoje
	if p == "amanha":
		return hoje + timedelta(days=1)
	if p in _DIAS_SEMANA:
		dias = (_DIAS_SEMANA[p] - hoje.weekday()) % 7
		return hoje + timedelta(days=dias or 7)
	m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", p)
	if m:
		dia, mes = int(m[1]), int(m[2])
		ano = int(m[3]) if m[3] else hoje.year
		ano += 2000 if ano < 100 else 0
		try:
			alvo = date(ano, mes, dia)
		except ValueError:
			return None
		if not m[3] and alvo < hoje:
			alvo = date(ano + 1, mes, dia)
		return alvo
	return None


def achar_pessoa(apelido: str, pessoas: Iterable[Pessoa]) -> tuple[Pessoa | None, list[Pessoa]]:
	"""@apelido: casa com o começo do nome ou de uma das palavras do nome (sem acento). Devolve (a pessoa, os
	candidatos quando há mais de uma)."""
	alvo = normalizar(apelido).replace("_", " ").replace(".", " ").strip()
	if not alvo:
		return None, []
	achados = []
	for p in pessoas:
		nome = normalizar(p.nome)
		if nome.startswith(alvo) or any(parte.startswith(alvo) for parte in nome.split()):
			achados.append(p)
	exatos = [p for p in achados if normalizar(p.nome).split()[:1] == [alvo]]
	if len(achados) == 1:
		return achados[0], achados
	if len(exatos) == 1:
		return exatos[0], achados
	return None, achados


def interpretar_titulo(texto: str, hoje: date, pessoas: Iterable[Pessoa] = ()) -> Interpretacao:
	"""Atalhos do "+ Nova tarefa": `@nome` (responsável), `!urgente`/`!alta` (prioridade) e o prazo no fim do título
	(`hoje`, `amanhã`, `sexta`, `25/11`, com ou sem "até"/"para" antes). O resto é o título."""
	pessoas = list(pessoas)
	palavras = str(texto or "").split()
	avisos: list[str] = []
	prioridade = responsavel = prazo = None
	sobra = []
	for palavra in palavras:
		minuscula = normalizar(palavra).rstrip(".,;")
		if minuscula in _PRIORIDADE_DO_ATALHO:
			prioridade = _PRIORIDADE_DO_ATALHO[minuscula]
			continue
		if palavra.startswith("@") and len(palavra) > 1:
			pessoa, candidatos = achar_pessoa(palavra[1:].rstrip(".,;"), pessoas)
			if pessoa:
				responsavel = pessoa
				continue
			if candidatos:
				nomes = ", ".join(p.nome for p in candidatos[:4])
				avisos.append(f"{palavra}: mais de uma pessoa ({nomes}); escolha no campo Responsável.")
			else:
				avisos.append(f"{palavra}: ninguém com esse nome; escolha no campo Responsável.")
			continue
		sobra.append(palavra)
	# o prazo só no fim do título (evita ler "banco de segunda" no meio de uma frase)
	if sobra:
		achada = _data_do_texto(sobra[-1], hoje)
		if achada:
			prazo = achada
			sobra.pop()
			if sobra and normalizar(sobra[-1]) in ("ate", "para", "pra"):
				sobra.pop()
	titulo = " ".join(sobra).strip(" -,;")
	if not titulo:
		avisos.append("Escreva o que precisa ser feito.")
	return Interpretacao(titulo, prioridade, prazo, responsavel, tuple(avisos))


# ------------------------------------------------------------------ repetição


def proxima_data(repetir: str, depois_de: date, dia: int | None) -> date | None:
	"""Próximo prazo de uma tarefa que se repete, depois de `depois_de`.
	Semanal: `dia` = dia da semana (0 = segunda). Mensal: `dia` = dia do mês (31 vira o último dia do mês)."""
	if repetir == SEMANAL:
		alvo = depois_de.weekday() if dia is None else int(dia) % 7
		dias = (alvo - depois_de.weekday()) % 7
		return depois_de + timedelta(days=dias or 7)
	if repetir == MENSAL:
		dia_mes = int(dia or depois_de.day)
		ano, mes = depois_de.year, depois_de.month
		for _ in range(2):
			ultimo = calendar.monthrange(ano, mes)[1]
			candidato = date(ano, mes, min(max(dia_mes, 1), ultimo))
			if candidato > depois_de:
				return candidato
			ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
		return None  # pragma: no cover - dois meses sempre bastam
	return None


# ------------------------------------------------------------------ textos dos avisos


def _data_br(d: date) -> str:
	return f"{d:%d/%m}"


def texto_resumo(
	primeiro_nome: str, abertos: int, atrasados: list[str], hoje_vencem: int, link: str
) -> str | None:
	"""O resumo da manhã (uma mensagem por dia por pessoa). Nada aberto = nada a mandar."""
	if not abertos:
		return None
	partes = [f"Bom dia, {primeiro_nome}. Você tem *{abertos} tarefa{'s' if abertos > 1 else ''}* no quadro"]
	detalhes = []
	if atrasados:
		exemplo = f' ("{atrasados[0]}")' if len(atrasados) == 1 else ""
		detalhes.append(f"{len(atrasados)} atrasada{'s' if len(atrasados) > 1 else ''}{exemplo}")
	if hoje_vencem:
		detalhes.append(f"{hoje_vencem} vence{'m' if hoje_vencem > 1 else ''} hoje")
	texto = partes[0] + (": " + " e ".join(detalhes) if detalhes else "") + "."
	return f"{texto}\nAbrir: {link}"


def texto_atribuida(titulo: str, prazo: date | None, link: str, urgente: bool = False) -> str:
	prefixo = "Tarefa URGENTE para você" if urgente else "Nova tarefa para você"
	quando = f" (prazo {_data_br(prazo)})" if prazo else ""
	return f"{prefixo}: {titulo}{quando}.\nAbrir: {link}"


def texto_colaborador(primeiro_nome: str, titulo: str, prazo: date | None, link: str) -> str:
	"""WhatsApp ao colaborador da equipe (sem acesso ao programa): o título, o prazo e o link pessoal."""
	quando = f" até {_data_br(prazo)}" if prazo else ""
	return (
		f"Olá, {primeiro_nome}. Seu gestor pediu: {titulo}{quando}.\n"
		f"Quando terminar, toque no link e marque Feito: {link}"
	)


def texto_atraso_rh(titulo: str, responsavel: str, prazo: date, dias: int) -> str:
	return f'Tarefa atrasada há {dias} dia(s) útil(eis): "{titulo}" ({responsavel}; prazo {_data_br(prazo)}).'
