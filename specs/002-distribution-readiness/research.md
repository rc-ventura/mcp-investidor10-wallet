# Research — Prontidão para distribuição (Fase 0)

Decisões de design do ciclo 002. Todos os "NEEDS CLARIFICATION" do Technical
Context foram resolvidos aqui; a sondagem da API ao vivo foi feita em
18/10/2026 (ver D4).

## D1 — Layout de pacote: src layout + pacote importável

**Decision**: reestruturar para `src/investidor10_wallet/{__init__,server,wallet_client,memory_store,bootstrap}.py` com `server.main()` como entry point (`[project.scripts] mcp-investidor10-wallet = "investidor10_wallet.server:main"`). Build backend: hatchling (default do ecossistema `uv build`).

**Rationale**: console scripts do Python exigem um callable importável (`modulo:funcao`); `python server.py`/`uv run server.py` não é uma forma instalável de publicar. Pacote próprio evita poluir o site-packages global.

**Alternatives considered**:
- Flat + `py-modules` (hatchling inclui os 3 módulos de topo): instalaria `server`, `wallet_client`, `memory_store` como módulos globais do site-packages — nomes genéricos com risco real de colisão. Rejeitado.
- `setuptools` backend: funcionalmente equivalente; hatchling é o par default do `uv` e não exige boilerplate. Rejeitado por não agregar.
- Manter `uv --directory <repo> run server.py` como história de instalação: exige clone, é exatamente a fricção que a Fase 0 elimina. Rejeitado.

## D2 — Entry point e execução de uma linha

**Decision**: `main()` em `server.py` chama `mcp.run()`; o `uvx mcp-investidor10-wallet` (executor de pacotes sob demanda) é o comando documentado de instalação+execução. `uv sync && uv run mcp-investidor10-wallet` permanece para desenvolvimento (editable install pelo próprio `uv sync`, já que o projeto passa a ter build-system). `pythonpath = ["src"]` no pytest garante imports sem install.

**Rationale**: `uvx` resolve "install de 1 linha, sem clone" (ROADMAP Fase 0) com zero passos adicionais de "instalar".

**Alternatives considered**: `pipx run` (segundo executor; documentar só confunde — um comando oficial basta; usuários de pipx conseguem derivar); publicar também como script shim (desnecessário — console script cobre).

## D3 — `WALLET_ID` obrigatório, sem default

**Decision**: remover `os.getenv("WALLET_ID", "1234567")`. Env ausente/vazio → `SystemExit(1)` com mensagem PT-BR nomeando a variável e ensinando a obter o ID na URL pública da carteira (`investidor10.com.br/carteira/<id>` — confirmado na prática de uso). Valor não numérico mantém o comportamento ADR-0003 §3 (mensagem ajustada para PT-BR). Checks de config executam antes da criação do app FastMCP, para que nenhuma tool responda sem carteira configurada.

**Rationale**: FR-002/SC-002 — produto não pode nascer com a carteira do autor como default; falha imediata e acionável é o padrão já estabelecido para env inválida.

**Alternatives considered**: default vazio que degrada só as tools de carteira (servidor sobe "sem carteira") — rejeitado: onboarding confuso, e sem carteira o produto não tem propósito; SystemExit no startup espelha ADR-0003 §3.

## D4 — Validação da carteira no startup (probe)

**Decision**: no início de `main()`, antes de servir, um GET em `/summary/metrics/{WALLET_ID}` (timeout 10s, headers de browser) classifica:
- **200** → startup continua (e o payload já aproveitado/populado o cache se trivial; não otimizar sem necessidade — decisão: descartar, probe é validação pura).
- **404** → `SystemExit(1)` PT-BR: carteira não encontrada **ou privada** — instruindo a conferir o ID na URL e a tornar a carteira pública nas configurações do Investidor10.
- **401/403** → `SystemExit(1)` PT-BR: carteira privada.
- **5xx/timeout/transporte** → warning no stderr e **startup continua** (servidor não fica refém de indisponibilidade transitória; as tools já retornam `source_unavailable` estruturado — ADR-0007).

