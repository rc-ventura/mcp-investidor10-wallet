# O `.mcpb` tipo `uv` não dispensa o `uv` no Claude Desktop: o plugin leva `uvx` e o `uv` vira pré-requisito

**Context:** A spec 005 apostava que um servidor empacotado como `.mcpb` do tipo `uv`, dentro do plugin, subiria no Claude Desktop sem que o usuário instalasse Python ou `uv` (ramo 1 da árvore de decisão de D1). O spike do Lote 1 (plugin de teste `spike-ping`, servidor `ping` em FastMCP) mediu isso em 03/11/2026 no macOS e em 08/11/2026 numa máquina sem `uv`. A conclusão: no computador real o `uv` precisa existir, o Claude Code CLI rejeita o tipo `uv`, e o ramo 1 não se sustenta.
**Date:** 2026-11-08
**Future intent:** Para o Desktop, o plugin declara o servidor com `command: uvx` no próprio `plugin.json`, fixando a versão publicada no PyPI, e o `uv` é pré-requisito documentado, com um tutorial conservador (`docs/INSTALACAO-DESKTOP.md`). Nenhuma decisão de distribuição presume que o app traz o `uv` sem uma evidência nova, em máquina sem `uv`, com a mensagem de erro registrada.

---

## O que foi medido

Fontes: README do plugin de teste (macOS, Claude Desktop 4.16336.0, Cowork, plano pago, Claude Code CLI 2.1.317, 03/11/2026), `main.log` do Desktop e o relato do mantenedor para a máquina sem `uv` (08/11/2026).

| Verificação | Resultado |
|---|---|
| Upload do plugin com `.mcpb` tipo `uv`; aba Connectors | Aceito, sem passo extra (macOS, com `uv` instalado) |
| `ping` e `abrir_pagina` numa sessão Cowork, com `uv` na máquina | `pong`; o navegador abriu, o arquivo foi gravado em `~/.investidor10-spike/` (pasta 0700) e o valor não apareceu na conversa |
| Qual `uv` o Desktop usou | O do usuário: o log mostra `Using MCP server command: …/.local/bin/uv` (03 e 07/11). Não há sinal de `uv` embutido no app |
| `formulario_app` (MCP App) | Não renderizou: o modelo recebeu só `[Rendered Prefab UI]`, o arquivo não foi criado, sem erro nos logs |
| Claude Code CLI 2.1.317 com o `.mcpb` tipo `uv` | O servidor não sobe: `MCPB manifest invalid … Expected 'python' \| 'node' \| 'binary', received 'uv'`. O resto do plugin (agentes) carrega |
| Máquina sem `uv`, plugin `.mcpb` tipo `uv` (B) e plugin com `uvx` no `plugin.json` (A) | Nos dois o servidor não subiu fora do sandbox. **A mensagem exata não foi registrada**: a causa (`uv` ausente ou fora do PATH do app) é a hipótese do mantenedor e ainda não foi confirmada por log |
| Sandbox do Cowork | O servidor rodou dentro do sandbox, onde o `uv` foi instalado. **Não está registrado** se foi o `mcpServers` do plugin ou comandos do próprio modelo; por isso não conta como prova de que o plugin dispensa o `uv` |
| Plugin com `mcpServers` inline `uvx` (servidor real, `0.4.0rc3`), macOS com `uv` | Conectou no Desktop e o fluxo ponta a ponta funcionou (link restrito com hash validado); a página recusou o link público sem `?h=` (corrigido separadamente, ADR-0019 §5) |
| Subagentes com `tools: ping` e `tools: mcp__plugin_spike-ping_ping__ping` | Os dois falharam: no Cowork o nome real da tool foi `mcp__remote-devices__plugin_spike-ping_ping__ping`. O nome muda por superfície, então uma lista `tools` fixa não é confiável |

---

## Decisão de D1

O ramo escolhido é uma variante do ramo 3: **`uvx` com o `uv` como pré-requisito documentado, só no Desktop**. O Claude Code continua pelo assistente de instalação (ADR-0012), que registra o servidor com `claude mcp add`. O binário por plataforma (ramo 2) foi descartado: assinatura com Developer ID, notarização e o bloqueio do Gatekeeper no macOS (o Sequoia removeu o atalho de Control-click) tornam o custo e o risco desproporcionais. O `.mcpb` tipo `uv` perdeu a razão de existir, porque só valeria se o app trouxesse o `uv`.

A FR-002 ("sem abrir terminal") é revista: o usuário abre o terminal uma única vez para instalar o `uv`, e todo o resto é feito no Desktop.

---

## Limites

- Os resultados são de macOS. Windows e Linux não foram testados nesta rodada.
- Seguem sem verificação: se o Desktop enxerga um `uv` recém-instalado sem reiniciar, se basta um terminal novo, a mensagem de erro sem `uv`, o comportamento do mesmo plugin `uvx` no Claude Code CLI, qual branch o Desktop lê por padrão no Add marketplace e se `dono/repo#ref` é aceito. O tutorial marca esses pontos como "a validar" e eles não bloqueiam o Lote 5; o T061 os cobre.
- O S1b (o link antigo recebe 301 quando se gera um link novo) segue pendente (T011).
- O resultado do `formulario_app` não bloqueia nada: MCP Apps ficam fora da spec e só alimentam o roadmap.

---
