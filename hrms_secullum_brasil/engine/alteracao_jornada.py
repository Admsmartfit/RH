"""Alteração do horário fixo da semana (docs/PRD-cockpit-escalas.md, DE-17 / CE-16). Python puro.

Classifica a troca do horário semanal (resumo da lei no PRD; confirmar com o jurídico):
- **Proibida** (não gera documento): quebra a lei no novo horário (mais de 10h no dia, intervalo, interjornada entre
  dias seguidos, carga acima de 44h) ou reduz o salário.
- **Concordância** (aditivo; CLT art. 468): muda a carga semanal ou as horas garantidas do horista, passa a ter
  trabalho noturno (ou mais noturno), muda os dias trabalhados, troca de turno (manhã/tarde/noite) ou tira horas
  extras habituais (Súmula 291).
- **Ciência** (termo; jus variandi): ajuste no mesmo turno, mesmos dias e mesma carga. Sair do noturno para o diurno é
  válido (Súmula 265) e também fica como ciência.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

CIENCIA = "Ciência"
CONCORDANCIA = "Concordância"
PROIBIDA = "Proibida"
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
NOITE_INICIO, NOITE_FIM = 22 * 60, 5 * 60 + 1440  # 22h às 5h

Horario = Mapping[int, tuple[Periodo, ...]]  # dia da semana (0 = segunda) -> períodos


@dataclass(frozen=True)
class Contexto:
	horista: bool = False
	minimo_horas_antes: float = 0  # horas garantidas do horista (semana)
	minimo_horas_depois: float = 0
	he_habituais: bool = False  # fez hora extra com habitualidade (o novo horário tira)
	reduz_salario: bool = False
	intervalo_minimo: int = d.INTERVALO_MINIMO_MIN
	jornada_fragmentada: bool = False


@dataclass(frozen=True)
class Classificacao:
	tipo: str
	motivos: tuple[str, ...]
	carga_antes: int
	carga_depois: int
	noturno_antes: int
	noturno_depois: int
	erros: tuple[str, ...] = field(default=())


def carga(horario: Horario) -> int:
	return sum(p.fim - p.inicio for periodos in horario.values() for p in periodos)


def _noturno_do_dia(periodos) -> int:
	total = 0
	for p in periodos:
		for inicio, fim in ((NOITE_INICIO - 1440, NOITE_FIM - 1440), (NOITE_INICIO, NOITE_FIM)):
			total += max(0, min(p.fim, fim) - max(p.inicio, inicio))
	return total


def noturno(horario: Horario) -> int:
	return sum(_noturno_do_dia(periodos) for periodos in horario.values())


def turno(periodos) -> str:
	inicio = periodos[0].inicio % 1440
	return "manhã" if inicio < 12 * 60 else ("tarde" if inicio < 18 * 60 else "noite")


def erros_legais(horario: Horario, ctx: Contexto) -> list[str]:
	# uma semana de exemplo (segunda 05/01/2026) com a semana anterior igual, para a interjornada de segunda
	base = date(2026, 1, 5)
	dias = [
		DiaEscala(base + timedelta(days=dia + 7 * semana), TRABALHO, periodos)
		for semana in (-1, 0)
		for dia, periodos in horario.items()
		if periodos
	]
	p = ev.Parametros(intervalo_minimo=ctx.intervalo_minimo, jornada_fragmentada=ctx.jornada_fragmentada)
	erros = sorted(
		{
			f"{DIAS[q.data.weekday()]}: {q.mensagem.split(': ', 1)[-1]}"
			for q in ev.quebras_da_escala(dias, p)
			if q.data >= base
			and q.tipo in (ev.EXCESSO, ev.INTERVALO, ev.INTERJORNADA, ev.SOBREPOSICAO, ev.INTERVALO_LONGO)
		}
	)
	if carga(horario) > d.CARGA_SEMANAL_MAXIMA_MIN:
		erros.append(
			f"carga semanal de {carga(horario) // 60}h{carga(horario) % 60:02d}, acima de 44h (CF art. 7º, XIII)."
		)
	return erros


def classificar(antes: Horario, depois: Horario, ctx: Contexto | None = None) -> Classificacao:
	ctx = ctx or Contexto()
	carga_antes, carga_depois = carga(antes), carga(depois)
	noturno_antes, noturno_depois = noturno(antes), noturno(depois)
	erros = erros_legais(depois, ctx)
	if ctx.reduz_salario:
		erros.append("o novo horário reduz o salário (CLT art. 468: nula mesmo com assinatura).")
	resumo = (carga_antes, carga_depois, noturno_antes, noturno_depois)
	if erros:
		return Classificacao(PROIBIDA, tuple(erros), *resumo, erros=tuple(erros))
	motivos = []
	if carga_antes != carga_depois:
		motivos.append(
			f"carga semanal muda de {carga_antes // 60}h{carga_antes % 60:02d} para {carga_depois // 60}h{carga_depois % 60:02d}."
		)
	if ctx.horista and ctx.minimo_horas_antes != ctx.minimo_horas_depois:
		motivos.append("muda as horas garantidas do horista.")
	if noturno_depois > noturno_antes:
		motivos.append("passa a ter (mais) trabalho noturno.")
	dias_antes = {dia for dia, periodos in antes.items() if periodos}
	dias_depois = {dia for dia, periodos in depois.items() if periodos}
	if dias_antes != dias_depois:
		motivos.append("muda os dias trabalhados.")
	for dia in sorted(dias_antes & dias_depois):
		if turno(antes[dia]) != turno(depois[dia]):
			motivos.append(
				f"{DIAS[dia]}: troca do turno da {turno(antes[dia])} para o da {turno(depois[dia])}."
			)
	if ctx.he_habituais:
		motivos.append("tira horas extras habituais (Súmula 291).")
	if motivos:
		return Classificacao(CONCORDANCIA, tuple(motivos), *resumo)
	observacao = (
		("deixa o trabalho noturno: o adicional deixa de ser devido (Súmula 265).",)
		if noturno_depois < noturno_antes
		else ("ajuste no mesmo turno, sem mudar dias, carga nem adicionais.",)
	)
	return Classificacao(CIENCIA, observacao, *resumo)


def resumo_do_horario(horario: Horario) -> str:
	"""'seg-sex 08:00-12:00, 13:00-17:00; sáb 08:00-12:00' (dias seguidos com o mesmo horário juntos)."""

	def hhmm(m):
		m %= 1440
		return f"{m // 60:02d}:{m % 60:02d}"

	grupos: list[tuple[list[int], str]] = []
	for dia in range(7):
		periodos = horario.get(dia) or ()
		if not periodos:
			continue
		texto = ", ".join(f"{hhmm(p.inicio)}-{hhmm(p.fim)}" for p in periodos)
		if grupos and grupos[-1][1] == texto and grupos[-1][0][-1] == dia - 1:
			grupos[-1][0].append(dia)
		else:
			grupos.append(([dia], texto))
	partes = []
	for dias, texto in grupos:
		nome = DIAS[dias[0]][:3] if len(dias) == 1 else f"{DIAS[dias[0]][:3]}-{DIAS[dias[-1]][:3]}"
		partes.append(f"{nome} {texto}")
	return "; ".join(partes) or "sem dias de trabalho"


def mesmo_horario(a: Horario, b: Horario) -> bool:
	return {k: tuple(v) for k, v in a.items() if v} == {k: tuple(v) for k, v in b.items() if v}
