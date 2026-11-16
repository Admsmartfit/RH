"""Escreve o endereço de cada caixa clicável dentro do rótulo e gera a página HTML do diagrama."""

import re
import sys
from pathlib import Path

md = Path(sys.argv[1])
texto = md.read_text(encoding="utf-8")
cliques = dict(re.findall(r'^\s*click (\w+) "https://ponto\.ricardo\.home\.nom\.br([^"]*)"', texto, re.M))


def com_link(m):
	no, abre, rotulo, fecha = m.group(1), m.group(2), m.group(3), m.group(4)
	caminho = cliques.get(no)
	if not caminho or "🔗" in rotulo:
		return m.group(0)
	return f'{no}{abre}"{rotulo}<br/>🔗 {caminho or "/"}"{fecha}'


texto = re.sub(r'(?<=\s)(\w+)(\[|\(\[)"([^"]*)"(\]\)|\])', com_link, texto)
md.write_text(texto, encoding="utf-8", newline="\n")

bloco = re.search(r"```mermaid\n(.*?)```", texto, re.S).group(1)
tabela = texto.split("## Links por etapa", 1)[1]
linhas = []
for linha in tabela.splitlines():
	m = re.match(r"\| (.+?) \| (.+?) \| \[(.+?)\]\((.+?)\) \|", linha)
	if m:
		linhas.append(
			f'<tr><td>{m[1]}</td><td>{m[2]}</td><td><a href="{m[4]}" target="_blank" rel="noopener">{m[3]}</a></td></tr>'
		)
html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ciclo do colaborador</title>
<!-- gerado a partir de docs/ciclo_colaborador.md (a fonte); não edite aqui -->
<style>
  /* visual escuro (pedido do RH): fundo pontilhado, caixas escuras, texto branco, etapas com borda colorida */
  :root {{ --fundo:#0b0f1a; --texto:#f1f5f9; --suave:#cbd5e1; --borda:#334155; --link:#93c5fd; }}
  body {{ margin:0; padding:16px; background:var(--fundo); color:var(--texto); font:14px/1.5 system-ui, sans-serif; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  h2 {{ font-size:16px; }}
  p {{ color:var(--suave); margin:0 0 12px; }}
  .diagrama {{ overflow:auto; border:1px solid var(--borda); border-radius:8px; padding:12px;
    background-color:var(--fundo);
    background-image:radial-gradient(circle, #2a3142 1px, transparent 1.2px); background-size:28px 28px; }}
  .diagrama svg {{ max-width:none !important; }}
  table {{ border-collapse:collapse; width:100%; margin-top:16px; }}
  td, th {{ border-top:1px solid var(--borda); padding:4px 8px; text-align:left; vertical-align:top; }}
  a {{ color:var(--link); }}
  .diagrama .flowchart-link {{ stroke-width:1.5px !important; }}
  .diagrama .nodeLabel, .diagrama .edgeLabel {{ color:#ffffff !important; font-weight:600; }}
  .diagrama .cluster-label .nodeLabel {{ font-weight:600; font-size:15px; color:#f1f5f9 !important; }}
  .diagrama .edgeLabel {{ background:var(--fundo) !important; padding:0 3px; }}
  .diagrama .node.clickable {{ cursor:pointer; }}
</style>
</head>
<body>
<h1>Ciclo do colaborador no sistema</h1>
<p>Do cadastro no Secullum ao desligamento. Caixas com borda azul abrem a tela (🔗). Role para os lados para ver tudo.</p>
<div class="diagrama"><pre class="mermaid">
{bloco}</pre></div>
<h2>Links por etapa</h2>
<table><thead><tr><th>Etapa</th><th>Tela</th><th>Endereço</th></tr></thead><tbody>
{chr(10).join(linhas)}
</tbody></table>
<p style="margin-top:12px">As páginas /ponto/whatsapp, /ponto/resposta, /ponto/termo, /ponto/assinar, /ponto/cobertura e /ponto/talentos
só abrem com o link pessoal (token) enviado à pessoa.</p>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
  // as cores valem pelo %%{{init}}%% do diagrama (docs/ciclo_colaborador.md); aqui só o padrão
  mermaid.initialize({{
    startOnLoad: true,
    securityLevel: "loose",
    theme: "base",
    themeVariables: {{
      fontSize: "16px",
      fontFamily: "system-ui, sans-serif",
      primaryColor: "#ffffff",
      primaryTextColor: "#0b1220",
      primaryBorderColor: "#1e3a8a",
      secondaryColor: "#fef3c7",
      tertiaryColor: "#f1f5f9",
      lineColor: "#1f2937",
      textColor: "#0b1220",
      clusterBkg: "#f1f5f9",
      clusterBorder: "#334155",
      titleColor: "#0b1220",
      edgeLabelBackground: "#ffffff",
      nodeTextColor: "#0b1220",
    }},
    flowchart: {{ htmlLabels: true, nodeSpacing: 40, rankSpacing: 55, padding: 12 }},
  }});
</script>
</body>
</html>
"""
md.with_suffix(".html").write_text(html, encoding="utf-8", newline="\n")
print(len(cliques), "links;", len(linhas), "linhas na tabela")
