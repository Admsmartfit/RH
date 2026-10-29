"""Validação CLT da escala do cockpit e soluções (docs/PRD-cockpit-escalas.md, CE-04 e CE-05). Python puro.

- Entrada: os dias da escala do colaborador (mês anterior ao seguinte, inclusive os dias escondidos pelo filtro
  "fim de semana e feriados"), o que já aconteceu (batidas reais dos dias passados, que valem no lugar da escala)
  e as alterações propostas.
- Quebras: interjornada (art. 66), intervalo (art. 71), intervalo acima de 2h sem jornada fragmentada, excesso
  acima de 10h (art. 59 — única que bloqueia, DE-6), 7º dia seguido (OJ 410), domingos (art. 386 / Lei 10.101),
  feriado sem folga (modo e prazo da CCT, DE-5), indisponibilidade, antecedência (DE-7) e sobreposição de turnos.
- Soluções: A — ajuste de horário que tira a quebra sem criar outra; B — colegas sem conflito para o turno.
  C (manter com justificativa) é decisão do gestor: `bloqueia` e `exige_justificativa` dizem o que é possível.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from itertools import pairwise

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.escala import NEUTRO, REPOUSO, TRABALHO, DiaEscala, segunda_da_semana
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

# tipos de quebra
INTERJORNADA = "interjornada"
INTERVALO = "intervalo"
INTERVALO_LONGO = "intervalo_longo"
EXCESSO = "excesso"
SETIMO_DIA = "setimo_dia"
DOMINGOS = "domingos"
FERIADO_SEM_FOLGA = "feriado_sem_folga"
INDISPONIBILIDADE = "indisponibilidade"
ANTECEDENCIA = "antecedencia"
SOBREPOSICAO = "sobreposicao"
TIPOS = (
	INTERJORNADA,
	INTERVALO,
	INTERVALO_LONGO,
	EXCESSO,
	SETIMO_DIA,
	DOMINGOS,
	FERIADO_SEM_FOLGA,
	INDISPONIBILIDADE,
	ANTECEDENCIA,
	SOBREPOSICAO,
)
# gravidade
BLOQUEIA = "Bloqueia"
JUSTIFICAR = "Justificar"
BLOQUEANTES = frozenset({EXCESSO, SOBREPOSICAO})

FOLGA_COMPENSADA = "Folga compensada"


@dataclass(frozen=True)
class Quebra:
	tipo: str
	data: date
	mensagem: str  # em linguagem de RH
	minutos: int = 0  # quanto falta/sobra (base do custo, CE-06)

	@property
	def gravidade(self) -> str:
		return BLOQUEIA if self.tipo in BLOQUEANTES else JUSTIFICAR

	@property
	def chave(self) -> tuple[str, date]:
		return (self.tipo, self.data)


@dataclass(frozen=True)
class Indisponibilidade:
	inicio: date
	fim: date
	periodo: Periodo | None = None  # None = o dia inteiro
	motivo: str = ""

	def conflita(self, dia: DiaEscala) -> bool:
		if not (self.inicio <= dia.data <= self.fim) or not dia.trabalho:
			return False
		if self.periodo is None:
			return True
		return any(p.inicio < self.periodo.fim and self.periodo.inicio < p.fim for p in dia.periodos)


@dataclass(frozen=True)
class Parametros:
	interjornada_minima: int = d.INTERJORNADA_MIN
	intervalo_minimo: int = d.INTERVALO_MINIMO_MIN  # jornada acima de 6h (ou o reduzido da CCT)
	intervalo_curto: int = d.INTERVALO_CURTO_MIN  # acima de 4h até 6h
	intervalo_maximo: int = d.INTERVALO_MAXIMO_MIN
	jornada_fragmentada: bool = False  # parâmetro do cargo/perfil: intervalo acima de 2h permitido
	jornada_maxima: int = d.JORNADA_MAXIMA_COM_HE_MIN
	limite_domingos: int = d.DOMINGOS_SEGUIDOS_HOMEM
	feriados: frozenset[date] = frozenset()
	modo_feriado: str = d.FERIADO_TRABALHADO_PADRAO
	prazo_folga_feriado_dias: int = d.PRAZO_FOLGA_FERIADO_DIAS
	antecedencia: int = d.ANTECEDENCIA_ESCALA_MIN
	indisponibilidades: tuple[Indisponibilidade, ...] = ()


@dataclass(frozen=True)
class SolucaoAjuste:
	"""Solução A: o dia ajustado e o que ele resolve."""

	descricao: str
	dia: DiaEscala
	resolve: tuple[str, ...]


@dataclass(frozen=True)
class Colega:
	"""Candidato da solução B: a escala dele e os parâmetros (CCT, cargo, gênero, indisponibilidades)."""

	employee: str
	nome: str
	dias: tuple[DiaEscala, ...]
	parametros: Parametros = field(default_factory=Parametros)
	realizados: Mapping[date, DiaEscala] = field(default_factory=dict)


@dataclass(frozen=True)
class Substituto:
	employee: str
	nome: str
	minutos_semana: int  # carga já escalada na semana do turno (menor primeiro)


def _hhmm(minutos: int) -> str:
	minutos %= 1440
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _duracao(minutos: int) -> str:
	return f"{minutos // 60}h{minutos % 60:02d}"


def _trabalho(data: date, periodos: Iterable[Periodo]) -> DiaEscala:
	return DiaEscala(data, TRABALHO, tuple(sorted(periodos, key=lambda p: p.inicio)))


# ------------------------------------------------------------------ montagem


def combinar(
	dias: Iterable[DiaEscala],
	alteracoes: Iterable[DiaEscala] = (),
	realizados: Mapping[date, DiaEscala] | None = None,
) -> list[DiaEscala]:
	"""Escala vigente com as alterações; dias passados usam o realizado (batidas), salvo se alterados agora."""
	por_data = {dia.data: dia for dia in dias}
	alterados = {dia.data: dia for dia in alteracoes}
	for data, realizado in (realizados or {}).items():
		if data not in alterados:
			por_data[data] = realizado
	por_data.update(alterados)
	return [por_data[data] for data in sorted(por_data)]


# ------------------------------------------------------------------ quebras


def _intervalos(dia: DiaEscala) -> list[int]:
	return [b.inicio - a.fim for a, b in pairwise(dia.periodos)]


def _quebras_do_dia(dia: DiaEscala, p: Parametros) -> list[Quebra]:
	quebras = []
	periodos = dia.periodos
	sobrepostos = any(b.inicio < a.fim for a, b in pairwise(periodos))
	if sobrepostos:
		quebras.append(Quebra(SOBREPOSICAO, dia.data, f"{dia.data:%d/%m}: dois turnos no mesmo horário."))
		return quebras
	trabalhado = dia.minutos
	if trabalhado > p.jornada_maxima:
		quebras.append(
			Quebra(
				EXCESSO,
				dia.data,
				f"{dia.data:%d/%m}: {_duracao(trabalhado)} de trabalho no dia; o máximo é "
				f"{_duracao(p.jornada_maxima)} com as horas extras (art. 59).",
				trabalhado - p.jornada_maxima,
			)
		)
	# intervalo exigido pelo trecho contínuo mais longo e pela jornada do dia (art. 71)
	exigido = 0
	if trabalhado > d.JORNADA_INTERVALO_CURTO_ATE_MIN:
		exigido = p.intervalo_minimo
	elif trabalhado > d.JORNADA_SEM_INTERVALO_ATE_MIN:
		exigido = p.intervalo_curto
	intervalos = _intervalos(dia)
	if exigido and max(intervalos, default=0) < exigido:
		faltam = exigido - max(intervalos, default=0)
		quebras.append(
			Quebra(
				INTERVALO,
				dia.data,
				f"{dia.data:%d/%m}: jornada de {_duracao(trabalhado)} precisa de {exigido} min de intervalo "
				f"(art. 71); faltam {faltam} min.",
				faltam,
			)
		)
	longo = max(intervalos, default=0)
	if longo > p.intervalo_maximo and not p.jornada_fragmentada:
		quebras.append(
			Quebra(
				INTERVALO_LONGO,
				dia.data,
				f"{dia.data:%d/%m}: intervalo de {_duracao(longo)}, acima de 2h; só vale com jornada fragmentada "
				"liberada para o cargo (art. 71).",
				longo - p.intervalo_maximo,
			)
		)
	for indisponivel in p.indisponibilidades:
		if indisponivel.conflita(dia):
			motivo = f" ({indisponivel.motivo})" if indisponivel.motivo else ""
			quebras.append(
				Quebra(
					INDISPONIBILIDADE, dia.data, f"{dia.data:%d/%m}: o colaborador está indisponível{motivo}."
				)
			)
			break
	return quebras


def _limite_folga_feriado(feriado: date, prazo: int) -> date:
	if prazo > 0:
		return feriado + timedelta(days=prazo)
	return segunda_da_semana(feriado) + timedelta(days=6)


def quebras_da_escala(dias: Iterable[DiaEscala], p: Parametros) -> list[Quebra]:
	"""Todas as quebras da sequência de dias (ordenada por data)."""
	ordenados = sorted(dias, key=lambda x: x.data)
	quebras: list[Quebra] = []
	anterior: DiaEscala | None = None
	seguidos = 0
	domingos = 0
	ultimo: DiaEscala | None = None
	for dia in ordenados:
		if dia.trabalho:
			quebras.extend(_quebras_do_dia(dia, p))
			if anterior is not None:
				descanso = (dia.data - anterior.data).days * 1440 + min(x.inicio for x in dia.periodos)
				descanso -= max(x.fim for x in anterior.periodos)
				if descanso < p.interjornada_minima:
					faltam = p.interjornada_minima - descanso
					quebras.append(
						Quebra(
							INTERJORNADA,
							dia.data,
							f"{dia.data:%d/%m}: descanso de {_duracao(descanso)} desde o turno anterior; o mínimo é "
							f"{_duracao(p.interjornada_minima)} (art. 66).",
							faltam,
						)
					)
			consecutivo = (
				ultimo is not None and ultimo.data + timedelta(days=1) == dia.data and ultimo.trabalho
			)
			seguidos = seguidos + 1 if consecutivo else 1
			if seguidos >= 7:
				quebras.append(
					Quebra(
						SETIMO_DIA,
						dia.data,
						f"{dia.data:%d/%m}: {seguidos}º dia seguido de trabalho, sem repouso semanal (OJ 410: o "
						"repouso é pago em dobro).",
					)
				)
			if dia.data in p.feriados and p.modo_feriado != d.FERIADO_PAGAR:
				limite = _limite_folga_feriado(dia.data, p.prazo_folga_feriado_dias)
				folga = any(x.situacao == FOLGA_COMPENSADA and dia.data < x.data <= limite for x in ordenados)
				if not folga:
					quebras.append(
						Quebra(
							FERIADO_SEM_FOLGA,
							dia.data,
							f"{dia.data:%d/%m}: feriado trabalhado sem folga compensatória até {limite:%d/%m} (CCT).",
						)
					)
			anterior = dia
		else:
			seguidos = 0
		if dia.data.weekday() == 6:
			domingos = domingos + 1 if dia.trabalho else 0
			if dia.trabalho and domingos >= p.limite_domingos:
				quebras.append(
					Quebra(
						DOMINGOS,
						dia.data,
						f"{dia.data:%d/%m}: {domingos}º domingo seguido de trabalho; a folga no domingo deve vir a "
						f"cada {p.limite_domingos} semanas (art. 386 / Lei 10.101).",
					)
				)
		ultimo = dia
	return quebras


def _quebras_antecedencia(
	atuais: Mapping[date, DiaEscala], alteracoes: Iterable[DiaEscala], agora: datetime, p: Parametros
) -> list[Quebra]:
	quebras = []
	for novo in alteracoes:
		antigo = atuais.get(novo.data)
		if antigo is not None and antigo.situacao == novo.situacao and antigo.periodos == novo.periodos:
			continue
		inicios = [
			x.periodos[0].inicio for x in (antigo, novo) if x is not None and x.trabalho and x.periodos
		]
		if not inicios:
			continue
		comeco = datetime.combine(novo.data, datetime.min.time()) + timedelta(minutes=min(inicios))
		faltam = int((comeco - agora).total_seconds() // 60)
		if faltam < p.antecedencia:
			quando = "já começou" if faltam <= 0 else f"faltam {_duracao(faltam)}"
			quebras.append(
				Quebra(
					ANTECEDENCIA,
					novo.data,
					f"{novo.data:%d/%m}: mudança com menos de {p.antecedencia // 60}h de antecedência ({quando}); "
					"registre o motivo e avise o colaborador.",
					max(p.antecedencia - max(faltam, 0), 0),
				)
			)
	return quebras


def validar(
	dias: Iterable[DiaEscala],
	alteracoes: Sequence[DiaEscala],
	p: Parametros,
	*,
	agora: datetime | None = None,
	realizados: Mapping[date, DiaEscala] | None = None,
) -> list[Quebra]:
	"""Quebras que as alterações criam (as que já existiam antes ficam de fora) mais as do próprio dia alterado,
	e a antecedência (quando `agora` é informado)."""
	dias = list(dias)
	antes = quebras_da_escala(combinar(dias, (), realizados), p)
	depois = quebras_da_escala(combinar(dias, alteracoes, realizados), p)
	ja_havia = {q.chave for q in antes}
	alteradas = {x.data for x in alteracoes}
	resultado = [q for q in depois if q.chave not in ja_havia or q.data in alteradas]
	if agora is not None:
		atuais = {x.data: x for x in combinar(dias, (), realizados)}
		resultado.extend(_quebras_antecedencia(atuais, alteracoes, agora, p))
	return resultado


def bloqueia(quebras: Iterable[Quebra]) -> bool:
	return any(q.gravidade == BLOQUEIA for q in quebras)


def exige_justificativa(quebras: Iterable[Quebra]) -> bool:
	return any(q.gravidade == JUSTIFICAR for q in quebras)


# ------------------------------------------------------------------ solução A: ajuste de horário


def _deslocar(dia: DiaEscala, minutos: int) -> DiaEscala:
	return _trabalho(dia.data, (Periodo(x.inicio + minutos, x.fim + minutos) for x in dia.periodos))


def _com_pausa(dia: DiaEscala, pausa: int) -> DiaEscala:
	"""Intervalo de `pausa` minutos mantendo as horas trabalhadas: aumenta o maior intervalo que já existe ou divide
	o trecho mais longo ao meio; o que vem depois anda para mais tarde."""
	intervalos = _intervalos(dia)
	if intervalos:
		i = intervalos.index(max(intervalos))
		atraso = pausa - intervalos[i]
		antes, depois = list(dia.periodos[: i + 1]), dia.periodos[i + 1 :]
	else:
		trecho = dia.periodos[0]
		meio = trecho.inicio + (trecho.fim - trecho.inicio) // 2
		atraso = pausa
		antes, depois = [Periodo(trecho.inicio, meio)], (Periodo(meio, trecho.fim),)
	return _trabalho(dia.data, (*antes, *(Periodo(x.inicio + atraso, x.fim + atraso) for x in depois)))


def _encurtar(dia: DiaEscala, minutos: int) -> DiaEscala | None:
	ultimo = dia.periodos[-1]
	if ultimo.fim - minutos <= ultimo.inicio:
		return None
	return _trabalho(dia.data, (*dia.periodos[:-1], Periodo(ultimo.inicio, ultimo.fim - minutos)))


def _aproximar(dia: DiaEscala, minutos: int) -> DiaEscala:
	"""Traz os períodos depois do intervalo longo para mais cedo (intervalo de no máximo 2h)."""
	i = _intervalos(dia).index(max(_intervalos(dia)))
	novos = list(dia.periodos[: i + 1]) + [
		Periodo(x.inicio - minutos, x.fim - minutos) for x in dia.periodos[i + 1 :]
	]
	return _trabalho(dia.data, novos)


def _candidatos_ajuste(dia: DiaEscala, quebra: Quebra, p: Parametros) -> list[tuple[str, DiaEscala]]:
	if quebra.tipo == INTERJORNADA:
		depois = _deslocar(dia, quebra.minutos)
		return [(f"Começar {quebra.minutos} min mais tarde ({_hhmm(depois.periodos[0].inicio)})", depois)]
	if quebra.tipo == INTERVALO:
		exigido = p.intervalo_minimo if dia.minutos > d.JORNADA_INTERVALO_CURTO_ATE_MIN else p.intervalo_curto
		novo = _com_pausa(dia, exigido)
		pausas = ", ".join(f"{_hhmm(a.fim)} às {_hhmm(b.inicio)}" for a, b in pairwise(novo.periodos))
		return [
			(
				f"Incluir {exigido} min de intervalo ({pausas}), terminando às {_hhmm(novo.periodos[-1].fim)}",
				novo,
			)
		]
	if quebra.tipo == EXCESSO:
		novo = _encurtar(dia, quebra.minutos)
		return (
			[(f"Terminar às {_hhmm(novo.periodos[-1].fim)} (máximo de {_duracao(p.jornada_maxima)})", novo)]
			if novo
			else []
		)
	if quebra.tipo == INTERVALO_LONGO:
		novo = _aproximar(dia, quebra.minutos)
		return [
			(
				f"Voltar do intervalo às {_hhmm(novo.periodos[_intervalos(dia).index(max(_intervalos(dia))) + 1].inicio)} (intervalo de 2h)",
				novo,
			)
		]
	return []


def solucoes_ajuste(
	dias: Iterable[DiaEscala],
	alterado: DiaEscala,
	p: Parametros,
	*,
	realizados: Mapping[date, DiaEscala] | None = None,
) -> list[SolucaoAjuste]:
	"""Solução A para cada quebra do dia alterado: só entra o ajuste que resolve a quebra sem criar outra."""
	dias = list(dias)
	quebras = [q for q in validar(dias, [alterado], p, realizados=realizados) if q.data == alterado.data]
	solucoes = []
	for quebra in quebras:
		for descricao, novo in _candidatos_ajuste(alterado, quebra, p):
			restantes = validar(dias, [novo], p, realizados=realizados)
			if quebra.chave in {q.chave for q in restantes}:
				continue
			antes = {q.chave for q in quebras}
			if any(q.chave not in antes for q in restantes):
				continue
			resolvidas = tuple(sorted(q.tipo for q in quebras if q.chave not in {r.chave for r in restantes}))
			solucoes.append(SolucaoAjuste(descricao, novo, resolvidas))
	return solucoes


# ------------------------------------------------------------------ solução B: colega sem conflito


def _somar_turno(dia_atual: DiaEscala | None, turno: DiaEscala) -> DiaEscala:
	if dia_atual is None or not dia_atual.trabalho:
		return turno
	return _trabalho(turno.data, (*dia_atual.periodos, *turno.periodos))


def substitutos(
	turno: DiaEscala,
	colegas: Iterable[Colega],
	*,
	agora: datetime | None = None,
) -> list[Substituto]:
	"""Solução B: colegas que podem fazer o turno sem nenhuma quebra (soma ao que já têm no dia), com a menor carga
	da semana primeiro."""
	resultado = []
	semana = segunda_da_semana(turno.data)
	for colega in colegas:
		atuais = {x.data: x for x in combinar(colega.dias, (), colega.realizados)}
		proposto = _somar_turno(atuais.get(turno.data), turno)
		if validar(colega.dias, [proposto], colega.parametros, agora=agora, realizados=colega.realizados):
			continue
		carga = sum(
			x.minutos
			for data, x in atuais.items()
			if x.trabalho and semana <= data <= semana + timedelta(days=6)
		)
		resultado.append(Substituto(colega.employee, colega.nome, carga))
	return sorted(resultado, key=lambda s: (s.minutos_semana, s.nome))


def remover_turno(dia: DiaEscala) -> DiaEscala:
	"""O dia sem o turno (para o colaborador que cede o turno na solução B)."""
	return replace(dia, situacao=NEUTRO, periodos=())


# ------------------------------------------------------------------ repouso semanal (AJ-02)


def ajustar_repouso(dias: Iterable[DiaEscala], alteracoes: Sequence[DiaEscala]) -> list[DiaEscala]:
	"""Quando uma alteração tira o repouso da semana (ex.: turno no domingo de repouso), marca como repouso outro dia
	sem trabalho da mesma semana — o domingo, se livre; senão o último livre. Devolve só os dias a mudar; semana sem
	dia livre fica sem ajuste (a quebra do 7º dia aparece na validação)."""
	vigentes = {x.data: x for x in combinar(dias, alteracoes)}
	alterados = {x.data for x in alteracoes}
	ajustes = []
	for segunda in sorted({segunda_da_semana(x.data) for x in alteracoes}):
		semana = [vigentes.get(segunda + timedelta(days=i)) for i in range(7)]
		if any(x is not None and x.situacao == REPOUSO for x in semana):
			continue
		tinha = any(x.situacao == REPOUSO for x in dias if segunda <= x.data <= segunda + timedelta(days=6))
		if not tinha:
			continue
		livres = [x for x in semana if x is not None and not x.trabalho and x.data not in alterados]
		if not livres:
			continue
		domingo = next((x for x in livres if x.data.weekday() == 6), None)
		escolhido = domingo or livres[-1]
		ajustes.append(replace(escolhido, situacao=REPOUSO, periodos=()))
	return ajustes
