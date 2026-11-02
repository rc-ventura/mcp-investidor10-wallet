# Contract — plugin completo e servidor empacotado

Cobre FR-001, FR-003, FR-006, FR-009 a FR-009d, FR-026, FR-030, FR-031.

## Layout do plugin

```text
plugin/
├── .claude-plugin/plugin.json      # version = pacote; mcpServers -> ./servers/carteira.mcpb
├── .codex-plugin/plugin.json       # só a versão muda
├── .devin-plugin/plugin.json       # só a versão muda
├── gemini-extension.json           # só a versão muda
├── servers/carteira.mcpb           # novo: servidor empacotado (tipo uv), gerado e commitado
├── agents/guardiao-de-disciplina.md
├── commands/*.toml                 # só Gemini, sem mudança
├── hooks/
│   ├── hooks.json                  # SessionStart lê o JSON estático; Stop segue em Bash
│   ├── session-start.json          # novo: persona em ASCII com escapes \u
│   └── stop-memory-reminder.sh
└── skills/
    ├── analise-da-carteira/
    ├── check-de-tese/
    ├── resumo-de-dividendos/
    └── configurar-carteira/        # nova
```

Proibido: diretório `bin/` no topo do plugin (Chat e Cowork recusam o
plugin inteiro).

## `plugin/.claude-plugin/plugin.json`

```json
{
  "name": "investidor10-carteira",
  "displayName": "Carteira Investidor10",
  "version": "<versão do pacote>",
  "description": "Assistente da sua carteira do Investidor10: tools da carteira, memória do investidor, skills, guardião de disciplina e persona",
  "license": "MIT",
  "mcpServers": "./servers/carteira.mcpb"
}
```

O nome `investidor10-carteira` não muda (identidade permanente do plugin).
O servidor aparece no Claude Code como `plugin:investidor10-carteira:carteira`.

## `hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "*", "hooks": [{"type": "command",
      "command": "cat \"${CLAUDE_PLUGIN_ROOT}/hooks/session-start.json\""}]}],
    "Stop": [{"matcher": "*", "hooks": [{"type": "command",
      "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-memory-reminder.sh\""}]}]
  }
}
```

`session-start.json` contém `hookSpecificOutput.additionalContext` com a
persona atual mais a regra: "se `get_session_context` indicar configuração
pendente, conduza a configuração (skill configurar-carteira) antes de
qualquer análise". Só ASCII no arquivo.

## Skill `configurar-carteira`

`description` voltada às situações do usuário: primeira conversa, "configure
minha carteira", "troque o link", "esconda os valores", ou qualquer erro
`wallet_not_configured`/`access_denied`. Corpo:

1. Explicar onde copiar o link no site e que a carteira restrita é a mais
   privada.
2. Chamar `open_wallet_setup`. Se a resposta trouxer o endereço, mostrá-lo ao
   usuário e citar `mcp-investidor10-wallet configure` como alternativa.
3. Pedir para colar o link **na página**, nunca na conversa. Se o usuário colar
   na conversa, não reutilizar o valor e avisar que ele ficou no histórico.
4. Quando o usuário disser que salvou, conferir em `get_session_context` o
   bloco `configuration`, mostrar modo e mascaramento e seguir para a pergunta
   original.

A skill não inventa valores quando as tools não estão disponíveis (conversa
Chat): diz que as tools só carregam numa sessão Cowork no computador
(FR-009a).

## Servidor empacotado (`servers/carteira.mcpb`)

Conteúdo e invariantes em data-model.md §6. Gerado por
`scripts/build_mcpb.py` (stdlib, zip determinístico), só no PR de release; o
pacote aponta para a versão publicada no PyPI e não leva o código. Validado na
release com o CLI oficial `@anthropic-ai/mcpb@2.1.2` (`mcpb validate`), só como
ferramenta de build.

## Marketplace

`.claude-plugin/marketplace.json` na raiz mantém nome `investidor10` e o
plugin `investidor10-carteira` com `source: "./plugin"` (conteúdo no mesmo
repositório, exigido para o Desktop sincronizar). A descrição passa a citar
o produto completo.

Endereço para o usuário colar em Customize > Plugins > Add marketplace:
`rc-ventura/mcp-investidor10-wallet`. No Claude Code o assistente usa
`#v<versão>`.

O marketplace entrega o conteúdo da branch padrão (`main`), que só recebe
versões já publicadas no índice (fluxo de branches e release). Que o Desktop
leia a branch padrão ao adicionar o marketplace é verificado no spike.

## Verificações automatizadas (a cada build)

- versão do pacote = `plugin.json` dos quatro manifestos = manifesto MCPB;
- no PR para a branch padrão, `plugin/` só muda junto com a versão;
- a lista `tools` do guardião usa a forma de nome confirmada no spike;
- `session-start.json` é JSON válido e só ASCII;
- `claude plugin validate ./plugin` passa (quando o CLI estiver na CI);
- nenhum `bin/` no topo do plugin;
- guarda de ID e credencial também sobre o conteúdo do MCPB.

Só na release (`--check`): tools do manifesto MCPB = tools listadas pelo
servidor; MCPB commitado = MCPB gerado.
