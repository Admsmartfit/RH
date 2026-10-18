"""Regras puras do estágio (Lei 11.788/2008) — seção 6 do docs/PRD-alteracoes.md (EST-02 a EST-09).

O estagiário não tem vínculo CLT: sem hora extra, banco, DSR nem adicional noturno pago. Os limites de jornada são
os do Termo de Compromisso (TCE), que não pode passar do teto legal do nível de ensino.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.banco_horas import adicionar_meses
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

CENTAVO = Decimal("0.01")


def limites_do_nivel(nivel: str) -> tuple[int, int]:
	"""(minutos por dia, minutos por semana) do nível de ensino (art. 10)."""
	if nivel not in d.ESTAGIO_LIMITES_POR_NIVEL:
		raise ValueError(f"Nível de ensino inválido: {nivel}")
	return d.ESTAGIO_LIMITES_POR_NIVEL[nivel]


def duracao_em_dias(periodos: Iterable[tuple[date, date]]) -> int:
	return sum((fim - inicio).days + 1 for inicio, fim in periodos)


@dataclass(frozen=True)
class TCE:
	nivel: str
	inicio: date
	fim: date
	carga_diaria: int  # minutos
	carga_semanal: int  # minutos
	obrigatorio: bool = False
	pcd: bool = False
	bolsa: Decimal = Decimal("0")
	auxilio_transporte: Decimal = Decimal("0")
	seguro_fim: date | None = None
	cadeia_anterior: tuple[tuple[date, date], ...] = field(default=())  # TCEs anteriores (aditivos)


def erros_do_tce(tce: TCE, estagiarios_do_supervisor: int = 0) -> list[str]:
	"""Erros que impedem o TCE. `estagiarios_do_supervisor` = outros TCEs vigentes do mesmo supervisor."""
	erros = []
	diario, semanal = limites_do_nivel(tce.nivel)
	if tce.carga_diaria > diario:
		erros.append(
			f"Carga diária de {tce.carga_diaria // 60}h{tce.carga_diaria % 60:02d} acima do limite de {diario // 60}h do nível {tce.nivel} (art. 10)."
		)
	if tce.carga_semanal > semanal:
		erros.append(
			f"Carga semanal de {tce.carga_semanal // 60}h acima do limite de {semanal // 60}h do nível {tce.nivel} (art. 10)."
		)
	if tce.fim < tce.inicio:
		erros.append("O fim do TCE é anterior ao início.")
	inicio_cadeia = min([tce.inicio, *[i for i, _f in tce.cadeia_anterior]])
	limite = (adicionar_meses(inicio_cadeia, d.ESTAGIO_DURACAO_MAXIMA_MESES) - inicio_cadeia).days
	if not tce.pcd and duracao_em_dias([*tce.cadeia_anterior, (tce.inicio, tce.fim)]) > limite:
		erros.append(
			f"A soma do TCE com os aditivos passa de {d.ESTAGIO_DURACAO_MAXIMA_MESES} meses (art. 11; exceto PcD)."
		)
	if not tce.obrigatorio and (Decimal(tce.bolsa) <= 0 or Decimal(tce.auxilio_transporte) <= 0):
		erros.append("Estágio não obrigatório exige bolsa e auxílio-transporte (art. 12).")
	if estagiarios_do_supervisor + 1 > d.ESTAGIO_MAX_POR_SUPERVISOR:
		erros.append(
			f"O supervisor já orienta {estagiarios_do_supervisor} estagiários (máximo {d.ESTAGIO_MAX_POR_SUPERVISOR}, art. 9º, III)."
		)
	return erros


def avisos_do_tce(tce: TCE) -> list[str]:
	if tce.seguro_fim is None:
		return ["Informe o seguro contra acidentes pessoais (art. 9º, IV)."]
	if tce.seguro_fim < tce.fim:
		return [f"O seguro vence em {tce.seguro_fim:%d/%m/%Y}, antes do fim do TCE ({tce.fim:%d/%m/%Y})."]
	return []


def jornada_dia_de_prova(previsto: int) -> int:
	"""Dia de prova: pelo menos metade da jornada (art. 10, §2º), em minutos arredondados para baixo."""
	return max(0, previsto) // 2


def periodos_dia_de_prova(periodos: Iterable[Periodo]) -> tuple[Periodo, ...]:
	"""Jornada do dia de prova: os primeiros minutos da jornada até completar a metade (EST-05)."""
	periodos = tuple(periodos)
	restante = jornada_dia_de_prova(sum(p.fim - p.inicio for p in periodos))
	resultado = []
	for p in periodos:
		if restante <= 0:
			break
		fim = min(p.fim, p.inicio + restante)
		resultado.append(Periodo(p.inicio, fim))
		restante -= fim - p.inicio
	return tuple(resultado)


def excesso_semanal(trabalhado_semana: int, carga_semanal: int) -> int:
	return max(0, trabalhado_semana - carga_semanal) if carga_semanal else 0


def meses_completos(inicio: date, ate: date) -> int:
	meses = (ate.year - inicio.year) * 12 + ate.month - inicio.month
	if adicionar_meses(inicio, meses) > ate:
		meses -= 1
	return max(0, meses)


def saldo_recesso(meses: int, dias_tirados: float = 0) -> float:
	"""2,5 dias por mês completo (30 a cada 12 meses), menos os dias já tirados (art. 13)."""
	return max(0.0, meses * d.ESTAGIO_RECESSO_DIAS_POR_MES - dias_tirados)


def datas_alerta_vencimento(fim: date) -> list[date]:
	return [fim - timedelta(days=dias) for dias in (30, 15, 5)]


def relatorios_devidos(inicio: date, ate: date) -> list[date]:
	"""Fim de cada semestre do TCE até a data (relatório a cada 6 meses, art. 9º, VII)."""
	devidos, n = [], 1
	while adicionar_meses(inicio, 6 * n) <= ate:
		devidos.append(adicionar_meses(inicio, 6 * n))
		n += 1
	return devidos


def limite_proporcao(quadro: int) -> int:
	"""Máximo de estagiários pelo quadro de empregados do estabelecimento (art. 17)."""
	if quadro <= 0:
		return 0
	if quadro <= 5:
		return 1
	if quadro <= 10:
		return 2
	if quadro <= 25:
		return 5
	return int(quadro * 20 / 100)


def aplica_proporcao(nivel: str) -> bool:
	return nivel not in d.ESTAGIO_NIVEIS_SEM_PROPORCAO


def desconto_bolsa(
	bolsa: Decimal, *, faltas_dias: int = 0, atraso: int = 0, carga_semanal: int = 1800
) -> Decimal:
	"""Falta = bolsa / 30 por dia; atraso = bolsa / (carga semanal x 5) por minuto (EST-09)."""
	valor_dia = Decimal(bolsa) / 30
	horas_mes = Decimal(carga_semanal) / 60 * 5
	valor_minuto = Decimal(bolsa) / horas_mes / 60 if horas_mes else Decimal("0")
	total = valor_dia * max(0, faltas_dias) + valor_minuto * max(0, atraso)
	return total.quantize(CENTAVO, rounding=ROUND_HALF_UP)
