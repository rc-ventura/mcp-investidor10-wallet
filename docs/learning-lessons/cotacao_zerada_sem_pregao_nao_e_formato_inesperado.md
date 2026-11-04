# Cotação do dia zerada sem pregão não é formato inesperado: `variation_day.last_quotation` vem `0` com a B3 fechada

**Context:** Em 02/11/2026, às 08:21, o alerta de BBSE3 apareceu em `pending_check` com a mensagem de formato inesperado. A reprodução contra a fonte real mostrou que BBSE3, PETR4 e VALE3 falhavam do mesmo jeito: o servidor lia o preço em `variation_day.last_quotation`, e a fonte devolvia `0`.
**Date:** 2026-11-02
**Future intent:** Preço do dia igual a zero significa que não houve pregão (feriado, fim de semana ou antes da abertura), e não que a fonte mudou de formato. O servidor trata esse caso como indisponibilidade com motivo próprio e nunca substitui o preço por um mais antigo.

---

## O que a fonte devolve sem pregão

Resposta de `GET /assets/tickers/<ticker>` observada em 02/11/2026, às 08:21 (horário de Brasília), para três tickers da B3:

| Campo | Valor observado |
|---|---|
| `variation_day.last_quotation` | `0` (número, não texto) |
| `variation_day.max` e `min` | `null` |
| `variation_day.variation_money` e `variation_percent` | `0` |
| `currentQuotation` | texto com vírgula, por exemplo `"41,32"` (BBSE3) |
| `lastUpdateCurrentQuotation` | `"30/10/2026"` (último fechamento) |

Com pregão aberto, `last_quotation` traz o preço corrente (as fixtures dos testes usam texto, como `"57.45"`). O dia 02/11 costuma ser feriado de Finados na B3; isso vem do calendário de feriados, que não foi conferido na fonte nesta data.

## Como ficou no código

- `WalletClient.get_quote` levanta `MarketClosedError` (subclasse de `SourceError`, código `source_unavailable`) quando o preço do dia é zero. Preço negativo, ausente ou não numérico continua sendo `unexpected_format`.
- `get_asset_quote` devolve o envelope de erro com `source_unavailable` e uma mensagem que diz que não houve pregão. A dica genérica de "a fonte está fora do ar" não é anexada a esse caso.
- `get_session_context` mantém o alerta ativo e o lista em `pending_check` com o motivo `market_closed`. Nenhum código de erro novo entrou no conjunto fechado.
- `currentQuotation` (último fechamento) não é usado como preço: o alerta é terminal e não pode disparar sobre cotação de dias atrás (ADR-0017).

## Limites

- O cache guarda a resposta zerada pelo TTL (10 minutos). Uma consulta feita pouco antes da abertura pode continuar devolvendo "sem pregão" por até esse tempo.
- Mostrar o último fechamento, com a data, em `get_asset_quote` fica como evolução possível, e não foi decidido.
