# Fichamento: como o usuário entrega dados a um servidor MCP

- **Pesquisado em**: 2026-11-01
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (configuração da carteira)

## Por que esta pesquisa

A carteira restrita usa um link que funciona como credencial. Era preciso saber quais
mecanismos existem para o usuário informar esse link e como cada um se comporta em
cada superfície, em especial se o valor passa pelo modelo.

## Perguntas

1. Plugins têm formulário de configuração, e em quais superfícies ele aparece?
2. O que é elicitation e quais clientes suportam?
3. MCP Apps permitem um formulário dentro da conversa? Onde funcionam?
4. Anotações de tool impõem segurança?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Plugin manifest reference: User configuration](https://code.claude.com/docs/en/plugins/manifest-reference.md) | Oficial | 2026-11-01 |
| F2 | [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support) | Oficial | 2026-11-01 |
| F3 | [Add components to a plugin](https://code.claude.com/docs/en/plugins/components) | Oficial | 2026-11-01 |
| F4 | [Spec MCP 2026-07-28: Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) | Oficial | 2026-11-01 |
| F5 | [MCP Apps (overview)](https://modelcontextprotocol.io/extensions/apps/overview) | Oficial | 2026-11-01 |
| F6 | [Get started with MCP Apps](https://claude.com/docs/connectors/building/mcp-apps/getting-started.md) | Oficial | 2026-11-01 |
| F7 | [Add an interactive UI to your MCP server](https://claude.com/docs/connectors/building/mcp-apps/quickstart.md) | Oficial | 2026-11-01 |
| F8 | [Troubleshoot MCP Apps](https://claude.com/docs/connectors/building/mcp-apps/troubleshooting.md) | Oficial | 2026-11-01 |
| F9 | [FastMCP: Apps overview](https://gofastmcp.com/apps/overview) | Oficial | 2026-11-01 |
| F10 | [FastMCP: Apps low-level](https://gofastmcp.com/apps/low-level) | Oficial | 2026-11-01 |
| F11 | [FastMCP: Tools](https://gofastmcp.com/servers/tools) | Oficial | 2026-11-01 |
| F12 | [Feature request: elicitation no Claude Desktop (#41110)](https://claudeissues.com/issue/41110-feature-mcp-elicitation-support-in-claude-desktop-app) | Comunidade | 2026-11-01 |
| F13 | [Feature request: elicitation no Claude Desktop (#41347)](https://claudeissues.com/issue/41347-feature-mcp-elicitation-support-in-claude-desktop-app) | Comunidade | 2026-11-01 |
| F14 | [Artigo sobre Tasks e Elicitations no Claude](https://azukiazusa.dev/en/blog/claude-mcp-tasks-elicitations) | Comunidade | 2026-11-01 |
| F15 | [MCP elicitation explained](https://nango.dev/blog/mcp-elicitation-explained) | Comunidade | 2026-11-01 |

As afirmações de F4, F9, F10 e F12 a F15 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### `userConfig` de plugin

- "`userConfig` declares values Claude Code prompts the user for when the plugin is
  enabled." Tipos: `string`, `number`, `boolean`, `directory`, `file`. [F1]
- `sensitive: true` "masks input and stores the value in secure storage instead of
  `settings.json`". Valores sensíveis não entram no conteúdo de skills e agentes. [F1]
- O formulário aparece no `/plugin` e na extensão do VS Code. `claude plugin install` no
  shell nunca pergunta; aceita `--config KEY=VALUE`. [F3]
- Cowork: "Ignored when a referenced option has no default; Cowork doesn't prompt for
  values". Chat: "Ignored when the URL contains the reference". [F2]

### Elicitation

- A spec define dois modos. Form mode: "Servers can request structured data from users".
  URL mode: "Servers can direct users to external URLs for sensitive interactions that must
  not pass through the MCP client". [F4]
- "Servers MUST use URL mode for interactions involving such sensitive information." [F4]
- Claude Code: diálogo no terminal para form mode e navegador para URL mode, segundo um
  panorama de setembro de 2026. [F15]
- Claude Desktop: dois pedidos de recurso de março de 2026 dizem que o CLI suporta e o app
  não. [F12] [F13]
- Um artigo diz que, em 23/10/2026, a Anthropic anunciou Tasks e Elicitations no Claude,
  disponíveis no Claude Code CLI e chegando a outros produtos depois. [F14]

### MCP Apps

- "MCP Apps let servers return interactive HTML interfaces (data visualizations, forms,
  dashboards) that render directly in the chat." [F5]
- Formulários são um caso citado: "an MCP App presents a form where users see all options at
  once". [F5]
- Rodam em iframe isolado, que não acessa a página pai, e se comunicam por `postMessage`. "The
  host controls which capabilities your app can access." [F5]
- O app pode pedir chamadas de tool, enviar mensagens e atualizar o contexto do modelo. O
  diagrama mostra a chamada indo do app ao host, e do host ao servidor. [F5]
- Suporte listado: Claude, Claude Desktop, VS Code GitHub Copilot, Microsoft 365 Copilot, Goose,
  Postman, MCPJam e Archestra.AI. [F5]
- "Claude asks for permission to display the app." Exemplos locais rodam no Desktop pelo arquivo
  de configuração. [F6]
- "Claude Code calls the tool as text and doesn't render the UI." [F7]
- "MCP tool calls are proxied through Claude's backend and egress from Anthropic's published IP
  ranges, not the user's device", em nota sobre requisições vindas do app. [F8]
- `ui.domain` não está disponível para conector stdio local. [F8]
- O FastMCP documenta suporte desde a 3.0, com `visibility=["app"]` para tools "hidden from the
  LLM" e `ctx.client_supports_extension(UI_EXTENSION_ID)`. [F9] [F10]

### Anotações de tool

- `annotations` aceita `readOnlyHint`, `destructiveHint`, `idempotentHint` e `openWorldHint`. São
  "advisory hints for clients and don't enforce security on their own". [F11]

## O que as fontes não cobrem

- Se o Claude Desktop ou o Cowork suportam elicitation: não há documentação oficial da Anthropic
  nas fontes lidas.
- Se MCP Apps aparecem numa sessão Cowork com servidor local de plugin: F5 e F6 citam Claude e
  Claude Desktop.
- Se o valor digitado num MCP App fica fora do histórico da conversa e dos servidores da Anthropic
  quando o servidor é local: F5 e F8 não tratam desse caso.
- O comportamento em Devin, Codex e Gemini: a matriz completa de clientes (F5 aponta
  `extensions/client-matrix`) não foi lida.

## Divergências entre fontes

Nenhuma registrada.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D4 e D15
- [Contrato da configuração](../../../specs/005-desktop-distribution/contracts/wallet-setup.md)
