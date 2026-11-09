# Fichamento: distribuição de servidores MCP locais em plugins e extensões

- **Pesquisado em**: 2026-11-06
- **Atualizado em**: 2026-11-06
- **Origem**: spec 005 (distribuição Desktop), decisão D1, após o spike em máquina limpa
- **Decisão que serve**: a escolha do runtime do servidor MCP local dentro de um plugin para o Claude Desktop (sessões Cowork e Chat) e o Claude Code, para um servidor em Python distribuído no PyPI.

## Por que esta pesquisa

Um spike em máquina limpa, com um plugin de teste que leva um servidor MCPB `server.type: "uv"`,
mostrou que o Claude Desktop não traz o `uv`: sem ele o servidor não sobe, e o app (via assistente)
pediu para instalá-lo. No Claude Code CLI 2.1.317, o manifesto com `server.type` `uv` foi recusado
(só aceita `python`, `node`, `binary`). A premissa "o app instala Python e dependências com uv,
sem passo do usuário" caiu. Falta saber a prática observada nas integrações oficiais e em projetos
de terceiros, e os relatos de problema com runtime.

## Perguntas

| # | Pergunta | Força da evidência |
|---|---|---|
| 1 | As integrações oficiais da Anthropic rodam o servidor como remoto (URL/HTTP) ou local? Quando local, com qual runtime e tipo? | Documentação |
| 2 | Como extensões MCPB de terceiros e do diretório empacotam servidores locais (tipo predominante, dependências, runtime)? | Exemplo real |
| 3 | Como plugins de terceiros declaram servidores MCP (`.mcp.json`, `npx`, `uvx`, binário) e quais pré-requisitos documentam? | Exemplo real |
| 4 | Como servidores MCP em Python chegam ao usuário leigo no Claude Desktop (MCPB `uv`, binário PyInstaller/Nuitka/shiv, wrapper em Node, remoto), e que relatos existem sobre `uv` ausente, `spawn uvx ENOENT` e PATH? | Exemplo real |
| 5 | O que o app embute de runtime, e o que a documentação diz sobre binários por plataforma, tamanho, assinatura, Gatekeeper, SmartScreen e download de binário em tempo de execução? | Documentação |
| 6 | (Acréscimo da segunda rodada) A documentação do Cowork descreve um sandbox ou VM para as ferramentas de shell e arquivos? Onde rodam os servidores MCP locais e os plugins (host ou sandbox)? O assistente instala software ou executa comandos no host? O servidor local do plugin enxerga o host (PATH do shell de login, `~/`, navegador)? | Sem evidência |

Força da evidência: `Norma oficial`, `Documentação`, `Exemplo real`, `Opinião` ou `Sem evidência`.
A pergunta 5 tem evidência de documentação para runtime embutido (só Node citado), tipos de servidor
aceitos e comando de assinatura; limite de tamanho, comportamento do Desktop com pacote assinado ou não,
Gatekeeper (além de uma frase genérica), SmartScreen e download em tempo de execução ficaram sem
evidência. A pergunta 6 não foi pesquisada: o limite de 15 consultas web da segunda rodada já estava
esgotado quando o acréscimo chegou.

## Afirmações testadas

| Afirmação | Situação | Fontes |
|---|---|---|
| A1: O Claude Desktop não traz o `uv` embutido. | Sem evidência | [F4] [F6] [F13] [F15] [F16] [F17] [F19] [F20] |
| A2: As integrações oficiais da Anthropic usam sobretudo servidor remoto ou local em Node; quase nenhuma depende de `uv` ou Python. | Sem evidência | [F9] [F10] [F11] [F12] [F19] [F24] |
| A3: O tipo `uv` do MCPB é o caminho recomendado pela documentação para servidores Python e dispensa instalação do usuário. | Contradita | [F2] [F3] [F4] [F6] [F13] [F16] [F19] [F22] |
| A4: O Claude Code CLI aceita servidor de plugin do tipo `uv`. | Contradita | [F15] |

Notas de classificação (só o que as fontes sustentam):

- A1: nenhuma fonte oficial afirma nem nega que o app embute o `uv`. Os relatos de terceiros são
  coerentes com a ausência, mas não a declaram. Segunda rodada: as páginas oficiais lidas citam só Node
  como runtime embutido e não mencionam `uv` quanto a quem o fornece [F16] [F17] [F19] [F20]; ausência na
  documentação não confirma a afirmação.
- A2: a amostra lida (23 servidores de um plugin de conhecimento, um plugin externo de parceiro, parte do
  `marketplace.json`) não contém `uv` nem Python, mas não cobre o conjunto das integrações oficiais.
  Segunda rodada: a página oficial de design de plugin diz que "most plugins reference remote servers"
  [F24] e a de MCPB recomenda Node [F19]; são orientações, não um levantamento das integrações, e o
  diretório de extensões não foi inventariado.
- A3: a documentação do MCPB diz "No user Python installation required" (sobre Python, não sobre
  `uv`) e marca o tipo como experimental; a palavra "recomendado" aparece em respostas de mantenedores
  numa issue, não na documentação lida. Os relatos de `uv` não encontrado contradizem a parte "dispensa
  instalação". Segunda rodada: o `MANIFEST.md` não usa "recomendado" para o `uv` [F16]; a página do
  Desktop recomenda Node [F19]; a skill oficial `build-mcpb` lista `node`, `python` e `binary` e não cita
  `uv` [F22].
