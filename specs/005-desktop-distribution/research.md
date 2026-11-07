# Research — Spec 005 (Distribuição Desktop)

Fontes consultadas em 31/10 e 01/11/2026. Cada decisão segue o formato
Decision / Rationale / Alternatives. Fonte não oficial aparece marcada como
tal e nunca sustenta sozinha uma decisão (Constituição I).

## Estado atual verificado no código

- O plugin é só de comportamento: nenhum manifesto em `plugin/` declara
  servidor (`plugin/.claude-plugin/plugin.json`, `.codex-plugin`,
  `.devin-plugin`, `gemini-extension.json`), por decisão do ADR-0012 §2.
- O servidor recebe a carteira pela variável `WALLET_ID` e aborta sem ela
  (`bootstrap.py:118-122`); o assistente preenche a variável em cada cliente
  (`installer/clients.py`, `add_command` dos quatro adaptadores).
- O cliente HTTP já não segue redirecionamento (`follow_redirects=False`,
  `wallet_client.py:242`), mas trata qualquer status `< 400` como sucesso e
  lê o corpo: o HTTP 301 "Acesso não autorizado" vira `unexpected_format`
  ("non-JSON body"), o diagnóstico enganoso da US2.
- A sonda de inicialização (`validate_wallet`) só distingue 200, 404 e
  401/403; o 301 cai em "fonte indisponível" e o servidor sobe mesmo assim.
- O hook de início de sessão roda `bash "${CLAUDE_PLUGIN_ROOT}/..."`, o que
  falha no Windows sem Git for Windows (o app usa PowerShell).

## D1 — Runtime do servidor dentro do plugin

Nota de leitura: aqui o `.mcpb` é só a embalagem interna do servidor
dentro do plugin. O usuário instala um plugin só, em Customize > Plugins, e
configura na página local (D4); ele não vê, não baixa e não abre o `.mcpb`. Isso
não é a opção A descartada na clarificação (extensão avulsa em Settings >
Extensions com formulário).

**Decision**: o manifesto Claude do plugin aponta `mcpServers` para um
pacote MCPB versionado dentro do próprio plugin,
`plugin/servers/carteira.mcpb`, do tipo `server.type: "uv"`
(`manifest_version` 0.4). O pacote **não leva o código**: seu `pyproject.toml`
depende de `mcp-investidor10-wallet==<versão>` do PyPI, e o app instala Python
e dependências com uv. O pacote é gerado de forma determinística por um script
do repositório, commitado, e só muda no PR de release. A CI falha se `plugin/`
mudar sem subir a versão.

A **primeira tarefa da implementação é um spike de verificação** (S1, ver
quickstart): instalar um plugin de teste com um MCPB `uv` mínimo numa
máquina limpa, em macOS e Windows, e checar (a) se uma sessão Cowork do
Claude unificado inicia o servidor e lista as tools, sem passo extra na aba
Connectors; (b) se o Claude Code CLI inicia o mesmo servidor a partir do plugin
sincronizado ou instalado, inclusive no Linux; (c) se o servidor abre o
navegador e grava em `~/` no computador; (d) qual branch o Desktop lê por padrão ao adicionar o marketplace e se Add
marketplace aceita `dono/repo#ref`; (e) qual forma do nome das tools funciona na lista `tools` de
um subagente de plugin. O resultado vira learning lesson. Se só o Linux falhar,
o assistente mantém ali o registro pelo terminal.

Árvore de decisão do spike:

1. Funciona no Cowork e no Claude Code: segue D1.
2. Falha em algum dos dois: MCPB `server.type: "binary"` com executável
   por plataforma (`platform_overrides` do manifesto), gerado na CI e
   publicado como asset da release; o plugin aponta o `mcpServers` para a
   URL `https://` do asset da versão. Exige reabrir a análise de tamanho
   (limite de 200 MB por plugin) e da quarentena do macOS.
3. Ambos falham: `command: "uvx"` com o uv como pré-requisito documentado e
   detectado pelo `doctor`; a FR-002 volta ao mantenedor antes de seguir
   (FR-003).

**Rationale**:

- "Local MCP server, a command the app starts, including `.mcpb` bundles —
  Cowork: Loads when the Cowork session runs on your computer" (Plugin
  feature support across platforms).
- "The `mcpServers` key also accepts a packaged server as an MCPB file
  [...] Point the key at the file, as a path inside the plugin or an
  `https://` URL" (Claude Code, Add components to a plugin).
- Tipo `uv`: "Python server using UV runtime (v0.4+)", dependências
  "installed by the host application using UV", "No user Python
  installation required", "Must include `pyproject.toml`", "Must NOT
  include `server/lib/` or `server/venv/`" (MCPB MANIFEST.md). O mesmo
  documento não diz se o app traz o próprio uv e marca o tipo como
  experimental, por isso o spike é obrigatório.
