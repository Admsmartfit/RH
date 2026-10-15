"""Vale-transporte: sugestão de passes, desconto em folha, trava por média e arquivo GVBus (AJ-06).

Python puro. Os dias de trabalho do mês chegam prontos do Frappe (perfil de jornada vigente + trocas de
escala); aqui só se aplicam feriados, ausências, acerto do mês anterior e abonos em lote.

Layout do arquivo: PRD "Módulo de Gestão, Sugestão e Carga de Vale-Transporte GVBus" v2.0, seção 4 —
27 campos separados por ";", sem cabeçalho, ISO-8859-1, CRLF. Validar com upload de teste no portal.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.documentos import cpf_valido, somente_digitos

CENTAVO = Decimal("0.01")
PERCENTUAL_DESCONTO = Decimal("6")  # Lei 7.418/1985, art. 4º, parágrafo único
MESES_MEDIA_PADRAO = 3
ALERTA_PADRAO = Decimal("15")
TRAVA_DURA_PADRAO = Decimal("30")

OK = "ok"
ALERTA = "alerta"  # ALT-01: motivo obrigatório
TRAVA = "trava"  # ALT-02: só exporta com aprovação do Gestor de DP

TOTAL_CAMPOS = 27


def _reais(valor) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


# ------------------------------------------------------------------ sugestão


def dias_de_trabalho(ano: int, mes: int, dias_semana: Iterable[int], trocas: dict[date, bool] | None = None):
	"""Datas do mês em que o colaborador trabalha: dias da semana do perfil (0 = segunda) e trocas
	de escala (data -> True trabalha / False folga), que prevalecem sobre o perfil."""
	semana = set(dias_semana)
	trocas = trocas or {}
	_, ultimo = calendar.monthrange(ano, mes)
	dias = []
	for dia in range(1, ultimo + 1):
		data = date(ano, mes, dia)
		if trocas.get(data, data.weekday() in semana):
			dias.append(data)
	return dias


@dataclass(frozen=True)
class Tarifa:
	codigo: str
	valor: Decimal
	quantidade_diaria: int


@dataclass(frozen=True)
class Sugestao:
	dias_previstos: int
	acerto: int
	abono: int
	dias: int
	valor: Decimal


def sugerir(
	dias_trabalho: Iterable[date],
	tarifas: Iterable[Tarifa],
	*,
	feriados: Iterable[date] = (),
	ausencias: Iterable[date] = (),
	acerto: int = 0,
	abono: int = 0,
) -> Sugestao:
	"""Dias e valor do VT do mês.

	- feriados e ausências já conhecidas (férias, afastamento, licença) saem dos dias de trabalho;
	- acerto: dias pagos e não usados no mês anterior (faltas, atestados...), abatidos agora;
	- abono: dias de recesso/ponte descontados em lote (positivo) ou dias somados (negativo).
	"""
	fora = set(feriados) | set(ausencias)
	previstos = len({d for d in dias_trabalho if d not in fora})
	dias = max(0, previstos - acerto - abono)
	por_dia = sum((Decimal(t.valor) * t.quantidade_diaria for t in tarifas), Decimal("0"))
	return Sugestao(previstos, acerto, abono, dias, _reais(por_dia * dias))


def desconto_em_folha(salario_base, valor_vt, percentual=PERCENTUAL_DESCONTO) -> Decimal:
	"""Até 6% do salário básico, nunca mais que o valor do benefício."""
	teto = _reais(Decimal(salario_base) * Decimal(percentual) / 100)
	return min(teto, _reais(valor_vt))


# ------------------------------------------------------------------ trava por média


def media_historica(cargas: Iterable, meses: int = MESES_MEDIA_PADRAO) -> Decimal | None:
	"""Média das últimas `meses` cargas confirmadas (mais recente por último). Sem histórico: None."""
	ultimas = [Decimal(c) for c in list(cargas)[-meses:]] if meses > 0 else []
	if not ultimas:
		return None
	return _reais(sum(ultimas, Decimal("0")) / len(ultimas))


def variacao_percentual(valor, media: Decimal | None) -> Decimal | None:
	if not media:
		return None
	return ((Decimal(valor) - media) / media * 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def nivel_trava(variacao: Decimal | None, alerta=ALERTA_PADRAO, trava_dura=TRAVA_DURA_PADRAO) -> str:
	"""OK abaixo do alerta; ALERTA entre alerta e trava dura (inclusive); TRAVA acima da trava dura."""
	if variacao is None or variacao < Decimal(alerta):
		return OK
	if variacao > Decimal(trava_dura):
		return TRAVA
	return ALERTA


# ------------------------------------------------------------------ arquivo GVBus


@dataclass(frozen=True)
class LinhaGVBus:
	nome: str
	matricula: str
	cpf: str
	rg: str
	cartao: str
	cargo: str = ""
	admissao: date | None = None
	endereco: str = ""
	bairro: str = ""
	municipio: str = ""
	cep: str = ""
	telefone: str = ""
	setor: str = ""
	tarifas: tuple[Tarifa, ...] = field(default_factory=tuple)
	inativo_desde: date | None = None


def erros_da_linha(linha: LinhaGVBus) -> list[str]:
	"""ERR-01 (CPF/RG) e ERR-02 (CartãoGV): a linha fica fora do arquivo enquanto houver erro."""
	erros = []
	if not linha.nome.strip():
		erros.append("Nome ausente.")
	if not linha.matricula.strip():
		erros.append("Matrícula ausente.")
	if not cpf_valido(somente_digitos(linha.cpf)):
		erros.append("ERR-01: CPF ausente ou inválido.")
	if not linha.rg.strip():
		erros.append("ERR-01: RG ausente.")
	if not linha.cartao.strip():
		erros.append("ERR-02: número do CartãoGV não cadastrado.")
	if len(linha.tarifas) > 2:
		erros.append("No máximo 2 tarifas por colaborador.")
	return erros


def _texto(valor: str, tamanho: int) -> str:
	"""Maiúsculas, sem ';' nem quebras de linha, cortado no tamanho do campo."""
	limpo = " ".join(str(valor or "").replace(";", " ").split()).upper()
	return limpo[:tamanho]


def _data(valor: date | None) -> str:
	return valor.strftime("%d/%m/%Y") if valor else ""


def campos_da_linha(linha: LinhaGVBus) -> list[str]:
	t1, t2 = [*linha.tarifas, None, None][:2]
	campos = [
		_texto(linha.nome, 50),
		_texto(linha.matricula, 15),
		_texto(linha.cargo, 50),
		_data(linha.admissao),
		_texto(linha.endereco, 60),
		_texto(linha.bairro, 40),
		_texto(linha.municipio, 50),
		somente_digitos(linha.cep)[:8],
		somente_digitos(linha.telefone)[:15],
		_texto(linha.setor, 50),
		_texto(t1.codigo, 4) if t1 else "",
		f"{t1.quantidade_diaria:02d}" if t1 else "",
		_texto(t2.codigo, 4) if t2 else "",
		f"{t2.quantidade_diaria:02d}" if t2 else "",
		*([""] * 9),  # campos 15 a 23: reserva
		_data(linha.inativo_desde),
		somente_digitos(linha.cartao)[:14] or _texto(linha.cartao, 14),
		somente_digitos(linha.cpf)[:11],
		_texto(linha.rg, 14),
	]
	assert len(campos) == TOTAL_CAMPOS
	return campos


def gerar_arquivo(linhas: Iterable[LinhaGVBus]) -> bytes:
	"""Conteúdo do arquivo de carga: só linhas sem erro, ISO-8859-1, CRLF ao fim de cada linha."""
	texto = "".join(";".join(campos_da_linha(lin)) + "\r\n" for lin in linhas if not erros_da_linha(lin))
	return texto.encode("iso-8859-1", errors="replace")


def nome_arquivo(cnpj: str, competencia: date, gerado_em: date) -> str:
	"""GVBUS_CARGA_[CNPJ]_[AAAAMM]_[DD].txt"""
	return f"GVBUS_CARGA_{somente_digitos(cnpj)}_{competencia:%Y%m}_{gerado_em:%d}.txt"
