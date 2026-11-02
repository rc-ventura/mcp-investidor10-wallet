# Contract — tool `open_wallet_setup`, página de configuração e bloco `configuration`

Cobre FR-004 a FR-008, FR-011, FR-014, FR-015, FR-016. Esquema dos dados em
data-model.md §1 a §5.

## Tool `open_wallet_setup` (a 20ª)

```text
open_wallet_setup() -> dict
```

Sem parâmetros: nenhuma tool recebe link, credencial, carteira ou mascaramento.

Anotações MCP: `readOnlyHint=False`, `destructiveHint=False`,
`idempotentHint=True`, `openWorldHint=True`.

### Regras de uso na docstring (Constituição III, camada confiável)

1. Chamar quando `get_session_context` ou uma tool de carteira indicar
   configuração pendente ou acesso recusado, ou quando o usuário pedir para
   trocar o link ou o mascaramento.
2. Pedir ao usuário para colar o link na página, nunca na conversa.
3. Se o usuário colar o link na conversa, não repetir nem reutilizar o valor.
4. Depois que o usuário disser que salvou, conferir o bloco `configuration` de
   `get_session_context`.

### Respostas de sucesso (sem `isError`)

| `status` | Quando | Campos |
|---|---|---|
| `opened` | navegador acionado | `message` pedindo para preencher a página e avisar quando salvar |
| `already_open` | página da mesma sessão ainda válida | `message`; o navegador é acionado de novo |
| `open_manually` | o navegador não pôde ser acionado | `setup_url` (endereço com token de uso único e prazo de 10 minutos), `terminal_alternative` (`mcp-investidor10-wallet configure`), `message` |

O token só vai na resposta em `open_manually`. O `setup_url` não dá acesso a
nenhum dado da carteira: serve só para enviar o formulário.

### Erro

Falha ao abrir a porta local (por exemplo, restrição do sistema): código
`setup_unavailable` (contracts/error-envelope.md), que aponta `configure` no
terminal.

## Página de configuração

Regras de segurança em research D4; sessão em data-model.md §5.

**Campos:** link da carteira (`type=password`, com opção de mostrar) e
mascaramento (liga/desliga), com o texto do que preserva (percentuais, alocação,
fundamentos) e do que esconde (valores em reais, histórico de patrimônio).

**Resultados de um envio:**

| Situação | A página mostra | Grava? |
|---|---|---|
| Válido e sem carteira diferente | Resumo: modo, mascaramento, ID mascarado; pede para voltar à conversa | Sim (`source` `setup_page`) |
| Carteira diferente da atual, sem confirmar | Atual e nova mascaradas, aviso de que a memória foi escrita para a atual, botão de confirmar | Não, até confirmar |
| Só mudou o mascaramento ou a credencial da mesma carteira | Resumo | Sim |
| Mesmos valores | "Nada mudou" | Não (idempotente) |
| Link não interpretável | Quais formas valem | Não |
| Acesso recusado | Causa (restrita sem link válido, ou privada) e o que fazer no site | Não |
| Carteira inexistente | Conferir o link | Não |
| Fonte indisponível | Tentar de novo depois | Não |
| Falha ao gravar | Causa e `configure` como alternativa | Não |
| Modo público | Aviso de que é indexável e que a restrita é a recomendada, junto do resumo | Sim |

Depois de gravar, ou ao vencer, a página encerra e o token deixa de valer.

Textos da página em PT-BR (ADR-0009, mensagem ao operador). Nenhuma resposta da
página repete o link nem a credencial.

## Bloco `configuration` em `get_session_context`

Sempre presente; nunca bloqueia o resto do contexto (a memória carrega mesmo
sem carteira).

```json
{"configuration": {"status": "pending", "reason": "missing",
  "next_action": "Call open_wallet_setup so the user can configure the wallet on the local page, before any wallet analysis."}}
```

```json
{"configuration": {"status": "configured", "mode": "restricted",
  "mask_values": false, "wallet": "…42", "origin": "file"}}
```

A docstring de `get_session_context` ganha a regra: com `status: "pending"`,
conduzir a configuração antes de qualquer análise da carteira.

## Testes de contrato

- schema: `open_wallet_setup` sem parâmetros; nenhuma tool do servidor tem
  argumento de link, credencial, carteira ou mascaramento;
- os três `status`, com o navegador simulado, e `setup_unavailable` com a porta
  local indisponível;
- a página: cada linha da tabela de resultados, provocada de verdade;
- segurança: só `127.0.0.1`; sem token, token usado, token vencido, `Host` ou
  `Origin` errados recusados sem gravar; corpo do envio fora de logs;
- nenhuma resposta de tool contém o ID completo, a credencial ou a URL do link
  (SC-009);
- a configuração gravada vale na chamada seguinte, no mesmo processo, sem
  reinício, e em outro processo depois da troca do arquivo.
