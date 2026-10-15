"""Mapeamento colaborador (Frappe) <-> funcionário (Secullum), diff e reconciliação. Python puro.

Campos e limites do recurso `Funcionarios` conforme o manual da Integração Externa (págs. 27-30).
O Secullum usa o CPF como chave do POST (inclusão ou alteração).
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from hrms_secullum_brasil.engine.documentos import somente_digitos

# Campos obrigatórios do POST Funcionarios. NumeroPis só é obrigatório em bancos com REP-A/REP-C e a
# validação de PIS ligada; quando o colaborador tem PIS, ele é enviado.
CAMPOS_OBRIGATORIOS = (
	"Nome",
	"NumeroFolha",
	"Cpf",
	"Admissao",
	"EmpresaCnpjCpf",
	"HorarioNumero",
	"DepartamentoDescricao",
	"FuncaoDescricao",
)

# Campos comparados na reconciliação (só os que este app envia).
CAMPOS_COMPARADOS = ("Nome", "NumeroFolha", "NumeroPis", "Admissao", "Demissao", *CAMPOS_OBRIGATORIOS[4:])

CAMPOS_SENSIVEIS = ("Cpf", "NumeroPis", "password", "senha")
CAMPOS_DOCUMENTO = ("Cpf", "NumeroPis", "EmpresaCnpjCpf")


@dataclass(frozen=True)
class DadosColaborador:
	nome: str | None
	cpf: str | None
	pis: str | None
	numero_folha: str | None
	admissao: date | None
	demissao: date | None
	empresa_documento: str | None
	horario_numero: int | None
	departamento: str | None
	funcao: str | None


def _texto(valor: str | None, limite: int) -> str | None:
	valor = (valor or "").strip()
	return valor[:limite] or None


def _data(valor: date | None) -> str | None:
	return valor.isoformat() if valor else None


def montar_payload_funcionario(d: DadosColaborador) -> dict:
	return {
		"Nome": _texto(d.nome, 150),
		"NumeroFolha": _texto(d.numero_folha, 22),
		"Cpf": somente_digitos(d.cpf) or None,
		"NumeroPis": somente_digitos(d.pis) or None,
		"Admissao": _data(d.admissao),
		"Demissao": _data(d.demissao),
		"EmpresaCnpjCpf": somente_digitos(d.empresa_documento) or None,
		"HorarioNumero": d.horario_numero or None,
		"DepartamentoDescricao": _texto(d.departamento, 50),
		"FuncaoDescricao": _texto(d.funcao, 50),
	}


def campos_faltantes(payload: dict) -> list[str]:
	return [campo for campo in CAMPOS_OBRIGATORIOS if not payload.get(campo)]


def hash_payload(payload: dict) -> str:
	"""Impressão digital do que seria enviado: muda só quando um campo relevante muda (PRD, 6.2)."""
	return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def mascarar(valor) -> str:
	texto = str(valor or "")
	return "*" * max(len(texto) - 4, 0) + texto[-4:] if len(texto) > 4 else "*" * len(texto)


def resumir_payload(payload, limite: int = 2000) -> str | None:
	"""JSON para o Sync Log com CPF/PIS mascarados (LGPD) e tamanho limitado."""
	if payload is None:
		return None

	def limpar(obj):
		if isinstance(obj, dict):
			return {k: mascarar(v) if k in CAMPOS_SENSIVEIS and v else limpar(v) for k, v in obj.items()}
		if isinstance(obj, list):
			return [limpar(v) for v in obj]
		return obj

	texto = json.dumps(limpar(payload), ensure_ascii=False, default=str)
	return texto if len(texto) <= limite else texto[: limite - 3] + "..."


# ------------------------------------------------------------------ reconciliação

SOMENTE_FRAPPE = "Somente no Frappe"
SOMENTE_SECULLUM = "Somente no Secullum"
CAMPO_DIVERGENTE = "Campo divergente"


@dataclass(frozen=True)
class Divergencia:
	tipo: str
	cpf: str
	campo: str | None = None
	valor_frappe: str | None = None
	valor_secullum: str | None = None
	nome_secullum: str | None = None


def _normalizar(campo: str, valor) -> str:
	if valor is None or valor == "":
		return ""
	if campo in CAMPOS_DOCUMENTO:
		return somente_digitos(str(valor))
	if campo in ("Admissao", "Demissao"):
		return str(valor)[:10]  # a API pode devolver "2024-01-15T00:00:00"
	return " ".join(str(valor).split()).casefold()


def comparar_cadastros(locais: dict[str, dict], remotos: Iterable[dict]) -> list[Divergencia]:
	"""Compara payloads do Frappe (chave = CPF) com a lista de funcionários do Secullum.

	Só compara campos presentes no registro do Secullum, para não acusar divergência quando a API
	devolve um formato diferente do POST. Nada é corrigido automaticamente (PRD, 6.2).
	"""
	divergencias = []
	remotos_por_cpf = {}
	for r in remotos:
		cpf = somente_digitos(str(r.get("Cpf") or ""))
		if cpf:
			remotos_por_cpf[cpf] = r

	for cpf in sorted(set(locais) - set(remotos_por_cpf)):
		divergencias.append(Divergencia(SOMENTE_FRAPPE, cpf))
	for cpf in sorted(set(remotos_por_cpf) - set(locais)):
		divergencias.append(
			Divergencia(SOMENTE_SECULLUM, cpf, nome_secullum=remotos_por_cpf[cpf].get("Nome"))
		)
	for cpf in sorted(set(locais) & set(remotos_por_cpf)):
		local, remoto = locais[cpf], remotos_por_cpf[cpf]
		for campo in CAMPOS_COMPARADOS:
			if campo not in remoto:
				continue
			if _normalizar(campo, local.get(campo)) != _normalizar(campo, remoto.get(campo)):
				divergencias.append(
					Divergencia(
						CAMPO_DIVERGENTE,
						cpf,
						campo,
						None if local.get(campo) is None else str(local.get(campo)),
						None if remoto.get(campo) is None else str(remoto.get(campo)),
						remoto.get("Nome"),
					)
				)
	return divergencias
