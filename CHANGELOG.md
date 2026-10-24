# Changelog

Todas as mudanças notáveis do `mcp-investidor10-wallet` são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota [versionamento semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x: mudanças de comportamento (features) incrementam o
minor; correções incrementam o patch.

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