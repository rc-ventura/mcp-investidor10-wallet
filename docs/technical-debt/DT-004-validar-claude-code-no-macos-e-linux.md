# DT-004: Validar o Claude Code pelo assistente de instalação (macOS e Linux)

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: spec 005, Lote 8, T085 ([tasks.md](../../specs/005-desktop-distribution/tasks.md), [validation-matrix.md](../../specs/005-desktop-distribution/validation-matrix.md))
**Related**: [DT-003](./DT-003-validar-o-produto-no-windows.md), T086, ADR-0018, ADR-0012

---

## Debt

O roteiro S7 (`uvx mcp-investidor10-wallet install --clients claude`) não foi rodado de verdade no Claude Code, e o Linux não foi testado em nenhum cliente:

- S7 no macOS: o instalador real nunca rodou. A única evidência é parcial: o registro antigo `carteira` foi removido à mão e o `claude mcp list` mostrou um só servidor.
- Claude Code no Linux (a única célula Linux do roteiro S10).

## Cause

Corte deliberado de escopo (20/11/2026): o mantenedor validou à mão só o macOS com o Claude Desktop. Além disso, na máquina de desenvolvimento do mantenedor o plugin e um servidor local já estão instalados, então rodar o S7 ali trocaria uma configuração que funciona; um teste honesto pede máquina limpa ou um `HOME` isolado.

## Impact

- O caminho de migração de quem atualiza da 0.3.x pelo terminal (o instalador pergunta antes de remover o registro antigo, o marketplace da 0.3.x e a cópia local) não foi provado ponta a ponta. A promessa de "um só servidor, sem tools duplicadas" no Claude Code fica apoiada em testes unitários e de contrato, não em execução real.
- O Linux não pode ser anunciado como validado (T086).

## Interim handling

- Células como `pendente`, ligadas a este débito.
- O README e o `CHANGELOG.md` já descrevem a migração; a T086 acrescenta que o caminho do Claude Code pelo instalador não foi validado ponta a ponta.
- Antes de qualquer execução real na máquina do mantenedor, rodar `install --dry-run` e fazer cópia de `~/.claude.json`.

## How to pay

1. Numa máquina limpa (ou com `HOME` temporário), rodar `uvx mcp-investidor10-wallet@<versão> install --clients claude` e conferir: o plugin instalado na versão do tag, o `claude mcp list` com um só servidor (`plugin:investidor10-carteira:carteira`) e a pergunta antes de remover o registro antigo.
2. Repetir o roteiro de instalação no Linux.
3. Preencher a `validation-matrix.md`.
4. Resolver com `/tech-debt resolve DT-004`.

## Revisit trigger

Subir para High se um usuário relatar tools duplicadas no Claude Code depois de atualizar da 0.3.x.
