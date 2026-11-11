# Pré-teste de submissão aos diretórios (spec 005, T064a)

**Data**: 2026-11-10. **Nada foi submetido**: nenhuma conta criada, nenhum envio feito. Este
documento compara o que os diretórios pedem com o estado do projeto na `develop` e lista
o que precisaria mudar. A fonte de cada requisito está em
[`docs/research/fichamentos/diretorios-de-plugins-e-registries-requisitos.md`](../../docs/research/fichamentos/diretorios-de-plugins-e-registries-requisitos.md)
(IDs F1 a F10). Abaixo, **fato** é o que a fonte diz ou o que se mediu no repositório;
**avaliação** é leitura nossa e pede decisão do mantenedor. A política, os Termos e o trecho de
finanças da Usage Policy foram lidos na íntegra em 10/11/2026.

Escopo: serve para decidir a reabertura da FR-030 (critérios no `docs/ROADMAP.md`). Qualquer
envio real continua fora da spec 005.

## O que se mediu localmente

| Verificação | Resultado |
|---|---|
| `claude plugin validate ./plugin` | Passa, com 1 aviso: sem ícone (`ICON_MISSING`) |
| `claude plugin validate .` (marketplace) | Passa, com 2 avisos: sem descrição do marketplace, sem `author` no plugin |
| Pasta `plugin/` | 15 arquivos, 60 KB, sem `.DS_Store`, sem link simbólico, sem `bin/` |
| `plugin/README.md` | **Não existe** (o README fica na raiz do repositório) |
| `license` no `plugin.json` | `MIT` presente; `LICENSE` na raiz |
| Repositório no GitHub | Público; **sem descrição, sem tópicos, sem página inicial** |
| `gemini-extension.json` na raiz do repositório | **Não existe** (fica em `plugin/`) |

## Diretório da Anthropic (portal do desenvolvedor)

Quem submete: conta paga do Claude, conta GitHub conectada com push no repositório (F2).
Caminho do plugin a informar: `plugin`. Branch ou tag acompanhada: `main` (só recebe versões
já publicadas, ADR-0020) ou uma tag.

