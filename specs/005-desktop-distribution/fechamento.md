# Fechamento da spec 005 — rastreabilidade e pendências

**Data do registro**: 2026-11-25
**Versão entregue**: `0.4.0`, tag `v0.4.0` em `bfa733d` (publicada no PyPI em 2026-11-20), promovida para `main` em 2026-11-22 pelo PR #39 (`8a13943`)
**Intervalo**: `v0.3.0..v0.4.0` (145 arquivos alterados)

## Por que este documento existe

A spec 005 levou o produto ao Claude Desktop: plugin único com o servidor via `uvx`, configuração local da carteira (pública ou restrita) por uma página local, assistente de instalação e `doctor`, e um fluxo de release com `develop`, portão de promoção e `main` só com versões publicadas. Este registro liga cada requisito e cada critério de sucesso à evidência que existe, diz o que ficou como débito técnico e o que o mantenedor ainda precisa decidir. Não reescreve a história.

## Ramo de D1 e mudanças de rota

- **Ramo escolhido (D1, revisada em 08/11/2026):** variante do ramo 3. O plugin declara o servidor `carteira` inline com `uvx --from mcp-investidor10-wallet==<versão>`; o `uv` é pré-requisito só no Claude Desktop. **Não há `.mcpb`**: as tasks T051, T054 e T077 foram removidas. Decisão em ADR-0018.
- **FR-002 revista** por causa disso: o usuário do Desktop instala o `uv` uma vez no terminal (`docs/INSTALACAO-DESKTOP.md`).
- **Claude unificado:** o app já não tem Chat separado (ver FR-009a).

## Marcos do intervalo

| Marco | Data | Observação |
|-------|------|------------|
| `v0.4.0rc1` a `v0.4.0rc4` | 2026-11 | rc2 e rc3 só corrigiram o `verify` do release; a rc4 é a primeira com o plugin único no tag |
| PRs #30, #31 e #32 | 2026-11-11 e 11-12 | rc4, README e `doctor`, e o `uv` falso do teste do `doctor` no Windows |
| Lote 7 (`cc58873`) | 2026-11-20 | **entrou em `develop` por push direto, sem PR** (ver "Desvios de processo") |
| PR #34 | 2026-11-20 | `dnspython` 2.9.2 e `opentelemetry-api` 1.45.2 (job `audit` vermelho) |
| PR #35 | 2026-11-20 | Lote 8: instruções do servidor, changelog, matriz, débitos DT-001 e DT-002 |
| PR #36 | 2026-11-20 | versão `0.4.0` nos seis pontos |
| Tag `v0.4.0` | 2026-11-20 | `Release` verde (`build`, `publish` com aprovação, `verify` nos três sistemas) |
| PR #39 | 2026-11-22 | `promote/v0.4.0` em `main`, 28 checks verdes |
| PRs #49, #52, #53 e #54 | 2026-11-22 a 11-25 | correção do `live.yml`, registros da revisão final, S2 e S9, e atualização conjunta das dependências |

## Revisão SDD

O **ciclo 1** da spec 005 (`reports/sdd-final-review/005/cycle-1-20261120-1004.md`, 2026-11-20): QA **PASS** (950 testes, 97% de cobertura de linhas), Segurança **PASS** (nenhum achado crítico ou alto) e Tech Leader **APPROVED**. Foram classificados 46 achados: 5 do grupo A (antes de promover), 11 do B (0.4.1), 16 do C (aceitar ou registrar) e 14 do D (informativos). A revisão rodou depois da criação da tag, então todo achado de código vai para a `0.4.1`.

Itens obrigatórios do Tech Leader:

