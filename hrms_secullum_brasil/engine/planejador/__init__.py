"""Planejador de escalas 5x2 (docs/PRD-planejador-5x2.md). Python puro: modelos, demanda, turnos candidatos,
restrições, custo, índice, heurística de reserva e avaliação das propostas. O otimizador (OR-Tools) fica em
`hrms_secullum_brasil/otimizacao/`; o Frappe só lê os dados e mostra. É **só simulação** (DP-9): nada aqui grava
escala."""
