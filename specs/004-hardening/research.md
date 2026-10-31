# Research — spec 004 Hardening

Fontes primárias consultadas em 2026-10-27: código instalado em `.venv/`
(`fastmcp==4.0.11`, `filelock==4.2.2`), docs oficiais do FastMCP
(gofastmcp.com via Context7: `/servers/server`, `/clients/tools`,
`/python-sdk/fastmcp-tools-base`), PyPI JSON API (`filelock`, `portalocker`),
e probes na API do Investidor10 que imprimiram **só nomes e tipos de campo**,
nunca valores (carteira pública do mantenedor). Pesquisa anterior reaproveitada:
`docs/research/tool-error-channels.md`.

---

## D1 — Biblioteca de trava entre processos

**Decision**: `filelock==4.2.4` como dependência direta de runtime, usando
`FileLock(<memória>.lock, timeout=5, fallback_to_soft=False,
thread_local=False)`.

**Rationale**:
- Já está na árvore resolvida (`filelock 4.2.2`, transitiva de
  `pre-commit → virtualenv`, grupo dev). Promover para runtime não adiciona
  autor/supply chain novo ao projeto.
- Multiplataforma com um só import: `fcntl.flock` no Unix (`_unix.py`),
  `msvcrt.locking` no Windows (`_windows.py`) — a escolha da opção C da
  clarificação.
- Trava num **arquivo separado** (`memory.json.lock`). Isso é obrigatório
  aqui: a gravação atômica faz `os.replace` do `memory.json`, trocando o
  inode; uma trava no próprio arquivo de dados se perderia a cada save.
- Trava do kernel: liberada automaticamente quando o processo morre (edge
  case da spec), ao contrário de trava por existência de arquivo.
