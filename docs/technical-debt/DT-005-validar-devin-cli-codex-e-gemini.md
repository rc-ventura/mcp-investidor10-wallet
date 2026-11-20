# DT-005: Validar o Devin CLI, o Codex, o Gemini CLI e o assistente real

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: spec 005, Lote 8, T085 e T086a ([tasks.md](../../specs/005-desktop-distribution/tasks.md), [validation-matrix.md](../../specs/005-desktop-distribution/validation-matrix.md))
**Related**: [DT-001](./DT-001-verificar-devin-desktop-real.md), [DT-004](./DT-004-validar-claude-code-no-macos-e-linux.md), T086, ADR-0012

---

## Debt

Nenhuma instalação real em máquina limpa foi feita nestes clientes:

- Devin CLI: servidor, plugin, skills, guardião e persona.
- Codex pela interface interativa, com o plugin fixado na tag (`--ref`).
- Gemini CLI, com a extensão fixada na tag (`--ref`).
- O assistente de instalação real nos roteiros V2.2 e V2.4 da spec 003.
- T086a: avaliar se o plugin com servidor inline pode substituir o registro `mcp add` mais o plugin de comportamento nesses três clientes.

## Cause

Corte deliberado de escopo (20/11/2026): validação manual só do macOS com o Claude Desktop. Na máquina do mantenedor, o Devin CLI já tem o plugin `investidor10-carteira v0.4.0rc4` e um servidor `carteira` de desenvolvimento em `.devin/mcp_config.local.json`; não é máquina limpa.

## Impact

- Esses clientes não podem ser anunciados como validados (T086); o README precisa dizer que o suporte é pelo assistente de instalação, testado por testes automatizados e não por instalação real.
- A T086a não tem como ser decidida com evidência: o gate do Lote 8 pede a decisão "unificado ou mantido, com a causa".
- Fica a colisão de dois caminhos de registro (servidor mais plugin) observada no Devin (ADR-0012) sem prova de que o fluxo atual a evita.

## Interim handling

- Células como `pendente`, ligadas a este débito.
- Proposta, a confirmar com o mantenedor: registrar a T086a como "mantido" (o assistente continua a registrar o servidor e instalar o plugin de comportamento, como no ADR-0012), com a causa "não validado em máquina limpa", sem anunciar unificação nem mudar o README sobre isso.
- Para o Devin CLI, só comandos de leitura (`devin mcp list`, `devin plugins list`) e `install --dry-run` com `HOME` temporário e a carteira fictícia.

## How to pay

1. Para cada cliente, numa máquina limpa ou com `HOME` isolado, rodar o `install --clients <cliente>` da versão publicada e conferir: 20 tools, skills, guardião, persona e um só caminho de registro.
2. Rodar os roteiros V2.2 e V2.4 da spec 003.
3. Preencher a `validation-matrix.md` e decidir a T086a (testes primeiro, se unificar).
4. Resolver com `/tech-debt resolve DT-005`.

## Revisit trigger

Reavaliar quando a promoção da 0.4.0 estiver feita: o instalador passa a ser executado por usuários reais, e qualquer relato nestes clientes sobe a prioridade para High.
