"""Texto que sai para o Secullum e para o colaborador: nada de pausa/intervalo pago (RH, 13/11/2026)."""

import pytest

from hrms_secullum_brasil.engine import intervalo_horista as ih
from hrms_secullum_brasil.engine import texto_externo as t


@pytest.mark.parametrize(
	"texto",
	[
		"Pausa paga por liberalidade (intervalo de 15 min)",
		"Intervalo remunerado de 15 minutos",
		"pausa remunerada",
		"Intervalo não marcado — lançado pelo RH (instrutor horista, não remunerado)",
		"o intervalo que faltou é pago como indenização",
		"PAUSA PAGA LIBERALIDADE",
		"15 min de pausa paga",
		"intervalo indenizado",
	],
)
def test_proibidos(texto):
	assert t.tem_texto_proibido(texto)
	assert t.motivo_para_o_secullum(texto) == t.MOTIVO_NEUTRO


@pytest.mark.parametrize(
	"texto",
	[
		"Esqueceu de bater o ponto",
		"Intervalo não registrado — termo assinado",
		"Intervalo incluído no cartão ponto",
		"Atestado médico",
		"Licença não remunerada",
		"",
		None,
	],
)
def test_permitidos(texto):
	assert not t.tem_texto_proibido(texto)
	assert t.motivo_para_o_secullum(texto) == (texto or "").strip()


def test_motivos_do_programa_ja_sao_neutros():
	from hrms_secullum_brasil.integrations.secullum import sincronizacao as s

	assert not t.tem_texto_proibido(ih.MOTIVO)
	assert not t.tem_texto_proibido(s.MOTIVO_PAUSA)
	assert not t.tem_texto_proibido(s.PAUSA_PAGA.nome_completo)
