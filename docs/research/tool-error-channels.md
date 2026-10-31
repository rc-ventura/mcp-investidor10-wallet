# Pesquisa: canais de erro de tool e envelope estruturado (17/10/2026)

Dossiê da análise feita em sessão sobre como erros de tool call chegam ao
modelo: o que o `ParameterErrorMiddleware` resolve e o que não resolve, os
três canais de erro do MCP, e a conexão com o problema "erro como string que
o agente ignora" observado no smolagents. Fontes primárias: código do
`fastmcp==4.0.10` instalado em `.venv/`, ADRs 0003/0007 e `server.py`.

## Os três canais de erro do MCP

Uma falha de tool pode chegar ao cliente por três níveis distintos:

| Canal | Sinal | O que o modelo recebe |
|---|---|---|
| **A. Erro JSON-RPC** | campo `error` na response do protocolo | "a chamada falhou" + texto livre do framework |
| **B. `isError` no result** | `CallToolResult.isError = true` + content | flag de protocolo + texto (mascarado ou não) |
| **C. Payload estruturado** | `structured_content` com `{error: {code, message}}` | dados normais contendo o erro — protocolo diz "sucesso" |

A decisão do projeto (ADR-0007) é o canal C para todos os erros previstos:
conjunto fechado de códigos (`source_unavailable`, `unexpected_format`,
`invalid_asset_type`, `ticker_not_found`, `asset_type_not_supported`,
`invalid_params`, `memory_unavailable`, `not_found`).

## O que o código do FastMCP 4.0.10 faz sem o middleware

Verificado em `.venv/lib/python3.13/site-packages/fastmcp/server/server.py`
(~linhas 1504-1565) e `fastmcp/tools/base.py` (~linhas 171-190):

- **`ValidationError` (args inválidos)** → loga warning e **re-levanta**:
  propaga para o handler de request e vira erro JSON-RPC (canal A). É o
  único erro que o framework escolhe não mascarar.
- **Exceção genérica dentro da tool** → convertida em `ToolError` mascarado
  (`"Error calling tool X: {e}"`, ou apenas o nome da tool com
  `mask_error_details`) → resultado com `isError` (canal B), texto genérico,
  **fora** do conjunto fechado de códigos.
- **`ToolError` levantado pela tool** → canal B com a mensagem.
- **`ToolResult`** aceita `is_error=True` **junto com** `structured_content`
  — os dois sinais podem coexistir numa resposta.

## O que o ParameterErrorMiddleware resolve (e o que não resolve)

`server.py` linhas 24-37: `on_call_tool` envolve `call_next` e converte
`ValidationError` em `ToolResult(structured_content={"error":
{"code": "invalid_params", ...}})`.

**Resolve**: o erro gerado pelo framework (validação de schema, antes do
corpo da tool) deixa de vazar pelo canal A e entra no mesmo envelope de
todos os outros erros. Sem ele, `invalid_params` seria o único código do
conjunto fechado com caminho de fuga — o modelo veria "call failed" + texto
pydantic em vez de JSON com `code`.

**Não resolve**:

1. **Não marca `isError`** (resolvido na spec 004, ADR-0014: o middleware passou a marcar `isError` em todo erro previsto) — no metadata do protocolo a chamada constava como
   sucesso. Cliente/modelo que só olhe nível A/B não percebe o erro (é o
   mesmo modo de falha observado no smolagents: erro dentro de conteúdo que
   precisa ser lido, não sinalizado).
2. **Não cobre exceções inesperadas** na tool — essas seguem saindo pelo
   canal B com texto mascarado do FastMCP, fora do conjunto de códigos.
   (Defensável: exceção inesperada é bug, não erro previsto.)
3. **Não faz o modelo entender** — só torna o erro legível e uniforme;
   reconhecimento e recuperação dependem do modelo + docstrings.

## Mapa de falhas × canal efetivo neste servidor

