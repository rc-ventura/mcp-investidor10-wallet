# Fichamento: componentes de plugin por superfície, instalação e hooks

- **Pesquisado em**: 2026-10-31
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (distribuição Desktop)

## Por que esta pesquisa

A primeira versão da spec afirmava que persona, hooks e skills não chegariam ao
Claude Desktop. O mantenedor contestou, porque viu que dava para adicionar
plugins no app. Foi preciso conferir o que cada superfície carrega de fato e como
um plugin é instalado.

## Perguntas

1. O que Chat, Cowork e Claude Code carregam de um plugin?
2. Como um usuário instala um plugin fora do diretório?
3. Como o plugin chega ao Claude Code?
4. Como os hooks se comportam, em especial no Windows?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support) | Oficial | 2026-11-01 |
| F2 | [Plugins (overview)](https://claude.com/docs/plugins/overview.md) | Oficial | 2026-11-01 |
| F3 | [Plugin structure and testing](https://claude.com/docs/plugins/build.md) | Oficial | 2026-11-01 |
| F4 | [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) | Oficial | 2026-10-31 |
| F5 | [Install plugins (Cowork)](https://claude.com/docs/cowork/guide/plugins.md) | Oficial | 2026-11-01 |
| F6 | [MCP, plugins, skills, and hooks (Desktop 3P)](https://claude.com/docs/third-party/claude-desktop/extensions) | Oficial | 2026-11-01 |
| F7 | [Add components to a plugin (Claude Code)](https://code.claude.com/docs/en/plugins/components) | Oficial | 2026-11-01 |
| F8 | [Plugin manifest reference (Claude Code)](https://code.claude.com/docs/en/plugins/manifest-reference.md) | Oficial | 2026-11-01 |
| F9 | [Install and manage plugins (Claude Code)](https://code.claude.com/docs/en/plugins/install) | Oficial | 2026-11-01 |
| F10 | [Claude Code on desktop](https://code.claude.com/docs/en/desktop.md) | Oficial | 2026-11-01 |

## Achados

### O que cada superfície carrega

| Componente | Chat | Cowork | Claude Code |
|---|---|---|---|
| Skills | Carrega | Carrega | Carrega |
| Commands | Carrega como skill | Carrega; `/plugin-name:command` | Carrega |
| Agents | Ignora | Carrega | Carrega |
| Hooks | Ignora | Carrega | Carrega |
| Servidor MCP remoto (URL fixa) | Listado em Connectors; funciona depois de conectar | Carrega; conectar em Connectors | Carrega |
| Servidor MCP local, incluindo `.mcpb` | Ignora | "Loads when the Cowork session runs on your computer" | Carrega |
| Servidor com `${user_config.*}` | Ignora se a URL tem a referência | Ignora se a opção não tem padrão; "Cowork doesn't prompt for values" | Carrega e pede os valores |
| `bin/` no topo | Não instala o plugin | Não instala o plugin | Carrega |
| LSP, output styles, themes, `settings` | Ignora | Ignora | Carrega |

Tabela de [F1]. "A surface skips a component it doesn't load, so a plugin can
look complete in one place and partial in another." [F1]

- Chat ignora agentes e hooks "without an error"; um servidor local é ignorado no
  chat como comportamento previsto. [F3]
- Um conector marcado **Runs in each session** "runs a program on your computer".
  [F2]
- Plugins locais rodam "with the same permissions as any other program". [F4]

### Instalação

- Tudo começa em **Customize > Plugins**, no claude.ai ou no app, por três
  caminhos: **Discover**, **Add > Add marketplace** e **Add > Upload plugin**
  (`.zip` ou `.plugin`). [F2]
- Add marketplace aceita repositório GitHub e GitHub Enterprise, e GitLab e
  Bitbucket públicos, por URL ou `owner/repo`. Repositório GitHub privado pede
  conectar a conta. [F2] [F1]
- "Anthropic reviews plugins listed in the directory"; isso "doesn't cover a
  plugin you add from a marketplace URL or upload yourself". [F2]
- Plugins exigem plano pago (Pro, Max, Ultra, Team, Enterprise). [F4]
- Limites: 200 MB por plugin, 5.000 arquivos, 500 plugins por marketplace, 25
  marketplaces adicionados pelo usuário. [F1] [F5]
- A aba Code instala por **+ > Add plugins**, em sessão local ou SSH; o navegador
  de plugins não existe em sessões na nuvem nem em WSL. [F10]
- O Desktop lê os mesmos arquivos de configuração que o CLI. [F10]

### Sincronização com o Claude Code

- "A plugin you install on your account also appears in Claude Code as a synced
  plugin at the next session start." O inverso não acontece. [F1]
- Ele aparece como `<name>@synced`. Para remover, é preciso desligar no claude.ai.
  [F9]
- Exige Claude Code v2.1.273 ou superior e login com a mesma conta; não sincroniza
  com chave de API nem provedores como Bedrock. `syncClaudeAiPlugins: false`
  desliga. [F4] [F9]
- "When another enabled plugin has the same name, one of the two registers its
  `hooks/hooks.json` hooks and the other's are left out." [F7]

### Servidor dentro do plugin

- Declarado em `.mcp.json` ou na chave `mcpServers`, que aceita mapa, caminho
  `.json`, bundle `.mcpb` ou `.dxt`, por caminho ou URL `https://`. [F7] [F8]
- No Claude Code, o servidor aparece como `plugin:<plugin>:<server>`, e as tools
  como `mcp__plugin_<plugin>_<server>__<tool>`. [F7]
- Em entrada local de plugin: "Give `command` as a program name on `PATH` or an
  absolute path, using `${CLAUDE_PLUGIN_ROOT}`". [F6]
- `${CLAUDE_PLUGIN_ROOT}` muda a cada atualização. `${CLAUDE_PLUGIN_DATA}` sobrevive
  a atualizações, mas é apagado por padrão ao desinstalar o plugin. [F8]

### Conectores depois de instalar

- "Adding a plugin doesn't add a connector to your account or sign you in to
  anything." A aba **Connectors** do plugin mostra Connected, Not connected ou Not
  added. [F2]
- "The plugin's skills load whether or not you connect anything." [F2]

### Hooks

- Hooks de plugin "run wherever the plugin itself loads". Cowork roda hooks de
  plugins de marketplace, de `org-plugins/` e dos que o usuário adiciona. [F6]
- Com o Claude unificado, uma sessão Cowork da tela inicial "runs the same hooks as
  any other Cowork session". [F6]
- "On a Windows device without Git for Windows, Claude Code runs a hook in
  PowerShell when the hook sets neither `shell` nor `args`. Hooks in Cowork
  sessions run the same way, on the device itself and not in Cowork's virtual
  machine." [F6]
- "PowerShell rejects some commands that Bash accepts, such as a quoted program
  path followed by arguments." [F6]
- Nesse cenário, um hook `PreToolUse` ou `PermissionRequest` sem `args` e sem
  `onFailure` "blocks the tool call when it fails or times out". [F6]
- `${CLAUDE_PLUGIN_ROOT}` é substituído em comandos de hook e exportado ao processo.
  No Windows, os caminhos mantêm barras invertidas em hook via PowerShell. [F7] [F8]
- A saída de um `PreToolUse` que termina com código 2 bloqueia a tool
  independentemente de `onFailure`. [F6]

## O que as fontes não cobrem

- Se o processo do servidor iniciado numa sessão Cowork pode abrir o navegador ou
  gravar em `~/`: F1, F2 e F6 dizem que ele roda no computador, sem detalhar esses
  acessos.
- Se um servidor local sem configuração aparece já conectado ou pede um passo na
  aba Connectors: F2 descreve os estados de forma geral.
- Se a forma curta de nome de tool funciona na lista `tools` de um agente de plugin:
  F7 cita o nome completo para permissões e matchers, sem tratar dessa lista.
- Se `transcript_path` chega aos hooks numa sessão Cowork.

## Divergências entre fontes

- **Hooks em conversa Chat:** F1 diz que o Chat ignora hooks. F6 diz que "Chat
  conversations run hooks from the same plugins as Cowork sessions, on Claude
  Desktop 1.52386.0 or later" (documentação do Desktop 3P). F4 os mostra como
  "Grayed out".
- **Conector depois de instalar:** F4 diz que "Bundled connectors are set up
  automatically". F2 e F5 dizem que instalar não adiciona nem conecta conector.

## Usado em

- [Spec 005](../../../specs/005-desktop-distribution/spec.md), FR-001 a FR-009d
- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D1,
  D9 e D10
