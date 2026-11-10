"""WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md): filtros de segurança, textos por tipo,
liberação gradual da regra e prazo de resposta. Python puro.

Enquanto o sistema está em ajuste, a mensagem só sai se passar por todos os filtros (seção 4 do PRD) e, com a regra
em teste, pela conferência do RH. Nada aqui grava ou envia: o Frappe (`apuracao/dia_seguinte.py`) lê os fatos do dia,
pergunta ao engine e registra o motivo de cada mensagem barrada.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from hrms_secullum_brasil.engine.sugestoes import COBRAVEIS, orientar
from hrms_secullum_brasil.engine.termo_ocorrencias import somar_dias_uteis

# tipos que o D+1 pode avisar: os do ponto do dia (os mesmos do "Cobrar pelo WhatsApp")
TIPOS_D1 = COBRAVEIS
# dependem da jornada prevista: sem jornada no dia (neutro, feriado, folga) não fazem sentido
DEPENDEM_DO_PREVISTO = frozenset({"falta", "atraso"})
# a falta de quem trabalha em escala só vale com a escala do mês publicada (evita "falta" por erro de escala)
EXIGEM_ESCALA = frozenset({"falta"})
PERFIS_DE_ESCALA = frozenset({"Escala", "Horista", "Intermitente", "Fragmentada"})

MINIMO_CONFERIDAS = 20  # mensagens conferidas e enviadas antes de a regra ir a produção
LIMITE_DESCARTES = 3  # descartes por erro em 7 dias que devolvem a regra a teste
JANELA_DESCARTES_DIAS = 7
HORAS_ESTABILIZAR = 2  # pendência mais nova que isto espera a próxima rodada (releitura do Secullum)
DIAS_UTEIS_RESPOSTA = 2  # sem resposta neste prazo, o dia vai para o termo do fechamento
VALIDADE_LINK_DIAS = 7

# motivos de bloqueio (registrados na mensagem barrada)
SEM_ESCALA = "dia sem escala publicada (perfil de escala)"
SEM_JORNADA = "dia sem jornada prevista (neutro, feriado, repouso ou folga)"
AUSENCIA = "ausência justificada no dia (férias, afastamento, licença ou atestado)"
RECENTE = "pendência aberta há pouco (esperando a releitura do Secullum)"
NO_TERMO = "o dia já está num termo de ocorrências aberto"
JA_COBRADO = "o dia já foi cobrado pelo WhatsApp"
JA_RESPONDIDO = "o colaborador já respondeu sobre o dia"
FECHADO = "período fechado"
INATIVO = "colaborador desligado"
TIPO_FORA = "tipo de inconsistência que o D+1 não avisa"


@dataclass(frozen=True)
class FatosDoDia:
	"""O que o Frappe leu sobre uma pendência de um dia de uma pessoa."""

	tipo: str
	perfil_tipo: str = "Fixa"
	escala_publicada: bool = False
	tem_jornada: bool = True  # falso em neutro, feriado, repouso, folga
	ausencia_justificada: bool = False
	aberta_em: datetime | None = None
	no_termo: bool = False
	ja_cobrado: bool = False
	ja_respondido: bool = False
	periodo_fechado: bool = False
	ativo: bool = True


def bloqueio(fatos: FatosDoDia, agora: datetime, horas_estabilizar: int = HORAS_ESTABILIZAR) -> str | None:
	"""Por que a mensagem do dia NÃO deve sair (None = pode sair). O primeiro motivo vence."""
	if fatos.tipo not in TIPOS_D1:
		return TIPO_FORA
	if not fatos.ativo:
		return INATIVO
	if fatos.periodo_fechado:
		return FECHADO
	if fatos.no_termo:
		return NO_TERMO
	if fatos.ja_respondido:
		return JA_RESPONDIDO
	if fatos.ja_cobrado:
		return JA_COBRADO
	if fatos.ausencia_justificada:
		return AUSENCIA
	if fatos.tipo in DEPENDEM_DO_PREVISTO and not fatos.tem_jornada:
		return SEM_JORNADA
	if fatos.tipo in EXIGEM_ESCALA and fatos.perfil_tipo in PERFIS_DE_ESCALA and not fatos.escala_publicada:
		return SEM_ESCALA
	if horas_estabilizar and fatos.aberta_em and agora - fatos.aberta_em < timedelta(hours=horas_estabilizar):
		return RECENTE
	return None


# ------------------------------------------------------------------ textos

MARCADORES = "{primeiro_nome}, {data}, {dia_semana}, {batidas}, {descricao}, {quantidade}, {link}"
FECHO = "Para justificar o ocorrido ou solicitar a correção, acesse o seu link exclusivo: {link}"
TEXTO_COLABORADOR = (
	"Olá, {primeiro_nome}!\n\nIdentificamos uma pendência no seu registro de ponto de {data} ({dia_semana}):\n"
	"• {descricao}\n\n" + FECHO
)
TEXTOS_COLABORADOR = {
	"marcacao_impar": (
		"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) o seu ponto ficou com uma batida faltando "
		"(registrado: {batidas}). Se esqueceu de bater, informe o horário pelo link (é só seu): {link}"
	),
	"falta": (
		"Olá, {primeiro_nome}! Não encontramos batidas no dia {data} ({dia_semana}). Se você trabalhou ou tem "
		"justificativa, responda pelo link (é só seu): {link}"
	),
	"atraso": (
		"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) o seu ponto registrou atraso ou saída antecipada "
		"(registrado: {batidas}). Se houve algum motivo, responda pelo link (é só seu): {link}"
	),
}
# mensagens que nunca saem sozinhas: o RH confere e envia (notificação oficial; pedido do RH de 04/11/2026)
SEMPRE_CONFERIR = frozenset({"excesso_jornada_nao_autorizada"})
TEXTOS_COLABORADOR["intrajornada"] = (
	"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) você passou do horário sem registrar a pausa (registrado: "
	"{batidas}). Se fez a pausa, informe o horário pelo link (é só seu): {link}"
)
TEXTOS_COLABORADOR["excesso_jornada_nao_autorizada"] = (
	"Olá, {primeiro_nome}. No dia {data} ({dia_semana}) você trabalhou além da sua jornada contratada sem autorização "
	"(registrado: {batidas}). As horas serão pagas, mas horas além da jornada precisam de autorização prévia do seu "
	"gestor. Por favor, siga a jornada combinada. Se houve algum motivo, responda pelo link (é só seu): {link}"
)
TEXTO_VARIOS = (
	"Olá, {primeiro_nome}!\n\nIdentificamos {quantidade} pendências no seu registro de ponto de {data} "
	"({dia_semana}):\n{descricao}\n\n" + FECHO
)

# O que o colaborador (e o gestor) lê na mensagem: curto, sem orientação interna do RH (pedido do RH, 08/11/2026).
# A explicação do balão do cartão (`sugestoes`) é para o RH e nunca vai no WhatsApp quando há texto aqui.
DESCRICOES_COLABORADOR = {
	"marcacao_impar": "Batida de entrada ou de saída faltando.",
	"marcacao_duplicada": "Ponto registrado duas vezes seguidas.",
	"falta": "Nenhum registro num dia de trabalho previsto.",
	"atraso": "Entrada depois do horário previsto ou saída antecipada, além da tolerância.",
	"he_acima_limite": "Horas extras acima do limite diário permitido.",
	"intrajornada": "Intervalo de almoço inferior ao tempo mínimo estabelecido.",
	"interjornada": "Descanso inferior a 11 horas entre o fim de um dia e o início do seguinte.",
	"intervalo_superior_2h": "Intervalo superior a 2 horas.",
	"intervalo_fora_de_hora": "Intervalo registrado no início ou no fim do expediente.",
	"excesso_jornada_nao_autorizada": (
		"Registro de horas além da jornada contratada sem autorização prévia (mesmo considerando tolerâncias e pausas)."
	),
	"excesso_jornada_horista": "Jornada acima de 4 horas sem registro do intervalo.",
	"aula_nao_registrada": "Aula prevista na grade sem registro de ponto.",
	"descanso_semanal": "Descanso semanal inferior ao mínimo.",
	"sete_dias_seguidos": "Sete dias seguidos de trabalho sem o descanso semanal.",
	"domingos_sem_folga": "Domingos seguidos de trabalho sem folga.",
	"folgas_semanais": "Semana com menos folgas do que o previsto.",
	"excesso_jornada_estagio": "Jornada diária acima do limite do estágio.",
	"excesso_semanal_estagio": "Carga semanal acima do limite do estágio.",
}
EXTENSO = {
	2: "duas",
	3: "três",
	4: "quatro",
	5: "cinco",
	6: "seis",
	7: "sete",
	8: "oito",
	9: "nove",
	10: "dez",
}
TEXTO_GESTOR = (
	"Olá, {primeiro_nome}! {colaborador} ficou com pendência no ponto do dia {data} ({dia_semana}): {descricao} "
	"Confira no cartão ponto."
)
TEXTO_RESPOSTA_GESTOR = (
	"Olá, {primeiro_nome}! {colaborador} respondeu sobre o ponto do dia {data}: {resumo}. Confira e aprove no "
	"painel de ponto (Inconsistências → Aguardando aprovação)."
)


def texto_padrao(tipo: str) -> str:
	return TEXTOS_COLABORADOR.get(tipo, TEXTO_COLABORADOR)


def explicacao(tipo: str) -> str:
	"""Em linguagem simples, sem contar batidas (o texto não tem as batidas do dia)."""
	return DESCRICOES_COLABORADOR.get(tipo) or orientar(tipo).explicacao


def _distintos(tipos: Iterable[str]) -> list[str]:
	vistos = []
	for tipo in tipos:
		if tipo not in vistos:
			vistos.append(tipo)
	return vistos


def quantidade(tipos: Iterable[str]) -> str:
	"""Quantas pendências, por extenso ("duas pendências")."""
	n = len(_distintos(tipos))
	return "uma" if n == 1 else EXTENSO.get(n, str(n))


def descricao_dos_tipos(tipos: Iterable[str]) -> str:
	"""Várias pendências no mesmo dia: uma linha por tipo, sem repetir."""
	vistos = _distintos(tipos)
	if len(vistos) == 1:
		return explicacao(vistos[0])
	return "\n".join(f"• {explicacao(t)}" for t in vistos)


def com_link(texto: str) -> str:
	"""Mensagem do colaborador sem o marcador {link} (texto antigo ou editado): o link vai no fim."""
	return texto if "{link}" in texto else f"{texto}\nResponda pelo link (é só seu): {{link}}"


# ------------------------------------------------------------------ liberação gradual


def pode_ir_para_producao(conferidas: int, minimo: int = MINIMO_CONFERIDAS) -> tuple[bool, int]:
	"""(pode, quantas faltam). `minimo` 0 = sem exigência."""
	faltam = max(0, minimo - conferidas)
	return faltam == 0, faltam


def deve_voltar_para_teste(
	descartes: Iterable[datetime], agora: datetime, limite: int = LIMITE_DESCARTES
) -> bool:
	"""Descartes por erro (mensagem errada) nos últimos 7 dias chegaram ao limite."""
	if not limite:
		return False
	desde = agora - timedelta(days=JANELA_DESCARTES_DIAS)
	return sum(1 for d in descartes if d >= desde) >= limite


# ------------------------------------------------------------------ prazo de resposta


def prazo_da_resposta(enviada_em: date, feriados: set[date], dias_uteis: int = DIAS_UTEIS_RESPOSTA) -> date:
	return somar_dias_uteis(enviada_em, dias_uteis, feriados)


def sem_resposta(
	enviada_em: date, hoje: date, feriados: set[date], dias_uteis: int = DIAS_UTEIS_RESPOSTA
) -> bool:
	"""Passou o prazo (em dias úteis) sem resposta: o dia vai para o termo do fechamento."""
	return hoje > prazo_da_resposta(enviada_em, feriados, dias_uteis)


def pausas_incluidas(antes: Iterable[str], informados: Iterable[str]) -> int:
	"""Quantas pausas a resposta cria (intervalo com uma ponta que não estava nas batidas). Pelo WhatsApp, o cargo com
	pausa paga inclui no máximo uma por dia (RH, 04/11/2026). Horários "HH:MM" do mesmo dia."""
	originais = set(antes)
	horas = sorted(informados)
	return sum(
		1 for i in range(1, len(horas) - 1, 2) if horas[i] not in originais or horas[i + 1] not in originais
	)


def resumo_da_resposta(dias: Iterable[dict]) -> str:
	"""Para o aviso ao gestor: "incluiu 17:00 em 03/11; explicou 04/11 (treinamento)"."""
	partes = []
	for d in dias:
		data = d["data"]
		if d.get("nao_reconhece"):
			partes.append(f"não reconhece {data}")
		elif d.get("incluidos") or d.get("retirados"):
			mudou = []
			if d.get("incluidos"):
				mudou.append("incluiu " + ", ".join(d["incluidos"]))
			if d.get("retirados"):
				mudou.append("tirou " + ", ".join(d["retirados"]))
			partes.append(f"{' e '.join(mudou)} em {data}")
		if d.get("explicacao"):
			partes.append(f"explicou {data} ({d['explicacao'][:60]})")
	return "; ".join(partes) or "confirmou os horários"


# ------------------------------------------------------------------ selos na central e no cartão (pedido do RH, 04/11/2026)

ORIGEM_COLABORADOR = "Informado pelo colaborador no WhatsApp"  # começo do motivo do tratamento da resposta
NEUTRO, ATENCAO, BOM, RUIM = "neutro", "atencao", "bom", "ruim"


def selo_whatsapp(
	situacao: str | None,
	enviada_em: date | None = None,
	lida: bool = False,
	prazo: date | None = None,
	sem_resposta: bool = False,
	filtro: str | None = None,
	resposta: str | None = None,
) -> dict | None:
	"""O que a linha da central mostra sobre o aviso do dia seguinte: {texto, tom}. None = sem aviso."""
	dia = lambda d: f"{d:%d/%m}"  # noqa: E731
	if resposta == "Aguardando aprovação":
		return {"texto": "Respondeu — aprovar", "tom": ATENCAO}
	if resposta in ("Aprovada", "Parcial"):
		return {"texto": f"Respondeu — {resposta.lower()}", "tom": BOM}
	if resposta == "Recusada":
		return {"texto": "Resposta recusada", "tom": RUIM}
	if situacao == "Barrada":
		return {"texto": f"WhatsApp barrado: {filtro or 'filtro de segurança'}", "tom": NEUTRO}
	if situacao == "Aguardando envio manual":
		return {"texto": "WhatsApp aguardando a sua conferência", "tom": ATENCAO}
	if situacao == "Descartada":
		return {"texto": "WhatsApp descartado", "tom": NEUTRO}
	if situacao in ("Enviada", "Entregue", "Lida"):
		quando = f" {dia(enviada_em)}" if enviada_em else ""
		visto = " · lido" if lida or situacao == "Lida" else ""
		if sem_resposta:
			return {"texto": f"WhatsApp{quando}{visto} · sem resposta (vai para o termo)", "tom": RUIM}
		ate = f" até {dia(prazo)}" if prazo else ""
		return {"texto": f"WhatsApp{quando}{visto} · aguardando resposta{ate}", "tom": NEUTRO}
	if situacao:
		return {"texto": f"WhatsApp: {situacao.lower()}", "tom": RUIM}
	return None


def com_o_colaborador(situacao: str | None, sem_resposta: bool, respondeu: bool) -> bool:
	"""Avisado, dentro do prazo e sem resposta: a pendência está com o colaborador (sai da lista do RH)."""
	return situacao in ("Enviada", "Entregue", "Lida") and not sem_resposta and not respondeu


def origem_da_correcao(motivos: Iterable[str]) -> str:
	return "colaborador" if any(str(m or "").startswith(ORIGEM_COLABORADOR) for m in motivos) else "rh"


def resumo_das_correcoes(correcoes: Iterable[dict | None]) -> dict:
	"""Topo do cartão: dias corrigidos por origem, aguardando aprovação, recusados e com erro no Secullum."""
	saida = {"colaborador": 0, "rh": 0, "aguardando": 0, "recusados": 0, "erro_secullum": 0}
	for c in correcoes:
		if not c:
			continue
		if c.get("situacao") == "Aprovado":
			saida[c.get("origem") or "rh"] += 1
		elif c.get("situacao") == "Aguardando aprovação":
			saida["aguardando"] += 1
		elif c.get("situacao") == "Recusado":
			saida["recusados"] += 1
		if c.get("secullum") == "Erro":
			saida["erro_secullum"] += 1
	return saida


def pode_cobrar(
	situacao: str | None,
	enviada_em: date | None,
	hoje: date,
	feriados: set[date],
	sem_resposta_marcado: bool = False,
	respondeu: bool = False,
	dias_uteis: int = DIAS_UTEIS_RESPOSTA,
) -> tuple[bool, str | None]:
	"""Cobrar pelo cartão (pedido do RH, 04/11/2026): manda a mesma mensagem do dia seguinte só se o dia ainda não
	foi avisado, ou se foi e ficou sem resposta além do prazo. (pode, motivo de não poder)."""
	dia = lambda d: f"{d:%d/%m}"  # noqa: E731
	if respondeu:
		return (
			False,
			"O colaborador já respondeu pelo WhatsApp do dia seguinte: aprove em Inconsistências → WhatsApp do dia seguinte.",
		)
	if situacao == "Aguardando envio manual":
		return (
			False,
			"O aviso do dia seguinte está na fila de conferência (Inconsistências → WhatsApp do dia seguinte).",
		)
	if situacao in ("Enviada", "Entregue", "Lida") and enviada_em:
		if sem_resposta_marcado or sem_resposta(enviada_em, hoje, feriados, dias_uteis):
			return True, None
		prazo = prazo_da_resposta(enviada_em, feriados, dias_uteis)
		return (
			False,
			f"WhatsApp do dia seguinte enviado em {dia(enviada_em)}: aguardando resposta até {dia(prazo)}.",
		)
	return True, None  # sem aviso, barrado, descartado ou com erro: pode mandar
