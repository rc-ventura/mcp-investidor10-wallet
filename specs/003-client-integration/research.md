# Research — Integração automática com clientes de agentes (spec 003)

- **Feature**: specs/003-client-integration/
- **Data**: 2026-10-24
- **Política de fontes**: toda decisão cita a documentação oficial do cliente
  alvo verificada hoje (Constituição I).

## Entradas do Technical Context resolvidas

| Entrada | Resolução |
|---|---|
| Linguagem/Versão | Python ≥3.11 (pacote existente) |
| Dependências | **apenas stdlib** no assistente de instalação (`argparse`, `json`, `pathlib`, `shutil`, `subprocess`, `platform`); validação da carteira reusa o `wallet_client` existente (httpx já pinado). Nenhuma dependência runtime nova (Constituição V) |
| Storage | O assistente é stateless entre execuções; estado vive nas configs gerenciadas pelos comandos nativos de cada cliente (nenhuma escrita direta de arquivo nesta feature) |
| Testes | pytest (suíte existente, `respx` para mocks de validação de carteira); assets do plugin validados por teste de contrato que parseia os manifestos |
| Plataforma | CLIs em macOS/Linux (matriz CI atual; Windows via comandos nativos onde existirem); Desktop fora do escopo desta feature |
| Tipo de projeto | Ferramenta de CLI + assets de distribuição de plugin de agente |
| Restrições | Mensagens ao operador em PT-BR (ADR-0009); registro idempotente (FR-005); zero deps runtime novas; hooks fail-open (hooks de plugin do Devin CLI são best-effort) |

## D1 — Caminho de registro por cliente: sempre comando nativo

**Decision**: o assistente registra o servidor exclusivamente pelo comando
nativo de gestão de MCP de cada CLI — `claude mcp add`, `devin mcp add`,
`codex mcp add`, `gemini mcp add`. Nenhuma edição direta de arquivo de
configuração nesta feature (o caso Desktop, sem comando nativo, saiu do
escopo — ver D3).

**Rationale**: comandos nativos são donos do próprio formato de arquivo; se o
cliente mudar o formato, o assistente continua funcionando. Quatro caminhos
idênticos em forma, zero lógica de escrita de arquivo para manter.

**Fontes verificadas**:
- Claude Code: `claude mcp add <name> [--scope user|project|local] -- <command>`
  (README deste projeto, documento da invocação que funciona).
- Devin CLI: `devin mcp add -s user carteira -e WALLET_ID=<id> -- uvx
  mcp-investidor10-wallet` — flags verificadas na versão instalada via
  `devin mcp add --help` em 2026-10-24: `-s/--scope user` grava em
  `~/.config/devin/mcp_config.json` e `-e/--env` injeta variáveis; `devin mcp
  list` lista os servidores (learning lesson
  `docs/learning-lessons/devin_mcp_add_user_scope.md`).
- Codex CLI: `codex mcp add <name> --env VAR=VAL -- <command>` e
  `codex mcp list` — docs oficiais (`learn.chatgpt.com/docs/extend/mcp`,
  buscado em 2026-10-24). Config em `~/.codex/config.toml` sob
  `[mcp_servers.<name>]` (user default; escopo de projeto via
  `.codex/config.toml` em projetos confiáveis). O Codex compartilha essa
  config com os apps desktop da OpenAI — ganho futuro para a spec de
  desktop.
- Gemini CLI: `gemini mcp add -s user -e WALLET_ID=… carteira uvx
  mcp-investidor10-wallet` — docs oficiais (`geminicli.com/docs/tools/mcp-server`,
  "Managing MCP servers with `gemini mcp`", buscado em 2026-10-24). Escopo
  user, alias sem underscores (`geminicli.com/docs/reference/configuration`).

**Alternatives considered**: editar o arquivo de config de algum cliente
diretamente — rejeitado (quatro formatos para manter; quebra silenciosa a
cada atualização de cliente).

## D2 — Um artefato de plugin, dois manifestos finos, no mesmo repositório

**Decision**: mesmo repositório (decisão do mantenedor, FR-009). Os assets de
comportamento vivem em `plugin/` (commands, agents, hooks, skills); dois
manifestos finos na raiz apontam para eles:

- `.claude-plugin/plugin.json` (Claude Code; o manifesto suporta caminhos
  explícitos de componentes, ex.: `"hooks": "./plugin/hooks/hooks.json"`)
- `.devin-plugin/plugin.json` (Devin CLI, que tem precedência quando presente
  e cai para o manifesto Claude caso contrário)

Um `.mcp.json` compartilhado define o servidor `carteira` com o ID da
carteira referenciado do ambiente em vez de valor embutido:

```json
{ "mcpServers": { "carteira": {
    "command": "uvx", "args": ["mcp-investidor10-wallet"],
    "env": { "WALLET_ID": "${WALLET_ID}" } } } }
```

