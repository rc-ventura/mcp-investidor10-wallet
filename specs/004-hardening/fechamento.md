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

Em 2026-10-31 todos os itens dos 5 ciclos foram conferidos contra o código, os
testes e os docs. O resultado está numa seção "Resolution status" no fim de cada
relatório (o texto histórico dos ciclos não foi editado):

| Ciclo | Itens conferidos | Resolvidos | Adiados (decisão registrada) | Abertos |
|-------|------------------|------------|------------------------------|---------|
| 1 | 17 | 15 | 0 | 2 (T054; T048/T055) |
| 2 | 10 | 9 | 0 | 1 (T048/T054/T055 agrupados) |
| 3 | 17 | 14 | 0 | 3 (`avg_price`, nota de injeção no `PRIVACY.md`, T048/T054/T055 agrupados) |
| 4 | 15 | 10 | 2 | 3 (`O_NOFOLLOW` no `.lock`, contagem de alertas, T048/T054/T055 agrupados) |
| 5 | 12 | 7 | 1 | 4 (teste de dedupe sem ticker, texto do ADR-0002, T054, T048/T055) |

O item bloqueante do ciclo 5 (maior `total` declarado entre páginas) está no código
(`wallet_client.py`, `max(total, declared)`) e no teste
`test_positions_adopt_a_larger_total_declared_by_a_later_page`.

Achado novo da conferência: `server.py` tinha um comentário citando `ADR-0017`, o
que a varredura de estilo da T053 proíbe. Foi removido nesta PR.

Itens ainda abertos, de baixo risco: teste do fallback de dedupe para linhas sem
ticker; nota no `PRIVACY.md` sobre texto livre vindo da fonte; `O_NOFOLLOW` ao abrir
o `.lock`; limite para a quantidade de alertas; texto do ADR-0002 sobre arquivo
maior que a RAM; confirmação do mantenedor sobre `avg_price` na lista do modo
privacidade.

## Estado das tarefas abertas em `tasks.md`

| Tarefa | Estado | Observação |
|--------|--------|------------|
| T048 | Aberta | Exige um leitor humano que não conheça o projeto validando `docs/PRIVACY.md` (SC-007) |
| T054 | Aberta | Local verde em 2026-10-31 (449 testes passam, `ruff check` e `ruff format --check` limpos). A PR #9 corrige o CI e ficou verde nos 10 jobs (audit, macOS, Linux e Windows em 3.11, 3.12 e 3.13); falta o merge em `main` |
| T055 | Aberta | Falta o ciclo 6 do `/sdd-final-review`, a ser rodado pelo mantenedor sobre este estado |

## CI em `main` (execução do push `3c6f969`, run 41238678472)

O CI estava vermelho em `main` nos dois últimos pushes (`3c6f969` e `a3e0eb6`).
macOS e Linux passavam em 3.11, 3.12 e 3.13. Falhavam:

1. **Job `audit`**: `pip-audit` encontrou `joserfc 1.7.5` com `CVE-2026-119284`
   (correção na `1.7.6`). É dependência transitiva de `authlib`/`fastmcp`.
2. **Windows (3.11, 3.12 e 3.13), 5 testes**:
   - `tests/contract/test_error_signal.py` (2 testes): a mensagem era procurada
     como substring do texto JSON, onde as barras invertidas do caminho do
     Windows aparecem escapadas.
   - `tests/contract/test_plugin_assets.py` (3 testes): dois liam os assets com
     `read_text()` na codificação padrão do Windows (cp1252); o terceiro rodava o
     `bash` do PATH, que no runner é o lançador do WSL.

**Corrigido na PR #9** (`spec-004/ci-verde`): `joserfc` 1.7.5 para 1.7.7 no
`uv.lock` (publicada em 2026-10-19, dentro da regra de 7 dias); comparação pelo
JSON decodificado; `encoding="utf-8"`; hooks rodados com o Git Bash no Windows. O
CI da PR ficou verde nos 10 jobs. No Windows, 410 testes passaram e os mesmos 39
foram pulados de antes, ou seja, o teste dos hooks rodou de verdade. O merge da
#9 em `main` depende do mantenedor.

## Pendências para o release 0.3.0

- [x] Corrigir o `audit` (`joserfc`) e os 5 testes do Windows (PR #9, verde; falta
      o merge).
- [x] Conferir os ciclos 1 a 5 contra o código e atualizar os relatórios.
- [ ] Mergear a PR #9 e esta PR em `main`.
- [ ] Rodar o ciclo 6 do `/sdd-final-review` (mantenedor) e registrar o relatório
      em `reports/sdd-final-review/004/`.
- [ ] Executar a T048 com um leitor humano.
- [ ] Criar a tag `v0.3.0` e o release no PyPI, depois do ciclo 6 e do CI verde em
      `main` (o `release.yml` publica via OIDC; só com decisão explícita do
      mantenedor).

## Processo daqui para frente

Trabalho novo entra por branch `spec-NNN/<nome>` e PR para `main`, como nas PRs #6
e #7, com a revisão SDD antes do merge. Evitar o prefixo `docs:` em commits que
alteram `src/`.
