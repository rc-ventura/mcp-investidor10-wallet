# Contador declarado pela fonte não é limite de laço: validar `total` antes de parar a paginação por ele

**Context:** O `get_positions` já tinha dedupe, guarda de progresso e teto de páginas (lição `paginacao_merge_guardar_dedupe_e_progresso`). Mesmo assim, a revisão final da spec 004 (ciclo 4) mostrou que ele confiava no `total` declarado: qualquer `int` virava limite. Com `total=0`, negativo ou menor que a primeira página cheia, `len(rows) >= total` parava na página 1 e `len(rows) < total` dava falso. Resultado: `truncated: false` sobre uma lista parcial, exatamente o que o sinal existe para marcar.
**Date:** 2026-10-29
**Future intent:** Todo número que a fonte declara sobre a própria resposta (total, contagem, próxima página) é tratado como dado a validar, nunca como verdade que encerra um laço ou garante completude.

---

## Mental Model

A guarda de merge protege as **linhas**. Ela não protege o **metadado** que decide quando parar. São camadas diferentes:

| Camada | Pergunta | Guarda |
|---|---|---|
| linhas | "esta linha é nova?" | dedupe por ticker |
| progresso | "a página trouxe algo novo?" | `added == 0` → para |
| recurso | "já fui longe demais?" | `MAX_POSITION_PAGES` → para + `truncated` |
| **contador** | "o total declarado é plausível?" | só `int > 0`; descartado se as linhas o superam |
| **contador entre páginas** | "outra página declarou mais?" | vale o maior total válido; nunca diminui |

Regra prática: um contador que a própria resposta contradiz (mais linhas únicas do que o total) já se provou errado. Descarte e deixe as outras guardas decidirem. Re-adotar o mesmo valor de uma página seguinte é inofensivo, porque ele é descartado de novo na mesma iteração.

Validar o **formato** do contador não basta: ele também precisa ser **consistente entre páginas**. O ciclo 5 da revisão achou o caso irmão: adotar o total só da primeira página (`total is None`) ignorava uma página 2 que declarasse mais, e a coleta parava no total antigo com `truncated: false`. Por isso cada página pode elevar o total, e uma declaração menor nunca o reduz.

---

## Como ficou no código

- `wallet_client.get_positions` adota `total` só se `type(...) is int and total > 0`, fica com o maior entre as páginas, e o zera para `None` quando `len(rows) > total`.
- `test_positions_never_trust_an_impossible_declared_total` (0, -5, 3), `test_positions_flag_a_page_cap_stop_under_an_impossible_total` e `test_positions_adopt_a_larger_total_declared_by_a_later_page`.

---

## Relation to ADRs and next steps

- **ADR-0003**, emenda de 29/10/2026 (ciclo 4).
- Vale para as próximas tools paginadas (ex.: `/entries/{id}/{seção}`): validar o contador antes do primeiro `break`.
