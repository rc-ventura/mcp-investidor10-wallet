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

## Matriz MoSCoW (priorização de 27/10/2026, revisada)

Critério: o produto 0.2.0 já está publicado e é usável pelo mantenedor.
**Atualização de 29/10/2026:** os itens da Fase 1 marcados ✅ foram entregues
na 0.3.0 (spec 004), que aguarda CI nas 3 plataformas e o sign-off. O próximo
Must é a spec 005 (distribuição Desktop).
Decisão do mantenedor (27/10/2026): **tudo que é distribuição do produto
vem na frente**; Claude Desktop é um upgrade do produto e o Devin Desktop
entra no mesmo teste. **Must** = necessário para distribuir com segurança
(alcance, privacidade, não perder dado). **Should** = alto valor, o produto
funciona sem. **Could** = ganho incremental ou de caso de uso único.
**Won't (agora)** = só faz sentido com mais usuários ou depende de fator
externo; reavaliar depois.

| Prioridade | Item | Fase | Por quê |
|---|---|---|---|
| **Must** | Claude Desktop — extensão `.mcpb` como asset de release | 3 | Principal canal de quem não usa CLI; assistente de instalação não alcança apps GUI (research.md D3, spec 003) |
| **Must** | Devin Desktop — testar registro do MCP e carga do plugin | 3 | Mesmo upgrade de alcance; formato ainda não verificado |
| **Must** | Validação de distribuição em máquina limpa (V2 real, Codex via TUI, Gemini) | 3 | Pendências aceitas da spec 003; hoje só há dry-run e contrato |
| **Must** | Carteira restrita (`hash`) + configuração interativa (link → pública/restrita, mascaramento) | 3 | Verificado em 31/10/2026: carteira restrita ou privada recebe HTTP 301 "Acesso não autorizado" e hoje todas as tools de carteira falham com um `unexpected_format` enganoso; leigo não escolhe modo por env var |
| **Must** | ✅ Doc de privacidade — entregue na 0.3.0 | 1 | Pré-requisito de divulgar: o ID da carteira é a credencial e o mascaramento do site é cosmético |
| **Must** | ✅ File lock no `memory.json` — entregue na 0.3.0 | 1 | Com Desktop + CLIs, mais processos escrevem no mesmo arquivo; last-write-wins perde dado |
| **Must** | Listagem em MCP registries (Smithery, PulseMCP, diretório Anthropic) | 3 | É distribuição; **antes de submeter, decidir o risco do ToS** da API não-documentada (ADR-0005) |
| **Should** | Spec 006 — verificação determinística de cálculos | 4 | Maior lacuna de confiança; fica depois da distribuição por ordem de decisão, não por importância |
| **Should** | ✅ Modo privacidade `WALLET_MASK_VALUES` — entregue na 0.3.0 | 1 | Passa a fazer sentido ao distribuir; env var, nunca parâmetro de tool |
| **Should** | Action semanal de live tests | 1 | Aviso antecipado de drift para o mantenedor; o usuário já é protegido pela validação em tempo de execução. Fora da spec 004 — entra quando houver usuários além do mantenedor (após a 005) |
| **Should** | Dependabot — updates revisáveis das actions pinadas por SHA e das deps | 1 | Complemento do pin por SHA entregue na 0.3.0: sem ele os hashes congelam e correções de segurança nunca chegam; com ele, cada update vira PR com diff revisável |
| **Should** | ✅ Changelog append-only da memória (`memory.json.log`) — entregue na 0.3.0 | 1 | Escrita válida porém errada do modelo hoje é invisível; ~25 linhas |
| **Should** | ✅ Sinal duplo de erro (`is_error` + envelope) — entregue na 0.3.0 | 1 | No protocolo, o erro aparece como sucesso |
| **Should** | `get_entries` — log de lançamentos | 2 | Endpoint já validado; responde "o que comprei e quando" |
| **Should** | Tool de projeção de renda recorrente (bola de neve) | 2 | Lição validada; evita usar DY médio |
| **Should** | Skill "monitor de juro longo" | 4 | Motivação real e pequena; vale para os 4 clientes |
| **Could** | ✅ `instructions=` no FastMCP — entregue na 0.3.0 | 1 | Melhora a descoberta; ajuda nos registries |
| **Could** | ✅ Validação de payloads via pydantic — entregue na 0.3.0 | 1 | Decisão de design para as tools novas |
| **Could** | ✅ Remover a migração legada `./memory.json` — entregue na 0.3.0 | 1 | Dead code de transição |
| **Could** | `get_earnings_detailed` | 2 | O detalhe por ativo existe na API; hoje só o total é exposto |
| **Could** | Roteamento de cotação por tipo de ativo | 2 | Cobre FIIs; o resto depende de fonte externa |
| **Could** | Alertas compostos e gatilhos por indicador | 2 | Depende de baseline real e de fonte de cotação |
| **Could** | Snapshot de posições para diff entre sessões | 2 | `get_entries` cobre parte do caso |
| **Could** | Coleção `trades` na memória | 2 | Caso de uso do mantenedor; `decisions` serve de contorno |
| **Could** | Métricas locais + subcomando `doctor` | 3 | Diagnóstico de suporte sem telemetria: o usuário cola o resumo sanitizado numa issue |
| **Won't (agora)** | Avaliação Ollama local + nota na doc | 1/3 | Depende do mask e de privacidade total como requisito |
| **Won't (agora)** | Reconciliação corretora↔carteira | 2 | Grande; reavaliar após `get_entries` |
| **Won't (agora)** | Spike multi-carteira | 2 | Contornado por regra de memória |
| **Won't (agora)** | Telemetria remota opt-in | 3 | Pouco valor com poucos usuários; contradiz o posicionamento local e exige endpoint hospedado |

