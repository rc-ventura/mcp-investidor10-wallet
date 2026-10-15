# Data Model — 001-mcp-investidor10-wallet

Duas famílias de dados: **(A)** dados da carteira/mercado, de leitura, vêm da API Investidor10 e são repassados quase crus (passthrough) com metadados de cache; **(B)** memória do investidor, de escrita, persiste localmente em `memory.json`.

## A. Entidades de leitura (API Investidor10 — passthrough)

O servidor NÃO re-modela esses dados; repassa o JSON da fonte. Campos-chave consumidos pelo agente:

| Entidade | Origem | Campos-chave |
|---|---|---|
| Resumo da carteira | `/summary/metrics/{id}` | `applied` (valor aplicado), `equity` (patrimônio), `variation`, TWR total e 12M |
| Alocação | `/summary/donutchart/{id}/all?groupBy=ticker` | fatias por ativo/classe com percentuais |
| Posição | `/summary/actives/{id}/{Tipo}` | ticker, quantidade, `average_price`, cotação, `equity_total`, rentabilidade, `percent_wallet`, `percent_ideal`, P/L, P/VP, DY, ROE (quando aplicável), flag `buy` |
| Evolução patrimonial | `/summary/barchart/{id}/{meses}/all` | série mensal: aplicado acumulado + ganho de capital |
| Provento | `/earnings/total-period/{id}` | total do período + detalhamento por ativo/tipo/data |
| Cotação | `/api/rest/assets/tickers/{ticker}` | preço, variação dia/12M, Graham, Bazin, P/L, P/VP, DY, setor |

**Validações/regras**:
- Tipo de classe em posições: `Ticker | Fii | EtfInternational | Treasure | Crypto`; valor fora dessa lista → erro `invalid_asset_type`.
- Indicadores não aplicáveis por classe (ex.: P/L de FII) vêm ausentes da fonte e são omitidos — nunca inventados.
- Toda resposta de tool de dados é envelopada com metadados: `{ "cached": bool, "fetched_at": iso8601, "data": ... }`.

## B. Memória do investidor (`memory.json`)

### Schema (version 1)

```json
{
  "version": 1,
  "wallet_goal": {
    "text": "Aposentadoria: renda passiva de R$ X/mês",
    "updated_at": "2026-10-10T12:00:00-03:00"
  },
  "theses": [
    {
      "id": 1,
      "ticker": "PETR4",
      "text": "Tese: ciclo de capex contido + payout elevado...",
      "created_at": "2026-10-09T15:30:00-03:00",
      "updated_at": "2026-10-09T15:30:00-03:00"
    }
  ],
  "rules": [
    {
      "id": 1,
      "text": "Só compro ativo com flag buy positiva no Investidor10",
      "created_at": "2026-10-09T15:31:00-03:00"
    }
  ],
  "decisions": [
    {
      "id": 1,
      "date": "2026-10-05",
      "kind": "recommendation",
      "ticker": "PETR4",
      "content": "Reduzir concentração: 15,2% vs 8% ideal",
      "rationale": "Risco de concentração setorial em commodities",
      "outcome": "pending",
      "outcome_note": null,
      "outcome_at": null
    }
  ],
  "insights_log": [
    {
      "id": 1,
      "date": "2026-10-09",
      "kind": "concentration_alert",
      "fingerprint": "PETR4:15.2>8.0",
      "summary": "Alerta de concentração em PETR4 comunicado"
    }
  ],
  "alerts": [
    {
      "id": 1,
      "ticker": "PETR4",
      "direction": "below",
      "limit_price": 30.0,
      "created_at": "2026-10-09T16:00:00-03:00",
      "state": "active",
      "triggered_at": null,
      "triggered_price": null
    }
  ]
}
```

### Entidades e regras

- **Tese** (`theses`): tese de investimento por ativo. `ticker` uppercase obrigatório; múltiplas teses por ticker permitidas (histórico); `updated_at` muda em revisão. Regra de validação: texto não vazio.
- **Regra pessoal** (`rules`): regras globais do usuário (ex.: "DY mínimo 6%"). Sem ticker — aplicam à carteira toda.
- **Decisão/Recomendação** (`decisions`): `kind ∈ {recommendation, user_decision}`; `outcome ∈ {pending, accepted, rejected, postponed}` começando em `pending`; registrar `outcome` grava `outcome_at`. Serve ao FR-010 (nunca repetir recomendação recusada sem novo fundamento) e à avaliação histórica (SC-004).
- **Log de insights** (`insights_log`): dedupe de comunicações (SC-005). `fingerprint` = chave estável derivada do conteúdo do insight (ex.: `"{ticker}:{pct_atual}>{pct_ideal}"`); antes de comunicar, o agente verifica via tool se fingerprint já existe — se sim, menciona persistência em vez de reapresentar como novidade.
- **Alerta de preço** (`alerts`): ver máquina de estados abaixo.
- **Objetivo da carteira** (`wallet_goal`): um único texto livre, atualizável.

### Máquina de estados — Alerta de preço

```text
create ──► active ──condição satisfeita em get_session_context──► triggered
              │                                                    (terminal;
              └──cancel_price_alert────────────────────────────► cancelled
                                                                   não dispara)
```

Transições:
- `active → triggered`: grava `triggered_at` e `triggered_price` (preço observado no disparo). **Terminal** — nunca volta a disparar (SC-006: sem duplicados).
- `active → cancelled`: ação explícita do usuário. Terminal.

Avaliação da condição: `direction=below` dispara quando `preço_atual <= limit_price`; `direction=above` quando `preço_atual >= limit_price`.

### Regras de integridade do store

- IDs inteiros monotônicos por coleção (`max(id)+1`).
- Timestamps ISO-8601 com timezone local.
- Escrita atômica: serializa → grava em `memory.json.tmp` → `os.replace`.
- Arquivo ausente na primeira execução → cria schema vazio v1.
- JSON inválido → modo sem memória (ver research D6); backup `.broken-<timestamp>` antes de qualquer reescrita.
- `version` desconhecida (>1) → modo sem memória + aviso (recusa silenciosa de downgrade).
