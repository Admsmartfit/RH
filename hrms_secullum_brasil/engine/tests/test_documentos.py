import pytest

from hrms_secullum_brasil.engine.documentos import cpf_valido, pis_valido, somente_digitos


def test_somente_digitos():
	assert somente_digitos("529.982.247-25") == "52998224725"
	assert somente_digitos(None) == ""


@pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725", "111.444.777-35"])
def test_cpf_valido(cpf):
	assert cpf_valido(cpf)


@pytest.mark.parametrize("cpf", ["529.982.247-24", "111.111.111-11", "123", ""])
def test_cpf_invalido(cpf):
	assert not cpf_valido(cpf)


@pytest.mark.parametrize("pis", ["170.33259.50-4", "120.5641.254-5", "10000000040"])  # o último tem DV 0
def test_pis_valido(pis):
	assert pis_valido(pis)


@pytest.mark.parametrize("pis", ["170.33259.50-5", "00000000000", "123"])
def test_pis_invalido(pis):
	assert not pis_valido(pis)
