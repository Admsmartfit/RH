"""Comunicação com o colaborador por WhatsApp (docs/configuracao_operacao.md): textos padrão das regras de envio e
quem a regra alcança. Python puro; o envio e a trava ficam em apuracao/whatsapp.py e apuracao/regras_whatsapp.py.
"""

from collections.abc import Iterable
from datetime import date

BATIDA_ESQUECIDA = "Ponto do dia: batida esquecida (marcação ímpar)"
FALTA = "Ponto do dia: falta sem justificativa"
HORISTA = "Horista além de 4h sem intervalo (limite do mês)"
ESCALA = "Escala: turno incluído/alterado/removido"  # docs/PRD-cockpit-escalas.md (CE-08)
COBRANCA = "Cobrança de inconsistência"  # docs/PRD-tratamento-inconsistencias.md (TI-08)
DISPONIBILIDADE = "Escala: pedido de disponibilidade"  # docs/PRD-cockpit-escalas.md (CE-14)
ASSINATURA = "Jornada: documento para assinar"  # docs/PRD-cockpit-escalas.md (CE-16)
CONVITE = "Escala: convite para turno"  # convite para um turno específico (pedido do RH, 27/10/2026)
# docs/PRD-termo-ocorrencias.md (TO-06, TO-09)
TERMO = "Termo de ocorrências"
TERMO_GERENTE = "Termo pendente — gerente"
TERMO_RH = "Termo pendente — RH"
# docs/PRD-whatsapp-dia-seguinte.md: uma regra por tipo de inconsistência (o tipo fica na regra); os dois eventos
# antigos continuam valendo, com o tipo fixo
D1 = "Ponto do dia (D+1)"
RESPOSTA_D1 = "Resposta do colaborador (D+1) — gestor"
EVENTOS_DO_DIA = {BATIDA_ESQUECIDA: "marcacao_impar", FALTA: "falta"}
# docs/PRD-substituicoes.md (cobertura de faltas e Banco de Talentos)
COBERTURA_INTERNO = "Cobertura: oferta (interno)"
COBERTURA_PRESTADOR = "Cobertura: oferta (prestador)"
COBERTURA_CONFIRMADA = "Cobertura: confirmada"
COBERTURA_PREENCHIDA = "Cobertura: vaga preenchida — gestor"
COBERTURA_NAO_PREENCHIDA = "Cobertura: vaga não preenchida — gestor"
COBERTURA_SEM_BATIDA = "Cobertura: falta sem batida — gestor"
TALENTOS_CADASTRO = "Banco de Talentos: cadastro"
EVENTOS_COBERTURA = (
	COBERTURA_INTERNO,
	COBERTURA_PRESTADOR,
	COBERTURA_CONFIRMADA,
	COBERTURA_PREENCHIDA,
	COBERTURA_NAO_PREENCHIDA,
	COBERTURA_SEM_BATIDA,
	TALENTOS_CADASTRO,
)
EM_TESTE = "Em teste"
EM_PRODUCAO = "Em produção"

DIAS_SEMANA = (
	"segunda-feira",
	"terça-feira",
	"quarta-feira",
	"quinta-feira",
	"sexta-feira",
	"sábado",
	"domingo",
)

