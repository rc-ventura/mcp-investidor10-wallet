# Changelog

Todas as mudanças notáveis do `mcp-investidor10-wallet` são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota [versionamento semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x: mudanças de comportamento (features) incrementam o
minor; correções incrementam o patch.

## [0.2.0] - 2026-10-26

Assistente de instalação e plugin de comportamento — o produto passa a ser o
bundle (MCP + plugin) distribuído por um único comando.

### Adicionado

- **Assistente de instalação** (`mcp-investidor10-wallet install`): detecta
  os CLIs de agente presentes (Claude Code, Devin CLI, Codex, Gemini CLI),
  valida o `WALLET_ID` e registra o servidor `carteira` via comando nativo
  de cada cliente (escopo user), com protocolo interativo de colisão de
  alias, idempotência, `--dry-run` e relatório em PT-BR.
- **Bundle por padrão**: o assistente instala o plugin de comportamento após
  o registro (`--mcp-only` registra apenas o servidor — modo técnico).
- **Plugin de comportamento** (`plugin/`, instalável nos 4 clientes):
  - 3 skills (`/analise-da-carteira`, `/check-de-tese`,
    `/resumo-de-dividendos`) com as regras do produto embutidas;
  - subagente `guardiao-de-disciplina` (read-only, confronta decisões com
    regras/teses salvas);
  - persona do assistente via hook `SessionStart` (`additionalContext`);
  - lembrete de memória via hook `Stop` (propõe `log_decision`/
    `log_insight` com confirmação; fail-open);
  - manifestos finos por cliente (`.claude-plugin`, `.devin-plugin`,
    `.codex-plugin`, `gemini-extension.json`) + `commands/*.toml` para o
    Gemini + marketplace do Claude Code.
- Pesquisa de formato de plugins dos 4 clientes em `docs/research/plugins-*`.

### Alterado

- Configuração manual do Devin CLI documentada com as flags verificadas
  (`devin mcp add -s user carteira -e WALLET_ID=…`) — learning lesson nova.
- README reestruturado: instalação automática como caminho principal,
  configuração manual rebaixada, links relativos corrigidos para URLs
  absolutas (quebravam na página do PyPI).

## [0.1.0] - 2026-10-18

Primeira release pública — prontidão para distribuição (Fase 0 do ROADMAP).

### Adicionado

- Empacotamento no PyPI: pacote `mcp-investidor10-wallet` com console script
  de mesmo nome; instalação/execução em uma linha via `uvx`.
- Validação da carteira no início de cada execução: carteira inexistente ou
  privada aborta com instrução em PT-BR; fonte indisponível apenas avisa e o
  servidor continua.
- Migração automática da memória legada (`./memory.json`) para o local
  canônico `~/.investidor10/memory.json`, com backup identificável em caso de
  conflito e mensagens de operador em PT-BR.
- Onboarding em PT-BR no README: obtenção do `WALLET_ID`, exigência de
  carteira pública, configuração por cliente (Claude Desktop, Claude Code,
  Devin) e tabela de troubleshooting.
- Gates de qualidade: pre-commit (ruff lint + format), CI em matriz de
  Python 3.11/3.12/3.13 × Ubuntu/macOS e workflow de release com smoke test
  do artefato e verificação de changelog.

### Alterado

- `WALLET_ID` deixou de ter valor padrão — o servidor agora exige a variável
  de ambiente e aborta com instrução clara quando ausente (antes usava
  silenciosamente a carteira do autor como default).
- Caminho padrão da memória mudou de `./memory.json` (relativo ao diretório
  de trabalho) para `~/.investidor10/memory.json`; `WALLET_MEMORY_PATH`
  continua como override com precedência total.
- Código reestruturado para layout de pacote (`src/investidor10_wallet/`),
  com entrada única de execução `investidor10_wallet.server:main`.

### Interno

- Formatação do código existente e dos blocos Python em Markdown (`docs/learning-lessons/`) padronizada com ruff (lint + format).