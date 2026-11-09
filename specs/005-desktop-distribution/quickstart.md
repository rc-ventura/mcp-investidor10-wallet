# Quickstart — validação da spec 005

> **Revisão de 08/11/2026:** o servidor do plugin não é mais um `.mcpb`; o plugin declara `mcpServers` inline com `uvx` e o `uv` é pré-requisito do Desktop (research.md D1, spec.md Clarifications, learning lesson do spike). Trechos abaixo sobre `.mcpb`, `build_mcpb.py` e `servers/carteira.mcpb` estão substituídos.

Roteiros que provam a feature de ponta a ponta. Detalhes de formato ficam
nos contratos e no data-model; aqui só o que rodar e o que esperar. Nunca
usar a carteira do mantenedor em registros: os exemplos usam `<id>` e
`<hash>`, e os testes contra a API real usam a carteira fictícia dedicada.

## S1 — Spike do servidor empacotado (primeira tarefa, bloqueia o resto da US1)

Pré-requisitos: uma máquina (ou conta de usuário) limpa em macOS e outra em
Windows, só com o Claude Desktop, plano pago e o Claude unificado; uma
máquina com Claude Code CLI e outra com Claude Code no Linux.

1. Gerar um plugin de teste com um MCPB `uv` mínimo, compactar e subir por
   Customize > Plugins > Add > Upload plugin. Ele traz três tools: `ping`,
   `abrir_pagina` (abre no navegador um formulário em `127.0.0.1` e grava o
   valor em `~/.investidor10-spike/`) e `formulario_app` (o mesmo formulário
   como MCP App, dentro da conversa). Traz também dois subagentes de teste, um
   com o nome curto da tool e outro com o nome completo na lista `tools`.
   Conferir na aba Connectors do plugin se o servidor pede algum passo extra.
2. Numa conversa nova da tela inicial (sessão Cowork), pedir "use a tool
   ping".
3. Pedir "use a tool abrir_pagina", preencher e enviar um valor de teste.
4. Pedir "use a tool formulario_app", preencher e enviar outro valor de teste.
5. No Claude Code, abrir uma sessão (plugin sincronizado) e rodar `/mcp`.
6. Repetir o passo 5 com o plugin também instalado localmente.
7. Repetir o passo 5 no Linux.
8. Chamar cada subagente de teste no Cowork e no Claude Code e ver qual consegue
   usar a tool.
9. Adicionar o marketplace de teste (repositório com a branch padrão `main` e
   outra branch `teste` com conteúdo diferente): conferir qual conteúdo o
   Desktop instala por padrão e se `dono/repo#ref` é aceito em Add
   marketplace.

Esperado: a tool responde no Cowork em macOS e Windows sem Python nem uv
instalados e sem passo extra na aba Connectors; o navegador abre, o arquivo
aparece em `~/.investidor10-spike/` e o valor não aparece na conversa; o Claude Code mostra `plugin:<nome>:<servidor>` conectado; o passo 6
registra se aparece em dobro. O passo 4 só informa: se o formulário aparece e
se o valor fica fora da conversa e do histórico. Resultado e caminho escolhido
na árvore de decisão de research D1 viram learning lesson antes de seguir. Se o
navegador não abrir no Cowork (passo 3), o fluxo de configuração volta ao
mantenedor antes do Lote 5.

## S1b — Revogação do link (premissa a verificar)

Com a carteira fictícia em modo restrito: guardar o link atual, gerar um link
novo no site e consultar a API com o hash antigo.
Esperado, se a premissa valer: HTTP 301 com o hash antigo e 200 com o novo. O
resultado define o que `docs/PRIVACY.md` e os textos ao usuário podem prometer.

## S2 — Desktop do zero (US1, SC-001, SC-001a)

Antes da promoção para `main`, instalar o plugin por Customize > Plugins >
Add > Upload plugin (zip de `plugin/` com o pacote apontando para a rc
publicada) e executar os passos 2 a 4. Depois da promoção, repetir o passo 1
pelo marketplace.

1. Customize > Plugins > Add marketplace, colar
   `rc-ventura/mcp-investidor10-wallet`; instalar `investidor10-carteira`.
2. Conversa nova: "como está minha carteira?".
   Esperado: o assistente abre a página de configuração antes de qualquer
   número.
3. Na página, colar o link público da carteira fictícia, deixar o mascaramento
   desligado e salvar.
   Esperado: a página mostra o modo público e o aviso de indexação; a pergunta
   seguinte, na mesma conversa, retorna dados com `fetched_at`, e o link não
   aparece na conversa.
4. Cronometrar do passo 1 ao 3: até 5 minutos.

## S3 — Garantia sem hook (FR-004, FR-006)