| Item | Estado |
|------|--------|
| Ambiente `pypi` só para tags `v*` (ADR-0020 §8) | Feito em 2026-11-20 (revisor mantido; política de tag adicionada) |
| Confirmar o publisher confiável no PyPI | Confirmado pelo mantenedor em 2026-11-25: aponta para este repositório, `release.yml` e o ambiente `pypi` |
| Promover a 0.4.0 (T091) | Feito em 2026-11-22 (PR #39) |
| Fechar o ciclo (T092, T093) | T092 feito; este documento é o T093 |
| Registrar as decisões (emendas dos ADR-0019 e ADR-0020, nota do `--link` no `PRIVACY.md`, lição dos dígitos Unicode) | Feito (PR #52) |
| Não divulgar o plugin antes de corrigir os hooks da persona | **Vale até a 0.4.1**; item Must do roadmap |

## Rastreabilidade dos requisitos funcionais

| Requisito | Estado | Evidência |
|-----------|--------|-----------|
| FR-001, FR-002 | Atendido no macOS; Windows pendente | Plugin no marketplace próprio (`.claude-plugin/marketplace.json`); S2 ok no macOS (`validation-matrix.md`); o Desktop sincronizou o commit `8a13943` em 2026-11-25. Windows: DT-003 |
| FR-003 | Atendido | Job `verify` do release instala a versão exata do PyPI por `pip` e por `uvx` e sobe o servidor em Ubuntu, macOS e Windows |
| FR-004 a FR-008 | Atendido | Servidor sem configuração, `open_wallet_setup`, `wallet_not_configured`, token de uso único, link e credencial fora do modelo: testes de contrato e de integração; revisão SDD (QA e Segurança); S5 ok no macOS |
| FR-008a | Verificado, sem ação | Nenhuma menção a elicitation nas notas do Claude Desktop até 2026-11-06; `research.md` D15 (T082) |
| FR-009 | Atendido no macOS | Sessão Cowork com o produto completo: S2 e S6 ok no macOS |
| FR-009a | Não aplicável hoje | A tela inicial do Desktop não oferece Chat separado; só um computador que não roda o Cowork cai em Chat. O README descreve a limitação. Célula do macOS: `não aplicável` |
| FR-009b | macOS atendido; Windows sem Git pendente | Persona injetada no início da sessão, observada no uso; Windows: DT-003 |
| FR-009c | Atendido | S6: a tese salva no Claude Code apareceu no Desktop (2026-11-08, reconfirmado em 2026-11-10); a configuração fica em `~/.investidor10/`, fora do plugin |
| FR-009d | Parcial | Remoção do registro antigo conferida à mão (`claude mcp list` com um só servidor); o instalador real no Claude Code não rodou: DT-004 |
| FR-010 a FR-017 | Atendido | 3xx, 401 e 403 viram `access_denied`; link público ou restrito; credencial só nas requisições da carteira; validação antes de gravar; `configure`; flags `--link` e `--mask`. Testes unitários, de contrato e de integração; lição `proxy_301_acesso_recusado_sem_location` |
| FR-018 | Atendido | `docs/PRIVACY.md` recomenda a carteira restrita (mais a nota do `--link` na emenda de 2026-11-20) |
| FR-019 | Atendido | ADR-0009: mensagens ao usuário em PT-BR e ao modelo em inglês |
| FR-020, FR-021 | **Não atendido** | Sem acesso ao Devin Desktop: DT-001 e DT-002 |
| FR-022 | Atendido | Tabela "Validação por plataforma" no README; só o Claude Desktop no macOS aparece como validado, e o Devin Desktop como "sem suporte declarado" |
| FR-023 | **Parcial por decisão** | Matriz preenchida; só macOS com Claude Desktop foi validado à mão. O resto está como `pendente` ligado a DT-001 a DT-005 |
| FR-024, FR-025 | Atendido | `doctor` com saída sanitizada (`test_output_has_no_id_credential_home_or_user_name`) |
| FR-026 | Atendido | `pytest -k consistency`: versão do pacote, dos quatro manifestos e do `args` do servidor iguais; `--expected-tools` do `release.yml` igual às tools servidas |
| FR-027 | Atendido, com uma exceção | Marketplace e plugin fixados na tag no Claude Code, no Codex (`--ref`) e no Gemini (`--ref`). **Devin CLI não aceita referência** e segue a branch padrão; o relatório avisa |
| FR-028 | Atendido | `live.yml` semanal e sob demanda; execução agendada de 2026-11-23 verde. Os disparos manuais de 2026-11-22 falharam antes da correção (domingo, sem pregão) |
| FR-029 | Atendido | Dependabot ativo para `uv` e `github-actions`, contra `develop`, com carência de 7 dias; os PRs #40 a #42 foram mesclados um a um e os #43 a #48, que conflitavam entre si, pelo PR #54 (conjunto testado de uma vez) |
| FR-030, FR-031 | Atendido, com uma ressalva | Distribuição pelo marketplace próprio; README com a seção do Desktop em PT-BR. **Faltam as imagens** de `docs/images/desktop/` pedidas na T063 |
| FR-032 a FR-034 | Atendido | ADR-0020: `develop`, `main-gate`, `promote.yml`; `main` só recebeu `promote/v0.4.0` (PR #39); pré-lançamentos publicados sem promover |

## Rastreabilidade dos critérios de sucesso

| Critério | Estado | Evidência |
|----------|--------|-----------|
| SC-001, SC-001a | macOS atendido (informado) | S2: menos de 5 minutos, com e sem `uv`; página de configuração aberta sozinha em conversa nova (2026-11-08). Não foi medido em 100% das tentativas |
| SC-002 | Atendido no macOS | S6 em 2026-11-08 e 2026-11-10 |
| SC-003 | Atendido por teste | `access_denied` nunca vira `unexpected_format` (testes e lição do 301). Não há teste real com carteira restrita nem na `live` nem na matriz |
| SC-004 | Atendido | Testes, varredura de segredos da revisão SDD e `check-no-wallet-id` com saída 0 no ambiente do mantenedor (2026-11-20) |
| SC-005 | Atendido no macOS | S5: troca de carteira e mascaramento pela página |
| SC-006 | **Aberto por decisão** | Células pendentes sob DT-001 a DT-005; a documentação não anuncia essas combinações (FR-022) |
| SC-007 | Atendido | Os 5 cenários têm teste no `doctor`: runner ausente, link inválido, carteira privada, memória sem permissão de escrita e produto não registrado (`tests/unit/test_doctor.py`). O QA da revisão SDD disse que faltava o "link inválido", mas existe: `test_invalid_link_in_the_configuration_fails` |
| SC-008 | Atendido | Testes de consistência e `verify` do release |
| SC-009 | Atendido por teste, com uma ressalva | Nenhuma tool recebe o link nem a credencial. A flag `--link` do terminal coloca o link na linha de comando; isso está avisado em `docs/PRIVACY.md` |
| SC-010 | Atendido | `main-gate` em toda promoção; `main` só tem o merge do PR #39 em `8a13943`, com `0.4.0` publicada no índice |

## Matriz de validação e débitos técnicos

A matriz (`validation-matrix.md`) cobre à mão apenas o **macOS com o Claude Desktop** (decisão de 2026-11-20); o restante ficou como `pendente`, ligado a um débito em `docs/technical-debt/`:

| Débito | Assunto | Prioridade |
|--------|---------|------------|
| DT-001 | Verificar o Devin Desktop real (T083) | Medium |
| DT-002 | Linha do relatório sobre o Devin Desktop (T084) | Medium |
| DT-003 | Windows | Medium |
| DT-004 | Claude Code pelo assistente (macOS e Linux) | Medium |
| DT-005 | Devin CLI, Codex, Gemini e o assistente real | Medium |
| DT-006 | Falhas de subprocesso no instalador e a flag `--yes` | Medium |
| DT-007 | Endurecer a página local | Low |
| DT-008 | Higiene de scripts e workflows de release | Low |

O S9 tem evidência na matriz (promoção, portão, consistência, `live.yml`, `dry-run` do `promote.yml`); só o passo 4, o hotfix, fica para a primeira correção urgente de verdade.

## Desvios de processo

- **Lote 7 sem PR.** O commit `cc58873` foi enviado direto para `develop`; a branch local tinha como upstream `origin/develop`, o que explica o push sem PR (inferência, não confirmada pelo comando exato). Os rulesets de `develop` e `main` só foram criados depois, em 2026-11-20 (PR obrigatório com 0 aprovações, 11 e 12 checks, sem force push, bypass vazio). O CI rodou depois do push e passou.
- **PR #37** (`spec-005/fechamento-0.4.0` → `main`) foi aberto por engano e fechado; para `main` só entra PR de `promote/vX.Y.Z`.
- **A tag saiu antes do fim da revisão SDD**, então os achados de código não puderam entrar na 0.4.0.
- **O agendamento do `live.yml` caía antes da abertura da B3**, e o teste da cotação falharia toda segunda. Corrigido em `develop` (PR #49), mas o `schedule` só vale a partir da `main`: a correção chega lá com a 0.4.1.

## Itens devolvidos ao roadmap

- **Hooks da persona e do lembrete de memória** em toda sessão (item Must da Fase 4); inclui o texto "carteira pública" do `session-start.json`. Não divulgar o plugin antes.
- **Lote 0.4.1:** DT-006, DT-007 e DT-008; os PRs do Dependabot que forem surgindo; o issue #38 (ETFs), já mesclado no PR #50.
- **Pré-versão `v0.4.1rc1` antes da final**, para exercitar o `release.yml` com as actions novas (`setup-uv` 10, `download-artifact` 8, `upload-artifact` 7, `checkout` 7), que só rodam em tag.
- **S1b / T011:** conferir se gerar um link novo no site invalida a credencial antiga (D16). Segue sem verificação; o `docs/PRIVACY.md` já diz que isso não é confirmado.
- **Imagens do Desktop** (T063) em `docs/images/desktop/`, sem dado de carteira real.
- **Elicitation** no Claude Desktop (FR-008a): reverificar nas notas de versão a cada release.
- **Hotfix** (S9 passo 4): registrar o resultado em `docs/RELEASING.md` na primeira correção urgente.

## Decisões do mantenedor registradas

- **T086a, decidida em 2026-11-25: manter.** O assistente segue registrando o servidor por `mcp add` e instalando o plugin de comportamento no Devin, Codex e Gemini (ADR-0012). A causa é que a unificação não foi validada em máquina limpa de nenhum dos três (DT-005); nada foi anunciado nem mudado no README.
- **Publisher confiável no PyPI, confirmado em 2026-11-25:** aponta para este repositório, `release.yml` e o ambiente `pypi`.
- **Células `pendente` da matriz:** aceitas como débito técnico DT-001 a DT-005 (decisão de 2026-11-20).

## Processo daqui para frente

Trabalho novo entra por branch `spec-NNN/<nome>` e PR para `develop`, com os checks dos rulesets; só `promote/vX.Y.Z` chega a `main`. Pré-lançamento antes de versão final quando o `release.yml` ou as actions mudarem. Revisão SDD **antes** de criar a tag.
