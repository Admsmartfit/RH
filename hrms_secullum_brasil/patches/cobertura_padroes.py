"""docs/PRD-substituicoes.md: grava os padrões da cobertura na Configuração Apuração (o migrate não aplica o
`default` de campos novos de um Single) e cria as regras de WhatsApp dos eventos novos **desligadas** (Ativa
desmarcado) e **Em teste** (CE-09): nada sai nem entra na fila manual até o RH ligar cada uma."""

import frappe

from hrms_secullum_brasil.engine import cobertura as c
from hrms_secullum_brasil.engine import comunicacao as com

CONFIG = "Configuracao Apuracao"
REGRA = "Regra Envio WhatsApp"
PADROES = {
	"cobertura_t1_min": c.PADROES.t1,
	"cobertura_t2_min": c.PADROES.t2,
	"cobertura_por_rodada": c.PADROES.por_rodada,
	"cobertura_aviso_sem_batida_min": c.PADROES.aviso_sem_batida,
	"cobertura_max_plantoes_mes": c.PADROES.max_plantoes_mes,
	"cobertura_valor_hora": float(c.PADROES.valor_hora),
	"cobertura_hora_inicio": c.PADROES.hora_inicio,
	"cobertura_hora_fim": c.PADROES.hora_fim,
}
# evento → (para o colaborador/prestador, para o gestor)
REGRAS = {
	com.COBERTURA_INTERNO: (1, 0),
	com.COBERTURA_PRESTADOR: (1, 0),
	com.COBERTURA_CONFIRMADA: (1, 0),
	com.COBERTURA_PREENCHIDA: (0, 1),
	com.COBERTURA_NAO_PREENCHIDA: (0, 1),
	com.COBERTURA_SEM_BATIDA: (0, 1),
	com.TALENTOS_CADASTRO: (1, 0),
}


def execute():
	frappe.reload_doc("configuracao_ponto", "doctype", "configuracao_apuracao")
	frappe.reload_doc("apuracao", "doctype", "regra_envio_whatsapp")
	for campo, valor in PADROES.items():
		gravado = frappe.db.sql("select value from tabSingles where doctype=%s and field=%s", (CONFIG, campo))
		if not gravado or gravado[0][0] in (None, ""):
			frappe.db.set_single_value(CONFIG, campo, valor)
	for evento, (colaborador, gestor) in REGRAS.items():
		if frappe.db.exists(REGRA, {"evento": evento}):
			continue
		frappe.get_doc(
			{
				"doctype": REGRA,
				"nome_regra": evento,
				"ativa": 0,
				"evento": evento,
				"para_colaborador": colaborador,
				"para_gestor": gestor,
				"situacao": com.EM_TESTE,
				"mensagem_colaborador": com.texto_padrao(evento, "Colaborador") if colaborador else None,
				"mensagem_gestor": com.texto_padrao(evento, "Gestor") if gestor else None,
			}
		).insert(ignore_permissions=True)