| Falha | Gerada por | Canal efetivo |
|---|---|---|
| Args inválidos (schema) | FastMCP | C (via middleware) |
| Erro de domínio (fonte, params de domínio, memória) | a tool retorna envelope | C |
| Exceção inesperada na tool | framework | B (texto mascarado) |

## A conexão com o problema smolagents

No smolagents (e equivalentes), exceções de tool viram "observation" — texto
corrido no contexto. O modelo não parseia deterministicamente; `"Error:
division by zero"` é só mais texto, e se chega pelo mesmo canal dos dados
válidos, nada sinaliza "isto é falha". Modelos mais fracos passam direto.

`{"error": {...}}` melhora por três mecanismos:

1. `"error"` como chave é cue lexical forte (treinado em milhões de
   respostas de API);
2. `code` permite matching determinístico — pelo modelo *ou* pelo harness;
3. conjunto fechado = comportamentos documentáveis na docstring.

**Mas** estrutura no payload não é garantia: segue sendo conteúdo que o
modelo pode ignorar. O desenho mais robusto empilha sinais — flag de
protocolo (isError) + código estruturado + instrução na docstring.

## O que a pesquisa externa mudou no quadro (17/10/2026)

Três pesquisas paralelas cobriram: documentação oficial do FastMCP, taxonomia
de falhas/erros estruturados para agentes, e como smolagents/LangChain/
Anthropic SDK/OpenAI SDK tratam o problema. Os achados abaixo alteram a
avaliação da questão em aberto.

### 1. A spec converge para "tudo que o modelo pode corrigir vai por isError"

- **MCP spec (2026-07-28, tools)**: separa *Protocol Errors* (estrutura do
  request, "issues models are less likely to be able to fix") de *Tool
  Execution Errors* (`isError: true`, "actionable feedback that language
  models can use to self-correct and retry with adjusted parameters").
- **SEP-1303** propõe mover **toda** validação de input de erro de protocolo
  para tool execution error: "Protocol Errors are caught at the application
  level by the MCP Client. Only Tool Execution Errors are forwarded back to
  the model… models cannot see these error messages and thus cannot
  self-correct, leading to repeated failures." — ou seja, nosso middleware
  antecipa uma mudança que a própria spec está fazendo; só que a spec manda
  para **canal B**, e nós mandamos para **canal C**.
- **SEP-2145** estende o mesmo movimento para tool-resolution e
  output-validation.
- **Go SDK**: erros vindos da tool SHOULD ir em `isError: true`, "Otherwise,
  the LLM would not be able to see that an error occurred and self-correct."
- **MCP Python SDK v2** (base do FastMCP 4): "Raise `ToolError` and the model
  sees your message. Raise `MCPError` and the protocol sees it. Raise
  anything else and it is a crash." E mais afiado: "**Never `return` an
  error message from a tool.** A returned string has `is_error=False`, so to
  the model (and to every client UI) it looks like the tool worked… `raise`.
  The flag is the signal."

### 2. Payload-only é um anti-padrão documentado em produção

A combinação "middleware captura exceção → retorna ToolResult sem is_error"
— exatamente o padrão do nosso `ParameterErrorMiddleware` — aparece como bug
real em:

- **apache/superset#43358**: middleware catch-all retornando `ToolResult`
  sem `is_error` → "every failed MCP tool call returns a successful
  result… `isError` is never set, so a client following the MCP spec reads
  a failure — including a permission denial — as a success."
- **Classe de bugs "isError dropado"** em clients/SDKs:
  claude-agent-sdk-python PR #717 ("Claude would see the error text but
  treat it as a successful result, breaking error recovery logic"),
  Microsoft agent-framework #4511, Mastra #18482 (com `outputSchema`, o
  `content` era dropado e **nem o texto do erro chegava**), Claude Code
  #67477, adk-go #299 (`error: {}`).
- **Evidência empírica** — "Loud Failures, Quiet Failures" (arXiv
  2610.10062): agentes tratam falha como problema em **91.3%** dos casos com
  erro explícito vs. **58.8%** com valor errado plausível; "agents respond
  to the error channel rather than the content." O canal é o sinal.

