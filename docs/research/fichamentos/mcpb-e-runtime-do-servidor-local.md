# Fichamento: formato MCPB e runtime de servidor local

- **Pesquisado em**: 2026-10-31
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (distribuição Desktop)

## Por que esta pesquisa

O servidor do produto é escrito em Python e hoje roda com `uvx`. Para um usuário
leigo no Claude Desktop, era preciso saber o que o app oferece para rodar um
servidor local, se ele traz Python ou `uv` e o que o formato de extensão exige.

## Perguntas

1. O que é um MCPB e quais tipos de servidor ele aceita?
2. O que cada tipo exige da máquina do usuário?
3. O app traz algum runtime?
4. Um plugin pode levar um MCPB?
5. Por que servidores falham com `spawn uvx ENOENT` em apps gráficos?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [MCPB MANIFEST.md](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md) | Oficial | 2026-11-01 |
| F2 | [Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb) | Oficial | 2026-11-01 |
| F3 | [Getting started with local MCP servers on Claude Desktop](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) | Oficial | 2026-10-31 |
| F4 | [Add components to a plugin (Claude Code)](https://code.claude.com/docs/en/plugins/components) | Oficial | 2026-11-01 |
| F5 | [Plugin manifest reference (Claude Code)](https://code.claude.com/docs/en/plugins/manifest-reference.md) | Oficial | 2026-11-01 |
| F6 | [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support) | Oficial | 2026-11-01 |
| F7 | [Exemplos do repositório MCPB](https://github.com/modelcontextprotocol/mcpb/tree/main/examples) | Oficial | 2026-11-01 |
| F8 | [mcpb PR 158: tipo `uv`](https://github.com/modelcontextprotocol/mcpb/pull/158) | Oficial | 2026-11-01 |
| F9 | [Registro npm de `@anthropic-ai/mcpb`](https://registry.npmjs.org/@anthropic-ai%2fmcpb) | Oficial | 2026-11-01 |
| F10 | [unity-mcp PR 398](https://github.com/CoplayDev/unity-mcp/pull/398) | Comunidade | 2026-11-01 |
| F11 | [Fix "spawn npx ENOENT" in MCP Servers](https://mcpplaygroundonline.com/blog/fix-spawn-npx-enoent-mcp) | Comunidade | 2026-11-01 |
| F12 | [MCP, plugins, skills, and hooks (Desktop 3P)](https://claude.com/docs/third-party/claude-desktop/extensions) | Oficial | 2026-11-01 |

As afirmações de F8, F10 e F11 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### O formato

- "An MCP Bundle (`.mcpb`) is a zip archive containing a local MCP server and a
  `manifest.json`", instalado com um clique pelo Claude Desktop. O servidor roda na
  máquina do usuário por stdio. [F2]
- Instalação: duplo clique, arrastar para a janela, ou Settings > Extensions >
  Advanced settings > Install Extension. [F2]
- Listagens de extensões no diretório estão obsoletas; o diretório não aceita mais
  submissões MCPB. [F2]

### Tipos de servidor

| Tipo | Exige |
|---|---|
| `node` | Runtime incluído no Claude Desktop; é a linguagem "strongly recommended" [F2] |
| `python` | `entry_point`; "All dependencies must be bundled", em `server/lib` ou `server/venv`; versão em `compatibility.runtimes.python` [F1] |
| `binary` | "Completely self-contained (no runtime requirements)"; aceita binários por plataforma [F1] |
| `uv` | "Python server using UV runtime (v0.4+)"; dependências "installed by the host application using UV"; "No user Python installation required"; "Must include `pyproject.toml`"; "Must NOT include `server/lib/` or `server/venv/`"; `mcp_config` opcional [F1] |

- O PR que adicionou `uv` ao esquema v0.4 é marcado como experimental. [F8]
- O repositório tem o exemplo `hello-world-uv`. [F7]
- O CLI `@anthropic-ai/mcpb`, na versão `2.1.2`, foi publicado em 04/12/2025 e é a
  `latest`. [F9]

### Runtime do app

- O Claude Desktop "includes a built-in Node.js environment". Extensões aceitam Node.js,
  Python e binários. [F3]
- Node "Included with Claude Desktop on macOS and Windows". [F2]

### Configuração no manifesto

- `user_config` gera a tela de configuração da extensão. [F2]
- `sensitive` mascara a entrada e guarda com segurança; `${user_config.KEY}` é
  substituído em `mcp_config`. [F1]
- Valores sensíveis usam o Keychain (macOS) e o Credential Manager (Windows). [F3]

### Plataformas

- `compatibility.platforms` aceita `darwin`, `win32` e `linux`. "If omitted, all
  platforms are supported." [F1]
- Claude Desktop roda em macOS e Windows. [F2]

### MCPB dentro de plugin

- "The `mcpServers` key also accepts a packaged server as an MCPB file [...] as a path
  inside the plugin or an `https://` URL". O servidor recebe o nome do manifesto do
  bundle. [F4]
- O Claude Code extrai o bundle em `.mcpb-cache/`. [F5]
- "A bundled server with a required setting that has no saved value doesn't start."
  [F4]
- A tabela de superfícies inclui "`.mcpb` bundles" entre os servidores locais de plugin
  que o Cowork carrega. [F6]

### PATH em apps gráficos

- Em entrada local de plugin, `command` é "a program name on `PATH` or an absolute path".
  [F12]
- Relato de comunidade: "Claude Desktop on macOS does not inherit the user's full PATH,
  causing 'spawn uvx ENOENT' errors". [F10]
- Guias de comunidade recomendam caminho absoluto para o executável. [F10] [F11]

## O que as fontes não cobrem

- Se o Claude Desktop traz o próprio `uv`: F1 diz que as dependências são instaladas "by
  the host application using UV", e não diz quem fornece o `uv`. F3 não cita Python
  embarcado nem `uv`.
- O que um cliente faz numa plataforma ausente de `compatibility.platforms`: F1 só trata
  do campo omitido.
- Se o Claude Code aceita MCPB do tipo `uv`, e se o CLI `2.1.2` valida o `manifest_version`
  `0.4`.

## Divergências entre fontes

- **Versão do manifesto:** F1 identifica a versão atual como 0.3 no cabeçalho, mas a seção
  do tipo `uv` usa `manifest_version` 0.4.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D1
