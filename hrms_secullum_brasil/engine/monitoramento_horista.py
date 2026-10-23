"""Monitoramento de horistas (docs/PRD-monitoramento-horistas.md, MH-02): dias além de 4h sem intervalo registrado.

Ocorrência (DH-1) = dia com trabalhado acima da jornada sem intervalo (240 min) e no máximo a tolerância além dela,
com intervalo suprimido. O aviso sai uma vez a cada limite atingido no mês (DH-2): 4, 8, 12... Python puro.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from hrms_secullum_brasil.engine import defaults_legais as d

TOLERANCIA_PADRAO = 15  # minutos além das 4h que contam como "esquecimento" da pausa
LIMITE_PADRAO = 4  # ocorrências no mês que disparam o alerta
HORA_INICIO_ENVIO, HORA_FIM_ENVIO = 8, 20  # DH-5: mensagem só entre 8h e 20h

MENSAGEM_HORISTA = """Olá, {primeiro_nome}!

Identificamos que no mês atual sua jornada ultrapassou o limite contratual de 4 horas em {ocorrencias} ocasiões \
(limite máximo tolerado: {limite}). Dias: {dias}.

Orientações importantes do RH:
1. Caso você tenha usufruído do seu intervalo de descanso/lanche (10 a 15 min) e apenas esquecido de registrar o \
ponto, procure imediatamente a gerência da sua unidade. Você deverá preencher e assinar o Termo de Ajuste para que o \
RH regularize sua folha.
2. Caso a permanência além das 4 horas tenha sido por extensão de aulas, alinhe imediatamente sua escala com a \
coordenação. A jornada contratual não prevê prorrogação rotineira.

Por favor, atente-se às marcações nos próximos dias para evitar advertências disciplinares.

Dúvidas? Procure seu gestor."""

MENSAGEM_GESTOR = """Olá, {primeiro_nome}!

{colaborador} passou de 4 horas sem registrar o intervalo em {ocorrencias} dia(s) neste mês ({dias}). \
Se a pausa foi feita e só não foi registrada, colha o Termo de Ajuste assinado e envie ao RH."""


@dataclass(frozen=True)
class DiaHorista:
	data: date
	trabalhado: int
	intervalo_suprimido: int


def e_ocorrencia(
	dia: DiaHorista,
	tolerancia: int = TOLERANCIA_PADRAO,
	sem_intervalo_ate: int = d.JORNADA_SEM_INTERVALO_ATE_MIN,
) -> bool:
	return (
		dia.intervalo_suprimido > 0 and sem_intervalo_ate < dia.trabalhado <= sem_intervalo_ate + tolerancia
	)


def ocorrencias(
	dias: Iterable[DiaHorista],
	tolerancia: int = TOLERANCIA_PADRAO,
	sem_intervalo_ate: int = d.JORNADA_SEM_INTERVALO_ATE_MIN,
) -> list[date]:
	return sorted(dia.data for dia in dias if e_ocorrencia(dia, tolerancia, sem_intervalo_ate))


def limite_atingido(quantidade: int, limite: int = LIMITE_PADRAO) -> int:
	"""Maior múltiplo do limite já alcançado (0 = ainda não chegou ao primeiro)."""
	if limite <= 0:
		return 0
	return quantidade // limite * limite


def precisa_avisar(quantidade: int, limite: int, ultimo_avisado: int) -> bool:
	"""DH-2: avisa quando chega a um limite novo (4, 8, 12...), uma vez só."""
	atingido = limite_atingido(quantidade, limite)
	return atingido > 0 and atingido > ultimo_avisado


def pendencia_aberta(quantidade: int, limite: int = LIMITE_PADRAO) -> bool:
	"""DH-3: a inconsistência do mês fica aberta enquanto as ocorrências não regularizadas estão no limite ou acima."""
	return limite > 0 and quantidade >= limite


def telefone_whatsapp(numero: str | None) -> str | None:
	"""Só dígitos e com o DDI 55 na frente (10 ou 11 dígitos = número brasileiro sem DDI). None se não der."""
	texto = str(numero or "").strip()
	digitos = re.sub(r"\D", "", texto)
	if texto.startswith("+") and not digitos.startswith("55"):
		return None  # DDI de outro país
	if len(digitos) in (10, 11):
		digitos = "55" + digitos
	if not digitos.startswith("55") or len(digitos) not in (12, 13):
		return None
	return digitos


class _Marcadores(dict):
	def __missing__(self, chave):
		return "{" + chave + "}"


def montar_mensagem(modelo: str, **valores) -> str:
	"""Troca os marcadores {primeiro_nome}, {ocorrencias}, {limite}, {dias}...; marcador desconhecido fica como está."""
	return (modelo or "").format_map(_Marcadores({k: str(v) for k, v in valores.items()}))


def dias_curtos(datas: Iterable[date]) -> str:
	return ", ".join(f"{dia:%d/%m}" for dia in sorted(datas))


def dentro_do_horario(hora: int, inicio: int = HORA_INICIO_ENVIO, fim: int = HORA_FIM_ENVIO) -> bool:
	return inicio <= hora < fim