### 3. `ToolResult(is_error=True)` existe e é o formato rico

Adicionado no FastMCP **v3.4.0** (PR #4217 — "Returnable Tool Errors") —
está disponível no nosso pin `4.0.10`:

```python
return ToolResult(
    content="not found",
    structured_content={"code": 404, "id": id},
    is_error=True,
)
```

Fecha o issue #4055: antes só `raise` sinalizava erro, "there's no way for a
tool to return a `ToolResult` that signals `isError=True` without raising —
the MCP protocol supports this, FastMCP does not." Agora suporta: **flag de
protocolo + payload estruturado juntos** — o sinal duplo que a questão em
aberto propunha.

### 4. Como os outros frameworks tratam o problema

| Framework | Canal de erro ao modelo | Flag de erro | Default em exceção |
|---|---|---|---|
| smolagents | observation texto (`"Error:\n…Now let's retry"`) | ❌ nenhuma | captura → texto + coaching de retry |
| LangChain/LangGraph | `ToolMessage` | `status="error"` (adapta p/ flag do provider) | `ToolNode` captura → template "Please fix your mistakes" |
| Anthropic SDK | bloco `tool_result` | ✅ `is_error: true` — **único com flag nativa** | tool runner converte exceção → `is_error:true` + msg |
| OpenAI | `tool` msg / `function_call_output` | ❌ nenhuma | erro vai **codificado na string** ("format is up to you") |

Notas relevantes:

- **smolagents** confirma o modo de falha observado: erros e dados normais
  compartilham o mesmo canal de texto (`to_messages` serializa tudo como
  `tool-response` role; issue #1232). Evidência externa: benchmark
  `manifold-cov` registrou *retry storm* — texto de retry-coaching fez o
  agente retentar tool morta 5× e queimar o budget.
- **LangGraph**: o `status="error"` do `ToolMessage` é o equivalente da flag
  — e o ecossistema discutiu ativamente o default de catch-all vs.
  re-raise (PRs #6321/#7177). Guidance do middleware oficial: retornar o
  **tipo** da exceção, não a mensagem crua (vazamento de internals).
- **Anthropic**: docs recomendam mensagem instrutiva ("what went wrong and
  what Claude should try next"); PR #717 mostra que a flag `is_error`
  **muda comportamento de recuperação** do modelo, não é cosmética.
- **OpenAI**: sem flag nenhuma — a convenção documentada é literalmente a
  nossa: codificar o erro no payload (`{"error": ...}` ou texto). Ou seja,
  nosso canal C é a única opção no mundo OpenAI; no mundo MCP existe
  canal B disponível e a spec o recomenda.

### 5. Taxonomia de falhas × recuperador

Síntese das fontes (LangChain fault-tolerance, MCP SDK, yaw.sh, SpecTool):

| Tipo de falha | Quem recupera |
|---|---|
| Schema/args inválidos | **Modelo** — caso mais forte para erro in-band |
| Domínio (not_found, regra violada) | **Modelo** ajusta ou informa usuário |
| Transitório/upstream (timeout, rate limit) | **Sistema** (retry w/ backoff) — modelo retentando "burns context on identical failures" |
| Protocolo/transporte | Cliente/harness (modelo não vê) |
| Bug interno | Ninguém em runtime — sanitizar, logar server-side |
| Auth/credencial | Usuário/operador |
| **Falha silenciosa de payload** (valor plausível errado) | Monitores externos — a categoria mais difícil |

### 6. Conteúdo da mensagem — o que funciona

- "Error messages are prompts" — escrever como instrução ao agente.
- Regra dos "três substantivos" (yaw.sh): nomear **o recurso** que falhou +
  **a causa** + **o próximo passo/tool** ("Use `list_devices` to see valid
  IDs"). Medido: erro nomeando tool → modelo a chama >80% das vezes; erro
  dizendo "check the documentation" → modelo desiste.
- Distinguir transient vs. terminal explicitamente no texto.
- arXiv 2609.35381: instruções estilo-desenvolvedor ("rode este comando")
  **prejudicam** agentes — dano cresce com a capacidade do modelo; o remédio
  é nomear tools do próprio servidor.
- Anthropic ("writing tools for agents"): erro é contrato entre sistema
  determinístico e agente não-determinístico — prompt-engineer a mensagem.

## Questão em aberto — atualizada para recomendação

O design atual (canal C puro) é **a única opção no mundo OpenAI**, mas em
MCP o consenso das fontes é sinal duplo:

1. **Manter o envelope `{error: {code, message}}`** — codes servem routing
   programático e docstrings (two-consumer, issue #3003).
2. **Adicionar `is_error=True`** em todos os erros previstos — via
   `ToolResult(structured_content=…, is_error=True)` nas tools e no
   middleware. Elimina o gap "protocolo diz sucesso"; alinha com a direção
   da spec (SEP-1303/2145); protege contra clients que só olham metadata.
3. **Aprimorar `message`** no estilo trigger-phrase: recurso + causa +
   próxima ação nomeando tool do servidor.
4. **Considerar campo `retryable`**/`category` no envelope — e2a/everruns
   mostram `{code, retryable, hint}` como shape emergente.
5. **`source_unavailable`**: transient upstream é a categoria onde retry
   por sistema (RetryMiddleware do FastMCP) bate retry por modelo — vale
   registrar na docstring se a tool já tentou, para o modelo não queimar
   turnos em chamadas idênticas.

Trade-off residual: setar `is_error` torna erros de domínio e de schema
indistinguíveis no metadata — a distinção fina continua no `code` do
payload. Isso é coerente com a spec: os dois são "tool execution errors".

## Referências externas

- Spec MCP 2026-07-28 (tools): modelcontextprotocol.io/specification/2026-07-28/server/tools
- SEP-1303 / SEP-2145 / issue #3003: github.com/modelcontextprotocol/modelcontextprotocol
- FastMCP docs: gofastmcp.com/servers/tools, /servers/middleware,
  /python-sdk/fastmcp-exceptions; PRs #4217 (ToolResult.is_error), #4445,
  #4579; issues #4055, #4126, #5484; discussion #469 + PRs #434/#550
  (histórico do mask_error_details)
- MCP Python SDK v2: py.sdk.modelcontextprotocol.io/servers/handling-errors
- Bugs de isError dropado: anthropics/claude-agent-sdk-python#717,
  microsoft/agent-framework#4511, mastra-ai/mastra#18482,
  apache/superset#43358, google/adk-go#299, anthropics/claude-code#67477
- Papers: "Loud Failures, Quiet Failures" (arXiv 2610.10062), "Outcome
  Monitors" (2608.19303), "Tools Fail" (2406.19228), "MCP Error Messages
  Written for Developers" (2609.35381), τ-bench (ICLR 2025), IRMA (EMNLP
  2025), SpecTool (2411.13547)
- Frameworks: huggingface/smolagents (agents.py, memory.py; issues #1232,
  #835, #2166, #2457; PR #1060), langchain-ai/langgraph (tool_node.py;
  PRs #6321/#7177, issue #1251; ToolErrorMiddleware), docs.anthropic.com
  (handle-tool-calls, tool-runner), developers.openai.com (function-calling,
  agents-api errors)
- Prática: yaw.sh/mcp-in-production/mcp-error-handling, AWS Well-Architected
  AGENTOPS04-BP03, anthropic.com/engineering/writing-tools-for-agents

## Referências locais

- `server.py` linhas 24-37 (middleware), 42-66 (helpers de envelope)
- `.venv/.../fastmcp/server/server.py` ~1504-1565 (dispatch de exceções)
- `.venv/.../fastmcp/tools/base.py` ~171-190 (ToolResult → CallToolResult)
- ADR-0007 (envelope e conjunto fechado de erros), ADR-0003 (validação)
