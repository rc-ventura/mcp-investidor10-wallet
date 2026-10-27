# Contract: manifestos e assets do plugin (spec 003)

Um único conjunto de assets em `plugin/` (raiz do plugin, layout canônico)
com **um manifesto fino por cliente** — quatro manifestos, zero duplicação de
conteúdo de comportamento. **O plugin não registra servidor MCP** (decisão
2026-10-24): a conexão é responsabilidade exclusiva do assistente de
instalação. Formato verificado empiricamente no Claude Code e no Devin CLI
em 2026-10-24 (T021) — divergências do publicado em
`docs/learning-lessons/claude_plugin_formato_verificado.md`; formatos de
Codex e Gemini validados por contrato, carga real pendente (Gemini CLI não
instalado nesta máquina; Codex em TUI — T021 estende quando disponível).

## Estrutura

```text
plugin/
├── .claude-plugin/plugin.json   # manifesto Claude (sem mcpServers)
├── .devin-plugin/plugin.json    # manifesto Devin (mesmos metadados)
├── .codex-plugin/plugin.json    # manifesto Codex (skills: "./skills")
├── gemini-extension.json        # manifesto Gemini
├── skills/
│   ├── analise-da-carteira/SKILL.md
│   ├── check-de-tese/SKILL.md
│   └── resumo-de-dividendos/SKILL.md
├── commands/                    # custom commands do Gemini (únicos ativos:
│   ├── analise-da-carteira.toml #   no Claude Code commands foram fundidos
│   ├── check-de-tese.toml       #   nas skills desde v2.1.3 — skills são
│   └── resumo-de-dividendos.toml #  user-invocable por padrão)
├── agents/
│   └── guardiao-de-disciplina.md
└── hooks/
    ├── hooks.json               # SessionStart (persona) + Stop (lembrete)
    ├── session-start-persona.sh
    └── stop-memory-reminder.sh
```

## Manifestos

Todos com `name: "investidor10-carteira"`, `version` e `description`
idênticos.

```json
// .claude-plugin/plugin.json — auto-discovery de skills/agents/hooks
{ "name": "investidor10-carteira", "version": "0.1.0", "description": "…" }

// .devin-plugin/plugin.json — idem
{ "name": "investidor10-carteira", "version": "0.1.0", "description": "…" }

// .codex-plugin/plugin.json — paths empacotados com prefixo ./
{ "name": "investidor10-carteira", "version": "0.1.0", "description": "…",
  "skills": "./skills" }

// gemini-extension.json — skills/ e commands/ auto-descobertos
{ "name": "investidor10-carteira", "version": "0.1.0", "description": "…" }
```

## `.claude-plugin/marketplace.json` (raiz do repo)

```json
{
  "name": "investidor10",
  "owner": { "name": "rc-ventura" },
  "plugins": [
    {
      "name": "investidor10-carteira",
      "description": "Comportamento do agente investidor: skills, guardião de disciplina, persona e lembrete de memória",
      "source": "./plugin"
    }
  ]
}
```

- `owner` é **obrigatório** (o `marketplace add` rejeita sem ele).
- Canal canônico no Claude Code: `claude plugin marketplace add
  rc-ventura/mcp-investidor10-wallet` + `/plugin install
  investidor10-carteira`. Instalação por path local documentada para dev.
- Devin: `devin plugins install ./plugin -y --local`. Codex:
  `codex plugin marketplace add <repo>` + TUI `/plugins`. Gemini:
  `gemini extensions install <repo-url|path>`.

## Assets obrigatórios v1

| Asset | Arquivo | Contrato |
|---|---|---|
| Skill análise | `plugin/skills/analise-da-carteira/SKILL.md` | frontmatter `name`+`description`; exige `get_session_context`; cita delay de cotação |
| Skill check de tese | `plugin/skills/check-de-tese/SKILL.md` | confronta tese salva com dados atuais; registro só com confirmação |
| Skill dividendos | `plugin/skills/resumo-de-dividendos/SKILL.md` | `get_earnings` + rendimento recorrente atual (nunca DY médio) |
| Commands Gemini | `plugin/commands/*.toml` | TOML v1 com `prompt` (obrigatório) e `description`; espelham as 3 skills |
| Subagente guardião | `plugin/agents/guardiao-de-disciplina.md` | frontmatter `name`/`description`/`model: inherit`/`color`/`tools` read-only; PROIBIDO tools de escrita; propõe `log_decision` com confirmação |
| Hook persona | `plugin/hooks/session-start-persona.sh` | imprime SOMENTE JSON `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "…"}}` no stdout; persona PT-BR com bootstrap, nunca inventar valores, delay ~15 min, sem ordens, confirmação para gravar |
| Hook memória | `plugin/hooks/stop-memory-reminder.sh` | lê `transcript_path` do stdin; lembrete propondo `log_decision`/`log_insight` com confirmação (FR-008); fail-open (exit 0 silencioso em erro) |

`hooks/hooks.json` em formato wrapper do Claude (lido também pelo Devin):
`{"hooks": {"SessionStart": [{"matcher": "*", "hooks": […]}], "Stop": […]}}`.
Hooks **não** são declarados para Gemini/Codex nesta versão (formatos
distintos; a verificar em spec futura — ver pesquisa plugins-gemini-cli.md).

## Invariantes verificadas pelo teste de contrato

1. Os 4 manifestos são JSON válidos com `name`/`version` idênticos e
   `description`; marketplace tem `owner` e `source: "./plugin"`.
2. **Nenhum** manifesto declara `mcpServers` e `plugin/.mcp.json` não existe.
3. Todos os caminhos declarados (marketplace, `skills` do Codex) existem.
4. `skills/` contém exatamente 3 `SKILL.md` com frontmatter
   `name`+`description` e chamada a `get_session_context`.
5. `commands/` contém exatamente 3 `.toml` com `prompt`+`description`
   espelhando as skills.
6. `hooks/hooks.json` cobre `SessionStart` e `Stop`; o script de persona
   emite `additionalContext`; o script do lembrete contém a palavra de
   confirmação; ambos executáveis.
7. Nenhum asset menciona `memory.json`, contém emoji ou literal numérico de
   `WALLET_ID`.