# Epg
Epg for me
# EPG Grabber (GitHub Actions)

Este repositório contém um EPG grabber que corre dentro do GitHub Actions e actualiza `epg.xml` no repositório.

## Como usar

1. Edite `config.yml` para apontar para as tuas fontes EPG (xml/json).
2. Faz push para um repositório no GitHub.
3. Workflow `EPG Grabber` está configurado para correr a cada 48 horas; podes também correr manualmente em _Actions > EPG Grabber > Run workflow_.