| # | Requisito (fonte) | Estado atual | Resultado previsto | Lacuna e artefato | Esforço |
|---|---|---|---|---|---|
| A1 | README de 40 palavras ou mais na pasta do plugin (F1) | Não existe em `plugin/` | **Bloqueia** | Criar `plugin/README.md` descrevendo o que o plugin executa, envia e busca | Baixo |
| A2 | `author`, `description`, `version` (F1) | Falta `author`; os outros existem | Aviso | `author` em `plugin/.claude-plugin/plugin.json` | Baixo |
| A3 | Ícone PNG quadrado de 512 a 2048 px, até 2 MB (validador); só vale na primeira submissão (validador) | Não existe | Aviso | Desenhar o ícone e adicioná-lo **antes** da primeira submissão | Baixo a médio (arte) |
| A4 | Launcher com pacote fixado em versão exata (F1) | `uvx --from …==<versão>` fixado | Passa esse bloqueio, mas **retém para revisor** em toda versão ("Runs a pinned npx or uvx package") | Nenhuma: a retenção é inevitável com `uvx`. Cada versão do plugin passa por revisor | Nenhum, mas **cadência**: lançamento no diretório deixa de ser imediato |
| A5 | Script de hook sem substituição de comando nem variáveis (F1) | `stop-memory-reminder.sh` usa `$(cat)` e variáveis | **Retém para revisor** ("Scripts the validator couldn't follow") | Reescrever o hook sem substituição de comando, ou aceitar a retenção | Médio |
| A6 | Caminhos de hook em `${CLAUDE_PLUGIN_ROOT}`, sem outra variável (F1) | `cat "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.json"` e `bash "${CLAUDE_PLUGIN_ROOT}/hooks/stop-memory-reminder.sh"` | Passa | Nenhuma | Nenhum |
| A7 | Sem `.mcpb`, sem `bin/` (F1, F4) | Nenhum dos dois | Passa | Nenhuma | Nenhum |
| A8 | Nome sem coincidir com marca conhecida; nome, `displayName` e `author.name` que não confundam; nada que apresente o plugin como oficial (F1) | Nome `investidor10-carteira`, `displayName` "Carteira Investidor10": **usam o nome do site do Investidor10, que não é nosso** | **Retém para revisor** ("Name matches a known brand"); risco maior de recusa (F5 §1F, §2C) | Decisão do mantenedor: renomear o plugin (o nome é permanente e há instalações 0.3.x e 0.4.x, exige `renames` no marketplace) ou obter autorização do titular da marca | Médio a alto, mais decisão |
| A9 | Código legível, README que descreve tudo que o plugin executa, envia ou busca (F1) | Código legível; o README do plugin não existe | Depende de A1 | Descrever no `plugin/README.md` a API do Investidor10, a página local em `127.0.0.1` e a memória em disco | Baixo |
| A10 | Formulário de tratamento de dados e e-mail de contato (F2) | Sem respostas preparadas | Preenchimento manual | Preparar as respostas a partir de `docs/PRIVACY.md`: lê dados financeiros pessoais; envia o ID e a credencial ao `investidor10.com.br`; memória local sem prazo de expiração; não é para menores de 18 anos | Baixo |
| A11 | Termos e Política do Software Directory (F2, F5, F11) | **Lidos na íntegra em 10/11/2026**; leitura contra o projeto na tabela abaixo | Ver P1 a P11 | — | — |
| A13 | Anotações das tools: `readOnlyHint`, `destructiveHint` e `title` em todas (F5 §5E) | **19 das 20 tools não declaram `readOnlyHint` nem `destructiveHint`**; só `open_wallet_setup` declara. Os 20 nomes têm título | Descumpre a regra; vale para qualquer diretório de servidores | Anotar as 19 tools (leitura: `readOnlyHint` verdadeiro; gravação na memória: `destructiveHint` falso), com teste de contrato. Também evita pedido de permissão a cada chamada de leitura nos clientes | Baixo |
| A12 | Superfícies (F4): hooks e agentes ignorados no Chat; servidor local só no Cowork no computador | O produto já documenta a limitação do Chat | Coerente | Nenhuma; o portal mostra as superfícies antes de submeter | Nenhum |

### A política lida na íntegra (F5, F11, F12): o que passa e o que bloqueia

Texto literal no fichamento. A coluna "Leitura" é avaliação nossa: a política não traz exemplos
nem interpretação, então a decisão final é do revisor da Anthropic.

