# ADR-0013: Concorrência da memória multiprocesso — trava `filelock` fail-closed, reload sob trava e modo somente-leitura

- **Status**: Accepted (amended 2026-10-28)
- **Date**: 2026-10-28
- **Deciders**: Tech Leader + User (ciclo spec 004, clarificações de 2026-10-27)
- **Related spec**: [`specs/004-hardening/`](../../specs/004-hardening/)
- **Code**: `src/investidor10_wallet/memory_store.py`, `src/investidor10_wallet/server.py` (`get_session_context`), `src/investidor10_wallet/bootstrap.py` (`LOCK_UNSUPPORTED_MESSAGE`)
- **Research**: `specs/004-hardening/research.md` (D1–D4); `docs/learning-lessons/filelock_fallback_soft_silencioso.md`

---

## Context

O ADR-0002 definiu a memória como um único `memory.json` com gravação atômica
(`tempfile` + `os.replace`). Isso evita corrupção, mas não perda: cada
processo do servidor mantinha uma cópia em memória e regravava o arquivo
inteiro. Com mais de um cliente ativo (Claude Code e, a partir da spec 005,
Claude Desktop), cada um spawna o seu processo sobre o mesmo arquivo, e a
última gravação vence: uma regra salva no cliente A some quando o cliente B
grava uma tese logo depois. O `next_id` calculado sobre a cópia local também
podia repetir identificadores, e dois bootstraps concorrentes podiam disparar
o mesmo alerta duas vezes.

A decisão do mantenedor foi suportar macOS, Linux e Windows já nesta spec, o
que exigiu uma trava multiplataforma e a emenda 1.2.0 da Constituição (V.1).

## Decision

1. **Trava de kernel em arquivo separado.** `filelock.FileLock(f"{path}.lock",
   timeout=5.0, fallback_to_soft=False, thread_local=False)`. A trava não fica
   no próprio `memory.json` porque a gravação atômica troca o inode a cada
   `os.replace`. É uma trava do sistema operacional, liberada quando o
   processo morre. `filelock==4.2.4` entra como dependência direta de runtime
   (a única autorizada pela emenda 1.2.0).
2. **`fallback_to_soft=False` (fail-closed).** Por padrão a biblioteca troca
   para uma trava por existência de arquivo quando o sistema de arquivos não
   implementa `flock`; essa trava sobrevive a um crash e bloquearia todos os
   processos. Com `False`, o erro (`ENOSYS`, `ENOLCK`, `EOPNOTSUPP`) é
   propagado e tratado pelo item 5.
3. **Reload do disco sob a trava, no nível mais externo.** Toda operação
   pública, de leitura ou de escrita, adquire a trava e recarrega o arquivo.
   O reload ocorre só na aquisição mais externa (contador de profundidade),
   para que operações compostas (`log_insight`, `evaluate_alerts`,
   `record_decision_outcome`) não descartem mutações em andamento. Geração de
   id, deduplicação e transição de alerta acontecem na mesma seção crítica.
   Reavaliar `available` a cada reload faz um arquivo consertado à mão voltar a
   funcionar sem reiniciar o processo.
4. **`get_session_context` em três fases.** (1) digest e alertas ativos sob
   trava; (2) busca de cotações sem trava (até 20 s por cotação, nunca
   segurando a trava durante rede); (3) `evaluate_alerts` sob trava, que relê
   o estado e só dispara o que ainda estiver `active`.
5. **Modo somente-leitura.** Se a trava não é suportada, o store entra em
   `read_only`: leituras seguem (sem exclusão mútua), gravações levantam
   `MemoryReadOnlyError` (`memory_read_only`) e o operador recebe uma mensagem
   PT-BR com a causa e o conserto (`WALLET_MEMORY_PATH` em disco local). Não há
   gravação sem trava nem troca automática de arquivo. `get_session_context`
   devolve `memory_status: "read_only"` e não avalia alertas.
6. **Trava ocupada.** Passados 5 s, a tool devolve `memory_busy`
   (`MemoryBusyError`) sem gravação parcial.
