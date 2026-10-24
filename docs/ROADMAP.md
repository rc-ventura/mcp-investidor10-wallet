# Roadmap — mcp-investidor10-wallet

Análise de produto de 17/10/2026. Prioridades em fases; itens de uma fase não
dependem dos anteriores, exceto onde indicado.

Princípios que orientam este roadmap (decisões já tomadas, não reabrir):

- **Local stdio é a arquitetura certa** — o dado é pessoal/financeiro; a
  interface é o agente (Claude Desktop/Code/Devin). Hosting multi-tenant
  (Vercel/Docker) não cria valor para o usuário e piora privacidade.
- **A fronteira de privacidade é o provedor do LLM, não a localização do
  MCP** — os resultados das tools entram no contexto do modelo de qualquer
  forma; documentar isso explicitamente em vez de fingir que "local" resolve.
- **Agente sugere, nunca muta** — sem escrita na carteira do Investidor10 via
  API não-documentada. A resposta para a fricção corretora↔carteira é
  reconciliação read-only, não um segundo MCP de escrita.
- **memory.json é a decisão certa para este escopo** — usuário único,
  escrita humana-escala. O degrau seguinte, se algum dia houver, é SQLite
  (ainda local, sem servidor), não Postgres.

---

## Fase 0 — Correções de produto (bloqueiam distribuição)

> Entregue no ciclo 002 (spec `specs/002-distribution-readiness/`, 18/10/2026).

- [x] **Remover o WALLET_ID pessoal do default** — hoje
  `wallet_client.py` usa `1234567` quando a env não está definida. Produto
  não pode nascer com a carteira do autor como default: exigir `WALLET_ID` na
  env e abortar startup com instrução clara de como achar o ID (está na URL
  pública da carteira).
- [x] **Empacotar no PyPI** — entry point + `uvx mcp-investidor10-wallet`
  como install de 1 linha (é o que reduz fricção de verdade; hoje exige
  clonar o repo). Inclui pre-commit/CI e versionamento semântico. Pré-
  requisito: item abaixo (path de memória estável — com `uvx` não existe
  repo dir, e o default relativo `memory.json` quebra).
- [x] **Path de memória estável por usuário** — o default relativo
  `memory.json` só funciona porque amarra ao diretório do repo (funciona em
  terminal e desktop, ambos com `uv --directory`). Para produto, o default
  deve ser um local estável por usuário (ex.: `~/.investidor10/memory.json`
  ou `platformdirs.user_data_dir`) — e todos os clientes passam a
  compartilhar o mesmo arquivo (reforça o file lock da Fase 1).
- [x] **Onboarding de primeira execução** — validar o WALLET_ID (fetch +
  erro amigável), explicar que a carteira precisa ser pública, docs PT-BR.
  Incluir o gotcha de desktop: apps GUI no macOS não herdam o PATH do
  shell — a config precisa do **caminho absoluto do `uv`** (ex. 
  `/Users/<user>/.local/bin/uv`); é a causa nº 1 de "MCP failed to
  connect" no Claude Desktop.

## Fase 1 — Robustez e confiança

- [ ] **File lock no memory.json** — dois clientes (ex.: Claude Desktop +
  Devin) spawnam dois processos sobre o mesmo arquivo; `os.replace` atômico
  evita corrupção, mas escritas concorrentes se perdem (last-write-wins).
  Lock barato (fcntl/portalocker) resolve.
- [ ] **Changelog append-only da memória (`memory.json.log`)** — hoje toda
  mutação escrita pelo modelo é invisível: o backup `.broken-*` só cobre
  arquivo corrompido, não "escrita válida porém errada" (tese ruim, regra
  sobrescrita, outcome errado). Implementar `_append_changelog(op,
  collection, id, before, after)` nos dois funis de mutação (`add()` e
  `update()`) + `set_wallet_goal()` e `evaluate_alerts()` (um registro por
  alerta triggered). Decisões: JSONL em **arquivo separado** (dentro do
  memory.json cresceria sem bound e sujaria cada save); logar **antes** do
  `save()` — mutação cujo save falha também fica registrada, melhor para
  forense; falha no log é best-effort e não derruba a operação; adicionar
  `memory.json.log` ao `.gitignore` (mesmos dados financeiros pessoais).
  Rotação deferida — single-user, escrita humana-escala. ~25 linhas em
  `memory_store.py`, zero mudança de schema nem de contrato das tools.
