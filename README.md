# Epg
Epg for me
# EPG Grabber (GitHub Actions)

Este repositório contém um EPG grabber que corre dentro do GitHub Actions e actualiza `epg.xml` no repositório.

## Como usar

1. Edite `config.yml` para apontar para as tuas fontes EPG (xml/json).
2. Faz push para um repositório no GitHub.
3. Workflow `EPG Grabber` está configurado para correr a cada 3 horas; podes também correr manualmente em _Actions > EPG Grabber > Run workflow_.

## Segurança
- O workflow usa `GITHUB_TOKEN` automático para fazer commit. Não coloques tokens de terceiros no repositório.
- Se precisares de credenciais para aceder a uma fonte, usa GitHub Secrets e altera `fetch_url`/workflow para injectar as variáveis (ex.: `AUTH_HEADER`).

## Formato JSON esperado (opcional)
Se a tua fonte for JSON, o formato esperado é simples:
```json
{
  "channels": [{"id":"ch1","display-name":"Canal 1"}],
  "programs": [
    {"channel":"ch1","start":"20251013T150000 +0000","stop":"20251013T153000 +0000","title":"Título","desc":"Descrição"}
  ]
}
