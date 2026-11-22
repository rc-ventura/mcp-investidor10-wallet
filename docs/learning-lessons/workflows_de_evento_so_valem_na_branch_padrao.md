# Workflows de evento só valem na branch padrão: `promote.yml` e `live.yml` não rodam antes da primeira promoção

**Context:** Lote 7 da spec 005 (`spec-005/us6-promocao`). Ao escrever o `promote.yml` (promoção automática por `workflow_run`), o `live.yml` (alarme semanal da API) e o `dependabot.yml`, o checkpoint do lote pedia o `dry-run` do `promote.yml` e o disparo manual do `live.yml` ainda dentro do lote. A documentação do GitHub ("Events that trigger workflows") diz que `workflow_run`, `schedule` e `workflow_dispatch` só disparam com o workflow existente na **branch padrão**, que aqui é `main`. Como `main` só recebe versões publicadas (ADR-0020), nenhum desses workflows existe lá antes da promoção da 0.4.0.
**Date:** 2026-11-14
**Future intent:** Ao desenhar qualquer automação que dependa de `workflow_run`, `schedule` ou `workflow_dispatch` num repositório cuja branch padrão fica atrás do trabalho, planejar desde o início como validá-la e quem a executa até ela chegar à branch padrão.

---

## O que dispara onde

| Gatilho | Onde o workflow precisa existir | Consequência neste projeto |
|---|---|---|
| `push` e `pull_request` | na branch/ref do evento | `ci.yml` roda em `develop` e nos pedidos, como previsto |
| `workflow_run` | na branch padrão (`main`) | `promote.yml` não reage ao `Release` concluído até estar em `main` |
| `schedule` | na branch padrão (`main`) | `live.yml` não roda toda segunda-feira até estar em `main` |
| `workflow_dispatch` | na branch padrão (`main`) | o disparo manual do `live.yml` e do `promote.yml` (modo `dry-run`) só existe depois |
| Dependabot | configuração lida na branch padrão (conforme `docs/RELEASING.md`) | `dependabot.yml` só vale depois de chegar a `main` |

Além disso, o `head_branch` de um `workflow_run` disparado por tag não é definido pela documentação. Por isso o `plan_promotion.py` tem `--sha`: acha a tag final no commit do release em vez de confiar no nome da branch do evento.

---

## O ciclo que isso cria

```
develop ──(lote 7 mergeado)──> promote.yml, live.yml, dependabot.yml existem só em develop
   │
   └─ tag v0.4.0 ──> Release publica ──> promote.yml NÃO dispara (não está em main)
                                           │
                                           └─> promoção da 0.4.0 à mão:
                                               plan_promotion.py --tag v0.4.0 --apply
                                               └─> promote/v0.4.0 ──> main-gate ──> merge (mantenedor)
                                                                        │
                                                                        └─> workflows passam a valer
```

A primeira promoção é, portanto, a que leva os workflows para `main`. Ela não pode ser feita por eles.

---

## Como ficou no projeto

- **Checkpoint do Lote 7 revisado (12/11/2026):** o `dry-run` do `promote.yml` e o disparo manual do `live.yml` passam para depois da promoção da 0.4.0 (T091/T092). No lote, o `dry-run` foi validado chamando `scripts/plan_promotion.py` direto, que é a lógica que o workflow executa.
- **Promoção da 0.4.0 à mão:** `python3 scripts/plan_promotion.py --tag vX.Y.Z --apply`, descrita na seção "Promoção à mão" de `docs/RELEASING.md`, que também registra a limitação no topo.
- **O que fica coberto por teste dentro do lote:** `tests/contract/test_release_workflows.py` e `tests/contract/test_release_consistency.py` conferem o conteúdo dos workflows (gatilhos, permissões, chamada ao script) e do `dependabot.yml`, mas não provam que o GitHub os dispara. A prova de que disparam é o `dry-run` e o `live.yml` manual depois de chegarem a `main`.

---

## Limites

- Esta lição descreve o que a documentação do GitHub afirma e o que foi lido e conferido em 12/11/2026. O comportamento do Dependabot em relação à branch padrão está registrado em `docs/RELEASING.md`; vale reconferir na documentação oficial de opções do Dependabot se a decisão depender dele.
- Mudar a branch padrão para `develop` evitaria o problema, mas desfaz a premissa do ADR-0020 de que o usuário do Desktop recebe `main` (verificação pendente 1 do ADR).

---

## Relation to ADRs and next steps

- **ADR-0020**, emenda de 14/11/2026: a primeira versão final é promovida à mão; o passo 4 e a automação só valem depois.
- **ADR-0005**: o `live.yml` é o alarme semanal de mudança da API e só passa a rodar quando chegar a `main` (emenda de 14/11/2026).
- **Próximos passos:** depois da promoção da 0.4.0, rodar o `dry-run` do `promote.yml` e disparar o `live.yml` manualmente (T091/T092), e registrar o resultado em `docs/RELEASING.md` (item 4 da seção de promoção à mão). O `--apply` da 0.4.0 é o passo de T091; o T092 repete o roteiro contra o marketplace em `main`.
