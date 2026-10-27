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
  `wallet_client.py` usa `2061045` quando a env não está definida. Produto
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
- [ ] **`get_entries` — log de lançamentos (compras/vendas)** — endpoint
  **descoberto e validado em 26/10/2026** via a página pública
  `/wallet/public/{id}/entries?h={hash}`: `GET
  /wallet/api/proxy/wallet-app/entries/{id}/{seção}` com
  `?length&start&orderBy=date&raw=1` (paginação DataTables, mesmo padrão
  de `summary/actives`). Retorna cada lançamento com data, tipo
  (Compra/Venda), ticker, quantidade, preço, total e `source`
  (MANUAL/BÔNUS/integração). Seções observadas: `1` = renda variável
  (ações + FIIs + ETFs internacionais), `2` = cripto, `4` = outros/caixa,
  `5` = tesouro, `6` = renda fixa privada; `3` retornou vazio na carteira
  testada — mapear a enum completa antes de implementar. Resolve a
  pergunta "o que eu comprei/vendi e quando", que hoje só se infere por
  aproximação. Payload inclui HTML em `ticker_img` — passthrough ou
  strip no cliente, decidir.
- [ ] **Alertas compostos e gatilhos por indicador (juro longo)** — motivação
  real de 26/10/2026: o usuário quis alertar sobre "juro longo subindo" e
  não conseguiu — alertas são só ticker+preço e não há cotação de Tesouro.
  Decisão de design (honesta): **baseline real, não proxy correlacionado**
  (EGIE3 ~ juro é correlação frouxa = falso positivo). Caminho em 3 partes:
  1. **Depende de "Roteamento de cotação por tipo de ativo"** (item acima):
     NTN-B 2035/2045 e ETFs IMA-B (B5P211/IMAB11) têm preço observável com
     correlação mecânica ao juro (duration) — cotação de Tesouro vem da
     mesma API (já aparece em `get_wallet_positions`; falta rotear).
  2. **Alertas compostos**: condições com múltiplos fatores + **janela de
     confirmação** (gatilho persiste por N sessões consecutivas antes de
     disparar) — histerese contra falso positivo. Candidato a spec própria.
  3. **Limite arquitetural declarado**: produto stdio local sem daemon →
     "automático" = avaliado no bootstrap de cada sessão. Hook de sessão
     seria redundante (`get_session_context` já avalia alertas); skill do
     agente não resolve fonte de dados. Notificação sem abrir sessão exige
     arquitetura de daemon — decisão de produto separada, se um dia fizer
     sentido.
- [ ] **Snapshot de posições para diff entre sessões** — motivação real
  de 26/10/2026: sem um snapshot anterior, o agente não consegue dizer o
  que mudou na carteira (compras, vendas, mudança de PM/quantidade)
  quando a API de lançamentos não basta ou está stale. Persistir em
  memory.json (ou arquivo irmão) o último snapshot de posições por
  classe `{ticker, qty, avg_price, equity_brl}` + `captured_at`; no
  bootstrap ou sob demanda, diff contra `get_wallet_positions` e listar
  deltas. Complementa `get_entries` (que cobre lançamentos explícitos):
  o snapshot detecta também drift de PM e posições criadas por eventos
  (bonificação, desdobramento) que não viram lançamento. Cuidado com
  tamanho do memory.json — snapshot é leve (~20 posições).
- [ ] **Coleção `trades` na memória (tracking de trades táticos)** —
  motivação real de 26-27/10/2026: o usuário opera tranches de marcação
  a mercado em títulos longos (IPCA+), e hoje o melhor encaixe é
  `decisions` — que registra intenção, não ciclo de vida do trade
  (abertura, tranches parciais, alvo de saída, fechamento, P&L).
  Nova coleção `trades` no schema do memory.json (bump de versão +
  migração vazia, padrão do `memory_store`): campos propostos
  `{ticker_ou_titulo, thesis_ref, opened_at, tranches: [{date, qty,
  price}], status: open|closed, close_price, close_at, outcome_note}`.
  Tools: `open_trade`, `add_tranche`, `close_trade`, `list_trades`.
  Sinergia direta com a regra de monitor de juro longo (baseline DI) e
  com `get_entries` para conferir se o lançamento registrado no
  Investidor10 bate com o tranche declarado.
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
    segunda carteira (ID 2076291). Não há auth nem endpoint de "listar
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

