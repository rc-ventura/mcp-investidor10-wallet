# mcp-investidor10-wallet Constitution

## Core Principles

### I. Documentação oficial primeiro (NON-NEGOTIABLE)

Toda decisão de implementação que toque protocolo MCP ou framework FastMCP
DEVE ser fundamentada na documentação oficial vigente — spec do Model Context
Protocol (modelcontextprotocol.io, incluindo changelog e SEPs) e docs do
FastMCP (gofastmcp.com) — **antes** de codificar ou decidir. Em dúvida, a
primeira ação é uma busca na documentação oficial, com atenção especial às
atualizações recentes (a spec revisa com frequência; premissas de 2025 não
valem automaticamente em 2026). Decisões baseadas na memória do modelo de
linguagem, em convenções de frameworks de agentes genéricos (LangChain,
smolagents, OpenAI function calling) ou em "como geralmente se faz" não são
aceitas sem fonte oficial citada. O resultado da consulta deve ser registrado
(como ADR, research note ou learning lesson, conforme o caso), nunca deixado
só na conversa.

**Rationale**: o projeto já registrou evidência própria de que suposição
falha — `docs/research/agent-behavior.md` verificou no bundle que o Claude
Desktop armazena `instructions` mas nunca o lê, e
`docs/research/tool-error-channels.md` localizou anti-padrão de canal de erro
documentado em produção. Premissa não verificada na fonte é premissa errada
esperando ser descoberta.

### II. Sem anti-padrões de protocolo

O servidor NUNCA introduz padrão já documentado como anti-padrão pelo
ecossistema MCP/FastMCP. Regras mínimas, todas com fonte:

1. Erros previstos nunca retornam como sucesso: o anti-padrão
   "middleware retorna ToolResult sem `isError`" (apache/superset#43358; a
   classe de bugs "isError dropado" em clients/SDKs) é proibido. Erros
   previstos usam o envelope estruturado `{error: {code, message}}` com
   conjunto fechado de códigos (ADR-0007) e evoluem para sinal duplo
   (`isError` + envelope) conforme a direção oficial da spec
   (SEP-1303/SEP-2145: tudo que o modelo pode corrigir é *tool execution
   error*, não *protocol error*; MCP Python SDK v2: "the flag is the
   signal").
2. Valores nunca são fabricados em falha — a fonte falhou, o erro estruturado
   entra; número sintético é corrupção de produto (ADR-0005 §2).
3. Exceções inesperadas não são "tratadas" de volta ao modelo com texto
   mascarado inútil — bug é bug: sanitiza, loga server-side, reporta como
   falha (taxonomia de falhas, research tool-error-channels §5).
4. Mensagens de erro seguem o estilo trigger-phrase: nomeiam o recurso, a
   causa e o próximo passo apontando tool do próprio servidor (evidência medida
   na pesquisa: erro nomeando tool → modelo a chama >80% das vezes).

### III. Uso, não comportamento (fronteira MCP × harness)

O servidor comunica **o que é e como usar**, nunca o comportamento global do
agente. Fontes: spec MCP (lifecycle: `instructions` são "instructions
describing how to use the server and its features"; tools: `description` é
"human-readable description of functionality") e docs do FastMCP (o exemplo
oficial de `instructions` é um índice de uso, não persona). Regras:

1. As **docstrings/descriptions das tools são a camada confiável** — entram
   no prompt de todo cliente ao listar tools. Regras de uso (frescura
   `cached`/`fetched_at`, delay de ~15 min, protocolo de bootstrap, nunca
   inventar valores) moram nelas (ADR-0007 §4).
2. `instructions=` carrega propósito + índice apenas; suporte por cliente é
   desigual e verificado empiricamente (Claude Desktop: nunca lê; Claude Code:
   sim, truncado; Google ADK: bug fechado "by design" indicando tool
   descriptions). Nenhuma invariante do produto pode depender de
   `instructions=`.
3. Persona, idioma, tom e workflow pertencem ao harness (CLAUDE.md, `.devin/`,
   instruções de projeto). O teste de fronteira: "se o agente ignorar, ele usa
   errado a saída da minha tool?" → sim: docstring; não: harness (research
   agent-behavior).

### IV. Estado explícito, protocolo stateless

O design segue a revisão 2026-07-28 da spec (SEP-2567/SEP-2575, ADR-0008):
MCP é stateless no protocolo. Regras:

1. Nenhuma dependência de sessão de protocolo, handshake lifecycle ou
   `Mcp-Session-Id` — removidos da spec; mesmo antes, não eram confiáveis.
2. Estado vive no store versionado `memory.json` (ADR-0002/0006) e é acessado
   por tools com IDs explícitos — exatamente o padrão prescrito pela spec
   ("explicit, server-minted handles passed as ordinary tool arguments"; o
   handle adicional é desnecessário no escopo single-user).
3. Idempotência é o mecanismo de fronteira de sessão: estados terminais
   persistidos (`triggered`, `cancelled`) tornam re-execução do bootstrap
   inócua (SC-006 da spec 001).
4. `get_session_context` permanece bootstrap obrigatório **por convenção
   documentada** (docstring + contrato), nunca por mecanismo de protocolo —
   e skips degradam para "alertas atrasados", jamais para estado corrompido.

### V. Dependências pinadas, upgrades conscientes de protocolo

1. Runtime: `fastmcp` + `httpx` + stdlib, pinados a versões publicadas há
   ≥7 dias (ADR-0001 §4). Tooling pode adicionar deps pinadas; runtime, não.
2. Upgrade de FastMCP não é bump cego: exige leitura do changelog/release
   notes oficiais, conferência contra os SEPs/revisões de spec absorvidos
   (postura de advisory escopado, ADR-0004 §8) e suíte completa verde
   (incl. marcador `live` quando o upgrade tocar cliente/protocolo).