- Comando simples não serve ao usuário leigo: "Give `command` as a program
  name on `PATH` or an absolute path" (Desktop 3P, MCP, plugins, skills,
  and hooks); o app embarca Node.js, não Python ("Included with Claude
  Desktop on macOS and Windows", Build a desktop extension with MCPB); e
  apps gráficos no macOS não herdam o PATH do shell (fonte não oficial:
  guia de troubleshooting do unity-mcp, coerente com a causa nº 1 de "MCP
  failed to connect" já registrada no roadmap).
- Apontar para o PyPI mantém o ADR-0011 ("PyPI é o único canal") para o código:
  o que roda é o wheel testado na release, e merges em `main` não chegam ao
  usuário. O pacote fica com poucos KB. Custo aceito: quem atualizar entre o
  merge da release e a publicação vê falha por alguns minutos.
- A regra de versão atende a documentação: com `version` definido, quem já tem
  o plugin só atualiza quando ela muda (Publish and distribute a plugin), mas
  uma instalação nova recebe o conteúdo atual da branch. O Cowork "pull[s] the
  latest plugins" do repositório, sem dizer se respeita a versão (Install
  plugins).

**Alternatives considered**:

- Extensão `.mcpb` avulsa (Settings > Extensions) mais plugin de
  comportamento: descartada na clarificação de 01/11/2026 (sem
  documentação de que aparece nas sessões unificadas; duas instalações).
- MCPB `python` com dependências em `server/lib`: exige Python no sistema
  do usuário (`compatibility.runtimes.python`), mesmo problema do `uvx`.
- Executável único (`binary`) como primeira opção: dezenas de MB por
  plataforma, build por sistema na CI, assinatura e quarentena do macOS;
  fica como reserva do spike.
- Código dentro do pacote: dispensa o PyPI nesse caminho, mas cria um segundo
  canal de código, fora do teste do wheel, e pede emenda maior do ADR-0011.
- Reescrever o servidor em Node para usar o runtime do app: reescrita do
  produto inteiro, fora de proporção.

## D2 — Configuração local única

**Decision**: a configuração da carteira sai da variável de ambiente para o
arquivo `~/.investidor10/config.json`, no mesmo diretório canônico da
memória (0700), com permissão 0600, aberto por descritor com `O_NOFOLLOW`
pelo mesmo ponto único de abertura da memória e gravado de forma atômica
(arquivo temporário + `os.replace`). Esquema em data-model.md. Regras:

- O servidor relê o arquivo quando a identidade dele muda (inode, tamanho,
  `mtime_ns`), conferida no início de cada chamada de tool de carteira e do
  contexto de sessão: uma configuração feita no Desktop vale no Claude Code
  aberto sem reiniciar.
- Precedência: arquivo válido vence; sem arquivo, vale `WALLET_ID` do
  ambiente (instalações anteriores e CI); sem nenhum, estado pendente.
- Mascaramento fail-closed: ligado se o arquivo **ou** `WALLET_MASK_VALUES`
  disser que sim (coerente com o ADR-0015).
- Arquivo ilegível, corrompido, link simbólico ou com versão futura: estado
  pendente com causa e ação, sem apagar nem reescrever o arquivo.
- Escrita concorrente (dois clientes configurando ao mesmo tempo): último a
  gravar vence, sem trava; a gravação é atômica e o arquivo é pequeno.

**Rationale**: um lugar só para o link e o mascaramento é o que permite a
mesma configuração em todo cliente (o Cowork não pede valores do plugin: "Ignored
when a referenced option has no default; Cowork doesn't prompt for values",
Plugin feature support) e reduz a reconfiguração a reescrever um arquivo, em
vez de reescrever o registro de cada cliente. O diretório e o padrão de
abertura já foram endurecidos na 0.3.0 (learning lesson
arquivo_local_abrir_por_fd_sem_seguir_link).

**Alternatives considered**: `userConfig` do plugin com campo sensível
(funciona no Claude Code, ignorado no Cowork); variável de ambiente por
cliente (mantém N cópias da credencial e não alcança o Desktop); guardar na
memória (mistura credencial com dado do investidor e entra no changelog);
cofre do sistema (sem acesso documentado para um servidor de plugin e sem
dependência pinada para isso, Constituição V.1).

## D3 — Servidor sem configuração

**Decision**: `bootstrap.load_config` deixa de abortar sem `WALLET_ID`; o
servidor sempre sobe. Em estado pendente, as tools que dependem da carteira
(resumo, alocação, posições, histórico, proventos) devolvem o código novo
`wallet_not_configured`, cuja mensagem nomeia `open_wallet_setup`; as tools
de memória e de cotação continuam funcionando; `get_session_context` ganha
o bloco `configuration` (`status`, `mode`, `mask_values`, `next_action`).
A sonda de inicialização só roda com configuração presente e nunca aborta
por 301 (vira aviso de acesso recusado). ID inválido no ambiente continua
abortando com a mensagem atual (é erro de quem registrou, não de usuário
leigo).

**Rationale**: sem isso a conversa não tem por onde começar; o erro
estruturado é a camada que vale em qualquer cliente, inclusive sem hooks
(FR-004, FR-006). Erro que nomeia a tool do servidor leva o modelo a
chamá-la (Constituição II.4, research tool-error-channels).

**Alternatives considered**: tool de configuração com o servidor ainda
abortando (impossível: o processo não sobe); estado pendente silencioso com
dados vazios (fabrica resultado, viola II.2).

## D4 — Página local de configuração e tool `open_wallet_setup`

**Decision**: a configuração acontece numa página local temporária, servida
pelo próprio servidor. A tool nova `open_wallet_setup()`, sem parâmetros,
sobe o formulário (biblioteca padrão do Python, numa thread) e abre o
navegador com `webbrowser`. Fluxo na página: o usuário cola o link, escolhe o
mascaramento e salva; o servidor interpreta o link (D5), valida contra a
fonte (D6), pede confirmação na própria página se for outra carteira, grava o
arquivo (D2) e encerra a página. A conversa percebe a mudança pelo estado
(D2), sem reiniciar. Total de tools: 20.

Regras da página:

- Escuta só em `127.0.0.1`, em porta livre escolhida pelo sistema.
- Exige token aleatório de uso único (`secrets`), com prazo de 10 minutos.
- Confere `Host` e `Origin` no envio, para barrar envio vindo de outro site.
- HTML embutido, sem recurso externo; resposta com `Cache-Control: no-store`
  e `Content-Security-Policy` restritiva.
- Nunca grava o corpo do envio em log; o link não aparece na URL.
- Chamar a tool com a página já aberta reaproveita a mesma página.
- Se o navegador não abrir, a resposta traz o endereço da página para o
  usuário abrir e aponta `configure` no terminal.
- Se a porta local não abrir, a tool devolve o erro `setup_unavailable`, que
  aponta `configure` no terminal (D7).

Anotações da tool: `readOnlyHint=False`, `destructiveHint=False`,
`idempotentHint=True`, `openWorldHint=True`. Elas são "advisory hints [...]
and don't enforce security on their own" (gofastmcp.com/servers/tools).

A primeira tarefa da implementação (spike S1) confere se o servidor iniciado
numa sessão Cowork abre o navegador. Se não abrir, o fluxo volta ao mantenedor
antes do Lote 5.

**Rationale**: FR-005, FR-007, FR-008. Nenhuma tool recebe o link, a
credencial ou o mascaramento, então:

- a credencial não passa pelo modelo nem pelo provedor (a fronteira do
  ADR-0004 fica onde está, com a porta local e o arquivo como acréscimo ao
  modelo de ameaças);
- "o modelo não pode desligar a proteção" (ADR-0015 §1) continua verdadeiro;
- a troca de carteira é confirmada pela pessoa, uma barreira que o modelo não
  alcança pela conversa. Limite conhecido: um agente com controle do navegador
  (computer use, Claude in Chrome) poderia abrir a página; o token de uso
  único e o prazo curto reduzem esse risco, e o ADR-0019 o registra.

É o mesmo princípio do modo URL de elicitation ("sensitive interactions that
must not pass through the MCP client", spec MCP 2026-07-28), que não tem
suporte documentado no Claude Desktop (D15). Sem dependência nova
(Constituição V.1).

**Alternatives considered**:

- Link colado na conversa (decisão anterior, substituída em 01/11/2026): a
  credencial entra no histórico e passa pelo provedor; o modelo poderia
  desligar o mascaramento, contra o ADR-0015.
- `userConfig` do plugin: funciona no Claude Code, mas "Cowork doesn't prompt
  for values" (Plugin feature support); exigiria dois caminhos.
- Formulário dentro da conversa (MCP Apps): melhor experiência, mas "Claude
  Code calls the tool as text and doesn't render the UI" (Add an interactive
  UI to your MCP server), o Cowork não é citado, e a documentação não garante
  que o valor digitado fica fora do histórico e dos servidores da Anthropic.
  FastMCP documenta suporte (tools com `visibility=["app"]`). Fica só como
  teste no spike; se passar, pode entrar depois como camada sobre a mesma
  função de salvar.

## D5 — Interpretação do link

**Decision**: formas aceitas, depois de remover espaços, aspas e texto em
volta quando há exatamente um link inequívoco:

| Entrada | Modo | Extrai |
|---|---|---|
| `https://investidor10.com.br/wallet/public/<id>?h=<hash>` | restrita | ID e credencial |
| `https://investidor10.com.br/carteira/<id>` (e variações de rota com o mesmo ID) | pública | ID |
| só dígitos (forma antiga do assistente) | pública | ID |

Parâmetros de rastreamento são ignorados; host diferente de
`investidor10.com.br` (com ou sem `www.`), mais de um ID ou credencial com
caracteres fora de `[A-Za-z0-9_-]` são recusados com orientação (na página e
no terminal), nunca adivinhados. A credencial vai à API como parâmetro
`hash` (o site usa `h` no link; verificado contra a fonte em 31/10/2026) e
só nas requisições do proxy da carteira, nunca nas de cotação (FR-013).

**Rationale**: FR-011 e o caso de borda "link de outra rota". O formato e o
nome do parâmetro foram observados na fonte durante a especificação.

**Alternatives considered**: pedir ID e credencial separados (mais atrito,
contradiz "link como entrada"); seguir links encurtados (exigiria
requisição a terceiros com a credencial).

## D6 — Acesso recusado (HTTP 301 sem `Location`)

**Decision**: no cliente HTTP, status 300–399 vira `SourceError` com o
código novo `access_denied`, antes de ler o corpo, e nunca entra no cache
nem serve cache vencido. A mensagem diz que a fonte recusou o acesso à
carteira (restrita sem credencial válida ou privada) e manda chamar
`open_wallet_setup` para o usuário informar o link restrito atual. A validação
do link (página, assistente, `configure`, `doctor`) usa o mesmo mapeamento:
200 = válido; 3xx, 401, 403 = acesso recusado; 404 = carteira inexistente;
5xx ou erro de transporte = fonte indisponível (não grava). Teste de
regressão com a resposta real anonimizada e learning lesson (FR-010).

**Rationale**: a fonte não distingue restrita sem credencial de privada
(ambas devolvem o 301), então o produto não promete distinguir: a mensagem
cobre os dois casos e a ação é a mesma. Recusa de acesso é decisão da
fonte, não queda, por isso não serve cache vencido.

**Alternatives considered**: seguir o redirecionamento (não há `Location`;
e seguir com a credencial na URL vaza o hash); reaproveitar
`source_unavailable` (o modelo tentaria de novo, o que não resolve).

## D7 — Códigos de erro (12 para 15)

**Decision**: emenda do conjunto fechado do ADR-0014 com
`wallet_not_configured`, `access_denied` e `setup_unavailable`; contrato em
contracts/error-envelope.md.

**Rationale**: os três pedem ações diferentes de todos os códigos atuais
(configurar; informar link novo; usar o terminal) e retentabilidade diferente ("não, até
configurar"). Constituição II.1 e II.4.

**Alternatives considered**: `invalid_params` para o estado pendente (o
erro não é do argumento da chamada); campo `retryable` (rejeitado na
decisão D7 da spec 004).

## D8 — A credencial fora de todo texto visível

**Decision**: o `_redact` do cliente HTTP passa a substituir também a
credencial (por `<hash>`), inclusive no texto de exceções do httpx, que
carrega a URL com a query. A configuração nunca é logada nem entra no
changelog da memória; as respostas mostram o ID mascarado (últimos 2
dígitos) e nunca a credencial; o `doctor` mostra só "presente/ausente". A
guarda automatizada que já procura o ID passa a procurar a credencial lida
do ambiente da CI, nunca escrita no repositório (learning lesson
relatorio_que_prova_ausencia_de_segredo_nao_o_cita), e varre também o
pacote MCPB commitado.

**Rationale**: FR-012, SC-004, SC-009; mesmo tratamento já dado ao ID.

## D9 — As três camadas que conduzem a configuração

**Decision**:

1. **Servidor (garantia)**: D3 e a tool `open_wallet_setup` de D4.
2. **Hook de início de sessão**: deixa de ser script Bash. Passa a ser a
   leitura de um JSON estático do plugin,
   `cat "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.json"`, comando que roda
   igual no Bash e no PowerShell (`cat` é alias de `Get-Content`; o
   problema documentado do PowerShell é caminho entre aspas na posição de
   programa, não como argumento). O JSON usa só ASCII, com escapes `\u`
   para os acentos, para não depender da codificação do Windows
   PowerShell 5.1. A persona ganha a regra: se `get_session_context`
   indicar configuração pendente, conduzir a configuração (skill
   `configurar-carteira`) antes de qualquer análise.
3. **Skill `configurar-carteira`**: explica onde copiar o link no site, abre
   a página com `open_wallet_setup`, orienta a não colar o link na conversa e
   confere o resultado em `get_session_context`.

O hook de fim de sessão (lembrete de memória) continua em Bash: no Windows
sem Git ele falha em aberto (o evento `Stop` não bloqueia em falha comum),
e a matriz da US4 registra o resultado.

**Rationale**: "On a Windows device without Git for Windows, Claude Code
runs a hook in PowerShell when the hook sets neither `shell` nor `args`.
Hooks in Cowork sessions run the same way" e "PowerShell rejects some
commands that Bash accepts, such as a quoted program path followed by
arguments" (Desktop 3P, MCP, plugins, skills, and hooks). Com a regra de
pendência no texto estático, o hook não precisa de lógica. Constituição
III: a invariante (não mostrar valores antes da configuração) mora no
servidor; o hook só antecipa a pergunta.

**Alternatives considered**: hook do tipo `mcp_tool` (sem garantia de que
o servidor está conectado no `SessionStart` nem de suporte no Cowork);
duas versões do hook com `shell` diferente (rodam em dobro no Windows com
Git); hook chamando o pacote via `uvx` (uv pode não estar no PATH, D1).

## D10 — O plugin como fonte única da conexão, só no Claude

**Decision**: é um produto só, sem versão nem flag por superfície: o mesmo
plugin serve o Claude Desktop e o Claude Code, e cada superfície ignora o que
não suporta ("A surface skips a component it doesn't load", Plugin feature
support). Só o manifesto `.claude-plugin/plugin.json` ganha `mcpServers`.
Devin, Codex e Gemini seguem como hoje: o assistente registra o servidor e
instala o plugin só de comportamento, agora sem passar a carteira por variável
(o servidor lê o arquivo de D2). Emenda do ADR-0012 §2 restrita ao Claude.
`--mcp-only` continua como escape: no Claude Code registra só o servidor, sem
o plugin.

**Rationale**: o Desktop exige o servidor no plugin; nos CLIs a
verificação de servidor dentro de plugin seria trabalho novo sem ganho de
usuário nesta spec. A FR-009d pede apenas que nada fique em dobro, e com um
caminho por cliente isso vale por construção.

**Alternatives considered**: servidor no plugin dos quatro clientes
(formatos de Devin, Codex e Gemini não verificados para isso; fica para o
roadmap); só o servidor no Claude Code, com o comportamento ajustado por
projeto (cria dois produtos, perde guardião e hooks, e o ADR-0012 já rejeitou:
"vender 'MCP de dados' comoditiza o produto").

## D11 — Assistente, reconfiguração e diagnóstico

**Decision**:

- `install` aceita `--link` (e mantém `--wallet-id`), pergunta o
  mascaramento (ou `--mask`/`--no-mask`), valida (D6), grava o arquivo (D2)
  e então: no Claude Code, instala o plugin pinado na versão
  (`rc-ventura/mcp-investidor10-wallet#v<versão>`), pula a instalação local
  se `claude plugin list` já mostrar `investidor10-carteira@synced`, e
  oferece remover o registro antigo em escopo de usuário
  (`claude mcp remove carteira -s user`) quando ele existir. Na recusa, instala
  o plugin, avisa da duplicação e o `doctor` aponta. Na migração da 0.3.x, com
  uma pergunta só, remove e readiciona o marketplace na versão certa e reinstala
  o plugin, porque não pode haver dois marketplaces com o mesmo nome e remover
  um desinstala os plugins dele (Publish and distribute; Install and manage
  plugins); com `@synced`, oferece desinstalar a cópia local. Memória e
  configuração ficam fora do plugin e não são afetadas. Nos outros
  três, registra sem `WALLET_ID` e instala o plugin pinado quando o
  comando do cliente aceitar referência.
- `configure`: refaz as perguntas e reescreve só o arquivo; não toca em
  registros nem plugins; idempotente.
- `doctor`: confere runner, arquivo de configuração (presente, permissões,
  versão, modo), validação contra a fonte, memória e trava, clientes com o
  produto (registro ou plugin, incluindo `@synced`) e versões; saída
  sanitizada (home vira `~`, sem ID, sem credencial, sem valores).
- O relatório pareia cada cliente com o próprio resultado, inclusive o
  cliente citado e ausente (pendência do ciclo 6).

**Rationale**: FR-009d, FR-016, FR-017, FR-024, FR-025, FR-027. Sintaxe de
referência no Claude Code: "Add `#ref` to pin a branch or tag" (Install and
manage plugins). Plugin da conta aparece "under the ID `<name>@synced`" no
Claude Code; dois plugins habilitados com o mesmo nome registram os hooks
de só um deles ("Hooks when two enabled plugins share a name", Add
components to a plugin), o que torna a instalação local redundante e
arriscada quando o sincronizado existe. A sintaxe de referência de Devin,
Codex e Gemini é verificada na documentação de cada CLI durante a
implementação e registrada na research do cliente.

**Alternatives considered**: reescrever os registros na reconfiguração
(desnecessário com o arquivo único); remover o registro antigo sem
perguntar (mexe na configuração do usuário sem consentimento).

## D12 — Plugin sincronizado mais instalação local

**Decision**: tratado em D11 (pular a instalação local quando há
`@synced`); o spike S1 também registra o que o Claude Code faz quando os
dois existem (servidores `plugin:investidor10-carteira:carteira` em dobro
ou deduplicados), e a documentação diz qual manter.

## D13 — Pipeline de release, testes contra a API real e Dependabot

**Decision**:

- `release.yml` dispara por tag `v*` (inclui `vX.Y.ZrcN`) e tem três jobs:
  `build` (constrói wheel e sdist, confere a seção do changelog da versão
  base, confere o MCPB com `--check`, valida com `@anthropic-ai/mcpb@2.1.2`,
  roda os testes de fumaça e de consistência, sem `id-token`), `publish` (só
  baixa os artefatos, com `id-token: write` no ambiente `pypi`, sem checkout
  nem testes) e `verify` (depois de `publish`, em Linux, macOS e Windows:
  instala `mcp-investidor10-wallet==<versão>` do índice em ambiente limpo, por
  pip e por `uvx`, e confere o `initialize` e as 20 tools). O MCPB também vai
  como asset da release, para inspeção.
- O teste de fumaça deixa de exigir saída 1 sem `WALLET_ID`: o servidor sobe
  sem carteira e o `initialize` responde.
- Para tag de pré-lançamento, a checagem de changelog usa a seção da versão
  base (`[X.Y.Z]`).
- `promote.yml`: depois de `verify` verde numa tag final (sem `rc`), cria a
  branch `promote/vX.Y.Z` no commit da tag e abre o pedido de revisão para
  `main`; se o commit da tag não está em `develop` (hotfix), abre também um
  pedido da tag para `develop`. O mantenedor aprova e faz o merge.
- `main-gate.yml` (verificação obrigatória em `main`): origem
  `promote/vX.Y.Z`, commit igual ao da tag, versão final presente no índice e
  igual nos manifestos do plugin e no pacote do servidor empacotado. Falha
  fechada se o índice estiver inacessível.
- Teste de consistência a cada build: versão do pacote = versão dos
  manifestos do plugin = versão do manifesto MCPB.
- Só na release (`--check`): pacote MCPB commitado = pacote gerado; lista de
  tools do manifesto MCPB = lista exposta pelo servidor (entre releases a lista
  do servidor pode andar à frente do pacote publicado).
- `live.yml`: `schedule` semanal e `workflow_dispatch`, nunca
  `pull_request`; carteira pública fictícia por segredo do repositório;
  asserts que imprimem só o código do erro.
- `.github/dependabot.yml`: ecossistemas `uv` (ou `pip`, conforme o suporte
  verificado na documentação do Dependabot na implementação) e
  `github-actions`, semanal.
- Ambiente `pypi`: aprovação manual a cada execução e implantação permitida
  para tags `v*`, a verificar na implementação (a publicação confiável do
  índice referencia repositório, arquivo do workflow e ambiente, não a
  branch).

**Rationale**: FR-026, FR-028, FR-029, FR-032 a FR-034 e as decisões do
roadmap; separar a permissão de publicação do código que roda testes é a
pendência do ciclo 6. O guia de publicação do Python pede jobs de build e de
publicação separados, publicação por tag e aprovação manual no ambiente
`pypi` (fichamento `publicacao-de-pacotes-e-promocao-de-artefatos`).

## D14 — Devin Desktop

**Decision**: nenhuma suposição de caminho. A US3 é uma verificação real:
rodar o assistente numa máquina com Devin Desktop, ver se o registro do
Devin CLI e o plugin carregam, e registrar em learning lesson. O caminho do
arquivo de configuração do app diverge entre fontes e não entra no código
antes da verificação (FR-021).

## D15 — Elicitation no Claude Desktop

**Decision**: não usar nesta spec; a página local (D4) é o caminho. A FR-008a
fica como gatilho de revisão: quando a Anthropic documentar elicitation no
Claude Desktop, a mesma página passa a ser aberta por URL mode, sem outra
mudança no fluxo do usuário.

**Rationale**: a spec MCP 2026-07-28 define form mode e URL mode e diz que
"Servers MUST use URL mode for interactions involving such sensitive
information" (modelcontextprotocol.io/specification/2026-07-28/client/
elicitation). Não há documentação oficial da Anthropic de suporte no
Claude Desktop; fontes não oficiais (pedidos de recurso de março de 2026 e
um artigo sobre o anúncio de 23/10/2026) dizem que o suporte existe no
Claude Code CLI e chega aos outros produtos depois. Tarefa de reverificar
nas release notes antes do fechamento da spec.

## D16 — Revogação do link da carteira

**Decision**: testar no Lote 1, com a carteira fictícia em modo restrito, se
gerar um link novo no site faz o antigo receber o HTTP 301 de acesso recusado.
Só depois disso `docs/PRIVACY.md` e os textos ao usuário descrevem a revogação,
dizendo apenas o que o teste confirmar.

**Rationale**: é uma premissa da especificação, sem fonte. O produto não pode
prometer uma proteção que talvez não exista.

## D17 — Documentação e decisões registradas

**Decision**:

- ADR-0018: plugin único e completo, com servidor MCPB (emenda ADR-0012 §2 e
  §6 para o Claude e ADR-0011: o PyPI segue como único canal de código, o plugin
  só aponta para a versão publicada, e o teste de fumaça deixa de exigir saída 1
  sem carteira; registra D1, D9, D10, D12).
- ADR-0019, escrito no Lote 2, com o primeiro código que ele descreve:
  configuração local única, modo restrito e página local (emenda o modelo de
  ameaças do ADR-0004 e a ativação do mascaramento do ADR-0015 §1; registra D2
  a D6, D8, D15 e o limite de um agente com controle do navegador).
- ADR-0020, escrito no Lote 0: fluxo de branches e release (D18); emenda o
  ADR-0011 (a ordem passa a ser publicar antes de promover para `main`).
- Emenda do ADR-0014 (D7).
- Learning lessons: HTTP 301 de acesso recusado (FR-010); resultado do
  spike S1; plugin sincronizado mais local; Devin Desktop (US3).
- README: passo a passo do Desktop (FR-031); PRIVACY.md: carteira restrita
  como padrão e a página local (FR-018); CHANGELOG.

## D18 — Fluxo de branches e release (Git Flow adaptado)

**Decision**: o princípio é que **`main` só contém versões já publicadas no
índice**, porque o Desktop lê o plugin de `main` e o plugin manda baixar uma
versão do índice. Regras:

| Regra | Conteúdo |
|---|---|
| Branches | `main` (versões lançadas), `develop` (integração), `spec-NNN/*` (lotes, saem e voltam por `develop`) e `hotfix/*` (saem de `main`). Sem `release/*` |
| Versão final | pedido de preparação em `develop` (versão, pacote, changelog); tag `vX.Y.Z` em `develop`; publicação, depois de aprovação; `verify`; `promote.yml` cria `promote/vX.Y.Z` no commit da tag e abre o pedido para `main`; o mantenedor aprova |
| Pré-lançamento | tag `vX.Y.ZrcN` em `develop`, publicada e verificada como a final, nunca promovida; é a base da validação no Desktop (Upload plugin) |
| Hotfix | `hotfix/X.Y.Z` sai de `main`; tag, publicação, `verify`, promoção para `main` e pedido para `develop` |
| Portão | verificação obrigatória em `main` (`main-gate`): só aceita `promote/vX.Y.Z`, no commit da tag, com a versão final presente no índice |

Diferenças em relação ao Git Flow padrão: não há `release/*` (um mantenedor
só; a preparação é um pedido comum em `develop`); a tag fica em `develop`, não
em `main`; o lançamento é a publicação, não o merge em `main`; e a CI impede
que `main` aponte para o que ainda não existe no índice. Sem `release/*`,
`develop` fica parado entre o pré-lançamento e a versão final, ou cada
correção gera um novo pré-lançamento.

**Rationale**:

- `main` = produção e `develop` = integração, com merges em `main` marcando
  versões, vêm do Git Flow, que o autor ainda considera adequado para
  "software that is explicitly versioned" (fichamento `modelos-de-branching`).
- No Git Flow padrão o merge em `main` é o lançamento; aqui o plugin em `main`
  depende de um artefato externo, e o merge antes da publicação deixaria `main`
  apontando para uma versão inexistente. Publicar antes de mover o ponteiro
  aparece em exemplos reais de automação (fichamento
  `publicacao-de-pacotes-e-promocao-de-artefatos`), sem norma formal.
- Pré-lançamento promovido ao estável (build once, promote) é o padrão de
  Tuist e Snap, documentado em blogs e documentação de projetos.
- Release por tag e sem branch de release é uma otimização reconhecida pelo
  trunk-based development; "CD teams do not do release branches".

**Alternatives considered**:

- Git Flow estrito: merge em `main` antes da publicação deixa uma janela de
  alguns minutos com `main` apontando para versão inexistente, e a validação
  no Desktop só aconteceria depois de todos os lotes, porque o pré-lançamento
  sairia de `release/*`.
- `main` + `develop` sem `hotfix/*`: sem caminho limpo para uma correção
  urgente enquanto `develop` tem trabalho inacabado.
- `stable` como branch padrão e trabalho em `main`: só há apoio em discussões
  de comunidade (graphql-js, Kotlin), e o GitHub usa uma única configuração
  para a visão padrão e a base dos pedidos de revisão.
- Ponteiro por `ref` ou `sha` no `marketplace.json`: documentado para o
  Claude Code, mas o caso do marketplace pessoal no Desktop não está
  documentado.
- Repositório só de marketplace: um repositório e um token de escrita a mais.

**Verificações pendentes (na implementação)**: (1) o Desktop lê a branch
padrão ao adicionar o marketplace (spike); (2) o ambiente `pypi` aceita
tags criadas em `develop` e em `hotfix/*`; (3) a instalação por versão exata
de pré-lançamento funciona com pip e com `uvx` (a documentação do `uv` não
cobre o caso).

**Resultado da verificação (3), 2026-11-07 (`v0.4.0rc1`, run 42379935532)**:
a versão exata de pré-lançamento instala com pip e com `uvx`; o `uvx` não
ignora o `==0.4.0rc1` (o resolvedor reporta "you require
mcp-investidor10-wallet==0.4.0rc1"), então D1 e D18 seguem sem revisão.

| Verificação | Ubuntu | macOS | Windows |
|---|---|---|---|
| pip `==0.4.0rc1` em ambiente limpo, `initialize` e 20 tools | verde | verde | verde |
| `uvx --from ==0.4.0rc1`, importação | verde | verde | verde |
| `uvx --offline --from ==0.4.0rc1`, `initialize` e 20 tools | **vermelho** | verde | verde |

- Causa do vermelho: o `uv` offline não fechou a resolução do `pydantic` com o
  cache do passo anterior (`No solution found when resolving tool
  dependencies`). Não reproduziu no macOS com cache limpo, com e sem
  `--offline`; a causa exata no runner Linux não foi identificada.
- Correção: o `--offline` saiu do `verify` (PR #21). Vale só para tags
  futuras, porque um re-run usa o `release.yml` do commit da tag; o run da
  `v0.4.0rc1` segue com o `verify (ubuntu-latest)` vermelho.
- Também verificado nesse run: o ambiente `pypi` aceitou a tag criada em
  `develop`. A publicação falhou duas vezes antes por um `500` do Rekor
  (`unexpected error communicating with inactive shard`), indisponibilidade do
  serviço do Sigstore, e passou na quarta tentativa sem mudança de código. Tags
  em `hotfix/*` seguem sem verificação.

## Fontes

Os achados por fonte, sem reflexão, estão nos fichamentos em
`docs/research/fichamentos/` (índice em `README.md`). Lista de fontes desta
spec:

- Plugin feature support across platforms — claude.com/docs/plugins/platform-support
- Plugin structure and testing — claude.com/docs/plugins/build
- Cowork, Plugins — claude.com/docs/cowork/guide/plugins
- MCP, plugins, skills, and hooks (Desktop 3P) — claude.com/docs/third-party/claude-desktop/extensions
- Build a desktop extension with MCPB — claude.com/docs/connectors/building/mcpb
- MCPB MANIFEST.md e examples (hello-world-uv) — github.com/modelcontextprotocol/mcpb
- Add components to a plugin — code.claude.com/docs/en/plugins/components
- Install and manage plugins — code.claude.com/docs/en/plugins/install
- Publish and distribute a plugin — code.claude.com/docs/en/plugins/publish
- Tools (annotations) — gofastmcp.com/servers/tools
- MCP Apps — modelcontextprotocol.io/extensions/apps/overview;
  claude.com/docs/connectors/building/mcp-apps (getting-started, quickstart,
  troubleshooting); gofastmcp.com/apps/overview e /apps/low-level
- Plugins (overview) — claude.com/docs/plugins/overview
- Plugin manifest reference — code.claude.com/docs/en/plugins/manifest-reference
- Elicitation, spec 2026-07-28 — modelcontextprotocol.io/specification/2026-07-28/client/elicitation
- Não oficiais, só contexto: claudeissues.com 41110 e 41347 (elicitation
  no Desktop); unity-mcp PR 398 (PATH no macOS); azukiazusa.dev (anúncio de
  Tasks e Elicitations).
