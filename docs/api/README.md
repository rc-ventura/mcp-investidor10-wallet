# API Investidor10 — referência não-oficial

Catálogo de endpoints validados em **17/10/2026**, obtido por engenharia
reversa dos chunks JS do app Next.js `/wallet/` + probes HTTP diretos na
carteira pública `<id>`. Complementado pelas learning lessons.

**Modelo de auth:** carteira pública = **o ID é a credencial** (quem tem o
link lê tudo — o botão "mascarar" do site é cosmético). Rotas de
escrita/configuração retornam `401 Unauthenticated` para carteiras públicas.

**Aviso:** API não-documentada e não-versionada — pode mudar ou exigir auth
sem aviso. Headers: `User-Agent` de browser.

## Superfícies

| Base | Uso |
|---|---|
| `investidor10.com.br/wallet/api/proxy/wallet-app` | Dados da carteira |
| `investidor10.com.br/api/rest` | Catálogo de ativos (cotações, fundamentos) |
| `investidor10.com.br/api/proxy` | Outros proxies (`carteiras`, `minhas-carteiras`) |

---

## Endpoints já expostos como tools (6)

| Endpoint | Params | Info obtida | Tool |
|---|---|---|---|
| `/summary/metrics/{id}` | `type=without-earnings`, `raw=1` | Aplicado, patrimônio, variação, TWR total e 12m | `get_wallet_summary` |
| `/summary/donutchart/{id}/all` | `groupBy=ticker` | Alocação por ticker/classe | `get_wallet_allocation` |
| `/summary/actives/{id}/{asset_type}` | `raw=1`, `api_version=v2`, `selected_wallet_currency`, `start`/`length` | Posições: qty, preço médio, equity, appreciation, %wallet vs %ideal, buy flag, rating, fundamentos | `get_wallet_positions` |
| `/summary/barchart/{id}/{months}/all` | — | Patrimônio mensal: contribuído × ganho de capital | `get_patrimony_history` |
| `/earnings/total-period/{id}` | `start_date`, `end_date` | Total de proventos líquidos no período | `get_earnings` |
| `/assets/tickers/{ticker}` (REST) | — | Cotação + fundamentos de ação B3 (só B3; 404=inexistente, 410=tipo não coberto) | `get_asset_quote` |

## Endpoints validados sem tool — e a decisão para cada um

