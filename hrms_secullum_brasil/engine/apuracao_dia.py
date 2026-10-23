"""Apuração de um dia de trabalho (PRD, 5.1 a 5.6 e 5.9). Orquestra os módulos do engine."""

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.horas_extras import distribuir_em_faixas, tipo_do_dia
from hrms_secullum_brasil.engine.intervalos import interjornada_suprimida, intrajornada
from hrms_secullum_brasil.engine.models import ALTA, BAIXA, MEDIA, EntradaDia, Inconsistencia, ResultadoDia
from hrms_secullum_brasil.engine.noturno import minutos_fictos, minutos_noturnos
from hrms_secullum_brasil.engine.pareamento import (
	inconsistencia_duplicadas,
	minutos_relativos,
	parear,
	remover_duplicadas,
	truncar,
)
from hrms_secullum_brasil.engine.tolerancia import apurar_saldo


def apurar_dia(entrada: EntradaDia) -> ResultadoDia:
	regra = entrada.regra
	setimo_dia = entrada.setimo_dia and bool(entrada.marcacoes)
	previsto = 0 if entrada.feriado or setimo_dia else entrada.jornada.minutos
	resultado = ResultadoDia(
		data=entrada.data,
		tipo_dia=tipo_do_dia(
			entrada.data,
			feriado=entrada.feriado,
			folga=entrada.jornada.folga and not entrada.horista,
			repouso=None if entrada.horista else entrada.repouso,
		),
		previsto=previsto,
	)
	if setimo_dia:
		# AJ-10 / OJ 410: 7º dia seguido de trabalho é pago em dobro — todas as horas como HE de repouso
		if not entrada.feriado:
			resultado.tipo_dia = d.TIPO_DIA_FOLGA
		resultado.inconsistencias.append(
			Inconsistencia(
				"sete_dias_seguidos",
				ALTA,
				"7º dia seguido de trabalho sem repouso: horas pagas em dobro (OJ 410 SDI-1 TST).",
			)
		)
	consideradas, ignoradas = remover_duplicadas(
		(truncar(m) for m in entrada.marcacoes), regra.duplicidade_minutos
	)
	resultado.marcacoes_consideradas = consideradas
	resultado.marcacoes_ignoradas = ignoradas
	duplicadas = inconsistencia_duplicadas(ignoradas, regra.duplicidade_minutos, regra.ignorar_duplicadas)
	if duplicadas:
		resultado.inconsistencias.append(Inconsistencia(*duplicadas))
		if not regra.ignorar_duplicadas:
			resultado.apurado = False
			return resultado

	if not consideradas:
		if entrada.horista and not entrada.horista_escalado:
			resultado.previsto = 0
			return resultado
		if entrada.abonado:
			resultado.normais = previsto
		elif previsto:
			resultado.falta = previsto
			resultado.inconsistencias.append(Inconsistencia("falta", MEDIA, "Dia previsto sem marcação."))
		return resultado

	pares_dt = parear(consideradas)
	if pares_dt is None:
		resultado.apurado = False
		resultado.inconsistencias.append(
			Inconsistencia("marcacao_impar", ALTA, f"{len(consideradas)} marcações: dia não apurado.")
		)
		return resultado

	pares = [(minutos_relativos(e, entrada.data), minutos_relativos(s, entrada.data)) for e, s in pares_dt]
	resultado.trabalhado = sum(s - e for e, s in pares)

	if ((entrada.horista and entrada.horista_escalado) or entrada.jornada.neutro) and not setimo_dia:
		# AJ-14: horista por escala não ganha HE por trabalhar em folga ou fim de semana; só acima de 8h no dia
		# (44h na semana: DSR Semanal) ou em feriado sem folga compensatória. Sem tolerância: paga o trabalhado.
		# O dia neutro do Secullum (rodízio) segue a mesma regra.
		feriado_pago = entrada.feriado and not entrada.feriado_compensado
		resultado.tipo_dia = tipo_do_dia(entrada.data, feriado=feriado_pago, folga=False, repouso=False)
		normais = 0 if feriado_pago else min(resultado.trabalhado, d.JORNADA_DIARIA_MAXIMA_MIN)
		previsto, atraso, hora_extra = normais, 0, resultado.trabalhado - normais
	elif (
		entrada.horista
		and not setimo_dia
		and resultado.tipo_dia not in (d.TIPO_DIA_DOMINGO, d.TIPO_DIA_FERIADO)
	):
		# sem jornada prevista: o trabalhado é a jornada do dia, até o limite legal de 8h
		previsto = resultado.previsto = min(resultado.trabalhado, d.JORNADA_DIARIA_MAXIMA_MIN)
		atraso, hora_extra = 0, resultado.trabalhado - previsto
	elif previsto:
		atraso, hora_extra = apurar_saldo(
			pares, entrada.jornada.periodos, resultado.trabalhado, previsto, regra
		)
	elif entrada.feriado and entrada.feriado_compensado:
		# AJ-03: feriado trabalhado com folga compensatória: as horas viram normais, sem HE
		previsto, atraso, hora_extra = resultado.trabalhado, 0, 0
	else:
		atraso, hora_extra = 0, resultado.trabalhado  # folga ou feriado: todo o tempo é extra
	if entrada.abonado:
		atraso = 0
	resultado.atraso = atraso
	resultado.normais = previsto - atraso
	resultado.hora_extra = hora_extra
	resultado.he_faixas = distribuir_em_faixas(hora_extra, resultado.tipo_dia, regra.faixas_he)
	if atraso:
		resultado.inconsistencias.append(
			Inconsistencia("atraso", BAIXA, f"{atraso} min de atraso/saída antecipada.")
		)
	if hora_extra > regra.limite_he_diaria:
		resultado.inconsistencias.append(
			Inconsistencia(
				"he_acima_limite",
				MEDIA,
				f"{hora_extra} min de HE, acima de {regra.limite_he_diaria} min (Art. 59).",
			)
		)

	resultado.noturno_real = minutos_noturnos(pares, regra)
	resultado.noturno_ficto = minutos_fictos(resultado.noturno_real, regra.minutos_hora_noturna)

	resultado.intrajornada_suprimida, avisos = intrajornada(
		pares, regra, permite_estendido=entrada.jornada.permite_intervalo_estendido
	)
	if (
		entrada.horista
		and entrada.tolerancia_aviso_intervalo
		and resultado.trabalhado <= regra.jornada_sem_intervalo_ate + entrada.tolerancia_aviso_intervalo
	):
		# poucos minutos além das 4h: quem acompanha é o monitoramento do mês (Alerta Horista), sem poluir o dia
		avisos = [a for a in avisos if a.tipo != "intrajornada"]
	resultado.inconsistencias += avisos

	resultado.interjornada_suprimida = interjornada_suprimida(
		consideradas[0], entrada.marcacoes_dia_anterior, regra.interjornada_minima
	)
	if resultado.interjornada_suprimida:
		resultado.inconsistencias.append(
			Inconsistencia(
				"interjornada",
				MEDIA,
				f"Descanso entre jornadas {resultado.interjornada_suprimida} min abaixo do mínimo de {regra.interjornada_minima} min.",
			)
		)
	if entrada.estagio:
		_aplicar_estagio(resultado, entrada)
	return resultado


