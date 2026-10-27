# Pesquisa: extensões no Gemini CLI (24/10/2026)

Fonte primária: documentação oficial do Gemini CLI
(`geminicli.com/docs/extensions/` e `geminicli.com/docs/extensions/reference/`,
buscadas em 2026-10-24).

## Conceito

O Gemini CLI tem **extensões** — pacotes que distribuem prompts, MCP
servers, custom commands, temas, hooks, sub-agents e agent skills num
formato instalável: `gemini extensions install <github-url|path>` (copia o
diretório para `~/.gemini/extensions`; `update` puxa mudanças; `link`
aponta para diretório local em desenvolvimento; `new` cria a partir de
template). Extensões habilitadas globalmente por padrão; `disable/enable`
por escopo user/workspace.

## Manifesto `gemini-extension.json` (raiz da extensão)

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "description": "Minha extensão",
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${extensionPath}/my-server.js"],
      "cwd": "${extensionPath}"
    }
  },
  "settings": [
    { "name": "API Key", "description": "...", "envVar": "MY_API_KEY", "sensitive": true }
  ]
}
```

Pontos relevantes:

- `mcpServers` no manifesto carrega como os de `settings.json` (settings do
  usuário têm precedência em colisão de nome); `${extensionPath}` para
  portabilidade; **tudo suportado exceto `trust`**.
- `settings[]` declara variáveis de ambiente que a extensão precisa — por
  segurança, extensões **não herdam o ambiente do shell**; só variáveis
  declaradas (e o mínimo seguro: HOME, PATH, TMPDIR) são passadas.
- `contextFileName` (default `GEMINI.md`) injeta contexto da extensão.

## Componentes (por convenção de diretórios, não campos do manifesto)

| Componente | Formato |
|---|---|
| Custom commands | `commands/*.toml` (campo `prompt` obrigatório, `description` opcional); nome deriva do caminho (`commands/gcs/sync.toml` → `/gcs:sync`) |
| Hooks | `hooks/hooks.json` (não declarado no manifesto) |
| Agent skills | `skills/<nome>/SKILL.md` |
| Sub-agents | `agents/*.md` — **feature em preview** |
| Políticas | `policies/*.toml` (tier 2 do Policy Engine; `allow`/yolo de extensão são ignorados por segurança) |

## Commands: primitivo ativo no Gemini (verificado 2026-10-26)

Ao contrário do Claude Code — onde commands foram **fundidos nas skills**
(v2.1.3) e a skill já é o command do usuário — no Gemini os dois papéis são
separados: `skills/` são invocadas pelo **agente** (agent skills) e
`commands/*.toml` são o primitivo de invocação pelo **usuário** (`/deploy`).
Por isso o nosso plugin envia commands TOML **apenas** para o Gemini:
espelham as 3 skills para dar ao usuário a invocação manual que nos outros
clientes as skills já entregam.

## Compatibilidade com Claude/Devin

- **Não há compatibilidade de formato direta**: o manifesto e os formatos
  internos são próprios (TOML para commands, JSON próprio para hooks).
- A interseção real é conceitual: skills (`SKILL.md` com frontmatter
  `name`/`description`) seguem o mesmo formato de skill dos demais; o MCP
  continua sendo o canal universal — `gemini mcp add` registra o mesmo
  servidor `carteira` sem extensão nenhuma.

## Conclusões para o produto

- Nenhuma mudança na spec 003: o Gemini continua atendido pelo assistente de
  instalação (`gemini mcp add -s user`), que já funciona.
- Se um dia o plugin de comportamento for estendido ao Gemini, o custo é um
  manifesto `gemini-extension.json` próprio + converter os 3 prompts para
  `commands/*.toml` e o hook para o formato de hooks do Gemini — candidato a
  spec futura, junto com a mesma pergunta para o Codex.