| Endpoint | Params | Info obtida | Tem tool? | Decisão |
|---|---|---|---|---|
| `/positions/wallet-buying-opportunities/{id}` | `type=list`\|`count` | A "análise inteligente": onde direcionar aporte — ticker, preço atual vs médio, %wallet vs %ideal | ✗ | **CRIAR** `get_buying_opportunities` — é a análise inteligente do site; permite cruzar com nosso cálculo próprio de rebalanceamento |
| `/profitability/{id}/summary` | — | Rentabilidade da carteira vs CDI/IPCA/Ibov/IVVB11, com textos comparativos prontos | ✗ | **CRIAR** `get_profitability` — hoje o MCP não compara com benchmarks; lacuna real |
| `/profitability/{id}/table` | — | Rentabilidade mensal por ano | ✗ | **MESMA TOOL** — `get_profitability` com opção de visão resumida/mensal |
| `/profitability/{id}/compare-chart/{idx}/{m}` | `idx`, `months` | Série comparativa com índice | ✗ | **NÃO CRIAR** — probe retornou 500 genérico; instável |
| `/earnings/list/{id}` | `start`/`length` (paginação) | Tabela por pagamento: ticker, tipo, datas, bruto, líquido | ✗ | **CRIAR** `get_earnings_detailed` — filtrar por `date_payment_original` (provisionados vêm no ano 2126); habilita segregação isenta vs tributada |
| `/earnings/summary-chart/{id}/{months}` | `months` | Proventos por ativo já agregados no período | ✗ | **NÃO SEPARADA** — pode ser fonte interna alternativa ao `earnings/list` no `get_earnings_detailed` (avaliar qual é mais rico: este já agrega, aquele dá bruto/líquido por pagamento) |
| `/earnings/summary-card/{id}` | — | Cards + metas da carteira (`greatest_goal`: target × current × estimated_date) | ✗ | **CRIAR** `get_wallet_goals` — metas que o usuário criou na plataforma, para cruzar com `wallet_goal` da memória (nossa é declarativa; esta é quantitativa) |
| `/earnings/barchart/{id}/{months}` | `months` | Proventos por mês por categoria | ✗ | **NÃO SEPARADA** — mesma informação derivável de `earnings/list` agregando por `month`; usar internamente se preciso |
| `/positions/wallet-highlights/{id}` | — | Melhor e pior ativo da carteira | ✗ | **CRIAR** `get_wallet_highlights` — barata, alto valor de apresentação ("sua melhor posição hoje é...") |
| `/positions/earnings-position/{id}` | `type=count`\|`list` | Posições com retorno positivo/negativo de proventos | ✗ | **AVALIAR** — pode virar parte de `get_wallet_highlights` (mesmo conceito: top/bottom); não merece tool própria |
| `/summary/ticker-percentage-notification/{id}/{type}/{tid}` | `?other=1` | Indicação comprar/vender por posição (`{value, type: comprar\|vender}`) | ✗ | **AVALIAR** — enriquecer `get_wallet_positions` ou `get_buying_opportunities` com o veredito da plataforma; baixa prioridade |
| `/entries/{id}/contribution-consolidation` | `qtymonths`, `dategroup`, `tickertype`, `qtymin`, `currency` | Aportes BUY/SELL por mês | ✗ | **CRIAR** `get_contributions` — histórico de aportes; complementa `get_patrimony_history` (que separa contribuído de ganho) |
| `/entries/{id}/contribution-distribution` | `qtymonths`, `dategroup`, `tickertype`, `date`, `grouptype` | Distribuição de aportes | ✗ | **AVALIAR** — provavelmente parte do `get_contributions`; sondear payload antes de decidir |
| `/entries/{id}/{seção}` | `length`, `start`, `orderBy=date`, `raw=1`, `search[value]`, `tickerableId`/`tickerableType` | **Log de lançamentos ordem a ordem** (data, Compra/Venda, ticker, qty, preço, total, source) — descoberto 26/10/2026 via página `/wallet/public/{id}/entries?h={hash}`. Seções: `1`=renda variável, `2`=cripto, `4`=outros, `5`=tesouro, `6`=RF privada | ✗ | **CRIAR** `get_entries` — log transacional completo; resolve "o que comprei/vendi e quando" |
| `/get-user-bootstrap` | `wallet_id` | Metadados: nome, `public`, `last_update`, currency | ✗ | **CRIAR** `get_wallet_meta` — `last_update` permite ao agente dizer "carteira atualizada há X dias"; mitiga a fricção de stale wallet |
| `/summary/info/{id}` | — | Dados brutos da carteira (~20KB) | ✗ | **NÃO CRIAR** — redundante com `actives`; útil só como fonte interna |
| `/summary/banner-profit/{id}` | `raw=1` | Lucro decomposto: capital + proventos recebidos | ✗ | **AVALIAR** — valor incremental pequeno; pode enriquecer `get_wallet_summary` em vez de tool própria |
| `/commentary/{id}` | — | Comentários | ✗ | **NÃO CRIAR** — vazio na carteira testada; baixo valor |
| `/assets/fiis/{ticker}` (REST) | — | Cotação + `payments[]` de FII (`last_quotation.price`, rendimentos por cota) | ✗ | **ESTENDER `get_asset_quote`** — não é tool nova: roteamento interno por tipo de ativo (FII → `/fiis/`). Habilita também alertas de preço em FIIs |

## Auth-gated (401 na carteira pública — sem possibilidade de tool)