Nota: os itens "Fora de escopo" ao final do documento seguem valendo e não
entram na matriz.

**Numeração e sequência (decisão do mantenedor, 27/10/2026):**
1. **Spec 004 — Hardening** (Fase 1 inteira, exceto Ollama): file lock, doc de
   privacidade, `WALLET_MASK_VALUES`, changelog append-only da memória, sinal
   duplo de erro e os itens menores (`instructions=`, pydantic, remoção da
   migração legada). A action semanal de live tests saiu da 004 em
   27/10/2026 (ver item na Fase 1). Vem primeiro
   porque o Desktop da 005 aumenta o número de processos sobre o mesmo
   `memory.json`. **Entregue na 0.3.0** (28-29/10/2026), com revisão final em
   7 ciclos (`reports/sdd-final-review/004/`). A T048 e a T055 foram aprovadas pelo
   mantenedor em 31/10/2026 e a T054 fechou com o CI verde em `main`; falta
   criar a tag. A sequência está em `specs/004-hardening/fechamento.md`.
2. **Spec 005 — Distribuição Desktop**: `.mcpb` do Claude Desktop, teste do
   Devin Desktop e validação em máquina limpa (V2 real, Codex, Gemini);
   suporte à carteira restrita com configuração interativa (link →
   pública/restrita + mascaramento, decisão de 31/10/2026); depois, a
   submissão aos registries.
3. **Spec 006 — Verificação determinística de cálculos** (desenho em 3
   camadas já aprovado); os demais Should da Fase 2 por ordem de risco.

---

## Fase 0 — Correções de produto (bloqueiam distribuição)

> Entregue no ciclo 002 (spec `specs/002-distribution-readiness/`, 18/10/2026).

- [x] **Remover o WALLET_ID pessoal do default** — o `wallet_client.py`
  usava a carteira do autor quando a env não estava definida. Produto
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

> Escopo da **spec 004 (Hardening)**, decisão de 27/10/2026 — exceto a
> avaliação Ollama e a action semanal de live tests. Entregue na 0.3.0
> (28-29/10/2026); seguem abertos só esses dois itens.

- [x] **File lock no memory.json** — dois clientes (ex.: Claude Desktop +
  Devin) spawnam dois processos sobre o mesmo arquivo; `os.replace` atômico
  evita corrupção, mas escritas concorrentes se perdem (last-write-wins).
  Lock barato (fcntl/portalocker) resolve.
- [x] **Changelog append-only da memória (`memory.json.log`)** — hoje toda
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
- [x] **Sinal duplo de erro (`is_error` + envelope)** — ver
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
- [x] **Doc de privacidade** — tabela "o que vai para onde": Investidor10
  (API pública), provedor do LLM (contexto das tools), arquivo local
  (memory.json). Incluir o modelo de ameaça real: **o ID/link da carteira é
  a credencial** — quem o tem vê todos os valores via API, e o botão de
  mascarar do site é cosmético (verificado em 17/10/2026, ver item abaixo).
  Nota explícita de que o modo 100% local exige LLM local (Ollama).