| # | Regra | Estado do projeto | Leitura |
|---|---|---|---|
| P1 | **3F**: "Developers must verify that they own or control any API endpoint, domain, or user interface their Software connects to, as well as any external resources it retrieves or renders. Plugins are an exception, and may connect to any Connector approved in the Software Directory." | O servidor MCP, que vai dentro do plugin, chama a API interna do Investidor10 (ADR-0005), que **não é nossa e não é um Connector aprovado** | **Bloqueio provável.** A exceção de plugins só cobre Connectors aprovados no diretório. É fato que a regra existe e que, lida literalmente, nos alcança |
| P2 | **1G**: não "persistently store or use conversation content to build user profiles or attempt to make any changes to Claude's behavior across sessions" | A memória guarda teses, regras e decisões e o `get_session_context` as devolve a cada sessão para orientar o agente. É o diferencial do produto | **Bloqueio possível, e central.** A regra não abre exceção para consentimento nem para dado local. O que atenua: o usuário escreve e confirma cada item, e o arquivo é dele |
| P3 | **1B** com a AUP, finanças: "a personalized recommendation to buy, sell, hold, or allocate among specific investment products" exige "a qualified person" que revise antes de virar conselho, e aviso de uso de IA | O produto "sugere e analisa, nunca executa ordens" (persona); o guardião "nunca recomenda ordens de compra ou venda"; as skills comparam a carteira com as regras do próprio usuário "sem recomendar" | **Risco médio.** O texto do projeto evita a recomendação personalizada, mas a persona usa "sugere"; um revisor pode enquadrar como alto risco, caso em que exigiria pessoa qualificada, inviável aqui. Mitigação: reescrever a persona e declarar na listagem que não há recomendação |
| P4 | **Termos**: o desenvolvedor garante que "has and will maintain all necessary rights to provide your Software to users" | Sem autorização do Investidor10 para o uso da API; ADR sobre os termos de uso pendente (critério 3 da FR-030) | **Pendente**: mesmo ponto da P1, do lado jurídico |
| P5 | **1F** e **2C**: não infringir propriedade intelectual; não confundir com outro software | O plugin e o nome usam a marca do Investidor10 (A8) | Risco de recusa pelo nome |
| P6 | **3A**: link de política de privacidade, inclusive de terceiros | `docs/PRIVACY.md` existe, mas precisa de endereço público e de cobrir a API de terceiros e o armazenamento local | Ajuste de texto |
| P7 | **3B**, **3C**, **3E**: contato verificado, documentação, três exemplos de prompt | Há README, INSTALACAO-DESKTOP e `PRIVACY.md`; faltam contato e exemplos formalizados | Baixo esforço |
| P8 | **3D**: "a standard testing account with sample data" | Há carteira fictícia (pública e restrita) usada nos roteiros | Passa, se a carteira de teste continuar no ar e puder ser entregue ao revisor |
| P9 | **3H**: notificar mudanças de endpoint, de descrições e de práticas de dados | A API pode mudar sem aviso (ADR-0005) | Processo contínuo a assumir |
| P10 | **2F** e **2G**: não puxar instruções de fonte externa; sem instruções "hidden, obfuscated, or encoded" | O `get_session_context` devolve regras do arquivo **local** do usuário; `session-start.json` usa escapes `\u` | Risco baixo; os escapes decodificam para texto legível, mas um verificador automático pode estranhar |
| P11 | **4A** e **5A**, **5B**, **5C**, **5G** | Só leitura, sem mover dinheiro; erros estruturados; nomes de tool de até 23 caracteres; dependências com `audit` no CI | Passa. Ressalva em 5B: respostas repassam o payload da fonte, que pode ser grande |

**Resposta direta às perguntas do mantenedor**

- *"É fato que temos que controlar a API?"* Para o diretório da Anthropic, sim: é a regra 3F, e o
  texto acima é literal. Não há exceção para "API pública sem autenticação" nem para API de terceiros.
  A única exceção é plugin que se conecta a um Connector aprovado no diretório.
- *"Passamos?"* Na forma, falta pouco (README do plugin, `author`, ícone, anotações das tools).
  No fundo, a P1 e a P2 são os dois pontos em que a leitura literal da política nos bloqueia, e a P3 é um risco.

## Registry oficial de servidores MCP (fonte oficial, F13)

**Formalmente não bloqueia.** As páginas oficiais lidas não trazem política de conteúdo, nem
exigem posse de API de terceiros; o registry só guarda metadados e confere que o publicador é
dono do nome e do pacote.

| # | Requisito | Estado atual | Lacuna e artefato | Esforço |
|---|---|---|---|---|
| R1 | `server.json` com nome `io.github.<usuário>/…`, pacote `pypi` e transporte `stdio` | Não existe | Criar `server.json` | Baixo |
| R2 | `mcp-name: <nome>` no README do pacote publicado no PyPI (pode ser comentário) | Não existe | Acrescentar ao `README.md`; muda o **pacote publicado**, então só entra numa nova versão | Baixo, amarrado a um release |
| R3 | Versão do `server.json` igual à do PyPI; versão publicada é imutável | — | Passo extra no fluxo de release | Baixo |
| R4 | Login com a conta do GitHub (`mcp-publisher login github`) | Conta existe | Passo manual do mantenedor | Baixo |

