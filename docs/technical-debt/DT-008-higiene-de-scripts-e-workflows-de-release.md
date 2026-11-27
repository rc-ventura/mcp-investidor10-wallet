# DT-008: Higiene dos scripts e workflows de release

**Status**: Open
**Priority**: Low
**Date**: 2026-11-20
**Origin**: revisão final da spec 005, ciclo 1 (`reports/sdd-final-review/005/cycle-1-20261120-1004.md`, achados #36, #37 e #38, classe B)
**Related**: [lição sobre dígitos Unicode](../learning-lessons/digitos_unicode_isdigit_e_d_aceitam_alem_de_ascii.md), [ADR-0020](../adrs/0020-fluxo-de-branches-e-release.md), `scripts/check_release_tag.py:7`, `scripts/plan_promotion.py:9-10`, `scripts/check_promotion.py:13,53-58`, `.github/workflows/`

---

## Debt

Três endurecimentos pequenos ficaram para a 0.4.1:

- **`\d` nas expressões de tag e de referência** casa com dígitos Unicode (`check_release_tag.py:7`, `plan_promotion.py:9-10`, `check_promotion.py:13`). Trocar por `[0-9]` ou `re.ASCII`.
- **`published_in_index` aceita índice `http://`** (`check_promotion.py:53-58`). O padrão é `https://pypi.org`, então só seria explorável por `--index-url`. Exigir https, falhando fechado.
- **`actions/checkout` mantém `persist-credentials` no padrão** nos jobs de leitura (`ci`, `main-gate`, `live`, `release`). Definir `false` em todos, menos no `promote.yml`, onde o push precisa da credencial.

## Cause

Achados da revisão final do ciclo 1, classificados para a 0.4.1: a 0.4.0 já estava publicada. Os scripts não vão no wheel, mas a mudança passa por `develop`.

## Impact

Nulo hoje: a versão ainda precisa bater com `__version__`, os valores vão entre aspas no shell e o índice padrão é https. A regra da ADR-0010 §5 e a postura de menor privilégio dos workflows não estão totalmente cumpridas.

## How to pay

1. Testes primeiro: uma tag com dígito Unicode é recusada pelos três scripts, `--index-url http://...` falha, e um teste de contrato confere `persist-credentials: false` nos workflows, exceto no `promote.yml`.
2. Aplicar as três mudanças.
3. Entrar na 0.4.1, com ciclo próprio de revisão sobre o diff `v0.4.0..0.4.1`.
4. Resolver com `/tech-debt resolve DT-008`.

## Revisit trigger

Reavaliar se um dos scripts passar a receber tag ou URL de uma fonte que não seja o mantenedor.
