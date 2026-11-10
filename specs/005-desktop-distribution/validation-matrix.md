# Matriz de validação — spec 005

Preencher em T061 (Lote 5) e completar em T083 a T086 (Lote 8). Resultado: `ok`, `falhou` (com a mensagem exata) ou `não testado`.

| Roteiro | Cliente | Plataforma | Resultado | Tempo | Data | Observações |
|---|---|---|---|---|---|---|
| S2 passos 2 a 4 | Claude Desktop | macOS | ok | menos de 5 min (informado pelo mantenedor) | 2026-11-08 | Assistente abriu a página de configuração sozinho em conversa nova; zip do plugin por Upload plugin |
| S2 passos 2 a 4 | Claude Desktop | Windows | não testado | | | |
| S2 sem `uv` | Claude Desktop | macOS | ok | menos de 5 min (informado pelo mantenedor) | 2026-11-08 | `uv` instalado pelo terminal, terminal fechado, Desktop reiniciado (talvez dispensável); servidor subiu. |
| Plugin `uvx` | Claude Code CLI | macOS | não testado | | | `/mcp` com um só servidor (20 tools) |
| S5, S6, S7 | Claude Desktop | macOS | não testado | | | |
| S5, S6, S7 | Claude Desktop | Windows | não testado | | | |
| S6 memória compartilhada | Claude Desktop | macOS | ok | | 2026-11-08 | A tese salva no Claude Code apareceu no Desktop |
