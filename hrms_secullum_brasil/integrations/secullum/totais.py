"""Totais calculados pelo Secullum (rota Calcular/SomenteTotais, manual pág. 39) para o relatório de divergência.

A resposta traz "Colunas" e "Totais" paralelos, com horas no formato "HH:MM". Os nomes das colunas
dependem da configuração de cada banco Secullum, por isso o mapeamento coluna -> categoria é configurável.
Limite da API: 100 requisições por hora por banco e período de no máximo um mês.
"""

CATEGORIAS = ("normais", "hora_extra", "falta", "atraso", "noturno_real")

MAPEAMENTO_PADRAO = {
	"Normais": "normais",
	"Extras": "hora_extra",
	"Ex50%": "hora_extra",
	"Ex70%": "hora_extra",
	"Ex100%": "hora_extra",
	"Faltas": "falta",
	"Atrasos": "atraso",
	"Atraso": "atraso",
	"Noturno": "noturno_real",
	"Not.": "noturno_real",
}


def horas_para_minutos(valor) -> int | None:
	"""'08:48' -> 528; '-01:30' -> -90; '125:00' -> 7500. None se não for um total de horas."""
	texto = str(valor or "").strip()
	if not texto or ":" not in texto:
		return None
	sinal = -1 if texto.startswith("-") else 1
	horas, _, minutos = texto.lstrip("+-").partition(":")
	if not (horas.isdigit() and minutos[:2].isdigit()):
		return None
	return sinal * (int(horas) * 60 + int(minutos[:2]))


def totais_por_categoria(resposta: dict, mapeamento: dict[str, str] | None = None) -> dict[str, int]:
	"""Soma, por categoria do app, as colunas do Secullum mapeadas. Colunas sem mapeamento são ignoradas."""
	mapeamento = mapeamento or MAPEAMENTO_PADRAO
	colunas = resposta.get("Colunas") or []
	totais = resposta.get("Totais") or []
	resultado = dict.fromkeys(CATEGORIAS, 0)
	encontrou = set()
	for coluna, total in zip(colunas, totais, strict=False):
		categoria = mapeamento.get(str(coluna).strip())
		minutos = horas_para_minutos(total)
		if categoria in resultado and minutos is not None:
			resultado[categoria] += minutos
			encontrou.add(categoria)
	return {c: v for c, v in resultado.items() if c in encontrou}
