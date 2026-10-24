# get_asset_quote só cobre ações da B3: FIIs, ETFs internacionais, cripto e tesouro retornam HTTP 410

**Context:** Descoberto em sessão de análise de carteira (15/10/2026) ao tentar buscar cotações de SCHE, VWO e IAUM para avaliar lacunas de diversificação internacional. A ferramenta `get_asset_quote` falhou com `source_unavailable` para todos — inclusive para SCHY, que consta na própria carteira.
**Date:** 2026-10-15
**Future intent:** Integrar uma fonte de dados especializada em ativos internacionais (candidata: Yahoo Finance) para cobrir os tipos que o endpoint atual não alcança.

---

## Mental Model: duas superfícies de API com coberturas diferentes

O `wallet_client.py` encapsula duas bases de URL distintas do investidor10.com.br, e cada uma enxerga um subconjunto dos tipos de ativo:

```
get_wallet_summary / get_wallet_allocation / get_wallet_positions
        │
        ▼
wallet_client ──► /wallet/api/proxy/wallet-app   (dados DA CARTEIRA)
                  cobre: Ticker, Fii, EtfInternational, Treasure, Crypto

get_asset_quote
        │
        ▼
rest_client ────► /api/rest/assets/tickers/{ticker}   (catálogo de ATIVOS)
                  cobre: apenas Ticker (ações B3)
                  410 Gone: Fii, EtfInternational, Treasure, Crypto
```

O erro não é "ticker inexistente" — é **seção da API não coberta**. No site, esses ativos vivem em rotas próprias (`/fiis/`, `/etfs-global/`, `/criptomoedas/`, `/tesouro-direto/`) que o endpoint REST `/assets/tickers/` não resolve.

## Cobertura verificada empiricamente

| Ticker testado | Tipo | Resultado |
|---|---|---|
| AXIA3, PETR4, VALE3, BBAS3, EGIE3, CMIG4 | Ação (Ticker) | ✅ 200 |
| MXRF11 | FII | ❌ HTTP 410 |
| SCHY, TFLO, NEAR, HYG, VTI, SCHD | ETF internacional (na carteira) | ❌ HTTP 410 |
| SCHE, VWO, IAUM, SPY, EEM | ETF internacional (fora da carteira) | ❌ HTTP 410 |
| BTC | Cripto | ❌ HTTP 410 |

## Detalhe técnico (wallet_client.py)

```python
REST_BASE_URL = "https://investidor10.com.br/api/rest"


async def get_quote(self, ticker: str) -> dict:
    normalized = (ticker or "").strip().upper()
    return await self.request(f"/assets/tickers/{normalized}")  # só ações
```

- O mapeamento de erro em `get_quote` só trata **404** → `ticker_not_found`. Tipos não cobertos retornam **410 Gone**, que vira `source_unavailable` genérico — a resposta de erro não deixa claro que o problema é o tipo de ativo, não o símbolo.
- Os dados de ETFs/FIIs/cripto/tesouro só aparecem via `get_wallet_positions` (endpoint da carteira), e apenas para ativos que o usuário já possui.

## Próximos passos

- Adicionar fonte internacional para cotações fora da B3 — candidata principal: **Yahoo Finance** (`yfinance` ou `query1.finance.yahoo.com/v8/finance/chart`), que cobre ETFs americanos, cripto e ADRs; alternativa: brapi.dev (cobre B3 + alguns internacionais).
- Rotear `get_asset_quote` por tipo de ativo: ação B3 → Investidor10 REST; demais tipos → fonte internacional.
- Mapear HTTP 410 para um código de erro semântico próprio (ex.: `asset_type_not_supported`) em vez de `source_unavailable`, para o agente não confundir seção não coberta com fonte fora do ar.
