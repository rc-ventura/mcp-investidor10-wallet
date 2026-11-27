# DT-006: Tratar falhas de subprocesso no instalador e no doctor, e a flag `--yes`

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: revisão final da spec 005, ciclo 1 (`reports/sdd-final-review/005/cycle-1-20261120-1004.md`, achados #1 e #5, classe B)
**Related**: [ADR-0012](../adrs/0012-integracao-automatica-de-clientes.md), `src/investidor10_wallet/installer/clients.py:30-33`, `src/investidor10_wallet/installer/cli.py:96`, `README.md:156`

---

## Debt

Dois pontos do instalador ficaram para a 0.4.1:

1. **`_run()` não trata falha do processo filho.** Ele chama `subprocess.run(..., timeout=120)` e nada captura `TimeoutExpired` nem `FileNotFoundError` (se o binário sumir entre a detecção e a chamada). Um `claude mcp list` lento (ele checa a saúde de cada servidor) ou uma instalação de plugin lenta aborta o `doctor` e o `install` com traceback, em vez de um diagnóstico.
2. **A flag `--yes` não faz nada.** Ela é aceita (`cli.py:96`) e documentada no README ("Pula confirmações de rotina"), mas nenhum código a lê. A ADR-0012 §1 diz que ela não afeta as perguntas de colisão.

## Cause

Achados da revisão final do ciclo 1, classificados para a 0.4.1 porque a 0.4.0 já estava publicada quando a revisão terminou. Nenhum dos dois bloqueia o caminho feliz nem a fronteira de privacidade.

## Impact

- No `doctor`, o traceback custa justamente o relatório sanitizado que o subcomando existe para produzir.
- O texto da `--yes` promete um efeito que não existe e contradiz a ADR-0012.

## How to pay

1. Escrever os testes primeiro: um processo filho que estoura o tempo e um binário ausente, no `doctor` e no `install`.
2. Capturar `TimeoutExpired` e `OSError` em `_run()` e devolver um resultado de falha com causa e ação; o `doctor` mostra uma verificação `falha` em vez de abortar.
3. Decidir a `--yes`: remover a flag ou corrigir a ajuda e a linha do README para dizer o que ela de fato faz.
4. Entrar na 0.4.1, com ciclo próprio de revisão sobre o diff `v0.4.0..0.4.1`.
5. Resolver com `/tech-debt resolve DT-006`.

## Revisit trigger

Subir para High se um usuário relatar `doctor` ou `install` com traceback.
