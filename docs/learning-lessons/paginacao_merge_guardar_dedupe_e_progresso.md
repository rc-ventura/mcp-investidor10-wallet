# Endpoints paginados podem ignorar `start`: proteja o merge com dedupe e guarda de progresso

**Context:** Descoberto no SDD Final Review ciclo 3 (2026-10-17): a QA reproduziu que `get_wallet_positions` duplicava linhas quando a fonte devolvia a mesma página para `start=0` e `start=50` — o merge resultava em 100 linhas (50 únicas) com `total=60`, dobrando a contagem de ativos (risco ao SC-002). A fonte real pagina corretamente, mas o cliente confiava cegamente em `start`. A correção entrou no ciclo 3 e foi registrada no ADR-0003 §2.
**Date:** 2026-10-17
**Future intent:** Aplicar o mesmo padrão de guarda a qualquer novo endpoint paginado (e revisitar a lição se a fonte live um dia confirmar o comportamento ignorando `start`).

---

## Mental Model: paginação como coleção de identidades, não de páginas

O erro clássico é tratar o merge como concatenação de páginas (`rows.extend(page["data"])`) confiando que `start` avança. A página é **evidência**, não verdade: o servidor pode ignorar `start`, repetir linhas ou mudar a ordem.

```
          página 1 (start=0)        página 2 (start=50)
fonte ──► [T0..T49]           ──► [T0..T49]  (ignorou start)
               │                      │
               ▼                      ▼
merge ingênuo: T0..T49 + T0..T49 = 100 linhas, total reivindicado 60  ✗
merge guardado: dedupe por identidade → 50 únicas, para sem progresso  ✓
```

A guarda tem três camadas:

| Guarda | O que detecta | Sem ela |
|---|---|---|
| Dedupe por identidade (ticker; fallback linha inteira serializada) | páginas repetidas/sobrepostas | contagem dobrada de ativos |
| Parada sem progresso (`added == 0`) | fonte que ignora `start` com página cheia | loop infinito ou duplicação |
| Parada por página curta / `total` atingido | fim real dos dados, `total` ausente ou mentiroso | truncamento ou loop |

E o `total` mesclado deve ser **derivado do que foi coletado** (`len(rows)`), nunca do valor declarado pela fonte — senão o payload afirma 60 linhas contendo 50.

## Detalhe técnico (wallet_client.py:274-330)

```python
seen: set = set()
rows: list = []
while True:
    start = len(rows)  # avança pelo que REALMENTE coletamos
    envelope = await self.request(...)
    page = envelope["data"]
    ...
    added = 0
    for row in page["data"]:
        ticker = row.get("ticker") if isinstance(row, dict) else None
        identity = (
            f"ticker:{ticker}"
            if ticker
            else json.dumps(row, sort_keys=True, default=str)
        )
        if identity not in seen:
            seen.add(identity)
            rows.append(row)
            added += 1
    if (
        added == 0
        or len(page["data"]) < page_size
        or (total is not None and len(rows) >= total)
    ):
        break
merged["total"] = len(rows)  # nunca reivindica mais linhas do que data contém
```

## Exemplos no projeto

### 1. Fonte ignora `start` (teste `test_positions_dedupe_when_source_ignores_start`)

Mesma página de 50 linhas devolvida duas vezes, `total=60`: resultado = 50 únicas, `total` mesclado = 50.

### 2. Sobreposição parcial (teste `test_positions_dedupe_overlapping_pages`)

Página 2 devolve `T40..T89` (10 repetidas + 40 novas): resultado = 90 únicas, cada ticker exatamente uma vez.

### 3. Classe maior que o teto antigo (teste `test_positions_collects_beyond_old_thousand_row_cap`)

1050 posições coletadas integralmente — o teto fixo de 20 páginas foi removido em favor das guardas de progresso.

## Relation to ADRs and next steps

- **ADR-0003 §2** — registra a semântica oficial do merge (dedupe, guarda de progresso, `total` honesto).
- Próximo passo: se um endpoint novo paginado aparecer (ex.: detalhe de proventos por ativo, learning lesson `earnings_list_detalhe_proventos_por_ativo`), reusar este padrão em vez de um merge ingênuo.