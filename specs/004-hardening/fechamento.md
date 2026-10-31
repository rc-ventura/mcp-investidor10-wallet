# Fechamento da spec 004 — rastreabilidade e pendências

**Data do registro**: 2026-10-31
**Intervalo**: `d1b1f28..3c6f969` (9 commits, 2026-10-27 a 2026-10-31)

## Por que este documento existe

A spec 004 (hardening) entrou em `main` por push direto, sem branch nem PR, ao
contrário da spec 003. O histórico de PRs do GitHub não mostra a spec, quatro dos
seis commits principais usam o prefixo `docs:` embora alterem código em `src/`, e
o `CHANGELOG.md` já declara `0.3.0` sem que exista tag ou release. Este registro
liga esses pontos e lista o que ainda está aberto. Não reescreve a história de
`main`.

## Commits do intervalo

| Commit | Data | Conteúdo |
|--------|------|----------|
| `846b88f` `0befb5f` `84f9068` | 2026-10-27 | Roadmap: matriz MoSCoW, distribuição primeiro, renumeração das specs (004 hardening, 005 desktop, 006 cálculos) |
| `365b9d0` | 2026-10-29 | Skills `speckit-analyze` e `speckit-checklist` |
| `e4c402c` | 2026-10-29 | ID da carteira de exemplo trocado por `<id>` na doc de privacidade e nos relatórios SDD |
| `bb8b99b` | 2026-10-31 | Entrega da spec 004: trava da memória (ADR-0013), sinal duplo de erro (ADR-0014), robustez de paginação e cache, guardas de symlink, aninhamento, BOM e relógio |
| `1a32b55` | 2026-10-31 | Relatórios da revisão SDD, ciclos 1 a 5, em `reports/sdd-final-review/004/` |
| `ddadd55` | 2026-10-31 | ADRs 0015 a 0017 e quatro learning lessons |
| `3c6f969` | 2026-10-31 | Job `audit` no CI, actions fixadas por SHA, roadmap atualizado; também contém o código de `memory_store.py`, `server.py`, `wallet_client.py`, `bootstrap.py` e o novo `privacy.py` (+1163/-488 linhas) |

## Revisão SDD

O relatório mais recente da spec 004 é o ciclo 5 e termina em **NEEDS WORK**. Não
existe ciclo 6 que reverifique as correções feitas depois dele.

| Ciclo | Relatório | Veredito do Tech Leader |
|-------|-----------|-------------------------|
| 1 | `cycle-1-20261028-0741.md` | NEEDS WORK |
| 2 | `cycle-2-20261028-0822.md` | APPROVED |
| 3 | `cycle-3-20261029-0732.md` | NEEDS WORK |
| 4 | `cycle-4-20261029-0803.md` | NEEDS WORK |
| 5 | `cycle-5-20261029-0832.md` | NEEDS WORK |

A mensagem do commit `1a32b55` fala em "cycles 1–2, APPROVED"; o diretório tem 5
ciclos e só o 2 foi aprovado.

O item bloqueante do ciclo 5 foi tratado no código atual, mas sem nova revisão:

- Adotar o maior `total` declarado entre as páginas em
  `wallet_client.py` (`max(total, declared)`), com o teste
  `test_positions_adopt_a_larger_total_declared_by_a_later_page`.
- Os itens não bloqueantes de BOM (`utf-8-sig`), `_seen_file` e limites 32/33 de
  aninhamento também estão no código e nos testes.

## Estado das tarefas abertas em `tasks.md`

| Tarefa | Estado | Observação |
|--------|--------|------------|
| T048 | Aberta | Exige um leitor humano que não conheça o projeto validando `docs/PRIVACY.md` (SC-007) |
| T054 | Aberta | Local verde em 2026-10-31 (449 testes passam, `ruff check` e `ruff format --check` limpos). **O CI em `main` está vermelho**, ver abaixo |
| T055 | Aberta | Falta um ciclo 6 do `/sdd-final-review` que reverifique as correções do ciclo 5 |

## CI em `main` (execução do push `3c6f969`, run 41238678472)

O CI está vermelho em `main` nos dois últimos pushes (`3c6f969` e `a3e0eb6`).
macOS e Linux passam em 3.11, 3.12 e 3.13. Falham:

1. **Job `audit`**: `pip-audit` encontrou `joserfc 1.7.5` com `CVE-2026-119284`;
   a correção está na `1.7.6`. Falta verificar se é dependência transitiva do
   `mcp`/`fastmcp` e atualizar o `uv.lock`.
2. **Windows (3.11, 3.12 e 3.13), 5 testes**, vistos no log do CI (causa ainda
   não investigada a fundo):
   - `tests/contract/test_error_signal.py` (2 testes): a mensagem esperada, com o
     caminho do Windows, não aparece na resposta da tool. A resposta é um JSON
     com o caminho (`C:\\Users\\...`).
   - `tests/contract/test_plugin_assets.py` (3 testes): dois falham ao procurar
     texto com acento (`não estime`, `confirmação`) em arquivos lidos com
     `read_text()`, o que sugere a codificação padrão do Windows em vez de UTF-8;
     o terceiro roda `bash` sobre o hook `session-start-persona.sh` e recebe
     código de saída 1.

As causas aparentes estão nos testes e no job de auditoria, não numa regressão
confirmada do servidor, mas isso não foi verificado. A T054 só fecha com o CI
verde nas 3 plataformas.

## Pendências para o release 0.3.0

- [ ] Corrigir o `audit` (`joserfc`) e os 5 testes do Windows; CI verde em `main`.
- [ ] Rodar o ciclo 6 do `/sdd-final-review` e registrar o relatório em
      `reports/sdd-final-review/004/`.
- [ ] Executar a T048 com um leitor humano.
- [ ] Criar a tag `v0.3.0` e o release no PyPI (o `release.yml` publica via OIDC;
      só com decisão explícita do mantenedor).

## Processo daqui para frente

Trabalho novo entra por branch `spec-NNN/<nome>` e PR para `main`, como nas PRs #6
e #7, com a revisão SDD antes do merge. Evitar o prefixo `docs:` em commits que
alteram `src/`.
