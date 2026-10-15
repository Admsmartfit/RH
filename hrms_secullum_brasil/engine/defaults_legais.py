"""Valores padrão legais (PRD, Seção 5).

São o ponto de partida de cada Regra Sindical CCT; a CCT pode alterá-los. Os mesmos valores
aparecem como `default` nos JSONs dos DocTypes — engine/tests/test_defaults_legais.py garante
que os dois lados não divergem. Nenhuma regra legal deve ser codificada fora deste arquivo.
"""

from dataclasses import dataclass, field

# Tipos de dia usados na tabela de horas extras (Select "tipo_dia" de Faixa Hora Extra).
TIPO_DIA_UTIL = "Útil"
TIPO_DIA_SABADO = "Sábado"
TIPO_DIA_DOMINGO = "Domingo"
TIPO_DIA_FERIADO = "Feriado"
TIPO_DIA_FOLGA = "Folga"
TIPOS_DIA = (TIPO_DIA_UTIL, TIPO_DIA_SABADO, TIPO_DIA_DOMINGO, TIPO_DIA_FERIADO, TIPO_DIA_FOLGA)

# 5.2 Tolerância — Art. 58, §1º CLT
TOLERANCIA_POR_MARCACAO_MIN = 5
TOLERANCIA_DIARIA_MIN = 10
COMPUTAR_TODO_TEMPO_AO_EXCEDER = True  # passou de 10 min no dia: computa tudo, não só o excedente

# 5.1 Pareamento: marcações a menos de N minutos da anterior são duplicidade (ignoradas e sinalizadas)
DUPLICIDADE_MIN = 2

# Atraso e HE do mesmo dia se compensam (saldo do dia). Decisão do negócio de 14/10/2026; desligado,
# cada marcação fora do previsto é computada separadamente ("todo o tempo computado", PRD T3).
COMPENSAR_ATRASO_COM_HE = True

# 5.3 Horas extras — Art. 59 caput e Art. 7º, XVI CF (adicional mínimo de 50%)
LIMITE_HE_DIARIA_MIN = 120
PERCENTUAL_MINIMO_HE = 50


@dataclass(frozen=True)
class FaixaHE:
	tipo_dia: str
	de_min: int
	ate_min: int  # 0 = sem limite superior
	percentual: float
	vai_para_banco: bool = field(default=False, compare=False)  # se o colaborador participa do banco de horas


# Domingo e feriado não compensados: 100% (Lei 605/1949, Art. 9º; Súmula 146 TST).
# Folga = repouso semanal remunerado de quem trabalha em escala, mesmo tratamento do domingo.
# Banco de horas (decisão do negócio de 15/10/2026): só HE de dia útil e sábado vão ao banco.
FAIXAS_HE_PADRAO = (
	FaixaHE(TIPO_DIA_UTIL, 0, 0, 50, vai_para_banco=True),
	FaixaHE(TIPO_DIA_SABADO, 0, 0, 50, vai_para_banco=True),
	FaixaHE(TIPO_DIA_DOMINGO, 0, 0, 100),
	FaixaHE(TIPO_DIA_FERIADO, 0, 0, 100),
	FaixaHE(TIPO_DIA_FOLGA, 0, 0, 100),
)

# 5.4 Adicional noturno — Art. 73 CLT (trabalhador urbano)
NOTURNO_INICIO = "22:00:00"
NOTURNO_FIM = "05:00:00"
MINUTOS_HORA_NOTURNA = 52.5  # hora ficta de 52min30s
PERCENTUAL_ADICIONAL_NOTURNO = 20
PRORROGACAO_NOTURNA = True  # Súmula 60, II TST

# 5.5 Intrajornada — Art. 71 CLT
JORNADA_SEM_INTERVALO_ATE_MIN = 240  # até 4h: intervalo não obrigatório
INTERVALO_CURTO_MIN = 15  # > 4h até 6h
JORNADA_INTERVALO_CURTO_ATE_MIN = 360
INTERVALO_MINIMO_MIN = 60  # > 6h
INTERVALO_MAXIMO_MIN = 120
PERMITE_REDUCAO_INTRAJORNADA = False
INTERVALO_REDUZIDO_MIN = 30  # piso legal da redução por CCT — Art. 611-A, III
PERCENTUAL_INDENIZACAO_INTRAJORNADA = 50  # Art. 71, §4º

# 5.6 Interjornada — Arts. 66 e 67 CLT
INTERJORNADA_MIN = 660  # 11h
DESCANSO_SEMANAL_MIN = 2100  # 24h + 11h

# 5.7 DSR — Lei 605/1949; Súmula 172 TST
DSR_PERDE_POR_FALTA = True
DSR_PERDE_FERIADO_DA_SEMANA = False
DSR_PERDE_POR_ATRASO = False  # tema controverso: desligado por padrão
DSR_REFLEXO_HE_NOTURNO = True

# 5.8 Banco de horas — Art. 59, §§2º, 5º e 6º CLT
BANCO_MENSAL = "Mensal"  # acordo individual, inclusive tácito: compensação no mesmo mês
BANCO_SEMESTRAL = "Semestral"  # acordo individual escrito
BANCO_ANUAL = "Anual"  # CCT/ACT
PRAZO_MAXIMO_BANCO_MESES = {BANCO_MENSAL: 1, BANCO_SEMESTRAL: 6, BANCO_ANUAL: 12}
BANCO_MODALIDADE_PADRAO = BANCO_MENSAL
BANCO_ALERTA_VENCIMENTO_DIAS = 30
BANCO_PERMITE_DESCONTAR_SALDO_NEGATIVO = False
BANCO_DEBITA_ATRASOS = (
	True  # atrasos/saídas antecipadas debitam o banco; faltas continuam descontadas em folha
)

# 5.10 Professores — Art. 320 CLT
SEMANAS_MES_PROFESSOR = 4.5

# Jornada contratual
JORNADA_DIARIA_MAXIMA_MIN = 480  # Art. 58: acima disso, o horista/intermitente faz hora extra
DIVISOR_PADRAO = 220
CARGA_SEMANAL_MAXIMA_MIN = 2640  # 44h — Art. 7º, XIII CF