- A4: a única fonte é o relato do brief (spike). Segunda rodada: a referência oficial do manifesto de
  plugin do Claude Code diz que `mcpServers` aceita `.mcpb`/`.dxt`, mas não lista os tipos de servidor
  aceitos dentro do bundle [F18]; a página de MCP do Claude Code (lida até 100000 de 156847 caracteres)
  não menciona o assunto [F21]. Nenhuma fonte oficial confirma nem contradiz o resultado do spike.

## O que o projeto já registra

- `specs/005-desktop-distribution/research.md`, D1: decisão de apontar o `mcpServers` do plugin para
  `plugin/servers/carteira.mcpb`, tipo `uv`, `manifest_version` 0.4, com dependência
  `mcp-investidor10-wallet==<versão>` do PyPI; define um spike (S1) e uma árvore de decisão com
  `binary` por plataforma e `command: "uvx"` como alternativas.
- `specs/005-desktop-distribution/data-model.md`, seção 6: manifesto gerado com `server.type` `uv`
  e `compatibility.platforms` `["darwin", "win32", "linux"]`.
- `specs/005-desktop-distribution/plan.md`: lista o pacote `uv` e o `binary` como alternativa.
- `docs/adrs/0011-estrategia-de-distribuicao-e-release.md`: PyPI como único canal, `uvx` como
  comando documentado.
- `docs/adrs/0012-integracao-automatica-de-clientes.md`: assistente de instalação com `uvx` de versão
  fixa; Desktop adiado para spec futura.
- Fichamento [mcpb-e-runtime-do-servidor-local](mcpb-e-runtime-do-servidor-local.md): formato MCPB,
  tipos de servidor, Node incluído no app, PATH em apps gráficos. Não repetido aqui.
- Fichamento [plugins-claude-componentes-e-instalacao](plugins-claude-componentes-e-instalacao.md) e
  [marketplace-e-versoes-de-plugin](marketplace-e-versoes-de-plugin.md): componentes de plugin e
  marketplace. Não repetidos aqui.

## Premissas do projeto tocadas

- `specs/005-desktop-distribution/research.md`, D1: "o app instala Python e dependências com uv" e
  "o app embarca Node.js, não Python"; tratadas em [F2], [F3], [F4], [F6], [F13], [F16], [F17], [F19], [F20].
- `specs/005-desktop-distribution/data-model.md`, seção 6: `server.type` `uv` com
  `manifest_version` 0.4; tratada em [F3], [F7].
- `specs/005-desktop-distribution/research.md`, D1, alternativa `binary`: "dezenas de MB por plataforma,
  [...] assinatura e quarentena do macOS"; o tema aparece em [F13] (sem tratar de assinatura nem
  quarentena), [F16] (`binary` autocontido), [F23] (`mcpb sign`) e [F17] (frase genérica sobre avisos de
  segurança no macOS).
- `specs/005-desktop-distribution/research.md`, D1, plugin com `mcpServers` apontando para `.mcpb` e
  "limite de 200 MB por plugin": o `.mcpb` em plugin é tratado em [F18]; o limite de 200 MB não foi
  encontrado nas fontes lidas.

## Fontes

