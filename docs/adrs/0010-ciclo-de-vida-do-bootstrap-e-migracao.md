# ADR-0010: Semântica do ciclo de vida do bootstrap e endurecimento da migração

- **Status**: Accepted
- **Date**: 2026-10-18
- **Deciders**: Tech Leader + User (SDD final review cycle 1, spec 002)
- **Related spec**: [`specs/002-distribution-readiness/`](../../specs/002-distribution-readiness/)
- **Code**: `src/investidor10_wallet/bootstrap.py`, `src/investidor10_wallet/server.py`, `src/investidor10_wallet/wallet_client.py`

---

## Context

O ciclo 1 de revisão da spec 002 (`reports/sdd-final-review/002/cycle-1-20261018-1349.md`) identificou lacunas na superfície nova de bootstrap que precisavam de decisão arquitetural explícita para não serem re-derivadas a cada ciclo:

1. **Side effects em import-time vs. pipeline determinístico**: `load_config()` rodava no import de `wallet_client.py` e `resolve_memory_path()`/`MemoryStore()` rodavam no import de `server.py`, enquanto `main()` executava apenas o probe e terminava sem chamar `mcp.run()`. Qualquer import do pacote exigia `WALLET_ID` válido e disparava migração/escrita em disco.
2. **Diretório canônico ausente em instalações novas (`NOVO_CANONICO`)**: `resolve_memory_path()` retornava `~/.investidor10/memory.json` sem criar `~/.investidor10/`, fazendo o primeiro `save()` do `MemoryStore` falhar com `FileNotFoundError` e degradar a memória (`available=False`) em máquinas limpas.
3. **Superfície de symlink/TOCTOU na migração e borda `cwd == ~/.investidor10`**: a migração seguia symlinks em `./memory.json` e `~/.investidor10`, executava `legacy.unlink()` sem verificar o inode lido nem capturar `OSError`, e tratava `cwd == ~/.investidor10` como conflito entre legado e canônico (renomeando o único arquivo existente).
4. **Colisão de timestamp em backup de conflito (`CANONICO_WINS`)**: o sufixo `%Y%m%d-%H%M%S` (resolução de segundos) permitia sobrescrita na mesma janela de 1 segundo, divergindo do padrão `%Y%m%d-%H%M%S-%f` já adotado em `.broken-*` pelo `MemoryStore`.
5. **Fallthrough de outros códigos HTTP no probe**: o contrato C5 especificava `200`, `404`, `401/403` e `5xx/timeout`, deixando implícito o comportamento para outros códigos (ex.: `429` de rate-limit/WAF).

## Decision

1. **Pureza de import e pipeline determinístico em `main()`**:
   - Importar `investidor10_wallet.wallet_client` ou `investidor10_wallet.server` não valida variáveis de ambiente, não realiza chamadas de rede e não toca o sistema de arquivos.
   - Os singletons de módulo (`wallet_client.wallet_client`, `wallet_client.rest_client` e `server.memory`) são preservados para compatibilidade com as tools e testes in-process: `WalletClient` aceita construção interna não configurada (`_allow_unconfigured=True`) atualizada por `wallet_client.configure(config)`, e `server.memory` inicia como proxy lazy (`_LazyMemory`) substituído pela instância real de `MemoryStore` em `main()`.
   - `main()` executa estritamente os 5 passos na ordem do contrato C3: `bootstrap.load_config()` -> `wallet_client.configure()` -> `bootstrap.resolve_memory_path()` -> `MemoryStore()` -> `wallet_client.validate_wallet()` -> `mcp.run()`.

2. **Criação do diretório canônico (`0700`) e guarda `cwd == canonical`**:
   - Em todos os ramos sem override (`NOVO_CANONICO`, `MIGRADO`, `CANONICO_WINS`), `resolve_memory_path()` garante que `~/.investidor10/` exista como diretório regular com permissão `0700` antes de entregar o caminho ao `MemoryStore`. Falha de permissão aborta com `SystemExit(1)` e mensagem acionável em PT-BR.
   - Quando `os.path.abspath(legacy) == os.path.abspath(canonical)` (processo iniciado com `cwd` igual a `~/.investidor10`), o bootstrap reconhece que se trata do mesmo arquivo e retorna `str(canonical)` sem entrar nos ramos de conflito ou migração.

