# ADR-0004: Threat model and security boundary of the single-user stdio server

- **Status**: Accepted (amended 2026-10-31 — see "Emenda 2026-10-28" and "Emenda 2026-10-31" at the end)
- **Date**: 2026-10-17
- **Deciders**: Tech Leader + user (SDD final review cycle 4, spec 001)

## Context

Every security review cycle (2, 3 and 4) re-derived the same threat model from
scratch to classify findings: the indirect prompt-injection LOWs, the runtime
`memory.json` created mode 0644, malformed env crashing at import, and the
scoped FastMCP GHSAs were all judged against an unrecorded mental model of what
this server is and who can attack it. Recording that model once prevents
re-litigating the same classification every cycle and defines the boundary that
decides whether a finding is a vulnerability, an accepted design property, or an
operator error.

## Decision

1. **Deployment shape**: the server is a single-user, single-wallet process
   spawned by a local MCP client over **stdio**. It never opens a network
   listener and never runs as a service.

2. **Authentication is delegated**: the local MCP client config owns `WALLET_ID`
   (a public wallet identifier, not a secret). The server authenticates nothing
   and trusts the local operator — whoever can edit the client config or the
   local files is already in the trust boundary. *Amended 2026-10-28: the ID
   works as a read credential — see "Emenda 2026-10-28".*

3. **Fixed outbound surface**: the only network egress is
   `https://investidor10.com.br` (wallet proxy + REST assets). There are no
   user-controlled URLs; `WALLET_ID` is validated digits-only and tickers pass a
   charset allowlist (`[A-Z][A-Z0-9]{3,11}`) before any URL is built — closing
   the URL/path-injection path.

4. **No secrets**: no API keys, tokens or credentials exist anywhere in the
   system; nothing is written to logs. *Amended 2026-10-28: the memory
   changelog `memory.json.log` is local personal data at rest — see "Emenda
   2026-10-28".*

5. **Local memory is trusted data**: `memory.json` is user-authored local data,
   treated like any other local config. Corrupted files degrade the store
   instead of crashing (ADR-0002). Memory text and upstream JSON are returned
   verbatim to the agent LLM at session bootstrap — an accepted indirect
   prompt-injection surface inherent to the product (a memory assistant); this
   server executes nothing.

6. **On-disk integrity**: atomic writes via private 0600 temp files +
   `os.replace`, backups `.broken-*` 0600/O_EXCL (ADR-0002), bounded stale
   cache (ADR-0003). The one-time `chmod 600 memory.json` applied in cycle 4
   aligned the pre-hardening runtime file with the new 0600 writes.