3. Adoção de revisão nova da spec = dependência atualizada pelo framework,
   nunca reescrita de protocolo à mão (ADR-0008 §4).
4. Quando a spec/FastMCP mudar em algo que este produto depende, a resposta
   é: atualizar a premissa registrada (ADR/research) **e** a implementação no
   mesmo ciclo — nunca manter premissa morta só porque ainda funciona.

## Formato e Estilo de Código

As regras abaixo valem para código e documentação **novos ou alterados** a
partir desta emenda; não exigem retrofit do código existente (exceto quando o
trecho já estiver sendo tocado por outra tarefa).

1. **Docstrings só dentro de funções.** Arquivos não começam com docstring de
   módulo antes dos imports nem carregam "docstring do file" em nenhum ponto.
   Documentação de módulo, quando indispensável, fica em um único comentário
   de linha (regra 6) ou fora do código (README/ADRs).
2. **Modularização com parcimônia.** Modularize sempre que organizar de
   verdade, mas não crie módulos minúsculos (poucas linhas) — excesso de
   arquivos com quase nada dentro confunde tanto quanto monólito. O critério
   é coesão visível, não contagem de módulos.
3. **Simplicidade primeiro.** Sempre simplifique quando possível: a solução
   mais simples que cumpre o contrato vence; indireção só entra com motivo
   demonstrável.
4. **TDD obrigatório.** Toda implementação começa pelos testes: escrever,
   ver falhar, implementar, ver passar. Correção de bug começa por um teste
   que reproduz o bug.
5. **Sem emojis.** Em código, comentários, docstrings e documentação do
   projeto.
6. **Comentários ao mínimo.** Evite comentários; quando inevitável, exatamente
   uma linha. Blocos de comentário multi-linha são proibidos.
7. **Comentários e docstrings agnósticos de decisões do projeto.** Nenhuma
   menção a decisões técnicas do projeto dentro do código: sem referências a
   ADRs, FRs/SCs, SPECs, ciclos de review, datas de decisão ou "pesquisa X".
   O código deve se explicar sozinho; as decisões vivem em `docs/adrs/` e
   `docs/research/`. (Docstrings de tools MCP seguem o Princípio III: descrevem
   uso/contrato para o modelo, também sem citar decisões internas.)
8. **TODO como marcador oficial de revisão.** Quando algo no código precisar
   de revisão futura, marcar com `TODO` (uma linha, regra 6). É o sinal
   padronizado de "precisamos revisar isto" — qualquer outra forma de nota
   pendente não é aceita.

## Premissas Vivas e Fontes de Verdade

- Os ADRs em `docs/adrs/` (0001–0008) são o índice decisório vivo: platform/
  storage, fronteira de persistência, cache/paginação, threat model,
  dependência da API não documentada, memória embutida + bootstrap, envelope
  passthrough, alinhamento stateless. Nenhuma decisão coberta por ADR é
  reaberta sem novo ADR.
- `docs/research/` fundamenta com fontes primárias (spec, docs FastMCP,
  issues rastreadas); `docs/learning-lessons/` registra fatos verificados do
  upstream. Novas pesquisas seguem o mesmo padrão (citação de fonte oficial
  + data).
- Toda premissa que depende de comportamento externo (spec MCP, FastMCP,
  API upstream) é **revalidável**: quando a fonte oficial mudar, a premissa
  correspondente é revisada no ciclo seguinte. O risco nº 1 (drift da API
  não documentada, ADR-0005) tem tripwire próprio: validação estrita +
  testes `live`.
- Comportamento divergente entre spec/verificado e código existente: a fonte
  oficial vence; o código se ajusta com teste de regressão e ADR quando a
  mudança for de decisão.

## Fluxo de Desenvolvimento e Gates de Compliance

- Ciclo SDD: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-analyze` → `/speckit-implement` → review (QA + Segurança + Tech
  Leader). Constitution Check é gate explícito em todo plan.
- Todo review classifica achados contra o threat model (ADR-0004) e esta
  constituição: violação de MUST = CRITICAL no `/speckit-analyze` e nas
  revisões — resolve-se o artefato (spec/plan/código), nunca se dilui o
  princípio.
- Gates técnicos: suíte pytest (não-live) verde a cada commit; pre-commit +
  CI por matriz (spec 002); testes `live` opt-in como tripwire de drift.
- Mudanças em contracts de tools, schema de memória ou canais de erro exigem
  ADR + learning lesson quando houver fato novo do upstream, além dos testes
  de contrato verdes.

## Governance

- Esta constituição prevalece sobre qualquer prática, convenção ou preferência
  de estilo. Em conflito, o artefato (spec/plan/tasks/código) é ajustado —
  nunca o princípio, que só muda por emenda formal.
- Emendas: PR dedicado com justificativa, referência à fonte que motiva (spec
  MCP, docs FastMCP, ADR novo) e plano de migração quando afetar trabalho em
  andamento. Versionamento do documento: MAJOR = remoção/redefinição
  incompatível de princípio; MINOR = princípio/seção nova ou expansão
  material; PATCH = clarificação/redação.
- Compliance: todo `/speckit-plan` executa o Constitution Check antes da
  Phase 0 e reconfere após o design; todo `/speckit-analyze` trata conflito
  com MUST como CRITICAL. Guidance de runtime: ADRs + learning lessons.
- A verificação contra documentação oficial (Princípio I) é responsabilidade
  de quem implementa **e** de quem revisa: citação ausente em decisão de
  protocolo é motivo suficiente para bloquear merge.

**Version**: 1.1.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
