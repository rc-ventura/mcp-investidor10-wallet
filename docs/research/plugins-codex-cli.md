# Pesquisa: plugins no Codex CLI (24/10/2026)

Fontes primárias: docs oficiais do Codex (`developers.openai.com/codex/plugins`,
`developers.openai.com/plugins/build/plugins`, `learn.chatgpt.com/docs/customization/overview`,
buscados em 2026-10-24) + o skill oficial `plugin-creator` e o plugin
`pluginstaller` do repo `openai/codex`.

## Conceito

O Codex tem **plugins** — bundles de skills, apps e MCP servers instaláveis
via diretório de plugins (TUI `/plugins` no CLI ou app ChatGPT) e via
marketplace. Skills são o formato de autoria; plugins são a unidade de
distribuição instalável. Invocação explícita por `@plugin`.

## Manifesto e layout

```text
my-plugin/
├── .codex-plugin/
│   └── plugin.json       # manifesto (só ele vive dentro de .codex-plugin/)
├── skills/               # skills (SKILL.md + scripts/references/assets)
├── .mcp.json             # servidores MCP do plugin
├── .app.json             # apps/conectores (opcional)
└── assets/               # demais arquivos
```

`plugin.json` canônico: `name`, `version`, `description` + caminhos
empacotados (`skills`, `apps`, `mcpServers`) relativos à raiz do plugin com
prefixo `./`. Referências encontradas apontam o `$schema` da spec aberta
**Agent Plugins** (`https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`)
em plugins portáteis — mesmo ecossistema de spec que o Devin CLI lê como
formato compatível (ver `plugins-devin-cli.md`).

## Skills (formato de autoria)

`SKILL.md` com frontmatter `name` + `description` (obrigatórios) — **o
mesmo formato de skill do Claude Code** — + opcionais `scripts/`,
`references/`, `assets/`. Exemplo oficial (`codex` docs):

```markdown
---
name: commit
description: Stage and commit changes in semantic groups. Use when the user wants to commit, organize commits, or clean up a branch before pushing.
---
1. Do not run `git add .`...
```

## Marketplace e instalação

- Marketplace = catálogo JSON: `$REPO_ROOT/.agents/plugins/marketplace.json`
  (repo) ou `~/.agents/plugins/marketplace.json` (pessoal); entries com
  `source.path` `./`-relativo e `interface.displayName`.
- CLI: `codex plugin marketplace add owner/repo [--ref] [--sparse]` e
  instalação via TUI `/plugins` ou `codex plugin add plugin@marketplace`
  (versões recentes do CLI; em releases antigas era `codex marketplace add`).

## Compatibilidade com Claude/Devin

- **Skills são o denominador comum real**: mesmo formato `SKILL.md`
  (frontmatter `name`/`description`) nos três clientes — nosso `plugin/skills/`
  já é portável ao Codex sem edição.

## Commands: não existe primitivo separado (verificado 2026-10-26)

O Codex não tem custom commands à parte (como os `.toml` do Gemini): a
invocação explícita do usuário é por `@plugin`/`@skill` e as skills são
auto-descobertas pelo agente a partir da pasta `skills/` — o mesmo padrão
"a skill é o command" do Claude Code pós-merge (v2.1.3). O
`commands/*.toml` do nosso plugin (Gemini-only) não se aplica ao Codex.
- Manifestos divergem (`.codex-plugin/plugin.json` próprio), mas o `$schema`
  Agent Plugins sinaliza convergência com o formato que o Devin já aceita.
- MCP universal: `codex mcp add` já registra o mesmo servidor `carteira`
  (verificado em 2026-10-24, T014).

## Conclusões para o produto

- Nenhuma mudança na spec 003: Codex já é atendido pelo assistente de
  instalação (`codex mcp add carteira --env WALLET_ID=... -- uvx ...`).
- Extensão futura do plugin de comportamento ao Codex exigiria apenas um
  manifesto `.codex-plugin/plugin.json` apontando para as mesmas
  `plugin/skills/` + `.mcp.json` — custo baixo, candidato a spec futura
  (mesmo envelope da pergunta do Gemini).