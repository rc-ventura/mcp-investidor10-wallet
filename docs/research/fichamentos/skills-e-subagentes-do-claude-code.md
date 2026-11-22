# Fichamento: skills e subagentes de projeto no Claude Code

- **Pesquisado em**: 2026-11-01
- **Atualizado em**: 2026-11-01
- **Origem**: criação da skill `research` e do subagente `pesquisador-fichamento`

## Por que esta pesquisa

O mantenedor pediu um comando que dispare um subagente de pesquisa na web e gere fichamentos. Era preciso
conferir o formato oficial de skills e subagentes e como os dois se ligam.

## Perguntas

1. Quais campos o `SKILL.md` aceita?
2. Como uma skill roda num subagente, e o que ele recebe?
3. Como um subagente de projeto é definido, e como devolve o resultado?
4. Um arquivo novo é carregado sem reiniciar a sessão?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Skills](https://code.claude.com/docs/en/skills.md) | Oficial | 2026-11-01 |
| F2 | [Subagents](https://code.claude.com/docs/en/sub-agents.md) | Oficial | 2026-11-01 |

## Achados

### Skills

- Skill de projeto fica em `.claude/skills/<skill-name>/SKILL.md`; a pessoal, em
  `~/.claude/skills/<skill-name>/SKILL.md`, vale para "All your projects on this machine, but not
  Cowork or cloud sessions" e tem precedência sobre a de projeto. [F1]
- `${CLAUDE_SKILL_DIR}` é o diretório do `SKILL.md`, substituído no conteúdo da skill e nas regras
  Bash de `allowed-tools`. A skill pode ter arquivos de apoio, como `references/` e `scripts/`. [F1]
- Campos: `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`,
  `allowed-tools`, `model`, `context` e `agent`. "Claude Code ignores a field it doesn't recognize without
  reporting an error." [F1]
- `disable-model-invocation: true` evita o carregamento automático, para fluxos acionados com `/name`. [F1]
- `$ARGUMENTS` traz todos os argumentos; se nenhum marcador os recebe, o Claude Code acrescenta `ARGUMENTS:
  <value>` ao fim do conteúdo. [F1]

### Skill em subagente

- "Set to `fork` to run in a forked subagent context." [F1]
- O Claude Code "starts a new subagent of the type set in the `agent` field and gives it the skill content
  as its prompt. The subagent doesn't see your conversation history, so the skill's instructions have to
  stand on their own." [F1]
- `agent` aceita agentes embutidos ou "any custom subagent from `.claude/agents/`". Sem o campo, usa
  `general-purpose`. [F1]
- O subagente roda em segundo plano por padrão; `background: false` faz o turno esperar. [F1]

### Subagentes

- Subagente de projeto fica em `.claude/agents/` (prioridade 3); o de usuário, em `~/.claude/agents/`
  (prioridade 4). [F2]
- `tools` aceita servidores MCP: "`mcp__github__*`". [F2]
- Subagentes podem definir hooks no frontmatter, que "only run while that specific subagent is active". Plugin
  não suporta, e subagente de projeto depende do aceite de confiança. [F2]
- Um subagente concluído pode ser retomado com `SendMessage`, mantendo o histórico. [F2]
- Obrigatórios: `name` e `description`. Opcionais: `tools`, `disallowedTools`, `model`, `skills`, `maxTurns` e
  outros. [F2]
- `tools` é uma lista separada por vírgulas ou uma lista YAML; sem ela, herda todas as tools disponíveis. [F2]
- Com `maxTurns`, ao atingir o limite "Claude Code returns its output marked as partial". [F2]
- O agente principal recebe só o relatório final. A transcrição fica em
  `~/.claude/projects/{project}/{sessionId}/subagents/`. [F2]

### Recarga

- Skills: mudanças em `.claude/skills/` são detectadas na sessão atual. Um diretório de skills criado depois do
  início da sessão pede `/reload-skills`. [F1]
- Subagentes: mudanças em `.claude/agents/` valem na delegação seguinte, mas é preciso reiniciar quando "You
  create a scope's first agent file in a new `agents` directory". [F2]

## O que as fontes não cobrem

- Se `WebSearch` e `WebFetch` podem constar em `tools`: F2 os cita entre as tools que um subagente em segundo
  plano mantém e não tem regra específica para listá-los.

## Divergências entre fontes

Nenhuma registrada.

## Usado em

- Skill de usuário `~/.claude/skills/research/` e subagente de usuário
  `~/.claude/agents/pesquisador-fichamento.md`