Com a configuração local removida, num cliente sem o hook de início de
sessão (por exemplo o Claude Code com o plugin desabilitado e o servidor
registrado à parte, ou um teste com `fastmcp.Client`): chamar
`get_wallet_summary`.
Esperado: `isError=true`, código `wallet_not_configured`, mensagem que
nomeia `open_wallet_setup`.

## S4 — Carteira restrita e acesso recusado (US2, SC-003)

1. Configurar na página com o link restrito (`…/wallet/public/<id>?h=<hash>`).
   Esperado: a página mostra o modo restrito; o link não aparece na conversa.
2. Gerar um link novo no site (o antigo deixa de valer) e repetir uma
   pergunta.
   Esperado: `access_denied` com a ação de reconfigurar; nunca
   `unexpected_format`.
3. `mcp-investidor10-wallet configure --link <link novo> --no-mask`.
   Esperado: código 0; a conversa aberta volta a responder sem reiniciar.

## S5 — Troca de carteira e segurança da página (FR-007, FR-008)

1. Com uma carteira configurada, colar na página o link de outra.
   Esperado: a página mostra a carteira atual mascarada e o aviso sobre a
   memória; o arquivo fica intocado até a confirmação na página.
2. Conferir o esquema das tools: nenhuma recebe link, credencial ou
   mascaramento.
3. Enviar o formulário sem token, com token usado, com token vencido e com
   `Origin` de outro site.
   Esperado: todos recusados, nada gravado; o corpo do envio não aparece em
   log nem na saída de erro do servidor.

## S6 — Memória e configuração compartilhadas (SC-002, FR-009c)

Salvar uma tese no Claude Code; perguntar pelas teses no Desktop.
Esperado: a tese aparece. Atualizar o marketplace e desinstalar e
reinstalar o plugin: memória e configuração intactas.

## S7 — Sem duplicação no Claude Code (FR-009d)

Numa máquina com o registro antigo `carteira` em escopo de usuário, rodar
`uvx mcp-investidor10-wallet@<versão> install --clients claude`.
Esperado: o assistente oferece remover o registro antigo; com o plugin
sincronizado presente, não instala localmente; `/mcp` mostra um só servidor
da carteira; 20 tools, não 40. Recusando a remoção: o plugin é instalado, o
relatório avisa da duplicação e o `doctor` a aponta. Numa máquina com a 0.3.x:
uma pergunta só cobre remover e readicionar o marketplace e reinstalar o plugin,
e memória e configuração ficam intactas.

## S8 — Diagnóstico (US5, SC-007)

Provocar cada causa (sem uv, link inválido, carteira privada, memória sem
escrita, produto não registrado) e rodar `mcp-investidor10-wallet doctor`.
Esperado: causa e ação corretas em 5 de 5; a saída não contém ID,
credencial, valores nem o nome do usuário local.

## S9 — Fluxo de release e cadeia de suprimentos (US6, SC-008, SC-010)

1. Pré-lançamento: tag `v0.4.0rcN` em `develop`. O job `build` roda sem
   `id-token`; o `publish` é o único com permissão e pede aprovação; o `verify`
   instala a versão exata em ambiente limpo nos três sistemas. `main` não muda.
2. Versão final: pedido de preparação em `develop`, tag `v0.4.0`, publicação e
   `verify` verde. Esperado: `promote.yml` cria `promote/v0.4.0` no commit da
   tag e abre o pedido para `main`; o `main-gate` passa; só depois do merge o
   marketplace entrega a versão.
3. Portão: abrir um pedido de teste para `main` a partir de `develop`, e outro
   de uma `promote/vX.Y.Z` cuja versão não esteja no índice. Esperado: o
   `main-gate` recusa os dois, com a causa em PT-BR.
4. Hotfix: na primeira correção urgente, `hotfix/*` sai de `main`, recebe tag,
   é publicada, promovida e volta para `develop`; registrar o resultado em
   `docs/RELEASING.md`.
5. `uv run pytest -k consistency`: versões iguais. No `build`,
   `scripts/build_mcpb.py --check`: tools iguais e MCPB commitado = gerado.
6. Disparar `live.yml` manualmente: roda com a carteira fictícia; falha
   imprime só o código.

## S10 — Matriz de máquinas limpas (US4, SC-006)

Preencher `specs/005-desktop-distribution/validation-matrix.md` (cliente ×
plataforma × resultado × data): Claude Desktop sessão Cowork e conversa
Chat (macOS, Windows), Claude Code (macOS, Windows, Linux), Devin CLI, Devin Desktop, Codex pela
interface interativa, Gemini CLI. Nenhuma célula "não testado" no
fechamento.

## Suíte automatizada

```bash
uv run pytest            # não-live, a cada commit
uv run pytest -m live    # opt-in, carteira fictícia via WALLET_ID do ambiente
```
