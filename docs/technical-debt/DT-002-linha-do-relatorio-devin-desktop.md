# DT-002: Linha do relatório do assistente sobre o Devin Desktop

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: spec 005, Lote 8, T084 ([tasks.md](../../specs/005-desktop-distribution/tasks.md))
**Related**: [DT-001](./DT-001-verificar-devin-desktop-real.md), T083, `src/investidor10_wallet/installer/cli.py`, `src/investidor10_wallet/installer/clients.py`

---

## Debt

A task T084 pede uma linha no relatório do assistente de instalação que diga se o Devin Desktop foi coberto: pelo registro compartilhado, por caminho próprio (mecanismo nativo do app, com fonte) ou não suportado. Hoje o relatório não diz nada sobre o Devin Desktop.

## Cause

As três respostas previstas dependem do resultado da verificação no app real, que não foi feita ([DT-001](./DT-001-verificar-devin-desktop-real.md)). A regra da task é firme: nunca registrar por adivinhação.

## Impact

- O usuário do assistente não sabe se o Devin Desktop foi coberto ou não.
- O checkpoint do Lote 8 pede "relatório do assistente coerente com a lição" da T083, que não existe.

## Interim handling

O relatório segue sem citar o Devin Desktop, e nada é registrado no app.

Proposta, a confirmar com o mantenedor: se o [DT-001](./DT-001-verificar-devin-desktop-real.md) continuar aberto no fechamento da 0.4.0, a linha pode dizer apenas "Devin Desktop: não verificado, o produto não declara suporte". É uma quarta resposta, honesta, que não registra nada no app e que o texto da T084 ainda não prevê, então exige alterar a T084 antes.

## How to pay

1. Resolver o [DT-001](./DT-001-verificar-devin-desktop-real.md) e ler a lição resultante.
2. Escrever primeiro os testes em `tests/unit/test_installer_cli.py`.
3. Implementar a linha em `installer/cli.py` e `installer/clients.py`, conforme o resultado: coberto pelo registro compartilhado, coberto por caminho próprio (com fonte) ou não suportado.
4. Resolver este débito com `/tech-debt resolve DT-002`.

## Revisit trigger

Decidir a quarta resposta ("não verificado") se a versão final da 0.4.0 (T088) for preparada com o [DT-001](./DT-001-verificar-devin-desktop-real.md) ainda aberto.