- [x] **Modo privacidade `WALLET_MASK_VALUES`** — mascaramento **do lado do
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
  **Retirada da spec 004 em 27/10/2026**: a validação em tempo de execução
  do `wallet_client` (campos e tipos obrigatórios → `unexpected_format`) já
  impede que drift vire dado errado; o job só antecipa o aviso ao
  mantenedor, que hoje usa o produto quase todo dia e é o primeiro a ver o
  erro. Reavaliar quando a spec 005 trouxer usuários do Desktop. Decisões
  já tomadas (clarificação da 004):
  - **carteira pública dedicada com posições fictícias** (ação B3, FII,
    ETF internacional, tesouro, cripto), nunca a carteira real — logs do
    Actions são públicos e um assert que falha imprime o payload;
  - ID em segredo do repositório (`LIVE_WALLET_ID`);
    `on: schedule` semanal + `workflow_dispatch`, nunca em PR; não bloqueia
    CI nem release; notificação padrão de falha do GitHub basta;
  - ~~`tests/conftest.py`: trocar o default `WALLET_ID` (carteira real) por ID
    fictício e exigir `WALLET_ID` explícito nos testes `live`~~ (feito em
    28/10/2026);
  - asserts dos testes `live` imprimem só `error.code`, nunca o payload;
  - fatos de plataforma a revalidar na doc oficial: schedule só roda no
    branch default e é desativado após 60 dias sem atividade no repo.
- [x] **`instructions=` no FastMCP** — preencher com **propósito + índice**
  (o que o servidor é, por onde começar, envelope de dados, delay das
  cotações), **não** com comportamento do agente — ver
  [`docs/research/agent-behavior.md`](research/agent-behavior.md).
  Uma linha no `server.py`; já ajuda no Claude Code hoje e a spec 2026-07-28
  formaliza o campo em `server/discover`.
- [x] **CHANGELOG** — acompanha o empacotamento da Fase 0.
- [x] **Validação de payloads via pydantic (decisão de design)** — pydantic
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
- [x] **Remover a migração legada `./memory.json` → canônico** — a
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
  ADR-0010 já registra a remoção como condição de invalidação nº 1.
  **Feito na 0.3.0**: a remoção foi antecipada (single-user já migrado), e a
  nota de migração está no CHANGELOG e na emenda do ADR-0010.

### Pendências da revisão final da spec 004 (28-29/10/2026)

> Achados dos ciclos 1 a 5 de `reports/sdd-final-review/004/`. Os bloqueantes
> do ciclo 1 (modo 0600 da trava e do log, `mask_error_details`, `.memory-*` no
> `.gitignore`, emendas dos ADRs) foram corrigidos no próprio ciclo. Os itens
> abaixo foram fechados em 28 e 29/10/2026, ainda dentro da 0.3.0, com teste
> para cada um. O ciclo 3 pediu um ciclo 4 (QA + Segurança) para verificar as
> correções; o ciclo 5 pediu um ciclo 6 (só QA).

- [x] **Frescor das cotações nos alertas** — uma cotação em cache vencido,
  servida durante queda da fonte, não dispara mais o alerta. Ele vai para
  `pending_check` com `reason: "stale_quote"` e segue ativo. ADR-0017.
- [x] **Memória apagada com o servidor rodando** — o arquivo não é recriado
  vazio. A memória fica indisponível, o operador recebe um aviso apontando
  `memory.json.log`, e restaurar o arquivo traz a memória de volta. ADR-0013,
  emenda.
- [x] **Posições truncadas** — `truncated: true` quando a coleta para antes do
  total declarado. O campo atravessa o modo privacidade.
- [x] **Privacidade** — um campo permitido com valor aninhado é omitido (fecha
  a condição 1 do ADR-0015).
- [x] **Cadeia de suprimentos e disponibilidade** — cache limitado a 256
  entradas, com descarte do que passou da idade máxima; resposta acima de
  10 MB é recusada; `uvx` do instalador com versão fixa (ADR-0012, emenda);
  actions do CI fixadas por SHA; job `audit` com `pip-audit` no CI (ADR-0001,
  emenda).