**Canal de instalação no Claude Code (revisado 2026-10-24, aprovado pelo
mantenedor)**: um `.claude-plugin/marketplace.json` vai no mesmo repo
apontando para o plugin; a instalação canônica vira
`claude plugin marketplace add rc-ventura/mcp-investidor10-wallet` +
`/plugin install investidor10-carteira`. Instalação por path local permanece
documentada para desenvolvimento.

**Rationale**: os dois CLIs leem `mcpServers` dos manifestos e referências
`${VAR}` das configs de servidor de plugin (docs do Devin: configs MCP de
plugin devem referenciar segredos como `${NAME}`; o `.mcp.json` do Claude
Code suporta expansão `${VAR}`). Manifestos são adaptadores finos; os assets
são a fonte única de verdade.

**Fontes verificadas**:
- Layout e campos do manifesto do Claude Code: repo oficial
  `anthropics/claude-code`, `plugins/plugin-dev/skills/plugin-structure/SKILL.md`
  + `references/manifest-reference.md` (via Context7, 2026-10-24): manifesto
  em `.claude-plugin/plugin.json`, `mcpServers` inline ou por caminho,
  caminhos custom de componentes permitidos.
- Layout do Devin CLI + ordem de fallback
  (`.devin-plugin/plugin.json` > `.claude-plugin/plugin.json` > `plugin.json`
  da raiz): `docs/extensibility/plugins/overview.mdx` (lido localmente,
  2026-10-24).
- Referência local funcionando: plugin instalado `ralph-loop`
  (`~/.config/devin/plugins/ralph-loop/`) — `hooks.json` na raiz +
  `.devin-plugin/plugin.json`.

**Risco**: o Devin CLI honrar caminhos *custom* de componentes dentro de um
manifesto em formato Claude não está documentado. Mitigação: dois manifestos
explícitos (planejado) em vez de depender do fallback de caminho; verificado
pelo teste de contrato e por um teste manual de carga nos dois clientes
(quickstart V3).

## D3 — Desktop adiado para spec futura dedicada

**Decision (revisada 2026-10-24, aprovada pelo mantenedor)**: Claude Desktop
(app GUI), extensão oficial (`.mcpb`), Devin Desktop e demais apps desktop
ficam **fora desta feature**. Serão tratados numa spec própria com estudo
específico de distribuição: o caminho provável é o mecanismo oficial de
extensões do Desktop (pacote `.mcpb` distribuído como asset de release, com a
UI do app pedindo o `WALLET_ID`), mas o estudo precisa cobrir também o
runtime exigido do usuário, a memória compartilhada (`~/.investidor10`) e a
experiência de subagentes/hooks dentro do app.

**Rationale**: é um público e um formato com exigências próprias (sem
terminal, sem comando nativo de registro, runtime Python, UX de configuração
de extensão) — misturá-lo ao MVP de CLIs atrasaria o valor do P1 e exigiria
decisões de produto que merecem discussão dedicada.

**Alternatives considered**: manter a extensão `.mcpb` como P3 desta feature
(descartado pelo mantenedor — escopo CLIs primeiro); wrapper `.command` de
duplo-clique (descartado em favor do mecanismo oficial, a reavaliar na spec
de desktop).

## D4 — Assets de comportamento do plugin (conjunto v1)

**Decision**: entregar exatamente:

1. `commands/` — três prompts: `analise-da-carteira`, `check-de-tese`,
   `resumo-de-dividendos`.
2. `agents/guardiao-de-disciplina.md` — confronta uma decisão de investimento
   com as regras salvas na memória (`get_rules`, `get_theses`) e reporta
   violações; nunca escreve.
3. `hooks/` — hook `Stop`: inspeciona o transcript da sessão e, quando
   decisões foram discutidas sem registro, injeta um lembrete para o agente
   **propor** `log_decision`/`log_insight` e aguardar confirmação do usuário
   (FR-010 — hook nunca grava sozinho; hooks são fail-open conforme docs do
   Devin, então a ausência degrada para "sem lembrete").

**Rationale**: mínimo, com valor e testabilidade independentes; a proteção de
escrita na memória segue o ADR-0002 (a memória é do usuário).

## D5 — Escopo de instalação para as CLIs

**Decision**: escopo user em todas (`claude mcp add --scope user`,
`devin mcp add -s user`, `gemini mcp add -s user`; o Codex grava por padrão
em `~/.codex/config.toml`, que é user-level). Registro em escopo de projeto
permanece opção manual documentada.

**Rationale**: a carteira é pessoal e por máquina (a memória em
`~/.investidor10` já é global por usuário — ADR-0010); o escopo user casa com
essa fronteira.

## Verificações abertas (fase de implementação)

- Testar a carga do plugin nos dois clientes e confirmar ativação dos hooks
  (hooks do Devin são fail-open por design).
- Confirmar que a expansão `${WALLET_ID}` no `.mcp.json` compartilhado
  resolve nos dois clientes quando a variável existe e falha visivelmente
  (não silenciosamente) quando ausente.