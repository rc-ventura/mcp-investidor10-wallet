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
| `--mcp-only` | ausente | **escape do bundle**: registra apenas o servidor MCP; nenhum comando de instalação de plugin é executado |
| `--dry-run` | ausente | percorre detecção + validação, reporta o que faria ("registraria o servidor" + "instalaria o plugin"), não executa nada |
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
| Devin CLI | `devin mcp add -s user carteira -e WALLET_ID=<id> -- uvx mcp-investidor10-wallet` (flags verificadas em 2026-10-24 — learning lesson) | `devin mcp list` |
| Codex CLI | `codex mcp add carteira --env WALLET_ID=<id> -- uvx mcp-investidor10-wallet` | `codex mcp list` |
| Gemini CLI | `gemini mcp add -s user -e WALLET_ID=<id> carteira uvx mcp-investidor10-wallet` | `gemini mcp list` |

Alias fixo `carteira` em todos (sem underscores — Gemini).

## Bundle (padrão): instalação do plugin após o registro

Sem `--mcp-only`, após o registro do servidor em cada cliente detectado
(exceto os com status `failed`), o assistente executa os comandos nativos de
instalação do plugin (fontes canônicas do repositório):

| Cliente | Comandos executados (na ordem) |
|---|---|
| Claude Code | `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet` → `claude plugin install investidor10-carteira@investidor10` |
| Devin CLI | `devin plugins install rc-ventura/mcp-investidor10-wallet#plugin -y` |
| Codex CLI | `codex plugin marketplace add rc-ventura/mcp-investidor10-wallet` → `codex plugin add investidor10-carteira@investidor10` |
| Gemini CLI | `gemini extensions install https://github.com/rc-ventura/mcp-investidor10-wallet` |

- Falha na instalação do plugin não altera o código de saída do registro do
  servidor; vira linha `failed` no relatório com o erro resumido.
- As fontes canônicas exigem o repositório público no GitHub (pendência até
  o merge/push das branches da spec 003 — validação real do bundle gated
  nisso; em dev, os comandos equivalentes locais já foram validados).
- O Gemini instala a extensão pela raiz do repo; se a CLI não suportar a
  extensão em subpasta, essa linha vira instrução manual — questão aberta
  registrada no contrato do plugin (carga real pendente).

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