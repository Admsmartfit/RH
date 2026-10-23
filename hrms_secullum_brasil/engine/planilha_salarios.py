"""Leitura da planilha de salários (docs/PRD-importacao-secullum.md, IS-13). Python puro.

Cada linha tem CPF, salário-base (ou o valor da hora, para horista: divisor 1, docs/regras_por_cargo.md) e a data de
início; opcionalmente a empresa (CNPJ), para o CPF com mais de um vínculo ativo. Os nomes das colunas são
flexíveis ("Salário", "valor_hora", "Data de início"...). Valores aceitam o formato brasileiro ("R$ 1.234,56").
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from hrms_secullum_brasil.engine.documentos import cpf_valido, somente_digitos

COLUNAS = {
	"cpf": ("cpf", "documento"),
	"valor": (
		"salario",
		"salario_base",
		"base",
		"valor",
		"valor_hora",
		"salario_ou_valor_hora",
		"remuneracao",
	),
	"inicio": ("inicio", "data_inicio", "data_de_inicio", "vigencia", "a_partir_de", "desde", "data"),
	"empresa": ("empresa", "cnpj", "cnpj_empresa"),
	"nome": ("nome", "colaborador", "funcionario"),
}
CENTAVOS = Decimal("0.01")


@dataclass
class LinhaSalario:
	linha: int
	cpf: str
	valor: Decimal
	inicio: date
	empresa: str | None = None
	nome: str | None = None


def _chave(texto: str) -> str:
	sem_acento = "".join(
		c for c in unicodedata.normalize("NFKD", str(texto or "")) if not unicodedata.combining(c)
	)
	return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def mapear_colunas(cabecalho: list[str]) -> dict[str, int]:
	"""{campo: índice} pelo cabeçalho; levanta ValueError se faltar CPF, valor ou início."""
	indices = {}
	normalizado = [_chave(c) for c in cabecalho]
	for campo, nomes in COLUNAS.items():
		for i, nome in enumerate(normalizado):
			if nome in nomes and campo not in indices:
				indices[campo] = i
	faltando = [c for c in ("cpf", "valor", "inicio") if c not in indices]
	if faltando:
		raise ValueError(
			"Colunas obrigatórias não encontradas: "
			+ ", ".join(faltando)
			+ ". Use CPF, Salário (ou Valor hora) e Início."
		)
	return indices


def valor_monetario(texto) -> Decimal:
	"""'R$ 1.234,56' / '1234.56' / 1234.5 → Decimal com 2 casas (ROUND_HALF_UP)."""
	if isinstance(texto, int | float | Decimal):
		bruto = Decimal(str(texto))
	else:
		limpo = re.sub(r"[^\d,.\-]", "", str(texto or ""))
		if not limpo:
			raise ValueError("valor vazio")
		if "," in limpo:  # formato brasileiro: ponto é milhar, vírgula é decimal
			limpo = limpo.replace(".", "").replace(",", ".")
		elif limpo.count(".") > 1 or re.fullmatch(r"-?\d{1,3}\.\d{3}", limpo):
			limpo = limpo.replace(".", "")  # "2.500" e "1.234.567": ponto de milhar
		try:
			bruto = Decimal(limpo)
		except InvalidOperation as exc:
			raise ValueError(f"valor inválido: {texto}") from exc
	if bruto <= 0:
		raise ValueError(f"valor deve ser positivo: {texto}")
	return bruto.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def data_planilha(texto) -> date:
	if isinstance(texto, datetime):
		return texto.date()
	if isinstance(texto, date):
		return texto
	bruto = str(texto or "").strip()[:10]
	for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
		try:
			return datetime.strptime(bruto, formato).date()
		except ValueError:
			continue
	raise ValueError(f"data inválida: {texto} (use dd/mm/aaaa)")


def ler_planilha(linhas: list[list]) -> tuple[list[LinhaSalario], list[str]]:
	"""(linhas válidas, erros "Linha N: ...") de uma planilha já lida (a primeira linha é o cabeçalho)."""
	linhas = [linha for linha in linhas if any(str(c or "").strip() for c in linha)]
	if not linhas:
		return [], ["Planilha vazia."]
	try:
		colunas = mapear_colunas([str(c or "") for c in linhas[0]])
	except ValueError as exc:
		return [], [str(exc)]
	validas, erros, vistos = [], [], {}
	for numero, linha in enumerate(linhas[1:], start=2):

		def celula(campo, linha=linha):
			i = colunas.get(campo)
			return linha[i] if i is not None and i < len(linha) else None

		cpf = somente_digitos(str(celula("cpf") or "")).zfill(11) if celula("cpf") else ""
		if not cpf_valido(cpf):
			erros.append(f"Linha {numero}: CPF inválido ({celula('cpf')}).")
			continue
		try:
			valor = valor_monetario(celula("valor"))
			inicio = data_planilha(celula("inicio"))
		except ValueError as exc:
			erros.append(f"Linha {numero}: {exc}.")
			continue
		empresa = somente_digitos(str(celula("empresa") or "")) or None
		chave = (cpf, empresa, inicio)
		if chave in vistos:
			erros.append(f"Linha {numero}: repete a linha {vistos[chave]} (mesmo CPF, empresa e início).")
			continue
		vistos[chave] = numero
		validas.append(
			LinhaSalario(numero, cpf, valor, inicio, empresa, str(celula("nome") or "").strip() or None)
		)
	return validas, erros
