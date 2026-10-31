# ADR-0012: Integração automática de clientes — assistente de instalação e plugin de comportamento

- **Status**: Accepted (amended 2026-10-28)
- **Date**: 2026-10-26
- **Deciders**: Tech Leader + User (ciclo spec 003, decisões de produto fechadas com o mantenedor)
- **Related spec**: [`specs/003-client-integration/`](../../specs/003-client-integration/)
- **Code**: `src/investidor10_wallet/installer/`, `plugin/`, `.claude-plugin/marketplace.json`, `src/investidor10_wallet/server.py`
- **Research**: `docs/research/plugins-{claude-code,devin-cli,gemini-cli,codex-cli}.md`; `docs/learning-lessons/{devin_mcp_add_user_scope,claude_plugin_formato_verificado}.md`

---

## Context

Publicar no PyPI (ADR-0011) resolve a instalação do servidor, mas a conexão
com os clientes de agente continuava manual (formatos e comandos diferentes
por CLI). A spec 003 transformou isso em produto: um assistente de instalação
que registra o servidor nos quatro CLIs alvo (Claude Code, Devin CLI, Codex,
Gemini CLI) e um plugin de comportamento que empacota skills, subagente,
persona e hooks. Durante o ciclo, o mantenedor fechou as decisões de produto:
escopo CLIs (Desktop adiado), produto = **bundle** (MCP + plugin), plugin
behavior-only, extensão aos quatro clientes, persona via hook de sessão.

## Decision

1. **Registro sempre via comando nativo** (`claude/devin/codex/gemini mcp
   add`, escopo user) — nenhuma escrita direta de arquivo de configuração
   nesta feature. Comandos exatos no contrato `contracts/install-cli.md`;
   o `devin mcp add` foi re-verificado (`-s user`, `-e KEY=VALUE` — learning
   lesson devin_mcp_add_user_scope). Idempotência via `mcp list` + protocolo
   interativo de colisão de alias (sempre pergunta pular/atualizar; `--yes`
   não afeta).
2. **O produto é o bundle**: `install` registra o servidor **e** instala o
   plugin por padrão (comandos nativos de instalação de plugin por cliente,
   fontes canônicas do repositório); `--mcp-only` é o escape técnico. O
   plugin permanece **behavior-only** — nenhum manifesto declara
   `mcpServers` — para manter uma única fonte de verdade de conexão (a
   colisão de dois caminhos foi observada de verdade no Devin).
3. **Um plugin, quatro manifestos finos**: assets únicos em `plugin/`
   (skills, agents, hooks) + um manifesto por cliente (`.claude-plugin`,
   `.devin-plugin`, `.codex-plugin`, `gemini-extension.json`) + marketplace
   do Claude Code na raiz do repo. Skills (SKILL.md) são o denominador comum
   verificado nos quatro.
4. **Comportamento empacotado**: 3 skills com as regras do produto; subagente
   `guardiao-de-disciplina` read-only; persona via hook `SessionStart`
   (`additionalContext`); lembrete de memória via hook `Stop` que **propõe**
   registro com confirmação (ADR-0002) e é fail-open. Formato real do Claude
   Code diverge do publicado — learning lesson claude_plugin_formato_verificado.
5. **Commands por cliente**: no Claude Code foram fundidos nas skills
   (v2.1.3 — skills user-invocable por padrão); Devin e Codex não têm
   primitivo separado; **apenas o Gemini** recebe `commands/*.toml`
   (primitivo ativo de invocação do usuário).
6. **Desktop adiado para spec futura** (Claude Desktop, `.mcpb`, apps
   desktop) — estudo próprio de distribuição.
7. **Execução em lotes sequenciais** com gate de aprovação do mantenedor
   entre lotes (decisão de processo do ciclo).

## Alternatives considered

### Alternative A: plugin declarando o servidor MCP (bundle via plugin)

Manifestos com `mcpServers` (via `${WALLET_ID}` do ambiente) fariam o
marketplace entregar o produto completo sem o assistente.

