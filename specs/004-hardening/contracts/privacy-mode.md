# Contract — modo privacidade (`WALLET_MASK_VALUES`)

Cobre FR-009…FR-015. Allowlist derivada do payload real (probe só de chaves
e tipos, 2026-10-27, research D8).

## Ativação

- Só por ambiente do processo (`WALLET_MASK_VALUES`); nenhuma tool tem
  parâmetro de privacidade, e o schema de entrada das tools não muda.
- Valores: ver [data-model.md](../data-model.md#configuração-do-processo).
  Inválido → exit 1 com:
  `WALLET_MASK_VALUES=<valor> inválido: use 1/true/yes/on para ligar ou 0/false/no/off para desligar. Corrija o ambiente e reinicie o servidor.`
- Ligado → uma linha em stderr no startup:
  `Modo privacidade ativo: montantes em reais e quantidades não serão enviados ao modelo.`

## Comportamento por tool

| Tool | Modo ligado |
|---|---|
| `get_wallet_summary` | `data` reduzido à allowlist A; envelope com `privacy` |
| `get_wallet_allocation` | cada item da lista reduzido à allowlist B; envelope com `privacy` |
| `get_wallet_positions` | topo reduzido à allowlist C; cada linha de `data.data` reduzida à allowlist D; envelope com `privacy` |
| `get_patrimony_history` | erro `privacy_mode_unavailable` **sem chamar a fonte** |
| `get_earnings` | erro `privacy_mode_unavailable` **sem chamar a fonte** (a validação de datas continua antes, para `invalid_params` seguir igual) |
| `get_asset_quote` | inalterada |
| memória, alertas, `get_session_context` | inalteradas |

Erros da fonte (`source_unavailable` etc.) passam inalterados — não contêm
valores.

### Allowlists

- **A — summary**: `type`, `variation`, `profit_twr`, `profit_twr_12m`, `currency`
- **B — allocation (item)**: `name`, `type`, `percent`
- **C — positions (topo)**: `total`, `draw`, `truncated`
- **D — positions (linha)**: `id`, `tickerable_id`, `ticker`, `ticker_name`,
  `ticker_type`, `currency`, `url`, `image`, `country`, `iso_alpha_2`,
  `segment`, `fii_type`, `percent_wallet`, `percent_ideal`, `buy`,
  `avg_price`, `user_avg_price`, `avg_price_treasure`, `current_price`,
  `current_price_treasure`, `target_price`, `appreciation`,
  `weighted_return`, `profitability`, `yoc`, `dy`,
  `dividend_yield_last_5_years`, `payout`, `p_l`, `p_vp`, `roe`,
  `net_margin`, `gross_margin`, `profit_1`, `profit_7`, `profit_30`,
  `profit_365`, `rating`, `raw_rating`, `avg_rating`, `raw_avg_rating`,
  `checklist_rate`, `graham`, `bazin`, `vacancy`, `quotes_count`,
  `shareholders`, `net_worth`, `last_yield`, `equity_per_share`,
  `capitalization`, `is_calculating_rentability`

Tudo que não está na lista é omitido, inclusive campos que a fonte venha a
adicionar (FR-011). Campo permitido com valor aninhado (objeto ou lista) é
omitido e listado em `privacy.omitted`: a allowlist só vale para valores
escalares (emenda 2026-10-28, ADR-0015).

## Marcador

```json
"privacy": {"masked": true, "omitted": ["<campo>", "..."]}
```

Presente só com o modo ligado e só nas 3 tools mascaradas. `omitted` =
nomes removidos nesta resposta, ordenados, sem repetição.

## Docstrings (modelo, inglês)

As 3 tools mascaradas ganham: "When the envelope has `privacy.masked`
true, the operator withheld monetary amounts and quantities: work with the
percentages and ratios provided and never estimate or reconstruct the
withheld values." `get_patrimony_history` e `get_earnings` ganham a
menção ao erro `privacy_mode_unavailable`.

## Testes

- fixture com payload real anonimizado de cada endpoint (todas as chaves do
  probe, valores sintéticos);
- SC-003: com o modo ligado, nenhuma chave da lista de omitidos aparece em
  nenhuma resposta e nenhum valor numérico da fixture associado a esses
  campos aparece serializado;
- campo desconhecido injetado na fixture → ausente da resposta e presente
  em `omitted`;
- modo desligado → respostas idênticas às de hoje (sem `privacy`).
