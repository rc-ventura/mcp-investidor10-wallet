# filelock: troca silenciosa para soft lock e criação do diretório pai

**Context:** Descoberto na spec 004 (Hardening), ao escolher a biblioteca de trava entre processos para o `memory.json` e ler o código instalado (`filelock` 4.2.2, fixado em 4.2.4) antes de adotá-la.
**Date:** 2026-10-28
**Future intent:** Manter `fallback_to_soft=False` e a guarda do diretório no `MemoryStore`; revalidar os dois comportamentos em qualquer upgrade do `filelock`.

---

## Mental Model: dois comportamentos padrão que contrariam a segurança do projeto

| Comportamento padrão | O que acontece | Por que é perigoso aqui |
|---|---|---|
| `fallback_to_soft=True` | Se o `flock` do sistema de arquivos devolve `ENOSYS` (ex.: algumas montagens de rede), `UnixFileLock` troca em silêncio para `SoftFileLock` | A trava soft é um arquivo de existência: sobrevive a um crash e bloqueia todos os processos até alguém apagá-lo. Além disso, esconde que a exclusão mútua do kernel não está valendo |
| `ensure_directory_exists` na aquisição | `acquire()` cria o diretório pai do arquivo de trava (`mkdir -p`) | Um `WALLET_MEMORY_PATH` apontando para uma pasta inexistente deixaria de degradar: o servidor criaria a árvore de diretórios por conta própria |

---

## API verificada (filelock 4.2.2/4.2.4)

- `filelock/_unix.py`: `UnixFileLock._acquire` chama `_acquire_native()`; se o `flock` falha com `ENOSYS` devolve o descritor para `_switch_to_soft_lock`, que só levanta o erro quando `falls_back` é falso (`fallback_to_soft=False`, `preserve_lock_file=True` ou `on_acquired` definido).
- `filelock/_api.py` (docstring de `fallback_to_soft`): "`False` fails closed, letting the `ENOSYS` propagate so a caller that needs kernel-enforced locking is never silently downgraded. It has no effect on Windows or `SoftFileLock`."
- `filelock/_api.py` (aquisição): `ensure_directory_exists(self._lock_path)` roda antes do laço de tentativa.
- Verificação empírica: `FileLock("<tmp>/nested/dir/x.lock", fallback_to_soft=False).acquire()` cria `nested/dir/` e deixa o arquivo `x.lock` em disco após a liberação.
- Com `thread_local=False`, o contador de reentrada do `FileLock` é do processo inteiro: uma segunda thread "adquire" na hora, sem esperar. A exclusão entre threads precisa de um `threading.Lock` próprio (ADR-0013, emenda de 29/10/2026).
- `TimeoutError` (`filelock.Timeout`) é subclasse de `OSError`: capturar `OSError` antes de `Timeout` engole o timeout como se fosse erro de sistema de arquivos.

---

## Examples for mcp-investidor10-wallet

### 1. Trava da memória

```python
filelock.FileLock(
    f"{path}.lock", timeout=5.0, fallback_to_soft=False, thread_local=False
)
```

`MemoryStore._acquire` captura `filelock.Timeout` primeiro (→ `MemoryBusyError`), depois `OSError` com `errno` em `{ENOSYS, EOPNOTSUPP}` (→ modo somente-leitura com aviso PT-BR; `ENOLCK` saiu do conjunto em 29/10/2026 por poder ser passageiro) e converte qualquer outro `OSError` em `MemoryUnavailableError`.

### 2. Guarda do diretório

Antes de adquirir, o store verifica `os.path.isdir(dirname(path))` e levanta `MemoryUnavailableError` se faltar: o comportamento de degradação anterior (memória em pasta inexistente → indisponível) é preservado, e o local canônico continua sendo criado só por `bootstrap._ensure_canonical_dir` com permissão 0700.

**Responsibility split:**
- `bootstrap.py`: cria e valida o diretório canônico (0700, não-symlink).
- `memory_store.py`: nunca cria diretórios; só trava, relê e grava.

---

## Relation to ADRs and next steps

- **ADR-0013** — decisão de usar `filelock` fail-closed, modo somente-leitura e a guarda do diretório.
- **Constituição V.2** — upgrade de dependência não é bump cego: ao subir o `filelock`, reler `_unix.py`/`_api.py` e reexecutar os testes de trava (`tests/unit/test_memory_locking.py`) e o teste de concorrência com `spawn`.