- [x] **Higiene de testes** — os testes usam o ID fictício `1234567`, e os
  testes `live` exigem `WALLET_ID` explícito. O smoke test de `release.yml` usa
  o ID fictício.
- [x] **Polimento do contrato de erro** — `state_conflict` (12º código) para
  cancelar um alerta inativo; `invalid_params` nomeia o argumento; o texto do
  contrato de retry foi corrigido para "até 5 novas tentativas (6 no total)".
  ADR-0014, emenda.
- [x] **Robustez da memória** — `fsync` antes do `os.replace`; `OSError` de
  leitura não é tratada como corrupção; nenhum backup em modo somente-leitura.
- [x] **Ciclo 2: changelog sem seguir symlink** — `O_NOFOLLOW` mais `fchmod`
  pelo descritor, com aviso se a restrição a 0600 falhar.
- [x] **Ciclo 2: dependências com CVE** — `fastmcp` 4.1.2, `authlib` 1.9.1,
  `certifi` 2026.10.19 e `virtualenv` 21.14.13; `pip-audit` sem achados.
- [x] **Ciclo 2: ADR-0004** — status "Accepted (amended)", com ponteiros nos
  itens 2 e 4 para a emenda.
- [x] **Ciclo 3 (29/10/2026)**:
  - idade da cotação pelo relógio monotônico do cache (ADR-0017, emenda);
  - profundidade da trava por thread, com `threading.Lock` (ADR-0013, emenda);
  - `ENOLCK` passageiro;
  - leitura do `memory.json` com `O_NOFOLLOW` e backup dos bytes já lidos;
  - limite de 400 páginas nas posições (ADR-0003, emenda);
  - ID real fora dos documentos (ADR-0004, emenda);
  - LOWs de `get_patrimony_history` e `pending_check`;
  - teste com processos concorrentes disparando o mesmo alerta;
  - 2 learning lessons.
- [ ] **Decisão do mantenedor** — `avg_price`, `user_avg_price` e
  `avg_price_treasure` continuam na allowlist do modo privacidade (decidido na
  spec, `spec.md:545`; o `PRIVACY.md` agora explica o preço médio). O ID real
  segue no histórico do git: aceitar a carteira como pública ou deixá-la privada
  e usar outra nos testes live.
- [ ] **Não feito (LOW)** — chaves do `pending_check` diferentes entre alerta
  inválido (`alert_id`) e falha de cotação (`ticker`); mudar quebraria o
  contrato atual.
- [x] **Ciclos 4 e 5 (29/10/2026)**:
  - `RecursionError` e profundidade acima de 32 níveis vão para o caminho de
    corrupção (ADR-0002, emenda);
  - `total` declarado só se adotado inteiro positivo, e o maior entre as
    páginas (ADR-0003, emendas dos ciclos 4 e 5);
  - `months` de 1 a 600 em `get_patrimony_history`;
  - `memory.json` com BOM é lido normalmente;
  - arquivo rejeitado (corrompido ou de versão futura) e apagado com o servidor
    rodando não é recriado vazio;
  - 2 learning lessons.
- [ ] **Adiado (LOW, ciclo 5)** — orçamento de tempo da checagem de cotações em
  `get_session_context`. Os alertas ativos são checados um a um, e cada
  cotação pode levar até 20 s (`REQUEST_TIMEOUT_SECONDS`), então muitos tickers
  com a fonte lenta atrasam a abertura da sessão. Adiado porque a carteira
  real tem poucos alertas ativos e cada ticker é cotado uma vez só, mesmo
  com vários alertas. Corrigir com um teto total de tempo, ou checagem concorrente
  limitada, quando o número de alertas crescer; o que passar do teto vai para
  `pending_check`.
- [x] **Corrigido na 0.3.0 (ciclo 6)** — ID da carteira fora das mensagens de
  erro visíveis ao modelo (`WalletClient._redact`, ADR-0004 emenda de 31/10/2026)
  e `RecursionError` do JSON da fonte tratado como `unexpected_format`.
