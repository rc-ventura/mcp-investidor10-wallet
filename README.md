# mcp-investidor10-wallet

Assistente de investimentos que conecta um agente (Claude Code, Devin CLI,
Codex, Gemini CLI) a uma carteira pública do
[Investidor10](https://investidor10.com.br), com memória de longo prazo do
investidor (teses, regras, decisões, insights), alertas de preço e um
**plugin de comportamento** (skills, guardião de disciplina, persona e
lembrete de memória).

Sem frontend — a interface é o cliente do agente. O servidor roda sobre stdio
(o cliente inicia o processo; nenhuma porta é exposta).

> **Aviso**: a fonte de dados é a API interna, não documentada, do
> Investidor10. Ela é pública e sem autenticação hoje, mas pode mudar ou ser
> desligada sem aviso. Falhas aparecem como erros estruturados explícitos —
> nunca como valores inventados.

> **Privacidade**: leia [docs/PRIVACY.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md) antes de instalar. Ele
> explica o que vai para onde, por que o ID da carteira deve ser tratado como
> senha e como o modo privacidade (`WALLET_MASK_VALUES`) evita que valores em
> reais cheguem ao modelo.

## Status

Roadmap: [docs/ROADMAP.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/ROADMAP.md).

As 19 tools estão implementadas (6 de dados da carteira/mercado + 13 de
memória/alertas) — contratos completos em
[specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md).

## Instalação automática (recomendada)

Pré-requisito: [uv](https://docs.astral.sh/uv/) (que traz Python 3.11+).

Um comando instala o **produto completo** — registra o servidor MCP **e**
instala o plugin de comportamento nos CLIs de agente presentes na máquina
(Claude Code, Devin CLI, Codex, Gemini CLI):

```bash
uvx mcp-investidor10-wallet install
```

O assistente pergunta apenas o ID da carteira (ver abaixo), valida que ela é
pública e cuida do resto, com relatório em PT-BR.

O servidor fica registrado na versão exata do assistente
(`uvx mcp-investidor10-wallet@<versão>`), e não na mais recente do PyPI a cada
abertura. Para atualizar, rode `uvx mcp-investidor10-wallet@latest install` de
novo.

Opções:

| Flag | Efeito |
|---|---|
| `--mcp-only` | Registra apenas o servidor MCP (sem o plugin) — modo técnico |
| `--dry-run` | Simula e relata o que faria, sem alterar nada |
| `--clients claude,devin,codex,gemini` | Restringe os clientes alvo |
| `--wallet-id <id>` | Informa o ID sem pergunta (scripts/CI) |
| `--yes` | Pula confirmações de rotina |

### O plugin de comportamento

O bundle inclui, além do servidor:

- **3 skills** (`/analise-da-carteira`, `/check-de-tese`,
  `/resumo-de-dividendos`) — roteiros com as regras do produto embutidas
  (bootstrap da memória, atraso de ~15 min das cotações, rendimento
  recorrente e nunca DY médio);
- **guardião de disciplina** — subagente read-only que confronta decisões de
  investimento com as regras e teses que você salvou na memória;
- **persona** — instruções de papel injetadas no início de cada sessão;
- **lembrete de memória** — ao fim da sessão, propõe registrar decisões
  discutidas (sempre com sua confirmação; nunca grava sozinho).

Instalação manual do plugin (sem o assistente):

```bash
# Claude Code
claude plugin marketplace add rc-ventura/mcp-investidor10-wallet
claude plugin install investidor10-carteira@investidor10

# Devin CLI
devin plugins install rc-ventura/mcp-investidor10-wallet#plugin -y

# Codex CLI
codex plugin marketplace add rc-ventura/mcp-investidor10-wallet
codex plugin add investidor10-carteira@investidor10

# Gemini CLI
gemini extensions install https://github.com/rc-ventura/mcp-investidor10-wallet
```

### Onde encontrar o seu `WALLET_ID`

Abra sua carteira no Investidor10 e copie o número da URL pública:

```
https://investidor10.com.br/carteira/SEU_ID
```

**A carteira precisa ser pública** — nas configurações do Investidor10, ative
"carteira pública". O ID é o único identificador que o servidor usa; quem
tiver o ID consegue ler os valores da carteira (o botão de mascarar do site
é apenas cosmético — a API continua retornando tudo).

## Configuração manual (sem o assistente)

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
claude mcp add carteira --scope user -- env WALLET_ID=SEU_ID uvx mcp-investidor10-wallet
```

**Devin CLI**:

```bash
devin mcp add -s user carteira -e WALLET_ID=SEU_ID -- uvx mcp-investidor10-wallet
```

**Codex CLI**:

```bash
codex mcp add carteira --env WALLET_ID=SEU_ID -- uvx mcp-investidor10-wallet
```

**Gemini CLI**:

```bash
gemini mcp add -s user -e WALLET_ID=SEU_ID carteira uvx mcp-investidor10-wallet
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
| `Não foi possível preparar o diretório de memória ...` | Permissões de `~/.investidor10/` | Corrija as permissões do diretório indicado e reinicie |

## Onde ficam os dados

- **Memória**: `~/.investidor10/memory.json` — arquivo local versionado com
  escrita atômica, compartilhado por todos os clientes da máquina. Vários
  clientes abertos ao mesmo tempo não perdem gravações: o servidor controla o
  acesso ao arquivo (`memory.json.lock`) e mantém um histórico de cada mudança
  (`memory.json.log`). Para quem tinha a memória no diretório do repositório:
  mova o arquivo com `mv ./memory.json ~/.investidor10/memory.json` ou defina
  `WALLET_MEMORY_PATH`.
- **Pasta sincronizada (Dropbox, iCloud, OneDrive)**: segura na mesma máquina;
  usar a mesma memória em duas máquinas ao mesmo tempo não é protegido (a
  sincronização pode gerar uma cópia em conflito). Use uma máquina por vez.
- **Cache de API**: apenas em memória de processo (TTL configurável).
- **Nada é enviado a outro lugar pelo servidor** — os resultados das tools
  entram no contexto do seu provedor de LLM (o agente), como qualquer tool.

## Configuração (variáveis de ambiente)

| Variável | Obrigatória | Default | Uso |
|---|---|---|---|
| `WALLET_ID` | Sim | — | ID público da carteira (o servidor aborta sem ela) |
| `WALLET_MEMORY_PATH` | Não | `~/.investidor10/memory.json` | Caminho da memória (use um disco local) |
| `WALLET_MASK_VALUES` | Não | desligado | `1`/`true`/`yes`/`on` ligam o modo privacidade: valores em R$ e quantidades não chegam ao modelo (ver [PRIVACY.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md)) |
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
  [learning lesson](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/learning-lessons/get_asset_quote_apenas_acoes_b3.md)).
  Ativos dessas classes na carteira aparecem via `get_wallet_positions`.
- **Detalhe de proventos**: `get_earnings` retorna o total do período; a
  tabela por pagamento existe no upstream e é candidata a uma tool futura
  (ver [learning lesson](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/learning-lessons/earnings_list_detalhe_proventos_por_ativo.md)).
- **Cotações com atraso** (~15 min na B3) — o agente deve sempre mencionar.
- **Uso pessoal/educacional**: o agente sugere, nunca executa ordens.