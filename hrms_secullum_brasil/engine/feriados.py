"""Feriados do ano por empresa (AJ-11) e prazo da folga de feriado trabalhado (AJ-03).

- Nacionais vêm de uma fonte pública (BrasilAPI). Carnaval e Corpus Christi chegam lá como "nacionais", mas são
  pontos facultativos (só entram na lista da empresa que adotar); o domingo de Páscoa é ignorado.
- Estaduais, municipais e pontos facultativos são cadastrados pelo RH (Feriado Regional), com data fixa
  (dia/mês) ou móvel (dias depois da Páscoa).
- Uma nova importação nunca apaga nem duplica: só inclui datas que não estão na lista e que o RH não removeu.
"""

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

FIXA = "Fixa"
MOVEL = "Móvel"
FERIADO = "Feriado"
PONTO_FACULTATIVO = "Ponto facultativo"

# Nomes da fonte pública que não são feriado nacional obrigatório (comparação sem acento e minúscula).
FACULTATIVOS_DA_FONTE = ("carnaval", "corpus christi")
IGNORADOS_DA_FONTE = ("pascoa",)  # domingo de Páscoa


def _normalizar(texto: str) -> str:
	sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
	return sem_acento.strip().lower()


def pascoa(ano: int) -> date:
	"""Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
	a, b, c = ano % 19, ano // 100, ano % 100
	d, e = b // 4, b % 4
	f = (b + 8) // 25
	g = (b - f + 1) // 3
	h = (19 * a + b - d - g + 15) % 30
	i, k = c // 4, c % 4
	m = (32 + 2 * e + 2 * i - h - k) % 7
	n = (a + 11 * h + 22 * m) // 451
	mes = (h + m - 7 * n + 114) // 31
	dia = (h + m - 7 * n + 114) % 31 + 1
	return date(ano, mes, dia)


@dataclass(frozen=True)
class RegraFeriado:
	descricao: str
	tipo_data: str = FIXA
	dia: int = 0
	mes: int = 0
	dias_apos_pascoa: int = 0  # móvel: negativo = antes da Páscoa (Carnaval = -48 e -47)

	def data(self, ano: int) -> date:
		if self.tipo_data == MOVEL:
			return pascoa(ano) + timedelta(days=self.dias_apos_pascoa)
		return date(ano, self.mes, self.dia)


def classificar_da_fonte(nome: str) -> str | None:
	"""FERIADO, PONTO_FACULTATIVO ou None (ignorar) para um item da fonte pública."""
	normalizado = _normalizar(nome)
	if any(normalizado.startswith(i) for i in IGNORADOS_DA_FONTE):
		return None
	if any(f in normalizado for f in FACULTATIVOS_DA_FONTE):
		return PONTO_FACULTATIVO
	return FERIADO


def feriados_novos(
	nacionais: Iterable[tuple[date, str]],
	regionais: Iterable[tuple[date, str]],
	existentes: Iterable[date],
	removidas: Iterable[date],
) -> list[tuple[date, str]]:
	"""Datas a incluir na lista: nacionais obrigatórios + regionais da empresa (já filtrados por UF/município e
	pelos facultativos adotados), sem as que já estão na lista nem as que o RH removeu."""
	fora = set(existentes) | set(removidas)
	novos: dict[date, str] = {}
	for dia, descricao in [*nacionais, *regionais]:
		if dia not in fora and dia not in novos:
			novos[dia] = descricao
	return sorted(novos.items())


# ------------------------------------------------------------------ AJ-03


def fim_do_prazo_da_folga(feriado: date, prazo_dias: int) -> date:
	"""Último dia para dar a folga: 0 = até o domingo da semana do feriado; N = N dias depois do feriado."""
	if prazo_dias and prazo_dias > 0:
		return feriado + timedelta(days=prazo_dias)
	return feriado + timedelta(days=6 - feriado.weekday())


def erros_compensacao(feriado: date, folga: date, prazo_dias: int, eh_feriado: bool) -> list[str]:
	erros = []
	if not eh_feriado:
		erros.append(f"{feriado:%d/%m/%Y} não é feriado para o colaborador.")
	fim = fim_do_prazo_da_folga(feriado, prazo_dias)
	if not feriado < folga <= fim:
		erros.append(f"A folga deve ser depois do feriado e até {fim:%d/%m/%Y} (prazo da CCT).")
	return erros