## Fase 4 — Plugin de comportamento (spec 003, em andamento)

> Decisões de produto fechadas com o mantenedor em 24/10/2026. Pesquisa de
> formato dos 4 clientes em
> `docs/research/plugins-{claude-code,devin-cli,gemini-cli,codex-cli}.md`.

- [x] **Plugin = casca de comportamento, sem MCP** — o plugin empacota
  skills + subagentes + hooks (+ persona abaixo), e **não** registra o
  servidor: o registro é responsabilidade exclusiva do assistente de
  instalação (`install`, spec 003 US1). Evita dois caminhos de registro do
  mesmo alias colidirem (observado na prática com o Devin) e mantém uma
  fonte de verdade para a conexão.
- [x] **3 skills** (análise da carteira, check de tese, resumo de
  dividendos) — cada uma embute as lições do produto (bootstrap
  `get_session_context`, delay ~15 min, rendimento recorrente e nunca DY
  médio).
- [x] **Subagente guardião de disciplina** (read-only por construção) —
  confronta decisões do usuário com as regras/teses salvas na memória;
  nunca grava, só propõe registro com confirmação.
- [x] **Hook Stop de memória** — lembra de registrar decisões discutidas
  sem `log_decision`/`log_insight`; propõe e aguarda confirmação
  (ADR-0002); fail-open.
- [x] **Persona via hook SessionStart** — injeta em toda sessão o papel do
  assistente de investimentos (instruções de uso das tools, linguagem,
  cuidados), via `additionalContext` (mecanismo oficial distribuível,
  equivalente a CLAUDE.md — ver pesquisa plugins-claude-code.md).
- [x] **Estender o plugin aos 4 clientes** — Codex (manifesto
  `.codex-plugin/plugin.json` sobre as mesmas skills) e Gemini
  (`gemini-extension.json` + `commands/*.toml` espelhando as skills);
  skills SKILL.md são o denominador comum verificado nos 4.
- [ ] **Spec 004 — Verificação determinística de cálculos** — o agente
  hoje calcula números financeiros na LLM, sem verificação. Desenho em 3
  camadas aprovado:
  1. **Tool `check_calculation` no servidor** (determinística): o modelo
     envia a fórmula usada + o resultado apresentado; o servidor computa e
     devolve `{computed, matches}` — alinha com a Constituição II (valores
     nunca fabricados);
  2. **Hook Stop tipo prompt** no plugin: antes de encerrar, validar
     qualquer cálculo financeiro com a tool e corrigir divergência — roda
     deterministicamente (matcher `*`), sem depender de o agente chamar
     subagente;
  3. **Subagente "auditor de números"** (read-only + tool): refaz o cálculo
     de forma independente e compara, para sessões de decisão.
  Exige ADR + learning lesson (mudança de contrato de tools).

---

## Fora de escopo (decisões deliberadas)

| Ideia | Por que não |
|---|---|
| Hosting multi-tenant (Vercel/Docker) | Resolve problema inexistente (multi-usuário), cria os que existem: auth, custódia de memória financeira, estado por usuário, hop a mais de dados |
| PostgreSQL | Usuário único, escrita humana-escala; exigir DB server para 4KB é anti-valor. Degrau futuro: SQLite |
| MCP de escrita na carteira | LLM mutando registro financeiro via API frágil = receita para corrupção de dados. Reconciliação read-only cobre a mesma fricção com risco muito menor |
| Frontend próprio | Construiria um Investidor10 pior; a diferenciação é a memória persistente, que só existe no agente |
