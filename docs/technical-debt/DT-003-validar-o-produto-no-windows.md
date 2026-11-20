# DT-003: Validar o produto no Windows

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: spec 005, Lote 8, T085 e T061 ([tasks.md](../../specs/005-desktop-distribution/tasks.md), [validation-matrix.md](../../specs/005-desktop-distribution/validation-matrix.md))
**Related**: [DT-004](./DT-004-validar-claude-code-no-macos-e-linux.md), T086, `docs/INSTALACAO-DESKTOP.md`

---

## Debt

Nenhum roteiro foi executado à mão num Windows. As células abaixo da matriz de validação seguem `pendente`:

- Claude Desktop: S2 passos 2 a 4 com o `uv` instalado pelo PowerShell, S5 (troca de carteira e segurança da página) e S6 (memória compartilhada).
- Claude Desktop: hooks (persona e lembrete de memória) numa máquina sem Git for Windows.
- Claude Desktop: conversa Chat comum, se a superfície ainda existir (ver a observação na matriz).
- Claude Code CLI: plugin e `install --clients claude` no Windows (S7).

## Cause

O mantenedor não tem acesso a uma máquina Windows no momento (decisão de 20/11/2026: validar à mão só o macOS com o Claude Desktop).

## Impact

- O produto não pode anunciar o Windows como validado (T086). O README e `docs/INSTALACAO-DESKTOP.md` precisam dizer que a experiência no Windows não foi validada à mão.
- O que já é coberto sem máquina Windows: a CI roda os testes e o job `verify` instala a versão publicada, por `pip` e por `uvx`, em `windows-latest`. Isso não cobre o Claude Desktop nem o Claude Code do Windows.
- O gate do Lote 8 pede "nenhuma célula não testado"; as células ficam como `pendente`, ligadas a este débito.

## Interim handling

- Manter as células como `pendente`, com link para este débito.
- A T086 ajusta o README e `docs/INSTALACAO-DESKTOP.md` para registrar "validado no macOS; Windows ainda não validado".
- Registrar o item como devolvido ao roadmap no `fechamento.md` (T093).

## How to pay

1. Numa máquina Windows limpa (e outra sem Git, para os hooks), seguir `docs/INSTALACAO-DESKTOP.md` do passo 1 ao 8 e anotar por passo: sistema, versão do Claude Desktop, se foi preciso reiniciar, e a mensagem exata de erro.
2. Rodar o S5, o S6 e o S7 do `quickstart.md` e preencher a `validation-matrix.md`.
3. Tirar os "(a validar)" de `docs/INSTALACAO-DESKTOP.md` e o aviso do README.
4. Resolver com `/tech-debt resolve DT-003`.

## Revisit trigger

Subir para High se chegar um relato de usuário no Windows, ou se o README voltar a citar o Windows como suportado antes da validação.
