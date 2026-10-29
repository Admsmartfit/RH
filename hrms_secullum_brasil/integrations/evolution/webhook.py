"""Retorno de entrega/leitura da Evolution API v2 (docs/PRD-cockpit-escalas.md, CE-12). Python puro.

O evento `messages.update` traz o id da mensagem e o novo estado. A Evolution manda o estado como texto
("DELIVERY_ACK", "READ", "PLAYED") ou, em versões antigas, como número do Baileys (3 entregue, 4 lida, 5 ouvida).
"""

from collections.abc import Iterable

ENTREGUE = "Entregue"
LIDA = "Lida"
ESTADOS = {
	"DELIVERY_ACK": ENTREGUE,
	"DELIVERED": ENTREGUE,
	"READ": LIDA,
	"PLAYED": LIDA,
	3: ENTREGUE,
	4: LIDA,
	5: LIDA,
}
ORDEM = {"Enviada": 1, ENTREGUE: 2, LIDA: 3}


def _itens(dados) -> Iterable[dict]:
	if isinstance(dados, list):
		return [x for x in dados if isinstance(x, dict)]
	return [dados] if isinstance(dados, dict) else []


def estados(payload: dict) -> list[tuple[str, str]]:
	"""(id da mensagem, Entregue|Lida) de um webhook; ignora o que não é atualização de mensagem nossa."""
	if not isinstance(payload, dict):
		return []
	evento = str(payload.get("event") or "").lower().replace("_", ".")
	if evento and evento != "messages.update":
		return []
	resultado = []
	for item in _itens(payload.get("data")):
		chave = item.get("key") or {}
		if chave.get("fromMe") is False or item.get("fromMe") is False:
			continue
		ident = item.get("keyId") or chave.get("id") or item.get("messageId") or item.get("id")
		bruto = item.get("status")
		if bruto is None:
			bruto = (item.get("update") or {}).get("status")
		if isinstance(bruto, str) and bruto.isdigit():
			bruto = int(bruto)
		estado = ESTADOS.get(bruto.upper() if isinstance(bruto, str) else bruto)
		if ident and estado:
			resultado.append((str(ident), estado))
	return resultado


def avancar(atual: str | None, novo: str) -> bool:
	"""Só avança (Enviada → Entregue → Lida); uma confirmação atrasada não volta o estado."""
	return ORDEM.get(novo, 0) > ORDEM.get(atual or "", 0)
