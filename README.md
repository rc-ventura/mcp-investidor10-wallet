# mcp-investidor10-wallet

Assistente de investimentos que conecta um agente (Claude Desktop, Claude
Code, Devin CLI, Codex, Gemini CLI) a uma carteira pública ou restrita do
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

As 20 tools estão implementadas (6 de dados da carteira/mercado, 13 de
memória/alertas e 1 de configuração) — contratos completos em
[specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/specs/001-mcp-investidor10-wallet/contracts/mcp-tools.md).

## Instalação no Claude Desktop

Para quem não usa terminal no dia a dia. Você abre o terminal **uma única vez**,
para instalar o `uv`; o resto é feito dentro do Claude Desktop. Detalhes e o que
fazer se algo não funcionar: [docs/INSTALACAO-DESKTOP.md](docs/INSTALACAO-DESKTOP.md).

**Requisitos**

- Conta paga do Claude (plano pago) com o Claude Desktop instalado.
- O [`uv`](https://docs.astral.sh/uv/), um programa gratuito que baixa e executa o
  servidor. O Claude Desktop não o traz.
- Não existe Claude Desktop para Linux; no Linux use um dos CLIs (seção seguinte).

**Passo a passo**

1. **Instale o `uv`** no terminal (Mac: `Cmd + Espaço`, digite `Terminal`; Windows:
   PowerShell) e reinicie o Claude Desktop depois:

   ```bash
   # Mac ou Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   ```powershell
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Adicione o marketplace.** Em Customize > Plugins, escolha adicionar o
   marketplace e cole o endereço:

   ```text
   rc-ventura/mcp-investidor10-wallet
   ```

3. **Instale o plugin** `investidor10-carteira`. Ele já traz o servidor da carteira,
   a memória do investidor, as skills, o guardião de disciplina e a persona.
4. **Abra uma conversa nova** e peça, por exemplo, "Configure minha carteira". O
   assistente abre uma página local no seu navegador (endereço `127.0.0.1`, que só
   existe no seu computador, com um código de uso único que vence em 10 minutos).
5. **Configure na página.** Cole o link da carteira, escolha se quer esconder os
   valores em reais do modelo e salve (veja abaixo qual link usar). Cole o link
   **só na página, nunca na conversa**: o que vai para a conversa fica no histórico.
6. **Pergunte** o que quiser sobre a carteira, como "faça um resumo da minha carteira".

**Atualizar:** em Customize > Plugins, atualize o marketplace e reinstale o plugin. A
memória e a configuração ficam intactas (estão em `~/.investidor10/`).

**Desinstalar:** remova o plugin em Customize > Plugins. Seus dados continuam em
`~/.investidor10/`; apague essa pasta se quiser apagá-los também.

**Limitações**

- As tools só carregam numa sessão **Cowork** no computador. Numa conversa **Chat**
  comum o assistente não tem acesso à carteira nem à memória e deve dizer isso, sem
  inventar valores.
- Um plugin adicionado na sua conta é sincronizado para o Claude Code. Nesse caso o
  assistente de instalação dos CLIs não instala uma cópia local, para não duplicar
  o servidor.
- **Se você já tinha uma entrada manual** do servidor `carteira` em
  `claude_desktop_config.json` (`~/Library/Application Support/Claude/` no Mac), remova
  essa entrada: o plugin já traz o servidor, e as duas juntas duplicam as tools.
- Privacidade: leia [docs/PRIVACY.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md).

## Instalação nos CLIs de agente (assistente)

Pré-requisito: [uv](https://docs.astral.sh/uv/) (que traz Python 3.11+).

Um comando configura a carteira e instala o **produto completo** nos CLIs de agente
presentes na máquina (Claude Code, Devin CLI, Codex, Gemini CLI):

```bash
uvx mcp-investidor10-wallet install
```

O assistente pergunta o link da carteira (ver abaixo), confere com a fonte, avisa
quando a carteira é pública e indexável, pergunta se você quer o modo privacidade e
grava tudo em `~/.investidor10/config.json`. Depois instala em cada cliente, com
relatório em PT-BR:

- **Claude Code**: instala o **plugin**, que já traz o servidor (sem `claude mcp add`).
  Se achar o registro antigo do servidor, o marketplace da 0.3.x ou uma cópia local do
  plugin, pergunta uma vez se deve remover, para não duplicar as tools.
- **Devin CLI, Codex e Gemini CLI**: registra o servidor **e** instala o plugin de
  comportamento.

O servidor fica na versão exata do assistente (`uvx mcp-investidor10-wallet@<versão>`),
e não na mais recente do PyPI a cada abertura. Para atualizar, rode
`uvx mcp-investidor10-wallet@latest install` de novo.

Opções:

| Flag | Efeito |
|---|---|
| `--link <link>` | Informa o link da carteira sem pergunta (scripts/CI) |
| `--wallet-id <id>` | Forma antiga de `--link` para a carteira pública |
| `--mask` / `--no-mask` | Liga ou desliga o modo privacidade sem perguntar |
| `--mcp-only` | Registra apenas o servidor MCP (sem o plugin) — modo técnico; no Claude Code avisa se o plugin já existir |
| `--dry-run` | Simula e relata o que faria, sem alterar nada |
| `--clients claude,devin,codex,gemini` | Restringe os clientes alvo |
| `--yes` | Pula confirmações de rotina |

Outros subcomandos:

- `uvx mcp-investidor10-wallet configure`: refaz o link e o modo privacidade, sem
  registrar nem instalar nada.
- `uvx mcp-investidor10-wallet doctor`: confere a instalação e imprime um resumo, com
  causa e ação para cada problema, sem ID, credencial, valores nem o nome do seu
  usuário, pronto para colar numa issue.

### O plugin de comportamento

O plugin inclui:

- **4 skills** (`/analise-da-carteira`, `/check-de-tese`,
  `/resumo-de-dividendos` e `/configurar-carteira`) — roteiros com as regras do
  produto embutidas (bootstrap da memória, atraso de ~15 min das cotações,
  rendimento recorrente e nunca DY médio; a última conduz a configuração da
  carteira);
- **guardião de disciplina** — subagente read-only que confronta decisões de
  investimento com as regras e teses que você salvou na memória;
- **persona** — instruções de papel injetadas no início de cada sessão;
- **lembrete de memória** — ao fim da sessão, propõe registrar decisões
  discutidas (sempre com sua confirmação; nunca grava sozinho).

Instalação manual do plugin (sem o assistente):

```bash
# Claude Code (o plugin já traz o servidor)
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

### Qual link da carteira usar

Copie o link no site do Investidor10 (compartilhar a carteira):

- **Carteira pública**: `https://investidor10.com.br/wallet/public/<número>`. Qualquer
  pessoa com o link lê a carteira e ela pode ser indexada por buscadores.
- **Carteira restrita** (recomendada): o link de compartilhamento completo, que termina
  em `?h=...`. O trecho `?h=...` funciona como senha e fica só no arquivo local
  `~/.investidor10/config.json` (permissão 0600), nunca em log nem em mensagem de erro.

Ative a opção correspondente nas configurações da carteira no site. O botão de
mascarar valores do site é apenas cosmético (a API continua retornando tudo); para
esconder valores do modelo use o modo privacidade do produto.

## Configuração manual (sem o assistente)

O servidor lê a carteira de `~/.investidor10/config.json`, que o assistente e o
comando `configure` gravam; não é preciso passar variável de ambiente ao cliente. O
cliente inicia o servidor como processo filho, então o comando precisa existir no
ambiente dele. Registre o servidor (troque `<versão>` pela versão instalada) e depois
configure a carteira:

**Claude Code** (alternativa ao plugin):

```bash
claude mcp add carteira --scope user -- uvx mcp-investidor10-wallet@<versão>
```

**Devin CLI**:

```bash
devin mcp add -s user carteira -- uvx mcp-investidor10-wallet@<versão>
```

**Codex CLI**:

```bash
codex mcp add carteira -- uvx mcp-investidor10-wallet@<versão>
```

**Gemini CLI**:

```bash
gemini mcp add -s user carteira uvx mcp-investidor10-wallet@<versão>
```

```bash
uvx mcp-investidor10-wallet configure
```

Se o servidor ficar registrado **e** o plugin do Claude Code estiver instalado, as
tools aparecem em dobro: mantenha só um dos dois.

O cliente reinicia o servidor a cada sessão; depois de uma atualização, reinicie a
sessão para carregar tools novas. A variável `WALLET_ID` continua aceita como forma
antiga (veja a tabela de variáveis), mas o arquivo local tem precedência.

## Solução de problemas

Rode primeiro `uvx mcp-investidor10-wallet doctor`: ele aponta causa e ação e imprime
um resumo sem dados sensíveis para colar numa issue.

| Sintoma | Causa provável | Correção |
|---|---|---|
| O servidor `carteira` não conecta no Claude Desktop | O `uv` não está instalado ou o app não o encontra | Instale o `uv` (passo 1 do Desktop), feche o Claude Desktop por completo e abra de novo |
| `wallet_not_configured` | Nenhuma carteira configurada | Peça ao assistente "configure minha carteira" ou rode `uvx mcp-investidor10-wallet configure` |
| `access_denied` | O link restrito foi renovado ou a carteira virou privada | Gere o link de compartilhamento atual no site e configure de novo |
| O navegador não abre na configuração | Ambiente sem navegador padrão | Copie o endereço que o assistente mostrar, ou use `configure` no terminal |
| As tools da carteira aparecem em dobro (40) | Servidor registrado e plugin instalados juntos | Remova um: `claude mcp remove carteira -s user` |
| `Não foi possível validar a carteira ... (fonte indisponível)` | API fora do ar ou sem rede | Aviso não-bloqueante: o servidor sobe e as tools de dados informarão o erro |
| `Não foi possível preparar o diretório de memória ...` | Permissões de `~/.investidor10/` | Corrija as permissões do diretório indicado e reinicie |

## Onde ficam os dados

- **Configuração da carteira**: `~/.investidor10/config.json` (arquivo 0600, com o ID
  da carteira, a credencial do link restrito e o modo privacidade). Todos os clientes
  da máquina leem o mesmo arquivo, e uma mudança vale na chamada seguinte, sem
  reiniciar.
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
| `WALLET_ID` | Não | — | Forma antiga: ID da carteira pública. O arquivo de configuração local tem precedência; sem nenhum dos dois, o servidor sobe e as tools de carteira devolvem `wallet_not_configured` |
| `WALLET_MEMORY_PATH` | Não | `~/.investidor10/memory.json` | Caminho da memória (use um disco local) |
| `WALLET_MASK_VALUES` | Não | desligado | `1`/`true`/`yes`/`on` ligam o modo privacidade: valores em R$ e quantidades não chegam ao modelo (ver [PRIVACY.md](https://github.com/rc-ventura/mcp-investidor10-wallet/blob/main/docs/PRIVACY.md)) |
| `WALLET_CACHE_TTL_SECONDS` | Não | `600` | TTL do cache em memória |
| `WALLET_CACHE_MAX_STALE_SECONDS` | Não | `86400` | Idade máxima de cache expirado servido em queda da fonte (24h); mais antigo vira erro explícito |

## Tools (20)

- **Dados da carteira/mercado (6)**: `get_wallet_summary`,
  `get_wallet_allocation`, `get_wallet_positions`, `get_patrimony_history`,
  `get_earnings`, `get_asset_quote`
- **Configuração (1)**: `open_wallet_setup` (abre a página local onde o usuário
  cola o link da carteira, sem passar pela conversa)
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