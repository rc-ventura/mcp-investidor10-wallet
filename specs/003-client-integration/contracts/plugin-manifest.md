# Contract: manifestos e assets do plugin (spec 003)

Um único conjunto de assets em `plugin/`, três manifestos finos na raiz
(dois de plugin + um de canal marketplace). Conteúdo fora do wheel (build
hatchling já restringe ao pacote). Variáveis de plugin são expandidas com
`${CLAUDE_PLUGIN_ROOT}` resolver root; Devin CLI também expande essa variável
(compatibilidade documentada).

## `.claude-plugin/plugin.json` (obrigatório no Claude Code)

```json
{
  "name": "investidor10-carteira",
  "version": "0.1.0",
  "description": "Comportamento do agente investidor: prompts, guardião de disciplina e lembrete de memória",
  "commands": "./plugin/commands",
  "agents": "./plugin/agents",
  "hooks": "./plugin/hooks/hooks.json",
  "mcpServers": "./plugin/.mcp.json"
}
```

## `.devin-plugin/plugin.json` (precedência no Devin CLI)

```json
{
  "name": "investidor10-carteira",
  "version": "0.1.0",
  "description": "Comportamento do agente investidor: prompts, guardião de disciplina e lembrete de memória"
}
```

Devin resolve os componentes por localização convencional do formato
Claude-equivalente lendo `plugin/` via manifesto; a carga real é validada no
quickstart V4 (risco documentado em research.md D2).

## `plugin/.mcp.json`

```json
{
  "mcpServers": {
    "carteira": {
      "command": "uvx",
      "args": ["mcp-investidor10-wallet"],
      "env": { "WALLET_ID": "${WALLET_ID}" }
    }
  }
}
```

- `${WALLET_ID}` vem do ambiente do usuário (nunca baked); ausente, o
  servidor falha visivelmente como faz hoje sem a variável.
- O assistente de instalação (Bloco B) continua o caminho principal de registro para usuários
  sem plugin; colisão de alias entre servidores registrados pelos dois
  caminhos é namespaced pelo próprio cliente (verificação manual V4).

## Assets obrigatórios v1

| Asset | Arquivo | Contrato |
|---|---|---|
| Prompt análise | `plugin/commands/analise-da-carteira.md` | guia de uso das tools de carteira; assa usar `get_session_context` antes e citar delay de cotação |
| Prompt check de tese | `plugin/commands/check-de-tese.md` | confronta a tese salva com dados atuais |
| Prompt dividendos | `plugin/commands/resumo-de-dividendos.md` | usa `get_earnings` + regras de periodo |
| Subagente guardião | `plugin/agents/guardiao-de-disciplina.md` | read-only: `get_rules`, `get_theses`, tools de dados; PROIBIDO escrever na memória; reporta violações e pede confirmação humana para `log_decision` |
| Hook memória | `plugin/hooks/hooks.json` + `stop-memory-reminder.sh` | evento `Stop`; inspeciona transcript do stdin; se detectou discussão de decisão sem chamada `log_decision`/`log_insight`, emite lembrete pedindo confirmação do usuário (FR-010); fail-open: sem transcript ou erro → sai 0 em silêncio |

## `.claude-plugin/marketplace.json` (canal de instalação no Claude Code)

```json
{
  "name": "investidor10",
  "plugins": [
    {
      "name": "investidor10-carteira",
      "description": "Comportamento do agente investidor: prompts, guardião de disciplina e lembrete de memória",
      "source": "./"
    }
  ]
}
```

- Habilita `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet`
  seguido de `/plugin install investidor10-carteira` — canal canônico
  decidido em 2026-10-24. Instalação por path local permanece documentada
  para desenvolvimento.
- Os campos exatos seguem a especificação de marketplace do Claude Code
  (verificar os campos suportados na doc oficial na implementação — task T020
  registra divergências como learning lesson).

## Invariantes verificadas pelo teste de contrato

1. Os três manifestos (`.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `.devin-plugin/plugin.json`) parseiam
   como JSON válidos; `name`/`version` do plugin idênticos nos dois
   manifestos de plugin, e o nome listado no marketplace coincide com o
   manifesto do plugin Claude.
2. Todo caminho declarado nos manifestos (components do plugin, `source` do
   marketplace) existe no repo.
3. `.mcp.json` contém exatamente o servidor `carteira`, comando `uvx`, env
   com referência `${WALLET_ID}` e nenhum literal numérico de carteira.
4. Nenhum asset contém escrita direta a `memory.json` nem a palavra-chave de
   escrita sem a co-presença de instrução de confirmação (checagem estática
   por padrões nos `.md`/`.sh`).
5. Nenhum asset contém emoji (constituição estilo §5).