**Cuidados**: o registry está em preview, **não permite apagar nem despublicar** ("Currently, no") e
a versão é imutável. Publicar é permanente. O risco jurídico da API de terceiros (P4) continua
nosso, mesmo que o registry não o cobre. O PulseMCP está com envios pausados e coletará do registry
oficial quando reabrir (página oficial).

## Outros diretórios

| Diretório | O que pede (fonte) | Estado atual | Lacuna e artefato | Esforço |
|---|---|---|---|---|
| Galeria do Gemini CLI | Repositório público, tópico `gemini-cli-extension`, `gemini-extension.json` na **raiz** (F6); não há submissão | Repositório público; **sem tópico; manifesto em `plugin/`** | Tópico no repositório e manifesto na raiz (ou arquivo de release). **Também** o assistente instala o Gemini pela URL da raiz do repositório: conferir que isso realmente carrega o manifesto de `plugin/` | Baixo a médio |
| Codex | Sem diretório público de submissão confirmado (F9); marketplace por Git funciona | `codex plugin marketplace add` já é o caminho usado | Acompanhar a abertura do diretório; entradas em listas comunitárias por PR, se desejado | Nenhum agora |
| Devin | Distribuição por repositório (`dono/repo#subcaminho`) e por administrador (F10); sem registry público encontrado | Instalação por `#plugin` já usada | Referência completa do manifesto não aberta | Nenhum agora |
| Smithery | **Encerrou em 2026-10-31** as contas, as chaves de API, a CLI e os SDKs; segue só como registry público **curado** de servidores verificados, com a URL MCP direta do fornecedor (página oficial `smithery.ai/future`); as páginas de documentação de publicação respondem 404 | Sem conta e sem CLI para publicar; nosso servidor também não tem URL | **Sem caminho de submissão por conta própria hoje.** Não é bloqueio de política, é que o serviço de publicação não existe mais. Só a curadoria deles poderia incluir o servidor, e não há página que diga como pedir | Não aplicável |
| PulseMCP | Envios pausados; pede publicar no registry oficial (página oficial) | — | Depende de R1 a R4; sem critérios listados | — |

## Resumo

**Diretório da Anthropic: bloqueado pela leitura literal da política em dois pontos de fundo**
(P1 posse do endpoint, P2 memória persistente) e com um risco (P3, finanças), além de lacunas de forma.
Isso não se resolve com arquivo: depende de decisão sobre a arquitetura, de autorização do
Investidor10, ou de consulta escrita à Anthropic (`directory@anthropic.com` é o canal citado nas docs
para submissões em conflito; a política só prevê exceção escrita na seção 4, não nestas regras).

**Registry oficial e, por consequência, PulseMCP: sem bloqueio formal.** Pede `server.json`, o
marcador no README do PyPI e um release; a publicação é permanente.

**Smithery: sem caminho de submissão.** Em 31/10/2026 ele encerrou contas, CLI e SDKs e virou registry curado (página oficial `smithery.ai/future`).

**Lacunas de forma, baixo esforço e sem decisão**: `plugin/README.md` (A1, A9), `author` (A2), ícone
(A3), **anotações das 19 tools (A13)**, respostas do formulário de dados (A10), política de privacidade
pública (P6), contato e exemplos de prompt (P7), `server.json` e marcador (R1 a R3), tópico e descrição
do repositório no GitHub.

**Decisões do mantenedor antes de qualquer submissão**: nome e marca (A8, P5); como tratar a P1 e a
P4 (autorização do Investidor10); como apresentar ou ajustar a memória diante da 1G (P2); a persona
diante da 1B (P3); aceitar a revisão humana em toda versão (A4, A5).

**Fora de alcance hoje**: submissão pública do Codex.

## O que este pré-teste não cobre

Não houve submissão, nem o botão Validate do portal (exige conta com plano pago e GitHub
conectado); então os resultados "previstos" vêm da leitura das tabelas oficiais (F1) e da
política (F5), não de uma execução. A revisão humana pode concluir diferente da nossa leitura. O primeiro passo real e sem efeito público seria rodar **Validate** no portal,
que só valida e não publica; isso pede decisão do mantenedor.