7. **Backup único de arquivo corrompido.** O nome passa a incluir o hash do
   conteúdo (`.broken-<timestamp>-<sha8>`) e o backup é pulado quando já
   existe um com o mesmo hash; como todo reload reavalia o arquivo, isso impede
   um backup por chamada e por processo.
8. **Windows.** `os.replace` falha se o destino estiver aberto por terceiros
   (antivírus, cliente de sincronização). A gravação é retentada até 5 vezes
   (50, 100, 200, 400 e 800 ms) dentro da trava. Os processos do próprio
   servidor nunca seguram o arquivo aberto durante o replace, porque leituras
   também rodam sob a trava. Permissões 0700/0600 valem no POSIX; no Windows o
   diretório do perfil já restringe o acesso e o servidor não altera ACLs.
9. **Guarda do diretório.** A biblioteca cria o diretório pai do arquivo de
   trava; o store verifica antes que o diretório da memória existe, para que
   um caminho inexistente continue degradando em vez de criar pastas.
10. **Arquivos auxiliares privados.** O arquivo de trava é criado com
    `mode=0o600` e, tal como o `memory.json.log`, é apertado para 0600 a cada
    aquisição ou abertura quando já existia com permissão mais aberta. No Windows
    vale o controle de acesso do perfil do usuário.

## Alternatives considered

### Alternative A: `portalocker`

Trava no próprio arquivo por padrão; sem vantagem sobre `filelock`, que já
estava na árvore como dependência transitiva de desenvolvimento.

**Why not chosen**:
- Dependência nova sem ganho; versão mais recente publicada há menos de 7 dias.

### Alternative B: stdlib (`fcntl` + `msvcrt`)

**Why not chosen**:
- Dois caminhos de código com semânticas diferentes; `msvcrt.locking` trava por
  faixa de bytes e é obrigatório no Windows. É o tipo de código sutil em que
  bugs de concorrência se escondem.

### Alternative C: detectar mudança por `mtime` e travar só nas escritas

**Why not chosen**:
- Resolução de `mtime` de 1–2 s em alguns sistemas de arquivos perde exatamente
  o caso de duas gravações no mesmo segundo, e não protege o `os.replace` no
  Windows.

### Alternative D: SQLite

**Why not chosen**:
- Fora do escopo; permanece como degrau futuro (ROADMAP) se o volume de
  escrita um dia justificar.

### Alternative E: fallback automático para outra memória quando a trava falha

**Why not chosen**:
- Cria duas memórias divergentes em silêncio e parece perda de dado.

## Consequences

### Accepted

- Nenhuma gravação confirmada é perdida entre processos; cada cliente enxerga
  o que o outro gravou sem reiniciar; ids únicos; alerta disparado uma vez.
- Falha de trava nunca vira gravação sem proteção.
- Windows passa a ser plataforma suportada e entra na matriz de CI.

### Trade-offs

- Cada operação relê e reanalisa o arquivo (KB, abaixo de 1 ms): custo aceito
  pela simplicidade.
- Após uma falha de `save`, o store não fica mais "preso" como indisponível: a
  próxima operação relê o arquivo (íntegro) e se recupera. O erro da própria
  gravação que falhou continua sendo `memory_unavailable`.
- A trava protege processos na mesma máquina. Memória em pasta sincronizada
  (Dropbox, iCloud, OneDrive) usada simultaneamente em duas máquinas não é
  protegida: cada máquina trava só a cópia local. Documentado, não detectado.
- Uma dependência de runtime a mais (`filelock`).

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. O backend de persistência migrar para SQLite, que traz controle de
   concorrência próprio.
2. A biblioteca remover ou mudar `fallback_to_soft`, ou o comportamento fail-closed
   deixar de valer.
3. Surgir necessidade de uso simultâneo em várias máquinas.

### Migration path when needed

1. Trocar a biblioteca de trava mantendo a interface `_locked()`.
2. Mover a persistência para SQLite local, mantendo o contrato das tools e o
   changelog append-only.

## References

