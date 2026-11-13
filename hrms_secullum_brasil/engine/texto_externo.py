"""Texto que sai do programa (Secullum e WhatsApp ao colaborador): nunca falar de pausa ou intervalo pago,
remunerado ou "por liberalidade" (RH, 13/11/2026). Python puro.

- No Secullum (motivo da batida manual, nome da justificativa) o texto fica no espelho homologado: vai o fato neutro
  ("Intervalo incluído no cartão ponto"), nunca o efeito no pagamento.
- No WhatsApp ao colaborador (ou prestador), mensagem com esse texto não sai: fica barrada com o motivo.
O pagamento da pausa continua só na folha (rubrica PAUSA_PAGA) e no Ajuste lançado pelo RH no Secullum.
"""

import re

MOTIVO_NEUTRO = "Intervalo incluído no cartão ponto"
MOTIVO_BARRADA = "texto fala de pausa ou intervalo pago (não pode ir ao colaborador)"

_PROIBIDO = re.compile(
	r"\b(?:pausas?|intervalos?)\b[^.;\n]{0,80}?\b(?:n[aã]o\s+)?(?:pag[oa]s?|remunerad[oa]s?|indenizad[oa]s?)\b"
	r"|\b(?:pag[oa]s?|remunerad[oa]s?)\b[^.;\n]{0,20}?\b(?:pausas?|intervalos?)\b"
	r"|liberalidade",
	re.IGNORECASE,
)


def tem_texto_proibido(texto: str | None) -> bool:
	return bool(_PROIBIDO.search(texto or ""))


def motivo_para_o_secullum(motivo: str | None) -> str:
	"""O motivo que vai ao Secullum: o original, se neutro; senão o motivo neutro."""
	motivo = (motivo or "").strip()
	return MOTIVO_NEUTRO if tem_texto_proibido(motivo) else motivo
