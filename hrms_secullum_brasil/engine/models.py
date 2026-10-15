"""Dataclasses de entrada e saída do motor de apuração (PRD, Seção 3.2).

Tempos em minutos inteiros. Horários previstos e intervalos trabalhados são minutos a partir das
00:00 do dia de trabalho (podem passar de 1440 em jornadas que atravessam a meia-noite).
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.jornada_prevista import Periodo, minutos_do_dia

ALTA = "Alta"
MEDIA = "Média"
BAIXA = "Baixa"


@dataclass(frozen=True)
class Inconsistencia:
	tipo: str  # mesmos códigos do Select "tipo" de Inconsistencia de Ponto
	severidade: str
	mensagem: str


@dataclass(frozen=True)
class JornadaPrevista:
	periodos: tuple[Periodo, ...] = ()
	permite_intervalo_estendido: bool = False

	@property
	def minutos(self) -> int:
		return sum(p.duracao for p in self.periodos)

	@property
	def folga(self) -> bool:
		return not self.periodos


@dataclass(frozen=True)
class RegraApuracao:
	"""Parâmetros da Regra Sindical CCT vigente que o motor usa. Padrões = defaults legais."""

	tolerancia_por_marcacao: int = d.TOLERANCIA_POR_MARCACAO_MIN
	tolerancia_diaria: int = d.TOLERANCIA_DIARIA_MIN
	computar_todo_tempo_ao_exceder: bool = d.COMPUTAR_TODO_TEMPO_AO_EXCEDER
	compensar_atraso_com_he: bool = d.COMPENSAR_ATRASO_COM_HE
	duplicidade_minutos: int = d.DUPLICIDADE_MIN
	limite_he_diaria: int = d.LIMITE_HE_DIARIA_MIN
	faixas_he: tuple[FaixaHE, ...] = d.FAIXAS_HE_PADRAO
	noturno_inicio: int = minutos_do_dia(d.NOTURNO_INICIO)
	noturno_fim: int = minutos_do_dia(d.NOTURNO_FIM)
	minutos_hora_noturna: float = d.MINUTOS_HORA_NOTURNA
	prorrogacao_noturna: bool = d.PRORROGACAO_NOTURNA
	jornada_sem_intervalo_ate: int = d.JORNADA_SEM_INTERVALO_ATE_MIN
	intervalo_curto: int = d.INTERVALO_CURTO_MIN
	jornada_intervalo_curto_ate: int = d.JORNADA_INTERVALO_CURTO_ATE_MIN
	intervalo_minimo: int = d.INTERVALO_MINIMO_MIN
	intervalo_maximo: int = d.INTERVALO_MAXIMO_MIN
	permite_reducao_intrajornada: bool = d.PERMITE_REDUCAO_INTRAJORNADA
	intervalo_reduzido: int = d.INTERVALO_REDUZIDO_MIN
	interjornada_minima: int = d.INTERJORNADA_MIN


@dataclass(frozen=True)
class EntradaDia:
	data: date
	marcacoes: tuple[datetime, ...]
	jornada: JornadaPrevista = field(default_factory=JornadaPrevista)
	regra: RegraApuracao = field(default_factory=RegraApuracao)
	feriado: bool = False
	abonado: bool = False  # atestado/abono aprovado para o dia inteiro
	marcacoes_dia_anterior: tuple[datetime, ...] = ()  # para a interjornada (inclui outros vínculos do CPF)
	horista: bool = False  # horista/intermitente: sem jornada prevista; até 8h no dia é normal


@dataclass(frozen=True)
class MinutosFaixa:
	tipo_dia: str
	percentual: float
	minutos: int
	vai_para_banco: bool = field(default=False, compare=False)


@dataclass
class ResultadoDia:
	data: date
	tipo_dia: str
	apurado: bool = True
	previsto: int = 0
	trabalhado: int = 0
	normais: int = 0
	atraso: int = 0  # atrasos + saídas antecipadas após a tolerância
	falta: int = 0
	hora_extra: int = 0
	he_faixas: list[MinutosFaixa] = field(default_factory=list)
	noturno_real: int = 0
	noturno_ficto: int = 0
	intrajornada_suprimida: int = 0
	interjornada_suprimida: int = 0
	aulas_previstas: int = 0
	aulas_dadas: int = 0
	aulas_nao_dadas: int = 0
	janela_minutos: int = 0
	marcacoes_consideradas: list[datetime] = field(default_factory=list)
	marcacoes_ignoradas: list[datetime] = field(default_factory=list)
	inconsistencias: list[Inconsistencia] = field(default_factory=list)

	def tipos_inconsistencia(self) -> list[str]:
		return [i.tipo for i in self.inconsistencias]
