# API upstream tem detalhe de proventos por ativo — o MCP só expõe o total agregado

**Context:** Descoberto em sessão de análise de proventos (17/10/2026). O usuário pediu o detalhamento por ativo dos proventos de 2025; a tool `get_earnings` retornava apenas `{"sum": ...}`. Sondando os endpoints upstream do Investidor10 foi encontrado `/earnings/list/{wallet_id}`, que retorna a tabela completa de proventos (pagos + provisionados) com registro por pagamento.
**Date:** 2026-10-17
**Future intent:** Expor esse endpoint como uma nova tool (`get_earnings_detailed`) para suportar breakdown por ativo/tipo/data sem chamadas diretas fora do MCP.

---

## Mental Model: dois níveis de granularidade na mesma API

```
get_earnings (tool MCP)
        │
        ▼
/earnings/total-period/{id}?start_date=&end_date=
        └──► {"sum": N}   ← soma dos net_total do período (líquido)

(não exposto como tool)
        │
        ▼
/earnings/list/{id}
        └──► {"table": {"total": 171, "totalAmount": "R$ 7.044,08",
                        "data": [ {pagamento}, ... ]}}
             ← tabela completa, SEM filtro de período na query;
             inclui pagamentos futuros "Provisionado"
```

| Endpoint | O que retorna | Filtra por data? | Exposto no MCP? |
|---|---|---|---|
| `/earnings/total-period/{id}` | Só `sum` (líquido) | Sim (`start_date`/`end_date`) | Sim (`get_earnings`) |
| `/earnings/list/{id}` | Tabela por pagamento: ticker, qty, tipo, datas, bruto e líquido | Não — filtrar no cliente por `date_payment_original` | Não |

## Detalhe técnico do `/earnings/list/{id}`

Registro por pagamento (exemplo real, campos relevantes):

```json
{
  "ticker": "NEAR",
  "category": "ETFs Intern.",
  "type": "Dividendos",
  "qty": 12.68,
  "date_with": "03/02/2025",
  "date_payment": "06/02/2025",
  "month": "2025-02",
  "date_with_original": "2025-02-03",
  "date_payment_original": "2025-02-06T03:00:00.000000Z",
  "total_original": 14.3284,
  "net_total_original": 10.02988,
  "tickerable_type": "App\\Models\\EtfInternational"
}
```

Armadilhas e fatos verificados:

- **Provisionados poluem a lista**: pagamentos futuros vêm com `date_payment: "Provisionado"` e `date_payment_original` placeholder no ano 2126. Filtrar por `date_payment_original` dentro da janela desejada — nunca confiar no campo `date_payment` formatado.
- **`sum` do `total-period` = soma de `net_total_original`**: conferido em 2025 (R$ 2.943,68) e 2026 YTD (R$ 3.571,17) — batimento centavo a centavo. Para "quanto recebi", usar líquido; `total_original` é o bruto.
- **Gap bruto→líquido identifica retenção**: JSCP e "Rend. Trib." de ações B3 têm IR na fonte; ETFs internacionais (TFLO, NEAR, HYG, SCHD, SCHY, VTI) têm withholding tax de ~30%.
- **`type` + `category` distinguem natureza**: "Dividendos", "JSCP", "Rend. Trib." combinados com "Ações", "FIIs", "ETFs Intern." — permite segregar renda isenta de tributada.
- **`month` (`YYYY-MM`) já vem agrupado** — atalho para breakdown mensal sem parsear data.

## Exemplo de uso (agregação por ativo)

```python
rows = data["table"]["data"]
for r in rows:
    dp = r.get("date_payment_original") or ""
    if "2026-01-01" <= dp[:10] <= "2026-10-17":
        agg[r["ticker"]] += r["net_total_original"] or 0
```

## Próximos passos

- Adicionar `get_earnings_detailed(start_date, end_date)` ao MCP: chamar `/earnings/list/{id}` uma vez (sem paginação aparente na API — `table.total` traz tudo) e filtrar/agregar no cliente; retornar `{by_ticker, by_month, by_type, gross, net}`.
- Reusar o cache em memória existente — a lista completa é o mesmo payload para qualquer período, então uma única fetch serve múltiplas consultas de breakdown.
- Atualizar `data-model.md` e `contracts/mcp-tools.md` (a spec já previa "detalhamento por ativo/tipo/data" no modelo Provento — a implementação parou no agregado).