3. **Política de symlinks e integridade TOCTOU na migração**:
   - `~/.investidor10`, `~/.investidor10/memory.json` e `./memory.json` são inspecionados com `os.lstat` e abertos com `os.O_NOFOLLOW`; qualquer symlink ou arquivo não-regular aborta a operação com `SystemExit(1)` em PT-BR antes de `os.chmod`, cópia ou remoção.
   - `_atomic_copy()` captura `os.fstat(src_fd)` do descritor efetivamente lido e confere o conteúdo gravado no destino. Antes de `legacy.unlink()`, `resolve_memory_path()` verifica via `os.lstat(legacy)` que `(st_dev, st_ino)` permanecem idênticos.
   - `legacy.unlink()` roda dentro do bloco `try`: se a verificação de inode ou a remoção falhar, o arquivo canônico recém-copiado é removido (rollback) e o servidor aborta com `MIGRATION_FAILED_MESSAGE` em PT-BR, mantendo o legado intacto como única cópia.

4. **Unicidade de backup em `CANONICO_WINS`**:
   - O arquivo legado preservado em conflito usa timestamp com microssegundos (`memory.json.legacy-%Y%m%d-%H%M%S-%f`), alinhado ao padrão `.broken-*` do `MemoryStore`, e recusa sobrescrever um backup caso o caminho já exista.

5. **Fallthrough conservador no probe (`validate_wallet`) e endurecimento HTTP/regex**:
   - Apenas `404` (`not_found_or_private`) e `401/403` (`private`) abortam o startup. Qualquer outro status diferente de `200` (incluindo `429` ou outros `4xx`/`5xx` de proxy/WAF) emite o aviso `PROBE_UNAVAILABLE_MESSAGE` no stderr e permite que o servidor inicie, preservando a disponibilidade das tools locais de memória.
   - Ambos os clientes HTTP fixam `follow_redirects=False` e a validação numérica de `WALLET_ID` usa `[0-9]+` (ASCII estrito, rejeitando dígitos Unicode).

6. **Semântica do override `WALLET_MEMORY_PATH`** (nota adicionada no ciclo 2, SDD final review): o override retorna o caminho *verbatim* — sem strip de whitespace, sem criação do diretório pai e sem a verificação de symlink/`0700` aplicada ao caminho canônico. É decisão consciente: o env do operador está dentro do trust boundary do ADR-0004 §2 (quem define a variável já controla a máquina), e um caminho inválido degrada o store para `available=False` — estado projetado e reportado, nunca crash nem dados fabricados. Endurecimento opcional (sanitização + criação do pai + `realpath` na guarda de mesmo-arquivo) está registrado como fast-follow no relatório do ciclo 2.

## Alternatives considered

### Alternative A: Remover os singletons de módulo e instanciar tudo via lifespan do FastMCP

**Why not chosen**:
- Quebraria o acoplamento simples das 19 tools e dos mais de 200 testes de unidade/contrato existentes que inspecionam ou fazem monkeypatch de `wallet_client.wallet_client`, `wallet_client.rest_client` e `server.memory`.

### Alternative B: Abortar o startup em qualquer HTTP 4xx no probe

**Why not chosen**:
- Respostas transitórias como HTTP 429 (rate-limit) ou desafios temporários de CDN impediriam o uso inclusive das 13 tools locais de memória, violando a diretriz de não tornar a fonte externa ponto único de falha do startup (research D4).

## Consequences

### Accepted

- `import investidor10_wallet.server` é livre de efeitos colaterais em disco, rede e ambiente.
- Instalações limpas sem `~/.investidor10` prévio inicializam e persistem `memory.json` (modo `0600` dentro de diretório `0700`) desde a primeira escrita.
- Migração legada resiste a symlinks plantados no `cwd`, corridas de substituição de inode e diretórios sem permissão de unlink, sem jamais produzir traceback cru.

### Trade-offs

- `_LazyMemory` adiciona uma pequena camada de indireção para chamadas de tools fora de `main()` (ex.: suíte de testes de contrato via `Client(mcp)`), eliminada em produção assim que `main()` substitui `server.memory` pela instância concreta de `MemoryStore`.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. A migração automática de `./memory.json` for removida em uma versão major futura (ex.: `1.0.0`) após o período de transição da Fase 0.
2. O backend de persistência migrar de JSON para SQLite (Fase futura do ROADMAP), alterando a semântica de criação e migração de arquivo.

## References

- ADR-0002 (fronteira de persistência da memória e escrita atômica)
- ADR-0003 (falhas estruturadas de configuração no startup)
- ADR-0004 (modelo de ameaça e integridade on-disk §6)
- ADR-0009 (idioma das mensagens: operador em PT-BR, modelo em inglês)
- `specs/002-distribution-readiness/contracts/packaging-and-config.md` (contratos C1–C7)
