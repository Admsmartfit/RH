"""Entrada no programa (RH, 04/11/2026): quem usa o painel entra no /ponto; o workspace padrão gravado pelo
aplicar_brasil venceria a página inicial e é tirado desses usuários."""

from hrms_secullum_brasil.utils.acesso import tirar_workspace_padrao


def execute():
	tirar_workspace_padrao()
