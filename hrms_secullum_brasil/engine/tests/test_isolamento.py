"""Garante que engine/ e integrations/ continuam Python puro (PRD, Seção 3.2 e AGENTS.md)."""

import ast
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ENGINE_DIR.parent
PACOTES_PUROS = (ENGINE_DIR, APP_DIR / "integrations", APP_DIR / "otimizacao")
PACOTES_PROIBIDOS = ("frappe", "erpnext", "hrms")
# o engine fica só com a biblioteca padrão: o otimizador (OR-Tools) mora em otimizacao/ (docs/PRD-planejador-5x2.md)
SO_FORA_DO_ENGINE = ("ortools",)


def _eh_proibido(nome: str, proibidos=PACOTES_PROIBIDOS) -> bool:
	return nome.split(".")[0] in proibidos


def imports_proibidos(arquivo: Path, proibidos=PACOTES_PROIBIDOS) -> list[str]:
	arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
	achados = []
	for no in ast.walk(arvore):
		if isinstance(no, ast.Import):
			achados += [alias.name for alias in no.names if _eh_proibido(alias.name, proibidos)]
		elif (
			isinstance(no, ast.ImportFrom)
			and no.level == 0
			and no.module
			and _eh_proibido(no.module, proibidos)
		):
			achados.append(no.module)
	return achados


def test_pacotes_puros_nao_importam_frappe():
	violacoes = [
		f"{arquivo.relative_to(APP_DIR)}: {nome}"
		for pacote in PACOTES_PUROS
		for arquivo in sorted(pacote.rglob("*.py"))
		for nome in imports_proibidos(arquivo)
	]
	assert not violacoes, "engine/ e integrations/ devem ser Python puro:\n" + "\n".join(violacoes)


def test_detector_pega_imports_proibidos(tmp_path):
	arquivo = tmp_path / "exemplo.py"
	arquivo.write_text(
		"import os\nimport frappe\nfrom hrms.payroll import x\nfrom erpnext import y\nfrom . import z\n",
		encoding="utf-8",
	)
	assert imports_proibidos(arquivo) == ["frappe", "hrms.payroll", "erpnext"]
