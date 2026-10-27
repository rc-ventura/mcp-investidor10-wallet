# Pesquisa: plugins no Devin CLI e compatibilidade com o formato Claude (24/10/2026)

Fonte primária: documentação oficial do Devin CLI
(`~/.local/share/devin/cli/_versions/<ver>/share/devin/docs/extensibility/plugins/overview.mdx`,
lida localmente em 2026-10-24) + verificação empírica de instalação do
nosso plugin (`devin plugins install ./plugin`).

## Conceito

Um plugin Devin é um bundle de **skills** + opcionalmente rules, hooks, MCP
servers e subagentes custom, instalável de repo GitHub, git URL, subpasta de
repo ou pasta local. A instalação de um plugin instala todas as suas skills
e `requiredPlugins`; skills ficam disponíveis como `/plugin:skill`.

## Formatos aceitos (ordem de precedência de manifesto)

1. `.devin-plugin/plugin.json` (formato próprio do Devin)
2. `.claude-plugin/plugin.json` (formato Claude — fallback)
3. `plugin.json` na raiz (spec aberta **Agent Plugins 1.0.0**,
   `github.com/agentplugins/agent-plugins-spec`)

Layout do formato próprio: `skills/`, `rules/`, `agents/`, `hooks.json` na
raiz, `.mcp.json`, `AGENTS.md` (regra always-on).

## Compatibilidade com Claude (verificada empiricamente)

- O Devin lê o **manifesto Claude** quando não há `.devin-plugin/plugin.json`
  e honra o `.mcp.json` da raiz e o campo `mcpServers` do manifesto.
- O **mesmo plugin físico** que carregamos no Claude Code carregou no Devin:
  Skills (3, expostas como `/investidor10-carteira:*`), Agents (1),
  Hook `Stop` (o Devin leu `hooks/hooks.json` em formato wrapper do Claude),
  MCP (1, com `WALLET_ID=${WALLET_ID}`). **Um conjunto de assets serve os
  dois clientes** — restrição que permanece: `commands/` é lido só pelo
  Claude; skills/ é o denominador comum.
- Limites documentados: hooks de plugin são **best-effort/fail-open** (não
  confiar neles como guardrail crítico); subagentes de plugin carregam
  apenas no CLI/Desktop locais, não em sessões cloud; configs MCP de plugin
  não podem conter client secret literal (referenciar `${NAME}`); plugins
  em formato Claude têm `${CLAUDE_PLUGIN_ROOT}` expandido para a raiz do
  plugin.

## Comandos

`devin plugins install <source> [-y] [--local]`, `devin plugins list`,
`devin plugins info <name>` (skills, hooks, rules), `devin plugins remove`.
`--local` instala só na máquina sem adicionar aos plugins pessoais.

## Conclusões para o produto

- O dual-manifesto do nosso plugin (`.claude-plugin/` + `.devin-plugin/`
  dentro de `plugin/`) é o adaptador mínimo; os assets são únicos.
- A spec aberta Agent Plugins 1.0.0 é a convergência futura a observar —
  o Devin já a lê como formato de plugin raiz.