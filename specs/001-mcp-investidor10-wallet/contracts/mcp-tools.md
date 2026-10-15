# Contratos — Tools MCP (19 tools)

Servidor `investidor10-wallet`, transport stdio. Convenções gerais:

- **Envelope de dados (tools de API)**: toda tool que consulta a fonte Investidor10 retorna `{ "cached": bool, "fetched_at": str (ISO-8601), "data": <payload> }`. O agente MUST informar ao usuário quando `cached=true` e a defasagem conhecida da fonte (~15 min B3).
- **Erros**: falhas retornam `{ "error": { "code": str, "message": str } }` — nunca exceção crua nem valores fabricados. Códigos: `source_unavailable` (API fora/timeout), `unexpected_format` (schema mudou), `invalid_asset_type`, `ticker_not_found`, `invalid_params`, `memory_unavailable`, `not_found`.
- **Idioma**: docstrings e mensagens de código em inglês (decisão do usuário, 2026-10-10); a interação com o usuário permanece em pt-BR conforme a spec.

## A. Tools de dados da carteira e mercado (6)

### `get_wallet_summary() -> dict`
Patrimônio, valor aplicado, variação, rentabilidade total e 12M da carteira configurada.
Fonte: `GET /summary/metrics/{WALLET_ID}?type=without-earnings&raw=1`.
`data`: payload cru da fonte.

### `get_wallet_allocation() -> dict`
Alocação por ativo e por classe.
Fonte: `GET /summary/donutchart/{WALLET_ID}/all?groupBy=ticker`.
`data`: payload cru da fonte.

### `get_wallet_positions(asset_type: str) -> dict`
Posições detalhadas de uma classe. `asset_type ∈ {Ticker, Fii, EtfInternational, Treasure, Crypto}` (qualquer outro → `invalid_asset_type` com a lista válida).
Fonte: `GET /summary/actives/{WALLET_ID}/{asset_type}?raw=1&api_version=v2&start=0&length=50&order_column=equity_total&order_dir=desc`.
`data`: lista de posições (PM, cotação, equity, rentabilidade, `% wallet`, `% ideal`, indicadores, flag `buy`). Classe sem posições → `data: []` (não é erro).

### `get_patrimony_history(months: int) -> dict`
Evolução mensal do patrimônio (aplicado vs ganho de capital). `months` inteiro > 0 (ex.: 12, 24, 60); inválido → `invalid_params`.
Fonte: `GET /summary/barchart/{WALLET_ID}/{months}/all`.

### `get_earnings(start_date: str | None = None, end_date: str | None = None) -> dict`
Proventos no período. Datas `YYYY-MM-DD`; omitidas → últimos 12 meses. `start_date > end_date` → `invalid_params` sugerindo correção (edge case da spec — nunca retorno vazio silencioso por data invertida).
Fonte: `GET /earnings/total-period/{WALLET_ID}?start_date=...&end_date=...`.

### `get_asset_quote(ticker: str) -> dict`
Cotação e fundamentos de um ticker (da carteira ou não): preço, variação dia/12M, Graham, Bazin, P/L, P/VP, DY, setor. Ticker é normalizado (upper/trim). Inexistente → `ticker_not_found`.
Fonte: `GET /api/rest/assets/tickers/{ticker}`.

## B. Tools de memória e alertas (13)

### `get_session_context() -> dict`
**Chamar obrigatoriamente no início de cada sessão.** Bootstrap determinístico:
1. Carrega digest da memória: objetivo da carteira, teses (por ticker), regras, decisões pendentes, insights recentes.
2. Para cada alerta `active`, consulta a cotação atual (via cache) e avalia a condição; os satisfeitos transitam para `triggered` (persistido com `triggered_at`/`triggered_price`).
Retorno: `{ "memory": {...digest...}, "triggered_alerts": [ {alerta + preço atual}... ], "memory_status": "ok" | "unavailable" }`.
Se `memory_status="unavailable"`, o agente MUST avisar o usuário e seguir em modo sem memória.

### `get_wallet_goal() -> dict` / `set_wallet_goal(text: str) -> dict`
Lê/atualiza o objetivo da carteira. `set` retorna o objetivo atualizado com `updated_at`.

### `save_thesis(ticker: str, text: str) -> dict`
Registra tese de investimento de um ativo. Retorna a tese criada (com `id`, `created_at`).

### `get_theses(ticker: str | None = None) -> dict`
Lista teses; com `ticker`, filtra por ativo. Retorna `{ "theses": [...] }` ordenadas por data.

### `save_rule(text: str) -> dict` / `get_rules() -> dict`
Registra/lista regras pessoais do usuário.

### `log_decision(kind: str, content: str, ticker: str | None = None, rationale: str | None = None) -> dict`
Registra recomendação do agente ou decisão do usuário. `kind ∈ {recommendation, user_decision}` (outro → `invalid_params`). `outcome` inicial = `pending`. Retorna a decisão criada (com `id`).

### `record_decision_outcome(decision_id: int, outcome: str, note: str | None = None) -> dict`
Grava o desfecho: `outcome ∈ {accepted, rejected, postponed}`. `decision_id` inexistente → `not_found`. Retorna a decisão atualizada.

### `log_insight(kind: str, fingerprint: str, summary: str) -> dict`
Registra insight/alerta já comunicado ao usuário (dedupe). Se `fingerprint` já existe, retorna `{ "already_logged": true, "existing": {...} }` sem duplicar — o agente usa isso para mencionar persistência em vez de repetir o alerta como novidade.

### `create_price_alert(ticker: str, direction: str, limit_price: float) -> dict`
Cria alerta de preço. `direction ∈ {above, below}`; `limit_price > 0`. Violações → `invalid_params`. Retorna o alerta criado (`state=active`). Disparo acontece exclusivamente em `get_session_context`.

### `list_price_alerts(state: str | None = None) -> dict`
Lista alertas; `state ∈ {active, triggered, cancelled}` filtra; omitido → todos.

### `cancel_price_alert(alert_id: int) -> dict`
Cancela alerta `active` (transição para `cancelled`). Alerta já `triggered`/`cancelled` ou inexistente → `not_found`/`invalid_params` conforme o caso.

## Mapeamento FR → tools

| FR | Tools |
|---|---|
| FR-001 | get_wallet_summary |
| FR-002 | get_wallet_allocation |
| FR-003 | get_wallet_positions |
| FR-004 | get_patrimony_history |
| FR-005 | get_earnings |
| FR-006 | get_asset_quote |
| FR-007 | get_wallet_positions + get_wallet_allocation (modelo cruza % atual vs ideal) |
| FR-008 / FR-009 | get_session_context + tools de escrita |
| FR-010 | log_decision + record_decision_outcome |
| FR-011 | create_price_alert + list_price_alerts + cancel_price_alert + get_session_context |
| FR-012 | get_asset_quote + get_wallet_positions (+ web search do próprio cliente) |
| FR-013 | env `WALLET_ID` (configuração, não tool) |
| FR-014 | cache em wallet_client (envelope `cached`/`fetched_at` evidencia ao agente) |
| FR-015 | transport stdio (arquitetura, não tool) |
| FR-016 | códigos de erro estruturados + modo degradado de memória |