| Endpoint | O que seria | Por que não |
|---|---|---|
| `/quotation?...` | Cotação interna da wallet (cobriria FIIs!) | 401 — só dono logado; o caminho para FII é `/api/rest/assets/fiis/{t}` |
| `/target-price/info/{id}/{type}` | Preço-alvo | 401 |
| `/calculate-ideal-percentage` | Cálculo de % ideal por rating | 401 |
| `/notes/{id}/{type}` (GET/POST) | Notas da carteira | 401 |
| `/settings/integration/{id}/b3`, `/minhas-carteiras/check-integration/.../b3` | **Sincronização corretora↔carteira** | 401 — confirma: integração automática é feature de conta logada; nosso MCP segue read-only |
| `/settings/{get-info,update,delete}`, `/notifications`, `/like`, `/average-price` (POST), `/entries` (POST) | Configurações e escritas | 401 — e fora de escopo por design (agente sugere, nunca muta) |

## Decisões resumidas — tools novas (Fase 2 do roadmap)

| Tool | Endpoint(s) | Justificativa |
|---|---|---|
| `get_buying_opportunities` | `positions/wallet-buying-opportunities` | A análise inteligente do site, dentro do MCP |
| `get_profitability` | `profitability/*/summary` + `table` | Lacuna: comparação com benchmarks |
| `get_earnings_detailed` | `earnings/list` (ou `summary-chart`) | Breakdown por ativo/tipo/mês; segregação isenta/tributada |
| `get_wallet_goals` | `earnings/summary-card` | Metas quantitativas da plataforma |
| `get_wallet_highlights` | `positions/wallet-highlights` (+ `earnings-position`) | Melhor/pior posição |
| `get_contributions` | `entries/contribution-*` | Histórico de aportes |
| `get_wallet_meta` | `get-user-bootstrap` | Nome + `last_update` → detecta carteira stale |
| (extensão) `get_asset_quote` | `assets/fiis/{t}` | Roteamento interno FII — habilita alertas de FII |

## As duas fronteiras de validação (não confundir)

O projeto valida em **duas fronteiras diferentes** — com motivos distintos:

| Fronteira | Onde | Por quê |
|---|---|---|
| **Fonte (esta API)** | `wallet_client.py`: `required_keys`, `required_types`, `NUMERIC`, `expected_type` | A API é não-documentada e não-versionada — pode mudar shape a qualquer momento. Validar **antes de cachear e antes de devolver ao agente** → `unexpected_format` em drift, nunca valor fabricado (FR-016) |
| **Persistência (memory.json)** | `memory_store.py`: `version`, `_valid_collection`, `alert_is_valid`, `TICKER_PATTERN` | O arquivo tem schema (v1) não por "gravação coesa", mas porque **pode ser editado à mão ou corrompido entre sessões** → degrada graciosamente (`memory_unavailable`), nunca crash, nunca sobrescreve o original |

Regra de polegar: persistência você controla; API de terceiro você **desconfia**. Para tools novas, a decisão registrada no roadmap é um `BaseModel` pydantic por endpoint em modo validate-then-passthrough.

## Quirks globais

- **`type` em `buying-opportunities`/`earnings-position` = `count`|`list`**
  (não é tipo de ativo); outro valor → 422 "O campo type selecionado é inválido."
- **Provisionados poluem `earnings/list`**: `date_payment` = "Provisionado",
  `date_payment_original` placeholder no ano 2126 — filtrar pela original.
- **`sum` do `total-period` = Σ `net_total_original`** do `earnings/list`
  (verificado centavo a centavo). O gap bruto→líquido revela retenção
  (~30% withholding em ETFs internacionais).
- **404 vs 410** em `/assets/tickers/{t}`: 404 = inexistente, 410 = classe
  não coberta — já mapeado para `ticker_not_found`/`asset_type_not_supported`.
- **Números chegam como string** (`"96801.5575437"`) — sempre parsear.
- **Paginação estilo DataTables** (`start`/`length`) em `earnings/list` e
  `summary/actives` — o client já faz merge (ADR-0002).
