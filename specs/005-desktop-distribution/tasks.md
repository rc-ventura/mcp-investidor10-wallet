---
description: "Task list for spec 005 - Distribuição Desktop"
---

# Tasks: Distribuição Desktop — plugin único, página local de configuração e carteira restrita

**Input**: Design documents from `/specs/005-desktop-distribution/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (`wallet-setup.md`, `error-envelope.md`, `cli.md`, `plugin-package.md`), quickstart.md

**Tests**: OBRIGATÓRIOS — a Constituição exige TDD (escrever, ver falhar,
implementar, ver passar; correção de bug começa por teste que a reproduz).
Em cada fase os testes vêm antes da implementação e a implementação NUNCA é
paralela ao teste correspondente.

**Organization**: tasks agrupadas por user story. **As fases seguem a ordem
de dependência do plan, não a numeração das USs** (cada US continua
testável sozinha): Fluxo de branches → Spike → Fundação → US2 → US1 (servidor,
pré-lançamento, plugin) → US7 → US5 → US6 → US3 → US4. A US2 vem antes da US1 porque corrige o diagnóstico de acesso recusado
para os usuários atuais e entrega o conceito de "link como entrada" que a
US1 usa; a US4 (matriz de máquinas limpas) fecha porque verifica tudo.

**Execução**: SEQUENCIAL em lotes com branch própria e gate de aprovação do
mantenedor entre lotes (convenção das specs 003 e 004) — ver "Fatiamento" no
fim. Cada lote sai de `develop` e volta por pedido de revisão contra
`develop`; `main` só recebe versões já publicadas (ADR-0020). Tags, aprovação
da publicação e merges são do mantenedor. Marcas `[P]` descrevem apenas o
desenho lógico.

Termos padronizados: **"configuração local"** (`~/.investidor10/config.json`),
**"servidor empacotado"** (`plugin/servers/carteira.mcpb`, embalagem interna
do servidor dentro do plugin, invisível ao usuário), **"estado pendente"**
(sem carteira configurada).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: [US1]…[US7] conforme spec.md
- Caminhos exatos de arquivo em cada task
- Regras globais de código (Constituição, Formato e Estilo): sem docstring de
  módulo, sem emojis, comentários de no máximo uma linha e só quando
  indispensável, nenhuma menção a ADR/FR/SC/spec dentro do código ou
  comentários, `TODO` como único marcador de revisão; mensagens de operador
  em PT-BR e mensagens ao modelo em inglês (ADR-0009)
- Nunca escrever o ID nem a credencial da carteira do mantenedor em arquivo
  versionado: usar `<id>` e `<hash>`; testes contra a API real usam a
  carteira fictícia dedicada pelo ambiente

## Path Conventions

Pacote: `src/investidor10_wallet/` · Testes: `tests/unit/`, `tests/contract/`,
`tests/integration/`, `tests/fixtures/` · Plugin: `plugin/` · Scripts:
`scripts/` · Docs: `docs/`, `docs/adrs/`, `docs/learning-lessons/` · CI:
`.github/`

---

## Phase 0: Fluxo de branches e release — Lote 0

**Purpose**: estabelecer o fluxo de branches e o portão de promoção para `main` antes de qualquer lote (FR-032 a FR-034, ADR-0020). BLOQUEIA todos os lotes: os documentos da spec e cada lote entram por `develop`.

- [X] T001 [mantenedor] Criar a branch `develop` a partir de `main` e publicá-la no repositório; abrir o pedido de revisão `spec-005/documentos` contra `develop` com `specs/005-desktop-distribution/`, `docs/research/fichamentos/` e `CLAUDE.md`

### Tests (escrever primeiro; DEVEM falhar antes de T005)

- [X] T002 [P] Criar `tests/unit/test_check_promotion.py` para `scripts/check_promotion.py` (stdlib; opções `--head-ref`, `--head-sha`, `--repo-root` e `--index-url`): o script sai com 0 só quando (a) `--head-ref` casa `promote/vMAJOR.MINOR.PATCH` sem sufixo de pré-lançamento; (b) `--head-sha` é igual ao commit da tag `v<versão>`, resolvido com `git rev-parse v<versão>^{commit}` num repositório temporário do teste; (c) a `version` de `plugin/.claude-plugin/plugin.json`, dos outros três manifestos e do manifesto do servidor empacotado (quando existir) é igual a `<versão>`; (d) a versão existe no índice, com um servidor HTTP local simulando `/pypi/mcp-investidor10-wallet/<versão>/json` com 200 e com 404; sai com 1 e mensagem em PT-BR em cada violação, inclusive para `--head-ref` `develop` ou `hotfix/*` e para `X.Y.ZrcN`; índice inacessível falha fechado
- [X] T003 [P] Criar `tests/contract/test_release_workflows.py` (parte 1), lendo os YAML com `pyyaml` (adicionar `pyyaml` pinada, publicada há 7 dias ou mais, a `[dependency-groups].dev` do `pyproject.toml`, só para os testes): `.github/workflows/ci.yml` dispara em `push` e `pull_request` para `main` e `develop`; `.github/workflows/main-gate.yml` dispara só em `pull_request` com `branches: [main]`, tem permissões `contents: read`, faz checkout com histórico e tags completos e chama `scripts/check_promotion.py`; todos os actions estão pinados por SHA

### Implementation

- [X] T004 Escrever `docs/adrs/0020-fluxo-de-branches-e-release.md`: princípio "`main` só contém versões publicadas no índice"; branches `main`, `develop`, `spec-NNN/*` e `hotfix/*`; fluxos de pré-lançamento, de versão final (pedido de preparação em `develop`, tag, publicação, verificação, `promote/vX.Y.Z`, pedido para `main`) e de hotfix; diferenças em relação ao Git Flow padrão (sem `release/*`, tag em `develop`, lançamento = publicação, portão de CI); alternativas descartadas com as fontes de `docs/research/fichamentos/modelos-de-branching.md` e `docs/research/fichamentos/publicacao-de-pacotes-e-promocao-de-artefatos.md`; verificações pendentes (branch padrão lida pelo Desktop, ambiente `pypi` com tags, instalação por versão exata de pré-lançamento); adicionar a linha ao índice de `CLAUDE.md` e uma nota de emenda no topo de `docs/adrs/0011-estrategia-de-distribuicao-e-release.md`
- [X] T005 Criar `scripts/check_promotion.py` conforme T002, sem docstring de módulo e sem dependências além da stdlib
- [X] T006 Criar `.github/workflows/main-gate.yml` e atualizar `.github/workflows/ci.yml` conforme T003
- [ ] T007 [mantenedor] Configurar no GitHub (Settings): conjunto de regras de `main` (pedido de revisão obrigatório, verificações `main-gate` e CI obrigatórias, sem push direto), conjunto de regras de `develop` (pedido de revisão e CI) e o ambiente `pypi` com aprovação manual a cada execução e implantação permitida para tags `v*`; registrar o resultado no corpo do pedido de revisão do lote

**Checkpoint (gate do Lote 0)**: um pedido de teste para `main` com origem diferente de `promote/v*` é recusado pelo `main-gate`; a CI roda em pedido para `develop`; o pedido dos documentos está em `develop`.

---

## Phase 1: Setup e spike do servidor empacotado — Lote 1

**Purpose**: baseline e a verificação empírica que decide o runtime do
servidor dentro do plugin (research D1). BLOQUEIA a parte de plugin da US1.

- [ ] T008 Registrar o baseline antes de alterar código: `uv run pytest` verde (anotar o total de testes no corpo do PR do lote) e `uv run ruff check . && uv run ruff format --check .` limpos
- [ ] T009 Criar o plugin de teste do spike em `specs/005-desktop-distribution/spike/ping-plugin/`: `.claude-plugin/plugin.json` (`name` `spike-ping`, `version` `0.0.1`, `mcpServers` `./servers/ping.mcpb`), e o servidor empacotado `servers/ping.mcpb` montado a partir do exemplo oficial `hello-world-uv` do repositório `modelcontextprotocol/mcpb` (`manifest_version` `0.4`, `server.type` `uv`, `pyproject.toml` com a dependência `fastmcp==4.1.2` do PyPI, validado com `@anthropic-ai/mcpb@2.1.2`), com três tools: `ping` (devolve `"pong"`), `abrir_pagina` (abre com `webbrowser` um formulário em `127.0.0.1` e grava o valor enviado em `~/.investidor10-spike/`) e `formulario_app` (o mesmo formulário como MCP App, com tool `visibility=["app"]`, conforme gofastmcp.com/apps); dois subagentes de teste, um com o nome curto da tool e outro com o nome completo (`mcp__plugin_spike-ping_<server>__ping`) na lista `tools`; mais um `README.md` com os passos do roteiro S1 de `quickstart.md`; sem `bin/` no topo
- [ ] T010 Executar o roteiro S1 de `specs/005-desktop-distribution/quickstart.md` (mantenedor, máquina ou conta limpa em macOS e em Windows, só Claude Desktop, plano pago, Claude unificado; e Claude Code CLI, inclusive no Linux): Upload plugin do zip de T009; conferir na aba Connectors se o servidor pede passo extra; tool `ping` numa sessão Cowork; `abrir_pagina` numa sessão Cowork (o navegador abre, o arquivo aparece em `~/.investidor10-spike/` e o valor não aparece na conversa); `formulario_app` numa sessão Cowork (só informativo: se aparece e se o valor fica fora da conversa e do histórico); `/mcp` no Claude Code com o plugin sincronizado; de novo com o plugin também instalado localmente (registrar se aparece em dobro); no Linux; os dois subagentes de teste no Cowork e no Claude Code (registrar qual consegue usar a tool); e qual branch o Desktop lê por padrão em Add marketplace e se `dono/repo#ref` é aceito
- [ ] T011 Executar o roteiro S1b de `specs/005-desktop-distribution/quickstart.md` (mantenedor, carteira fictícia em modo restrito, sem registrar o hash): verificar se gerar um link novo no site faz o hash antigo receber HTTP 301; registrar o resultado em `specs/005-desktop-distribution/research.md` D16
- [ ] T012 Escrever a learning lesson `docs/learning-lessons/mcpb_uv_dentro_de_plugin_no_desktop.md` com o resultado de T010 (fonte, versões do app e do Claude Code, data, o que funcionou em cada superfície, comportamento com sincronizado mais local) e a linha no índice de `CLAUDE.md`; registrar em `specs/005-desktop-distribution/research.md` D1 qual ramo da árvore de decisão foi escolhido. registrar também o resultado de `abrir_pagina` (incluindo a gravação em `~/`), de `formulario_app`, da aba Connectors, do Linux, da branch padrão lida pelo Desktop, de `#ref` e da forma do nome das tools no subagente. Se só o Linux falhar, o assistente mantém ali o registro pelo terminal. Se o ramo não for o 1, se `abrir_pagina` falhar no Cowork ou se a aba Connectors exigir passo extra, PARAR e revisar com o mantenedor as tasks T051–T061 antes do Lote 5 (no ramo 3, a FR-002 volta ao mantenedor). O resultado de `formulario_app` não bloqueia: só alimenta o roadmap

**Checkpoint (gate do Lote 1)**: ramo de D1 decidido e registrado; abertura da página no Cowork verificada.

---

## Phase 2: Foundational (configuração local e servidor sem configuração) — Lote 2

**Purpose**: o módulo de configuração e o bootstrap que não aborta; ambos
são usados pela US2 (credencial, `configure`) e pela US1 (tool, plugin).
BLOQUEIA as fases seguintes.

### Tests (escrever primeiro; DEVEM falhar antes de T017)

- [ ] T013 [P] Criar `tests/unit/test_wallet_config.py` com a tabela de interpretação do link (data-model.md §3): `https://[www.]investidor10.com.br/wallet/public/<id>?h=<hash>` → `mode=restricted` com `wallet_id` e `share_hash`; `https://[www.]investidor10.com.br/carteira/<id>[/...]` → `mode=public`; só dígitos → `mode=public`; remoção de espaços, aspas e sinais em volta; texto ao redor aceito quando há exatamente uma URL do host; parâmetros `utm_*` ignorados; recusa (erro com orientação, sem adivinhar) para host diferente, dois IDs, duas URLs, ID não numérico e credencial fora de `[A-Za-z0-9_-]{1,256}`
- [ ] T014 Adicionar a `tests/unit/test_wallet_config.py` os testes do arquivo `config.json` (data-model.md §1): campos `version` int `1`, `wallet_id` "Só dígitos (`[0-9]+`)", `share_hash` "`null` no modo público; no restrito, `[A-Za-z0-9_-]{1,256}`", `mode` `"public"` ou `"restricted"` "Coerente com `share_hash` (restrito exige credencial)", `mask_values` bool, `validated_at` ISO 8601, `source` `"setup_page"`, `"installer"` ou `"configure"`; gravação cria `<home>/.investidor10/` 0700 e o arquivo 0600 (asserts de modo com skip no Windows); gravação atômica (temporário no mesmo diretório + `os.replace`, nenhum temporário sobra em falha simulada); leitura por descritor com `O_NOFOLLOW` (link simbólico no lugar do arquivo → estado pendente `unreadable`, link intocado); JSON corrompido → pendente `unreadable` sem apagar nem reescrever; `version` maior que 1 → pendente `future_version`, arquivo intocado; campos fora das regras → pendente `unreadable`
- [ ] T015 Adicionar a `tests/unit/test_wallet_config.py` os testes do estado (data-model.md §2): sem arquivo e sem `WALLET_ID` → `pending/missing`; sem arquivo e `WALLET_ID` válido → `configured` com `origin=environment`, `mode=public`; arquivo válido vence o ambiente (`origin=file`); mascaramento efetivo = `mask_values` do arquivo OR `WALLET_MASK_VALUES` ligado; recarga só quando a identidade (inode, tamanho, `mtime_ns`) muda, contando leituras com um espião; a troca de arquivo por outro processo é vista na resolução seguinte; o ID exposto pelo estado para exibição é mascarado (`"…"` + 2 últimos dígitos) e a credencial nunca aparece em `repr`/`str`
- [ ] T016 Atualizar `tests/unit/test_bootstrap.py`: `load_config` sem `WALLET_ID` não levanta mais `SystemExit` e devolve a configuração sem carteira; `WALLET_ID` inválido continua levantando `SystemExit` com `INVALID_WALLET_ID_MESSAGE`; `WALLET_MASK_VALUES` inválido continua abortando; remover o teste que exigia aborto por `MISSING_WALLET_ID_MESSAGE`

### Implementation

- [ ] T017 Criar `src/investidor10_wallet/wallet_config.py` (sem docstring de módulo): `parse_link(text) -> WalletLink` (`wallet_id`, `share_hash`, `mode`), leitura e gravação de `config.json` reutilizando o diretório canônico e o padrão de abertura por descritor com `O_NOFOLLOW` de `bootstrap.py`/`memory_store.py` (sem duplicar o helper: extrair para um ponto único se preciso), gravação atômica com o mesmo retry de `os.replace` do Windows usado na memória, `resolve_state(environ, home)` com a precedência e a recarga por identidade de T015, e `masked_wallet(wallet_id)`; mensagens de operador em PT-BR
- [ ] T018 Escrever `docs/adrs/0019-configuracao-local-e-pagina-local.md` (configuração local única, modo restrito, servidor sem configuração, `open_wallet_setup` e página local; emenda o modelo de ameaças do ADR-0004 com a porta local e a credencial no arquivo; emenda o ADR-0015 §1, porque o mascaramento passa a ser ativado também pelo arquivo, mantendo que nenhuma tool altera o mascaramento; limite de um agente com controle do navegador; gatilho de revisão com elicitation); adicionar a linha ao índice de `CLAUDE.md` e uma nota de emenda no topo de `docs/adrs/0004-threat-model-and-security-boundary.md` e `docs/adrs/0015-modo-privacidade-wallet-mask-values.md`
- [ ] T019 Alterar `src/investidor10_wallet/bootstrap.py`: `load_config` não aborta mais sem `WALLET_ID` (o campo `wallet_id` fica vazio e a resolução da carteira passa a ser do `wallet_config`); manter as validações de ID inválido e de números; remover `MISSING_WALLET_ID_MESSAGE` se ficar sem uso

**Checkpoint (gate do Lote 2)**: `uv run pytest tests/unit/test_wallet_config.py tests/unit/test_bootstrap.py` verde nas 3 plataformas; suíte completa verde.

---

## Phase 3: User Story 2 — Configuração pelo link: carteira pública ou restrita (Priority: P1) — Lote 3

**Goal**: acesso recusado diagnosticado como tal; link como entrada no
terminal; credencial enviada só ao proxy e redigida em todo texto;
reconfiguração por subcomando (FR-010 a FR-019).

**Independent Test**: com a carteira restrita fictícia, `install --link`
com `?h=` funciona e as tools retornam dados; tornar a carteira privada →
erro `access_denied` com a ação correta; `configure --mask` liga o
mascaramento sem reinstalar (quickstart S4).

### Tests for User Story 2 (escrever primeiro)

- [ ] T020 [P] [US2] Criar `tests/fixtures/proxy_301_access_denied.json` a partir da resposta real observada (status 301, cabeçalhos sem `Location`, corpo "Acesso não autorizado"), anonimizada: sem ID, sem credencial, sem cookies
- [ ] T021 [US2] Adicionar a `tests/unit/test_wallet_client.py`: resposta 3xx do proxy (usar a fixture de T020 com `respx`) levanta `SourceError` com código `access_denied` antes de ler o corpo, nunca `unexpected_format`; 3xx não entra no cache e não serve cache vencido mesmo com entrada antiga; 401 e 403 do proxy também viram `access_denied`; 404 e 5xx mantêm o comportamento atual; a função de validação devolve `valid`/`access_denied`/`not_found`/`unavailable` para 200 / 3xx,401,403 / 404 / 5xx e transporte (data-model.md §4)
- [ ] T022 [P] [US2] Adicionar a `tests/unit/test_wallet_client_redaction.py`: com credencial configurada, toda requisição ao proxy da carteira leva o parâmetro `hash`, nenhuma requisição ao `REST_BASE_URL` (cotação) leva; a credencial é substituída por `<hash>` em todas as mensagens de `SourceError`, inclusive no texto de exceção de transporte do httpx que carrega a URL com a query; troca de carteira ou de credencial esvazia o cache dos dois clientes
- [ ] T023 [P] [US2] Adicionar a `tests/contract/test_error_signal.py` o caso `access_denied` provocado de verdade (proxy respondendo 301 via `respx`) para `get_wallet_summary`: `is_error is True`, código `access_denied`, `open_wallet_setup` citado na mensagem, nenhum ID nem credencial no texto; e o caso de `source_unavailable` para 4xx cuja dica não cita mais `WALLET_ID`
- [ ] T024 [P] [US2] Adicionar a `tests/unit/test_installer_cli.py`: `install --link <link restrito>` interpreta, valida (com `respx`), pergunta o mascaramento (ou usa `--mask`/`--no-mask`), grava a configuração local com `source` `installer` e mostra o resumo com modo e mascaramento; link público imprime o aviso de indexação e a recomendação da restrita; acesso recusado e carteira inexistente não gravam e saem com código 3; fonte indisponível pergunta `[s/N]` e só grava com `s` (e `--yes` não responde essa pergunta); `--wallet-id` continua aceito e equivale a link público
- [ ] T025 [US2] Adicionar a `tests/unit/test_installer_cli.py` os testes do subcomando `configure` (contracts/cli.md): refaz link e mascaramento, reescreve só a configuração local, não chama nenhum comando de cliente; troca para outra carteira pede `[s/N]` com o aviso sobre a memória; segunda execução igual não altera o arquivo (mesmo `mtime_ns`); códigos de saída 0, 2, 3 e 4; e a `tests/unit/test_installer_dispatch.py` o despacho de `mcp-investidor10-wallet configure`
- [ ] T026 [P] [US2] Adicionar a `tests/unit/test_installer_clients.py`: `add_command` de Devin, Codex e Gemini não contém mais `WALLET_ID=` nem `-e`/`--env` da carteira
- [ ] T027 [P] [US2] Adicionar a `tests/unit/test_check_no_wallet_id.py`: com `WALLET_HASH` no ambiente, a guarda também falha quando a credencial aparece em arquivo versionado e quando aparece dentro de um `.mcpb` versionado (conteúdo do zip); sem a variável, a parte da credencial é pulada com aviso

### Implementation for User Story 2

- [ ] T028 [US2] Alterar `src/investidor10_wallet/wallet_client.py`: 3xx, 401 e 403 do proxy viram `access_denied` antes de ler o corpo e sem tocar no cache; parâmetro `hash` só nas requisições ao proxy quando houver credencial; `_redact` cobre a credencial; `apply_configuration(state)` troca carteira e credencial dos dois clientes e esvazia o cache; a validação reutilizável devolve os quatro resultados de data-model.md §4; `validate_wallet` de inicialização passa a só avisar (nunca abortar) em acesso recusado
- [ ] T029 [US2] Alterar `src/investidor10_wallet/server.py`: `NEXT_ACTIONS` ganha `access_denied` com a mensagem-alvo de `contracts/error-envelope.md`; a dica de 4xx deixa de citar `WALLET_ID` e passa a citar `open_wallet_setup`
- [ ] T030 [US2] Alterar `src/investidor10_wallet/installer/cli.py`: flags `--link`, `--mask`/`--no-mask`, fluxo de validação, aviso de público, pergunta do mascaramento, gravação da configuração local e resumo; subcomando `configure` com os códigos de saída de `contracts/cli.md`; e `src/investidor10_wallet/server.py` `main` despacha `configure` como já despacha `install`
- [ ] T031 [US2] Alterar `src/investidor10_wallet/installer/clients.py`: Devin, Codex e Gemini registram o servidor sem a variável da carteira (o servidor lê a configuração local)
- [ ] T032 [US2] Alterar `scripts/check-no-wallet-id` para também procurar `WALLET_HASH` do ambiente (quando definido) nos arquivos versionados e dentro dos `.mcpb` versionados, mantendo o comportamento atual para `WALLET_ID`; atualizar o hook correspondente em `.pre-commit-config.yaml` se precisar
- [ ] T033 [P] [US2] Escrever a learning lesson `docs/learning-lessons/proxy_301_acesso_recusado_sem_location.md` (a fonte responde 301 sem `Location` para carteira restrita sem credencial válida e para privada; não distingue as duas; credencial vai como `hash` e o site usa `h`; fonte e data 31/10/2026) e a linha no índice de `CLAUDE.md`
- [ ] T034 [P] [US2] Emendar `docs/adrs/0014-sinal-duplo-de-erro.md` com a seção "Emenda 2026-11-01 (spec 005)": conjunto fechado passa de 12 para 15 com `wallet_not_configured`, `access_denied` e `setup_unavailable`, tabela de `contracts/error-envelope.md`; atualizar o título da linha no índice de `CLAUDE.md` para "15 códigos"
- [ ] T035 [P] [US2] Atualizar `docs/PRIVACY.md`: carteira restrita como recomendação padrão (a pública é indexável), o que é a credencial do link, onde ela fica (configuração local 0600), que ela é informada na página local e não passa pelo modelo, o que acontece se o usuário colar o link na conversa (fica no histórico), e, só se T011 confirmar, como revogar gerando um link novo no site (se não confirmar, dizer o que de fato protege)

**Checkpoint (gate do Lote 3)**: quickstart S4 passos 2 e 3 validados com a carteira fictícia restrita; suíte verde; guarda de ID e credencial verde.

---

## Phase 4: User Story 1 — Investidor sem terminal usa o produto no Claude Desktop (Priority: P1) — Lotes 4 e 5

**Goal**: servidor que conduz o usuário à página local de configuração (Lote
4) e o plugin único instalável pelo marketplace, sem registro em dobro no
Claude Code (Lote 5) (FR-001 a FR-009d).

**Independent Test**: máquina com Claude Desktop, plano pago e nada do
produto: adicionar o marketplace, instalar o plugin, preencher a página
aberta pelo assistente e receber dados reais em até 5 minutos, sem terminal
(quickstart S2).

### Tests for User Story 1 — servidor (Lote 4, escrever primeiro)

- [ ] T036 [P] [US1] Adicionar a `tests/contract/test_error_signal.py` o caso `wallet_not_configured` para cada uma das cinco tools de carteira (`get_wallet_summary`, `get_wallet_allocation`, `get_wallet_positions`, `get_patrimony_history`, `get_earnings`) em estado pendente: `is_error is True`, código `wallet_not_configured`, `open_wallet_setup` na mensagem, nenhuma requisição HTTP feita; e que as tools de memória e `get_asset_quote` continuam funcionando em estado pendente
- [ ] T037 [P] [US1] Criar `tests/contract/test_wallet_setup_tool.py` (contracts/wallet-setup.md): `open_wallet_setup` sem parâmetros; nenhuma tool do servidor tem argumento de link, credencial, carteira ou mascaramento; anotações `readOnlyHint=False`, `destructiveHint=False`, `idempotentHint=True`, `openWorldHint=True`; com `webbrowser` simulado, `status` `opened`, `already_open` (mesma página reaproveitada) e `open_manually` (com `setup_url` e `terminal_alternative`) quando o navegador não abre; `setup_url` só aparece em `open_manually`; com a porta local indisponível, `is_error is True`, código `setup_unavailable`, `configure` citado na mensagem
- [ ] T038 [P] [US1] Adicionar a `tests/contract/test_wallet_setup_tool.py` a verificação de SC-009: nenhuma resposta de `open_wallet_setup`, de `get_session_context` nem das tools de carteira contém o ID completo, a credencial ou a URL do link
- [ ] T039 [P] [US1] Criar `tests/integration/test_setup_page.py` (contracts/wallet-setup.md, data-model.md §5), com requisições HTTP reais à página e fonte simulada por `respx`: escuta só em `127.0.0.1`; cada linha da tabela de resultados de um envio (válido, carteira diferente sem e com confirmação, só mascaramento ou credencial da mesma carteira, mesmos valores, link não interpretável, acesso recusado, carteira inexistente, fonte indisponível, falha ao gravar, aviso do modo público) e o que cada uma grava com `source` `setup_page`; recusa sem gravar para envio sem token, com token usado, com token vencido (prazo de 10 minutos, relógio simulado), `Host` ou `Origin` errados; a página encerra depois de salvar ou vencer; respostas com `Cache-Control: no-store` e `Content-Security-Policy`, sem recurso externo; nenhuma resposta repete o link nem a credencial; o corpo do envio não aparece em log nem em stderr; a configuração gravada vale na chamada seguinte de tool, no mesmo processo
- [ ] T040 [P] [US1] Criar `tests/integration/test_config_reload.py`: dois processos do servidor (via `fastmcp.Client` sobre stdio ou o worker existente em `tests/integration/`), gravação da configuração pela página num deles e, sem reinício, o outro passa a usar a nova carteira na chamada seguinte
- [ ] T041 [P] [US1] Criar `tests/contract/test_session_context_configuration.py`: `get_session_context` sempre traz o bloco `configuration`; pendente com `status`, `reason` (`missing`, `unreadable`, `future_version`) e `next_action` citando `open_wallet_setup`; configurado com `status`, `mode`, `mask_values`, `wallet` mascarado e `origin` (`file` ou `environment`); a memória continua carregada em estado pendente; o total de tools passa a 20
- [ ] T042 [P] [US1] Adicionar a `tests/contract/test_tool_descriptions.py`: a descrição de `open_wallet_setup` chega ao modelo com as quatro regras de uso de contracts/wallet-setup.md (quando chamar; pedir o link na página, nunca na conversa; não repetir nem reutilizar um link colado na conversa; conferir `configuration` depois de salvar); e a de `get_session_context` traz a regra de conduzir a configuração com `status` pendente
- [ ] T043 [P] [US1] Adicionar a `tests/unit/test_privacy.py`: o mascaramento efetivo liga quando o arquivo ou `WALLET_MASK_VALUES` liga, e muda sem reinício quando a configuração local muda

### Implementation for User Story 1 — servidor (Lote 4)

- [ ] T044 [US1] Criar `src/investidor10_wallet/setup_page.py` (sem docstring de módulo, só biblioteca padrão: `http.server` numa thread, `secrets`, `webbrowser`, HTML embutido em PT-BR): sobe o formulário em `127.0.0.1` com porta livre, token de uso único e prazo de 10 minutos, confere `Host` e `Origin`, usa `wallet_config.parse_link`, a validação do `wallet_client` e a gravação do `wallet_config` com `source` `setup_page`, pede confirmação na página para outra carteira, encerra depois de salvar ou vencer; nunca loga o corpo do envio
- [ ] T045 [US1] Alterar `src/investidor10_wallet/server.py`: as cinco tools de carteira resolvem o estado no início e devolvem `wallet_not_configured` (mensagem-alvo de `contracts/error-envelope.md`) quando pendente, ou aplicam a configuração aos clientes HTTP quando ela mudou; nova tool `open_wallet_setup` com as anotações e a docstring de T042, usando `setup_page` e devolvendo `setup_unavailable` se a porta local não abrir; `get_session_context` ganha o bloco `configuration` e a regra na docstring; `main` não aborta sem carteira e só roda a sonda com configuração presente
- [ ] T046 [US1] Alterar `src/investidor10_wallet/privacy.py` para o mascaramento efetivo (arquivo OR ambiente) resolvido junto com o estado, sem reinício

### Pipeline mínima para o pré-lançamento (Lote 4, escrever os testes primeiro)

- [ ] T047 [P] [US1] Criar `tests/contract/test_release_workflow.py`: `.github/workflows/release.yml` dispara por tag `v*` e aceita `X.Y.ZrcN`; tem os jobs `build` (sem `id-token`), `publish` (`needs: build`, `id-token: write`, ambiente `pypi`, sem checkout e sem testes) e `verify` (`needs: publish`, matriz ubuntu, macos e windows); a checagem de changelog de uma tag `X.Y.ZrcN` procura a seção da versão base `[X.Y.Z]`; o teste de fumaça não espera saída 1 sem `WALLET_ID` e confere o `initialize` sem carteira com `HOME` temporário; o `verify` instala `mcp-investidor10-wallet==<versão>` do índice em ambiente limpo, por pip e por `uvx`, e confere o `initialize` e as 20 tools; a tag precisa ser igual a `__version__`
- [ ] T048 [US1] Reestruturar `.github/workflows/release.yml` em `build` (uv build, checagem do changelog, teste de fumaça, upload dos artefatos), `publish` (download dos artefatos e publicação no PyPI com o action pinado por SHA) e `verify`, conforme T047; manter os actions pinados por SHA
- [ ] T049 [US1] Preparar a pré-versão em `develop` (pedido de revisão `spec-005/rc1`): `__version__` `0.4.0rc1` em `src/investidor10_wallet/__init__.py` e uma seção `## [0.4.0] - não lançado` em `CHANGELOG.md` (será completada na versão final)
- [ ] T050 [US1] [mantenedor] Criar a tag `v0.4.0rc1` em `develop`, aprovar a publicação no ambiente `pypi` e conferir o `verify` verde nos três sistemas; registrar em `specs/005-desktop-distribution/research.md` D18 se a instalação por versão exata de pré-lançamento funciona com pip e com `uvx`; se `uvx` ignorar a versão exata, PARAR e revisar D1 e D18 com o mantenedor

**Checkpoint (gate do Lote 4)**: quickstart S3 com `fastmcp.Client` e S5 com a página real; suíte verde nas 3 plataformas; `0.4.0rc1` publicada no índice e verificada nos três sistemas; `main` inalterado.

### Tests for User Story 1 — plugin e instalador (Lote 5, escrever primeiro)

- [ ] T051 [P] [US1] Criar `tests/contract/test_mcpb_package.py` (data-model.md §6): `scripts/build_mcpb.py` gera zip determinístico (duas execuções = bytes iguais); `manifest.json` com `manifest_version` `0.4`, `name` `carteira`, `version` = `investidor10_wallet.__version__`, `server.type` `uv`, `server.entry_point` presente, `compatibility.platforms` `["darwin", "win32", "linux"]`, `tools` = nomes das tools listadas pelo servidor, sem `user_config`; `pyproject.toml` do pacote com `requires-python` igual ao da raiz e a dependência única `mcp-investidor10-wallet==<versão>`; contém `server/main.py`; não contém o código do pacote, `server/lib/` nem `server/venv/`; `--check` falha quando o commitado diverge do gerado
- [ ] T052 [P] [US1] Atualizar `tests/contract/test_plugin_assets.py` (contracts/plugin-package.md): `version` dos quatro manifestos = `__version__`; só `plugin/.claude-plugin/plugin.json` declara `mcpServers` e o valor é `./servers/carteira.mcpb`; `displayName` e `license` presentes; nenhum `bin/` no topo de `plugin/`; `hooks/hooks.json` com `SessionStart` = `cat "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.json"` e `Stop` inalterado; `hooks/session-start.json` é JSON válido, só ASCII, com `hookSpecificOutput.hookEventName` `SessionStart` e o `additionalContext` contendo a persona atual e a regra de configuração pendente; `skills/configurar-carteira/SKILL.md` existe com frontmatter `name` e `description`; a lista `tools` de `agents/guardiao-de-disciplina.md` usa a forma de nome registrada em T012
- [ ] T053 [P] [US1] Adicionar a `tests/unit/test_installer_clients.py` e `tests/unit/test_installer_cli.py` (contracts/cli.md, passo 6): no Claude Code o assistente só chama `claude mcp add` com `--mcp-only`; com `investidor10-carteira@synced` em `claude plugin list` não instala localmente e diz por quê; sem ele, `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet#v<versão>` e `claude plugin install investidor10-carteira@investidor10`; com o registro `carteira` em escopo de usuário em `claude mcp list`, pergunta e só com `s` roda `claude mcp remove carteira -s user`; na recusa, instala o plugin e o relatório avisa da duplicação; com o marketplace `investidor10` já adicionado (0.3.x), a mesma pergunta cobre `claude plugin marketplace remove`, `add` com `#v<versão>` e reinstalar o plugin; com `@synced` e cópia local, oferece desinstalar a cópia local; `--mcp-only` registra só o servidor em cada cliente, não instala o plugin e, se o plugin já existir no Claude Code, o relatório avisa da duplicação

### Implementation for User Story 1 — plugin e instalador (Lote 5)

- [ ] T054 [US1] Criar `scripts/build_mcpb.py` (stdlib: `zipfile` com ordem, datas e permissões fixas) que gera `plugin/servers/carteira.mcpb` a partir da versão do pacote, de `requires-python` do `pyproject.toml` raiz e da lista de tools do servidor, e um modo `--check` que falha se o commitado divergir; gerar e commitar `plugin/servers/carteira.mcpb` (só muda em pedido de preparação de versão, pré-lançamento ou final)
- [ ] T055 [US1] Atualizar `plugin/.claude-plugin/plugin.json` (campos de contracts/plugin-package.md: `name` `investidor10-carteira`, `displayName`, `version` = pacote, `description`, `license` `MIT`, `mcpServers` `./servers/carteira.mcpb`) e só a `version` de `plugin/.codex-plugin/plugin.json`, `plugin/.devin-plugin/plugin.json` e `plugin/gemini-extension.json`; atualizar a `description` em `.claude-plugin/marketplace.json`
- [ ] T056 [US1] Reescrever o hook de início de sessão: criar `plugin/hooks/session-start.json` (só ASCII, acentos com escapes `\u`) com a persona atual mais a regra "se get_session_context indicar configuração pendente, conduza a configuração (skill configurar-carteira) antes de qualquer análise"; trocar o comando em `plugin/hooks/hooks.json`; remover `plugin/hooks/session-start-persona.sh`
- [ ] T057 [P] [US1] Criar `plugin/skills/configurar-carteira/SKILL.md` com os quatro passos de contracts/plugin-package.md e o comportamento na conversa Chat sem tools (dizer que as tools só carregam numa sessão Cowork no computador, sem inventar valores)
- [ ] T058 [P] [US1] Ajustar a lista `tools` de `plugin/agents/guardiao-de-disciplina.md` para a forma de nome registrada em T012
- [ ] T059 [US1] Alterar `src/investidor10_wallet/installer/clients.py` e `src/investidor10_wallet/installer/cli.py` para o fluxo do Claude Code de T053
- [ ] T060 [US1] Escrever `docs/adrs/0018-plugin-unico-com-servidor-empacotado.md` (emenda ADR-0012 §2 e §6 para o Claude: um plugin só, fonte única da conexão no Claude Desktop e no Claude Code, `--mcp-only` como escape; emenda ADR-0011: o PyPI segue como único canal de código, o plugin só aponta para a versão publicada e o teste de fumaça deixa de exigir saída 1 sem carteira; servidor empacotado; hook estático; ramo de D1 escolhido em T012); adicionar a linha ao índice de `CLAUDE.md` e uma nota de emenda no topo de `docs/adrs/0012-integracao-automatica-de-clientes.md` e `docs/adrs/0011-estrategia-de-distribuicao-e-release.md`
- [ ] T061 [US1] Validar no Claude Desktop real (mantenedor) os roteiros S2 (passos 2 a 4, instalando o plugin por Upload plugin a partir do zip de `plugin/`, com o pacote apontando para a `0.4.0rc1` publicada), S5, S6 e S7 de `specs/005-desktop-distribution/quickstart.md` em macOS e Windows, cronometrando S2 (SC-001) e conferindo SC-001a; registrar resultado e data em `specs/005-desktop-distribution/validation-matrix.md` (criar com as colunas cliente × plataforma × resultado × data)

**Checkpoint (gate do Lote 5)**: S2 (passos 2 a 4, plugin por Upload plugin apontando para a rc) em até 5 minutos em macOS e Windows; `/mcp` no Claude Code com um só servidor da carteira (20 tools); `uv run python scripts/build_mcpb.py --check` verde.

---

## Phase 5: User Story 7 — Investidor encontra e adiciona o plugin pelo marketplace próprio (Priority: P2) — Lote 6

**Goal**: o caminho do usuário leigo até o plugin documentado no README;
diretórios fora desta spec com critérios de reabertura (FR-030, FR-031).

**Independent Test**: um usuário sem contexto segue só o README e chega ao
plugin instalado no Desktop.

### Tests for User Story 7

- [ ] T062 [P] [US7] Criar `tests/contract/test_readme_desktop.py`: o README tem a seção do Desktop com o texto `rc-ventura/mcp-investidor10-wallet` em bloco de código, os passos adicionar marketplace / instalar / configurar na página / atualizar / desinstalar, a exigência de plano pago e a limitação da conversa Chat, e o link para `docs/PRIVACY.md`

### Implementation for User Story 7

- [ ] T063 [US7] Escrever em `README.md` a seção do Claude Desktop em PT-BR (FR-031), com imagens em `docs/images/desktop/` (capturas sem dado de carteira real), a instrução para remover uma entrada manual antiga em `claude_desktop_config.json` e o aviso de que não há Claude Desktop para Linux, e ajustar as seções dos CLIs ao novo fluxo (`--link`, `configure`, Claude Code pelo plugin)
- [ ] T064 [P] [US7] Atualizar `docs/ROADMAP.md`: listagem em diretórios sai da Fase 3 desta spec e volta com os critérios de reabertura da FR-030 (matriz de máquinas limpas aprovada, 4 semanas de testes semanais sem mudança detectada, ADR sobre os termos de uso do Investidor10); extensão `.mcpb` avulsa registrada como alternativa descartada; SQLite com os gatilhos de reavaliação da spec

**Checkpoint**: T062 verde; leitura do README por alguém de fora sem ajuda.

---

## Phase 6: User Story 5 — Usuário diagnostica a instalação sem expor dados (Priority: P3) — Lote 6

**Goal**: subcomando `doctor` com causa e ação, saída sanitizada (FR-024,
FR-025).

**Independent Test**: provocar as cinco causas conhecidas e conferir causa,
ação e ausência de dado sensível (quickstart S8).

### Tests for User Story 5 (escrever primeiro)

- [ ] T065 [P] [US5] Criar `tests/unit/test_doctor.py` (data-model.md §8, contracts/cli.md): checagens com `id`, `status` (`ok`, `warn`, `fail`), `cause` e `action` em PT-BR para runner ausente, configuração ausente, link inválido, carteira com acesso recusado (via `respx`), memória sem permissão de escrita (skip no Windows), produto não registrado em nenhum cliente, plugin `@synced` detectado, servidor em dobro, entrada manual antiga em `claude_desktop_config.json`, carteira restrita que responde sem a credencial (ficou pública e indexável); código de saída 0 sem falhas e 1 com falha; a saída não contém o ID, a credencial, valores, conteúdo da memória nem o caminho da home (substituído por `~`); credencial só como "presente/ausente"
- [ ] T066 [P] [US5] Adicionar a `tests/unit/test_installer_dispatch.py` o despacho de `mcp-investidor10-wallet doctor`

### Implementation for User Story 5

- [ ] T067 [US5] Criar `src/investidor10_wallet/installer/doctor.py` com as checagens e a sanitização, reutilizando `wallet_config`, a validação do `wallet_client` e a detecção dos adaptadores; despachar o subcomando em `src/investidor10_wallet/server.py` `main`

**Checkpoint (gate do Lote 6)**: S8 com 5 de 5 causas corretas (SC-007); README revisado.

---

## Phase 7: User Story 6 — Mantenedor publica cada versão com o plugin e a cadeia de suprimentos em dia (Priority: P3) — Lote 7

**Goal**: versões consistentes, publicação separada dos testes, alarme
semanal de mudança da API, Dependabot e as pendências da 0.3.1 do
instalador, promoção automática e documentação do fluxo (FR-026 a FR-029 e FR-032 a FR-034).

**Independent Test**: tag de pré-release com `build` sem `id-token` e
`publish` com permissão; disparo manual de `live.yml` com a carteira
fictícia (quickstart S9).

### Tests for User Story 6 (escrever primeiro)

- [ ] T068 [P] [US6] Adicionar a `tests/unit/test_installer_cli.py` o teste da pendência do ciclo 6: com `--clients` citando um cliente ausente e outro presente, cada linha do relatório (registro e plugin) corresponde ao próprio cliente (hoje `zip(detected, session.outcomes)` desalinha quando há resultado `skipped_absent` antes)
- [ ] T069 [P] [US6] Adicionar a `tests/unit/test_installer_clients.py` a fixação na versão para Devin, Codex e Gemini quando o comando do cliente aceitar referência, com a sintaxe confirmada na documentação oficial de cada CLI (registrar a fonte em `docs/research/plugins-devin-cli.md`, `docs/research/plugins-codex-cli.md` e `docs/research/plugins-gemini-cli.md`); onde não houver referência, o relatório diz que o plugin segue a branch padrão
- [ ] T070 [P] [US6] Criar `tests/contract/test_release_consistency.py`: versão do pacote = versão dos quatro manifestos do plugin = versão do manifesto do servidor empacotado; lista de tools do manifesto = lista exposta pelo servidor; `.github/workflows/live.yml` só dispara por `schedule` e `workflow_dispatch`; `.github/dependabot.yml` cobre o ecossistema de dependências Python e `github-actions`
- [ ] T071 [P] [US6] Criar `tests/unit/test_plan_promotion.py` para `scripts/plan_promotion.py` (stdlib): dada uma tag final `vX.Y.Z`, devolve a ação "criar `promote/vX.Y.Z` no commit da tag e abrir pedido para `main`"; recusa tag com sufixo `rc`; quando o commit da tag não é ancestral de `origin/develop` (hotfix), devolve também a ação "abrir pedido da tag para `develop`" (repositórios temporários criados no teste)
- [ ] T072 [P] [US6] Adicionar a `tests/contract/test_release_workflows.py` (parte 2): `.github/workflows/promote.yml` dispara por `workflow_run` do `Release` concluído com sucesso ou por `workflow_dispatch` com a tag e a entrada `dry-run`, só para tags sem `rc`, tem permissões `contents: write` e `pull-requests: write` e chama `scripts/plan_promotion.py`; o job `build` de `release.yml` executa `scripts/build_mcpb.py --check` e `npx @anthropic-ai/mcpb@2.1.2 validate plugin/servers/carteira.mcpb`, e a release anexa o MCPB

### Implementation for User Story 6

- [ ] T073 [US6] Corrigir o pareamento cliente × resultado em `src/investidor10_wallet/installer/cli.py` (T068)
- [ ] T074 [US6] Implementar a fixação na versão em `src/investidor10_wallet/installer/clients.py`, conforme o teste correspondente desta fase
- [ ] T075 [US6] Criar `scripts/plan_promotion.py` conforme T071
- [ ] T076 [US6] Criar `.github/workflows/promote.yml` conforme T072 (com o modo `dry-run`, que só imprime as ações)
- [ ] T077 [US6] Acrescentar ao job `build` de `.github/workflows/release.yml` os passos `scripts/build_mcpb.py --check` e `npx @anthropic-ai/mcpb@2.1.2 validate plugin/servers/carteira.mcpb` (versão publicada em 04/12/2025), e anexar o MCPB à release
- [ ] T078 [US6] Escrever `docs/RELEASING.md` em PT-BR: pré-lançamento, versão final e hotfix (comandos de tag, onde aprovar a publicação, o pedido `promote/vX.Y.Z`, o retorno do hotfix para `develop`) e o que fazer quando a publicação falha (número publicado não se reutiliza: subir a versão)
- [ ] T079 [P] [US6] Criar `.github/workflows/live.yml`: `schedule` semanal e `workflow_dispatch`, `uv run pytest -m live` com `WALLET_ID` (e `WALLET_HASH`, se houver o teste restrito) vindos de segredos do repositório da carteira fictícia; asserts e logs só com o código do erro; actions pinados por SHA
- [ ] T080 [P] [US6] Criar `.github/dependabot.yml` com o ecossistema Python confirmado na documentação do Dependabot para projetos `uv` e `github-actions`, intervalo semanal; registrar a fonte usada no corpo do PR do lote
- [ ] T081 [P] [US6] Adicionar a `.github/workflows/ci.yml` o passo `claude plugin validate ./plugin`, quando o CLI estiver disponível na CI
- [ ] T082 [P] [US6] Reverificar nas release notes oficiais do Claude Desktop o suporte a elicitation (research D15); se houver, abrir item no roadmap para a FR-008a; registrar o resultado em `specs/005-desktop-distribution/research.md` D15

**Checkpoint (gate do Lote 7)**: S9 (passos 1 e 3) validados; `promote.yml` executado em modo `dry-run`; `live.yml` disparado manualmente com sucesso.

---

## Phase 8: User Story 3 — Devin Desktop com o mesmo produto do Devin CLI (Priority: P2) — Lote 8

**Goal**: verificação real do Devin Desktop, sem suposição de caminho
(FR-020 a FR-022).

**Independent Test**: numa máquina com Devin Desktop, rodar o assistente e
verificar tools, skills, guardião e hooks.

- [ ] T083 [US3] Verificar numa instalação real do Devin Desktop (mantenedor) se o registro feito pelo assistente para o Devin CLI e o plugin de comportamento carregam no app (as 20 tools, skills, guardião, persona); registrar em `docs/learning-lessons/devin_desktop_harness_compartilhado.md` com fonte, versão e data, e a linha no índice de `CLAUDE.md`
- [ ] T084 [US3] Adicionar a `tests/unit/test_installer_cli.py` (escrever primeiro) e implementar em `src/investidor10_wallet/installer/cli.py`/`clients.py` a linha do relatório que diz se o Devin Desktop foi coberto, conforme o resultado de T083: coberto pelo registro compartilhado, coberto por caminho próprio (mecanismo nativo do app, com fonte) ou não suportado; nunca registrar por adivinhação

**Checkpoint**: learning lesson escrita; relatório do assistente coerente com ela.

---

## Phase 9: User Story 4 — Usuário novo instala em máquina limpa nos clientes prometidos (Priority: P2) — Lote 8

**Goal**: matriz cliente × plataforma preenchida por instalação real antes
de anunciar suporte (FR-022, FR-023, SC-006).

**Independent Test**: seguir o roteiro S10 e não deixar célula "não
testado".

- [ ] T085 [US4] Executar o roteiro S10 de `specs/005-desktop-distribution/quickstart.md` em máquina limpa e preencher `specs/005-desktop-distribution/validation-matrix.md`: Claude Desktop sessão Cowork e conversa Chat (macOS, Windows, incluindo Windows sem Git para os hooks), Claude Code (macOS, Windows, Linux), Devin CLI, Devin Desktop, Codex pela interface interativa, Gemini CLI, assistente real (roteiros V2.2/V2.4 da spec 003)
- [ ] T086 [US4] Ajustar `README.md` e `docs/PRIVACY.md` para não anunciar nenhuma combinação com divergência registrada em T085

**Checkpoint (gate do Lote 8)**: nenhuma célula "não testado".

---

## Phase 10: Polish & Cross-Cutting Concerns — Lote 8

- [ ] T087 [P] Revisar as docstrings das 20 tools e as `instructions=` do servidor (hoje "Read-only access to one public Investidor10 wallet") para citar carteira pública ou restrita e a tool de configuração, mantendo `instructions=` como propósito e índice (Constituição III); revisar as mensagens e docstrings do modo privacidade em `privacy.py` e `server.py`, que hoje dizem que "o operador" ligou o modo, porque o usuário agora também liga pela página
- [ ] T088 Preparar a versão final em `develop` (pedido de revisão `spec-005/versao-0.4.0`): `__version__` `0.4.0` em `src/investidor10_wallet/__init__.py`, `version` nos quatro manifestos do plugin e `plugin/servers/carteira.mcpb` regenerado com `uv run python scripts/build_mcpb.py` (dependência `==0.4.0`)
- [ ] T089 [P] Escrever a seção `## [0.4.0]` em `CHANGELOG.md`: plugin único e Desktop, configuração local e página de configuração, carteira restrita, `access_denied` e `wallet_not_configured`, `configure` e `doctor`, servidor que sobe sem carteira, mudança do Claude Code para o plugin (com instrução de migração do registro antigo e da entrada manual em `claude_desktop_config.json`)
- [ ] T090 Rodar a suíte completa (`uv run pytest`), `uv run ruff check . && uv run ruff format --check .`, `scripts/check-no-wallet-id` com `WALLET_ID` e `WALLET_HASH` do ambiente e `uv run python scripts/build_mcpb.py --check`; anotar os totais no PR
- [ ] T091 [mantenedor] Executar a versão final conforme `docs/RELEASING.md`: tag `v0.4.0` em `develop`, aprovar a publicação, conferir o `verify` verde nos três sistemas, aprovar e fazer o merge do pedido `promote/v0.4.0` contra `main` (com o `main-gate` verde) e conferir que o marketplace em `main` entrega o plugin
- [ ] T092 [mantenedor] Repetir o roteiro S2 (passo 1, Add marketplace) e o S9 contra o marketplace em `main`; registrar o resultado e a data em `specs/005-desktop-distribution/validation-matrix.md`
- [ ] T093 Escrever `specs/005-desktop-distribution/fechamento.md` (mesmo formato da spec 004): FRs e SCs com evidência, ramo de D1, divergências da matriz, itens devolvidos ao roadmap

---

## Dependencies & Execution Order

### Phase Dependencies

- **Lote 0 (Fluxo de branches)**: sem dependências de código; BLOQUEIA todos os lotes, porque tudo entra por `develop`.
- **Phase 1 (Setup e spike)**: depende do Lote 0; a task que registra o ramo de D1 BLOQUEIA as tasks de plugin da US1 (T051–T061).
- **Phase 2 (Fundação)**: depende do baseline do Lote 1; BLOQUEIA todas as user stories.
- **US2 (Phase 3)**: depende da Fundação.
- **US1 (Phase 4)**: o servidor (T036–T046) depende da Fundação e do cliente HTTP da US2; a pré-versão (rc) depende do servidor e do pipeline mínimo; plugin e instalador (T051–T061) dependem do spike e da rc publicada.
- **US7 (Phase 5)**: depende da US1 (o README descreve o fluxo pronto).
- **US5 (Phase 6)**: depende da Fundação e da US2; independe da US1.
- **US6 (Phase 7)**: a promoção depende do pipeline mínimo (Lote 4) e do gerador do servidor empacotado (Lote 5); as tasks do instalador independem.
- **US3 (Phase 8)**: depende do registro sem variável (US2) e do servidor (Lote 4).
- **US4 (Phase 9)**: depende de todas as outras.
- **Polish (Phase 10)**: depende de todas; a versão final só sai depois da matriz.

### Within Each User Story

- Testes escritos e falhando antes da implementação correspondente.
- `wallet_config` antes do cliente HTTP; cliente HTTP antes do servidor; servidor antes da pré-versão; pré-versão antes do plugin; plugin antes do instalador do Claude.
- Publicação antes da promoção para `main`, sempre.

### Parallel Opportunities

- Lote 0: os testes de `check_promotion` e dos workflows em paralelo.
- Fundação: testes do link e do bootstrap em paralelo (arquivos diferentes); os blocos do mesmo arquivo seguem em sequência.
- US2: testes de cliente HTTP, redação, erro, instalador e guarda em paralelo; learning lesson, emenda do ADR-0014 e `PRIVACY.md` em paralelo depois da implementação.
- US1 servidor: os testes de contrato e de integração em paralelo.
- US1 plugin: testes do pacote, dos manifestos e do instalador em paralelo; a skill em paralelo com o gerador, o manifesto e o hook.
- US6: testes do instalador, de consistência, de promoção e dos workflows em paralelo; `live.yml`, Dependabot e a verificação de elicitation em paralelo.

## Parallel Example: User Story 1 (servidor)

```text
tests/contract/test_error_signal.py              (wallet_not_configured nas 5 tools)
tests/contract/test_wallet_setup_tool.py         (schema, status)
tests/integration/test_setup_page.py             (página: resultados e segurança)
tests/integration/test_config_reload.py          (dois processos)
tests/contract/test_session_context_configuration.py
tests/contract/test_tool_descriptions.py
tests/unit/test_privacy.py
```

## Implementation Strategy

### MVP

Lotes 0 a 5, mais a pré-versão `0.4.0rc1`: fluxo de branches, spike,
fundação, US2 e US1. Ao fim do Lote 5 o usuário do Desktop instala pelo
marketplace e configura na página local, e a carteira restrita funciona no
terminal e no Desktop. É o objetivo central da spec. A versão final só chega
aos usuários depois do Lote 8.

### Incremental Delivery

1. Lote 0: `develop`, ADR-0020 e portão de promoção para `main`.
2. Lote 1: spike decide o runtime (sem código do produto).
3. Lote 2: fundação (servidor ainda se comporta igual para quem tem `WALLET_ID`).
4. Lote 3: US2, entregável sozinho (corrige o diagnóstico para os usuários atuais).
5. Lote 4: servidor sem configuração, pipeline mínima e `0.4.0rc1`.
6. Lote 5: plugin, validado no Desktop com a rc.
7. Lote 6: README e `doctor`.
8. Lote 7: promoção automática, testes semanais e Dependabot.
9. Lote 8: Devin Desktop, matriz, versão final, promoção e fechamento da 0.4.0.

## Fatiamento em lotes (execução sequencial com gate de aprovação)

Mesma convenção das specs 003 e 004: cada lote é uma branch própria, saída de
`develop`, aberta, revisada e aprovada antes do lote seguinte começar, com o
pedido de revisão contra `develop`. O merge dos pedidos, as tags e a aprovação
da publicação são feitos pelo mantenedor. `main` só muda pela promoção da
pipeline (`promote/vX.Y.Z`) ou por um `hotfix/*`.

| Lote | Branch | Tasks | Gate de aprovação |
|---|---|---|---|
| L0 — Fluxo de branches | `spec-005/fluxo-de-branches` | T001–T007 | Pedido de teste para `main` fora de `promote/v*` recusado; CI em `develop` |
| L1 — Setup e spike | `spec-005/spike-mcpb` | T008–T012 | Ramo de D1 decidido e registrado em learning lesson |
| L2 — Fundação | `spec-005/configuracao-local` | T013–T019 | `test_wallet_config.py` e `test_bootstrap.py` verdes nas 3 plataformas |
| L3 — US2 Carteira restrita | `spec-005/us2-carteira-restrita` | T020–T035 | S4 passos 2 e 3 com a carteira fictícia restrita; guarda de credencial verde |
| L4 — US1 Servidor e rc | `spec-005/us1-servidor-sem-configuracao` | T036–T050 | S3 com `fastmcp.Client`; S5 com a página real; 20 tools; `0.4.0rc1` publicada e verificada |
| L5 — US1 Plugin | `spec-005/us1-plugin-completo` | T051–T061 | S2 (passos 2 a 4) em até 5 minutos em macOS e Windows; um só servidor no Claude Code |
| L6 — US7 e US5 | `spec-005/readme-e-doctor` | T062–T067 | README validado por alguém de fora; S8 com 5 de 5 |
| L7 — US6 Promoção e supply chain | `spec-005/us6-promocao` | T068–T082 | S9 (passos 1 e 3); `promote.yml` em `dry-run`; `live.yml` manual verde |
| L8 — US3, US4 e fechamento | `spec-005/matriz-e-fechamento` | T083–T093 | Matriz sem "não testado"; versão final publicada e promovida; fechamento escrito |
