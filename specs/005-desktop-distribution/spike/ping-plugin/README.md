# Plugin de teste do spike (S1)

Plugin descartável `spike-ping` para o roteiro S1 de `specs/005-desktop-distribution/quickstart.md`.
Ele só existe para responder, numa máquina limpa, se um servidor MCPB do tipo `uv` dentro de um
plugin funciona no Claude Desktop (sessão Cowork) e no Claude Code. Não faz parte do produto e não
carrega código da carteira.

## O que tem

| Item | Para que serve |
|---|---|
| `servers/ping.mcpb` | servidor empacotado (`server.type` `uv`, `manifest_version` `0.4`, `fastmcp[apps]==4.1.2`, `prefab-ui==0.20.2`) |
| tool `ping` | devolve `pong` e anota a chamada em `~/.investidor10-spike/log.txt` |
| tool `abrir_pagina` | abre no navegador um formulário em `127.0.0.1`; o valor vai para `~/.investidor10-spike/valor_pagina.txt` e não volta na resposta |
| tool `formulario_app` | o mesmo formulário como MCP App dentro da conversa; a tool de apoio `salvar_valor_app` fica só para a interface (`visibility` `app`) e grava em `valor_app.txt` |
| `agents/probe-short-name.md` | subagente com `tools: ping` |
| `agents/probe-full-name.md` | subagente com `tools: mcp__plugin_spike-ping_ping__ping` |

O nome do servidor vem do `manifest.json` do pacote (`ping`), então no Claude Code ele aparece como
`plugin:spike-ping:ping`. Não há `bin/` no topo do plugin (o Chat e o Cowork recusam o plugin inteiro).

## Antes de testar

1. Reconstruir o pacote, se o código do servidor mudou: `python3 specs/005-desktop-distribution/spike/ping-server/build.py`
   (zip determinístico: duas execuções geram bytes iguais).
2. Validar o pacote com o CLI oficial, que eu não consegui executar na minha sessão:
   `npx @anthropic-ai/mcpb@2.1.2 validate specs/005-desktop-distribution/spike/ping-server/manifest.json`.
   Anote no registro abaixo se passou.
3. Compactar o plugin: `cd specs/005-desktop-distribution/spike/ping-plugin && zip -r ../ping-plugin.zip .`
   Se o app recusar o zip, tente compactar a pasta inteira (`zip -r ping-plugin.zip ping-plugin`) e
   registre qual formato funcionou.

## Roteiro (S1, resumo)

Máquina ou conta limpa em macOS e em Windows, só com o Claude Desktop, plano pago e Claude unificado;
Claude Code CLI em macOS, Windows e Linux.

1. Customize > Plugins > Add > Upload plugin com o zip. Conferir na aba Connectors do plugin se o
   servidor pede passo extra.
2. Conversa nova da tela inicial (sessão Cowork): "use a tool ping".
3. "use a tool abrir_pagina": o navegador abre, preencher e enviar um valor.
4. "use a tool formulario_app": preencher e enviar outro valor (só informativo).
5. Claude Code com o plugin sincronizado: `/mcp`.
6. De novo com o plugin também instalado localmente: registrar se o servidor aparece em dobro.
7. Repetir o 5 no Linux.
8. Chamar `probe-short-name` e `probe-full-name` no Cowork e no Claude Code e ver qual consegue usar a tool.
9. Marketplace de teste (branch padrão `main` e outra branch `teste` com conteúdo diferente): qual conteúdo
   o Desktop instala por padrão e se `dono/repo#ref` é aceito em Add marketplace.

Esperado: `ping` responde sem Python nem uv instalados e sem passo extra na aba Connectors; o arquivo
aparece em `~/.investidor10-spike/` e o valor não aparece na conversa.

## Registro de resultados (preencher; vira a learning lesson do T012)

Anote versão do app e do Claude Code, sistema e data em cada coluna.

| Passo | macOS | Windows | Linux |
|---|---|---|---|
| Validação `mcpb validate` 2.1.2 | Passou (03/11/2026) | | |
| 1. Upload plugin aceito; Connectors sem passo extra | Aceito; sem passo extra (Desktop 4.16336.0, Cowork, plano pago) | | n/a |
| 2. `ping` no Cowork | `pong`. Atenção: o app usou o `uv` já instalado no Mac (`~/.local/bin/uv`) e o cache do `uv` estava quente | | n/a |
| 3. `abrir_pagina`: navegador abriu; arquivo gravado; valor fora da conversa | Navegador abriu; `valor_pagina.txt` gravado (pasta 700); valor não apareceu na conversa | | n/a |
| 4. `formulario_app`: apareceu; valor fora da conversa e do histórico | Não renderizou: o modelo recebeu só `[Rendered Prefab UI]`; `valor_app.txt` não foi criado; sem erro nos logs do app | | n/a |
| 5. `/mcp` no Claude Code (sincronizado) | Aba Code do Desktop: aparece 1 vez, conectado. CLI 2.1.317: ausente (`claude plugin list` mostra `spike-ping@synced` loaded; `claude mcp list` não lista o servidor) | | |
| 6. Plugin carregado como local no CLI (`--plugin-dir`) | Plugin habilitado e agentes carregados; 1 erro: `MCPB manifest invalid ... Expected 'python' \| 'node' \| 'binary', received 'uv'` | | n/a |
| 8. Subagente `probe-short-name` | Cowork: recusado, lista de tools vazia. CLI: `would be spawned with zero tools` (servidor não sobe no CLI) | | |
| 8. Subagente `probe-full-name` | Igual ao curto. No Cowork o nome real da tool é `mcp__remote-devices__plugin_spike-ping_ping__ping` | | |
| 9. Branch padrão lida; `dono/repo#ref` aceito | Pendente | | n/a |

### Achados até aqui (macOS, 03/11/2026)

- O Desktop resolve o comando `uv` pelo PATH do shell de login do usuário; não há sinal de `uv` embutido no app. O teste em máquina sem `uv` continua pendente.
- O Claude Code CLI 2.1.317 valida o manifesto do `.mcpb` e só aceita `python`, `node` e `binary`; o servidor do plugin não sobe no CLI, e o resto do plugin (agentes) carrega.
- O app anunciou 3 das 4 tools ao modelo: a de apoio do app (`visibility` `app`) fica oculta.
- O nome da tool de plugin muda por superfície, então uma lista `tools` fixa no subagente não é confiável.

Decisão da árvore de D1 (research.md): ramo 1, 2 ou 3, com a justificativa.

## Limpeza

Remover `~/.investidor10-spike/` e desinstalar o plugin `spike-ping` ao fim.
