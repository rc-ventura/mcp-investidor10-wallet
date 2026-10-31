# ADR-0002: Memory persistence boundary and alert delivery semantics

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Tech Leader (SDD final review cycle 2, spec 001)

## Context

The investor memory (goal, theses, rules, decisions, insights, price alerts)
is persisted to a single local `memory.json` (research D5/D6) and price alerts
are evaluated only at session open (research D7). Review cycles 1 and 2 found
that the boundary behavior was incomplete:

- unreadable files, wrong shapes, duplicate IDs and oversized numbers were not
  fully contained;
- alert triggers were persisted one-by-one, so a failure mid-evaluation could
  persist a trigger while losing its notification (SC-006 violation);
- there was no recorded decision for the failure semantics.

## Decision

1. **Single versioned store**: memory remains one versioned `memory.json`
   loaded fully into memory, written atomically via a private temporary file
   (`tempfile.NamedTemporaryFile`, default 0600) followed by `os.replace`.

2. **Degraded-mode classes**: the store degrades (`available=False`) instead of
   crashing for: unreadable files (OSError), unparseable/non-standard JSON,
   non-dict payloads, missing/non-int/duplicate entry IDs per collection,
   unknown schema versions. A degraded store never overwrites the original
   file; corrupted files are preserved best-effort as `.broken-<timestamp>`
   (0600, O_EXCL). Future schema versions are left untouched (no backup).

3. **Per-collection identity**: every entry in every collection must have a
   unique positive integer `id`; files violating this degrade at load instead
   of risking duplicate find/update behavior.

4. **Alert delivery**: all satisfied alerts are mutated in memory and persisted
   in ONE atomic save. If the save fails, nothing is persisted and every alert
   remains active for the next session — a partially delivered notification is
   impossible. A trigger is considered communicated only after the successful
   save; a crash between the save and the agent receiving the response may
   still lose that notification (accepted for the local single-user scope).

5. **Invalid persisted alerts**: structurally invalid alert entries are
   reported in `pending_check` as `invalid_alert` at bootstrap and skipped by
   evaluation — never a raw exception, never a full-store degradation.

6. **Unsupported-class alerts**: alerts on asset classes without B3 quotes
   (FIIs, international ETFs, crypto, treasury) are allowed and reported in
   `pending_check` with the source reason (`asset_type_not_supported`).

## Consequences

- Memory tools return structured `memory_unavailable` while degraded; data
  tools keep working (spec edge case).
- `evaluate_alerts` performs a single save per session bootstrap instead of
  one per trigger; failure semantics are all-or-nothing per evaluation.
- Future migration to SQLite (research D5) must preserve these semantics:
  unique positive IDs per collection and all-or-nothing trigger persistence.
## Emenda 2026-10-29 (revisão final da spec 004, ciclo 4)

**Toda falha ao interpretar o arquivo segue o caminho de corrupção do §2,
inclusive `RecursionError`.** Um `memory.json` aninhado demais fazia
`json.loads` levantar `RecursionError`, que não é `ValueError`: a exceção
escapava do tratamento, o store ficava com `available=True` e dados velhos,
nenhum `.broken-*` era criado e toda operação seguinte falhava com erro
genérico mascarado. Aninhamento moderado (centenas de níveis) passava pelo
`json.loads`, mas quebrava depois em `copy.deepcopy` e em `json.dump(indent=2)`,
que recursam em Python. Agora a carga rejeita, numa varredura iterativa,
qualquer arquivo mais fundo que `MAX_NESTING_DEPTH` (32; o esquema usa 4
níveis), e `RecursionError` entra no mesmo `except` de `ValueError`. Os dois
casos geram backup, `available=False` e `memory_unavailable` estruturado.

**O arquivo local não ganha teto de tamanho em bytes.** O cliente remoto tem
`MAX_RESPONSE_BYTES` porque a resposta vem de terceiro. O `memory.json` pertence
ao mesmo usuário que roda o servidor (ADR-0004), e quem consegue escrever nele
já controla a conta. Um arquivo grande só custa tempo proporcional ao que o
usuário gravou. Um teto transformaria uma memória legítima de longo prazo em
`memory_unavailable`, sem caminho de migração. A profundidade é limitada porque
derruba o processo de interpretação; o tamanho não, porque só custa tempo.