| ID | Fonte | Tipo | Leitura | Consultada em |
|---|---|---|---|---|
| F1 | [mcpb: pasta examples](https://github.com/modelcontextprotocol/mcpb/tree/main/examples) | Oficial | Parcial | 2026-11-06 |
| F2 | [mcpb issue 84: Claude Desktop disables installation if no system python detected, even with uv installed](https://github.com/modelcontextprotocol/mcpb/issues/84) | Oficial | Inteira | 2026-11-06 |
| F3 | [mcpb PR 158: feat: add experimental UV runtime support in manifest v0.4](https://github.com/modelcontextprotocol/mcpb/pull/158) | Oficial | Inteira | 2026-11-06 |
| F4 | [claude-code issue 38266: Windows: Python-based MCP extensions fail to connect due to uv venv build race condition](https://github.com/anthropics/claude-code/issues/38266) | Comunidade | Inteira | 2026-11-06 |
| F5 | [manager-mcp, release v0.2.6](https://github.com/flumpiey/manager-mcp/releases/tag/v0.2.6) | Comunidade | Parcial | 2026-11-06 |
| F6 | [Windows-MCP (CursorTouch): README](https://github.com/CursorTouch/Windows-MCP) | Comunidade | Parcial | 2026-11-06 |
| F7 | [Windows-MCP (CursorTouch): manifest.json](https://raw.githubusercontent.com/CursorTouch/Windows-MCP/main/manifest.json) | Comunidade | Inteira | 2026-11-06 |
| F8 | [anthropics/knowledge-work-plugins: README](https://github.com/anthropics/knowledge-work-plugins) | Oficial | Inteira | 2026-11-06 |
| F9 | [knowledge-work-plugins: sales/.mcp.json](https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/sales/.mcp.json) | Oficial | Parcial | 2026-11-06 |
| F10 | [anthropics/claude-plugins-official: README](https://github.com/anthropics/claude-plugins-official) | Oficial | Parcial | 2026-11-06 |
| F11 | [claude-plugins-official: .claude-plugin/marketplace.json](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json) | Oficial | Parcial | 2026-11-06 |
| F12 | [claude-plugins-official: external_plugins/firebase/.mcp.json](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/external_plugins/firebase/.mcp.json) | Oficial | Inteira | 2026-11-06 |
| F13 | [mcpb: README](https://raw.githubusercontent.com/modelcontextprotocol/mcpb/main/README.md) | Oficial | Parcial | 2026-11-06 |
| F14 | Resultados de busca (sem abrir a página): [mcp2mcpb no PyPI](https://pypi.org/project/mcp2mcpb/), [fix mcp uvx not found](https://eseospace.com/blog/fix-mcp-uvx-not-found/), [MCP server not showing in Claude Desktop (Towards AI)](https://pub.towardsai.net/mcp-server-not-showing-in-claude-desktop-heres-what-i-did-df43a09aea0d) | Comunidade | Trecho | 2026-11-06 |
| F15 | Relato do spike no brief da spec 005 (máquina limpa; Claude Code CLI 2.1.317). Não reproduzido nesta pesquisa. | Prática própria | Inteira | 2026-11-06 |
| F16 | [mcpb: MANIFEST.md](https://raw.githubusercontent.com/modelcontextprotocol/mcpb/main/MANIFEST.md) | Oficial | Parcial | 2026-11-06 |
| F17 | [Getting started with local MCP servers on Claude Desktop (suporte)](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) | Oficial | Parcial | 2026-11-06 |
| F18 | [Plugin manifest reference (Claude Code)](https://code.claude.com/docs/en/plugins-reference) | Oficial | Inteira | 2026-11-06 |
| F19 | [Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb) | Oficial | Inteira | 2026-11-06 |
| F20 | [Desktop Extensions (Anthropic Engineering, 26/06/2025)](https://www.anthropic.com/engineering/desktop-extensions) | Oficial | Parcial | 2026-11-06 |
| F21 | [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) | Oficial | Parcial | 2026-11-06 |
| F22 | [claude-plugins-official: skill build-mcpb (plugins/mcp-server-dev/skills/build-mcpb/SKILL.md)](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/mcp-server-dev/skills/build-mcpb/SKILL.md) | Oficial | Parcial | 2026-11-06 |
| F23 | [mcpb: CLI.md](https://raw.githubusercontent.com/modelcontextprotocol/mcpb/main/CLI.md) | Oficial | Parcial | 2026-11-06 |
| F24 | [Decide what to include in your plugin](https://claude.com/docs/connectors/building/what-to-build.md) | Oficial | Inteira | 2026-11-06 |
| F25 | Resultados de busca (sem abrir a página): [agentplugins/agent-plugins-spec discussão 64](https://github.com/agentplugins/agent-plugins-spec/discussions/64), [mcpb format reference (data-wise)](https://data-wise.github.io/himalaya-mcp/reference/mcpb-format-reference), [MCPB.md do mcp-bash-framework (Glama)](https://glama.ai/mcp/servers/@yaniv-golan/mcp-bash-framework/blob/419639dcbad77d210c9c8c802fa97be538c1f6e1/docs/MCPB.md), [zircote/mcp-bundle](https://github.com/zircote/mcp-bundle), [anthropic dxt (AdamKane)](https://github.com/AdamKane/anthropic-dxt), [mcp2mcpb 0.3.0 e 0.4.0 no PyPI](https://pypi.org/project/mcp2mcpb/0.4.0/) | Comunidade | Trecho | 2026-11-06 |

Limites de leitura: as páginas passaram por extração que resume o conteúdo; F9 trouxe as 25 primeiras
linhas e um resumo do restante; F11 tem 191833 caracteres e só os primeiros 100000 foram lidos; F1, F6,
F10 e F13 foram lidas por resumo de trecho, sem os arquivos de manifesto (exceto F7, F9, F12).
Segunda rodada: F21 tem 156847 caracteres e só os primeiros 100000 foram lidos; F16, F17, F20, F22 e F23
foram lidas por pergunta dirigida a trechos (resumo), e o caminho de F22 foi inferido a partir da listagem
da skill em um índice de terceiros, mas abriu. F18 e F19 vieram completas (a F18, inclusive, trouxe a
página inteira). Páginas que não deram conteúdo: `skillselion.com/.../build-mcpb` (só navegação do site) e
`pypi.org/project/mcp2mcpb/` (a página respondeu "A required part of this site couldn't load").

## Buscas realizadas

| Consulta | Ferramenta | Resultado |
|---|---|---|
| mcpb examples (abrir pasta) | WebFetch | Seis exemplos; tipos de quatro deles |
| Claude Desktop extension uv not installed "uv" MCPB server type uv issue | WebSearch standard | Issue 84 do mcpb, issue 38266 do claude-code, release do manager-mcp, guias de PATH |
| modelcontextprotocol mcpb issue "server.type" "uv" Claude Desktop requires uv installed bundled uv | WebSearch standard | Release notes do manager-mcp, mcp2mcpb; nenhuma issue que diga se o app traz `uv` |
| mcpb issue 84, PR 158, claude-code issue 38266, release v0.2.6 | WebFetch | Texto e datas das quatro páginas |
| knowledge-work-plugins (README e `sales/.mcp.json`) | WebFetch | Layout dos plugins; 23 servidores HTTP |
| claude-plugins-official (README e `marketplace.json`) | WebFetch | Estrutura `/plugins` e `/external_plugins`; lista de entradas; leitura parcial |
| external_plugins/firebase/.mcp.json | WebFetch | Comando `npx` |
| Windows-MCP (README e `manifest.json`) | WebFetch | Extensão `uv` de terceiros; pré-requisitos |
| mcpb README | WebFetch | Runtime do app; ausência de assinatura, tamanho e Gatekeeper |

Total da primeira rodada: 15 chamadas web (limite do método).

Segunda rodada:

| Consulta | Ferramenta | Resultado |
|---|---|---|
| mcpb `MANIFEST.md` (tipos, `platform_overrides`, `compatibility`, tamanho, assinatura) | WebFetch | Requisitos por tipo; `uv` instalado pelo host; sem tamanho nem assinatura |
| Artigo de suporte 10949351 (instalações exigidas, assinatura, tamanho, Gatekeeper, SmartScreen) | WebFetch | Node embutido; sem `uv`, assinatura, tamanho nem SmartScreen |
| Referência do manifesto de plugin do Claude Code (`mcpServers` com `.mcpb`) | WebFetch | `.mcpb`/`.dxt` aceitos; tipos de servidor do bundle não listados |
| Documentação MCPB em claude.com (assinatura, tamanho, `uv`, instalação) | WebFetch | Node recomendado; diretório não aceita MCPB; sem `uv`, assinatura nem tamanho |
| mcpb manifest "server.type" "binary" PyInstaller Python MCP server Claude Desktop extension platform_overrides | WebSearch standard | Guias de binário e `platform_overrides`; nada sobre PyInstaller |
| anthropics filesystem desktop extension manifest.json server type node official Claude Desktop extension directory | WebSearch standard | Resumos de terceiros; manifesto da extensão Filesystem não encontrado |
| skillselion.com, skill `build-mcpb` | WebFetch | Só navegação do site; sem conteúdo |
| anthropic.com/engineering/desktop-extensions | WebFetch | Node embutido; sem `uv`, assinatura nem `platform_overrides` |
| code.claude.com/docs/en/mcp (servidores de plugin e `.mcpb`) | WebFetch | Servidores de plugin em `.mcp.json`; `.mcpb` não aparece nos 100000 caracteres lidos |
| SKILL.md da skill `build-mcpb` no `claude-plugins-official` | WebFetch | Tipos `node`/`python`/`binary`; comando `sign`; sem `uv` |
| mcpb `CLI.md` (assinatura) | WebFetch | `sign`/`verify`/`unsign`; certificados PEM; comportamento do Desktop ausente |
| claude.com `what-to-build.md` (servidor local em plugin) | WebFetch | Servidor local roda no Claude Code e no Cowork em computador do usuário, não no chat |
| pypi.org/project/mcp2mcpb | WebFetch | Página não carregou |
| claude-code issue plugin mcpServers .mcpb manifest server type "uv" not supported OR invalid python node binary | WebSearch standard | Referências de terceiros; nenhuma issue do claude-code |
| mcpb extension Python bundled uv binary downloads uv first run Claude Desktop extension without installing Python | WebSearch standard | `mcp2mcpb`, referência do PR 158; nada sobre o app trazer ou baixar `uv` |

Total da segunda rodada: 15 chamadas web (limite do método). O acréscimo sobre sandbox/VM do Cowork
(pergunta 6) chegou com o limite já esgotado e não foi pesquisado. Ficaram de fora: a documentação do
Cowork sobre sandbox ou VM, onde rodam os servidores MCP locais e plugins, instalação de software pelo
assistente no host, e o que o servidor local do plugin enxerga do host; PyInstaller/Nuitka/shiv em
`server.type: binary` com manifesto real; wrapper Node que baixa ou invoca runtime; inventário dos
manifestos do diretório de extensões; e a segunda metade do `marketplace.json`.

## Achados

### Integrações oficiais: remoto ou local (pergunta 1)

- O plugin `sales` do repositório `anthropics/knowledge-work-plugins` declara em `.mcp.json` servidores
  com `"type": "http"` e `"url"`, por exemplo `"url": "https://mcp.slack.com/mcp"` e
  `"url": "https://mcp.hubspot.com/anthropic"`. Segundo o resumo da página, os 23 servidores usam `http`
  com `url`, nenhum usa `command`, e três (Google Calendar, Gmail e Google Drive) têm o `url` vazio. [F9]
- O README do mesmo repositório diz que os conectores ligam o Claude a ferramentas externas "via MCP
  servers", que "Every component is file-based — markdown and JSON, no code, no infrastructure, no build
  steps", e que para trocar de conector se edita o `.mcp.json`. Não cita `npx`, `uvx`, Node nem Python. [F8]
- O repositório `anthropics/claude-plugins-official` separa `/plugins` ("Internal plugins developed and
  maintained by Anthropic") de `/external_plugins` ("Third-party plugins from partners and the
  community"). O layout padrão marca `.mcp.json` como "MCP server configuration (optional)". [F10]
- O plugin `firebase`, em `external_plugins/`, declara um servidor local: `"command": "npx"`,
  `"args": ["-y", "firebase-tools@latest", "mcp"]`. [F12]
- No `marketplace.json`, a parte lida (cerca de 167 entradas) usa sobretudo `source` do tipo URL de
  repositório Git ou `git-subdir`; as descrições citam servidores MCP de GitHub, Firebase, Azure,
  Datadog, Airtable, Context7 (descrito com URL remota `https://mcp.context7.com/mcp`), entre outros.
  O comando e os argumentos de cada servidor não aparecem nessa parte; não foi possível ver qual runtime
  cada um usa. [F11]
- Não foram lidos os manifestos das extensões do diretório de extensões do Claude Desktop nesta pesquisa.
  [F11] [F13] As páginas oficiais de orientação foram lidas na segunda rodada (ver abaixo). [F19] [F24]

### Extensões MCPB: tipos e exemplos (pergunta 2)

- O repositório `modelcontextprotocol/mcpb` tem seis exemplos: `calculator-rust` (Binary),
  `chrome-applescript` (Node.js), `file-manager-python` (Python), `hello-world-node` (Node.js),
  `file-system-node` e `hello-world-uv`; o tipo dos dois últimos não aparece no resumo da tabela. [F1]
- O README do mcpb tem exemplos de estrutura para Node.js, Python e Binary, e diz sobre binários:
  "Static linking preferred for maximum compatibility" e "Include all required shared libraries if
  dynamic linking used". [F13]
- Windows-MCP (CursorTouch), extensão de terceiros em Python: o `manifest.json` (versão `0.8.8`) usa
  `manifest_version` `"0.4"`, `server.type` `"uv"`, `entry_point` `src/windows_mcp/__main__.py`,
  `mcp_config.command` `"uv"` com `args` `["--directory", "${__dirname}", "run", "python", "-m",
  "windows_mcp", "serve"]`, `env` com `UV_NO_SYNC` `"1"` e `UV_CACHE_DIR` `"${__dirname}/.uv-cache"`,
  `compatibility.platforms` `["win32"]` e `compatibility.runtimes.python` `">=3.13"`. [F7]
- O README do Windows-MCP exige Python 3.14+ ("The current package requires Python 3.14+") e lista `uv`
  como pré-requisito (instalável com `pip install uv` ou script do astral.sh). A instalação "Option A
  (PyPI, recommended)" é uma entrada em `claude_desktop_config.json` com `"command": "uvx"` e
  `args` `["windows-mcp", "serve"]`. Menciona `.mcpb` uma vez, no passo de `npm install -g
  @anthropic-ai/mcpb`. [F6]
- O README do Windows-MCP registra que a instalação automática pelo "Claude Directory" pode falhar na
  versão MSIX porque `${__dirname}` resolve para o caminho errado, e que em Electron na versão da Store
  o PATH do sistema não é herdado ("use the full path to `uvx.exe` or `uv.exe`", em paráfrase do resumo). [F6]
- O identificador da extensão citado no relato do claude-code é `ant.dir.cursortouch.windows-mcp`. [F4]

### Plugins de terceiros: declaração e pré-requisitos (pergunta 3)

- Forma de declaração vista: `.mcp.json` com `command`/`args` para servidor local (`npx -y
  firebase-tools@latest mcp`) [F12] e `type: "http"` com `url` para servidor remoto [F9].
- Pré-requisitos documentados para o usuário: o README do `knowledge-work-plugins` só cita instalar
  plugins em `claude.com/plugins` (Cowork) ou `claude plugin marketplace add
  anthropics/knowledge-work-plugins` e `claude plugin install <plugin>@knowledge-work-plugins` (Claude
  Code); não cita conta, chave de API ou autenticação dos conectores. [F8]
- Nos `.mcp.json` lidos, nada foi encontrado com `uvx` ou binário: só `npx` [F12] e `http` com `url` [F9].
  Marketplaces comunitários e repositórios de terceiros fora do `claude-plugins-official` não foram lidos
  (ver "O que as fontes não cobrem").

### Servidores em Python para o usuário leigo (pergunta 4)

- Issue 84 do mcpb, aberta em 28/07/2025 (2025): o Claude Desktop recusa instalar como "incompatible" um
  pacote Python que usa `uv`, mesmo com `uv` instalado e `uv run main.py` funcionando; esperado: o app
  deveria "detect the python / uv runtime declared above and install without complaints". [F2]
- Na mesma issue, o mantenedor joan-anthropic (25/11/2025) pede teste com a abordagem em que
  `server.type` é `uv`, há `pyproject.toml` e as dependências não vão no `.mcpb`. O mantenedor
  bryan-anthropic (12/03/2026) escreve que o MCPB v0.4 "resolves this by telling Claude Desktop to use uv
  for dependency management rather than requiring system Python" e pede nova issue se houver problema com
  o tipo `uv`. A issue foi fechada como "not planned" em 12/03/2026. [F2]
- O PR 158 (aberto em 13/11/2025, mesclado em 04/12/2025) acrescenta o tipo `uv` como experimental ao
  manifesto v0.4: "UV extensions rely on pyproject.toml for dependencies"; `mcp_config` passa a ser
  opcional; lista "No user Python installation required" como benefício. A página não diz quem fornece o
  `uv`, nem se o host o instala, nem quais clientes suportam o tipo. Revisor questionou se o mcpb continua
  autocontido; a resposta foi que pacotes Python como pydantic exigem a versão exata de Python do build,
  e que a funcionalidade foi marcada experimental para poder voltar à abordagem empacotada. [F3]
- Issue 38266 do claude-code (aberta em 24/03/2026; Claude Desktop v1.1.7714.0, Windows Store, extensão
  Windows-MCP): o app inicia `uv run` e envia o `initialize` do MCP antes de o `uv` terminar de instalar
  os pacotes no `.venv`, o que gera erro de arquivo em uso (os error 32) e laço de falha. Relata também
  que o app tentou primeiro `uv` como comando simples e obteve `'uv' is not recognized`; o `uv` do
  relator estava em `C:\Python38\Scripts\uv.exe`. Sem resposta humana; fechada por bot como "not planned"
  porque "doesn't appear to be about Claude Code". Contorno do relator: pré-construir o `.venv` com
  `uv.exe run windows-mcp --help`. [F4]
- Release v0.2.6 do manager-mcp (terceiros; a página mostra "03 Aug" sem ano): "Claude maps
  `server.type: uv` to `uv.exe` and was running `uv manager-mcp` instead of `uvx manager-mcp`"; correção:
  "use `uv tool run manager-mcp` in mcpb mcp_config". [F5]
- Resultados de busca não abertos (Trecho): notas de outro projeto dizem que a extensão exige `uv` no PATH;
  um guia afirma que apps de desktop em geral não herdam o PATH do terminal; o pacote `mcp2mcpb` do PyPI
  descreve conversão de servidores PyPI/npm em bundles `.mcpb`. [F14]
- Nas fontes consultadas, nenhum exemplo de binário gerado com PyInstaller/Nuitka/shiv, de wrapper em
  Node que invoca Python ou de hospedagem remota de servidor Python foi encontrado [F1] [F2] [F3] [F4] [F6] [F7] [F13]; não houve busca dedicada.

### Runtime do app, binários e segurança (pergunta 5)

- README do mcpb: "Node.js ships with Claude for macOS and Windows"; não diz que Python é incluído; sobre
  `uv`: "Host application manages Python and dependencies automatically". [F13]
- A mesma página não trata de assinatura (`mcpb sign`), limite de tamanho, `platform_overrides`,
  Gatekeeper, notarização nem SmartScreen. [F13]
- Nas fontes consultadas, nada foi encontrado sobre download de binário em tempo de execução (por exemplo
  script que baixa `uv` na primeira execução) [F2] [F3] [F4] [F6] [F7] [F13]; não houve busca dedicada.

### Segunda rodada: orientação oficial, tipos de servidor e runtime

Tipos de servidor e quem fornece o runtime:

- `MANIFEST.md` do mcpb, por tipo: `node`, "Node.js server with bundled dependencies" ("All dependencies
  must be bundled in `node_modules`"); `python`, "Python server with bundled dependencies" ("All
  dependencies must be bundled in the MCPB"); `binary`, "Pre-compiled executable with all dependencies
  included" e "Completely self-contained (no runtime requirements)"; `uv`, "Must include `pyproject.toml`
  with dependencies", "Must NOT include `server/lib/` or `server/venv/`" e "`mcp_config` is optional
  (host manages execution)". [F16]
- No mesmo documento, as dependências do tipo `uv` são "installed by the host application using UV". O
  resumo da página não traz frase que diga que o usuário instala o `uv`, nem que o app o fornece, nem
  versão exigida do `uv`; o "(v0.4+)" aparece no título do tipo. Cita um benefício de tamanho:
  "Small bundle size (~100 KB vs 5-10 MB)". [F16]
- `compatibility.platforms`: "Array of supported platforms (`darwin`, `win32`, `linux`)" e "If omitted, all
  platforms are supported"; `compatibility.runtimes`: "Only specify the runtime(s) your extension actually
  uses". `platform_overrides` aparece como "For cases where different platforms need different
  configurations, use platform-specific overrides:"; o exemplo que segue não veio no resumo. [F16]
- A skill oficial `build-mcpb`, publicada em `claude-plugins-official`, lista `node`, `python` e `binary`
  para `server.type`, "Informational; the actual launch comes from `mcp_config`", e não menciona `uv`.
  Diz que o usuário "runs without needing Node, Python, or any toolchain on their machine". Para Python:
  "Vendor dependencies into a subdirectory and prepend it to `sys.path` in your entry script"; extensões
  nativas "must be built for each target platform". [F22]
- O CLI `mcpb init` pergunta o tipo de servidor entre Node.js, Python e Binary (sem `uv` no texto lido);
  a documentação do `validate` não lista regras para `server.type`. [F23]

Orientação oficial sobre o que o app embute e o que o usuário precisa:

- A documentação de MCPB em claude.com: "Node.js is strongly recommended", "Included with Claude Desktop on
  macOS and Windows, so users need no separate runtime"; "Claude Desktop runs on macOS (`darwin`) and
  Windows (`win32`)". A página não cita `uv`, assinatura nem limite de tamanho. [F19]
- Instalação: cada método abre uma interface em que o usuário "reviews extension details and permissions";
  "Installation is per-user". "Desktop extension listings in the directory are deprecated, and the
  directory no longer accepts MCPB submissions. To distribute a local MCP server through the directory,
  include it in a plugin." [F19]
- O artigo de suporte: "Desktop extensions support Node.js, Python, and binary MCP servers" e "Claude
  Desktop includes a built-in Node.js environment, so Node.js installation isn't required". Não cita `uv`,
  assinatura, limite de tamanho nem SmartScreen. Sobre macOS: "On macOS, check System Preferences >
  Security & Privacy if you receive security warnings"; sobre Windows e Linux, só permissões de diretórios.
  [F17]
- O artigo de engenharia da Anthropic de 26/06/2025 (2025, anterior ao tipo `uv`): "We ship Node.js with
  Claude Desktop, eliminating external dependencies"; os três tipos (Node.js, Python e binários); exemplo
  Python com `lib/` de pacotes empacotados; bloco `platforms` dentro de `mcp_config` com sobreposições para
  `win32` e `darwin`; "a curated directory of extensions built into Claude Desktop". O resumo não traz
  `uv`, assinatura nem a palavra `platform_overrides`. [F20]
- A página "Decide what to include in your plugin": "A remote server reaches users on every surface. A
  local one runs in Claude Code and in a Cowork session that runs on the user's computer in the desktop
  app, not in chat, so most plugins reference remote servers." Também: "In a plugin, you reference a remote
  MCP server by URL." [F24]

Assinatura e tamanho:

- `mcpb sign` "Signs a MCPB extension file with a certificate"; a assinatura é destacada, de modo que "the
  original ZIP content remains unmodified"; o certificado deve estar em PEM, "Should have Code Signing
  extended key usage" e "Can be self-signed (for development) or CA-issued (for production)"; `verify`
  avisa quando é autoassinado; `unsign` é descrito como para desenvolvimento e teste. [F23]
- A skill `build-mcpb` traz o comando `npx @anthropic-ai/mcpb sign dist/local-files.mcpb` sob "Sign for
  distribution", sem requisitos. [F22]
- O que o Claude Desktop faz com pacote assinado ou não assinado: ausente em [F16] [F17] [F19] [F20] [F23].
  Limite de tamanho do `.mcpb`: ausente nas mesmas fontes (`max_file_size` no `MANIFEST.md` é exemplo de
  `user_config`, não limite do pacote). [F16]

Claude Code e `.mcpb`:

- A referência do manifesto de plugin (consultada em 2026-11-06; cita versões do Claude Code até v2.1.288):
  `mcpServers` aceita "`.mcpb` or `.dxt` bundles"; "Extracts the `.mcpb` or `.dxt` bundle into
  `.mcpb-cache/` under the plugin root and reads its server config"; por URL, "Downloads the bundle into
  `.mcpb-cache/`, then reads it"; "A bundle path or URL must end in `.mcpb` or `.dxt`". A página não
  lista os `server.type` aceitos dentro do bundle. [F18]
- Na mesma página: `claude plugin validate` verifica as entradas de servidor MCP a partir do Claude Code
  v2.1.281; e o diretório `bin/` de plugin: "claude.ai and Cowork don't install a plugin that has this
  directory". [F18]
- Nos primeiros 100000 caracteres da página de MCP do Claude Code, servidores de plugin ficam em `.mcp.json`
  ou inline em `plugin.json` ("Plugins define MCP servers in `.mcp.json` at the plugin root or inline in
  `plugin.json`"), e `.mcpb`/`.dxt` não aparece. [F21]

Terceiros (segunda rodada, só trechos de busca):

- Resumos de terceiros dizem que, no tipo `binary`, o Claude Desktop acrescenta `.exe` no Windows e o
  executável fica em `server/`; que `platform_overrides` fica por sistema (`darwin`, `win32`, `linux`); e
  que o tipo `uv` exige `manifest_version` 0.4. Uma referência de terceiros ainda dá 0.3 como versão
  atual. Nenhum resultado trata de PyInstaller, Nuitka, shiv, wrapper Node para Python ou download de `uv`
  em tempo de execução. [F25]
- Um resumo de terceiros diz que a extensão Filesystem da Anthropic usa `manifest_version` 0.2, `node`
  e depende de `@modelcontextprotocol/server-filesystem`; o manifesto oficial não foi aberto. [F25]
- `mcp2mcpb` (PyPI, descrito como "Convert PyPI/npm MCP servers into one-click .mcpb bundles for Claude
  Desktop"): a página não carregou; o tipo de servidor que gera não foi lido. [F25]

## O que as fontes não cobrem

- **Falta fonte:** se o Claude Desktop embute `uv`. F13 diz "Host application manages Python and
  dependencies automatically" e F3 diz "No user Python installation required", sem dizer quem fornece o
  `uv`; F4 e F6 mostram `uv` não encontrado ou exigido como pré-requisito. Na segunda rodada, F16 diz
  que o host instala as dependências com `uv`, sem dizer quem fornece o `uv`; F17, F19 e F20 só citam
  Node como runtime embutido.
- **Falta fonte:** o suporte do Claude Code ao tipo `uv`. A referência do manifesto de plugin [F18] aceita
  `.mcpb`/`.dxt` mas não lista os tipos de servidor do bundle; nenhuma issue do Claude Code sobre o assunto
  foi encontrada (busca dedicada sem resultado). O único dado é o relato do brief [F15].
- **Falta fonte:** pergunta 6, não pesquisada: a documentação do Cowork sobre sandbox ou VM para ferramentas
  de shell e arquivos; onde rodam os servidores MCP locais e os plugins (host ou sandbox); se o assistente
  instala software ou executa comandos na máquina host, e em que condições; se o servidor local do plugin
  enxerga o PATH do shell de login, `~/` e o navegador do host. A única frase relacionada lida nesta rodada
  é "a Cowork session that runs on the user's computer in the desktop app" [F24], que não menciona sandbox.
  Falta fonte, mais que teste, para (a); para (b) e (c) um teste em máquina limpa também responderia.
- **Falta fonte:** runtime e tipo de servidor de cada entrada do diretório de extensões do Claude Desktop e
  de cada plugin de `claude-plugins-official` (a segunda metade do `marketplace.json` não foi lida, e as
  entradas lidas não mostram `command`).
- **Falta fonte:** `.mcp.json` de plugins de marketplaces comunitários com `uvx` ou binário.
- **Falta fonte:** limite de tamanho do `.mcpb` e do plugin; o que o Claude Desktop faz com pacote assinado
  ou não assinado; quarentena do macOS (Gatekeeper) além da frase genérica sobre "security warnings" [F17];
  SmartScreen/antivírus no Windows. `MANIFEST.md`, o CLI, as páginas do Desktop e o artigo de suporte foram
  lidos e não os tratam [F16] [F17] [F19] [F23]. O exemplo completo de `platform_overrides` não veio no
  resumo de [F16].
- **Falta fonte:** download de binário em tempo de execução, e Python empacotado com PyInstaller, Nuitka,
  shiv ou `uv-pex` em `server.type: binary`, com manifesto real; wrapper Node que invoca ou baixa runtime;
  conteúdo do `mcp2mcpb` (a página do PyPI não carregou). Duas buscas dedicadas não trouxeram exemplo [F25].
- **Falta fonte:** manifestos das extensões do diretório de extensões do Desktop (por exemplo Filesystem);
  só há um resumo de terceiros [F25].
- **Só teste responde:** se o tipo `uv` funciona no Cowork e no Chat com `uv` instalado, e qual `uv` o app
  procura (PATH do app gráfico ou caminho próprio); o spike do brief [F15] cobre parte disso.

## Divergências entre fontes

- **Fechamento da issue 84:** a resposta de 12/03/2026 diz que o v0.4 resolve o problema e recomenda
  fechar; a issue consta como fechada "not planned". [F2]
- **Quem gerencia o Python/`uv`:** "Host application manages Python and dependencies automatically" [F13] e
  "No user Python installation required" [F3] x `'uv' is not recognized` [F4] e `uv` listado como
  pré-requisito do usuário [F6].
- **`mcp_config` no tipo `uv`:** o PR 158 torna `mcp_config` opcional para o tipo [F3]; o manifesto do
  Windows-MCP traz `mcp_config` com `command: "uv"` [F7] e o manager-mcp usou `uv tool run` em
  `mcp_config` [F5].
- **Versão de Python no Windows-MCP:** `compatibility.runtimes.python` `>=3.13` no manifesto [F7] x
  "Python 3.14+" no README e na `long_description` [F6] [F7].
- **Tipos de servidor listados:** `MANIFEST.md` descreve `node`, `python`, `binary` e `uv` [F16] x a skill
  oficial `build-mcpb` e o `mcpb init` listam só Node, Python e Binary [F22] [F23] x o relato do brief de
  que o Claude Code CLI 2.1.317 aceita só `python`, `node`, `binary` [F15].
- **Papel de `server.type`:** `MANIFEST.md` associa a cada tipo requisitos de empacotamento [F16] x a skill
  `build-mcpb` diz que `server.type` é "Informational; the actual launch comes from `mcp_config`" [F22].
- **Python e a máquina do usuário:** a skill diz que o usuário "runs without needing Node, Python, or any
  toolchain" [F22] e o `MANIFEST.md` exige que as dependências do tipo `python` venham no bundle [F16] x o
  campo `compatibility.runtimes.python` do manifesto do Windows-MCP e o README que exige Python 3.14+ [F6] [F7].
- **Plataformas:** a documentação do Desktop diz que ele roda em macOS e Windows [F19], enquanto o
  `MANIFEST.md` e a skill listam também `linux` em `compatibility.platforms` [F16] [F22].
- **Versão do manifesto:** o `MANIFEST.md` lido usa 0.4 para o tipo `uv` [F16]; um resumo de terceiros dá
  0.3 como versão atual e outro exige 0.4 para `uv` [F25].

## Usado em

- Ainda não usado.