TEXTOS = {
	(BATIDA_ESQUECIDA, "Colaborador"): (
		"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) o seu ponto ficou com uma batida faltando "
		"(registrado: {batidas}). Se esqueceu de bater, avise o seu gestor para o RH corrigir."
	),
	(BATIDA_ESQUECIDA, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} ficou com uma batida faltando no dia {data} ({dia_semana}); "
		"registrado: {batidas}. Confira e corrija no cartão ponto."
	),
	(FALTA, "Colaborador"): (
		"Olá, {primeiro_nome}! Não encontramos batidas no dia {data} ({dia_semana}). Se você trabalhou ou tem "
		"justificativa (atestado, declaração), fale com o seu gestor."
	),
	(FALTA, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} não tem batidas no dia {data} ({dia_semana}). Confira no cartão ponto."
	),
	(ESCALA, "Colaborador"): (
		"Olá, {primeiro_nome}! Aviso de escala — {empresa}. Sua escala mudou:\n{mudancas}\n"
		"Qualquer dúvida, fale com o seu gestor."
	),
	(DISPONIBILIDADE, "Colaborador"): (
		"Olá, {primeiro_nome}! Até {prazo}, informe os dias e horários em que você NÃO pode trabalhar em {mes}: {link}\n"
		"O link é só seu e vale por 7 dias."
	),
	(ASSINATURA, "Colaborador"): (
		"Olá, {primeiro_nome}! A {empresa} enviou o {documento} sobre o seu horário a partir de {data}. Leia e assine "
		"pelo link (prazo: {prazo}): {link}"
	),
	(CONVITE, "Colaborador"): (
		"Olá, {primeiro_nome}! A {empresa} tem um turno em {data} ({dia_semana}), das {horario}. Você pode trabalhar? "
		"Responda pelo link: {link}"
	),
	(TERMO, "Colaborador"): (
		"Olá, {primeiro_nome}! No seu cartão de ponto de {periodo} encontramos estas ocorrências:\n{ocorrencias}\n"
		"O seu gerente vai apresentar o Termo de ocorrências {codigo}, com a correção de cada dia, para você conferir e "
		"assinar. Se não concordar com algum item, informe no próprio termo.{link_assinatura}\nObrigado!"
	),
	(TERMO_GERENTE, "Gestor"): (
		"Olá, {primeiro_nome}! O Termo de ocorrências {codigo} de {colaborador}, emitido em {emissao}, ainda não foi "
		"assinado (prazo: {prazo}). Colha a assinatura e registre pelo link: {link}"
	),
	(TERMO_RH, "RH"): (
		"RH: o Termo de ocorrências {codigo} de {colaborador} ({empresa}), emitido em {emissao}, está há {dias} dias "
		"úteis sem assinatura. Gestor: {gestor}."
	),
	(D1, "Colaborador"): (
		"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) o seu ponto ficou com: {descricao}\n"
		"Se precisar corrigir ou explicar, responda pelo link (é só seu): {link}"
	),
	(D1, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} ficou com pendência no ponto do dia {data} ({dia_semana}): "
		"{descricao} Confira no cartão ponto."
	),
	(RESPOSTA_D1, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} respondeu sobre o ponto do dia {data}: {resumo}. Confira e aprove no "
		"painel de ponto (Inconsistências → WhatsApp do dia seguinte)."
	),
	# cobertura de faltas: só os campos do turno e o link pessoal; nunca instrução interna nem dado de outra pessoa
	(COBERTURA_INTERNO, "Colaborador"): (
		"Oi, {primeiro_nome}! Surgiu um turno na {empresa}: {dia_semana} {data}, das {horario}. Se puder, toque no "
		"link e confirme. O primeiro que confirmar fica com o turno: {link}"
	),
	(COBERTURA_PRESTADOR, "Colaborador"): (
		"🚨 Cobertura avulsa — {empresa}. Olá, {primeiro_nome}! {dia_semana} {data}, das {horario} ({duracao}). "
		"Valor: R$ {valor} (pagamento via NFS-e do seu CNPJ). O primeiro que confirmar pelo link fica com o "
		"horário: {link}"
	),
	(COBERTURA_CONFIRMADA, "Colaborador"): (
		"Confirmado, {primeiro_nome}! O turno de {dia_semana} {data}, das {horario}, na {empresa}, é seu. Obrigado!"
	),
	(COBERTURA_PREENCHIDA, "Gestor"): (
		"Olá, {primeiro_nome}! A vaga de {dia_semana} {data}, das {horario}, foi preenchida por {quem}."
	),
	(COBERTURA_NAO_PREENCHIDA, "Gestor"): (
		"Olá, {primeiro_nome}! Ninguém aceitou a vaga de {dia_semana} {data}, das {horario}. O horário continua "
		"descoberto: confira a tela Escalas."
	),
	(COBERTURA_SEM_BATIDA, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} não bateu o ponto para o turno das {horario} de hoje. Se for falta, "
		"abra a vaga de cobertura na tela Escalas: {link}"
	),
	(TALENTOS_CADASTRO, "Colaborador"): ("Olá, {primeiro_nome}! Banco de Talentos — {empresa}: {situacao}"),
	(COBRANCA, "Colaborador"): (
		"Olá, {primeiro_nome}! Notei uma pendência no seu cartão de ponto no dia {data} ({dia_semana}).\n"
		"Motivo: {descricao}\nPor favor, procure o seu gerente para justificar o mais breve possível. Obrigado!"
	),
}


PARTICULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_proprio(nome: str | None) -> str:
	"""Nome como se escreve ("LEANDRO DA SILVA" → "Leandro da Silva"): o Secullum guarda tudo em maiúsculas."""
	palavras = str(nome or "").strip().split()
	return " ".join(
		p.lower() if n and p.lower() in PARTICULAS else p[:1].upper() + p[1:].lower()
		for n, p in enumerate(palavras)
	)


def texto_padrao(evento: str, destinatario: str) -> str:
	return TEXTOS.get((evento, destinatario), "")


def alcanca(empresa: str | None, cargo: str | None, empresas: Iterable[str], cargos: Iterable[str]) -> bool:
	"""Filtro da regra: lista vazia = todos."""
	empresas, cargos = set(empresas), set(cargos)
	return (not empresas or empresa in empresas) and (not cargos or cargo in cargos)


def data_curta(dia: date) -> str:
	return f"{dia:%d/%m}"


def dia_da_semana(dia: date) -> str:
	return DIAS_SEMANA[dia.weekday()]


def chave(regra: str, employee: str, dia: date | str, destinatario: str) -> str:
	"""Identifica um aviso: a mesma regra não manda duas vezes o mesmo dia para a mesma pessoa."""
	return f"{regra}|{employee}|{dia}|{destinatario}"[:140]


def primeiro_nome(nome: str | None) -> str:
	partes = str(nome or "").split()
	return nome_proprio(partes[0]) if partes else ""


def linhas_de_mudanca(mudancas: Iterable[tuple[date, str, str]]) -> str:
	"""CE-08: uma linha por dia mudado — "• sáb 07/11: 08:00-11:00, 11:15-14:15 (antes: Neutro)"."""
	linhas = []
	for dia, antes, depois in sorted(mudancas):
		texto = (
			depois
			if depois not in ("Neutro", "Folga compensada", "Repouso semanal")
			else f"folga ({depois.lower()})"
		)
		anterior = f" (antes: {antes})" if antes and antes != depois else ""
		linhas.append(f"• {DIAS_SEMANA[dia.weekday()][:3]} {data_curta(dia)}: {texto}{anterior}")
	return "\n".join(linhas)


def aguarda_envio_manual(situacao_regra: str | None) -> bool:
	"""CE-09: regra em teste (ou sem situação, como as antigas) não envia sozinha."""
	return (situacao_regra or EM_TESTE) == EM_TESTE
