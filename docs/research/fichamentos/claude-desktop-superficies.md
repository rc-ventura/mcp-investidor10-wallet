# Fichamento: superfícies do Claude Desktop e diferença entre desktop e web

- **Pesquisado em**: 2026-10-31
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (distribuição Desktop)

## Por que esta pesquisa

O produto precisava chegar ao Claude Desktop, e havia dúvida sobre a diferença
entre desktop e web. Durante a especificação, o mantenedor apontou que a aba
Chat não existia mais no app, o que exigiu conferir como as superfícies estão
organizadas hoje.

## Perguntas

1. Qual a diferença entre o app desktop e a versão web para um servidor MCP?
2. O Chat e o Cowork ainda são superfícies separadas?
3. O que uma mensagem da tela inicial abre?
4. Onde fica a aba Code nesse arranjo?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Unified Claude in Claude Desktop on 3P](https://claude.com/docs/third-party/claude-desktop/unified-claude.md) | Oficial | 2026-10-31 |
| F2 | [Changelog do Cowork](https://claude.com/docs/cowork/changelog.md) | Oficial | 2026-10-31 |
| F3 | [Cowork overview](https://claude.com/docs/cowork/overview.md) | Oficial | 2026-10-31 |
| F4 | [Get started with custom connectors using remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-MCP) | Oficial | 2026-10-31 |
| F5 | [Getting started with local MCP servers on Claude Desktop](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) | Oficial | 2026-10-31 |
| F6 | [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/add-unlisted.md) | Oficial | 2026-10-31 |
| F7 | [Claude Cowork and chat come together for Enterprise](https://claude.com/resources/articles/unified-claude-enterprise) | Oficial | 2026-10-31 |
| F8 | [Use Claude Cowork on Team and Enterprise plans](https://support.claude.com/en/articles/13455879-use-claude-cowork-on-team-and-enterprise-plans) | Oficial | 2026-10-31 |
| F9 | [XDA: Anthropic merges Claude Cowork and chat](https://www.xda-developers.com/anthropic-merges-claude-cowork-and-chat-into-one-singular-claude/) | Comunidade | 2026-10-31 |
| F10 | [PYMNTS: Anthropic merges Claude Chat and Cowork for Enterprise users](https://www.pymnts.com/news/artificial-intelligence/2026/anthropic-merges-claude-chat-and-cowork-for-enterprise-users/) | Comunidade | 2026-10-31 |
| F11 | [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support) | Oficial | 2026-11-01 |

As afirmações de F7 a F10 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### Claude unificado

- "Unified Claude combines Chat and Cowork into one experience, with Cowork's
  agentic capabilities." O Code "stays separate". [F1]
- Com ele ligado, o usuário escreve na tela inicial sem escolher entre Chat e
  Cowork. "On a device that can run Cowork, each message sent from the home
  screen starts a Cowork session. On a device that can't run Cowork's virtual
  machine, the message starts a Chat conversation instead." [F1]
- Conversas e tarefas anteriores continuam disponíveis, listadas juntas na barra
  lateral. [F1]
- "The Chat experience is going away", com restrição de capacidades por
  configuração. [F1]
- Em implantações em provedores terceiros (3P), o recurso é beta e opcional até
  10/11/2026; depois das 12:00 PT desse dia, um `desktopHome` não definido é
  lido como `standard`, e o Cowork fica ligado mesmo onde foi desligado.
  [F1] [F2]
- A fusão foi anunciada em 16/09/2026, primeiro para Pro e Max, em etapas: "If
  your message box still shows separate 'Chat' and 'Cowork' options, your
  account has not moved over yet". O artigo de ajuda cita Pro, Max e Ultra. [F9]
- Em Team (beta) e Enterprise, está disponível onde a opção unificada está ligada.
  [F8]
- Conversas, projetos, artefatos, conectores e skills continuam disponíveis após
  a fusão; a fonte do Enterprise cita também plugins. [F7] [F9]

### O que o Cowork carrega

- "Cowork uses the same agentic architecture that powers Claude Code." [F3]
- Conectores, skills e plugins são geridos em **Customize**. O Cowork "loads the
  ones enabled for your claude.ai account, synced at session start, and doesn't
  read the Claude Code CLI's `~/.claude` directory on your machine". [F3]

### Aba Code

- A coluna Claude Code da tabela oficial cobre "the terminal, the IDE extensions,
  and the desktop app's Code tab". [F11]
- O Code não é afetado por `desktopHome`. [F2]

### Desktop e web

- Conector remoto: "Claude connects to your remote MCP server from Anthropic's
  cloud infrastructure". "The connection to your MCP server originates from
  Anthropic's servers, not from your machine's network interface." Vale para
  claude.ai, Claude Desktop, Cowork e apps móveis. [F4]
- Servidor local configurado em `claude_desktop_config.json`: "a separate
  mechanism", que usa a rede local, e "those aren't available in Cowork or
  claude.ai". [F4]
- Extensão de desktop: "runs the server on your own computer"; serve para acesso
  a arquivos e ferramentas locais, dados sensíveis e trabalho offline. [F6]
- Uma extensão instalada "will automatically be available in your
  conversations". [F5]
- Servidor local trazido por plugin "works in Claude Code and in a Cowork session
  that runs on your computer in the desktop app, not in chat". Na web, a aba
  Connectors do plugin o marca como "Runs in each session". [F11]

## O que as fontes não cobrem

- Se uma extensão `.mcpb` instalada em Settings > Extensions aparece nas sessões
  do Claude unificado: F2 não tem entradas sobre isso, e F5 não cita Cowork nem o
  Claude unificado.
- Quais planos o changelog alcança: ele diz apenas "all orgs" e "orgs". [F2]

## Divergências entre fontes

- **Data para organizações:** F1 e F2 dizem 10/11/2026 (Desktop 3P). Um
  trecho de busca cita 16/11 para organizações existentes, sem página identificada. [F10]
- **Aba Chat:** F1 diz "The Chat experience is going away", mas nenhuma entrada de
  F2 usa a expressão "removing the Chat tab", e guias de terceiros descrevem o
  arranjo de formas diferentes conforme a etapa de liberação.

## Usado em

- [Spec 005](../../../specs/005-desktop-distribution/spec.md), tabela de
  superfícies
- [Research da spec 005](../../../specs/005-desktop-distribution/research.md)