- ADR-0001 (dependências pinadas; emendado para incluir `filelock`)
- ADR-0002 (fronteira de persistência da memória e entrega de alertas)
- ADR-0004 (modelo de ameaça)
- ADR-0010 (ciclo de vida do bootstrap; migração legada removida na spec 004)
- Constituição 1.2.0, Princípio V.1
- `specs/004-hardening/contracts/memory-concurrency.md`

## Emenda 2026-10-28 (pendências da revisão final da spec 004)

Robustez do arquivo de memória, decidida depois do ciclo 1 da revisão final:

1. **Arquivo apagado com o servidor rodando não é recriado vazio.** O store
   lembra se já leu ou gravou o arquivo neste processo. Se depois disso o
   arquivo some, a memória fica indisponível (`memory_unavailable`) e o
   operador recebe, uma vez, `MEMORY_FILE_VANISHED_MESSAGE` em PT-BR com o
   caminho do histórico `memory.json.log`. Restaurar o arquivo devolve a
   memória na operação seguinte. Reiniciar o servidor começa uma memória vazia,
   que é o caso de primeira execução.
2. **Erro de leitura não é corrupção.** Uma `OSError` ao ler (permissão,
   antivírus, cliente de sincronização) deixa a memória indisponível sem criar
   o backup `.broken-*`, e a operação seguinte tenta de novo. Só JSON inválido
   ou schema inválido geram backup.
3. **Modo somente-leitura não grava nada**, nem o backup de arquivo corrompido.
4. **Gravação durável**: o temporário recebe `fsync` antes do `os.replace`,
   para que uma queda de energia não deixe um `memory.json` vazio.
5. **Changelog sem seguir symlink**: o `memory.json.log` é aberto com
   `O_NOFOLLOW` (quando o sistema oferece) e restrito a 0600 pelo descritor
   (`fchmod`), não pelo caminho. Um symlink no lugar do log faz a linha falhar
   com aviso, e a gravação na memória segue (FR-017). Se a restrição a 0600
   falhar em qualquer arquivo lateral, o operador recebe
   `TIGHTEN_FAILED_MESSAGE`.
6. **Texto do retry**: o item 8 já dizia "retentada até 5 vezes", ou seja, 6
   tentativas no total (a primeira mais 5). O contrato `memory-concurrency.md`
   dizia "até 5 tentativas" e foi corrigido para "até 5 novas tentativas (6 no
   total)". O código não mudou.

## Emenda 2026-10-29 (revisão final da spec 004, ciclo 3)

1. **`ENOLCK` não deixa a memória somente-leitura.** Ele pode significar a
   tabela de travas do kernel cheia, que é passageira. Agora falha uma operação
   com `memory_unavailable`, e a seguinte tenta de novo. Só `ENOSYS` e
   `EOPNOTSUPP` (sistema de arquivos sem trava) fixam o modo somente-leitura.
2. **Trava também entre threads.** O `FileLock` com `thread_local=False` é
   reentrante para o processo inteiro: uma segunda thread entraria sem esperar,
   pulando o reload e alterando `self.data` junto com a primeira. A
   profundidade de reentrada passou a ser por thread (`threading.local`), e um
   `threading.Lock` protege a trava de arquivo. Outra thread espera até o
   timeout e recebe `memory_busy`. Hoje todas as tools rodam no loop asyncio,
   numa thread só, então isso fecha uma armadilha latente, não um bug ativo.
3. **O arquivo de memória nunca é lido por symlink.** A leitura usa `os.open`
   com `O_NOFOLLOW` e lê os bytes pelo descritor. O backup de arquivo corrompido
   grava esses mesmos bytes, sem reabrir o caminho. Um `memory.json` que vira
   link depois da partida (ou um `WALLET_MEMORY_PATH` que já é um link) deixa a
   memória indisponível, com aviso `MEMORY_SYMLINK_MESSAGE` ao operador, e o
   link nunca é seguido nem substituído.
4. **Trava restringida pelo descritor.** O `memory.json.lock` é aberto com
   `O_NOFOLLOW` só para o `fchmod` 0600, e nunca por `chmod` no caminho.
