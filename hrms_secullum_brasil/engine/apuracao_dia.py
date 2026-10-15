"""Apuração de um dia de trabalho (PRD, 5.1 a 5.6 e 5.9). Orquestra os módulos do engine."""

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.horas_extras import distribuir_em_faixas, tipo_do_dia
from hrms_secullum_brasil.engine.intervalos import interjornada_suprimida, intrajornada
from hrms_secullum_brasil.engine.models import ALTA, BAIXA, MEDIA, EntradaDia, Inconsistencia, ResultadoDia
from hrms_secullum_brasil.engine.noturno import minutos_fictos, minutos_noturnos
from hrms_secullum_brasil.engine.pareamento import minutos_relativos, parear, remover_duplicadas, truncar
from hrms_secullum_brasil.engine.tolerancia import apurar_saldo


def apurar_dia(entrada: EntradaDia) -> ResultadoDia:
	regra = entrada.regra
	previsto = 0 if entrada.feriado else entrada.jornada.minutos
	resultado = ResultadoDia(
		data=entrada.data,
		tipo_dia=tipo_do_dia(
			entrada.data, feriado=entrada.feriado, folga=entrada.jornada.folga and not entrada.horista
		),
		previsto=previsto,
	)
	consideradas, ignoradas = remover_duplicadas(
		(truncar(m) for m in entrada.marcacoes), regra.duplicidade_minutos
	)
	resultado.marcacoes_consideradas = consideradas
	resultado.marcacoes_ignoradas = ignoradas
	if ignoradas:
		resultado.inconsistencias.append(
			Inconsistencia(
				"marcacao_duplicada",
				BAIXA,
				f"{len(ignoradas)} marcação(ões) a menos de {regra.duplicidade_minutos} min da anterior ignorada(s).",
			)
		)

	if not consideradas:
		if entrada.horista:
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

	if entrada.horista and resultado.tipo_dia not in (d.TIPO_DIA_DOMINGO, d.TIPO_DIA_FERIADO):
		# sem jornada prevista: o trabalhado é a jornada do dia, até o limite legal de 8h
		previsto = resultado.previsto = min(resultado.trabalhado, d.JORNADA_DIARIA_MAXIMA_MIN)
		atraso, hora_extra = 0, resultado.trabalhado - previsto
	elif previsto:
		atraso, hora_extra = apurar_saldo(
			pares, entrada.jornada.periodos, resultado.trabalhado, previsto, regra
		)
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
	return resultado
