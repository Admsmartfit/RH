"""Normalização e dígitos verificadores de CPF e PIS/PASEP/NIT."""


def somente_digitos(valor: str | None) -> str:
	return "".join(c for c in (valor or "") if c.isdigit())


def cpf_valido(cpf: str) -> bool:
	digitos = somente_digitos(cpf)
	if len(digitos) != 11 or digitos == digitos[0] * 11:
		return False
	numeros = [int(c) for c in digitos]
	for posicao in (9, 10):
		soma = sum(n * peso for n, peso in zip(numeros[:posicao], range(posicao + 1, 1, -1), strict=True))
		dv = soma * 10 % 11 % 10
		if dv != numeros[posicao]:
			return False
	return True


def pis_valido(pis: str) -> bool:
	digitos = somente_digitos(pis)
	if len(digitos) != 11 or digitos == digitos[0] * 11:
		return False
	pesos = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
	soma = sum(int(c) * p for c, p in zip(digitos[:10], pesos, strict=True))
	dv = 11 - soma % 11
	if dv >= 10:
		dv = 0
	return dv == int(digitos[10])
