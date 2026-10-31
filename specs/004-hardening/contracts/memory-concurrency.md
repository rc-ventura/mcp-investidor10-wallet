# Contract — concorrência, changelog e caminho da memória

Cobre FR-001…FR-006, FR-016…FR-020, FR-029…FR-031, FR-038, FR-039.
Entidades e estados em [data-model.md](../data-model.md).

## Trava

- Arquivo `<memória>.lock`, `filelock.FileLock(timeout=5,
  fallback_to_soft=False, thread_local=False)`.
- Seção crítica = reload do disco + operação + (changelog + save, se
  escrita). Nenhuma I/O de rede dentro da seção crítica.
- Timeout → `memory_busy`. `OSError(ENOSYS)` na sonda inicial → estado
  `read_only` + aviso PT-BR em stderr:
  `A memória em <caminho> está em um sistema de arquivos sem suporte a trava (ex.: pasta de rede). Leituras seguem funcionando, mas gravações serão recusadas para não perder dados. Aponte WALLET_MEMORY_PATH para um disco local (ex.: ~/.investidor10/memory.json) e reinicie.`

## `get_session_context` sob concorrência

1. sob trava: reload, digest, lista de alertas `active`;
2. sem trava: busca de cotações;
3. sob trava: reload, `evaluate_alerts(quotes)` só sobre alertas ainda
   `active`, changelog `trigger`, save.

`memory_status` ganha o valor `read_only` (passo 3 pulado). O retorno não
muda de forma.

## Gravação atômica

Tempfile no mesmo diretório → `fsync` → `os.replace`. `PermissionError` no
replace → até 5 novas tentativas (50, 100, 200, 400, 800 ms; 6 tentativas no
total) dentro da trava; persistindo → `memory_unavailable`.

Leitura (emenda 2026-10-28, ADR-0013): JSON ou schema inválido → backup
`.broken-*` (nunca em modo somente-leitura) e `memory_unavailable`; `OSError`
de leitura → `memory_unavailable` sem backup, nova tentativa na operação
seguinte; arquivo que sumiu depois de lido ou gravado neste processo →
`memory_unavailable` e aviso ao operador, sem recriar vazio; `memory.json` que
é link simbólico → `memory_unavailable` e aviso, sem seguir nem substituir o
link (leitura com `O_NOFOLLOW`; o backup grava os bytes já lidos).

Trava (emenda 2026-10-29, ADR-0013): `ENOSYS`/`EOPNOTSUPP` → somente-leitura;
`ENOLCK` → `memory_unavailable` só naquela operação. Uma segunda thread do mesmo
processo espera a trava e, esgotado o timeout, recebe `memory_busy`.

## Changelog

`<memória>.log`, JSONL, linha definida em data-model.md; criado 0600 no
POSIX; escrito sob a trava antes do save; falha →
`Aviso: não foi possível registrar a mudança em <caminho>.log (<causa>); a gravação na memória seguiu normalmente.`
em stderr.

## Resolução do caminho (após remoção da migração)

| Situação | Resultado |
|---|---|
| `WALLET_MEMORY_PATH` definido | usado verbatim; nada mais é inspecionado |
| ausente | `~/.investidor10/` garantido (0700 no POSIX, regular, não-symlink); `memory.json` não pode ser symlink; retorna o canônico |
| `memory.json` no cwd | **ignorado**: não é lido, copiado, renomeado nem alterado |
| falha ao preparar o diretório canônico | exit 1 com `CANONICAL_DIR_FAILED_MESSAGE` (inalterada) |

Supera o §4 de `specs/002-distribution-readiness/contracts/packaging-and-config.md`
(linhas de Conflito, Migração e Falha de migração).

## Plataformas

macOS, Linux e Windows na matriz de CI. Testes de concorrência usam
`multiprocessing` com o método `spawn` (o mesmo nas três plataformas):
2 processos × 100 gravações intercaladas → 200 entradas, ids únicos
(SC-001); gravação em A visível na próxima leitura de B (SC-002).
