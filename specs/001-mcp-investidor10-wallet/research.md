# Research — 001-mcp-investidor10-wallet

Pesquisa e decisões técnicas. Todas as questões em aberto do Technical Context foram resolvidas; não restam NEEDS CLARIFICATION.

## D1 — Framework MCP: FastMCP (Python)

- **Decision**: [FastMCP](https://gofastmcp.com) (`fastmcp` no PyPI), tools via decorador `@mcp.tool`, `mcp.run()` com transport stdio por padrão.
- **Rationale**: framework oficial de referência para MCP em Python; gera schemas das tools a partir das anotações de tipo e docstrings (as docstrings viram a descrição que o modelo lê — crítico para o agente usar as tools corretamente); suporta tools async nativamente; stdio é exatamente o modelo "cliente spawna processo" exigido por FR-015. Confirmado na documentação atual via Context7. Pin de produção: `4.0.10` (última publicada há ≥7 dias em 2026-10-10).
- **Alternatives considered**: SDK MCP low-level (`mcp.server.lowlevel`) — muito boilerplate para zero ganho; implementação TypeScript do SDK — quebra a familiaridade Python do usuário sem benefício.

## D2 — Cliente HTTP: httpx async + cache TTL em memória

- **Decision**: `httpx.AsyncClient` com `User-Agent` de browser e timeout de 20s; cache em memória (dict chave path+params → `(timestamp, resposta)`, TTL via `WALLET_CACHE_TTL_SECONDS`, padrão 600s). Toda resposta de tool inclui metadado `cached: bool` + `fetched_at` para o agente sinalizar idade dos dados (FR-014, edge case de indisponibilidade).
- **Rationale**: httpx é o padrão async moderno em Python e é mockável com `respx` nos testes. Cache in-process é suficiente porque o processo é spawnado por sessão de chat; TTL curto garante dados "recentes" no sentido da spec.
- **Alternatives considered**: `requests` — bloqueante, forçaria tools sync; `aiohttp` — API mais verbosa sem ganho; `cachetools.TTLCache` — dependência extra para algo de ~15 linhas de stdlib.

## D3 — Fonte de dados: API interna Investidor10 Wallet (já descoberta)

- **Decision**: usar os endpoints já mapeados na investigação prévia (base `https://investidor10.com.br/wallet/api/proxy/wallet-app` + `/api/rest/assets/tickers/{ticker}` para cotações), conforme tabela da spec de planejamento original:
  - `/summary/metrics/{id}?type=without-earnings&raw=1` → resumo
  - `/summary/donutchart/{id}/all?groupBy=ticker` → alocação
  - `/summary/actives/{id}/{Tipo}?raw=1&api_version=v2&start=0&length=50&order_column=equity_total&order_dir=desc` → posições (Tipo ∈ `Ticker|Fii|EtfInternational|Treasure|Crypto`)
  - `/summary/barchart/{id}/{meses}/all` → evolução patrimonial
  - `/earnings/total-period/{id}?start_date=&end_date=` → proventos
  - `/api/rest/assets/tickers/{ticker}` → cotação/fundamentos
- **Rationale**: endpoints verificados manualmente respondendo sem auth para carteira pública. Tratamento de falha: resposta não-2xx, schema inesperado ou classe vazia geram erro explícito estruturado (ver contracts), nunca valores sintéticos (FR-016).
- **Alternatives considered**: scraping das páginas HTML públicas — frágil e mais lento; APIs pagas de mercado (brapi etc.) como fonte primária — desnecessário enquanto a interna responder; descartadas como primária (podem virar fallback futuro fora do escopo).

## D4 — Memória de longo prazo: tools embutidas no próprio servidor (NÃO MCP separado)

- **Decision**: subsistema de memória implementado como tools do próprio servidor FastMCP, persistido em `memory.json` local.
- **Rationale**: esta era a principal questão de design aberta. Decisão tomada com o usuário em 2026-10-10. Fatores:
  1. **Determinismo**: FR-009 (carregar memória no início da sessão) e FR-011 (verificar alertas na abertura, sem duplicar disparos) exigem comportamento garantido. Com um MCP genérico separado (`@modelcontextprotocol/server-memory`), tudo depende do modelo lembrar de ler o grafo e de interpretar estado de alertas a partir de observações livres — falha silenciosa provável. Uma tool `get_session_context` única torna o bootstrap da sessão determinístico: carrega o digest da memória **e** avalia alertas ativos contra cotações atuais, marcando os disparados.
  2. **Schema de domínio**: alertas têm máquina de estados (`active → triggered/cancelled`) e decisões têm desfecho (`pending/accepted/rejected/postponed`) — incompatível com knowledge graph genérico.
  3. **Não compete com o harness**: Devin/Claude Code já têm memórias genéricas — mas elas não respondem deterministicamente "quais alertas ativos existem?" nem "qual o desfecho da decisão #7?". Nosso store cobre apenas conhecimento de domínio estruturado; notas narrativas podem continuar no harness sem sobreposição.
- **Alternatives considered**: `@modelcontextprotocol/server-memory` separado (rejeitado pelos motivos acima); híbrido (estruturado no próprio servidor + notas no server-memory — rejeitado: dois stores para manter, e o harness já cobre notas livres).

## D5 — Storage da memória: `memory.json` único, versionado, escrita atômica

- **Decision**: um único arquivo JSON (path via `WALLET_MEMORY_PATH`, default `<repo>/memory.json`) com `"version": 1`, carga inteira em memória por operação, persistência via tmp+rename atômico. Acessos encapsulados em `memory_store.py`.
- **Rationale**: decisão tomada com o usuário — menor fricção para um MVP que é "um conector num harness que já existe". Zero dependências (stdlib), legível/editável à mão, e a migração futura para SQLite é reescrever uma classe com um script de import trivial (schema já é relacional-friendly: coleções nomeadas com IDs). Escala esperada (centenas de entradas) torna queries em memória irrelevantes.
- **Alternatives considered**: SQLite — mais robusto mas overkill no MVP; mantido como caminho de migração documentado. Markdown+frontmatter — máxima legibilidade mas parsing frágil e sem queries.

## D6 — Falha/corrupção da memória: modo degradado explícito

- **Decision**: se `memory.json` estiver corrompido/inacessível, o servidor sobe em "modo sem memória": tools de dados funcionam normalmente; tools de memória retornam erro estruturado `memory_unavailable` instruindo o agente a avisar o usuário (edge case da spec). O arquivo corrompido é preservado com sufixo `.broken-<timestamp>` na primeira tentativa de reescrita.
- **Rationale**: a spec exige operação degradada sem perder as demais capacidades.
- **Alternatives considered**: crash no startup — viola o edge case; recriar silenciosamente — perda de dados inaceitável.

## D7 — Alertas de preço: verificação na abertura de sessão

- **Decision**: alertas vivem em `memory.json` com estado; a avaliação acontece dentro de `get_session_context`, que busca cotações apenas dos tickers com alertas `active` (reusando o cache), dispara os satisfeitos (`triggered_at`), e retorna-os no payload. Sem monitoramento contínuo (decisão de escopo já registrada na spec).
- **Rationale**: implementa FR-011/SC-006 de forma determinística e barata (uma chamada por ticker com alerta ativo, no máximo).
- **Alternatives considered**: daemon/monitor em background — fora do escopo aprovado; tool separada `check_alerts` — o modelo poderia esquecer de chamá-la; embutir no bootstrap da sessão é o único caminho que garante 100% de entrega (SC-006).

## D8 — Docstrings como contrato com o modelo

- **Decision**: todas as tools terão docstring descrevendo quando usar, formato dos parâmetros e o significado dos campos de retorno — o FastMCP usa isso como descrição exposta ao LLM.
- **Rationale**: a qualidade das respostas do agente depende diretamente dessas descrições (o modelo não lê o código).
- **Ajuste (2026-10-10, decisão do usuário)**: docstrings e mensagens de código em **inglês**; a interação do agente com o usuário permanece em pt-BR conforme a spec (a spec define o idioma da interação, não o do código).

## D9 — Política de dependências

- **Decision**: `fastmcp` e `httpx` pinados a versões publicadas há ≥7 dias; sem ranges flutuantes (`latest`, `*`). Instalação/execução via `uv` (`uv run server.py`), conforme config dos clientes.