- [ ] **Sinal duplo de erro (`is_error` + envelope)** — ver
  [`docs/research/tool-error-channels.md`](research/tool-error-channels.md).
  Hoje todos os erros chegam só pelo payload `{error: {code, message}}` —
  no metadata do protocolo a chamada consta como sucesso (o mesmo
  anti-padrão documentado em apache/superset#43358). Migrar erros
  previstos para `ToolResult(structured_content=…, is_error=True)` nas
  tools e no `ParameterErrorMiddleware`: flag de protocolo + código
  estruturado juntos (disponível desde FastMCP 3.4.0; alinha com a direção
  da spec — SEP-1303/2145). Aproveitar para: revisar `message`s no estilo
  trigger-phrase (recurso + causa + próxima ação nomeando tool do
  servidor) e avaliar campo `retryable`/`category` no envelope.
- [ ] **Doc de privacidade** — tabela "o que vai para onde": Investidor10
  (API pública), provedor do LLM (contexto das tools), arquivo local
  (memory.json). Incluir o modelo de ameaça real: **o ID/link da carteira é
  a credencial** — quem o tem vê todos os valores via API, e o botão de
  mascarar do site é cosmético (verificado em 17/10/2026, ver item abaixo).
  Nota explícita de que o modo 100% local exige LLM local (Ollama).
- [ ] **Modo privacidade `WALLET_MASK_VALUES`** — mascaramento **do lado do
  MCP**, o único que funciona de verdade: o botão de mascarar do site só
  altera a renderização, a API segue retornando tudo. Verificado
  empiricamente em 17/10/2026 — com a carteira mascarada,
  `get_wallet_summary` retornou patrimônio/aplicado/lucro reais e
  `get_wallet_positions` retornou quantidades, `equity_brl` e
  `earnings_received` por ativo. Quando ativo, as tools retornam apenas
  percentuais/ratios (`percent_wallet`, `percent_ideal`, `dy`, `p_vp`,
  ratings, variações %) e omitem montantes (`applied`, `equity`,
  `profit_amount`, `quantity`, `equity_brl`, `earnings_received`,
  patrimônio). **Preserva**: análise de alocação, rebalanceamento por %,
  diversificação, fundamentos, bola de neve por cotas. **Perde**: valores
  em R$, aporte sugerido em reais, histórico de patrimônio. **Deve ser env
  var, não parâmetro de tool** — a proteção é contra o dado sair da máquina
  para a LLM; um param poderia ser "desligado" pelo próprio modelo. Combinado
  com Ollama forma o modo "privacidade total" (item abaixo).
- [ ] **Avaliação Ollama local** — testar se um modelo local com bom
  tool-calling (candidatos: qwen3, llama3.1+) opera o MCP com qualidade
  suficiente para as funções necessárias. Critérios de sucesso (a medir em
  sessão real): chama `get_session_context` no bootstrap sem ser lembrado;
  não inventa valores em erro; respeita as regras de apresentação
  (`cached`/`fetched_at`, delay ~15 min); usa as memory tools corretamente;
  raciocínio de rebalanceamento coerente em PT-BR. Se passar,
  `WALLET_MASK_VALUES` + Ollama = modo "privacidade total" — seus dados
  nunca saem da máquina, um diferencial de produto real.
- [ ] **Action semanal de live tests** — a API upstream é não-documentada; o
  risco #1 de produção é ela mudar sem aviso. Rodar `pytest -m live` em
  schedule (GitHub Actions) para detectar drift antes dos usuários.
- [ ] **`instructions=` no FastMCP** — preencher com **propósito + índice**
  (o que o servidor é, por onde começar, envelope de dados, delay das
  cotações), **não** com comportamento do agente — ver
  [`docs/research/agent-behavior.md`](research/agent-behavior.md).
  Uma linha no `server.py`; já ajuda no Claude Code hoje e a spec 2026-07-28
  formaliza o campo em `server/discover`.
- [ ] **CHANGELOG** — acompanha o empacotamento da Fase 0.
- [ ] **Validação de payloads via pydantic (decisão de design)** — pydantic
  já está no dependency tree (transitivo do FastMCP). Regra proposta para
  as **tools novas da Fase 2**: um `BaseModel` leve por endpoint em modo
  **validate-then-passthrough** (`model_validate` só para validar; o
  envelope continua devolvendo o payload cru — preserva a decisão de
  passthrough do ADR-0007). `Strict` cobre o bool-vs-int; `FiniteFloat`
  cobre NaN/inf; materializa a "regra uniforme de validação" que o ciclo 3
  diagnosticou. **Não fazer**: retrofit das tools existentes sem outro
  motivo para tocar nelas (já passaram 4 ciclos verdes) nem schema de
  memory.json via pydantic — shape é a parte fácil, a semântica de degrade
  (backup `.broken-*`, modo indisponível) continua custom.
- [ ] **Remover a migração legada `./memory.json` → canônico** — a
  máquina inteira (ramos `MIGRADO`/`CANONICO_WINS`, `_atomic_copy`,
  verificação de inode, backup `legacy-<timestamp>`, guarda
  `cwd == canonical`) é código de transição da Fase 0 e virou dead code:
  o único usuário migrou em 18/10/2026 (`./memory.json` →
  `~/.investidor10/memory.json`) e `memory.json` está no `.gitignore`.
  Removê-la elimina toda a superfície TOCTOU/symlink da migração e faz o
  bootstrap **parar de inspecionar o cwd** — um `memory.json` stray
  passa a ser ignorado em vez de absorvido no canônico. Manter:
  `_ensure_canonical_dir` + `_ensure_not_symlink` no canônico e o
  `WALLET_MEMORY_PATH` verbatim. `resolve_memory_path()` colapsa para
  override → garantir `~/.investidor10` (0700) → retornar canônico.
  Impacto: altera contratos da spec 002
  (`contracts/packaging-and-config.md`) e remove testes de migração;
  ADR-0010 já registra a remoção como condição de invalidação nº 1 —
  decidir se antecipa agora (single-user já migrado) ou gateia no 1.0.0
  conforme o texto original. Se adiada, o hardening da ADR-0010 §3–4
  segue válido até lá.

## Fase 2 — Valor de produto (oriundo das learning lessons)

- [ ] **`get_earnings_detailed`** — ver
  [lesson 17/10](learning-lessons/earnings_list_detalhe_proventos_por_ativo.md).
  Chamar `/earnings/list/{id}` uma vez (payload completo, sem paginação) e
  filtrar/agregar no cliente por `date_payment_original` (nunca pelo campo
  formatado — provisionados vêm com placeholder no ano 2126). Retornar
  `{by_ticker, by_month, by_type, gross, net}`. Habilita:
  - breakdown por ativo (pedido real de sessão);
  - segregação de renda **isenta** (FIIs, "Dividendos") vs **tributada**
    (JSCP, "Rend. Trib.", ETFs internacionais com withholding ~30%);
  - base para a projeção de renda abaixo.
- [ ] **Roteamento de cotação por tipo de ativo** — duas etapas, na ordem:
  1. **Interno primeiro**: a [lesson do bola de neve](learning-lessons/efeito_bola_de_neve_calculo.md)
     mostra que `/api/rest/assets/fiis/{ticker}` existe e retorna
     `last_quotation.price` + `payments[]`. Rotear FIIs para essa rota já
     habilita cotação **e alertas de preço para FIIs** — hoje MXRF11,
     CDII11, IRIM11 e JURO11 ficam como `pending_check` eterno nos alertas
     (a carteira é FII-heavy; alerta de FII é valor imediato).
  2. **Depois, fonte externa** para ETFs internacionais/cripto (candidatas:
     Yahoo Finance / brapi.dev), conforme
     [lesson 15/10](learning-lessons/get_asset_quote_apenas_acoes_b3.md).
     O mapeamento do HTTP 410 → `asset_type_not_supported` já está feito.
- [ ] **Tool de projeção de renda recorrente ("efeito bola de neve")** —
  ver [lesson 17/10](learning-lessons/efeito_bola_de_neve_calculo.md).
  Regras obrigatórias vindas da lição validada em sessão:
  - usar o **rendimento recorrente atual** (piso dos últimos ~6
    pagamentos; mediana + flag "extras detectados" quando desvio > ~20%),
    nunca DY 12m nem média cega dos últimos 12;
  - mostrar sempre **o rendimento usado e o racional** (piso vs. média),
    nunca o número nu;
  - escopo: efeito literal só para FIIs (pagamento mensal); ações B3 =
    média conceitual; declarar a escolha (ex.: JURO11 oscila — média mais
    honesta que o último pagamento).
  - cruzar **declarado vs. recebido**: `payments[]` do FII ×
    `/earnings/list` da carteira (fontes complementares).
- [ ] **Tool de reconciliação corretora↔carteira** — responde à maior
  fricção do fluxo real (compra na corretora → Investidor10 fica stale → MCP
  lê carteira desatualizada). Read-only: usuário cola posições da corretora
  (ou CSV), o MCP faz o diff contra `get_wallet_positions` e lista
  exatamente o que atualizar manualmente no site. **Não** é um segundo MCP
  de escrita — escrita via API não-documentada em registro financeiro é
  anti-feature.
- [ ] **Spike: multi-carteira (reserva × investimento)** — motivação real de
  sessão (24/10/2026): a reserva de emergência (~16% do patrimônio, em
  Tesouro Selic) entrou na soma da classe Tesouro e distorceu a análise de
  alocação — corrigido na conversa com regra de memória, não por feature.
  Cenário do usuário: carteiras separadas no Investidor10 (reserva de
  emergência × aposentadoria). Investigar **antes** de prometer escopo:
  - **Pergunta de API — RESOLVIDA (24/10/2026)**: cada carteira é um ID
    público isolado; `summary/metrics`, `summary/donutchart` e
    `summary/actives` respondem HTTP 200 com o mesmo envelope para a
    segunda carteira (ID `<id>`). Não há auth nem endpoint de "listar
    carteiras" — aceitar N IDs basta;
  - **Caso de borda descoberto**: posições podem se repetir entre
    carteiras — a mesma posição de Tesouro Selic 2031 (0,86 título) está
    registrada tanto na carteira principal quanto na de reserva do
    usuário. Uma view consolidada precisa de dedup (mesmo ticker +
    quantidade), senão conta o patrimônio em dobro;
  - **Config**: `WALLET_IDS` (lista) na env + parâmetro `wallet` opcional
    nas tools de carteira (default = primeira); ou `wallet` como filtro
    sobre uma única config;
  - **Memória**: rules/theses provavelmente globais; `wallet_goal`,
    posições e análises de alocação são **por carteira** — decidir schema
    (chave por wallet_id) sem quebrar o memory.json atual;
  - **Alternativa leve (avaliar primeiro)**: tag de papel da posição na
    memória local (ex.: `role=reserva`) excluindo da análise de alocação —
    resolve o caso real de hoje sem multi-carteira. O spike decide se
    multi-carteira é over-engineering frente a essa opção.

## Fase 3 — Distribuição

- [ ] **Listagem em MCP registries** (Smithery, PulseMCP, diretório
  Anthropic) — após Fase 0. Posicionar como ferramenta comunitária/pessoal:
  o gating real não é técnico, é o ToS da API não-documentada.
- [ ] **Nota Ollama na doc** — depende do resultado da avaliação (Fase 1):
  se o modelo local passar nos critérios, documentar o "modo privacidade
  total" (mask + Ollama); se não passar, documentar honestamente as
  limitações de tool-calling observadas.

---

## Fora de escopo (decisões deliberadas)

| Ideia | Por que não |
|---|---|
| Hosting multi-tenant (Vercel/Docker) | Resolve problema inexistente (multi-usuário), cria os que existem: auth, custódia de memória financeira, estado por usuário, hop a mais de dados |
| PostgreSQL | Usuário único, escrita humana-escala; exigir DB server para 4KB é anti-valor. Degrau futuro: SQLite |
| MCP de escrita na carteira | LLM mutando registro financeiro via API frágil = receita para corrupção de dados. Reconciliação read-only cobre a mesma fricção com risco muito menor |
| Frontend próprio | Construiria um Investidor10 pior; a diferenciação é a memória persistente, que só existe no agente |