**Why not chosen**: duas fontes de registro do mesmo alias — colisão
observada na prática (config project-local vs user no Devin). O bundle via
assistente entrega o mesmo UX de "um comando" mantendo conexão única.

### Alternative B: assistente default = só MCP (plugin opt-in)

Versão inicial da spec.

**Why not chosen**: o diferenciador do produto é memória + comportamento;
vender "MCP de dados" comoditiza o produto. Os canais de distribuição que
existem nos 4 clientes são de plugin, não de MCP.

### Alternative C: commands/ markdown para todos os clientes

**Why not chosen**: commands são específicos por cliente (Claude .md
legacy/deprecado, Gemini .toml ativo, Devin/Codex sem o conceito). Skills
cobrem a invocação do usuário em 3 de 4 clientes; TOML apenas no Gemini.

## Consequences

### Accepted

- Onboarding de um comando (`uvx mcp-investidor10-wallet install`) com
  relatório PT-BR, idempotente e validado em máquina real (Claude Code
  "Connected", Devin user config, Codex list).
- Plugin com carga real verificada nos dois clientes principais (Skills 3,
  Agents 1, Hooks 2, MCP 0 por decisão).
- Premissas de formato registradas e revalidáveis (learning lessons +
  research docs com fontes e datas).

### Trade-offs

- A validação real do bundle (comandos canônicos `rc-ventura/…`) depende do
  repositório público no GitHub — gated no push/merge das branches da 003.
- Carga real do plugin no Codex e no Gemini pendente (formatos validados por
  contrato; Gemini não instalado na máquina de dev).
- Hooks de plugin do Devin são fail-open e os do Gemini/Codex não foram
  incluídos nesta versão (formatos distintos) — persona e lembrete atuam
  onde foram verificados (Claude Code e Devin).

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. Algum dos 4 clientes mudar o formato de plugin/commands de forma
   incompatível (tripwires: learning lessons + testes de contrato dos
   manifestos).
2. O produto evoluir para distribuição no Desktop (`.mcpb`/extensões) — a
   spec dedicada substituirá/aumentará parte deste desenho.
3. A spec aberta Agent Plugins 1.0.0 se tornar o formato universal (Devin e
   Codex já referenciam; Claude não) — avaliar convergir os manifestos.

### Migration path when needed

- Adicionar/remover um cliente: um adapter em `installer/clients.py` + um
  manifesto fino em `plugin/` + linha no contrato — superfície isolada.
- Mudar a fonte canônica do bundle (repo/org): atualizar
  `plugin_install_commands()` e o contrato.
- Estender hooks para Gemini/Codex: converter `hooks/hooks.json` para os
  formatos próprios de cada um, com carga real verificada antes de ativar.

## References

- `specs/003-client-integration/research.md` (D1–D5)
- `specs/003-client-integration/contracts/install-cli.md` e `plugin-manifest.md`
- `docs/learning-lessons/devin_mcp_add_user_scope.md`,
  `docs/learning-lessons/claude_plugin_formato_verificado.md`
- ADR-0011 (distribuição PyPI), ADR-0002 (memória é do usuário), ADR-0009 (PT-BR operador)
## Emenda 2026-10-28 (pendências da revisão final da spec 004)

**O servidor registrado fica na versão do assistente.** O assistente registra
`uvx mcp-investidor10-wallet@<versão do assistente>` em todos os clientes, e não
mais `uvx mcp-investidor10-wallet` sem versão. Sem versão, cada abertura de
cliente baixava a release mais nova do PyPI, inclusive uma comprometida, sem
nenhuma ação do operador. Com a versão fixa, o que roda é exatamente o que foi
instalado. Para atualizar, roda-se o assistente da release nova
(`uvx mcp-investidor10-wallet@latest install`), que reescreve o registro. Os
comandos manuais do README continuam sem versão, porque o operador que os
digita escolhe o que roda.
