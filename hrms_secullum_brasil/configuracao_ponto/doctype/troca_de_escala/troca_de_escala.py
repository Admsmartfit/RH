"""Troca de Escala (AJ-09): linhas livres por colaborador e dia — troca entre dois, cobertura por outro
colaborador ou folga sem cobertura.

Aprovar (submit, RH ou o gestor da equipe) muda a Escala do Mês de cada envolvido e reapura os dias; cancelar
desfaz. Interjornada, intervalo, 7 dias seguidos e domingos geram avisos, sem impedir a troca.
"""

import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, now_datetime

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.configuracao_ponto.escala import (
	CAMPOS_HORARIO,
	dia_para_conferencia,
	horarios_do_dia,
	obter_ou_criar_escala,
	periodos_da_linha,
)
from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.escala import (
	FOLGA_COMPENSADA,
	REPOUSO,
	TRABALHO,
	DiaEscala,
	avisos_escala,
	limite_domingos,
	repouso_padrao,
)

CAMPOS_COPIADOS = ["situacao", *CAMPOS_HORARIO, "troca"]


class TrocadeEscala(Document):
	def before_validate(self):
		for linha in self.dias:
			descartar_hora_automatica(linha, CAMPOS_HORARIO)

	def validate(self):
		erros = []
		vistos = set()
		for linha in self.dias:
			dia = getdate(linha.data)
			chave = (linha.employee, dia)
			if chave in vistos:
				erros.append(_("{0} aparece duas vezes em {1}.").format(linha.employee, formatdate(dia)))
			vistos.add(chave)
			if periodo_fechado(linha.employee, dia):
				erros.append(_("O ponto de {0} está fechado em {1}.").format(linha.employee, formatdate(dia)))
			if linha.situacao == TRABALHO:
				self._preencher_horario(linha, erros)
			else:
				linha.cobrindo = None
				for campo in CAMPOS_HORARIO:
					linha.set(campo, None)
		if erros:
			frappe.throw(erros, title=_("Troca de escala inválida"), as_list=True)
		if self.docstatus == 0:
			self._ajustar_repousos()
		self.avisos = "\n".join(self._avisos()) or None
		if self.avisos:
			frappe.msgprint(
				self.avisos.replace("\n", "<br>"), title=_("Atenção (não impede a troca)"), indicator="orange"
			)

	def before_submit(self):
		usuario = frappe.session.user
		papeis = set(frappe.get_roles(usuario))
		if not papeis & {"System Manager", "RH Ponto"} and usuario != "Administrator":
			visiveis = set(employees_visiveis(usuario) or [])
			fora = sorted({linha.employee for linha in self.dias} - visiveis)
			if fora:
				frappe.throw(
					_("Só o RH aprova trocas com colaboradores fora da sua equipe: {0}.").format(
						", ".join(fora)
					)
				)
		self.aprovado_por = usuario
		self.aprovado_em = now_datetime()

	def on_submit(self):
		for escala, linhas in self._por_escala():
			for linha in linhas:
				dia = _linha_da_escala(escala, getdate(linha.data))
				linha.db_set("anterior", json.dumps({c: str(dia.get(c) or "") for c in CAMPOS_COPIADOS}))
				dia.situacao = linha.situacao
				for campo in CAMPOS_HORARIO:
					dia.set(campo, linha.get(campo) if linha.situacao == TRABALHO else None)
				dia.troca = self.name
			escala.flags.ignore_permissions = True
			escala.save()

	def before_cancel(self):
		for linha in self.dias:
			if periodo_fechado(linha.employee, linha.data):
				frappe.throw(
					_("O ponto de {0} está fechado em {1}.").format(linha.employee, formatdate(linha.data))
				)

	def on_cancel(self):
		for escala, linhas in self._por_escala():
			for linha in reversed(linhas):
				anterior = json.loads(linha.anterior or "{}")
				if not anterior:
					continue
				dia = _linha_da_escala(escala, getdate(linha.data))
				for campo in CAMPOS_COPIADOS:
					dia.set(campo, anterior.get(campo) or None)
			escala.flags.ignore_permissions = True
			escala.save()

	# ------------------------------------------------------------------

	def _preencher_horario(self, linha, erros):
		if periodos_da_linha(linha):
			return
		origem = horarios_do_dia(linha.cobrindo, getdate(linha.data)) if linha.cobrindo else None
		origem = origem or horarios_do_dia(linha.employee, getdate(linha.data))
		if not origem:
			erros.append(
				_("Informe o horário de {0} em {1} (ninguém tem horário nesse dia para copiar).").format(
					linha.employee, formatdate(linha.data)
				)
			)
			return
		for campo in CAMPOS_HORARIO:
			linha.set(campo, origem.get(campo))

	def _ajustar_repousos(self):
		"""Semana que perdeu o repouso com a troca (ex.: o domingo de folga virou trabalho): inclui uma linha
		marcando outra folga da semana como repouso semanal (o domingo, se for folga; senão a primeira)."""
		trocados = {(linha.employee, getdate(linha.data)): linha for linha in self.dias}
		semanas = {(employee, dia - timedelta(days=dia.weekday())) for employee, dia in trocados}
		for employee, segunda in sorted(semanas):
			situacoes = {}
			for i in range(7):
				dia = segunda + timedelta(days=i)
				if (employee, dia) in trocados:
					situacoes[dia] = trocados[(employee, dia)].situacao
					continue
				perfil = get_perfil_vigente(employee, dia)
				if perfil:
					situacoes[dia] = dia_para_conferencia(employee, dia, perfil).situacao
			if REPOUSO in situacoes.values():
				continue
			folgas = [dia for dia, situacao in situacoes.items() if situacao == FOLGA_COMPENSADA]
			escolhido = repouso_padrao(folgas)
			if not escolhido:
				continue
			if (employee, escolhido) in trocados:
				trocados[(employee, escolhido)].situacao = REPOUSO
			else:
				self.append("dias", {"employee": employee, "data": escolhido, "situacao": REPOUSO})
				frappe.msgprint(
					_(
						"{0}: {1} passou a ser o repouso semanal da semana (ajuste automático da troca)."
					).format(employee, formatdate(escolhido)),
					indicator="blue",
				)

	def _por_escala(self):
		grupos = defaultdict(list)
		for linha in self.dias:
			dia = getdate(linha.data)
			grupos[(linha.employee, dia.year, dia.month)].append(linha)
		for (employee, ano, mes), linhas in sorted(grupos.items()):
			yield obter_ou_criar_escala(employee, ano, mes), linhas

	def _avisos(self) -> list[str]:
		"""Simula a escala de cada envolvido com a troca aplicada e confere descansos e domingos."""
		avisos = []
		por_colaborador = defaultdict(dict)
		for linha in self.dias:
			por_colaborador[linha.employee][getdate(linha.data)] = DiaEscala(
				getdate(linha.data), linha.situacao, periodos_da_linha(linha)
			)
		for employee, trocados in por_colaborador.items():
			inicio, fim = min(trocados), max(trocados)
			dias = []
			atual = inicio - timedelta(days=14)
			while atual <= fim + timedelta(days=7):
				if atual in trocados:
					dias.append(trocados[atual])
				else:
					perfil = get_perfil_vigente(employee, atual)
					if perfil:
						dias.append(dia_para_conferencia(employee, atual, perfil))
				atual += timedelta(days=1)
			emp = frappe.get_cached_doc("Employee", employee)
			empresa = frappe.db.get_value(
				"Company", emp.company, ["domingos_seguidos_mulher", "domingos_seguidos_homem"], as_dict=True
			)
			limite = limite_domingos(
				emp.gender,
				cint(empresa.domingos_seguidos_mulher) or d.DOMINGOS_SEGUIDOS_MULHER,
				cint(empresa.domingos_seguidos_homem) or d.DOMINGOS_SEGUIDOS_HOMEM,
			)
			nome = emp.employee_name or employee
			avisos += [
				f"{nome} — {a}"
				for a in avisos_escala(dias, limite_domingos=limite, conferir_a_partir_de=inicio)
			]
		return avisos


def _linha_da_escala(escala, dia):
	linha = next((x for x in escala.dias if getdate(x.data) == dia), None)
	if linha is None:
		linha = escala.append("dias", {"data": dia, "situacao": TRABALHO})
	return linha
