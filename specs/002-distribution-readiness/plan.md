# Implementation Plan: Prontidão para distribuição do produto (Fase 0 do ROADMAP)

**Branch**: `002-distribution-readiness` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-distribution-readiness/spec.md`

## Summary

Transformar o servidor em produto distribuível: reestruturar o código para um pacote instalável com console script (instalação/execução de uma linha via `uvx`), tornar `WALLET_ID` obrigatório (sem default pessoal), mover o default da memória para o local canônico `~/.investidor10/memory.json` com migração sem perda do arquivo legado, validar a carteira configurada na inicialização (sonda live confirma: ID inexistente → HTTP 404, pública → 200) com mensagens de onboarding em PT-BR, e completar a infra de release — CHANGELOG, pre-commit/CI e publicação no PyPI com versionamento semântico. Nenhuma tool muda de comportamento observável (FR-010); as duas mudanças deliberadas de contrato são o `WALLET_ID` obrigatório e o novo caminho default da memória.

## Technical Context

**Language/Version**: Python 3.11+ (inalterado)

**Primary Dependencies**: runtime inalterado — `fastmcp==4.0.10`, `httpx==0.28.1` (zero novas deps de runtime, ADR-0001). Build/backend: hatchling via `uv build`. Dev/qualidade: `pytest`, `pytest-asyncio`, `respx` (existentes) + `ruff` e `pre-commit` (novos, apenas tooling, pinned ≥7 dias).

**Storage**: `memory.json` versionado inalterado em schema e semântica (ADR-0002). Novo: resolução de caminho com default canônico `~/.investidor10/memory.json` (dir 0700), override `WALLET_MEMORY_PATH` preservado, migração do legado `./memory.json`.

**Testing**: pytest + respx existentes (ajustados ao novo layout para importar pelo nome do pacote); novos testes de unidade para resolução de caminho/migração, config de startup e validação da carteira; probe real marcada `live` (ID inexistente → 404 já confirmado manualmente em 18/10/2026).

**Target Platform**: macOS local (dev e alvo principal), portável para Linux; publicado no PyPI como pacote de console.

**Project Type**: MCP server empacotado (console script stdio, sem rede exposta).

**Performance Goals**: validação da carteira adiciona no máximo uma chamada (timeout ≤ 10s) ao startup; em fonte indisponível o startup não fica refém — warning no stderr e o servidor sobe (erros explícitos nas tools continuam garantidos). Instalação limpa via executor de pacotes sob demanda sem clone (SC-001).

**Constraints**: stdout é reservado ao protocolo MCP — toda mensagem de operador (migração, validação, erros de config) sai no stderr ou aborta via `SystemExit` com código 1 (padrão ADR-0003 §3). Mensagens de onboarding/startup em PT-BR (spec 002 FR-006/FR-007); docstrings e erros de tools permanecem em inglês (ADR-0007 §4) — desvio registrado em research.md D9. Nenhuma escrita na API; nenhum host de saída novo (ADR-0004 §3).

**Scale/Scope**: 1 pacote PyPI, 1 comando, 4 pontos de mudança de código (config de startup, resolução/migração do path da memória, validação da carteira, empacotamento/layout) + documentação de onboarding PT-BR + gates (pre-commit, CI, workflow de release).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` está como template não preenchido (sem princípios definidos) — **nenhum gate aplicável**. Nenhuma violação a justificar.

*Re-check pós-Phase 1*: o design adiciona apenas reorganização de módulos em pacote e funções de bootstrap (resolução de path, migração, probe) — nenhum componente novo além do necessário; runtime segue com duas dependências e um arquivo de estado. Sem mudanças.

## Project Structure

### Documentation (this feature)

```text
specs/002-distribution-readiness/
├── plan.md                        # Este arquivo
├── research.md                    # Phase 0 — decisões D1–D9 (layout, entry point, WALLET_ID, probe, memória canônica, gates, release, docs)
├── data-model.md                  # Phase 1 — entidades de config/paths/validação/release (sem mudança de schema persistido)
├── quickstart.md                  # Phase 1 — cenários de validação ponta a ponta (SC-001..SC-006)
├── contracts/
│   └── packaging-and-config.md    # Phase 1 — contratos: CLI, env vars, startup, migração de memória, release
├── checklists/
│   └── requirements.md            # checklist de qualidade da spec (16/16)
└── tasks.md                       # Phase 2 (/speckit-tasks — NÃO criado por este comando)
```

### Source Code (repository root)

```text
mcp-investidor10-wallet/
├── pyproject.toml                 # + build-system (hatchling), [project.scripts], readme/license/classifiers, ruff config, pytest pythonpath src
├── CHANGELOG.md                   # novo — Keep a Changelog, semver; 0.1.0 = primeira release pública
├── README.md                      # reescrito: onboarding PT-BR (install 1 linha, WALLET_ID da URL, carteira pública, gotcha PATH absoluto GUI)
├── .pre-commit-config.yaml        # novo — hooks ruff (lint + format check)
├── .github/workflows/
│   ├── ci.yml                     # novo — matriz py 3.11/3.12/3.13 × ubuntu/macos: uv sync --locked + pytest (não-live)
│   └── release.yml                # novo — tag v* → uv build → smoke test do wheel → publish (trusted publishing)
├── src/
│   └── investidor10_wallet/
│       ├── __init__.py            # __version__ (fonte única de versão)
│       ├── server.py              # movido de ./server.py; FastMCP app + tools + main() (console script)
│       ├── wallet_client.py       # movido de ./wallet_client.py; + probe de validação da carteira
│       ├── memory_store.py        # movido de ./memory_store.py; inalterado em schema/semântica
│       └── bootstrap.py           # novo — resolução de path da memória + migração legada + mensagens PT-BR
├── memory.json                    # arquivo legado do autor — migra para ~/.investidor10/ na 1ª execução da versão nova
└── tests/
    ├── unit/
    │   ├── test_memory_store.py   # ajuste de imports (pacote)
    │   ├── test_wallet_client.py  # ajuste de imports + testes do probe de carteira (respx)
    │   ├── test_alerts.py         # ajuste de imports
    │   └── test_bootstrap.py      # novo — resolução de path, migração (3 casos), override, SystemExit de config
    ├── contract/
    │   └── test_tools_schemas.py  # ajuste de imports; shapes inalterados (FR-010)
    └── integration/
        └── test_live_api.py       # marcado `live`; + caso ID inexistente → 404
```

**Structure Decision**: migração de layout flat para **src layout com pacote importável**. Motivo: console script exige ponto de entrada como função (`investidor10_wallet.server:main`) e não se instala scripts soltos; a alternativa flat com `py-modules` instalaria `server`/`wallet_client`/`memory_store` como módulos de topo no site-packages global (poluição de namespace e risco de colisão — ver research.md D1). `bootstrap.py` concentra toda a lógica nova de inicialização (paths, migração) deixando `memory_store.py` intacto como fronteira de storage para a futura migração SQLite (research 001 D5).

## Complexity Tracking

Sem violações de constituição — seção não aplicável.
