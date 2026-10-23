"""Anonimização das respostas reais do Secullum para virar fixture de teste (docs/PRD-importacao-secullum.md, IS-03).

Troca por valores fictícios coerentes tudo o que identifica uma pessoa ou empresa. O mesmo valor original vira
sempre o mesmo valor fictício dentro de uma execução, para manter as ligações entre os arquivos (o CPF do
afastamento continua apontando para o funcionário). Mantém a estrutura, os tipos, a presença ou ausência de cada
campo e os dados de negócio (horários, funções, departamentos, cidades, justificativas).
"""

import hashlib
from typing import Any

from hrms_secullum_brasil.engine.documentos import cpf_valido

CPF = {"cpf", "funcionariocpf"}
PIS = {"numeropis", "funcionariopis", "pis"}
CNPJ = {"documento", "empresacnpjcpf", "empresadocumento"}
NUMEROS = {
	"numerofolha",
	"numeroidentificador",
	"numeroprovisorio",
	"carteira",
	"rg",
	"codigoholerite",
	"inscricao",
	"cei",
}
TEXTOS = {
	"endereco": "Rua Exemplo, 100",
	"bairro": "Centro",
	"cep": "29000-000",
	"telefone": "(27) 3000-0000",
	"celular": "(27) 99999-0000",
	"fax": None,
	"email": "pessoa@example.com",
	"responsavelnome": "Responsável Exemplo",
	"responsavelemail": "responsavel@example.com",
	"mae": "Mãe Exemplo",
	"pai": "Pai Exemplo",
	"naturalidade": "Cidade Exemplo",
	"observacao": None,
	"motivo": "Motivo de exemplo",
	"ssp": None,
	"foto": None,
	"logotipo": None,
	"enderecoip": None,
}


def _digitos(valor) -> str:
	return "".join(c for c in str(valor or "") if c.isdigit())


def _dv(base: str, pesos) -> str:
	resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
	return "0" if resto < 2 else str(11 - resto)


def cpf_ficticio(n: int) -> str:
	base = f"{900000000 + n:09d}"[-9:]
	for _ in range(2):
		base += str(
			sum(int(d) * p for d, p in zip(base, range(len(base) + 1, 1, -1), strict=True)) * 10 % 11 % 10
		)
	assert cpf_valido(base)
	return base


def cnpj_ficticio(n: int) -> str:
	base = f"{90000000 + n:08d}0001"
	base += _dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
	base += _dv(base, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
	return base


def pis_ficticio(n: int) -> str:
	base = f"{1900000000 + n:010d}"[-10:]
	resto = sum(int(d) * p for d, p in zip(base, [3, 2, 9, 8, 7, 6, 5, 4, 3, 2], strict=True)) % 11
	return base + ("0" if resto < 2 else str(11 - resto))


class Anonimizador:
	def __init__(self, semente: str = ""):
		self.semente = semente
		self.mapas: dict[str, dict[str, Any]] = {
			"cpf": {},
			"pis": {},
			"cnpj": {},
			"numero": {},
			"pessoa": {},
			"empresa": {},
		}
		self.originais: set[str] = set()  # CPFs, PIS e CNPJs reais vistos (para conferir que nenhum sobrou)

	def _troca(self, tipo: str, original, gerar):
		chave = _digitos(original) if tipo in ("cpf", "pis", "cnpj", "numero") else str(original)
		if not chave:
			return original
		if tipo in ("cpf", "pis", "cnpj") and len(chave) >= 8:
			self.originais.add(chave)
		mapa = self.mapas[tipo]
		if chave not in mapa:
			mapa[chave] = gerar(len(mapa) + 1, chave)
		return mapa[chave]

	def _numero(self, n: int, chave: str) -> str:
		h = hashlib.sha256(f"{self.semente}|{chave}".encode()).hexdigest()
		return str(int(h, 16))[: max(4, min(len(chave), 11))]

	def anonimizar(self, valor):
		if isinstance(valor, list):
			return [self.anonimizar(v) for v in valor]
		if not isinstance(valor, dict):
			return valor
		chaves = {k.lower() for k in valor}
		eh_pessoa = bool(chaves & {"cpf", "numeropis"}) and "documento" not in chaves
		eh_empresa = "documento" in chaves and "tipodocumento" in chaves
		saida = {}
		for chave, v in valor.items():
			k = chave.lower()
			if v is None or v == "":
				saida[chave] = v
			elif k in CPF:
				saida[chave] = self._troca("cpf", v, lambda n, c: cpf_ficticio(n))
			elif k in PIS:
				saida[chave] = self._troca("pis", v, lambda n, c: pis_ficticio(n))
			elif k in CNPJ:
				saida[chave] = self._troca("cnpj", v, lambda n, c: cnpj_ficticio(n))
			elif k in NUMEROS:
				saida[chave] = self._troca("numero", v, self._numero)
			elif k == "nome" and eh_pessoa:
				saida[chave] = self._troca("pessoa", v, lambda n, c: f"Pessoa Exemplo {n:03d}")
			elif k == "nome" and eh_empresa:
				saida[chave] = self._troca("empresa", v, lambda n, c: f"Empresa Exemplo {n:02d} Ltda")
			elif k == "nascimento":
				saida[chave] = "1990-01-01T00:00:00"
			elif k in TEXTOS:
				saida[chave] = TEXTOS[k]
			else:
				saida[chave] = self.anonimizar(v)
		return saida

	def sobrou_original(self, dados) -> list[str]:
		"""Documentos reais (CPF, PIS, CNPJ) que ainda aparecem em algum texto do resultado: precisa ser vazio."""
		achados = set()

		def visitar(v):
			if isinstance(v, dict):
				for x in v.values():
					visitar(x)
			elif isinstance(v, list):
				for x in v:
					visitar(x)
			elif isinstance(v, str) and _digitos(v) in self.originais:
				achados.add(_digitos(v))

		visitar(dados)
		return sorted(achados)
