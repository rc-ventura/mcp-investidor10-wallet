# ADR-0011: Estratégia de distribuição e release — PyPI via `uvx`, src layout, versionamento 0.x e pipeline OIDC

- **Status**: Accepted
- **Date**: 2026-10-18
- **Deciders**: Tech Leader + User (SDD final review cycle 2, spec 002)
- **Related spec**: [`specs/002-distribution-readiness/`](../../specs/002-distribution-readiness/)
- **Code**: `pyproject.toml`, `src/investidor10_wallet/server.py`, `.github/workflows/release.yml`, `.github/workflows/ci.yml`, `CHANGELOG.md`

---

## Context

A spec 002 transformou o projeto de "código que roda a partir do clone" em produto publicável. As decisões de design foram registradas em `specs/002-distribution-readiness/research.md` (D1, D2, D6, D7), mas — como ocorreu na spec 001 (ver ADR-0001, Context) — o research mora dentro da pasta da spec e não faz parte do índice vivo de decisões (`docs/adrs/`) que o pipeline de revisão lê. Sem este ADR, revisores futuros re-derivariam perguntas já respondidas: por que `uvx` e não `pipx`? Por que OIDC e não token? Por que o release falha sem seção de changelog?

Quatro grupos de decisões estavam sem ADR próprio:

1. **Formato do pacote**: a reestruturação para `src/` layout com pacote importável `investidor10_wallet` e build backend `hatchling` — escolhido porque console scripts exigem `modulo:funcao` importável e porque módulos flat de topo (`server`, `wallet_client`, `memory_store`) poluem o site-packages global com nomes genéricos e colisíveis.
2. **Canal de instalação**: `uvx mcp-investidor10-wallet` como comando oficial de uma linha, sem clone — diretriz da Fase 0 do ROADMAP.
3. **Versionamento e changelog**: `CHANGELOG.md` em Keep a Changelog (PT-BR), primeira release `0.1.0`, política 0.x (feat→minor, fix→patch) com semver estrito a partir de `1.0.0`, e gate automatizado que falha o release se a tag `v*` não tiver seção correspondente.
4. **Pipeline de release**: gatilho por tag `v*` → `uv build` → verificação de changelog → smoke test do wheel em venv limpo (import sem `WALLET_ID`, exit 1 PT-BR, handshake JSON-RPC `initialize` no stdio, criação de `~/.investidor10`) → publish no PyPI via **trusted publishing OIDC** com `environment: pypi` — zero tokens armazenados.

## Decision

1. **Empacotamento**: `src/` layout, pacote único `investidor10_wallet`, `hatchling` pinado (`hatchling==1.32.4` em `build-system.requires`), versão em fonte única (`src/investidor10_wallet/__init__.py` via `tool.hatch.version`), entry point `[project.scripts] mcp-investidor10-wallet = "investidor10_wallet.server:main"`. Suporte declarado: `requires-python = ">=3.11"` (matriz de CI 3.11–3.13 × ubuntu/macos).
2. **Distribuição**: PyPI é o único canal; `uvx mcp-investidor10-wallet` é o comando documentado de instalação+execução. `uv sync && uv run mcp-investidor10-wallet` permanece para desenvolvimento.
3. **Versionamento**: Keep a Changelog em PT-BR; enquanto `0.x`, feat→minor e fix→patch; semver estrito a partir de `1.0.0`. Toda tag `v*` exige `## [X.Y.Z]` no `CHANGELOG.md` — enforceado pelo workflow, não por disciplina humana.
4. **Release**: pipeline tag-driven com smoke test do wheel *antes* do publish (pega falhas de empacotamento que testes em source tree não pegam) e publicação via OIDC trusted publishing sob `environment: pypi` (gate de aprovação de ambiente + `id-token: write`, sem secret de longa duração — ADR-0004 §4).

## Alternatives considered

### Alternative A: Flat layout + `py-modules` (sem pacote)

Instalaria `server`, `wallet_client`, `memory_store` como módulos globais do site-packages.

**Why not chosen**:
- Nomes genéricos com risco real de colisão no site-packages do usuário.

### Alternative B: `pipx run` / múltiplos executores documentados / `setuptools`

**Why not chosen**:
- Um comando oficial basta; documentar segundos executores só confunde o onboarding (usuários de `pipx` derivam sozinhos).
- `setuptools` é funcionalmente equivalente ao `hatchling`, mas exige boilerplate e não é o par default do `uv`.

### Alternative C: Changelog gerado de commits / publicação com token em secret

**Why not chosen**:
- Changelog automático exige conventional commits retroativo e gera ruído num documento curado.
- Token PyPI em secret é credencial de longa duração; OIDC é o padrão atual e não armazena segredo (ADR-0004 §4).

## Consequences

### Accepted

- Instalação de uma linha sem clone (`uvx`), onboarding medido em minutos (SC-001).
- Nenhuma credencial de publish existe fora do trust do GitHub ↔ PyPI OIDC; o `environment: pypi` adiciona gate humano antes de cada publicação.
- O wheel publicado é sempre o wheel smoke-tested na própria pipeline (import, exit-1 PT-BR, handshake `initialize`, dir canônico) — empacotamento quebrado não chega ao PyPI.
- Versão única e changelog enforced impedem drift entre tag, pacote e histórico.

### Trade-offs

- O release exige tag + changelog + aprovação de ambiente: fricção intencional por release (aceita — publicar é ato do mantenedor).
- Actions do workflow permanecem em tags mutáveis (`@v4`, `@v5`, `@release/v1`) — carry-over conhecido, SHA-pin agendado como hardening.
- GHSAs do FastMCP: `fastmcp==4.0.10` tinha GHSAs escopados aceitos (ADR-0004 §8); upgrade para `==4.0.11` executado em 2026-10-27 (patch do GHSA crítico do client), ≥4.1.0 segue agendado como hardening.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. O PyPI deixar de ser o canal adequado (ex.: distribuição corporativa/artifactory ou mudança de registry).
2. O projeto adotar versionamento de API/contrato (ex.: múltiplas majors simultâneas) que exija política de release mais rica que "0.x → 1.x semver".
3. O trusted publishing OIDC deixar de ser suportado ou o threat model mudar para exigir provenance/Sigstore adicional.

### Migration path when needed

- Trocar de backend de build: editar `build-system` + `tool.hatch.*` (entrada pequena e isolada em `pyproject.toml`).
- Adicionar segundo executor documentado (`pipx`): apenas README.
- Escalar publicação (outro registry/artifactory): substituir o step `gh-action-pypi-publish`, mantendo build + smoke + changelog gate inalterados.

## References

- `specs/002-distribution-readiness/research.md` (D1, D2, D6, D7)
- `specs/002-distribution-readiness/contracts/packaging-and-config.md` (contratos C1–C7)
- ADR-0001 (política de deps pinadas), ADR-0004 §4/§8 (sem segredos; postura de advisories), ADR-0009 (idioma PT-BR também no changelog), ADR-0010 (pipeline determinístico verificado pelo smoke test)
