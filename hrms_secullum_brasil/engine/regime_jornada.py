"""Jornada legal com vigência (docs/PRD-planejador-5x2.md, PE-01; EC nº 141/2026). Python puro.

A emenda reduz o teto semanal (44h → 42h → 40h) e garante 2 repousos por semana, mas a troca **não muda sozinha**:
o RH ativa cada regime com a data de início (DP-1). Até lá vale o regime da CLT (44h, divisor 220, 1 repouso).

- `regime_na_data`: o regime ativo mais recente com início até a data; sem nenhum, o padrão da CLT.
- `teto_semanal`: na semana que atravessa a troca, o teto é proporcional aos dias corridos em cada regime (DP-13).
- `contar_dias`: dias úteis e de descanso da semana para o DSR do horista: os repousos remunerados do regime (1 na
  CLT, 2 na EC — em qualquer dia, um preferencialmente no domingo; a regra de domingos é a da CCT/CLT de sempre) mais
  os feriados que não caem no domingo. Na CLT dá o mesmo que `engine.dsr.contar_dias` (domingo + feriados).
- `divisor_efetivo`: o divisor do contrato/perfil, limitado ao do regime (jornada acima do teto cai ao teto sem
  redução de salário: 220 → 210 com 42h; quem tem carga menor fica como está). No período que atravessa a troca, a
  média dos dias (`divisor_do_periodo`, RH 30/10/2026: proporcional).
- `folgas_insuficientes`: semana com menos dias sem trabalho do que o regime exige.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import defaults_legais as d


@dataclass(frozen=True)
class RegimeJornada:
	nome: str
	inicio: date | None  # None = desde sempre (o padrão da CLT)
	semanal_min: int
	divisor: int
	folgas_semana: int = 1
	repousos_remunerados: int = 1  # dias de descanso por semana no DSR do horista
	diaria_min: int = d.JORNADA_DIARIA_MAXIMA_MIN


CLT = RegimeJornada("CLT (44h)", None, d.CARGA_SEMANAL_MAXIMA_MIN, d.DIVISOR_PADRAO, 1, 1)


def regime_na_data(data: date, ativos: Iterable[RegimeJornada]) -> RegimeJornada:
	"""O regime ativo de início mais recente até a data (os preparados não entram aqui)."""
	validos = [r for r in ativos if r.inicio and r.inicio <= data]
	return max(validos, key=lambda r: r.inicio) if validos else CLT


def teto_semanal(segunda: date, ativos: Iterable[RegimeJornada]) -> int:
	"""Teto da semana (min): proporcional aos dias corridos em cada regime (DP-13). Semana inteira num regime = o
	teto dele."""
	ativos = list(ativos)
	total = sum(
		Decimal(regime_na_data(segunda + timedelta(days=i), ativos).semanal_min) / 7 for i in range(7)
	)
	return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def divisor_na_data(data: date, ativos: Iterable[RegimeJornada]) -> int:
	return regime_na_data(data, ativos).divisor


def contar_dias(
	dias: Iterable[date], feriados: set[date], ativos: Iterable[RegimeJornada]
) -> tuple[int, int]:
	"""(dias úteis, dias de descanso) da semana: repousos do regime (o do domingo, que fecha a semana) + feriados fora
	do domingo. Os repousos não têm dia fixo (EC 141/2026)."""
	dias = list(dias)
	if not dias:
		return 0, 0
	repousos = regime_na_data(max(dias), list(ativos)).repousos_remunerados
	feriados_fora_do_domingo = sum(1 for dia in dias if dia in feriados and dia.weekday() != 6)
	descanso = min(len(dias), repousos + feriados_fora_do_domingo)
	return len(dias) - descanso, descanso


def divisor_efetivo(divisor_contrato: int, data: date, ativos: Iterable[RegimeJornada]) -> int:
	regime = regime_na_data(data, ativos)
	if regime.inicio is None or not divisor_contrato:
		return divisor_contrato
	return min(divisor_contrato, regime.divisor)


def divisor_do_periodo(
	divisor_contrato: int, inicio: date, fim: date, ativos: Iterable[RegimeJornada]
) -> Decimal:
	"""Média do divisor efetivo nos dias do período (proporcional na troca de regime), com 4 casas."""
	ativos = list(ativos)
	dias = (fim - inicio).days + 1
	if dias <= 0:
		return Decimal(divisor_efetivo(divisor_contrato, fim, ativos))
	soma = sum(divisor_efetivo(divisor_contrato, inicio + timedelta(days=i), ativos) for i in range(dias))
	return (Decimal(soma) / dias).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def folgas_exigidas(segunda: date, ativos: Iterable[RegimeJornada]) -> int:
	"""Folgas da semana: as do regime do domingo (o regime que fecha a semana)."""
	return regime_na_data(segunda + timedelta(days=6), ativos).folgas_semana


def folgas_insuficientes(
	segunda: date, dias_trabalhados: Iterable[date], ativos: Iterable[RegimeJornada]
) -> int:
	"""Quantas folgas faltaram na semana (0 = ok). Só olha os dias da semana [segunda, domingo]."""
	semana = {segunda + timedelta(days=i) for i in range(7)}
	trabalhados = len(semana & set(dias_trabalhados))
	return max(0, folgas_exigidas(segunda, ativos) - (7 - trabalhados))
