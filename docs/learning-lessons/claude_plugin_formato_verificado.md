# Learning lesson: formato real de plugin do Claude Code (versão instalada 2026-10)

- **Data**: 2026-10-24
- **Fontes**: `claude plugin marketplace add` + `claude plugin details`
  (versão instalada do Claude Code); docs oficiais do repo
  `anthropics/claude-code` (`plugins/plugin-dev/skills/plugin-structure` e
  `hook-development`, via Context7)

## Fatos verificados (divergem dos exemplos publicados)

1. **`marketplace.json` exige `owner`** (objeto, ex.: `{"name": "..."}`) — sem
   ele, `claude plugin marketplace add` rejeita com "Invalid input: expected
   object, received undefined".
2. **Os campos `agents` e `hooks` do manifesto são ignorados silenciosamente**
   na carga: declarar paths custom nesses campos não gera erro, mas o
   inventário mostra `Agents (0)` e `Hooks (0)`. O que funciona é o
   **auto-discovery do layout canônico** (diretórios `agents/`, `hooks/`,
   `skills/` na raiz do plugin). `commands/` e `mcpServers` declarados
   funcionam.
3. **Agents exigem frontmatter completo**: `name`, `description`, `model:
   inherit`, `color` (e `tools` opcional). Sem `model`/`color`, o arquivo em
   `agents/` não vira agente.
4. **Hooks de plugin usam formato wrapper** (`{"description": …,
   "hooks": {"Stop": [{"matcher": "*", "hooks": […]}]}}`) — o formato plano
   (sem wrapper/`matcher`, como o do ralph-loop do Devin) não registra no
   Claude Code.
5. **`commands/` é só do Claude Code** — o Devin CLI não lê `commands/`; o
   diretório canônico compartilhado é `skills/` (Devin expõe como
   `/plugin:skill`, Claude lista como skills).
6. **Persona via hook `SessionStart` funciona** — script que imprime
   `{"hookSpecificOutput": {"hookEventName": "SessionStart",
   "additionalContext": "…"}}` injeta instruções em toda sessão, no Claude
   Code e no Devin CLI (verificado 2026-10-24: inventário Hooks (2) —
   SessionStart + Stop — nos dois).

## Decisões decorrentes (spec 003, US2)

- O plugin vive em `plugin/` com **layout canônico completo** (raiz do
  plugin): `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json` + dois
  manifestos finos dentro dele (`.claude-plugin/plugin.json` e
  `.devin-plugin/plugin.json`). O marketplace fica na raiz do repo com
  `"source": "./plugin"`.
- Manifesto Claude declara **apenas** `mcpServers`; skills/agents/hooks são
  auto-descobrídos. O Devin CLI também leu `hooks/hooks.json` (formato
  wrapper) via fallback do manifesto Claude — um arquivo de hooks serve os
  dois.
- Os 3 prompts viraram skills (formato compartilhado), não `commands/`.
- Verificação de carga real (T021): Claude Code — Skills (3), Agents (1),
  Hooks (1 Stop), MCP (1); Devin CLI — Skills (3 como slash commands),
  Agents (1), Hook on stop (caminho único correto), MCP com
  `WALLET_ID=${WALLET_ID}`.