# Contract — erros das tools (emenda: 12 para 15 códigos)

Emenda o contrato da spec 004 (`specs/004-hardening/contracts/error-envelope.md`)
e o ADR-0014. Forma no protocolo, ponto único de emissão e testes de
contrato não mudam: `isError=true`, `structuredContent = {"error": {"code",
"message"}}` e o mesmo JSON em `content[0]`.

## Códigos novos

| Código | Origem | Tentar de novo? | Próxima ação nomeada na `message` |
|---|---|---|---|
| `wallet_not_configured` | tool de carteira (`get_wallet_summary`, `get_wallet_allocation`, `get_wallet_positions`, `get_patrimony_history`, `get_earnings`) em estado pendente | não, até configurar | chamar `open_wallet_setup` para o usuário configurar a carteira na página |
| `access_denied` | fonte respondeu 3xx, 401 ou 403 para a carteira | não com a mesma configuração | chamar `open_wallet_setup` para o usuário informar o link restrito atual (ou deixar a carteira pública) |
| `setup_unavailable` | `open_wallet_setup` não conseguiu abrir a porta local | não nesta máquina | pedir ao usuário para rodar `mcp-investidor10-wallet configure` no terminal; nunca pedir o link na conversa |

## Mudanças em códigos existentes

- `source_unavailable`: deixa de cobrir 401/403 do proxy da carteira (agora
  `access_denied`); a dica "check WALLET_ID" passa a ser "check the wallet
  link with open_wallet_setup".
- `unexpected_format`: deixa de ser emitido para respostas 3xx.

## Mensagens-alvo (inglês, ADR-0009)

- `wallet_not_configured`: "No Investidor10 wallet is configured yet. Call
  open_wallet_setup to open the local setup page, and ask the user to enter
  their wallet link there, not in this conversation. Do not invent wallet
  data."
- `access_denied`: "Investidor10 refused access to the configured wallet:
  it is restricted and the share link is missing or no longer valid, or it
  is private. Call open_wallet_setup so the user can enter the current
  restricted share link, or ask them to make the wallet public. Retrying
  will not help."
- `setup_unavailable`: "The local setup page could not start on this machine.
  Ask the user to run `mcp-investidor10-wallet configure` in a terminal. Do not
  ask for the wallet link in this conversation."

Nenhuma mensagem carrega o ID por extenso, a credencial ou a URL com
query.

## Testes de contrato

- um caso por código novo, provocado de verdade (estado pendente; resposta
  301 sem `Location` do proxy; porta local indisponível), afirmando `is_error`, o código e a tool
  nomeada na mensagem;
- regressão: resposta 301 real anonimizada nunca produz `unexpected_format`;
- resposta 3xx nunca entra no cache nem serve cache vencido.
