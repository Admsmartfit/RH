"""Lançamentos de ausência pelo cartão ponto (pedido do RH, 08/11/2026): falta com justificativa, atestado médico e
férias/licença/afastamento.

Regra pura: o que pode ser lançado em cada dia, os tipos de licença oferecidos, o texto do abono no cartão e os dias
a reapurar. A gravação (Tratamento de Ponto, Atestado Medico, Leave Application) fica em `apuracao/lancamentos.py`.
"""

from dataclasses import dataclass
from datetime import date, timedelta

FALTA, ATESTADO, LICENCA = "falta", "atestado", "licenca"
TIPOS = (FALTA, ATESTADO, LICENCA)
MAXIMO_DIAS = 366  # um lançamento cobre no máximo um ano (licença-maternidade de 180 dias cabe)
EFEITO_FALTA = "Falta"  # efeito da Justificativa Secullum que mantém o dia como falta
ATESTADO_MEDICO = "Atestado Médico"  # tipo de licença do atestado: entra pelo Atestado Medico, nunca direto

# situação do dia no cartão (cartao_ponto._situacao) em que cabe uma falta
DIA_DE_TRABALHO = "Trabalho"


@dataclass(frozen=True)
class DiaDaFalta:
	"""O que o cartão sabe do dia para lançar a falta."""

	data: date
	situacao: str  # Trabalho, Folga, Repouso, Neutro, Feriado, Fora do contrato, Não apurado, Professor
	batidas: int  # batidas que contam no dia (as desconsideradas não entram)
	abonado: bool  # tratamento de abono, atestado, licença ou afastamento
	falta_lancada: bool = False
	fechado: bool = False
	futuro: bool = False


def motivo_mantida(justificativa: str, tratamento: str) -> str:
	"""Motivo gravado na inconsistência de falta mantida (o cancelamento do tratamento a reabre por este texto)."""
	return f"Falta justificada ({justificativa}) — {tratamento}"


def erros_do_periodo(inicio: date | None, fim: date | None) -> list[str]:
	if not inicio or not fim:
		return ["Informe o início e o fim."]
	if fim < inicio:
		return ["O fim não pode ser antes do início."]
	if (fim - inicio).days + 1 > MAXIMO_DIAS:
		return [f"Um lançamento cobre no máximo {MAXIMO_DIAS} dias."]
	return []


def dias(inicio: date, fim: date) -> list[date]:
	return [inicio + timedelta(days=n) for n in range((fim - inicio).days + 1)]


def dias_a_reapurar(inicio: date, fim: date, hoje: date) -> list[date]:
	"""Dias já passados (ou hoje) do período: o futuro é apurado quando chegar."""
	return dias(inicio, min(fim, hoje)) if inicio <= hoje else []


def motivo_da_falta(dia: DiaDaFalta) -> str | None:
	"""Por que a falta não cabe no dia (None = cabe). Falta só em dia de trabalho previsto, sem batida e sem abono:
	o dia com batida precisa ter as batidas desconsideradas antes (a batida do relógio pede a confirmação dupla)."""
	data = dia.data.strftime("%d/%m/%Y")
	if dia.fechado:
		return f"{data}: período fechado."
	if dia.futuro:
		return f"{data}: dia que ainda não chegou."
	if dia.situacao != DIA_DE_TRABALHO:
		return f"{data}: não é dia de trabalho ({dia.situacao.lower()})."
	if dia.falta_lancada:
		return f"{data}: a falta já está lançada."
	if dia.abonado:
		return f"{data}: o dia está abonado; tire o abono antes."
	if dia.batidas:
		return f"{data}: o dia tem batidas; desconsidere-as no cartão antes de lançar a falta."
	return None


def separar_faltas(dias_da_falta: list[DiaDaFalta]) -> tuple[list[date], list[str]]:
	"""(dias em que a falta entra, avisos dos dias pulados)."""
	entram, avisos = [], []
	for dia in dias_da_falta:
		motivo = motivo_da_falta(dia)
		if motivo:
			avisos.append(motivo)
		else:
			entram.append(dia.data)
	return entram, avisos


def erro_da_justificativa(efeito: str | None) -> str | None:
	if not efeito:
		return "Escolha a justificativa da falta."
	if efeito != EFEITO_FALTA:
		return 'A justificativa da falta precisa ter o efeito "Falta" no cadastro de justificativas.'
	return None


def tipos_de_licenca(tipos: list[dict]) -> list[str]:
	"""Tipos oferecidos no cartão: sem o atestado (tem lançamento próprio). A licença não remunerada (`is_lwp`) entra:
	a apuração não a paga nem a conta como falta (RH, 10/11/2026)."""
	return sorted(t["name"] for t in tipos if t["name"] != ATESTADO_MEDICO and not t.get("disabled"))


def texto_do_abono(doctype: str | None, tipo_licenca: str | None = None) -> str:
	"""O que a coluna Abono do cartão mostra para o documento que abona o dia."""
	if doctype == "Atestado Medico":
		return "Atestado"
	if doctype == "Leave Application":
		return tipo_licenca or "Licença"
	if doctype == "Afastamento Secullum":
		return "Afastamento"
	return "Abonado"
