# Etapa 0 — Cadastros da ES Fitness (para o RH conferir)

Etapa 0 do `docs/PRD-alteracoes.md` (C-01, C-03, C-04, C-07). A TI já aplicou estes cadastros com o script
`utils/config_es_fitness.py`. Confira cada item nas telas e complete o que está marcado como **RH completa**.

## C-07 — Empresa e feriados de Vila Velha

**Empresa → ES Fitness Ltda**

- [ ] CNPJ (campo "Tax ID"): 23.620.822/0002-51.
- [ ] Aba Ponto: UF **ES**, município **Vila Velha**, "Feriados do ponto" = **Feriados 2026-2027 - Vila Velha**.

**Holiday List → Feriados 2026-2027 - Vila Velha**

- Já cadastrados: os feriados nacionais de 2026 e 2027 e o estadual N. Sra. da Penha (13/04/2026 e 05/04/2027).
- [ ] **RH completa:** inclua os feriados **municipais de Vila Velha** de 2026 e 2027, conforme a lei municipal
      (botão "Add Row" na tabela de feriados; preencha data e descrição).
- O 08/09 (N. Sra. da Vitória) é feriado **só de Vitória**: não inclua.
- O 27/07 (Dia da Liberdade, CCT cl. 34ª) **não é folga**: não inclua.
- Pontos facultativos (Carnaval, Corpus Christi): só inclua se a empresa der folga.

## C-01 e C-04 — Regra Sindical CCT

**Regra Sindical CCT → SENALBA-ES × SINDELIVRE-ES 2026/2027** (empresa ES Fitness Ltda)

- [ ] Vigência: 01/05/2026 a 30/04/2027. A partir de 01/05/2027, cadastre a nova CCT como um novo registro.
- [ ] Adicional noturno: **25%** (cl. 12ª).
- [ ] Banco de horas: **Anual**, prazo de **12 meses** (cl. 22ª).
- [ ] "CCT permite reduzir o intervalo": **desmarcado** (C-04; a CCT não tem cláusula de redução).
- [ ] Cargos: em branco (vale para todos os cargos da empresa).

Duas regras da CCT ainda não são opções da CCT no programa:

- **Intervalo maior que 2h** (cl. 23ª): é liberado no **Perfil de Jornada**. Marque "Permite intervalo
  estendido" nos perfis com jornada fragmentada (ex.: instrutor 06–10h e 17–21h).
- **Banco de horas na rescisão pago a 50%** (cl. 22ª): hoje o saldo é pago com o percentual da formação de cada
  crédito. Isso precisa de uma mudança no programa, que ainda não está no PRD de alterações.

A academia de exemplo (Academia Exemplo Vitória) recebeu as mesmas correções.

## C-03 — Vale-refeição por dia trabalhado

**Regra de Benefício → VR da ES Fitness Ltda**

- [ ] **RH completa:** se não existir, crie com: tipo **VR**, modo **Proporcional**, **valor por dia** (o valor
      atual da empresa), vigência a partir de 01/05/2026.
- [ ] Ausências que tiram o dia (resposta de 15/10/2026): marque **falta**, **atestado**, **afastamento**,
      **férias** e **abono**.

Se preferir, a TI cria a regra pelo script, informando o valor do dia:

```bash
bench --site <site> execute hrms_secullum_brasil.utils.config_es_fitness.aplicar --kwargs "{'valor_dia_vr': 25}"
```

## Antes de seguir

- [ ] Colaboradores da ES Fitness com a empresa **ES Fitness Ltda** e a CCT acima (aba Ponto do colaborador).
- [ ] Se algum colaborador já foi apurado com a CCT antiga, use **Reapurar período** no Fechamento de Ponto em
      rascunho.