**Evidência live (18/10/2026)**: `summary/metrics/99999999999` → **404**; `summary/metrics/1234567` → **200**. Não há como testar carteira privada sem um ID real privado — o caso fica coberto pela mensagem "não encontrada ou privada" (RFC: assumir indistinguível) e um teste `live` documenta a regressão se a fonte passar a diferenciar.

**Rationale**: ROADMAP Fase 0 pede "validar o WALLET_ID (fetch + erro amigável)". Fazer no startup (e não na 1ª tool) dá feedback no momento da configuração, quando o usuário está olhando; proteger o startup contra indisponibilidade transitória preserva a filosofia de degrade do projeto.

**Alternatives considered**: validar lazy na primeira chamada de tool de carteira — feedback chega tarde e mistura validação de config com operação; falhar o startup também em 5xx/timeout — torna a fonte single point of failure do servidor inteiro (inclusive das memory tools locais). Ambos rejeitados.

## D5 — Caminho canônico da memória e migração do legado

**Decision**: resolução do caminho em `bootstrap.py`, na ordem:

1. `WALLET_MEMORY_PATH` definido → usar como está (override; **sem migração**).
2. `~/.investidor10/memory.json` existe → usar.
3. `./memory.json` (cwd) existe → **migrar**: criar `~/.investidor10/` (0700), copiar o arquivo para o canônico com escrita atômica (temp 0600 + `os.replace`, mesmo padrão do store), verificar o conteúdo copiado e só então remover o legado; aviso no stderr nomeando os dois caminhos.
4. Nenhum existe → usar o canônico (criado sob demanda pelo store).

**Conflito** (2 e 3 coexistem): o canônico vence; o legado é renomeado para `memory.json.legacy-<YYYYMMDD-HHMMSS>` no próprio local (backup identificável, nunca apagado) e o stderr avisa da divergência. Falha de cópia/permissão: `SystemExit(1)` PT-BR com o caminho tentado — nunca começar a usar um canônico vazio ignorando um legado com dados.

**Rationale**: FR-003/FR-004/FR-005. Stdlib apenas (`pathlib`/`shutil`/`os`) — zero deps novas (ADR-0001). O `MemoryStore` recebe o path já resolvido: schema, escrita atômica, modo degrade e backups `.broken-*` ficam intocados (ADR-0002), e convergir todos os clientes para um arquivo único maximiza a utilidade do file lock planejado na Fase 1 (ROADMAP). Nota: o arquivo o que virar `.broken-*`/backups é sempre criado ao lado do arquivo ativo — com o canônico, todos ficam em `~/.investidor10/`. Adicionar `~/.investidor10/` não entra no `.gitignore` do repo (fora do projeto).

**Alternatives considered**: `platformdirs.user_data_dir` — rejeitado pelo usuário na clarificação Q1 (18/10/2026); symlink do legado → canônico — frágil em apps GUI (cwd instável do stdio); nunca remover o legado após migrar — manteria dois arquivos divergindo silenciosamente entre instalação antiga e nova, pior caso de uso.

## D6 — CHANGELOG e versionamento

**Decision**: `CHANGELOG.md` no formato Keep a Changelog, em PT-BR. Primeira release pública: **0.1.0** (o número já em `pyproject.toml`; nada foi publicado antes). Política enquanto 0.x: feat → bump minor, fix → patch; a partir de 1.0.0, semver estrito. Toda tag `v*` exige seção correspondente no changelog — o workflow de release falha sem ela (FR-008).

**Rationale**: ausência de changelog foi apontada no ROADMAP; gate automatizado na pipeline (não disciplina humana) é o que cumpre SC-006.

**Alternatives considered**: changelog gerado automaticamente de commits — exige conventional commits retroativo e gera ruído em repositório de changelog curado; rejeitado por ora.

## D7 — Gates de qualidade (pre-commit + CI + release)

