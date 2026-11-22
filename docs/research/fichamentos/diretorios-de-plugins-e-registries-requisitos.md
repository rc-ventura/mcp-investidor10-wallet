# Fichamento: requisitos dos diretórios de plugins e dos registries de servidores MCP

- **Pesquisado em**: 2026-11-10
- **Atualizado em**: 2026-11-10
- **Origem**: spec 005, T064a (pré-teste de submissão, sem submeter nada)

## Por que esta pesquisa

O mantenedor quer saber que ambiente e que artefatos o projeto precisaria ajustar
para enviar o plugin e o servidor ao diretório oficial da Anthropic e aos principais
diretórios. Este fichamento só registra o que as fontes dizem. A comparação com o
projeto está em `specs/005-desktop-distribution/directory-preflight.md`.

## Perguntas

1. Como se submete ao diretório de plugins da Anthropic e o que a validação e a varredura exigem?
2. O que a política do diretório diz sobre dados, APIs de terceiros e finanças?
3. Como se publica no registry oficial de servidores MCP, no Smithery e no PulseMCP?
4. Como a galeria de extensões do Gemini CLI, o Codex e o Devin listam plugins de terceiros?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Plugin pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist.md) | Oficial | 2026-11-10 |
| F2 | [Submit your plugin](https://claude.com/docs/plugins/submit.md) | Oficial | 2026-11-10 |
| F3 | [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish.md) | Oficial | 2026-11-10 |
| F4 | [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support) | Oficial | 2026-11-10 |
| F5 | [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy) | Oficial, **texto integral lido** (HTML baixado) | 2026-11-10 |
| F11 | [Anthropic Software Directory Terms](https://support.claude.com/en/articles/13145338-anthropic-software-directory-terms) | Oficial, texto integral lido | 2026-11-10 |
| F12 | [Usage Policy (AUP)](https://www.anthropic.com/legal/aup), seção de casos de alto risco | Oficial, trecho lido | 2026-11-10 |
| F13 | [MCP Registry: quickstart, package types e FAQ](https://modelcontextprotocol.io/registry/quickstart) | Oficial | 2026-11-10 |
| F6 | [Release extensions (Gemini CLI)](https://geminicli.com/docs/extensions/releasing/) | Oficial | 2026-11-10 |
| F7 | Guias sobre o MCP Registry (composio.dev, stackone.com, glama.ai) | Secundária (superada por F13) | 2026-11-10 |
| F8 | [PulseMCP submit](https://www.pulsemcp.com/submit) | Oficial | 2026-11-10 |
| F14 | [The future of Smithery](https://smithery.ai/future) e página inicial do Smithery | Oficial | 2026-11-10 |
| F9 | [Codex plugins](https://developers.openai.com/codex/plugins/build.md) e guias de terceiros | Mista | 2026-11-10 |
| F10 | [Devin plugins](https://docs.devin.ai/product-guides/plugins.md) | Oficial | 2026-11-10 |

A F5, a F11 e a F12 foram lidas no texto publicado. A F13 e a página do PulseMCP foram abertas.
As F9 (Codex) vieram de resumos de busca e estão marcadas como não confirmadas.

## Achados

### Diretório de plugins da Anthropic (F1, F2, F3)

- Submissão pelo portal do desenvolvedor em `claude.ai/directory/manage`, a partir de um
  repositório GitHub, escolhendo "Plugin bundle". Exige plano pago (Pro, Max, Ultra; em
  Team e Enterprise, o Owner ou o papel com a permissão Directory) e a conta GitHub
  conectada, com permissão de push no repositório. O repositório pode ser privado ao
  submeter e precisa ser público para a listagem entrar no ar (F2).
- Cada pasta de plugin é uma submissão; um repositório com vários plugins submete um por
  vez, com o caminho da pasta que contém `.claude-plugin/plugin.json`. Uma submissão por
  repositório e pasta; até 10 submissões por 24 h por organização (F2).
- O diretório acompanha uma branch ou tag e confere novos commits por agenda e, se
  configurado, por webhook de push; versões que passam são publicadas conforme a
  configuração de publicação (por padrão, um revisor da Anthropic publica cada versão) (F2).
- `claude plugin validate` só confere se os arquivos estão bem formados; o botão
  Validate do portal confere as regras do diretório (F1). Resultados: **Blocks**
  (impede submeter), **Held for a reviewer** (revisor lê antes de entrar no ar),
  **Warning**, **Note** (F1).
- Regras de **Blocks** relevantes: README de pelo menos 40 palavras na pasta do plugin
  (palavras em blocos de código não contam); `LICENSE` na pasta ou `license` no
  `plugin.json`; pacote de launcher (`uvx`, `npx`…) fixado em versão exata; sem credencial
  real em arquivo; caminhos de hook e de servidor MCP em `${CLAUDE_PLUGIN_ROOT}`, sem
  outra variável, substituição de comando, curinga ou programa inline; sem arquivos
  `.DS_Store`; nome sem caracteres fora do ASCII (F1).
- Regras de **Held for a reviewer** relevantes: um launcher que roda pacote fixado
  (`uvx pacote==X`) é sempre retido, "porque as dependências do pacote resolvem na
  instalação"; script de hook ou servidor que usa substituição de comando, variáveis
  além de `${CLAUDE_PLUGIN_ROOT}` ou chama outros arquivos; arquivos binários que não
  sejam texto, imagem ou fonte; arquivo não-imagem acima de 256 KiB; mais de 512
  arquivos; nome que coincide com marca conhecida ou que pode ser confundido com outra
  listagem; `displayName` e `author.name` idem (F1).
- **Warning**: `description`, `author` e `version` ausentes; nome fora do padrão (F1).
- Regras de nome: nome construído sobre o nome próprio do produto, sem palavras
  reservadas inteiras (`claude`, `anthropic`, `official`, `plugin`, `mcp`, `test`) e
  "nada que apresente o plugin como oficial"; o nome é permanente porque instalações
  existentes ficam registradas por ele (F1, F3).
- A varredura de segurança procura comportamento não divulgado (envio de dados a destino
  não declarado, código oculto, mudança de permissões). Uma primeira submissão que falha é
  rejeitada. O README deve descrever tudo o que o plugin executa, envia ou busca, e o
  código deve ser legível, não compilado ou minificado (F1).
- O portal pergunta sobre tratamento de dados: se lê ou guarda dados pessoais, se envia
  dados a serviços diferentes dos conectores declarados, por quanto tempo retém, se é
  para menores de 18 anos; e pede e-mail de contato e quatro confirmações (F2).
- O ícone: o validador do Claude Code procura `icon` no `plugin.json` ou um arquivo em
  `.claude-plugin/icon.png` ou similar, PNG ou JPEG quadrado de 512 a 2048 px e até 2 MB;
  esse arquivo pode virar o ícone da listagem apenas na primeira vez que o plugin é salvo
  ou submetido no portal (saída do `claude plugin validate` em 2026-11-10).
- O marketplace oficial `claude-plugins-official` não recebe submissões pelo portal;
  é por contato de parceiro (F3).
- Um plugin listado aparece no Claude Code do usuário como `<nome>@synced` (F3).
- Se o plugin referencia um servidor MCP **remoto** do autor, ele deve ser submetido
  também como conector MCP (F2).

### Superfícies (F4)

- Skills carregam no Chat, no Cowork e no Claude Code.
- Agentes e hooks: ignorados no Chat; carregam no Cowork e no Claude Code.
- Servidor MCP local (comando que o app inicia): ignorado no Chat; carrega no Cowork
  quando a sessão roda no computador do usuário, e no Claude Code.
- Diretório `bin/` no topo do plugin: não pode ser instalado no Chat nem no Cowork.
- O portal mostra as superfícies que o plugin suporta antes de submeter (F4).

### Política do diretório (F5, texto integral)

Definição: "Software" é "Model Context Protocol servers, Skill folders, plugins, apps, and
other software, containers, or data". A seção 2 vale para "Instructional Software" (servidores
MCP, Skill folders e similares); a seção 5 vale para servidores MCP, locais e remotos.

- **1A**: o software não pode violar nem facilitar violação da Usage Policy, "including
  high-risk use cases around legal, healthcare, insurance, finance and other areas".
- **1B**: "When Software is providing a high-risk use case, Developers must comply with the
  human-in-the-loop measures and provide direct disclosure to consumers (as detailed in our
  AUP)".
- **1D**: proteger a privacidade do usuário e de terceiros. **1E**: coletar só o necessário e
  nenhum dado extra de conversa, "even for logging purposes".
- **1F**: "must not infringe on the intellectual property rights of others".
- **1G**: "Software must not query or extract data from Claude's memory, chat history,
  conversation summaries, or user-generated or uploaded files and must not persistently
  store or use conversation content to build user profiles or attempt to make any changes
  to Claude's behavior across sessions."
- **2B**: descrições "must precisely match actual functionality" e não prometer o que não
  entrega. **2C**: não criar confusão com outro software dos diretórios. **2D** a **2F**: não
  induzir Claude a chamar outros softwares sem o usuário pedir; não direcionar Claude a
  "dynamically pull behavioral instructions from external sources". **2G**: "must not contain
  hidden, obfuscated, or encoded instructions. All behavioral guidance must be human-readable".
- **3A**: link de política de privacidade para software que coleta dados ou conecta a serviço
  remoto, e links de todas as políticas aplicáveis. **3B**: contato verificado e canais de
  suporte. **3C**: documentar funcionamento, propósito e solução de problemas.
- **3D**: "a standard testing account with sample data for Anthropic to verify full Software
  functionality". **3E**: "at least three working examples of prompts or use cases".
- **3F**: "Developers must verify that they own or control any API endpoint, domain, or user
  interface their Software connects to, as well as any external resources it retrieves or
  renders. Plugins are an exception, and may connect to any Connector approved in the
  Software Directory."
- **3G**: manter o software. **3H**: notificar a Anthropic sobre mudanças materiais de
  funcionalidade, descrições, práticas de dados ou "connected endpoints"; podem ter nova
  revisão. **3I**: aceitar os Termos e as diretrizes de design.
- **4A**: não permitido software que transfere dinheiro ou executa transações financeiras de
  forma autônoma sem proteção com humano no circuito; "We do not generally allow
  cryptocurrency software". A seção 4 abre exceção só por permissão expressa e escrita.
- **5A**: erros úteis. **5B**: ser econômico em tokens, com opção de excluir texto
  desnecessário quando possível. **5C**: nomes de tool de até 64 caracteres. **5E**: "MCP servers
  must provide all applicable annotations for their tools, in particular readOnlyHint,
  destructiveHint, and title". **5G**: servidores MCP locais com dependências razoavelmente atuais.

### Termos do diretório (F11, texto integral)

- Ao submeter, o desenvolvedor declara e garante que "(i) you have and will maintain all
  necessary rights to provide your Software to users"; que o software "complies with all
  applicable laws and regulations and does not violate Anthropic's Software Directory Policy";
  que as informações são exatas; e que, se coleta ou compartilha dados pessoais, terá
  política de privacidade e fornecerá as políticas de terceiros aplicáveis.
- Concorda em indenizar a Anthropic por reclamações ligadas ao software ou ao uso dele;
  licencia descrições, documentação, nome, marcas e logos para a exibição nos diretórios;
  autoriza a Anthropic a revisar e testar o software.
- A Anthropic pode remover ou recusar qualquer software "at any time for any reason".
- O desenvolvedor mantém um canal para receber relatos de vulnerabilidade.
- O texto não fala de termos de uso de serviços de terceiros nem de posse de endpoint.

### Usage Policy, alto risco em finanças (F12)

- "Finance — a personalized recommendation to buy, sell, hold, or allocate among specific
  investment products, such as securities, funds, digital assets, or annuities; advising an
  individual on their own taxes...; or preparing a tax return".
- Controles exigidos: "Qualified human-in-the-loop for advice and decisions — A qualified
  person must meaningfully review a High-risk AI Recommendation, with the authority to change
  or modify it, before it is delivered as advice to an individual who might rely on it";
  "Disclosure for advice and decisions" (a pessoa deve ser informada de que IA foi usada).
  "A qualified person is someone with the training or experience to evaluate the output in
  that field, and who holds a license where applicable law requires one."

### Registry oficial de servidores MCP (F13, oficial; em preview)

- O registry "only hosts metadata, not artifacts": o pacote é publicado antes no npm, no PyPI,
  no NuGet, em crates.io, em registry de imagens OCI ou como MCPB. Publica-se com a CLI
  `mcp-publisher` (`init`, `login`, `publish`) e um `server.json`.
- Nome em namespace; com login pelo GitHub, o nome deve começar com `io.github.<usuário>/`.
- PyPI: a posse é verificada pela string `mcp-name: <nome>` no README do pacote (que vira a
  descrição no PyPI); pode ficar em comentário, e o nome deve ser igual ao do `server.json`.
  O transporte do exemplo é `stdio`.
- Versão publicada é imutável; atualiza-se com um novo `server.json` de versão única.
- FAQ: não é possível apagar nem despublicar um servidor ("Currently, no"). Abusos são
  denunciados ao registry do pacote e por issue no repositório do registry.
- As páginas lidas não trazem política de conteúdo nem exigem posse de API de terceiros.

### Smithery e PulseMCP (F8)

- PulseMCP (oficial): "We are not accepting new MCP server or client submissions right now";
  recomenda publicar no registry oficial, "the best first step even when we are not paused",
  e diz que pegará o servidor automaticamente quando reabrir. Não lista critérios.
- Smithery (F14, oficial): o site diz "now part of Arcade". Em 2026-10-31 encerrou "Smithery's connection
  management services": URLs `run.tools` e `server.smithery.ai`, "Smithery API, Connect, and Toolbox",
  "Smithery accounts and API keys" e "The Smithery CLI and SDKs" (versões marcadas como obsoletas).
  Permanece como "a public (non-proxied) MCP registry", "a curated set of verified servers", com as
  páginas mostrando a URL MCP direta do fornecedor. As páginas de documentação de publicação
  (`/docs/build/publish` e outras) respondem HTTP 404. Uma busca anterior citava `smithery mcp publish`;
  essa via depende do CLI e das contas que o próprio site diz ter encerrado.

### Gemini CLI (F6)

- A galeria indexa sozinha repositórios públicos do GitHub: não há submissão. Pede
  repositório público, o tópico `gemini-cli-extension` e o `gemini-extension.json` na
  **raiz** do repositório ou do arquivo de release; a galeria confere os repositórios
  marcados por dia.

### Codex (F9, mista)

- A documentação oficial descreve marketplace por repositório Git
  (`codex plugin marketplace add dono/repo`) e publicação por workspace para administradores,
  que não lista o plugin no diretório público. Um blog de maio de 2026 diz que a
  publicação self-serve no diretório oficial ainda não existia; um guia de terceiros
  descreve upload de ZIP por um portal, não confirmado pela OpenAI.
- Há listas comunitárias que aceitam plugins por pull request.

### Devin (F10)

- Plugin é um diretório com `.devin-plugin/plugin.json` (cai para `.claude-plugin/plugin.json`
  quando não há o do Devin). A instalação por GitHub aceita `dono/repo#subcaminho`.
- A distribuição descrita é por repositório e por administrador da organização (lista de
  plugins obrigatórios no manifesto gerenciado) ou por upload de pasta ou ZIP; não foi
  encontrado um registry público para submissão. A referência completa do manifesto não
  foi aberta.

## Lacunas

- Não há, nas páginas oficiais atuais do Smithery, um caminho de submissão por conta própria; não se sabe se a curadoria aceita indicações.
- Referência completa do manifesto do Devin e da publicação no Codex não abertas.
- Não se sabe como a revisão da Anthropic aplica a 1G, a 3F e a 1B a um plugin com servidor
  local; o texto da política é o que está acima e não traz exemplos nem interpretação.