SEM_EFEITO_NO_ESTAGIO = ("he_acima_limite", "intrajornada", "interjornada")


def _aplicar_estagio(resultado: ResultadoDia, entrada: EntradaDia) -> None:
	"""EST-04: o que passa do previsto (ou da carga diária do TCE) não é hora extra nem banco: fica em
	`excesso_estagio` com inconsistência Alta (risco de vínculo CLT). Sem intervalo indenizado nem
	interjornada paga; o noturno fica só para conferência. Atraso e falta continuam (descontam a bolsa)."""
	excesso = resultado.hora_extra
	limite = entrada.limite_diario_estagio
	if limite and resultado.normais > limite:
		excesso += resultado.normais - limite
		resultado.normais = limite
	resultado.hora_extra = 0
	resultado.he_faixas = []
	resultado.intrajornada_suprimida = resultado.interjornada_suprimida = 0
	resultado.inconsistencias = [i for i in resultado.inconsistencias if i.tipo not in SEM_EFEITO_NO_ESTAGIO]
	if excesso > 0:
		resultado.excesso_estagio = excesso
		resultado.inconsistencias.append(
			Inconsistencia(
				"excesso_jornada_estagio",
				ALTA,
				f"Jornada de estágio passou do limite do TCE em {excesso} min (risco de vínculo CLT).",
			)
		)
