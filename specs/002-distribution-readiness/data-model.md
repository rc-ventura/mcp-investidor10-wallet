# Data Model — Prontidão para distribuição (Fase 0)

**Não há mudança de schema persistido.** O `memory.json` mantém exatamente o
schema e a semântica da spec 001 (ADR-0002) — a migração da Fase 0 move bytes,
não transforma dados. As entidades abaixo descrevem os objetos de
configuração/estado do bootstrap, efêmeros por processo.

## Entidades

### Configuração do Servidor (ambiente → bootstrap)

| Campo | Tipo | Obrigatório | Validação | Falha |
|---|---|---|---|---|
| `WALLET_ID` | string de dígitos | **Sim** (novo — era default `2061045`) | ausente/vazio → aborta; `re.fullmatch(r"\d+")` → aborta | `SystemExit(1)` PT-BR com instrução (URL pública da carteira) |
| `WALLET_MEMORY_PATH` | path | Não (override) | usado como está quando definido | comportamento do store (degrade) |
| `WALLET_CACHE_TTL_SECONDS` | número ≥ 0 | Não (default 600) | finito ≥ 0 | `SystemExit(1)` — ADR-0003 §3 |
| `WALLET_CACHE_MAX_STALE_SECONDS` | número ≥ 0 | Não (default 86400) | finito ≥ 0 | `SystemExit(1)` — ADR-0003 §3 |

### Localização da Memória (resolvida uma vez por processo)

| Campo | Valor |
|---|---|
| `canonical` | `~/.investidor10/memory.json` (dir 0700, arquivo 0600) |
| `legacy` | `./memory.json` (cwd do processo spawned) |
| `override` | valor de `WALLET_MEMORY_PATH`, quando definido |

**Ordem de resolução**: `override` → `canonical` existente → migração do `legacy` → `canonical` novo.

**Máquina de estados da localização** (por execução):

```
            override definido?
             /          \
           sim          não
            |            |
        OVERRIDE      canonical existe?
        (usa, sem     /          \
        migração)   sim          não
                     |            |
                  CONFLITO?    legacy existe?
            (legacy também    /          \
             existe?)       sim          não
              |              |            |
        CANONICO_WINS    MIGRADO      NOVO_CANONICO
        (legacy →        (copia →     (store cria
         .legacy-<ts>,    verifica →   sob demanda,
         aviso stderr)    remove)      em canonical)
```

- `NOVO_CANONICO`: nenhum arquivo existente; store cria no canônico na primeira escrita.
- `MIGRADO`: cópia atômica (temp 0600 + `os.replace`) → verificação de conteúdo → remoção do legado; aviso no stderr com ambos os caminhos.
- `CANONICO_WINS`: canônico usado; legado renomeado para `memory.json.legacy-<YYYYMMDD-HHMMSS>` no local original; aviso de divergência no stderr.
- Falha de cópia/permissão em `MIGRADO` → `SystemExit(1)` PT-BR com o caminho tentado (nunca começar canônico vazio ignorando legado com dados).

### Resultado da Validação da Carteira (probe de startup)

| Estado | Condição | Ação |
|---|---|---|
| `ok` | HTTP 200 em `/summary/metrics/{WALLET_ID}` | startup continua |
| `not_found_or_private` | HTTP 404 | `SystemExit(1)` PT-BR: conferir ID na URL + tornar carteira pública |
| `private` | HTTP 401/403 | `SystemExit(1)` PT-BR: carteira privada — tornar pública |
| `source_unavailable` | 5xx/timeout/transporte (timeout 10s) | warning no stderr; **startup continua** |

Evidência live 18/10/2026: ID inexistente `99999999999` → 404; ID público → 200.

### Release

| Campo | Descrição |
|---|---|
| `version` | semver; fonte única em `investidor10_wallet.__version__`, refletida no `pyproject.toml` |
| `tag` | `v<version>` no Git; gatilho do workflow de release |
| `changelog_section` | seção `## [<version>]` obrigatória em `CHANGELOG.md` (gate no release) |
| `artifact` | sdist + wheel publicados no PyPI como `mcp-investidor10-wallet` |

**Regras**: versão por release única (PyPI rejeita re-upload); enquanto major=0: feat→minor, fix→patch; changelog em PT-BR, formato Keep a Changelog.

## Relacionamentos

- Configuração → (valida) → Carteira alvo: probe consome `WALLET_ID`.
- Configuração → (resolve) → Localização da Memória: `WALLET_MEMORY_PATH` decide o ramo.
- Localização da Memória → **sem acoplamento** ao `MemoryStore` além do path resolvido (fronteira preservada para futura migração SQLite, research 001 D5).
- Release → pacote: `pyproject.toml` lê `__version__`; entry point `mcp-investidor10-wallet` → `investidor10_wallet.server:main`.
