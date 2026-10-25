# mcp-investidor10-wallet

Servidor MCP que conecta um agente (Claude Desktop, Claude Code, Devin) a uma
carteira pública do [Investidor10](https://investidor10.com.br), com memória
de longo prazo do investidor (teses, regras, decisões, insights) e alertas de
preço.

Sem frontend — a interface é o cliente do agente. O servidor roda sobre stdio
(o cliente inicia o processo; nenhuma porta é exposta).

> **Aviso**: a fonte de dados é a API interna, não documentada, do
> Investidor10. Ela é pública e sem autenticação hoje, mas pode mudar ou ser
> desligada sem aviso. Falhas aparecem como erros estruturados explícitos —
> nunca como valores inventados.

## Status

Roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md).

As 19 tools estão implementadas (6 de dados da carteira/mercado + 13 de
memória/alertas) — contratos completos em
[`specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md`](specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md).

## Instalação e execução (1 linha)

Pré-requisito: [uv](https://docs.astral.sh/uv/) (que traz Python 3.11+).

```bash
WALLET_ID=SEU_ID uvx mcp-investidor10-wallet
```

Sem clonar repositório: o `uvx` baixa o pacote do PyPI e executa o servidor
em stdio.

### Onde encontrar o seu `WALLET_ID`

Abra sua carteira no Investidor10 e copie o número da URL pública:

```
https://investidor10.com.br/carteira/SEU_ID
```

**A carteira precisa ser pública** — nas configurações do Investidor10, ative
"carteira pública". O ID é o único identificador que o servidor usa; quem
tiver o ID consegue ler os valores da carteira (o botão de mascarar do site
é apenas cosmético — a API continua retornando tudo).

## Configuração nos clientes

O cliente do agente inicia o servidor como processo filho; por isso o
comando configurado precisa existir no ambiente do cliente.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`) —
apps GUI no macOS **não herdam o PATH do shell**: use o caminho absoluto do
`uv` (descubra com `which uv`):

```json
{
  "mcpServers": {
    "carteira": {
      "command": "/Users/<seu-usuario>/.local/bin/uv",
      "args": ["tool", "run", "mcp-investidor10-wallet"],
      "env": { "WALLET_ID": "SEU_ID" }
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add carteira -- env WALLET_ID=SEU_ID uvx mcp-investidor10-wallet
```

**Devin CLI**:

```bash
devin mcp add -s user carteira -e WALLET_ID=SEU_ID -- uvx mcp-investidor10-wallet
```

O cliente reinicia o servidor a cada sessão; depois de uma atualização,
reinicie a sessão para carregar tools novas.

## Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| "MCP failed to connect" (Claude Desktop) | PATH do shell não existe no app GUI | Use o caminho absoluto do `uv` (veja acima; `which uv` para descobrir) |
| `WALLET_ID não configurado` + saída | `WALLET_ID` ausente na config do cliente | Adicione `WALLET_ID` no bloco `env` do servidor |
| `Carteira ... não encontrada ou não é pública` | ID errado ou carteira privada | Confira o ID na URL pública e deixe a carteira pública nas configurações do site |
| `Não foi possível validar a carteira ... (fonte indisponível)` | API fora do ar ou sem rede | Aviso não-bloqueante: o servidor sobe e as tools de dados informarão o erro |
| `Não foi possível migrar a memória ...` | Permissões de `~/.investidor10/` | Corrija as permissões do diretório indicado e reinicie |

## Onde ficam os dados

- **Memória**: `~/.investidor10/memory.json` — arquivo local versionado com
  escrita atômica, compartilhado por todos os clientes da máquina. A
  instalação anterior (memória no diretório de trabalho) é migrada
  automaticamente na primeira execução, com aviso no stderr.
- **Cache de API**: apenas em memória de processo (TTL configurável).
- **Nada é enviado a outro lugar pelo servidor** — os resultados das tools
  entram no contexto do seu provedor de LLM (o agente), como qualquer tool.

## Configuração (variáveis de ambiente)

| Variável | Obrigatória | Default | Uso |
|---|---|---|---|
| `WALLET_ID` | Sim | — | ID público da carteira (o servidor aborta sem ela) |
| `WALLET_MEMORY_PATH` | Não | `~/.investidor10/memory.json` | Caminho da memória (override sem migração) |
| `WALLET_CACHE_TTL_SECONDS` | Não | `600` | TTL do cache em memória |
| `WALLET_CACHE_MAX_STALE_SECONDS` | Não | `86400` | Idade máxima de cache expirado servido em queda da fonte (24h); mais antigo vira erro explícito |

## Tools (19)

- **Dados da carteira/mercado (6)**: `get_wallet_summary`,
  `get_wallet_allocation`, `get_wallet_positions`, `get_patrimony_history`,
  `get_earnings`, `get_asset_quote`
- **Memória e alertas (13)**: `get_session_context` (bootstrap da sessão —
  chame no início de toda sessão), `get_wallet_goal`, `set_wallet_goal`,
  `save_thesis`, `get_theses`, `save_rule`, `get_rules`, `log_decision`,
  `record_decision_outcome`, `log_insight`, `create_price_alert`,
  `list_price_alerts`, `cancel_price_alert`

## Testes

```bash
uv run pytest          # unit + contrato (API mockada com respx)
uv run pytest -m live  # integração opt-in contra a API real
```

## Limitações e riscos

- **API interna não documentada**: endpoints públicos mas sem contrato; podem
  mudar ou passar a exigir autenticação sem aviso.
- **Cobertura de cotação**: `get_asset_quote` só cobre ações B3; FIIs, ETFs
  internacionais, cripto e tesouro retornam `asset_type_not_supported` (ver
  [learning lesson](docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md)).
  Ativos dessas classes na carteira aparecem via `get_wallet_positions`.
- **Detalhe de proventos**: `get_earnings` retorna o total do período; a
  tabela por pagamento existe no upstream e é candidata a uma tool futura
  (ver [learning lesson](docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md)).
- **Cotações com atraso** (~15 min na B3) — o agente deve sempre mencionar.
- **Uso pessoal/educacional**: o agente sugere, nunca executa ordens.