**Decision**:
- **pre-commit**: framework `pre-commit` pinado (dev tool), hooks `ruff` (lint) e `ruff-format` (check), pins ≥7 dias. `ruff format` rodado uma vez sobre o código existente no PR da feature (registrado como mudança interna no changelog), para os gates ficarem verdes desde o primeiro dia.
- **CI** (`.github/workflows/ci.yml`): matriz Python 3.11/3.12/3.13 × ubuntu-latest/macos-latest; passos `uv sync --locked` → `pytest` (marcador `live` desligado por padrão) → `ruff check` + `ruff format --check`. Testes live ficam fora do CI normal (podem quebrar por drift da fonte — ROADMAP coloca a action semanal de live tests na Fase 1, fora deste ciclo).
- **Release** (`.github/workflows/release.yml`, gatilho tag `v*`): `uv build` → smoke test do wheel (instala num venv limpo, `python -c "import investidor10_wallet"` e entry point `--help`-equivalente sem WALLET_ID deve sair com a mensagem PT-BR e exit 1) → verificação da seção de changelog → publish no PyPI via **trusted publishing (OIDC)** — sem token armazenado.

**Rationale**: FR-009/SC-006; CI matriz cobre o alvo real (macOS) e a portabilidade prometida (Linux); smoke test do wheel pega erros de empacotamento (módulo faltando, entry point quebrado) que testes em source tree não pegam.

**Alternatives considered**: GitLab CLI/local only gates — sem valor, repo já vive no GitHub; publicar com token em secret — OIDC é o padrão atual e não guarda credencial (ADR-0004 §4: sem segredos).

## D8 — Documentação de onboarding (PT-BR)

**Decision**: README reescrito como documento de onboarding PT-BR (a página do projeto no GitHub/PyPI — `readme` no pyproject aponta para ele):
1. O que é + aviso da API interna não documentada (ADR-0005).
2. Instalação/execução de 1 linha (`uvx`) e o único pré-requisito (`uv`/Python 3.11+).
3. **Obter o `WALLET_ID`** — está na URL da carteira pública; **a carteira precisa ser pública** (e o que isso implica em privacidade, 1 frase, apontando para o doc de privacidade da Fase 1).
4. Config por cliente: Claude Desktop (JSON com **caminho absoluto do `uv`** — apps GUI no macOS não herdam o PATH do shell; causa nº 1 de "MCP failed to connect" — `which uv` para descobrir), Claude Code (`claude mcp add`), Devin/config genérica.
5. Tabela de troubleshooting (ID ausente → mensagem X; carteira privada → Y; "failed to connect" → PATH absoluto).
6. Env vars de override (memória, cache TTLs) + onde fica a memória (`~/.investidor10/`).

**Rationale**: FR-006/FR-007/SC-001/SC-004 — onboarding medido em minutos e falhas auto-diagnosticáveis.

**Alternatives considered**: docs só em inglês (público-alvo da comunidade Investidor10 é BR; ROADMAP já decidiu "docs PT-BR"); mkdocs/site — overkill para um README; rejeitado.

## D9 — Idioma das mensagens de startup/onboarding: PT-BR (desvio parcial registrado)

**Decision**: mensagens voltadas ao operador no startup (config inválida, migração de memória, validação da carteira) passam a ser **PT-BR**, conforme spec 002 FR-006/FR-007. **Ficam em inglês**: docstrings (contrato com o modelo, ADR-0007 §4), erros estruturados das tools (`error.message`) e logs técnicos. Isso é um desvio parcial *deliberado* da decisão de 2026-10-10 ("código, docstrings e mensagens de erro em inglês") registrada na spec 001 — escopo do desvio: apenas mensagens operador-facing de bootstrap. Um ADR consolidando a regra de idiomas (bootstrap PT-BR / tools EN) deve ser escrito na implementação.

**Rationale**: o operador que configura o produto é o usuário final BR; o "consumidor" das docstrings é o LLM.

## Restrições carregadas das decisões vivas (não reabrir)

- ADR-0001: runtime = fastmcp + httpx + stdlib; deps novas só em tooling.
- ADR-0002: schema/semântica do `memory.json` intocada (migração copia bytes, não transforma).
- ADR-0003: falhas de config abortam startup com mensagem acionável (não traceback).
- ADR-0004: egresso só investidor10.com.br; PyPI/GitHub não entram em runtime — apenas tooling/pipeline.
- ADR-0007: envelope e conjunto fechado de erros inalterados (FR-010).
