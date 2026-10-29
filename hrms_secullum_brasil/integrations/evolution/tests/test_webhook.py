"""Retorno de entrega/leitura da Evolution (docs/PRD-cockpit-escalas.md, CE-12)."""

from hrms_secullum_brasil.integrations.evolution.webhook import ENTREGUE, LIDA, avancar, estados


def test_formato_v2_com_status_em_texto():
	payload = {
		"event": "messages.update",
		"instance": "ponto",
		"data": {
			"keyId": "3EB0A1",
			"remoteJid": "5527999990077@s.whatsapp.net",
			"fromMe": True,
			"status": "DELIVERY_ACK",
		},
	}
	assert estados(payload) == [("3EB0A1", ENTREGUE)]
	payload["data"]["status"] = "READ"
	assert estados(payload) == [("3EB0A1", LIDA)]


def test_formato_baileys_com_numero_e_lista():
	payload = {
		"event": "MESSAGES_UPDATE",
		"data": [
			{"key": {"id": "A1", "fromMe": True}, "update": {"status": 3}},
			{"key": {"id": "A2", "fromMe": True}, "update": {"status": "4"}},
			{"key": {"id": "A3", "fromMe": False}, "update": {"status": 4}},  # mensagem recebida: ignora
			{"key": {"id": "A4", "fromMe": True}, "update": {"status": 2}},  # só chegou ao servidor
		],
	}
	assert estados(payload) == [("A1", ENTREGUE), ("A2", LIDA)]


def test_outros_eventos_e_lixo_sao_ignorados():
	assert estados({"event": "messages.upsert", "data": {"keyId": "X", "status": "READ"}}) == []
	assert estados({"event": "messages.update", "data": "nada"}) == []
	assert estados(None) == []
	assert estados({"data": {"id": "S1", "status": "PLAYED"}}) == [("S1", LIDA)]


def test_estado_so_avanca():
	assert avancar("Enviada", ENTREGUE) and avancar(ENTREGUE, LIDA) and avancar(None, ENTREGUE)
	assert not avancar(LIDA, ENTREGUE) and not avancar(ENTREGUE, ENTREGUE)