- [ ] **Pendências do ciclo 6 para a 0.3.1** (LOW, nenhuma bloqueia a 0.3.0):
  - `release.yml`: separar o job do smoke test (`pip install dist/*.whl`
    resolve dependências transitivas sem pin) do job que publica, deixando
    `id-token: write` só no segundo; ensaiar com TestPyPI ou pré-release.
  - `installer/cli.py:150`: `zip(detected, session.outcomes)` pareia o adaptador
    errado quando `--clients` cita um cliente ausente; parear cada adaptador com o
    seu resultado. Em `clients.py`, `_run` deve tratar `TimeoutExpired` e
    `FileNotFoundError`.
  - Caminho absoluto da memória em `memory_error_payload` (e `str(exc)` de
    `_memory_or_param_error`) chega ao modelo; tirar o caminho e escrever o
    ADR-0018 "superfície de erro visível ao modelo".
  - Política de limites: quantidade de alertas e de coleções, tamanho do texto,
    linhas por página em `get_positions` e rotação do `memory.json.log`.
    Decidir primeiro, depois registrar em ADR.
  - `fdopen` em `_read_file` e `_backup_corrupt_file` ainda tem a janela de
    vazamento de descritor que o changelog já fechou.
  - Testes que faltam: `months` inválido com o modo privacidade ligado,
    `months == 600`, dedupe de linhas sem ticker, `memory_store.py` no ramo do
    `fdopen` e `pending_check` com `unexpected_format`.
  - `alert_id=true` aceito como 1 (usar inteiro estrito); surrogate isolado em
    texto vira `memory_unavailable` em vez de `invalid_params`; decidir se
    `record_decision_outcome` pode sobrescrever um desfecho terminal; `cached` e
    `fetched_at` de `get_positions` descrevem só a última página.
- [ ] **Pendências do ciclo 7 para a 0.3.1** (nenhuma bloqueia a 0.3.0):
  - Guarda de profundidade depois do `json.loads` em `wallet_client.request`,
    reaproveitando `memory_store._nests_deeper_than`: um corpo com ~256 a ~9 000
    níveis passa pelo parser, entra no cache e falha na serialização da tool
    (erro genérico mascarado, sem o envelope `{error:{code}}`, e a entrada
    envenenada fica no cache pelo TTL). Só com upstream hostil; teste a ~500 níveis.
  - `Content-Length` com `isdigit()` verdadeiro mas `int()` inválido levanta
    `ValueError` em `wallet_client.py` (só reproduzível com mocks; o h11 recusa
    valores assim numa conexão real). Proteger com `try/except` na mesma mudança.
  - Caminhos absolutos com o usuário local em 3 arquivos antigos versionados
    (`cycle-1-*.md`, `cycle-4-*.md` e `specs/001-mcp-investidor10-wallet/quickstart.md`).
  - Fonte do plugin no instalador sem pin (marketplace, branch `#plugin` e URL da
    extensão do Gemini seguem a branch padrão) e `uvx mcp-investidor10-wallet@<versão>`
    resolvendo as dependências transitivas sem o `uv.lock`.
- [ ] **Dependabot para actions e dependências** — complemento do pin por
  SHA (entregue na 0.3.0, item "Cadeia de suprimentos" acima): o SHA elimina
  o ataque de repontar tag, mas também congela correções de segurança —
  sem automação, os pins envelhecem parados. Criar
  `.github/dependabot.yml` com dois ecossistemas: `github-actions`
  (atualiza o hash e o comentário `# vX` nas actions, schedule semanal
  basta) e `uv` (atualiza `uv.lock`; o job `audit` com `pip-audit` já
  detecta o CVE, o Dependabot fecha o ciclo trazendo o patch). Cada
  update vira PR com diff revisável — mantém a imutabilidade do pin e
  recupera a metade "updates" do trade-off. Fora do escopo do Dependabot:
  o `rev:` do `.pre-commit-config.yaml` (`v0.17.0` do ruff-pre-commit é
  tag, mesma exposição) — pinar por SHA também ou cobrir com
  `pre-commit autoupdate`.

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

> Claude Desktop, Devin Desktop e validação em máquina limpa são a **spec 005**.

- [ ] **Claude Desktop — extensão `.mcpb`** — pacote distribuído como asset
  de release (pesquisa em `specs/003-client-integration/research.md` D3);
  é a spec 005. O assistente de instalação não alcança
  apps GUI.
