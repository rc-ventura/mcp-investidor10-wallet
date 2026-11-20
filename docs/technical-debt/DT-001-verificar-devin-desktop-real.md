# DT-001: Verificar o produto no Devin Desktop real

**Status**: Open
**Priority**: Medium
**Date**: 2026-11-20
**Origin**: spec 005, Lote 8, T083 ([tasks.md](../../specs/005-desktop-distribution/tasks.md))
**Related**: [DT-002](./DT-002-linha-do-relatorio-devin-desktop.md), T084, T085, T086, [fichamento do Devin Desktop](../research/fichamentos/devin-desktop.md)

---

## Debt

A task T083 pede verificar, num Devin Desktop real, se o registro do servidor feito pelo assistente para o Devin CLI e o plugin de comportamento carregam no app: as 20 tools, as skills, o subagente guardião e a persona (hooks). O resultado deve virar a lição `docs/learning-lessons/devin_desktop_harness_compartilhado.md`, com fonte, versão e data. Essa verificação não foi feita.

## Cause

O mantenedor não tem o Devin Desktop instalado; só usa o Devin web. O Devin CLI (`devin 3000.14.30821`) está instalado na máquina, mas não prova que o app carrega o produto.

## Impact

- Bloqueia a T084 (ver [DT-002](./DT-002-linha-do-relatorio-devin-desktop.md)).
- Deixa sem resultado a célula "Devin Desktop" da matriz de validação (T085), e o gate do Lote 8 pede "nenhuma célula não testado".
- O produto não pode anunciar suporte ao Devin Desktop (T086).

O que as fontes dizem (`docs/research/fichamentos/devin-desktop.md`, pesquisado em 31/10 e 01/11/2026):

- O app compartilha o harness de agente e o formato das personalizações com o Devin CLI (F1, a única fonte lida por inteiro).
- Elas **não** cobrem se o arquivo de configuração de MCP é compartilhado entre o CLI e o app, e divergem sobre o caminho: `~/.config/devin/config.json`, `~/.config/devin/mcp_config.json` e `.devin/mcp_config.json`.
- Hooks não rodam em Restricted Mode, o que afeta a persona e o lembrete de memória do plugin.
- Uma chave de servidor que o cliente não reconhece é ignorada em silêncio.

## Interim handling

Proposta, a confirmar com o mantenedor:

- Registrar a célula "Devin Desktop" da matriz como `pendente (sem acesso ao app)`, valor que a própria matriz já admite.
- Registrar a decisão no `fechamento.md` (T093) como item devolvido ao roadmap.
- README e `docs/PRIVACY.md` seguem sem citar o Devin Desktop.

## How to pay

1. Alguém com o Devin Desktop instalado (ou o mantenedor, se instalar o app) segue a T083.
2. No app, mostrar: as 20 tools do servidor `carteira`, as skills, o subagente guardião, a persona (hooks) e onde o app guarda a configuração de MCP.
3. Escrever `docs/learning-lessons/devin_desktop_harness_compartilhado.md` com fonte, versão do app e data, e a linha no índice do `CLAUDE.md`.
4. Resolver este débito com `/tech-debt resolve DT-001` e seguir para o [DT-002](./DT-002-linha-do-relatorio-devin-desktop.md).

## Revisit trigger

Subir a prioridade para High se a 0.4.0 final for preparada (T088) com este débito ainda aberto e o texto de divulgação citar o Devin Desktop.
