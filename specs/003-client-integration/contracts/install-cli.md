# Contract: subcomando `install` (spec 003)

Superfície de CLI do assistente de instalação. Mensagens em PT-BR envolvem
stdout/stderr e são parte do contrato (testes assertam trechos-chave), não
detalhes cosméticos.

## Invocação

```
mcp-investidor10-wallet install [opções]
```

Nenhum argumento posicional. `main()` despacha `argv[1] == "install"` antes
da inicialização do servidor; todo o resto permanece servidor MCP.

## Opções

| Flag | Default | Efeito |
|---|---|---|
| `--clients claude,devin,codex,gemini` | todos os detectados | restringe o alvo do registro; itens inválidos abortam com erro PT-BR |
| `--wallet-id <id>` | interativo (pergunta) | uso não-interativo (scripts, CI) |
| `--plugin` | ausente | ativa modo opt-in do plugin: imprime as instruções oficiais de instalação do plugin (Claude Code: `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet` + `/plugin install investidor10-carteira`; Devin CLI: instalação do plugin pela mesma origem) |
| `--dry-run` | ausente | percorre detecção + validação, reporta o que faria, não executa registro nenhum |
| `--yes` | ausente | pula confirmações intermediárias de rotina (mantém a pergunta do ID se `--wallet-id` ausente); **NÃO afeta a pergunta de colisão de alias abaixo** |

## Pré-condições verificadas na ordem

1. Runner `uv` presente na PATH → caso contrário erro PT-BR + instrução de
   instalação e exit 2.
2. `WALLET_ID` fornecido (flag ou resposta) e carteira válida/pública
   (validação via `wallet_client`) → erro PT-BR + instrução e exit 3.

## Comportamento por cliente (comando nativo, escopo user)

| Cliente | Comando executado | Detecção de existência |
|---|---|---|
| Claude Code | `claude mcp add carteira --scope user -- env WALLET_ID=<id> uvx mcp-investidor10-wallet` | `claude mcp list` |
| Devin CLI | `devin mcp add carteira -- env WALLET_ID=<id> uvx mcp-investidor10-wallet` (user scope; flag exata confirmada na implementação) | `devin mcp list` |
| Codex CLI | `codex mcp add carteira --env WALLET_ID=<id> -- uvx mcp-investidor10-wallet` | `codex mcp list` |
| Gemini CLI | `gemini mcp add -s user -e WALLET_ID=<id> carteira uvx mcp-investidor10-wallet` | `gemini mcp list` |

Alias fixo `carteira` em todos (sem underscores — Gemini).

## Protocolo de colisão de alias

Quando o alias `carteira` já está registrado no cliente (registro realizado
por este assistente ou por outra origem), o assistente **sempre pergunta
interativamente** em PT-BR — independentemente de `--yes`:

1. **Pular** (default, Enter): nada altera; status `skipped_present` no
   relatório com nota de que a entrada existente foi mantida.
2. **Atualizar**: o registro é refeito com a configuração atual deste
   assistente (o comando nativo de `add` reescreve a entrada do cliente);
   status `updated`.

Sem flag dedicada: a escolha é sempre situacional e por cliente, nunca
automatizada.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | sucesso (ao menos um cliente registrado/detectado-present) |
| 1 | nenhum cliente alvo detectado — relatório orienta (US1 AS4) |
| 2 | runner ausente |
| 3 | carteira inválida/privada |
| 4 | falha em todos os registros tentados |

## Relatório final (stdout, PT-BR)

Uma linha por cliente com seu status (`registered`/`updated`/
`skipped_present`/`skipped_absent`/`failed`) e a frase de conclusão indicando
reiniciar o(s) cliente(s). Em `--dry-run`, o relatório é prefixado com
"SIMULAÇÃO (nenhuma configuração foi alterada)".