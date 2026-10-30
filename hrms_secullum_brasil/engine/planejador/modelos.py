"""Modelos do planejador (PE-02, PE-05). Horários em minutos do dia; o horizonte é uma lista de semanas inteiras
(segunda a domingo) e cada dia é indexado pela posição no horizonte. Faixas de 30 min das 06h às 23h (PE-03)."""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from hrms_secullum_brasil.engine import defaults_legais as d

FAIXA_MIN = 30
ABRE = 6 * 60
FECHA = 23 * 60
FAIXAS = tuple(range(ABRE // FAIXA_MIN, FECHA // FAIXA_MIN))  # 12 (06:00) a 45 (22:30)

MENSALISTA = "Mensalista"
HORISTA = "Horista"
ESTAGIARIO = "Estagiario"
VAGA = "Vaga"  # contratação sugerida (proposta D)


def hhmm(minutos: int) -> str:
	return f"{(minutos // 60) % 24:02d}:{minutos % 60:02d}"


def faixa_texto(faixa: int) -> str:
	return f"{hhmm(faixa * FAIXA_MIN)}-{hhmm((faixa + 1) * FAIXA_MIN)}"


@dataclass(frozen=True, order=True)
class Turno:
	inicio: int
	fim: int
	pausa: int = 0  # minutos de pausa no meio do turno (não contam como trabalho nem cobertura)

	@property
	def minutos(self) -> int:
		return self.fim - self.inicio - self.pausa

	@property
	def pausa_inicio(self) -> int:
		return self.inicio + (self.fim - self.inicio - self.pausa) // 2

	def faixas(self) -> tuple[int, ...]:
		"""Faixas de 30 min inteiras dentro do turno, fora da pausa."""
		saida = []
		for faixa in range(self.inicio // FAIXA_MIN, -(-self.fim // FAIXA_MIN)):
			ini, fim = faixa * FAIXA_MIN, (faixa + 1) * FAIXA_MIN
			if ini < self.inicio or fim > self.fim:
				continue
			if self.pausa and ini < self.pausa_inicio + self.pausa and self.pausa_inicio < fim:
				continue
			saida.append(faixa)
		return tuple(saida)

	@property
	def texto(self) -> str:
		pausa = f" (pausa {self.pausa} min)" if self.pausa else ""
		return f"{hhmm(self.inicio)}-{hhmm(self.fim)}{pausa}"

	def periodos(self) -> tuple[tuple[int, int], ...]:
		"""Os períodos de trabalho (com a pausa no meio), para a validação do cockpit."""
		if not self.pausa:
			return ((self.inicio, self.fim),)
		return ((self.inicio, self.pausa_inicio), (self.pausa_inicio + self.pausa, self.fim))


HORA = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


def ler_hora(texto: str) -> int:
	achado = HORA.match(str(texto or ""))
	if not achado:
		raise ValueError(f"horário inválido: {texto!r}")
	return int(achado.group(1)) * 60 + int(achado.group(2))


@dataclass(frozen=True)
class Indisponivel:
	dia: int  # índice no horizonte
	inicio: int = 0
	fim: int = 1440


@dataclass(frozen=True)
class Pessoa:
	id: str
	nome: str
	tipo: str = HORISTA
	genero: str = ""
	cref: bool = True  # profissional de educação física com CREF ativo (supervisiona estagiário)
	custo_hora: Decimal = Decimal("0")  # valor da hora (horista) ou salário / divisor (mensalista)
	salario_mensal: Decimal = Decimal("0")  # mensalista: salário; estagiário: bolsa
	diaria_atual: int = 240  # maior turno de hoje (o contrato de fato)
	diaria_max: int = 24 * 60  # teto pessoal (o do TCE no estagiário); o legal vem das Regras
	semanal_max: int = d.CARGA_SEMANAL_MAXIMA_MIN  # o teto do regime ou o do TCE
	semanal_min: int = 0  # mínimo semanal garantido do horista (complemento pago)
	indisponivel: tuple[Indisponivel, ...] = ()
	atual: tuple[Turno | None, ...] = ()  # um por dia do horizonte (None = folga)
	limite_domingos: int = d.DOMINGOS_SEGUIDOS_HOMEM  # domingos seguidos de trabalho permitidos
	domingos_seguidos_antes: int = 0  # domingos trabalhados seguidos logo antes do horizonte
	indice: int = 50
	fixa: bool = False  # "não mexer": a escala de hoje fica
	vaga: bool = False

	@property
	def estagiario(self) -> bool:
		return self.tipo == ESTAGIARIO


@dataclass(frozen=True)
class Horizonte:
	datas: tuple[date, ...]

	@staticmethod
	def semanas(segunda: date, semanas: int) -> "Horizonte":
		segunda = segunda - timedelta(days=segunda.weekday())
		return Horizonte(tuple(segunda + timedelta(days=i) for i in range(7 * semanas)))

	@property
	def dias(self) -> range:
		return range(len(self.datas))

	@property
	def n_semanas(self) -> int:
		return len(self.datas) // 7

	def dias_da_semana(self, semana: int) -> range:
		return range(7 * semana, 7 * semana + 7)

	def domingos(self) -> list[int]:
		return [i for i, dia in enumerate(self.datas) if dia.weekday() == 6]


@dataclass(frozen=True)
class Regras:
	teto_semanal: int = d.CARGA_SEMANAL_MAXIMA_MIN
	folgas_semana: int = 1
	repousos: int = 1
	interjornada: int = d.INTERJORNADA_MIN
	diaria_legal: int = d.JORNADA_DIARIA_MAXIMA_MIN
	diaria_compensada: int = 0  # CCT com compensação (ex.: 504 = 8h24), DP-11
	regime: str = "CLT (44h)"

	@property
	def diaria(self) -> int:
		return max(self.diaria_legal, self.diaria_compensada)


@dataclass(frozen=True)
class Demanda:
	"""Por (dia da semana 0-6, faixa): o mínimo (abaixo é déficit) e o ideal."""

	minimo: dict[tuple[int, int], int] = field(default_factory=dict)
	ideal: dict[tuple[int, int], int] = field(default_factory=dict)

	def de(self, data: date, faixa: int) -> tuple[int, int]:
		chave = (data.weekday(), faixa)
		return self.minimo.get(chave, 0), self.ideal.get(chave, 0)


TODOS, POR_INDICE, LISTA, NINGUEM = "todos", "indice", "lista", "nenhum"


@dataclass(frozen=True)
class Premissas:
	"""Regras do jogo definidas pelo gestor (PE-05)."""

	teto_horista: int = 240  # 4h, 6h ou 8h por dia
	ampliar: str = POR_INDICE  # quem pode ter a carga ampliada
	indice_minimo: int = 70
	lista_ampliar: tuple[str, ...] = ()
	max_ampliacoes: int = 99
	usar_estagiarios: bool = True
	cota_estagiario_pct: int = 30  # máximo de estagiários por faixa (% dos presentes)
	budget_pct: float | None = 15.0  # aumento máximo da folha em relação à escala de hoje
	peso_cobertura: int = 5  # 1 a 10
	peso_custo: int = 5  # 1 a 10
	peso_estabilidade: int = 3  # 0 a 10: quanto custa cada mudança
	contratar: bool = False
	custo_vaga_hora: Decimal = Decimal("0")
	max_vagas: int = 3
	nao_mexer: tuple[str, ...] = ()
	travas: tuple[tuple[str, int, Turno | None], ...] = ()  # (pessoa, dia, turno ou folga)
	usar_compensacao: bool = False
	teto_semanal_horista: int = (
		40 * 60
	)  # margem da escala do horista (RH: 40h, para nunca chegar à HE das 44h)


Escala = dict[str, tuple[Turno | None, ...]]


def pode_ampliar(pessoa: Pessoa, premissas: Premissas) -> bool:
	if pessoa.tipo != HORISTA or pessoa.fixa or pessoa.vaga:
		return False
	if premissas.ampliar == TODOS:
		return True
	if premissas.ampliar == POR_INDICE:
		return pessoa.indice >= premissas.indice_minimo
	if premissas.ampliar == LISTA:
		return pessoa.id in premissas.lista_ampliar
	return False


def diaria_permitida(pessoa: Pessoa, regras: Regras, premissas: Premissas, ampliar: bool) -> int:
	"""O maior turno que a pessoa pode ter nesta proposta."""
	teto_legal = min(pessoa.diaria_max, regras.diaria if premissas.usar_compensacao else regras.diaria_legal)
	if pessoa.vaga:
		return min(teto_legal, max(premissas.teto_horista, 240))
	if pessoa.tipo == HORISTA:
		base = max(pessoa.diaria_atual, 1)
		if ampliar and pode_ampliar(pessoa, premissas):
			base = max(base, premissas.teto_horista)
		return min(teto_legal, base)
	return min(teto_legal, max(pessoa.diaria_atual, 1))
