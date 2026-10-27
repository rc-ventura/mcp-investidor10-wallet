# Pesquisa: como criar plugins no Claude Code (24/10/2026)

Formato oficial de plugins do Claude Code, verificado na documentação do
próprio repositório (`anthropics/claude-code`, pasta
`plugins/plugin-dev/skills/`, via Context7) e empiricamente na versão
instalada do CLI (ver `docs/learning-lessons/claude_plugin_formato_verificado.md`
para as divergências entre o publicado e o comportamento real).

## Conceito

Um plugin empacota **comportamento** (skills, agents, hooks — commands
foram fundidos nas skills, ver seção própria) e
**integrações** (MCP servers, LSP) numa unidade instalável. A instalação é
via marketplace: `claude plugin marketplace add <owner/repo|url|path>` e
`claude plugin install <plugin>[@marketplace]` (ou `/plugin install` dentro
da sessão).

## Manifesto e layout canônico

```text
plugin-name/
├── .claude-plugin/
│   └── plugin.json       # manifesto (obrigatório)
├── commands/             # legacy — fundido nas skills (v2.1.3+)
├── agents/               # subagentes (.md) — auto-descobertos
├── skills/               # skills (skill-name/SKILL.md) — auto-descobertos
├── hooks/
│   └── hooks.json        # hooks de lifecycle
└── .mcp.json             # servidores MCP do plugin
```

`plugin.json` (campos): `name` (kebab-case, único), `version`,
`description`, `author`, e referências opcionais (`commands`, `agents`,
`hooks`, `mcpServers`) — mas, na versão verificada em 2026-10, **apenas
`mcpServers` declarado é honrado; skills/agents/hooks são auto-descobertos
do layout de raiz** (os campos declarados são ignorados silenciosamente).

## Componentes

| Componente | Formato | Fonte oficial |
|---|---|---|
| Skill | `skills/<nome>/SKILL.md` com frontmatter `name` + `description` (obrigatórios) + opcionais `scripts/`, `references/`, `assets/` | `plugin-dev/skills/skill-development` |
| Agent | `agents/<id>.md` com frontmatter `name`, `description`, `model: inherit`, `color`, `tools` (opcional) | `plugin-dev/skills/agent-development` |
| Hook | `hooks/hooks.json` em **formato wrapper**: `{"hooks": {"Stop": [{"matcher": "*", "hooks": [{"type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/...\""}]}]}}` | `plugin-dev/skills/hook-development` |
| MCP | `.mcp.json` raiz ou `mcpServers` no manifesto; `${CLAUDE_PLUGIN_ROOT}` e `${VAR}` expansíveis | `plugin-dev/skills/mcp-integration` |

## Commands: fundidos nas skills (verificado 2026-10-26)

- Changelog oficial 2.1.3: *"Merged slash commands and skills … no change in
  behavior"*. Docs oficiais (`code.claude.com/docs/en/skills`): *"Custom
  commands have been merged into skills. A file at `.claude/commands/deploy.md`
  and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy`."*
- **Skills são user-invocable por padrão** (aparecem no menu de slash
  commands; opt-out com `user-invocable: false` no frontmatter) — a skill
  **é** o command. Não há primitivo de command separado ativo.
- `commands/` legado é cidadão de segunda classe (issue #42073: quebrou em
  v2.1.89, corrigido em v2.1.91).
- Consequência para o produto: nosso plugin **não** envia `commands/` para o
  Claude Code — as skills já entregam `/analise-da-carteira` etc. O
  `commands/*.toml` existe apenas para o Gemini (único cliente onde commands
  são o primitivo ativo de invocação do usuário).

## Marketplace

`.claude-plugin/marketplace.json` na raiz de um repo (schema em
`json.schemastore.org/claude-code-marketplace.json`): `name`, `owner`
(objeto — **obrigatório** na prática), `plugins[]` com `name`,
`description`, `source` (caminho `./`-relativo à raiz do marketplace),
`category`. O `source` aponta para a pasta-raiz do plugin.

## Conclusões para o produto

- Nosso `plugin/` usa o layout canônico com manifesto declarando só
  `mcpServers` — carga verificada: Skills (3), Agents (1), Hooks (1 Stop),
  MCP (1).
- O canal canônico de distribuição é o marketplace do repo (`source:
  "./plugin"`), instalável por `owner/repo` no GitHub.