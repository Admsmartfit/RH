"""Termo de ocorrências de ponto (docs/PRD-termo-ocorrencias.md, TO-04): o que entra no termo, a regularização
proposta de cada dia (a mesma correção que o cartão sugere), o resumo do WhatsApp, os prazos em dias úteis (DO-7) e a
reincidência (DO-11). Puro: as telas e os jobs só gravam e enviam.

Horários em minutos do dia de trabalho, como em engine/cartao_edicao.py.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import pairwise

from hrms_secullum_brasil.engine.cartao_edicao import DESCONSIDERAR, INCLUIR, ORIGINAL, Batida, hhmm
from hrms_secullum_brasil.engine.sugestoes import ContextoDia, intervalo_exigido, orientar

# nome que o colaborador entende (WhatsApp, e-mail e PDF), na ordem em que o dia é regularizado
NOMES = {
	"marcacao_duplicada": "Batida repetida",
	"marcacao_impar": "Batida faltando (entrada ou saída)",
	"intrajornada": "Intervalo não registrado ou menor que o mínimo",
	"falta": "Falta (dia sem batida)",
	"atraso": "Atraso ou saída antecipada",
	"he_acima_limite": "Hora extra acima do limite do dia",
	# sem "interjornada" (RH, 09/11/2026): pode ser da escala ou de ter chegado antes; não vai ao termo
	"intervalo_superior_2h": "Intervalo maior que 2 h",
	"intervalo_fora_de_hora": "Intervalo no começo ou no fim do expediente",
	"aula_nao_registrada": "Aula sem batida",
	"excesso_jornada_estagio": "Estágio acima da jornada do TCE",
	"intervalo_nao_marcado_horista": "Excedeu o horário de trabalho de 4 h sem marcar o intervalo",
}
TIPOS_DO_TERMO = tuple(NOMES)  # uma linha a confirmar por dia
# no termo, mas nunca cobrados do colaborador pelo WhatsApp (o RH trata; RH, 09/11/2026)
SO_NO_TERMO = frozenset({"intervalo_nao_marcado_horista"})
# da semana ou do mês, sem um dia a corrigir: só como informação no texto (seção 6)
INFORMATIVOS = {
	"sete_dias_seguidos": "7 dias seguidos de trabalho",
	"descanso_semanal": "Descanso semanal menor que 35 h",
	"folgas_semanais": "Semana com menos folgas do que o regime exige",
	"domingos_sem_folga": "Domingos seguidos sem folga",
	"excesso_jornada_horista": "Mais de 4 h sem intervalo além do limite do mês",
}
CIENTE = "Sem regularização a fazer no ponto"

DE_ACORDO = "De acordo"
ALTERADO = "Alterado"
NAO_RECONHECE = "Não reconhece"
JA_RESOLVIDO = "Já resolvido"
PERIODO_FECHADO = "Período fechado"
RESPOSTAS = (DE_ACORDO, ALTERADO, NAO_RECONHECE)

PRAZO_DIAS_UTEIS = 3
AVISO_RH_DIAS_UTEIS = 10
REINCIDENCIA_LIMITE = 3
REINCIDENCIA_JANELA_DIAS = 90

# textos do termo (RH, 09/11/2026): fato neutro, sem citar lei e sem dizer o efeito na folha
APROVADA, AGUARDANDO_RH, RECUSADA = "Aprovado", "Aguardando aprovação", "Recusado"
# tipos em que o "Horário correto" fica aberto (o resto é só registro: a coluna sai hachurada)
# o intervalo também (RH, 09/11/2026): quem não respondeu pelo link escreve o horário do intervalo no termo
COM_HORARIO_CORRETO = frozenset({"marcacao_impar", "intrajornada", "falta", "aula_nao_registrada"})
ESCREVA_O_INTERVALO = "Se fez o intervalo, escreva o horário."


@dataclass(frozen=True)
class Proposta:
	texto: str
	# o dia inteiro depois da correção; None = ciente, sem mudar o ponto
	horarios: tuple[int, ...] | None = None
	intervalo: tuple[int, int] | None = None  # o intervalo do termo incluído (entra com o motivo do termo)
	sem_horario: bool = False  # "Horário correto" hachurado: a linha é só registro


@dataclass(frozen=True)
class CorrecaoColaborador:
	"""O que o colaborador mandou pelo link do WhatsApp para o dia (Resposta WhatsApp Ponto)."""

	enviada_em: date
	situacao: str  # Aprovado, Aguardando aprovação, Recusado, Para o RH
	antes: tuple[str, ...] = ()
	informados: tuple[str, ...] = ()
	nao_reconhece: bool = False
	explicacao: str = ""
	decidida_em: date | None = None


@dataclass(frozen=True)
class DiaTermo:
	data: date
	ocorrencias: tuple[tuple[str, str], ...]  # (nome da Inconsistencia de Ponto, tipo) em aberto
	contexto: ContextoDia
	correcao: CorrecaoColaborador | None = None
	tipos_do_dia: tuple[str, ...] = ()  # o que o dia teve (para o quadro), mesmo já resolvido pela correção


@dataclass(frozen=True)
class ItemTermo:
	data: date
	tipos: tuple[str, ...]
	inconsistencias: tuple[str, ...]
	marcacoes: tuple[int, ...]
	proposta: Proposta


def entra_no_termo(tipo: str) -> bool:
	return tipo in NOMES


def duracao(minutos: int) -> str:
	"""60 → "1 h", 30 → "30 min", 150 → "2h30"."""
	minutos = int(minutos)
	if minutos < 60:
		return f"{minutos} min"
	if minutos % 60 == 0:
		return f"{minutos // 60} h"
	return f"{minutos // 60}h{minutos % 60:02d}"


def _pares(minutos: Sequence[int]) -> list[tuple[int, int]]:
	return [(minutos[i], minutos[i + 1]) for i in range(0, len(minutos) - 1, 2)]


def _pausas(minutos: Sequence[int]) -> list[tuple[int, int]]:
	pares = _pares(minutos)
	return [(a[1], b[0]) for a, b in pairwise(pares) if b[0] > a[1]]


def _trabalhado(minutos: Sequence[int]) -> int:
	return sum(s - e for e, s in _pares(minutos))


def _batida_que_falta(minutos: Sequence[int], prevista: int | None) -> str:
	if prevista is None:
		return "Não houve registro de uma das batidas (entrada ou saída). Escreva o horário correto."
	posicao = sorted([*minutos, prevista]).index(prevista)
	return f"Não houve registro da {'entrada' if posicao % 2 == 0 else 'saída'}. Escreva o horário correto."


def _intervalo(minutos: Sequence[int], contexto: ContextoDia) -> str:
	trabalhado = _trabalhado(minutos)
	exigido = intervalo_exigido(trabalhado, contexto) or contexto.intervalo_curto
	pausas = _pausas(minutos)
	if not pausas:
		return (
			f"Jornada de {duracao(trabalhado)} sem o registro do intervalo mínimo de {duracao(exigido)}. "
			+ ESCREVA_O_INTERVALO
		)
	maior = max(fim - inicio for inicio, fim in pausas)
	return (
		f"Intervalo registrado de {duracao(maior)}, menor que o mínimo de {duracao(exigido)}. "
		+ ESCREVA_O_INTERVALO
	)


def _atraso(minutos: Sequence[int], contexto: ContextoDia) -> str:
	if not minutos or not contexto.previsto:
		return "Entrada depois ou saída antes do horário previsto."
	inicio, fim = contexto.previsto[0][0], contexto.previsto[-1][1]
	partes = []
	if minutos[0] > inicio:
		partes.append(
			f"Entrada às {hhmm(minutos[0])}, {duracao(minutos[0] - inicio)} depois do horário previsto ({hhmm(inicio)})"
		)
	if len(minutos) % 2 == 0 and minutos[-1] < fim:
		partes.append(
			f"Saída às {hhmm(minutos[-1])}, {duracao(fim - minutos[-1])} antes do horário previsto ({hhmm(fim)})"
		)
	if not partes:
		return "Entrada depois ou saída antes do horário previsto."
	return "; ".join([partes[0], *(p[0].lower() + p[1:] for p in partes[1:])]) + "."


def _hora_extra(minutos: Sequence[int], contexto: ContextoDia) -> str:
	trabalhado = _trabalhado(minutos)
	previsto = sum(f - i for i, f in contexto.previsto)
	return (
		f"Jornada de {duracao(trabalhado)}, com {duracao(max(trabalhado - previsto, 0))} além do previsto, acima do "
		f"limite de {duracao(contexto.limite_he_diaria)} extras por dia."
	)


def _intervalo_longo(minutos: Sequence[int]) -> str:
	pausas = _pausas(minutos)
	maior = max((fim - inicio for inicio, fim in pausas), default=0)
	return f"Intervalo de {duracao(maior)}, maior que o máximo de 2 h."


def _intervalo_fora(minutos: Sequence[int]) -> str:
	pausas = _pausas(minutos)
	if not pausas:
		return "Intervalo registrado no começo ou no fim do expediente; o descanso deve ser feito no meio da jornada."
	inicio, fim = min(pausas, key=lambda p: min(p[0] - minutos[0], minutos[-1] - p[1]))
	onde = "no começo" if inicio - minutos[0] < minutos[-1] - fim else "no fim"
	return (
		f"Intervalo registrado {onde} do expediente ({hhmm(inicio)} às {hhmm(fim)}); o descanso deve ser feito no meio "
		"da jornada."
	)


def _texto_do_tipo(tipo: str, minutos: Sequence[int], contexto: ContextoDia) -> str:
	if tipo == "falta":
		return "Não houve registro de ponto neste dia de trabalho previsto."
	if tipo == "intrajornada":
		return _intervalo(minutos, contexto)
	if tipo == "atraso":
		return _atraso(minutos, contexto)
	if tipo == "he_acima_limite":
		return _hora_extra(minutos, contexto)
	if tipo == "intervalo_superior_2h":
		return _intervalo_longo(minutos)
	if tipo == "intervalo_fora_de_hora":
		return _intervalo_fora(minutos)
	if tipo == "aula_nao_registrada":
		return "Aula prevista na grade sem registro de ponto."
	if tipo == "excesso_jornada_estagio":
		return f"Jornada de {duracao(_trabalhado(minutos))}, acima do limite diário do termo de estágio."
	if tipo == "intervalo_nao_marcado_horista":
		jornada = minutos[-1] - minutos[0] if minutos else 0
		return f"Jornada de {duracao(jornada)}, acima de 4 h, sem o registro do intervalo."
	return NOMES.get(tipo, CIENTE) + "."


def propor_dia(tipos: Iterable[str], contexto: ContextoDia) -> Proposta:
	"""A regularização do dia: tira a batida repetida (o ponto muda); o resto é o fato do dia, para ciência. Só a
	batida faltando, a falta e a aula deixam o "Horário correto" aberto (sem sugerir horário)."""
	minutos = sorted(b.minuto for b in contexto.batidas)
	partes = []
	ordem = sorted(set(tipos), key=lambda t: TIPOS_DO_TERMO.index(t) if t in NOMES else len(NOMES))
	for tipo in ordem:
		if tipo == "marcacao_duplicada":
			sugestoes = orientar(tipo, _com_batidas(contexto, minutos)).sugestoes
			repetidas = [s.minuto for s in sugestoes if s.acao == DESCONSIDERAR and s.minuto is not None]
			if repetidas:
				for m in repetidas:
					anterior = max((x for x in minutos if x <= m and x != m), default=m)
					partes.append(
						f"Batida {hhmm(m)} registrada em duplicidade ({duracao(m - anterior)} depois de "
						f"{hhmm(anterior)}); a repetida é desconsiderada."
					)
					minutos.remove(m)
				continue
		if tipo == "marcacao_impar":
			sugestoes = orientar(tipo, _com_batidas(contexto, minutos)).sugestoes
			prevista = next((s.minuto for s in sugestoes if s.acao == INCLUIR and s.minuto is not None), None)
			partes.append(_batida_que_falta(minutos, prevista))
			continue
		partes.append(_texto_do_tipo(tipo, minutos, contexto))
	originais = tuple(sorted(b.minuto for b in contexto.batidas))
	horarios = tuple(minutos)
	return Proposta(
		" ".join(partes) or CIENTE,
		horarios if horarios != originais else None,
		None,
		sem_horario=not (set(ordem) & COM_HORARIO_CORRETO),
	)


def _horas(lista: Sequence[str]) -> str:
	return ", ".join(lista[:-1]) + f" e {lista[-1]}" if len(lista) > 1 else (lista[0] if lista else "")


def texto_da_correcao(c: CorrecaoColaborador) -> str:
	"""O que o colaborador já fez pelo link: aparece no termo como registro (RH, 09/11/2026)."""
	quando = c.enviada_em.strftime("%d/%m")
	incluidos = [h for h in c.informados if h not in c.antes]
	retirados = [h for h in c.antes if h not in c.informados]
	if c.nao_reconhece:
		texto = f"O(a) empregado(a) informou pelo link, em {quando}, que não reconhece os registros do dia"
	elif incluidos or retirados:
		partes = []
		if incluidos:
			partes.append(
				f"{'Horários' if len(incluidos) > 1 else 'Horário'} {_horas(incluidos)} informado"
				f"{'s' if len(incluidos) > 1 else ''}"
			)
		if retirados:
			partes.append(f"{_horas(retirados)} retirado{'s' if len(retirados) > 1 else ''}")
		texto = " e ".join(partes) + f" pelo(a) empregado(a) pelo link em {quando}"
	else:
		explicacao = (c.explicacao or "").strip()
		texto = f"Explicação enviada pelo(a) empregado(a) pelo link em {quando}" + (
			f": “{explicacao}”" if explicacao else ""
		)
	decidida = f" em {c.decidida_em:%d/%m}" if c.decidida_em else ""
	if c.situacao == APROVADA:
		return f"{texto}; aprovado pelo RH{decidida}."
	if c.situacao == RECUSADA:
		return f"{texto}; não aprovado pelo RH{decidida}."
	return f"{texto}; aguardando aprovação do RH."


def _com_batidas(contexto: ContextoDia, minutos: Sequence[int]) -> ContextoDia:
	antigas = {b.minuto: b for b in contexto.batidas}
	return replace(
		contexto,
		batidas=tuple(antigas.get(m) or Batida(m, ORIGINAL, f"proposta-{m}") for m in sorted(minutos)),
	)


def montar_itens(dias: Iterable[DiaTermo]) -> list[ItemTermo]:
	"""Uma linha por dia com as ocorrências que cabem no termo; o resto fica de fora (seção 6). O dia que o colaborador
	corrigiu pelo link entra com o registro do que ele fez: aprovado, a correção e o que ainda ficou aberto;
	aguardando o RH, só o registro (as pendências do dia ficam com o RH, a assinatura não as toca)."""
	itens = []
	for dia in sorted(dias, key=lambda d: d.data):
		do_termo = [(nome, tipo) for nome, tipo in dia.ocorrencias if entra_no_termo(tipo)]
		marcacoes = tuple(sorted(b.minuto for b in dia.contexto.batidas))
		c = dia.correcao
		if c and c.situacao != RECUSADA:
			abertas = [] if c.situacao != APROVADA else do_termo
			tipos = tuple(
				sorted(
					{t for t in dia.tipos_do_dia if entra_no_termo(t)} | {t for _, t in abertas},
					key=TIPOS_DO_TERMO.index,
				)
			)
			resto = propor_dia([t for _, t in abertas], dia.contexto) if abertas else None
			texto = texto_da_correcao(c) + (f" {resto.texto}" if resto else "")
			itens.append(
				ItemTermo(
					data=dia.data,
					tipos=tipos,
					inconsistencias=tuple(nome for nome, _ in abertas),
					marcacoes=marcacoes,
					proposta=Proposta(
						texto,
						resto.horarios if resto else None,
						None,
						sem_horario=resto.sem_horario if resto else True,
					),
				)
			)
			continue
		if not do_termo:
			continue
		tipos = tuple(sorted({t for _, t in do_termo}, key=TIPOS_DO_TERMO.index))
		proposta = propor_dia(tipos, dia.contexto)
		if c:  # recusada: o registro do que ele mandou vem antes do fato do dia
			proposta = replace(proposta, texto=f"{texto_da_correcao(c)} {proposta.texto}")
		itens.append(
			ItemTermo(
				data=dia.data,
				tipos=tipos,
				inconsistencias=tuple(nome for nome, _ in do_termo),
				marcacoes=marcacoes,
				proposta=proposta,
			)
		)
	return itens


def data_curta(data: date) -> str:
	return data.strftime("%d/%m")


def resumo_ocorrencias(
	itens: Sequence[ItemTermo], informativos: Iterable[tuple[str, date | None]] = ()
) -> str:
	"""As ocorrências por tipo com os dias ("• Batida faltando (entrada ou saída): 02/10, 05/10"), para o WhatsApp e o
	e-mail. As informativas entram no fim, sem dias a confirmar."""
	por_tipo: dict[str, list[date]] = {}
	for item in itens:
		for tipo in item.tipos:
			por_tipo.setdefault(tipo, []).append(item.data)
	linhas = [
		f"• {NOMES[tipo]}: {', '.join(data_curta(d) for d in sorted(set(datas)))}"
		for tipo, datas in sorted(por_tipo.items(), key=lambda x: TIPOS_DO_TERMO.index(x[0]))
	]
	vistos = []
	for tipo, _data in informativos:
		if tipo in INFORMATIVOS and tipo not in vistos:
			vistos.append(tipo)
	linhas += [f"• {INFORMATIVOS[tipo]}" for tipo in vistos]
	return "\n".join(linhas)


def texto_marcacoes(minutos: Sequence[int]) -> str:
	return " ".join(hhmm(m) for m in minutos) or "sem batida"


# ------------------------------------------------------------------ prazos em dias úteis (DO-7)


def dia_util(data: date, feriados: set[date]) -> bool:
	return data.weekday() < 5 and data not in feriados


def dias_uteis_entre(inicio: date, fim: date, feriados: set[date]) -> int:
	"""Dias úteis depois de `inicio` até `fim` (inclusive). A emissão não conta."""
	total, dia = 0, inicio + timedelta(days=1)
	while dia <= fim:
		total += dia_util(dia, feriados)
		dia += timedelta(days=1)
	return total


def somar_dias_uteis(inicio: date, dias: int, feriados: set[date]) -> date:
	"""O n-ésimo dia útil depois de `inicio` (o prazo final para assinar)."""
	dia = inicio
	while dias > 0:
		dia += timedelta(days=1)
		dias -= dia_util(dia, feriados)
	return dia


GERENTE = "gerente"
RH = "rh"


def avisos_do_dia(
	emissao: date,
	hoje: date,
	feriados: set[date],
	rh_avisado: bool = False,
	prazo: int = PRAZO_DIAS_UTEIS,
	aviso_rh: int = AVISO_RH_DIAS_UTEIS,
) -> tuple[str, ...]:
	"""Quem cobrar hoje: o gerente todo dia útil depois do prazo; o RH uma vez, no dia útil `aviso_rh` (ou no
	primeiro dia útil depois, se o job não rodou). Fim de semana e feriado: ninguém."""
	if not dia_util(hoje, feriados):
		return ()
	passados = dias_uteis_entre(emissao, hoje, feriados)
	avisos = []
	if passados > prazo:
		avisos.append(GERENTE)
	if passados >= aviso_rh and not rh_avisado:
		avisos.append(RH)
	return tuple(avisos)


# ------------------------------------------------------------------ reincidência (DO-11)


def reincidente(
	emissoes: Iterable[date],
	hoje: date,
	limite: int = REINCIDENCIA_LIMITE,
	janela_dias: int = REINCIDENCIA_JANELA_DIAS,
) -> bool:
	"""Chegou ao limite de termos na janela (contando o de hoje, se já está na lista)."""
	if limite <= 0:
		return False
	desde = hoje - timedelta(days=janela_dias)
	return sum(1 for d in emissoes if desde < d <= hoje) >= limite


# ------------------------------------------------------------------ relatório (TO-12)

CONFORME = "Assinado (conforme)"
COM_ALTERACAO = "Assinado (com alteração)"
RECUSADO = "Recusado"
CANCELADO = "Cancelado"
AGUARDANDO = "Aguardando assinatura"


@dataclass(frozen=True)
class TermoResumo:
	employee: str
	status: str
	emitido: date
	confirmado: date | None = None
	tipos: tuple[str, ...] = ()


def estatisticas(termos: Iterable[TermoResumo]) -> dict[str, dict]:
	"""Por colaborador: quantos termos em cada situação, dias até a assinatura (média, corridos), taxa de recusa
	(recusados / respondidos) e os tipos de ocorrência mais frequentes."""
	saida: dict[str, dict] = {}
	for t in termos:
		linha = saida.setdefault(
			t.employee,
			{
				"emitidos": 0,
				"conforme": 0,
				"com_alteracao": 0,
				"recusados": 0,
				"cancelados": 0,
				"aguardando": 0,
				"_dias": [],
				"_tipos": {},
			},
		)
		linha["emitidos"] += 1
		chave = {
			CONFORME: "conforme",
			COM_ALTERACAO: "com_alteracao",
			RECUSADO: "recusados",
			CANCELADO: "cancelados",
		}.get(t.status, "aguardando")
		linha[chave] += 1
		if t.status in (CONFORME, COM_ALTERACAO) and t.confirmado:
			linha["_dias"].append((t.confirmado - t.emitido).days)
		for tipo in t.tipos:
			linha["_tipos"][tipo] = linha["_tipos"].get(tipo, 0) + 1
	for linha in saida.values():
		dias = linha.pop("_dias")
		tipos = linha.pop("_tipos")
		respondidos = linha["conforme"] + linha["com_alteracao"] + linha["recusados"]
		linha["dias_medio"] = round(sum(dias) / len(dias), 1) if dias else None
		linha["taxa_recusa"] = round(100 * linha["recusados"] / respondidos, 1) if respondidos else None
		linha["tipos"] = ", ".join(
			f"{NOMES.get(tipo, tipo)} ({n})"
			for tipo, n in sorted(tipos.items(), key=lambda x: (-x[1], x[0]))[:3]
		)
	return saida
