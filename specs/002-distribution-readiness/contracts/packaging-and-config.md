# Contracts — Empacotamento, configuração e bootstrap (spec 002)

Contratos externos introduzidos/alterados por esta feature. Os contratos das
19 tools MCP **não mudam** (FR-010) — referência em
[`specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md`](../../001-mcp-investidor10-wallet/contracts/mcp-tools.md).

## 1. Contrato do comando (console script)

| Item | Contrato |
|---|---|
| Comando | `mcp-investidor10-wallet` |
| Execução documentada | `uvx mcp-investidor10-wallet` (nome do pacote PyPI) |
| Entry point | `investidor10_wallet.server:main` |
| Transporte | stdio — stdout é **exclusivamente** protocolo MCP (JSON-RPC) |
| Canal do operador | stderr: avisos de migração/validação; mensagens de erro de config |
| Exit codes | `0` encerramento normal; `1` erro de configuração/validação no startup (SystemExit) |
| Sinal de versão | `investidor10_wallet.__version__` (fonte única; pyproject lê dela) |

Configuração canônica do cliente (Claude Desktop, macOS GUI — caminho absoluto do `uv`):

```json
{
  "mcpServers": {
    "carteira": {
      "command": "/Users/<user>/.local/bin/uv",
      "args": ["tool", "run", "mcp-investidor10-wallet"],
      "env": { "WALLET_ID": "<id da URL pública da carteira>" }
    }
  }
}
```

## 2. Contrato de variáveis de ambiente

| Variável | Obrigatória | Default | Comportamento ausente/inválido |
|---|---|---|---|
| `WALLET_ID` | **Sim** (mudança deliberada de contrato) | — | ausente/vazio → exit 1, PT-BR com instrução da URL; não numérico → exit 1 (ADR-0003 §3) |
| `WALLET_MEMORY_PATH` | Não | `~/.investidor10/memory.json` (mudança deliberada de contrato; era `./memory.json`) | definido → override direto, sem migração |
| `WALLET_CACHE_TTL_SECONDS` | Não | `600` | inalterado (ADR-0003 §3) |
| `WALLET_CACHE_MAX_STALE_SECONDS` | Não | `86400` | inalterado (ADR-0003 §3) |

Pontos de validação: todas as checagens de config acontecem **antes** da
criação do app FastMCP — nenhum request MCP é atendido com config inválida.

## 3. Contrato do startup (ordem determinística)

1. Ler e validar config (env). Falha → exit 1 PT-BR, zero chamadas de rede.
2. Resolver localização da memória (ver §4). Falha de migração → exit 1 PT-BR.
3. Instanciar `MemoryStore(path_resolvido)` — semântica de degrade inalterada.
4. Probe da carteira (§5). `ok`/`source_unavailable` → continua; demais → exit 1.
5. Servir MCP (stdio).

Invariantes: **zero egresso de rede antes do passo 4**; passos 1–4 nunca
escrevem no stdout; avisos sempre no stderr.

## 4. Contrato da resolução/migração da memória

> **Superado pela spec 004 (0.3.0):** as linhas Conflito, Migração e Falha
> de migração abaixo, e as mensagens correspondentes do §6, deixaram de
> valer. A resolução agora é override verbatim ou local canônico, sem
> inspecionar o diretório corrente. Contrato vigente em
> `specs/004-hardening/contracts/memory-concurrency.md`.

| Caso | Condição | Resultado |
|---|---|---|
| Override | `WALLET_MEMORY_PATH` definido | usa o override; migração **não** ocorre |
| Conflito | canônico **e** legado existem | canônico usado; legado → `memory.json.legacy-<YYYYMMDD-HHMMSS>` no local original; aviso stderr |
| Migração | só legado existe | cópia atômica (0600) → verificação → remoção do legado; aviso stderr; dir `~/.investidor10/` criado 0700 |
| Novo | nenhum existe | canônico usado; arquivo criado pelo store na primeira escrita |
| Falha de migração | destino não gravável etc. | exit 1 PT-BR nomeando o caminho tentado; legado **intocado** |

Não funciona/é intencionalmente fora: rotação, merge de dois arquivos
divergentes, migração de schema (inexistente nesta fase).

## 5. Contrato da validação da carteira (probe)

`GET /wallet/api/proxy/wallet-app/summary/metrics/{WALLET_ID}`, headers de
browser, timeout 10s:

| Resposta | Estado | Ação |
|---|---|---|
| 200 | `ok` | startup continua |
| 404 | `not_found_or_private` | exit 1, PT-BR: conferir o ID na URL pública + garantir carteira pública |
| 401/403 | `private` | exit 1, PT-BR: carteira privada — tornar pública |
| 5xx/timeout/transporte | `source_unavailable` | warning stderr; startup **continua** |

Nota: carteira privada vs. ID inexistente é indistinguível no 404 hoje (sonda
live 18/10/2026: ID inexistente → 404; público → 200). Se a fonte passar a
diferenciar, o teste `live` documenta e a mensagem é refinada.

## 6. Contrato das mensagens de onboarding (PT-BR, estilo trigger-phrase)

Esqueleto obrigatório (pesquisa tool-error-channels: recurso + causa + próximo
passo):

| Caso | Esqueleto |
|---|---|
| Sem `WALLET_ID` | "WALLET_ID não configurado. Defina a variável de ambiente WALLET_ID com o ID da sua carteira. O ID aparece na URL pública: investidor10.com.br/carteira/<ID>. Depois, reinicie o servidor." |
| Carteira não encontrada/privada (404) | "Carteira <ID> não encontrada ou não é pública. Confira o ID na URL da carteira e, nas configurações do Investidor10, deixe a carteira pública. Depois, reinicie o servidor." |
| Falha de migração | "Não foi possível migrar a memória de <legado> para <canônico> (<causa>). Corrija as permissões do diretório <dir> e reinicie — seus dados em <legado> não foram alterados." |
| Conflito resolvido | "Memória:<canônico>em uso. O arquivo antigo <legado> foi preservado como <backup> e não é mais utilizado." |

## 7. Contrato de release

| Item | Contrato |
|---|---|
| Versão | semver; `__version__` única; `pyproject.toml` dinâmico |
| Changelog | `CHANGELOG.md` Keep a Changelog PT-BR; release sem seção própria → pipeline falha |
| Tag | `v<versão>` dispara `.github/workflows/release.yml` |
| Pipeline | build → smoke test do wheel (import + exit 1 sem `WALLET_ID` com mensagem PT-BR) → gate do changelog → publish PyPI (trusted publishing, sem token) |
| Imutabilidade | versão publicada nunca é reescrita; correção = nova versão |