- `fallback_to_soft=False` (docs da classe, `_api.py`: "fails closed,
  letting the ENOSYS propagate so a caller that needs kernel-enforced
  locking is never silently downgraded"). **O default `True` violaria o
  FR-039**: num sistema de arquivos sem `flock`, a biblioteca trocaria em
  silêncio para `SoftFileLock`, cuja trava sobrevive a crash e travaria
  todos os processos até intervenção manual.
- 4.2.4 publicada em 2026-10-19 (8 dias) — cumpre o mínimo de 7 dias
  (Constituição V.1). `requires_python >=3.11`, sem dependências.
- `thread_local=False`: o servidor é asyncio num único thread; o lock é
  reentrante por instância, o que simplifica funis aninhados.

**Alternatives considered**:
- `portalocker` 4.4.x: trava no próprio arquivo por padrão; a release
  mais recente (4.4.2) tem 0 dias; extra `pywin32` opcional. Sem vantagem
  sobre `filelock`, que já está na árvore.
- stdlib (`fcntl` + `msvcrt` escritos à mão): rejeitada na clarificação
  (semântica obrigatória e por faixa de bytes do `msvcrt`, mais código
  próprio de concorrência).

**Constituição**: emenda 1.2.0 (V.1) autoriza exatamente uma biblioteca de
trava escolhida por ADR → ADR novo (D11) + atualização do ADR-0001 §4.

---

## D2 — Modelo de concorrência do `MemoryStore`

**Decision**: toda operação pública (leitura e escrita) roda dentro de
`with self._lock:` e **recarrega o arquivo do disco no início**. Escritas:
recarregar → validar → mutar → changelog → `save()` → liberar. Leituras:
recarregar → ler → liberar.

**Rationale**:
- FR-002/FR-003 (ler-modificar-gravar sob a trava; leituras refletem o
  disco). Recarregar sempre é mais simples que detectar mudança por
  `mtime`/tamanho (Constituição, "Simplicidade primeiro"): o arquivo tem
  KB e o parse custa menos de 1 ms. A detecção por `mtime_ns` falha em
  sistemas de arquivos com resolução de 1–2 s, e o caso do teste (duas
  gravações no mesmo segundo) é exatamente o que precisa funcionar.
- Leituras também sob a trava garantem que nenhum processo tenha o
  `memory.json` aberto durante o `os.replace` de outro. No Windows isso é
  pré-requisito de correção (D3).
- `next_id` e `evaluate_alerts` passam a rodar dentro da mesma seção
  crítica da escrita (FR-004): o id é calculado sobre o estado recém-lido
  e a transição `active → triggered` só se aplica se, após o reload, o
  alerta ainda estiver `active` (a segunda sessão concorrente não o
  dispara de novo — US1 cenário 3).
- `get_session_context` hoje lê o digest e depois avalia alertas em
  chamadas separadas, buscando cotações (I/O de rede) entre elas. **A
  trava não pode ser segurada durante a busca de cotações** (até 20 s por
  cotação). Fluxo: (1) digest + lista de ativos sob trava, (2) cotações
  sem trava, (3) `evaluate_alerts(quotes)` sob trava, recarregando e
  reavaliando só os que seguem `active`.
- Timeout de 5 s → `filelock.Timeout` → novo código `memory_busy`
  (FR-005).
- O estado `available=False` (arquivo corrompido ou versão desconhecida)
  passa a ser **reavaliado a cada reload**: se o usuário consertar o
  arquivo à mão, o processo volta a operar sem reinício. É mais simples
  que manter o modo degradado "grudado" e coerente com FR-003.

**Backup único sob concorrência** (edge case): o backup `.broken-*` passa
a embutir um hash curto do conteúdo (`.broken-<timestamp>-<sha256[:8]>`) e
é pulado quando já existe um `.broken-*-<mesmo hash>`. Dois processos que
encontram o mesmo arquivo corrompido geram um só backup; um conteúdo
corrompido diferente gera outro.

**Alternatives considered**: SQLite (fora de escopo — roadmap,
"degrau futuro"); trava só nas escritas com detecção por `mtime` (falha
nos casos de resolução de tempo e não protege o `os.replace` no Windows).

---

## D3 — Gravação atômica e permissões no Windows

**Decision**:
- Manter `tempfile` no mesmo diretório + `os.replace`. Com D2, nenhum
  processo do servidor mantém o arquivo aberto durante o replace. Para
  terceiros (antivírus, indexador, cliente de sincronização segurando o
  arquivo), `os.replace` com `PermissionError` é **retentado até 5 vezes
  com backoff curto (50→800 ms)**, ainda dentro da trava; persistindo,
  vira `MemoryUnavailableError` como hoje.
- Permissões: no POSIX, mantém 0700 no diretório e 0600 no arquivo, no
  changelog e na trava. No Windows, `os.chmod` só controla o bit de
  leitura; o local canônico (`%USERPROFILE%\.investidor10`) herda a ACL
  do perfil, restrita ao usuário. Não mexemos em ACLs (Assumptions da
  spec).
- Recusa de symlink no arquivo canônico: `os.lstat` + `stat.S_ISLNK`
  funcionam no Windows (Python ≥3.8). Os testes que criam symlink são
  pulados no Windows quando `os.symlink` exige privilégio (`OSError`).

**Rationale**: o comportamento documentado do `os.replace` no Windows
(falha se o destino estiver aberto sem `FILE_SHARE_DELETE`) é a fonte do
problema; o protocolo de trava de D2 elimina o caso entre os nossos
processos, e o retry cobre os segurados por terceiros, que são
transitórios.

**Matriz de CI**: `windows-latest` entra na matriz. Testes POSIX-only
(fake binaries `#!/bin/sh` do assistente de instalação, asserts de modo
0700/0600) ganham `skipif(sys.platform == "win32")` com motivo explícito;
os testes do `MemoryStore`, da trava e do changelog rodam nas três
plataformas.

---

## D4 — Sistema de arquivos sem suporte a trava (FR-039)

**Decision**: na construção do `MemoryStore`, uma sonda de trava
(adquire/libera). `OSError(ENOSYS)` (propagado por
`fallback_to_soft=False`) coloca o store em **modo somente-leitura**:
- leituras: reload sem trava (melhor esforço, sem garantia de exclusão);
- escritas: erro `memory_read_only` com mensagem para o modelo;
- operador: uma mensagem PT-BR em stderr na inicialização com causa e
  conserto (`WALLET_MEMORY_PATH` em disco local);
- `get_session_context`: devolve o digest, **não avalia alertas** (avaliar
  é escrita) e informa `memory_status: "read_only"`.

**Rationale**: decisão da clarificação (opção B, sem fallback). Não há
como gravar com segurança; também não se troca de arquivo.

**Note**: o Dropbox/iCloud/OneDrive são pastas locais — a sonda passa e a
trava funciona na mesma máquina. O caso de duas máquinas não é detectável
(D10, documentação).

---

## D5 — Changelog append-only (`memory.json.log`)

**Decision**: JSONL em `<caminho da memória>.log`, uma linha por mutação:
`{ts, pid, op, collection, id, before, after}`. Escrito **sob a trava,
antes do `save()`**, com `open(..., "a")` (no POSIX, criado com
`os.open(O_WRONLY|O_CREAT|O_APPEND, 0o600)`). Falha de escrita do log →
aviso PT-BR em stderr e a operação segue (FR-018).

Pontos de emissão (FR-016): `add()` (op `create`, `before: null`),
`update()` (op `update`), `set_wallet_goal()` (op `set`, collection
`wallet_goal`, `id: null`) e `evaluate_alerts()` (op `trigger`, uma linha
por alerta). `cancel_price_alert` e `record_decision_outcome` passam por
`update()` e saem como `update`. Detalhe em `data-model.md`.

**Rationale**: roadmap (arquivo separado, logar antes do save, best-effort,
sem rotação). `pid` entra porque agora há vários processos — é o único
jeito de saber, na forense, qual cliente fez a gravação. `before`/`after`
como cópias profundas (o `entry.update()` atual muta o dict no lugar).

**`.gitignore`**: `memory.json.log`, `memory.json.lock` e `*.broken-*`
(se ainda não estiverem).

---

## D6 — Sinal duplo de erro

**Decision**: estender o middleware existente (renomeado
`ErrorSignalMiddleware`): depois de `call_next`, se o `ToolResult` tiver
`structured_content` com uma chave de topo `error`, devolver
`ToolResult(structured_content=..., is_error=True)`. O caminho do
`ValidationError` (`invalid_params`) passa a sair com `is_error=True`
também. As tools continuam retornando o dict do envelope — nenhuma tool
muda de assinatura.

**Rationale**:
- `ToolResult.__init__` (fastmcp 4.0.11, `tools/base.py:114–156`): sem
  `content` explícito, o content vira a serialização JSON do
  `structured_content` → **o texto da resposta carrega `code` e
  `message`** (FR-022) sem código extra.
- `to_mcp_result` (`tools/base.py:179–186`): "An error result must
  round-trip through CallToolResult so isError reaches the client" — o
  flag chega ao cliente junto com o `structured_content`.
- Docs oficiais (gofastmcp.com/clients/tools): `CallToolResult.is_error`
  "indicating if the tool execution failed"; `call_tool` levanta por
  padrão e `raise_on_error=False` dá acesso ao resultado. Alinha com
  SEP-1303/2145 (erro corrigível pelo modelo = tool execution error).
- Um ponto único (o middleware) é mais simples e não esquece tool nenhuma.
  Falso positivo é impossível: nenhum envelope de sucesso tem `error` no
  topo (`{cached, fetched_at, data}` ou `{<coleção>: ...}`).
- Exceções inesperadas continuam no canal B do framework (Constituição
  II.3) — o middleware não as converte.

**Impacto nos testes**: chamadas via `fastmcp.Client.call_tool` que
esperam um payload de erro passam a precisar de `raise_on_error=False`
(o client levanta `ToolError` por padrão). São os testes de contrato em
`tests/contract/test_tools_schemas.py`.

---

## D7 — Retentabilidade/categoria no envelope (FR-025)

**Decision**: **não** adicionar campo `retryable`/`category`. O envelope
segue `{error: {code, message}}`. O contrato publica uma tabela fixa
código → "tentar de novo?" → próxima ação (contracts/error-envelope.md), e
a `message` diz a próxima ação no estilo trigger-phrase.

**Rationale**: o conjunto de códigos é fechado e pequeno (11 após esta
feature); a retentabilidade é função do código, então um campo seria
redundante e poderia divergir dele. O sinal que o modelo usa é a
`message` (evidência da pesquisa: nomear a tool → modelo a chama >80%).
Registrado no ADR do sinal duplo.

---

## D8 — Modo privacidade: lista de campos permitidos

**Decision**: módulo `privacy.py` com allowlist por tool, aplicada **na
saída** da tool (depois do cache, que guarda o payload cru). Probe de
2026-10-27 (só chaves/tipos):

| Tool | Permitidos (atravessam) | Omitidos (montante/quantidade ou desconhecido) |
|---|---|---|
| `get_wallet_summary` (`/summary/metrics`) | `type`, `variation`, `profit_twr`, `profit_twr_12m`, `currency` | `applied`, `equity`, `profit_amount`, `profit_twr_12m_amount` |
| `get_wallet_allocation` (`/summary/donutchart`, lista) | `name`, `type`, `percent` | `value` |
| `get_wallet_positions` (topo) | `total` (contagem de posições), `draw` | `weighted` (semântica não confirmada → fail-closed) |
| `get_wallet_positions` (por posição) | identificação: `id`, `tickerable_id`, `ticker`, `ticker_name`, `ticker_type`, `currency`, `url`, `image`, `country`, `iso_alpha_2`, `segment`, `fii_type`; pesos: `percent_wallet`, `percent_ideal`, `buy`; preço por unidade: `avg_price`, `user_avg_price`, `avg_price_treasure`, `current_price`, `current_price_treasure`, `target_price`; % e razões: `appreciation`, `weighted_return`, `profitability`, `yoc`, `dy`, `dividend_yield_last_5_years`, `payout`, `p_l`, `p_vp`, `roe`, `net_margin`, `gross_margin`, `profit_1`, `profit_7`, `profit_30`, `profit_365`; notas: `rating`, `raw_rating`, `avg_rating`, `raw_avg_rating`, `checklist_rate`; preço justo: `graham`, `bazin`; dados públicos do ativo: `vacancy`, `quotes_count`, `shareholders`, `net_worth`, `last_yield`, `equity_per_share`, `capitalization`; flags: `is_calculating_rentability` | `quantity`, `equity_brl`, `equity_total`, `earnings_received`, `target_price_amount`, `gnr`, `gnp`, `ranking`, e qualquer campo fora da lista |
| `get_patrimony_history`, `get_earnings` | — | tool inteira → erro `privacy_mode_unavailable` |
| `get_asset_quote` | inalterada (dado de mercado) | — |
| tools de memória e `get_session_context` | inalteradas (texto do usuário; alertas são preços de mercado) | — |

`variation` foi confirmado como percentual (comparação local
`variation ≈ (equity/applied − 1)·100`, só o booleano impresso).
`net_worth`, `shareholders`, `equity_per_share` são do **fundo** (FII), não
do investidor. `gnr`/`gnp` e `ranking` têm semântica não confirmada →
omitidos (fail-closed; podem ser liberados depois com evidência).

Marcador na resposta (FR-012): o envelope ganha
`"privacy": {"masked": true, "omitted": [<campos removidos nesta resposta>]}`
ao lado de `cached`/`fetched_at`. As docstrings das 3 tools mascaráveis
ganham uma frase: "when `privacy.masked` is true, amounts were withheld by
the operator — never estimate or reconstruct them".

**Config** (FR-014): `WALLET_MASK_VALUES` lido em `bootstrap.load_config`;
`1/true/yes/on` → ligado, `0/false/no/off`/ausente → desligado,
case-insensitive, espaços aparados; qualquer outro valor → `fail()` PT-BR.

**Rationale**: allowlist é fail-closed (FR-011); aplicar depois do cache
garante que alternar o modo entre execuções nunca vaze dado cru (o cache é
em processo e o modo é fixo por processo). Os nomes vêm do payload real,
não de suposição.

**Alternatives considered**: denylist (vaza campo monetário novo da fonte);
mascarar no `wallet_client` antes do cache (acopla privacidade ao
transporte e complica testes).

---

## D9 — Execução semanal dos testes `live` (removida da spec)

Movida para o roadmap em 27/10/2026, com as decisões já tomadas (carteira
pública fictícia, segredo do repositório, asserts sem payload, default do
`conftest.py` sem a carteira real). A validação em tempo de execução do
`wallet_client` continua sendo a proteção do usuário contra drift.

---

## D10 — Documento de privacidade

**Decision**: `docs/PRIVACY.md` (PT-BR), linkado no topo do README e na
mensagem final do assistente de instalação (`installer/cli.py`).
Conteúdo mínimo em `contracts/privacy-doc.md`.

---

## D11 — ADRs e documentação de decisão

| ADR | Assunto |
|---|---|
| 0013 | Concorrência da memória: trava `filelock` (fail-closed), reload sob trava, modo somente-leitura, changelog append-only, suporte Windows — atualiza ADR-0001 §4 (deps) e referencia a emenda 1.2.0 |
| 0014 | Sinal duplo de erro (`isError` + envelope) — emenda o ADR-0007; decisão D7 (sem `retryable`); 3 códigos novos |
| 0015 | Modo privacidade `WALLET_MASK_VALUES` — env var, allowlist, marcador `privacy` |
| 0016 | Regra de validação de payloads para tools novas (validate-then-passthrough com pydantic, sem retrofit, sem schema da memória) — pydantic é transitiva do FastMCP, não é dependência direta; a regra exige que continue transitiva ou que haja emenda |
| 0010 (emenda) | Condição de invalidação nº 1 antecipada: migração legada removida na 0.3.0 |

Learning lesson nova: "`filelock` troca para soft lock em silêncio por
padrão quando o FS não suporta flock" (fato verificado do upstream).

---

## D12 — `instructions=`

**Decision**: `FastMCP("investidor10-wallet", instructions=INSTRUCTIONS)`,
em inglês (ADR-0009), com propósito + índice: o que é; comece por
`get_session_context`; dados vêm em envelope `{cached, fetched_at, data}`
e erros em `{error: {code, message}}`; cotações B3 com ~15 min de atraso;
`privacy.masked` quando o operador ligou o modo privacidade. Sem persona,
idioma ou tom (Constituição III.2). Docs oficiais: "Instructions help
clients (and the LLMs behind them) understand what your server does and
how to use it" (gofastmcp.com/servers/server).

---

## D13 — Remoção da migração legada

**Decision**: `resolve_memory_path(home=None, environ=None)`:
override → retorna verbatim; senão → `_ensure_canonical_dir` +
`_ensure_not_symlink` → retorna o canônico. Removem-se `_atomic_copy`,
os ramos de conflito/migração, as mensagens `MIGRATION_FAILED_MESSAGE`,
`MIGRATED_MESSAGE` e `CONFLICT_RESOLVED_MESSAGE`, e o parâmetro `cwd`/`now`.
Os testes de migração saem; um teste novo garante que um `memory.json` no
cwd não é lido, copiado nem alterado (SC-008). Contrato da spec 002 §4
anotado como superado pela 004; nota de release no `CHANGELOG.md`.

---

## D14 — Versão

**Decision**: `0.3.0` (MINOR em 0.x, ADR-0011): mudança de canal de erro
(clientes que tratavam erro como sucesso passam a ver `isError`), nova
dependência, remoção da migração.
