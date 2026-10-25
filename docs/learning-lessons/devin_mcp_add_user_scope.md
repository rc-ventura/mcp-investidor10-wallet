# Devin CLI `mcp add` tem flags de user scope e env — baseline do README estava incompleto

- **Data**: 2026-10-24
- **Fonte**: `devin mcp add --help` na versão instalada (Devin CLI 3000.11.x)

## Fato verificado

O comando `devin mcp add` suporta:

- `-s, --scope <SCOPE>` — escopo da configuração; `user` grava em
  `~/.config/devin/mcp_config.json` (user-level da máquina)
- `-e, --env <KEY=VALUE>` — variáveis de ambiente para o processo stdio do
  servidor

O baseline anterior do projeto (README + contract install-cli) usava
`devin mcp add carteira -- env WALLET_ID=<id> uvx ...`, sem `--scope` —
portanto registrava no escopo default (não user) e usava a forma `env` como
primeiro argumento posicional do comando, que também não é a flag `-e`.

## Decisão decorrente

O assistente de instalação registra o Devin CLI como:

```
devin mcp add -s user carteira -e WALLET_ID=<id> -- uvx mcp-investidor10-wallet
```

— consistente com a decisão D5 da spec 003 (escopo user em todos os
clientes) e com a forma nativa das flags. Contrato install-cli.md e README
ajustados no mesmo ciclo (Constituição: premissa revalidada + implementação
juntas).