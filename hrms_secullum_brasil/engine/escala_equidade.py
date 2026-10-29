"""Equidade dos turnos de fim de semana e feriado no cockpit (docs/PRD-cockpit-escalas.md, CE-07). Python puro.

Cada colaborador é comparado com a média da equipe filtrada pela soma do mês com os 3 meses anteriores. Sempre com
texto, além da cor: "Na média" (verde), "Acima da média" (laranja) e "Muito acima da média" (vermelho); quem está
abaixo aparece em verde como "Abaixo da média" (bom candidato para o próximo turno).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

VERDE = "verde"
LARANJA = "laranja"
VERMELHO = "vermelho"
TOLERANCIA = 1  # turnos acima da média ainda considerados na média
LIMITE_LARANJA = 3


@dataclass(frozen=True)
class Equidade:
	no_mes: int
	nos_3_meses: int
	media: Decimal  # média da equipe (mês + 3 meses)
	cor: str
	texto: str


def equidade(contagens: dict[str, tuple[int, int]]) -> dict[str, Equidade]:
	"""contagens: colaborador -> (turnos no mês, turnos nos 3 meses anteriores)."""
	if not contagens:
		return {}
	totais = {e: mes + anteriores for e, (mes, anteriores) in contagens.items()}
	media = (Decimal(sum(totais.values())) / len(totais)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
	resultado = {}
	for employee, (mes, anteriores) in contagens.items():
		desvio = totais[employee] - media
		if desvio > LIMITE_LARANJA:
			cor, texto = VERMELHO, "Muito acima da média"
		elif desvio > TOLERANCIA:
			cor, texto = LARANJA, "Acima da média"
		elif desvio < -TOLERANCIA:
			cor, texto = VERDE, "Abaixo da média"
		else:
			cor, texto = VERDE, "Na média"
		resultado[employee] = Equidade(mes, anteriores, media, cor, texto)
	return resultado
