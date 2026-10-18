import dataclasses

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.regras import (
	carregar_regras_cct,
	titulo_com_vigencia,
	validar_datas_vigencia,
	validar_edicao_em_periodo_fechado,
	validar_sem_sobreposicao,
)
from hrms_secullum_brasil.engine import defaults_legais
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.validacoes_cadastro import (
	avisos_tolerancia,
	erros_banco_horas,
	erros_faixas_he,
	erros_intrajornada,
	erros_tolerancia,
)


class RegraSindicalCCT(Document):
	def before_validate(self):
		descartar_hora_automatica(self, ("noturno_inicio", "noturno_fim"))
		# Valores escalares vêm do `default` do JSON; as faixas de HE vêm do engine.
		if self.is_new() and not self.faixas_hora_extra:
			for faixa in get_faixas_padrao():
				self.append("faixas_hora_extra", faixa)

	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company])
		validar_datas_vigencia(self)
		self.titulo = titulo_com_vigencia(self.sindicato, self.vigencia_inicio, self.vigencia_fim)
		self._validar_parametros()
		self._validar_cargos()
		self._validar_parametros_cargo()
		validar_sem_sobreposicao(
			self,
			carregar_regras_cct(
				{"company": self.company, "sindicato": self.sindicato, "name": ["!=", self.name]}
			),
			escopo=f"{self.company} / {self.sindicato}",
			cargos=self._cargos(),
		)
		self._avisar_riscos()

	def _cargos(self) -> frozenset[str]:
		return frozenset(c.designation for c in self.cargos)

	def _validar_cargos(self):
		if len(self._cargos()) != len(self.cargos):
			frappe.throw(_("Há cargos repetidos na tabela de cargos."))

	def _validar_parametros_cargo(self):
		"""AJ-01, AJ-04 e AJ-05: piso, adicional noturno e banco padrão por cargo."""
		erros = []
		vistos = set()
		escopo = self._cargos()
		minimo_noturno = max(
			flt(self.percentual_adicional_noturno), defaults_legais.PERCENTUAL_ADICIONAL_NOTURNO
		)
		for linha in self.parametros_cargo:
			if linha.designation in vistos:
				erros.append(_("Cargo {0} repetido nos parâmetros por cargo.").format(linha.designation))
			vistos.add(linha.designation)
			if escopo and linha.designation not in escopo:
				erros.append(_("Cargo {0} não está na lista de cargos desta CCT.").format(linha.designation))
			if (
				flt(linha.percentual_noturno) and flt(linha.percentual_noturno) < minimo_noturno
			):  # vazio ou 0 = o da CCT
				erros.append(
					_(
						"Adicional noturno do cargo {0} ({1}%) menor que o mínimo de {2}% (Art. 73 CLT e CCT)."
					).format(linha.designation, flt(linha.percentual_noturno), minimo_noturno)
				)
			if (
				flt(linha.valor_piso)
				and linha.tipo_piso == "Mensalista"
				and not flt(linha.carga_referencia_horas)
			):
				erros.append(
					_("Informe a carga semanal de referência do piso do cargo {0}.").format(linha.designation)
				)
		if erros:
			frappe.throw(erros, title=_("Parâmetros por cargo inválidos"), as_list=True)

	def _validar_parametros(self):
		faixas = [
			FaixaHE(f.tipo_dia, cint(f.de_min), cint(f.ate_min), flt(f.percentual))
			for f in self.faixas_hora_extra
		]
		erros = [
			*erros_tolerancia(cint(self.tolerancia_por_marcacao), cint(self.tolerancia_diaria)),
			*erros_faixas_he(faixas),
			*erros_intrajornada(
				jornada_sem_intervalo_ate=cint(self.jornada_sem_intervalo_ate),
				intervalo_curto=cint(self.intervalo_curto),
				jornada_intervalo_curto_ate=cint(self.jornada_intervalo_curto_ate),
				intervalo_minimo=cint(self.intervalo_minimo),
				intervalo_maximo=cint(self.intervalo_maximo),
				permite_reducao=bool(self.permite_reducao_intrajornada),
				intervalo_reduzido=cint(self.intervalo_reduzido),
			),
			*erros_banco_horas(self.banco_modalidade, cint(self.banco_prazo_meses)),
		]
		if flt(self.percentual_adicional_noturno) < defaults_legais.PERCENTUAL_ADICIONAL_NOTURNO:
			erros.append(
				_("Adicional noturno não pode ser menor que {0}% (Art. 73 CLT).").format(
					defaults_legais.PERCENTUAL_ADICIONAL_NOTURNO
				)
			)
		if erros:
			frappe.throw(erros, title=_("Regra Sindical CCT inválida"), as_list=True)

	def _avisar_riscos(self):
		"""Avisos não bloqueiam o salvamento (PRD, 5.2)."""
		for aviso in avisos_tolerancia(cint(self.tolerancia_por_marcacao), cint(self.tolerancia_diaria)):
			frappe.msgprint(aviso, title=_("Atenção: risco jurídico"), indicator="orange")


@frappe.whitelist()
def get_faixas_padrao() -> list[dict]:
	return [dataclasses.asdict(f) for f in defaults_legais.FAIXAS_HE_PADRAO]


@frappe.whitelist()
def get_prazo_maximo_banco() -> dict[str, int]:
	return defaults_legais.PRAZO_MAXIMO_BANCO_MESES
