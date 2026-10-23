"""Escala do mês, repouso semanal e conferências de descanso (AJ-02 e AJ-09 do docs/PRD-alteracoes.md).

- Cada dia da escala é Trabalho, Repouso semanal, Folga compensada ou Neutro (rodízio: sem falta, horas
  normais se trabalhar). Semana = segunda a domingo.
- Toda semana inteira precisa de exatamente um repouso (AJ-02). Sem escala, o repouso padrão é o domingo, se
  for folga; senão a primeira folga da semana (ou o dia da semana configurado no perfil).
- Avisos (não impedem): interjornada menor que o mínimo, jornada longa sem intervalo, 7 dias seguidos de
  trabalho e domingos seguidos sem folga acima do limite (mulher 2, homem 3 — Lei 10.101/2000).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import MEDIA, Inconsistencia

TRABALHO = "Trabalho"
REPOUSO = "Repouso semanal"
FOLGA_COMPENSADA = "Folga compensada"
NEUTRO = "Neutro"
SITUACOES = (TRABALHO, REPOUSO, FOLGA_COMPENSADA, NEUTRO)
DIAS_SEMANA = (
	"Segunda-feira",
	"Terça-feira",
	"Quarta-feira",
	"Quinta-feira",
	"Sexta-feira",
	"Sábado",
	"Domingo",
)


@dataclass(frozen=True)
class DiaEscala:
	data: date
	situacao: str
	periodos: tuple[Periodo, ...] = ()

	@property
	def trabalho(self) -> bool:
		return self.situacao == TRABALHO and bool(self.periodos)

	@property
	def minutos(self) -> int:
		return sum(p.fim - p.inicio for p in self.periodos)


def segunda_da_semana(dia: date) -> date:
	return dia - timedelta(days=dia.weekday())


def repouso_padrao(folgas_da_semana: Iterable[date], preferencia: str = d.REPOUSO_PADRAO) -> date | None:
	"""Qual folga da semana é o repouso quando a escala não marca (AJ-02)."""
	folgas = sorted(folgas_da_semana)
	if not folgas:
		return None
	if preferencia in DIAS_SEMANA:
		preferido = DIAS_SEMANA.index(preferencia)
		escolhido = next((f for f in folgas if f.weekday() == preferido), None)
		if escolhido:
			return escolhido
	domingo = next((f for f in folgas if f.weekday() == 6), None)
	return domingo or folgas[0]


def erros_repouso(dias: Iterable[DiaEscala], inicio: date, fim: date) -> list[str]:
	"""Semana inteira dentro do período: exatamente um repouso. Semana parcial: no máximo um."""
	por_semana: dict[date, list[DiaEscala]] = defaultdict(list)
	for dia in dias:
		if inicio <= dia.data <= fim:
			por_semana[segunda_da_semana(dia.data)].append(dia)
	erros = []
	for segunda in sorted(por_semana):
		repousos = [x for x in por_semana[segunda] if x.situacao == REPOUSO]
		inteira = segunda >= inicio and segunda + timedelta(days=6) <= fim
		semana = f"semana de {segunda:%d/%m}"
		if len(repousos) > 1:
			erros.append(f"{semana}: {len(repousos)} dias marcados como repouso semanal; marque só um.")
		elif inteira and not repousos:
			erros.append(f"{semana}: nenhum dia marcado como repouso semanal.")
	return erros


def _fim_do_dia(dia: DiaEscala) -> int:
	return max(p.fim for p in dia.periodos)


def _inicio_do_dia(dia: DiaEscala) -> int:
	return min(p.inicio for p in dia.periodos)


def avisos_escala(
	dias: Iterable[DiaEscala],
	*,
	interjornada_minima: int = d.INTERJORNADA_MIN,
	limite_domingos: int = d.DOMINGOS_SEGUIDOS_HOMEM,
	conferir_a_partir_de: date | None = None,
) -> list[str]:
	"""Avisos da escala (não bloqueiam). `dias` pode incluir dias anteriores ao mês (para as sequências);
	só são avisados problemas em datas a partir de `conferir_a_partir_de`."""
	ordenados = sorted(dias, key=lambda x: x.data)
	inicio = conferir_a_partir_de or (ordenados[0].data if ordenados else None)
	avisos = []
	anterior: DiaEscala | None = None
	seguidos = 0
	domingos = 0
	for dia in ordenados:
		conferir = inicio is not None and dia.data >= inicio
		if dia.trabalho:
			if anterior and anterior.trabalho and anterior.data + timedelta(days=1) == dia.data:
				descanso = 1440 - _fim_do_dia(anterior) + _inicio_do_dia(dia)
				if descanso < interjornada_minima and conferir:
					avisos.append(
						f"{dia.data:%d/%m}: descanso de {descanso // 60}h{descanso % 60:02d} desde o dia anterior, "
						f"abaixo de {interjornada_minima // 60}h (art. 66)."
					)
			maior_intervalo = max(
				(b.inicio - a.fim for a, b in zip(dia.periodos, dia.periodos[1:], strict=False)), default=0
			)
			if (
				dia.minutos > d.JORNADA_INTERVALO_CURTO_ATE_MIN
				and maior_intervalo < d.INTERVALO_MINIMO_MIN
				and conferir
			):
				avisos.append(f"{dia.data:%d/%m}: jornada de mais de 6h sem 1h de intervalo (art. 71).")
			seguidos = seguidos + 1 if anterior and anterior.data + timedelta(days=1) == dia.data else 1
			if seguidos == 7 and conferir:
				avisos.append(
					f"{dia.data:%d/%m}: 7º dia seguido de trabalho, sem repouso (OJ 410: repouso em dobro)."
				)
		else:
			seguidos = 0
		if dia.data.weekday() == 6:
			domingos = domingos + 1 if dia.trabalho else 0
			if domingos >= limite_domingos and conferir:
				avisos.append(
					f"{dia.data:%d/%m}: {domingos}º domingo seguido de trabalho; a folga no domingo deve vir a cada "
					f"{limite_domingos} semanas."
				)
			elif domingos == limite_domingos - 1 and dia.trabalho and conferir:
				avisos.append(f"{dia.data:%d/%m}: o próximo domingo precisa ser de folga.")
		anterior = dia
	return avisos


def limite_domingos(genero: str | None, limite_mulher: int, limite_homem: int) -> int:
	return (
		limite_mulher if (genero or "").strip().lower() in ("female", "feminino", "mulher") else limite_homem
	)


def inconsistencia_domingos(domingos_trabalhados: Iterable[bool], limite: int) -> Inconsistencia | None:
	"""Pelas batidas: domingos trabalhados seguidos (do mais antigo ao mais recente) até o limite (AJ-09)."""
	seguidos = 0
	for trabalhou in domingos_trabalhados:
		seguidos = seguidos + 1 if trabalhou else 0
	if seguidos >= limite:
		return Inconsistencia(
			"domingos_sem_folga",
			MEDIA,
			f"{seguidos} domingos seguidos de trabalho; a folga no domingo deve vir a cada {limite} semanas "
			"(Lei 10.101/2000, art. 6º).",
		)
	return None
