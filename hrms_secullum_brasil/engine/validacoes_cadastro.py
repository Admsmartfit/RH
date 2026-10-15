"""Validações dos parâmetros da Regra Sindical CCT (PRD, Seção 5).

Funções `erros_*` devolvem mensagens que bloqueiam o salvamento; `avisos_*` devolvem alertas
de risco que não bloqueiam.
"""

from collections import defaultdict
from collections.abc import Iterable

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE


def erros_tolerancia(por_marcacao: int, diaria: int) -> list[str]:
	erros = []
	if por_marcacao < 0 or diaria < 0:
		erros.append("Tolerâncias não podem ser negativas.")
	elif diaria < por_marcacao:
		erros.append("Tolerância diária não pode ser menor que a tolerância por marcação.")
	return erros


def avisos_tolerancia(por_marcacao: int, diaria: int) -> list[str]:
	"""Art. 58, §1º CLT: ampliar a tolerância além de 5/10 min tem risco jurídico (PRD, 5.2)."""
	avisos = []
	if por_marcacao > d.TOLERANCIA_POR_MARCACAO_MIN:
		avisos.append(
			f"Tolerância por marcação de {por_marcacao} min ultrapassa o limite legal de "
			f"{d.TOLERANCIA_POR_MARCACAO_MIN} min (Art. 58, §1º CLT)."
		)
	if diaria > d.TOLERANCIA_DIARIA_MIN:
		avisos.append(
			f"Tolerância diária de {diaria} min ultrapassa o limite legal de "
			f"{d.TOLERANCIA_DIARIA_MIN} min (Art. 58, §1º CLT)."
		)
	return avisos


def erros_faixas_he(faixas: Iterable[FaixaHE]) -> list[str]:
	"""Cada tipo de dia precisa de faixas contíguas cobrindo de 0 min até "sem limite" (ate_min = 0)."""
	por_tipo: dict[str, list[FaixaHE]] = defaultdict(list)
	erros = []
	for faixa in faixas:
		if faixa.tipo_dia not in d.TIPOS_DIA:
			erros.append(f"Tipo de dia inválido: {faixa.tipo_dia}.")
			continue
		if faixa.percentual < d.PERCENTUAL_MINIMO_HE:
			erros.append(
				f"{faixa.tipo_dia}: percentual de {faixa.percentual}% abaixo do mínimo constitucional "
				f"de {d.PERCENTUAL_MINIMO_HE}% (Art. 7º, XVI CF)."
			)
		por_tipo[faixa.tipo_dia].append(faixa)

	for tipo in d.TIPOS_DIA:
		lista = sorted(por_tipo.get(tipo, []), key=lambda f: f.de_min)
		if not lista:
			erros.append(f"Falta faixa de hora extra para o tipo de dia {tipo}.")
			continue
		esperado = 0
		for i, faixa in enumerate(lista):
			ultima = i == len(lista) - 1
			if faixa.de_min != esperado:
				erros.append(
					f"{tipo}: faixa deveria começar em {esperado} min, começa em {faixa.de_min} min."
				)
				break
			if faixa.ate_min == 0 and not ultima:
				erros.append(f"{tipo}: apenas a última faixa pode ser sem limite (até = 0).")
				break
			if faixa.ate_min != 0 and faixa.ate_min <= faixa.de_min:
				erros.append(
					f"{tipo}: faixa {faixa.de_min} a {faixa.ate_min} min tem fim menor ou igual ao início."
				)
				break
			if ultima and faixa.ate_min != 0:
				erros.append(f"{tipo}: a última faixa deve ser sem limite (até = 0).")
			esperado = faixa.ate_min
	return erros


def erros_intrajornada(
	*,
	jornada_sem_intervalo_ate: int,
	intervalo_curto: int,
	jornada_intervalo_curto_ate: int,
	intervalo_minimo: int,
	intervalo_maximo: int,
	permite_reducao: bool,
	intervalo_reduzido: int,
) -> list[str]:
	erros = []
	if not 0 < jornada_sem_intervalo_ate < jornada_intervalo_curto_ate:
		erros.append(
			"Limites de jornada da intrajornada devem ser crescentes (sem intervalo < intervalo curto)."
		)
	if intervalo_curto <= 0:
		erros.append("Intervalo para jornada de 4h a 6h deve ser maior que zero.")
	if intervalo_minimo <= 0 or intervalo_maximo < intervalo_minimo:
		erros.append("Intervalo máximo deve ser maior ou igual ao mínimo, e o mínimo maior que zero.")
	if permite_reducao:
		if intervalo_reduzido < d.INTERVALO_REDUZIDO_MIN:
			erros.append(
				f"Intervalo reduzido não pode ser menor que {d.INTERVALO_REDUZIDO_MIN} min (Art. 611-A, III CLT)."
			)
		elif intervalo_reduzido > intervalo_minimo:
			erros.append("Intervalo reduzido não pode ser maior que o intervalo mínimo.")
	return erros


def erros_banco_horas(modalidade: str, prazo_meses: int) -> list[str]:
	maximo = d.PRAZO_MAXIMO_BANCO_MESES.get(modalidade)
	if maximo is None:
		return [f"Modalidade de banco de horas inválida: {modalidade}."]
	if not 1 <= prazo_meses <= maximo:
		return [
			f"Banco {modalidade}: prazo de compensação deve ficar entre 1 e {maximo} mês(es) (Art. 59 CLT)."
		]
	return []
