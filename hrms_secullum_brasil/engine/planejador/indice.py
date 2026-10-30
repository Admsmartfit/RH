"""Índice de desempenho e disponibilidade (DP-6): de 0 a 100, pelo histórico dos últimos 90 dias, com pesos à mostra
(o gestor também inclui ou exclui pessoas à mão). Não é nota de avaliação: só diz quem é bom candidato para ampliar
a carga."""

from dataclasses import dataclass

PESOS_PADRAO = {"assiduidade": 40, "pontualidade": 20, "consistencia": 20, "disponibilidade": 20}
ATRASO_TOLERADO_POR_DIA = 10  # minutos médios de atraso por dia que zeram a pontualidade


@dataclass(frozen=True)
class Historico:
	dias_previstos: int = 0
	faltas: int = 0
	atraso_minutos: int = 0
	inconsistencias: int = 0
	convites_respondidos: int = 0
	convites_aceitos: int = 0
	informou_disponibilidade: bool = False


def componentes(h: Historico) -> dict[str, float]:
	if not h.dias_previstos:
		return {"assiduidade": 0.5, "pontualidade": 0.5, "consistencia": 0.5, "disponibilidade": 0.5}
	if h.convites_respondidos:
		disponibilidade = h.convites_aceitos / h.convites_respondidos
	else:
		disponibilidade = 0.75 if h.informou_disponibilidade else 0.5
	return {
		"assiduidade": max(0.0, 1 - h.faltas / h.dias_previstos),
		"pontualidade": max(0.0, 1 - h.atraso_minutos / (h.dias_previstos * ATRASO_TOLERADO_POR_DIA)),
		"consistencia": max(0.0, 1 - h.inconsistencias / h.dias_previstos),
		"disponibilidade": disponibilidade,
	}


def indice(h: Historico, pesos: dict[str, int] | None = None) -> int:
	pesos = pesos or PESOS_PADRAO
	total = sum(pesos.values()) or 1
	c = componentes(h)
	return round(100 * sum(c[k] * pesos.get(k, 0) for k in c) / total)
