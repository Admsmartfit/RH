"""Índices compostos da auditoria de 02/11/2026 (docs/auditoria-2026-11.md). O `on_doctype_update` de cada
controller só roda quando o JSON do DocType muda; este patch os cria nos sites que já existem."""

from importlib import import_module

CONTROLLERS = (
	"hrms_secullum_brasil.apuracao.doctype.apuracao_diaria.apuracao_diaria",
	"hrms_secullum_brasil.apuracao.doctype.inconsistencia_de_ponto.inconsistencia_de_ponto",
	"hrms_secullum_brasil.apuracao.doctype.reapuracao_pendente.reapuracao_pendente",
	"hrms_secullum_brasil.apuracao.doctype.tratamento_de_ponto.tratamento_de_ponto",
	"hrms_secullum_brasil.ingestion.doctype.secullum_checkin_raw.secullum_checkin_raw",
)


def execute():
	for modulo in CONTROLLERS:
		import_module(modulo).on_doctype_update()