- [ ] **Devin Desktop — teste de registro do MCP e do plugin** — verificar
  o formato antes de prometer suporte; registrar divergências em
  `docs/learning-lessons/`.
- [ ] **Validação em máquina limpa** — `uvx ... install` real (V2.2/V2.4 do
  quickstart da spec 003), plugin no Codex via TUI e Gemini CLI.
- [ ] **Carteira restrita + configuração interativa** (decisão de
  31/10/2026). Fatos verificados contra a fonte em 31/10/2026:
  - O site tem três modos de compartilhamento: **Pública** (indexável por
    buscadores), **Restrita** (só quem tem o link) e **Privada** (só o
    dono). O link da restrita é `…/wallet/public/<id>?h=<hash>`.
  - Restrita ou privada, sem credencial: o proxy responde **HTTP 301** com
    `{"error":"…Acesso não autorizado"}` e sem `Location`. O
    `wallet_client` só trata `>= 400` como erro: o 301 passa como sucesso,
    faltam as chaves e o resultado é `unexpected_format` ("o payload
    mudou"), um diagnóstico errado. O `validate_wallet` cai no aviso
    genérico de fonte indisponível.
  - Restrita com credencial: o proxy aceita **`?hash=<hash>`** (não `h=`;
    o front lê o `h` da URL e repassa como `hash`). Testado com 200 em
    `summary/metrics`, `donutchart/…/all`, `actives/…`, `barchart/…` e
    `earnings/total-period`. A cotação (`/api/rest`) não depende do modo.

  Escopo:
  - **Correção dos 3xx (independe do resto):** tratar 3xx sem redirect
    seguido como recusa de acesso, com mensagem acionável ("carteira
    privada ou restrita: torne-a pública ou configure o link restrito"),
    no `request()` e no `validate_wallet`. Teste de regressão com o 301
    real e learning lesson.
  - **Hash como credencial:** o cliente do proxy acrescenta `hash=` em
    toda requisição de carteira, nunca na REST. Tratamento igual ao do
    `WALLET_ID` (ADR-0004, `PRIVACY.md`): fora de mensagens de erro, logs,
    envelopes e arquivos versionados. Revisar `request failed: {exc}`, já
    que exceções do httpx podem carregar a URL com a query. A env var
    (ex.: `WALLET_HASH`) existe só como transporte entre o assistente e o
    cliente, não como interface para o usuário.
  - **Modo interativo no terminal (a interface para o leigo):** em vez de
    pedir o ID e documentar env vars, o assistente `install` pede **o link
    da carteira** e deduz o modo. Com `?h=`, é restrita (extrai ID e hash);
    sem ele, é pública; carteira privada é explicada e recusada. Antes de
    registrar, o assistente valida contra a fonte. Em seguida pergunta, em
    linguagem simples, se quer **esconder os valores em R$ do modelo**
    (`WALLET_MASK_VALUES`), dizendo o que se preserva (percentuais,
    alocação) e o que se perde (montantes, histórico de patrimônio). Ao
    final, um resumo mostra o modo escolhido.
  - **Mudar depois sem reinstalar:** um subcomando (ex.: `configure`)
    refaz as perguntas e reescreve o registro nos clientes detectados,
    para quando o usuário troca a carteira de pública para restrita, gera
    um link novo ou liga/desliga o mascaramento. As flags não-interativas
    (`--wallet-url`, `--mask-values`) continuam para scripts e CI.
  - **Claude Desktop (`.mcpb`):** o equivalente gráfico é o formulário de
    configuração da extensão. Verificar na doc oficial do `.mcpb` se o
    `user_config` aceita campo sensível (link) e booleano (mascaramento)
    antes de fechar o desenho.
  - Um ADR próprio (modo restrito e configuração interativa) e o
    `PRIVACY.md` atualizado: a restrita passa a ser a recomendação
    padrão, já que a pública é indexável por buscadores.
- [ ] **Listagem em MCP registries** (Smithery, PulseMCP, diretório
  Anthropic) — após Fase 0. Posicionar como ferramenta comunitária/pessoal:
  o gating real não é técnico, é o ToS da API não-documentada.
- [ ] **Nota Ollama na doc** — depende do resultado da avaliação (Fase 1):
  se o modelo local passar nos critérios, documentar o "modo privacidade
  total" (mask + Ollama); se não passar, documentar honestamente as
  limitações de tool-calling observadas.
- [ ] **Métricas locais + subcomando `doctor`** — observabilidade sem dado
  saindo da máquina. Um evento JSONL por chamada de tool em arquivo irmão
  da memória (`{ts, tool, duration_ms, error_code, cached, version}`,
  nunca argumentos, payload, ticker, valor nem ID da carteira; mesmas
  permissões e `.gitignore` do `memory.json`). `doctor` resume o período
  (chamadas por tool, erros por código, latência p50/p95, taxa de cache,
  versão, SO, cliente) e checa a instalação (runner, `WALLET_ID`
  válido, caminho da memória, trava disponível). A saída é sanitizada
  para o usuário colar numa issue: **relato iniciado pelo usuário** é o
  canal de diagnóstico de máquinas de terceiros. Os hooks do plugin podem
  registrar no mesmo arquivo se o bootstrap `get_session_context` rodou
  (mede se o bundle funciona). Sinais passivos que já existem e
  dispensam telemetria: downloads no PyPI (pypistats.org/BigQuery, por
  versão e SO) e tráfego/issues do GitHub; drift da API será coberto pela
  action semanal de live tests (Fase 1, ainda não implementada).
- [ ] **Telemetria remota opt-in — Won't (agora)** — tecnicamente simples
  (`httpx` já é dependência), mas é decisão de produto/privacidade:
  vira uma quarta linha na tabela "o que vai para onde" do doc de
  privacidade. Só reavaliar com base de usuários que justifique, e então
  com regras fixas: **desligada por padrão** (opt-in por env var), só
  contadores anônimos (versão, SO, cliente, tool, código de erro,
  latência) — nunca ticker, valor, payload, ID da carteira ou conteúdo da
  memória —, documentada no doc de privacidade, com ADR próprio e custo
  de operar o endpoint assumido explicitamente.

---

## Fase 4 — Plugin de comportamento (spec 003 entregue na 0.2.0)

> O plugin (3 skills, guardião, hooks, 4 clientes) saiu na 0.2.0. Seguem
> abertos a spec 006 e a skill "monitor de juro longo".
>
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
- [ ] **Spec 006 — Verificação determinística de cálculos** — o agente
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
- [ ] **Skill "monitor de juro longo" (cruzamento de fontes)** — motivação
  real de 26-27/10/2026: não há cotação de Tesouro/DI na API do
  Investidor10 (410 em `/assets/tickers`, IMAB11 idem), então o alerta de
  juro é manual por natureza. A skill embute o fluxo validado em sessão:
  1. carregar baseline da memória (regras #3/#4 — DI jan/2031 e juros
     reais >2040);
  2. consultar taxa atual em **duas fontes cruzadas** —
     `taxasdotesouro.com` (leitura intraday por título) × CSV oficial do
     Tesouro Transparente (`PrecoTaxaTesouroDireto.csv`, verdade diária);
     ANBIMA como terceira quando o tema for curva de atacado;
  3. reportar delta vs baseline (subiu/caiu e quanto) e enquadrar na
     regra do ciclo MtM: taxa subiu → "fundo" potencial (checar se TD
     está vendendo indexados — suspensões tornam o fundo não executável);
     taxa caiu → ganho já capturado;
  4. instrumentos de referência fixos: IPCA+ 2050 sem juros (duration
     máxima ~24a), IPCA+ 2040, Renda+ 2065 — explicar que acima de 2040
     não existe DI, é juro real de NTN-B.
  Vale para os 4 clientes do bundle (SKILL.md é o denominador comum).

---

## Fora de escopo (decisões deliberadas)

| Ideia | Por que não |
|---|---|
| Hosting multi-tenant (Vercel/Docker) | Resolve problema inexistente (multi-usuário), cria os que existem: auth, custódia de memória financeira, estado por usuário, hop a mais de dados |
| PostgreSQL | Usuário único, escrita humana-escala; exigir DB server para 4KB é anti-valor. Degrau futuro: SQLite |
| MCP de escrita na carteira | LLM mutando registro financeiro via API frágil = receita para corrupção de dados. Reconciliação read-only cobre a mesma fricção com risco muito menor |
| Frontend próprio | Construiria um Investidor10 pior; a diferenciação é a memória persistente, que só existe no agente |