7. **No side effects**: all calls to the source are read-only GETs; the server
   never places orders (spec assumption: suggestions only, execution is the
   user's).

8. **Dependency posture**: fastmcp and httpx pinned (research D9). The Oct-2026
   FastMCP GHSAs in range for 4.0.10 affect client/OpenAPI surfaces this server
   never instantiates — accepted as scoped risk with a scheduled tested upgrade
   to >=4.1.0 as hardening. Atualizado 2026-10-27: upgrade para
   `fastmcp==4.0.11` executado no ciclo spec 003 (patch que corrige o GHSA
   crítico do client — superfície que este servidor não instancia), com suíte
   completa verde; a meta >=4.1.0 permanece como hardening agendado.
   Atualizado 2026-10-28: upgrade para `fastmcp==4.1.2` executado (corrige
   GHSA-7xgj-8392-5q4r e GHSA-vqqp-x5qm-5qp4), com `authlib` 1.9.1 e
   `certifi` 2026.10.19 no lock; suíte completa verde e `pip-audit` sem
   achados. A política de atualização ficou no ADR-0001 (emenda 2026-10-28).

## Consequences

- Security findings are classified against this model: misconfiguration by the
  local operator (bad env, loose file perms) is not an attacker boundary;
  anything requiring a network listener, multi-user access, secrets, new
  outbound hosts, or order execution WOULD be.
- The single-user scope keeps auth, rate limiting and audit logging out of the
  product by design (A01/A04/A09 do not apply at this boundary).
- This decision should be **revisited** if: the server gains a network
  transport or multi-user scope; outbound hosts grow beyond investidor10.com.br
  (e.g. an international quotes source per the learning lesson
  `get_asset_quote_apenas_acoes_b3`); secrets are introduced; or web-fetched
  content starts being executed or written to disk by this process.

## Emenda 2026-10-28 (spec 004)

Duas decisões acima ficaram desatualizadas e foram reconciliadas com a spec 004
e o ADR-0015:

- **Item 2 (ID da carteira)**: o ID continua não sendo um segredo no sentido de
  chave de API (o servidor não autentica nada), mas **funciona como credencial de
  leitura**: quem o possui lê todos os valores da carteira pela API, e o botão de
  mascarar do site é só visual. Deve ser tratado como senha na divulgação (ver
  `docs/PRIVACY.md`). O modo privacidade protege o que vai ao modelo, não quem
  tem o link.
- **Item 4 (logs)**: o servidor continua sem registrar segredos nem payloads da
  fonte, mas passou a gravar o **histórico de mudanças da memória**
  (`memory.json.log`), com cópias do estado anterior e novo de teses, regras,
  decisões e alertas. É dado pessoal em repouso, local, com modo 0600 (também o
  arquivo de trava `memory.json.lock`), fora do controle de versão
  (`.gitignore`) e sob a mesma fronteira de confiança do `memory.json`. Não há
  rotação nesta versão.

## Emenda 2026-10-29 (revisão final da spec 004, ciclo 3) — ID real no repositório

O ID da carteira do mantenedor aparecia em specs, docs e relatórios, embora a
emenda acima o trate como credencial de leitura. Ele foi trocado por `<id>` em
todos os arquivos do working tree, e os testes usam o fictício `1234567`. O ID
continua no **histórico do git**, e reescrever o histórico de um repositório
público não o tira de clones e forks já feitos. A decisão fica com o
mantenedor, que tem duas saídas: aceitar que essa carteira é pública (ela já é
pública por desenho do produto) ou deixá-la privada no Investidor10 e usar
outra carteira pública para os testes live.

## Emenda 2026-10-31 (revisão final da spec 004, ciclo 6) — o ID não aparece em texto visível ao modelo

A emenda de 28/10/2026 trata o ID da carteira como credencial de leitura, mas as
mensagens de erro da fonte (`SourceError`) o repetiam: elas citavam o caminho da
requisição, que contém o ID, e o `mask_error_details` não as cobre, porque o
`SourceError` volta como resultado normal da tool, não como exceção. Com
qualquer ferramenta de busca na web no cliente, ou com texto da fonte tentando
instruir o modelo, o ID leria os valores brutos da API pública e anularia o
`WALLET_MASK_VALUES`.

Agora o `WalletClient` troca o ID por `<wallet>` num único ponto
(`WalletClient._redact`), que cobre o caminho nas mensagens e o texto das
exceções do `httpx`. A requisição e a chave do cache continuam usando o caminho
real, e a dica "check WALLET_ID" dos 4xx do proxy permanece. A saída para o
operador (stderr, `bootstrap`) não muda: quem opera o servidor é dono do ID
(ADR-0009). O mesmo vale para o que o modelo vê em qualquer tool: nenhum texto
de erro que ele recebe carrega o ID. Os caminhos absolutos da memória local em
`memory_error_payload` seguem como pendência registrada no ROADMAP.

## Emenda 2026-10-31 (revisão final da spec 004, ciclo 7) — o ID voltou a um arquivo versionado

O ciclo 7 achou o ID real da carteira num relatório do ciclo 5 (a linha de
verificação de que ele havia sido removido o citava), versionado desde
31/10/2026 em `main` e nas branches `spec-004/*`. Isso reabriu, depois da
reescrita de 29/10/2026, o que a emenda "ID real no repositório" havia fechado.
Pior, o sdist da `0.3.0` incluía `reports/`, `specs/` e `docs/`, e um build local
levava junto a config local do Devin com o ID, porque o empacotador só respeita o
`.gitignore`.

Medidas no working tree (sem reescrever o histórico):

- O ID foi trocado por `<id>` no relatório.
- `scripts/check-no-wallet-id`, hook local do pre-commit, lê `WALLET_ID` do
  ambiente e falha se o valor estiver em arquivo versionado; ele não é ligado ao
  CI, porque isso exigiria guardar o ID como secret do repositório.
- O sdist inclui só `/src` e `/CHANGELOG.md`; o wheel já continha só o pacote.
  Um sdist e um wheel construídos depois da mudança não têm o ID.

**Decisão do mantenedor (2026-10-31): aceitar que a carteira é pública.** O ID
segue no histórico de `main` e das branches `spec-004/*`. Reescrevê-lo exigiria
force-push num repositório público e não o tiraria dos `refs/pull/*`, de clones e
forks nem de sdists antigos do PyPI; o mantenedor escolheu não reescrever e manter
a carteira pública, que já é pública por desenho do produto (opção A das três
avaliadas, junto com reescrever o histórico e trocar ou privar o link no
Investidor10). Consequência aceita: o ID antigo continua alcançável nesses lugares.
O que a medida acima garante é que ele não volte ao working tree nem entre no
sdist e no wheel publicados daqui para frente.

