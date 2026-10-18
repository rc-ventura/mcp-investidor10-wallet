# Pesquisa: comportamento do agente e clientes MCP (17/10/2026)

Onde definir o comportamento global do agente que usa este MCP — e como os
clientes desktop o consomem. Fontes primárias: spec MCP 2025-11-25, docs do
FastMCP, issues rastreadas abaixo.

## O campo `instructions` é "para que serve + como usar", não comportamento

- **Spec MCP** (lifecycle): `"instructions": "Optional instructions for the
  client"`, definido como *"Instructions describing **how to use the server
  and its features**... a 'hint' to the model"*.
- **FastMCP** (docs): *"Description of **how to interact with this server**...
  the server's **purpose and available functionality**"*. O exemplo oficial é
  literalmente um índice: *"Provides tools for analyzing numerical datasets.
  Start with get_summary() for an overview."*
- **Spec MCP** (tools): a `description` de uma tool é *"human-readable
  description of functionality"*.

**Conclusão confirmada:** o MCP deve dizer o que é e como usar — não definir
persona/comportamento global do agente.

## Suporte real do campo `instructions` por cliente (varia muito)

| Cliente | Consome `instructions`? |
|---|---|
| Claude Desktop | **Não** — armazena o campo mas nunca lê (`getInstructions()` tem zero usos no bundle; feature request [anthropics/claude-code#43749](https://github.com/anthropics/claude-code/issues/43749)) |
| Claude.ai (web) | Não confiável ([modelcontextprotocol#2428](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/2428)) |
| Claude Code | **Sim** — em user turn (não system prompt), truncado em 2048 chars; "more useful with tool search enabled" |
| Google ADK | Não — bug fechado como *by design*: *"to guide model behavior, put the context in **tool descriptions** instead"* ([google/adk-python#1974](https://github.com/google/adk-python/issues/1974)) |

**Por isso as docstrings das tools são a camada confiável**: descrições de
tool sempre entram no prompt quando o cliente lista as tools, em todos os
clientes. A aposta atual do projeto (regras de uso embutidas nas docstrings)
foi validada pela pesquisa.

## Critério de fronteira: uso vs. comportamento

> Se o agente ignorar a instrução, ele usa **errado a saída da minha tool**?
> - Sim → semântica de uso, pertence ao MCP (docstring): frescura/`cached`,
>   delay de ~15 min, protocolo de bootstrap, nunca inventar valores em erro
> - Não, é sobre o agente em geral → pertence ao **harness**: idioma, tom,
>   persona, workflow pessoal (Claude Projects têm instruções por projeto
>   injetadas antes de cada conversa; Devin usa `.devin/`; Claude Code usa
>   `CLAUDE.md`)

Caso mais frágil hoje: `"Never suggest selling an asset unless the user
explicitly asks"` em `get_wallet_allocation` — política de assessoria, não
uso da tool. Defensável (o `percent_ideal`/`buy` flag existem para o fluxo
FR-007), mas é o primeiro candidato a migrar se formos purgar comportamento
das docstrings.

## Como os desktops usam o servidor (e o memory.json)

- **Não é preciso rodar nada** — stdio significa que o cliente (Claude
  Desktop, Devin) **spawna o server como processo filho** ao abrir a sessão e
  o mata no fim. É isso que a config `command/args` descreve.
- **memory.json fica disponível normalmente** — mesmo processo, mesma
  máquina, mesmo arquivo; o `uv --directory <repo>` define o cwd do processo
  filho, então o caminho relativo resolve. Idêntico em terminal e desktop.
- **Limitação real**: clientes em **nuvem** (conectores Claude.ai, sessões
  Devin cloud) não alcançam um stdio local — exigiriam MCP remoto + memória
  hosteada, que está fora de escopo.
- Mecanismo emergente para acompanhar: FastMCP **Skills provider** (expõe
  SKILL.md como `skill://` resources) — o Claude Code consulta skills
  proativamente; o Claude Desktop, não. Não é caminho principal hoje.
