# DT-009: Dependências indiretas flutuam na instalação do usuário

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-26
**Origin**: revisão final da 0.5.0, ciclo 1 (`reports/sdd-final-review/0.5.0/cycle-1-20261125-2016.md`, achado N2)
**Related**: [ADR-0001](../adrs/0001-platform-and-storage-choices.md) (emenda de 2026-11-26), [ADR-0012](../adrs/0012-integracao-automatica-de-clientes.md), `plugin/.claude-plugin/plugin.json`

---

## Debt

O `uv.lock` não vale para quem instala o produto. O plugin roda `uvx` com a versão exata do pacote, mas as dependências indiretas são resolvidas na máquina do usuário, pela versão compatível mais nova no momento da instalação. Só `fastmcp`, `httpx` e `filelock` são fixas.

## Cause

É o comportamento do `uvx` com um pacote publicado no PyPI: ele usa os metadados do pacote, e não o arquivo de trava do repositório. O projeto fixa apenas as dependências diretas.

## Impact

- O usuário pode receber versões indiretas que o CI nunca testou, inclusive publicadas há poucas horas.
- A regra dos 7 dias e o `pip-audit` do CI protegem o ambiente de desenvolvimento, e não a instalação do usuário.
- A frase do ADR-0012 de que o que roda é exatamente o que foi instalado vale só para o pacote principal.

## Interim handling

- Dependências diretas fixadas com `==`.
- O job `verify` instala a versão publicada do PyPI em três sistemas, com a resolução que o usuário teria naquele momento.
- O `live.yml` semanal avisa se o produto quebrar, mas roda com o `uv.lock`, não com a resolução do usuário.

## How to pay

1. Verificar na documentação oficial do `uv` o que o `uvx` permite para limitar a resolução (por exemplo, um corte por data de publicação nos argumentos do plugin, ou um arquivo de restrições).
2. Comparar com a alternativa de fixar as transitivas nos metadados do pacote, e o custo de manter isso.
3. Decidir o caminho. Se mudar a forma de distribuição, registrar em ADR.
4. Implementar com teste e resolver com `/tech-debt resolve DT-009`.

## Revisit trigger

Subir para High se uma dependência indireta tiver aviso de segurança ou publicação comprometida, ou se uma instalação quebrar por causa de uma versão indireta nova.
