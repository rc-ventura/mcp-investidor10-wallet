# Um relógio só por decisão de frescor: monotônico dentro do processo, relógio de parede só na fronteira

**Context:** A primeira versão do ADR-0017 (cotação vencida não dispara alerta) calculava a idade como "agora menos `fetched_at`" no relógio de parede, enquanto o cache decidia TTL e cache vencido com `time.monotonic()`. A revisão final da spec 004 (ciclo 3) mostrou que um relógio atrasado faz uma cotação vencida parecer fresca e dispara um alerta terminal com preço velho, justamente o que o ADR proibia.
**Date:** 2026-10-29
**Future intent:** Qualquer decisão que dependa da idade de um dado em cache usa a mesma idade monotônica do cache. `fetched_at` serve só para mostrar ao usuário.

---

## Mental Model

| Relógio | Para que serve | Para que não serve |
|---|---|---|
| `time.monotonic()` | medir idades e intervalos dentro do processo (TTL, cache vencido, timeout) | mostrar hora; comparar entre processos |
| relógio de parede (`datetime.now()`) | carimbar `fetched_at` para o usuário e para logs | decidir se algo está velho: NTP, ajuste manual e fuso fazem ele andar para trás |

A regra: **uma decisão, uma fonte de idade.** Se `request()` decide "vencido, sirvo o cache velho" pelo relógio monotônico, quem depois pergunta "isso está vencido?" tem que receber a mesma resposta, calculada do mesmo jeito.

---

## Como ficou no código

- `WalletClient.is_stale(envelope)` procura a entrada do próprio cache cujo `data` é o mesmo objeto do envelope e calcula `time.monotonic() - cached_at`, igual a `request()`.
- Envelope em cache sem entrada correspondente (descartada, ou vinda de outro cliente) tem idade desconhecida e conta como vencido: na dúvida, não dispara.
- O teste coloca `fetched_at` no futuro (relógio "atrasado") e envelhece a entrada no relógio monotônico. O resultado tem que ser "vencido".

---

## Relation to ADRs and next steps

- **ADR-0017**, emenda de 29/10/2026: correção do mecanismo e do trade-off.
- **ADR-0003**: o cache vencido continua servido com `fetched_at` explícito nas tools de consulta. Ali o relógio de parede é informação, não decisão.
