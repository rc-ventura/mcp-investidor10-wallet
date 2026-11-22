# Fichamento: Devin Desktop

- **Pesquisado em**: 2026-10-31
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (US3, Devin Desktop)

## Por que esta pesquisa

O roadmap prevê testar o produto no Devin Desktop depois do Claude Desktop. O projeto já
registra servidor e plugin no Devin CLI, e era preciso saber o que é o app, onde ele lê a
configuração de MCP e o que compartilha com o CLI.

## Perguntas

1. O que é o Devin Desktop?
2. Onde fica a configuração de MCP?
3. Ele compartilha formato e recursos com o Devin CLI?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Devin Local Customizations](https://docs.devin.ai/desktop/cascade/mcp) | Oficial | 2026-10-31 |
| F2 | [Devin Desktop changelog](https://docs.devin.ai/desktop/changelog) | Oficial | 2026-10-31 |
| F3 | [Devin MCP docs](https://docs.devin.ai/work-with-devin/mcp.md) | Oficial | 2026-10-31 |
| F4 | [How to Set Up MCP Servers in Windsurf (Now Devin Desktop)](https://fast.io/resources/windsurf-mcp-setup-guide/) | Comunidade | 2026-10-31 |
| F5 | [Sevalla: Windsurf](https://docs.sevalla.com/ai-agents/windsurf) | Comunidade | 2026-10-31 |

As afirmações de F2 a F5 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada. Só F1 foi lida.

## Achados

### Origem

- A Cognition renomeou o Windsurf para Devin Desktop; as fontes datam isso de junho de 2026. O
  app foi anunciado em 02/06/2026 como a próxima geração do Windsurf. [F4]

### Configuração de MCP

- Caminhos na documentação oficial: projeto `.devin/config.json`, sobrescrita local
  `.devin/config.local.json` (fora do git) e usuário `~/.config/devin/config.json`. [F1]
- Por padrão, o agente pede aprovação antes de chamar uma tool MCP. [F1]
- Suporta transporte stdio, Streamable HTTP e SSE, com OAuth. [F3]
- Aceita `serverUrl` ou `url`; "a field name the client does not recognize causes the server to be
  silently ignored". [F3]
- Um trecho de busca cita limite de 100 tools somadas entre servidores, sem página identificada; F1 não cita limite. [F3]
- Recursos recentes: servidores podem ser citados com @, e o app se conecta a MCPs remotos do Devin
  Cloud, em prévia privada. [F2]

### Recursos

- Plugins agrupam skills, rules, hooks, servidores MCP e subagentes. [F1]
- Skills: workspace (`.devin/skills/`), global (`~/.config/devin/skills/`) e por plugin. [F1]
- Hooks: `.devin/hooks.v1.json` ou nível de usuário; não rodam em Restricted Mode. [F1]
- Regras: `AGENTS.md`, `AGENTS.local.md`, `AGENT.md` e `.devin/rules/*.md`. [F1]

### Relação com o Devin CLI

- O Devin Local compartilha o harness de agente com o Devin CLI, e as personalizações usam o mesmo
  formato e a mesma descoberta. [F1]

## O que as fontes não cobrem

- Se os arquivos de configuração de MCP são compartilhados entre o CLI e o app: F1 fala do harness e
  das personalizações.
- O formato da entrada stdio: F1 aponta para outra página, que não foi lida.
- Problemas de PATH em ambiente gráfico: F1 não cita.

## Divergências entre fontes

- **Arquivo de configuração:** F1 cita `~/.config/devin/config.json`. F4 cita
  `~/.config/devin/mcp_config.json` (ou `%APPDATA%\devin\mcp_config.json`). F5 cita
  `.devin/mcp_config.json` no projeto e `~/.codeium/windsurf/mcp_config.json` em versões anteriores ao
  novo nome.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D14
