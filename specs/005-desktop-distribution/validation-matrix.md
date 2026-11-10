# Matriz de validação — spec 005

Preencher em T061 (Lote 5) e completar em T085 (Lote 8). Resultado: `ok`, `falhou` (com a mensagem exata), `pendente` (com onde será feito) ou `não testado`. Tempos são os informados pelo mantenedor, sem cronômetro.

| Roteiro | Cliente | Plataforma | Resultado | Tempo | Data | Observações |
|---|---|---|---|---|---|---|
| S2 passos 2 a 4 | Claude Desktop | macOS | ok | menos de 5 min | 2026-11-08 | Assistente abriu a página de configuração sozinho em conversa nova; zip do plugin por Upload plugin |
| S2 sem `uv` | Claude Desktop | macOS | ok | menos de 5 min | 2026-11-08 | `uv` instalado pelo terminal, terminal fechado, Desktop reiniciado (talvez dispensável); servidor subiu |
| S6 memória compartilhada | Claude Desktop | macOS | ok | | 2026-11-08 | A tese salva no Claude Code apareceu no Desktop; reconfirmado em 2026-11-10 |
| Casos extras (plugin no Claude Code CLI, branch padrão, `#ref`) | Claude Desktop e Code | macOS | ok (caminho feliz) | | 2026-11-10 | Informado pelo mantenedor; sem registro por caso |
| Plugin `uvx` no Claude Code, duplicação | Claude Code CLI | macOS | ok (parcial) | | 2026-11-10 | Registro antigo `carteira` removido à mão, `claude mcp list` com um só servidor (`plugin:investidor10-carteira:carteira`); o instalador real não foi rodado |
| S2 passos 2 a 4, com `uv` do PowerShell | Claude Desktop | Windows | **pendente, carregado para T085 (Lote 8)** | | | Não validado no Lote 5 |
| S5, S6 | Claude Desktop | Windows | **pendente, carregado para T085 (Lote 8)** | | | |
| S5 troca de carteira e segurança da página | Claude Desktop | macOS | ok | | 2026-11-10 | Informado pelo mantenedor; sem registro por caso |
| S7 `install --clients claude` | Claude Code CLI | macOS e Windows | **pendente: depende da `0.4.0rc4`** | | | O tag `v0.4.0rc3` carrega o plugin antigo (0.1.1, sem `mcpServers`); rodar o instalador agora trocaria o plugin que funciona por ele |
