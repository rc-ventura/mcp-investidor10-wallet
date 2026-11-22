# Feature Specification: Distribuição Desktop — Claude Desktop, Devin Desktop e configuração pelo link da carteira

**Feature Branch**: `005-desktop-distribution`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "analise o roadmap e crie a spec 005 a principal ideia eh servir o mcp para os servicos de Ui dos produtos como o claude desktop e e depois devin deskotp ( naoi sei se existe diferenca entre desktop web e o desktop local) adicione nessa spec outras pontos do roapmap que vc achar que faca sentido com visao do produto. Qume sabe nao podmeos migarr para um sqlite .. avalie o que vc considera relevante para essa spec 005"

Escopo derivado de `docs/ROADMAP.md` (matriz MoSCoW de 27/10/2026, revisada
em 29 e 31/10/2026): todos os itens **Must** da Fase 3 — extensão do Claude
Desktop, Devin Desktop, validação em máquina limpa, carteira restrita com
configuração interativa e listagem em registries (esta última trocada pelo
marketplace próprio, ver Clarifications) — mais os itens que a
chegada de usuários do Desktop torna necessários: diagnóstico `doctor` (sem
as métricas locais), execução semanal dos testes contra a API real,
Dependabot e as pendências da 0.3.1 que tocam o instalador e o pipeline de
release.

## Clarifications

### Session 2026-11-08

- Q: O servidor empacotado dispensa o `uv` no Claude Desktop? → A: **não**.
  O spike (Lote 1) mostrou que o Desktop usa o `uv` do usuário e que, sem
  ele, o servidor não sobe nem como `.mcpb` tipo `uv` nem como `uvx` no
  `plugin.json`; o Claude Code CLI ainda rejeita o tipo `uv`. O plugin do
  Claude passa a declarar o servidor com `command: "uvx"` e a versão fixada,
  e o **`uv` é pré-requisito documentado do Desktop**, com um tutorial
  conservador (`docs/INSTALACAO-DESKTOP.md`). Isso revisa a FR-002 (o usuário
  abre o terminal uma vez, só para instalar o `uv`) e fecha a FR-003 pelo
  caminho que ela já previa. Binário por plataforma está descartado (assinatura,
  notarização e Gatekeeper). O Claude Code segue pelo assistente de instalação.
  As substituições estão em `research.md` D1 e na learning lesson do spike.

### Session 2026-11-01

- Q: Como as tools e a configuração da carteira chegam às sessões do Claude
  unificado? → A: um **plugin completo**, com o servidor dentro, adicionado
  pela conta. O servidor inicia sem configuração e conduz o usuário até ela
  (erro estruturado em toda tool de carteira, reforçado pelo hook de início
  de sessão e por uma skill de configuração). O plugin passa a ser a fonte
  única da conexão (emenda do ADR-0012). O caminho da extensão `.mcpb` com
  formulário foi descartado: não há documentação de que extensões aparecem
  nas sessões unificadas, e ele exigiria duas instalações.
- Q: O produto muda conforme a superfície (Claude Code, Claude Desktop)? →
  A: não. É **um plugin só**, sem feature flag: cada superfície ignora o que
  não suporta. `--mcp-only` continua como escape para quem quer só o
  servidor no terminal.
- Q: Como o link e o mascaramento chegam ao servidor? → A: por uma **página
  local de configuração** aberta pelo próprio servidor em `127.0.0.1`, no
  navegador, com a conversa só conduzindo o usuário até ela. O modelo não
  recebe o link nem altera o mascaramento. Isso substitui a decisão anterior
  de colar o link na conversa. O formulário dentro da conversa (MCP Apps)
  não entra nesta spec: é só testado no spike, como possível melhoria.
- Q: Submeter o produto aos diretórios de servidores MCP nesta spec? → A:
  não. A distribuição desta spec é o **marketplace próprio** (o repositório
  público, adicionado em Customize > Plugins). O diretório da Anthropic fica
  para depois, com critérios de reabertura (FR-030).
- Q: Como o repositório organiza branches e lançamentos, já que o Desktop lê o
  plugin do repositório e o plugin aponta para uma versão do pacote no índice?
  → A: um **Git Flow adaptado**. `main` só contém versões já publicadas no
  índice e é o que o usuário recebe; `develop` integra o trabalho; cada lote
  sai e volta por `develop`; correções urgentes saem de `main` em `hotfix/*`.
  Não há `release/*`. A tag é criada em `develop`; a pipeline publica no
  índice e só depois propõe a promoção para `main`, e a CI recusa promover uma
  versão que não esteja publicada. Pré-lançamentos (`X.Y.ZrcN`) saem de
  `develop`, servem à validação no Desktop e nunca chegam a `main`. Difere do
  Git Flow padrão em três pontos: não há `release/*`, a tag fica em `develop`
  e o lançamento é a publicação, não o merge em `main`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investidor sem terminal usa o produto no Claude Desktop (Priority: P1)

Um investidor que não usa linha de comando quer conversar com o assistente
sobre a própria carteira no aplicativo Claude Desktop. Hoje isso exige editar
um arquivo de configuração à mão e descobrir o caminho absoluto do runner
(causa nº 1 de "MCP failed to connect" em apps gráficos no macOS). Com esta
feature, ele abre Customize > Plugins, adiciona o marketplace do produto
colando o endereço do repositório, clica para instalar o plugin e abre uma
conversa. Antes de qualquer análise, o assistente abre a **página de
configuração** no navegador. Lá ele cola o **link da carteira**, escolhe em
linguagem simples se quer esconder os valores em reais do modelo e salva. De
volta à conversa, o assistente passa a responder com dados reais. A memória
do investidor (teses, regras, decisões, alertas) é a mesma usada pelos CLIs
na mesma máquina.

**Why this priority**: é o principal canal de quem não usa CLI, e o
assistente de instalação da spec 003 não alcança apps gráficos. É a ideia
central desta spec e a decisão do mantenedor de 27/10/2026 ("tudo que é
distribuição vem na frente").

**Independent Test**: numa máquina com Claude Desktop instalado, plano pago
e nenhuma configuração prévia do produto, adicionar o marketplace, instalar
o plugin, preencher a página de configuração aberta pelo assistente e
verificar que uma pergunta como "qual a alocação da minha carteira?" é
respondida com dados reais, sem abrir terminal nem editar arquivo.

**Acceptance Scenarios**:

1. **Given** o Claude Desktop em macOS ou Windows, plano pago, o Claude
   unificado e nenhuma configuração do produto, **When** o usuário adiciona
   o marketplace do repositório, instala o plugin e manda a primeira
   mensagem numa conversa nova, **Then** o assistente abre a página de
   configuração antes de qualquer análise.
2. **Given** a configuração pendente e um cliente que não rodou o hook de
   início de sessão, **When** o usuário pergunta algo sobre a carteira,
   **Then** toda tool de carteira devolve um erro estruturado que diz que a
   carteira não está configurada e nomeia a tool que abre a página, e o
   assistente conduz a configuração.
3. **Given** a página de configuração aberta, **When** o usuário cola o link
   de uma carteira pública, escolhe o mascaramento e salva, **Then** o link é
   validado contra a fonte, a página mostra modo e mascaramento escolhidos e
   a pergunta seguinte, na mesma conversa e sem reiniciar o app, retorna
   dados da carteira.
4. **Given** a página de configuração, **When** o usuário informa o link de
   uma carteira restrita, **Then** o link não entra na conversa, e nenhuma
   resposta de tool nem do assistente contém o link ou a credencial.
5. **Given** uma tese salva pelo Claude Code na mesma máquina, **When** o
   usuário pergunta pelas teses no Claude Desktop, **Then** a tese aparece
   (memória compartilhada sob a trava entregue na 0.3.0).
6. **Given** o link de uma carteira privada, inexistente ou com credencial
   inválida, **When** o usuário o informa na página, **Then** a página
   explica em PT-BR a causa e o que fazer no site, nada é gravado e a
   configuração continua pendente.
7. **Given** o plugin de uma versão anterior, memória e configuração com
   dados, **When** o usuário atualiza o marketplace ou desinstala o plugin,
   **Then** a memória e a configuração permanecem intactas.
8. **Given** uma carteira já configurada, **When** o usuário informa na
   página o link de outra carteira, **Then** a página mostra a carteira atual
   mascarada, avisa que a memória foi escrita para ela e só troca depois de
   uma confirmação na própria página. Nenhuma tool troca a carteira nem altera
   o mascaramento.
9. **Given** o plugin instalado, **When** uma mensagem nova abre uma sessão
   Cowork no computador, **Then** a persona é aplicada, as 3 skills e o
   guardião ficam disponíveis e o lembrete de memória roda ao fim (FR-009).
10. **Given** uma máquina que não roda a máquina virtual do Cowork (a
    mensagem abre uma conversa Chat, que ignora servidores locais de
    plugin), **When** o usuário pergunta sobre a carteira, **Then** a
    resposta diz que as tools não estão disponíveis nessa conversa e o que
    fazer, sem inventar valores (FR-009a).

---

### User Story 2 - Configuração pelo link: carteira pública ou restrita, com escolha de mascaramento (Priority: P1)

Verificado contra a fonte em 31/10/2026: o site tem três modos de
compartilhamento — **Pública** (indexável por buscadores), **Restrita** (só
quem tem o link `…/wallet/public/<id>?h=<hash>`) e **Privada** (só o dono).
Hoje só a pública funciona, e uma restrita ou privada faz todas as tools de
carteira falharem com um diagnóstico enganoso ("o formato do payload
mudou"). O investidor leigo não deveria escolher modo por variável de
ambiente nem tornar a carteira indexável para usar o produto. Com esta
feature, tanto o assistente no terminal quanto a página de configuração pedem
**o link da carteira**: o produto deduz o modo, valida contra a fonte,
pergunta em linguagem simples sobre o mascaramento e mostra um resumo. A
reconfiguração (um subcomando no terminal, ou a mesma página aberta a pedido
na conversa) permite mudar depois (de pública para restrita, link novo,
mascaramento ligado ou desligado) sem reinstalar.

**Why this priority**: a carteira restrita passa a ser a recomendação
padrão de privacidade (a pública é indexável). Sem ela, distribuir para
terceiros empurra o usuário para a opção menos privada. A página de
configuração (US1) depende do mesmo conceito de "link como entrada". A correção
do diagnóstico de acesso recusado independe do resto e protege os usuários
atuais.

**Independent Test**: com uma carteira restrita real, rodar o assistente no
terminal colando o link com `?h=`, verificar que o registro funciona e que
as tools retornam dados; tornar a carteira privada e verificar que o erro diz
"acesso recusado" com a ação correta; rodar a reconfiguração e ligar o
mascaramento sem reinstalar.

**Acceptance Scenarios**:

1. **Given** uma carteira restrita ou privada configurada sem credencial,
   **When** qualquer tool de carteira é chamada, **Then** o erro estruturado
   diz que o acesso foi recusado pela fonte e orienta "torne a carteira
   pública ou configure o link restrito", e nunca diz que o formato mudou.
2. **Given** o assistente de instalação no terminal, **When** o usuário cola
   o link de uma carteira restrita, **Then** o assistente identifica o modo
   restrito, valida contra a fonte e registra o servidor com a credencial,
   sem pedir o ID separado.
3. **Given** o link de uma carteira pública, **When** o usuário cola o link,
   **Then** o modo público é identificado e o assistente informa que a
   carteira é indexável e que o modo restrito é o recomendado.
4. **Given** o link de uma carteira privada, **When** o assistente valida,
   **Then** explica que a carteira privada não é acessível ao produto e como
   mudar para restrita, sem registrar nada.
5. **Given** a validação concluída, **When** o assistente pergunta sobre o
   mascaramento, **Then** a pergunta diz em linguagem simples o que se
   preserva (percentuais, alocação, fundamentos) e o que se perde (valores em
   reais, histórico de patrimônio), e o resumo final mostra modo de
   compartilhamento e mascaramento escolhidos.
6. **Given** o produto já instalado em dois CLIs e no Desktop, **When** o
   usuário reconfigura com um link novo, **Then** a configuração local única
   é reescrita e vale para todos os clientes, o plugin não é reinstalado e
   uma segunda execução igual não muda nada (idempotência).
7. **Given** uma carteira restrita configurada, **When** o usuário gera um
   link novo no site (o antigo deixa de valer), **Then** as tools retornam
   acesso recusado apontando a reconfiguração (subcomando no terminal ou
   página de configuração).

---

### User Story 3 - Devin Desktop com o mesmo produto do Devin CLI (Priority: P2)

O Devin Desktop (antigo Windsurf, renomeado pela Cognition em junho de 2026)
compartilha o harness de agente com o Devin CLI: skills, regras, hooks,
plugins e servidores MCP usam o mesmo formato e a mesma descoberta. O
investidor que usa o Devin Desktop quer o servidor e o plugin de
comportamento funcionando lá sem configuração extra. O formato ainda não foi
verificado na prática pelo projeto, e o roadmap exige verificar antes de
prometer suporte.

**Why this priority**: mesmo upgrade de alcance que o Claude Desktop, com
custo provavelmente menor (o assistente da spec 003 já registra no Devin
CLI). Vem depois do P1 porque o público do Claude Desktop é maior e o caminho
do Devin pode já estar coberto.

**Independent Test**: numa máquina com Devin Desktop, rodar o assistente de
instalação e verificar se o app descobre as tools e carrega as skills, o
subagente guardião e os hooks; registrar o resultado em learning lesson.

**Acceptance Scenarios**:

1. **Given** o Devin Desktop instalado, **When** o assistente de instalação
   roda, **Then** o relatório final diz explicitamente se o Devin Desktop foi
   coberto (pelo registro compartilhado com o Devin CLI ou por um caminho
   próprio) ou por que não foi.
2. **Given** o produto registrado, **When** o usuário abre uma sessão no
   Devin Desktop, **Then** as 20 tools aparecem e o hook de início de sessão
   injeta a persona.
3. **Given** uma divergência entre o comportamento do Devin Desktop e o do
   Devin CLI, **When** a verificação termina, **Then** a divergência fica
   registrada em learning lesson e a documentação não promete o que não foi
   verificado.

---

### User Story 4 - Usuário novo instala em máquina limpa nos clientes prometidos (Priority: P2)

Antes de divulgar o produto para terceiros, cada cliente prometido na
documentação precisa ter sido instalado de verdade numa máquina sem nada do
projeto: o assistente real (não só o modo de simulação), o plugin no Codex
pela interface interativa, o Gemini CLI e o plugin completo no Claude
Desktop em macOS e Windows. Hoje só há simulação e testes de contrato (pendências
aceitas da spec 003).

**Why this priority**: é o gate de distribuição — promessa não verificada
vira o primeiro relato de bug de um usuário novo.

**Independent Test**: seguir o roteiro de validação numa máquina (ou conta de
usuário) limpa e preencher a matriz cliente × plataforma com resultado e
data.

**Acceptance Scenarios**:

1. **Given** uma máquina limpa com cada cliente alvo, **When** o roteiro é
   executado, **Then** cada célula da matriz cliente × plataforma tem
   "funciona" ou uma divergência registrada, nunca "não testado".
2. **Given** uma célula com divergência, **When** a documentação é
   publicada, **Then** ela não anuncia suporte naquela combinação.

---

### User Story 5 - Usuário diagnostica a instalação sem expor dados (Priority: P3)

Um usuário do Desktop que vê "o servidor não conectou" não tem terminal
aberto nem sabe onde ficam os logs. Com esta feature, ele roda um comando de
diagnóstico que confere a instalação (runner, configuração da carteira e
modo, memória acessível e trava disponível, clientes onde o produto está
registrado, versão) e imprime um resumo sanitizado que pode colar numa issue
— sem ID da carteira, credencial, valores ou caminhos com o nome do usuário.

**Why this priority**: relato iniciado pelo usuário é o único canal de
suporte de máquinas de terceiros (telemetria remota é Won't). Fica em P3
porque o produto funciona sem ele; as métricas locais por chamada de tool
ficam fora desta spec.

**Independent Test**: provocar cada causa conhecida de falha (runner
ausente, link inválido, carteira privada, memória sem permissão de escrita,
produto não registrado em nenhum cliente) e verificar que o diagnóstico
nomeia a causa e a ação, e que a saída não contém nenhum dado sensível.

**Acceptance Scenarios**:

1. **Given** uma das causas conhecidas de falha, **When** o usuário roda o
   diagnóstico, **Then** a saída nomeia a causa e a próxima ação em PT-BR.
2. **Given** qualquer instalação, **When** o diagnóstico roda, **Then** a
   saída não contém ID da carteira, credencial do link, valores monetários
   nem o nome do usuário local.

---

### User Story 6 - Mantenedor publica cada versão com o pacote Desktop e a cadeia de suprimentos em dia (Priority: P3)

O mantenedor cria a tag numa versão de `develop`; o pipeline publica o pacote
no índice, confere a versão publicada e só então propõe a promoção para
`main`. O plugin do marketplace aponta para essa mesma versão do servidor, e
quem instala nunca recebe um plugin que aponte para uma versão inexistente.
Com usuários de terceiros chegando, o mantenedor também precisa
saber de mudança da API não documentada antes deles e receber as correções
de segurança das dependências e das actions pinadas.

**Why this priority**: sustenta o P1 ao longo do tempo. O roadmap condiciona
a execução semanal dos testes contra a API real à chegada dos usuários do
Desktop, e o Dependabot é o complemento do pin por SHA da 0.3.0.

**Independent Test**: criar uma tag de pré-release e verificar que a versão
do plugin e a versão do servidor que ele inicia são as do pacote publicado;
disparar a execução manual dos testes contra a API real e verificar que roda
com a carteira fictícia dedicada.

**Acceptance Scenarios**:

1. **Given** uma tag de versão, **When** o pipeline termina, **Then** o
   plugin do marketplace declara a mesma versão do pacote publicado e inicia
   exatamente essa versão do servidor, e o passo que publica é o único com
   permissão de publicação.
2. **Given** a execução semanal dos testes contra a API real, **When** um
   teste falha, **Then** o log mostra só o código do erro, nunca o payload, e
   a carteira usada é a fictícia dedicada, nunca a do mantenedor.
3. **Given** uma correção de segurança numa dependência ou numa action
   pinada, **When** ela é publicada, **Then** um pedido de atualização com
   diff revisável é aberto automaticamente.
4. **Given** um pedido de promoção para `main` cuja origem não é uma branch
   `promote/vX.Y.Z` no commit de uma tag, ou cuja versão não existe no índice,
   **When** a CI roda, **Then** a promoção é recusada com a causa em PT-BR e
   nada chega a `main`.
5. **Given** uma versão de pré-lançamento (`X.Y.ZrcN`) publicada a partir de
   `develop`, **When** ela é validada no Desktop, **Then** `main` permanece
   inalterado e nenhum usuário do marketplace recebe o pré-lançamento.
6. **Given** um defeito na versão lançada e trabalho inacabado em `develop`,
   **When** o mantenedor corrige numa branch `hotfix/*` saída de `main` e cria
   a tag, **Then** a correção é publicada, promovida para `main` e levada de
   volta a `develop`, sem levar para `main` nada que não foi lançado.

---

### User Story 7 - Investidor encontra e adiciona o plugin pelo marketplace próprio (Priority: P2)

Sem listagem em diretório, o usuário chega ao produto pelo README ou pela
página do projeto. Lá ele encontra, em PT-BR e com imagens, o passo a passo
do Desktop: abrir Customize > Plugins, escolher adicionar marketplace, colar
o endereço do repositório (exibido pronto para copiar), instalar o plugin e
abrir uma conversa. O mesmo marketplace atende o Claude Code. A submissão
aos diretórios de servidores MCP (incluindo o da Anthropic) fica para depois
desta spec, com critérios de reabertura.

**Why this priority**: sem este caminho documentado, o usuário leigo não
acha o plugin, e a US1 não se cumpre. Os diretórios ficam de fora por causa
do risco dos termos de uso da API não documentada (ADR-0005), que cresce com
a exposição, e porque o alarme de mudança da API (US6) e a matriz de
máquinas limpas (US4) ainda não existem.

**Independent Test**: um usuário sem contexto do projeto segue só o README
e chega ao plugin instalado no Desktop, sem pedir ajuda.

**Acceptance Scenarios**:

1. **Given** o README publicado, **When** o usuário segue o passo a passo
   do Desktop, **Then** ele adiciona o marketplace com um único texto colado
   e instala o plugin com um clique.
2. **Given** o marketplace adicionado, **When** sai uma versão nova,
   **Then** o passo a passo diz como atualizar pela própria tela de plugins.
3. **Given** o fim desta spec, **When** os critérios de reabertura da
   FR-030 são avaliados, **Then** o resultado fica registrado e o item dos
   diretórios volta ao roadmap.

---

### Edge Cases

- O link colado tem `?h=` mas o hash está errado ou expirou: a validação
  recusa com "acesso recusado", não registra nada e explica como copiar o
  link restrito atual.
- O link colado vem de outra rota do site (página da carteira com abas,
  link encurtado, URL com parâmetros extras de rastreamento): o produto
  extrai ID e hash quando presentes e recusa com orientação quando não
  consegue identificar a carteira, nunca adivinha.
- Carteira restrita configurada e o dono muda para pública: a credencial
  sobra e não deve quebrar nada; o diagnóstico informa que a carteira está
  pública e indexável.
- Fonte fora do ar no momento da validação: o assistente distingue "fonte
  indisponível" de "acesso recusado" e não registra uma configuração não
  validada sem confirmação explícita do usuário.
- Claude Desktop e um CLI abertos ao mesmo tempo gravando na memória: a
  trava da 0.3.0 serializa as gravações; nenhuma é perdida.
- Máquina sem o runtime que o servidor do plugin exige: o usuário recebe uma
  explicação do que falta e de como resolver, nunca o servidor desconectando
  sem explicação (FR-003).
- Duas instalações do produto no Claude Desktop (o plugin e uma entrada
  manual antiga no arquivo de configuração do app com o mesmo alias): o
  usuário é orientado a remover a entrada manual; a documentação de
  migração cobre o caso.
- Plugin adicionado na conta pelo Claude Desktop numa máquina onde o
  assistente da spec 003 já registrou o servidor no Claude Code: o app
  sincroniza o plugin para o Claude Code, e o produto não pode terminar com
  dois servidores, 40 tools ou skills e hooks em dobro (FR-009d).
- Usuário em plano gratuito: plugins não ficam disponíveis no Desktop; a
  documentação diz isso e aponta os CLIs.
- Link colado no meio de outro texto, com espaços ou entre aspas: a página
  extrai o link quando ele é inequívoco e pede de novo quando não é, nunca
  adivinha.
- Usuário cola o link na conversa em vez de usar a página: nenhuma tool
  recebe o link; o assistente abre a página, e o produto explica que o link
  colado ficou no histórico da conversa.
- O navegador não abre, ou a máquina não tem navegador (SSH, servidor): a
  tool devolve o endereço da página para o usuário abrir e aponta o
  subcomando de configuração no terminal.
- A porta local não abre (restrição do sistema): a tool devolve um erro
  estruturado que aponta o subcomando de configuração no terminal.
- Página de configuração aberta e vencida, ou o cliente encerrado antes de
  salvar: nada é gravado; a tool abre uma página nova com um token novo.
- Configuração local ausente, mas a variável de ambiente do ID presente
  (instalação de uma versão anterior pelo assistente): o servidor continua
  funcionando, e a reconfiguração migra para a configuração local.
- Configuração local ilegível ou corrompida: o servidor volta ao estado
  "não configurado" com causa e ação, sem apagar o arquivo e sem tocar na
  memória.
- Usuário em Linux procurando o Claude Desktop: o app não tem versão Linux
  oficial; a documentação diz isso e aponta os CLIs.
- Reconfiguração com o link de uma carteira diferente da atual: o
  assistente avisa que a memória (teses, regras, metas) foi escrita para a
  carteira anterior e pede confirmação antes de trocar.
- Exceção da biblioteca HTTP com a URL completa (que contém o hash) no
  texto: nenhuma mensagem visível ao modelo ou ao operador carrega a URL com
  a credencial.
- Tag criada em `develop` e `develop` recebe novos commits antes da promoção: a
  promoção usa a branch `promote/vX.Y.Z` no commit da tag, não a ponta de
  `develop`.
- Publicação que falha depois da tag: a versão não é promovida; um número já
  publicado no índice não pode ser reutilizado, então a correção sai com a
  versão seguinte.
- Correção urgente com trabalho inacabado em `develop`: sai de `main` em
  `hotfix/*`, é publicada e promovida, e volta para `develop` por pedido de
  revisão aberto pela pipeline.

## Requirements *(mandatory)*

### Functional Requirements

**Claude Desktop (US1)**

- **FR-001**: O plugin publicado no marketplace do repositório DEVE ser o
  produto completo e único: o servidor local (as tools da carteira e a tool
  que abre a página de configuração) e o comportamento (skills, guardião,
  persona, lembrete de memória). Não há versão nem flag por superfície: cada
  uma ignora o que não suporta. Nos clientes cujo formato de plugin aceita
  servidor, o plugin é a fonte única da conexão; a mudança DEVE ser
  registrada como emenda do ADR-0012. `--mcp-only` continua como escape no
  terminal, registrando só o servidor, sem o plugin.
- **FR-002**: O usuário DEVE conseguir instalar e configurar o produto no
  Claude Desktop sem editar arquivo e com o menor uso possível de terminal:
  instalar o `uv` uma única vez, com um comando de uma linha copiado de um
  tutorial passo a passo (`docs/INSTALACAO-DESKTOP.md`); depois, adicionar o
  marketplace (um texto colado), instalar o plugin (um clique) e preencher,
  na página de configuração, o link da carteira e a escolha de mascaramento.
  *(Revisada em 08/11/2026: o texto original dispensava o terminal; o spike
  mostrou que o Desktop depende do `uv` da máquina. Ver Clarifications.)*
- **FR-003**: O servidor do plugin DEVE iniciar numa máquina limpa, em macOS
  e Windows, que tenha só o Claude Desktop. O plano DEVE verificar na
  documentação oficial qual runtime o app oferece a servidores locais de
  plugin; se nenhum dispensar pré-requisito, o plano registra o
  pré-requisito mínimo e como o produto o resolve ou orienta, e a FR-002 é
  revista com o mantenedor antes de implementar. No Linux não há Claude
  Desktop, mas o Claude Code usa o mesmo plugin: o servidor empacotado DEVE
  declarar e ser verificado também nessa plataforma; se falhar, o assistente
  mantém no Linux o registro do servidor pelo terminal.
- **FR-004**: O servidor DEVE iniciar sem configuração. Nesse estado, toda
  tool que depende da carteira DEVE devolver um erro estruturado que diz que
  a carteira não está configurada e nomeia a tool que abre a página
  (Constituição II.4), e o contexto de sessão DEVE informar a configuração
  pendente. O código de erro (novo ou reaproveitado do conjunto fechado do
  ADR-0014) é decisão do plano.
- **FR-005**: Uma tool sem parâmetros DEVE abrir no navegador a página de
  configuração, servida pelo próprio servidor. A página DEVE receber o link e
  a escolha de mascaramento, validar contra a fonte (FR-014), deduzir o modo
  (FR-011), gravar a configuração localmente na máquina do usuário com
  permissão restrita ao dono, fora do arquivo de memória, e passar a valer na
  mesma conversa, sem reiniciar o app.
- **FR-006**: A configuração DEVE ser conduzida antes de qualquer análise,
  em três camadas: o erro estruturado do servidor (FR-004) é a garantia,
  porque vale em qualquer cliente; o hook de início de sessão injeta a
  instrução de configuração pendente quando não há configuração; e uma skill
  de configuração orienta o usuário a usar a página e a não colar o link na
  conversa.
- **FR-007**: O link e a credencial NÃO DEVEM passar pelo modelo: nenhuma
  tool os recebe como argumento nem os devolve. As respostas de tool só
  mostram modo, mascaramento e ID mascarado. A página DEVE aceitar conexões
  só em `127.0.0.1`, exigir um token de uso único com prazo curto, conferir a
  origem do envio, carregar só recursos locais e encerrar depois de salvar
  ou vencer. O modelo de ameaças do ADR-0004 DEVE ser emendado com a porta
  local e a credencial no arquivo.
- **FR-008**: Só o usuário, na página ou no terminal, DEVE poder trocar a
  carteira ou a credencial e ligar ou desligar o mascaramento. Nenhuma tool
  aceita esses valores (proteção contra troca por engano ou por conteúdo
  injetado na conversa). Com uma carteira já configurada, trocar por outra
  DEVE exigir uma confirmação do usuário na própria página ou no terminal,
  avisando que a memória foi escrita para a carteira atual. A ativação do
  mascaramento pelo arquivo DEVE ser registrada em emenda do ADR-0015.
- **FR-008a**: O plano DEVE reverificar nas fontes oficiais o suporte do
  Claude Desktop ao modo URL de elicitation da spec MCP. Havendo suporte, a
  mesma página de configuração passa a ser aberta por esse mecanismo, sem
  outra mudança no fluxo do usuário.
- **FR-009**: No Claude unificado (Chat e Cowork numa tela só, o padrão do
  Claude Desktop), uma sessão Cowork no computador DEVE receber o produto
  completo: as tools, as 3 skills (mais a de configuração), o guardião de
  disciplina, a persona de início de sessão e o lembrete de memória, com o
  mesmo conteúdo do plugin dos CLIs.
- **FR-009a**: Numa conversa Chat (máquina que não roda a máquina virtual
  do Cowork), a documentação oficial diz que servidores locais de plugin,
  hooks e subagentes são ignorados. O produto NÃO DEVE inventar valores
  nesse caso: a skill diz que as tools não estão disponíveis naquela
  conversa e o que fazer, e a documentação declara a limitação.
- **FR-009b**: Os hooks DEVEM funcionar no computador do usuário em macOS e
  Windows, inclusive no Windows sem Git for Windows (onde o app os roda no
  PowerShell), ou falhar em aberto sem bloquear a sessão; a FR-004 garante a
  configuração mesmo sem hook.
- **FR-009c**: O servidor iniciado pelo plugin DEVE usar a mesma memória e a
  mesma configuração local que os CLIs usam na mesma máquina, sob a mesma
  trava entre processos. Atualizar, reinstalar ou desinstalar o plugin NÃO
  DEVE apagar a memória nem a configuração.
- **FR-009d**: Um plugin adicionado na conta é sincronizado para o Claude
  Code; o produto NÃO DEVE acabar com o servidor registrado duas vezes nem
  com skills ou hooks em dobro, salvo recusa explícita do usuário, sempre
  avisada no relatório e apontada pelo diagnóstico. O assistente de instalação
  DEVE, nos clientes cujo plugin traz o servidor, instalar o plugin e oferecer
  remover o registro separado feito por versões anteriores. Na migração da
  0.3.x, com uma pergunta só, DEVE remover e readicionar o marketplace na versão
  certa e reinstalar o plugin, e oferecer desinstalar a cópia local quando
  houver a cópia sincronizada da conta. `--mcp-only` com o plugin já instalado
  segue a mesma regra de aviso. Devin, Codex e Gemini seguem com registro pelo
  assistente e plugin só de comportamento.

**Carteira restrita e configuração pelo link (US2)**

- **FR-010**: Uma resposta de redirecionamento da fonte que não é seguida
  (como o HTTP 301 "Acesso não autorizado" observado em 31/10/2026) DEVE ser
  tratada como acesso recusado, com diagnóstico distinto de "formato
  inesperado", tanto nas tools quanto na validação da carteira. Teste de
  regressão com a resposta real e learning lesson.
- **FR-011**: O assistente de instalação e a página de configuração DEVEM
  aceitar o link da carteira como entrada e deduzir o modo: com o parâmetro
  de credencial, restrita (extrai ID e credencial); sem ele, pública;
  privada é explicada e recusada.
- **FR-012**: A credencial da carteira restrita DEVE ter o mesmo tratamento
  do ID da carteira: fora de mensagens de erro visíveis ao modelo ou ao
  operador, logs, envelopes, changelog da memória, saída do diagnóstico e
  arquivos versionados. A guarda automatizada que já existe para o ID DEVE
  cobrir a credencial.
- **FR-013**: A credencial DEVE ser enviada somente às requisições de dados
  da carteira, nunca às de cotação.
- **FR-014**: O assistente DEVE validar o link contra a fonte antes de
  registrar em qualquer cliente, distinguindo acesso recusado, carteira
  inexistente e fonte indisponível.
- **FR-015**: Depois da validação, o assistente DEVE perguntar sobre o
  mascaramento em linguagem simples (o que se preserva e o que se perde) e
  terminar com um resumo do modo de compartilhamento e do mascaramento
  escolhidos.
- **FR-016**: O produto DEVE oferecer a reconfiguração por um subcomando no
  terminal e pela página de configuração; ambos refazem as perguntas e
  reescrevem a configuração local única, sem reinstalar o plugin, com a mesma
  idempotência do assistente.
- **FR-017**: Flags não interativas DEVEM existir para o link e o
  mascaramento, para scripts e CI; a flag atual do ID da carteira DEVE
  continuar aceita nesta versão.
- **FR-018**: O documento de privacidade DEVE passar a recomendar a
  carteira restrita como padrão (a pública é indexável) e explicar a
  credencial do link; a decisão DEVE ser registrada em ADR próprio (modo
  restrito e configuração interativa).
- **FR-019**: Mensagens ao operador e ao usuário seguem o ADR-0009
  (operador em PT-BR); mensagens de erro de tool seguem o estilo
  recurso + causa + próxima ação (Constituição II.4).

**Devin Desktop (US3)**

- **FR-020**: O projeto DEVE verificar numa instalação real do Devin
  Desktop se o registro feito pelo assistente (compartilhado com o Devin
  CLI) e o plugin de comportamento são carregados; o resultado, positivo ou
  não, DEVE virar learning lesson com fonte e data.
- **FR-021**: O relatório do assistente DEVE dizer se o Devin Desktop foi
  coberto; se a verificação mostrar caminho próprio, o assistente DEVE
  cobri-lo pelo mecanismo nativo do app ou declarar o cliente não
  suportado — nunca registrar por adivinhação.
- **FR-022**: A documentação NÃO DEVE anunciar suporte a um cliente ou
  plataforma antes da verificação real correspondente (US3, US4).

**Validação em máquina limpa (US4)**

- **FR-023**: Antes de fechar a spec, DEVE existir uma matriz cliente ×
  plataforma preenchida a partir de instalação real em máquina limpa,
  cobrindo: assistente real (roteiros V2.2/V2.4 da spec 003), plugin no
  Codex pela interface interativa, Gemini CLI, Devin Desktop e o plugin
  completo no Claude Desktop em macOS e Windows (sessão Cowork e conversa
  Chat).

**Diagnóstico (US5)**

- **FR-024**: O produto DEVE oferecer um subcomando de diagnóstico que
  confere runner, configuração e modo da carteira (com validação contra a
  fonte), memória acessível e trava disponível, clientes onde o produto está
  registrado e versão, e imprime um resumo em PT-BR com causa e ação para
  cada problema.
- **FR-025**: A saída do diagnóstico DEVE ser sanitizada para colar numa
  issue pública: sem ID, credencial, valores monetários, conteúdo da memória
  nem caminhos com o nome do usuário local.

**Pipeline de release e cadeia de suprimentos (US6)**

- **FR-026**: A versão do plugin e a versão do servidor que ele inicia DEVEM
  ser iguais à do pacote publicado, verificadas por teste automatizado a
  cada build; a lista de tools do pacote DEVE ser igual à do servidor em cada
  release; e o pipeline DEVE separar o teste de fumaça do passo de publicação, deixando a permissão de
  publicação só no segundo (pendência do ciclo 6), e conferir a versão publicada
  em instalação limpa nos três sistemas antes de propor a promoção.
- **FR-027**: O assistente de instalação DEVE fixar a fonte do plugin na
  versão instalada do pacote (marketplace, branch do plugin e extensão do
  Gemini hoje seguem a branch padrão — pendência do ciclo 7) e parear cada
  cliente com o seu resultado no relatório, inclusive quando o usuário cita
  um cliente ausente (pendência do ciclo 6).
- **FR-028**: Os testes contra a API real DEVEM rodar semanalmente e sob
  demanda, nunca em pull request, com a carteira pública fictícia dedicada
  cujo ID fica em segredo do repositório, e com asserts que imprimem só o
  código do erro (decisões já registradas no roadmap).
- **FR-029**: Atualizações das dependências e das actions pinadas por SHA
  DEVEM chegar como pedidos de atualização revisáveis e automáticos.

**Fluxo de branches e release (US6)**

- **FR-032**: O repositório DEVE seguir o fluxo de branches registrado em ADR:
  `main` contém somente versões já publicadas no índice e é o que o
  marketplace entrega; `develop` integra o trabalho; cada lote da spec sai de
  `develop` e volta por pedido de revisão; correções urgentes saem de `main`
  em `hotfix/*`. Não há `release/*`.
- **FR-033**: Nenhum commit DEVE chegar a `main` antes de a versão que o plugin
  declara estar publicada no índice. A promoção DEVE ser feita pela pipeline,
  numa branch `promote/vX.Y.Z` criada no commit da tag, e a CI DEVE recusar
  qualquer pedido para `main` cuja origem não seja essa branch, cujo commit não
  seja o da tag, ou cuja versão não exista no índice como versão final.
- **FR-034**: Pré-lançamentos (`X.Y.ZrcN`) DEVEM poder ser publicados a partir
  de `develop` e instalados por versão exata, nunca chegam a `main`, e são o
  meio de validar o plugin no Desktop antes da versão final. A pipeline DEVE
  tratar a tag de pré-lançamento sem exigir seção própria no changelog.

**Marketplace próprio e diretórios (US7)**

- **FR-030**: A distribuição desta spec DEVE ser o marketplace próprio (o
  repositório público, adicionado em Customize > Plugins no Desktop e por
  `/plugin` no Claude Code). Nenhuma submissão a diretório de servidores MCP
  ou de plugins é feita nesta spec. O item volta ao roadmap com critérios de
  reabertura: matriz de máquinas limpas aprovada (FR-023), testes semanais
  contra a API real rodando por 4 semanas sem detectar mudança (FR-028) e
  decisão sobre os termos de uso do Investidor10 registrada em ADR.
- **FR-031**: O README DEVE trazer, em PT-BR, o passo a passo do Desktop
  (adicionar o marketplace com o endereço pronto para copiar, instalar o
  plugin, configurar na página, atualizar e desinstalar), com a exigência
  de plano pago e a limitação da conversa Chat (FR-009a).

### Key Entities *(include if feature involves data)*

- **Link da carteira**: a entrada única do usuário. Contém o ID da carteira
  e, no modo restrito, a credencial. É dado sensível: quem tem o link vê
  todos os valores pela API.
- **Modo de compartilhamento**: pública (indexável), restrita (só com o
  link) ou privada (inacessível ao produto). Deduzido do link e confirmado
  contra a fonte.
- **Configuração do usuário**: link + escolha de mascaramento. Vive num
  arquivo local único na máquina do usuário, com permissão restrita ao dono
  e separado da memória; vale para todos os clientes da máquina. É gravada
  pela página de configuração ou pelo assistente (terminal).
- **Página de configuração**: formulário local e temporário, servido pelo
  servidor em `127.0.0.1`, com token de uso único. É o único caminho do link
  fora do terminal.
- **Estado de configuração**: configurado ou pendente. Pendente faz toda
  tool de carteira devolver o erro que aponta a tool que abre a página.
- **Plugin completo**: o pacote do marketplace com o servidor e o
  comportamento. Versão sempre igual à do pacote publicado.
- **Relatório de diagnóstico**: resumo sanitizado da instalação (checagens,
  causa e ação), destinado a ser colado numa issue.
- **Matriz de validação**: cliente × plataforma × resultado × data,
  preenchida por instalação real.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário que já tem o `uv` instalado (ou que o instala seguindo
  o tutorial) instala o produto no Claude Desktop e recebe a primeira resposta
  com dados da própria carteira em até 5 minutos, com zero edição de arquivo e
  no máximo três entradas (o endereço do marketplace, o link da carteira e a
  resposta do mascaramento). O tempo de instalar o `uv` é medido à parte e
  registrado, sem entrar nos 5 minutos *(revisado em 08/11/2026)*.
- **SC-001a**: Em 100% das conversas novas sem configuração, o assistente
  abre a página antes de qualquer análise (10 de 10 conversas novas no roteiro
  de validação), e 0 respostas trazem valores da carteira antes da
  configuração.
- **SC-002**: Em 100% das tentativas do roteiro de validação, uma tese salva
  num cliente aparece no outro (Desktop ↔ CLI) na consulta seguinte.
- **SC-003**: 100% das recusas de acesso da fonte (restrita sem credencial,
  privada, credencial expirada) são diagnosticadas como acesso recusado; 0
  aparecem como "formato inesperado".
- **SC-004**: 0 ocorrências do ID ou da credencial em mensagens de erro,
  logs, changelog da memória, saída do diagnóstico e arquivos versionados,
  verificadas pela guarda automatizada a cada build.
- **SC-005**: Trocar de pública para restrita, ou ligar o mascaramento, leva
  um comando e menos de 1 minuto no terminal, ou um envio na página de
  configuração no Desktop, sem reinstalar.
- **SC-006**: 100% das células da matriz cliente × plataforma têm resultado
  verificado ("funciona" ou divergência registrada) antes de a documentação
  anunciar o suporte.
- **SC-007**: O diagnóstico identifica a causa correta em 5 de 5 cenários de
  falha conhecidos (runner ausente, link inválido, carteira privada, memória
  sem permissão de escrita, produto não registrado).
- **SC-008**: Em 100% das releases desta spec em diante, o plugin do
  marketplace tem a mesma versão do pacote publicado e inicia essa versão do
  servidor.
- **SC-009**: 0 ocorrências do link ou da credencial em argumentos e
  respostas de tool e em erros, verificadas por teste; nenhuma tool altera a
  carteira, a credencial ou o mascaramento.
- **SC-010**: 0 commits em `main` cujo plugin declare uma versão ausente do
  índice, verificado pela CI a cada promoção; entre a publicação e a promoção,
  o que o usuário recebe continua apontando para uma versão existente.

## Assumptions

### Superfícies avaliadas (fatos verificados em 31/10 e 01/11/2026)

| Superfície | Como acessa um MCP | Nesta spec |
|---|---|---|
| Claude Desktop — Claude unificado (Chat e Cowork numa tela só) | Desde 16/09/2026 em Pro, Max e Ultra (em etapas), e padrão para todas as organizações a partir de 10/11/2026. Cada mensagem da tela inicial abre uma sessão Cowork quando a máquina roda a máquina virtual do Cowork. A sessão carrega os plugins da conta (Customize): skills, subagentes, hooks (rodam no computador, fora da máquina virtual) e servidores locais trazidos por plugin ("Loads when the Cowork session runs on your computer"); não pede valores de configuração do plugin e não lê `~/.claude` | **Sim** (US1), pelo plugin completo, configurado na página local |
| Claude Desktop — máquina que não roda a máquina virtual do Cowork | A mensagem abre uma conversa Chat. Plugin: carrega skills e commands; servidores locais de plugin são ignorados. Sobre hooks as fontes divergem: a tabela geral diz que o Chat os ignora, a doc do Desktop diz que conversas Chat rodam hooks a partir da versão 1.52386.0 | **Sim**, como limitação declarada (FR-009a) |
| Claude Desktop — aba Code | É o Claude Code: carrega tudo; um plugin instalado na conta também aparece ali sincronizado | Coberto pelo mesmo plugin (FR-009d); entra na matriz da US4 |
| claude.ai (web) e apps móveis | Só conectores remotos: a conexão parte da nuvem da Anthropic até um servidor HTTPS público. O plugin carrega as skills, mas sem as tools elas não têm dados | **Fora** — exigiria hospedar o servidor com o link da carteira e a memória fora da máquina (ver abaixo) |
| Devin Desktop (antigo Windsurf, app local) | Servidor local por stdio; harness compartilhado com o Devin CLI | **Sim** (US3) |
| Devin na nuvem (web) | Agente remoto; MCP remoto configurado na nuvem | **Fora**, pelo mesmo motivo do claude.ai |

Fontes: "Plugin feature support across platforms" e "Plugin structure and
testing" (claude.com/docs/plugins), "Cowork overview", Cowork "Plugins"
(claude.com/docs/cowork/guide/plugins), "Unified Claude in Claude Desktop on
3P", "MCP, plugins, skills, and hooks" (Desktop 3P), "Build a desktop
extension with MCPB" e "Add a connector that isn't in the directory"
(claude.com/docs), "Use plugins in Claude" e "Get started with custom
connectors using remote MCP" (support.claude.com), consultadas em 31/10 e
01/11/2026.

Fatos que sustentam o caminho escolhido:

- Instalação na conta: Customize > Plugins, por **Add marketplace** (um
  repositório GitHub, GitHub Enterprise, GitLab ou Bitbucket público, pelo
  endereço completo ou pelo atalho `dono/repo`), por **Upload plugin** (zip
  da pasta, até 200 MB) ou por **Discover** (o diretório). Até 25
  marketplaces por conta; **Update** no marketplace puxa as versões novas.
- O repositório já tem o marketplace na raiz (`.claude-plugin/marketplace.json`,
  plugin `investidor10-carteira` em `./plugin`), hoje só de comportamento.
- Um plugin instalado na conta aparece no Claude Code como plugin
  sincronizado na sessão seguinte.
- Servidor de plugin que referencia `${user_config.*}` sem valor padrão é
  ignorado no Cowork, que não pede os valores; por isso a configuração vai
  pela página local e por arquivo local, não por campos do plugin. O modo URL
  de elicitation segue o mesmo princípio ("sensitive interactions that must
  not pass through the MCP client", spec MCP 2026-07-28), mas não tem suporte
  documentado no Claude Desktop.
- Plugins pedem plano pago (Pro, Max, Ultra, Team ou Enterprise); um plugin
  com diretório `bin/` no topo é recusado no Chat e no Cowork (o atual não
  tem). O diretório da Anthropic não aceita mais extensões `.mcpb`: um
  servidor local só é listado lá dentro de um plugin.
- Hooks em Windows sem Git for Windows rodam no PowerShell, que recusa parte
  dos comandos de Bash (os hooks atuais do plugin são scripts Bash).

A diferença entre "desktop" e "web" é, portanto, de arquitetura, não de
interface: o app desktop roda o servidor na máquina do usuário; a versão web
só fala com servidores públicos na internet. Servir a web exigiria hospedar
o servidor, guardar o link da carteira (a credencial) e a memória financeira
num servidor de terceiros e adicionar autenticação — exatamente o que o
roadmap registra como fora de escopo ("Local stdio é a arquitetura certa";
"Hosting multi-tenant ... piora privacidade").

### Avaliação da migração para SQLite

A migração da memória para SQLite fica **fora desta spec**. Motivos:

- O problema que justificaria a troca — vários processos gravando no mesmo
  arquivo, que esta spec aumenta com o Desktop — já foi resolvido na 0.3.0
  pela trava entre processos com releitura sob a trava (ADR-0013). O
  Desktop entra nesse modelo sem mudança.
- O volume continua em escala humana (KBs, um usuário); SQLite não muda
  nada que o usuário perceba nesta spec de distribuição.
- A troca tem custo alto e risco de perder dado: migração de schema,
  reescrita da semântica de degradação (backup de arquivo corrompido, modo
  somente-leitura, recusa de versão futura, memória apagada com o servidor
  rodando), do changelog e de testes de 7 ciclos de revisão; e o arquivo
  deixa de ser legível e restaurável à mão pelo usuário.
- Misturar mudança de armazenamento com a chegada de usuários novos junta
  dois riscos no mesmo lançamento.

Gatilhos para reavaliar (registrar em ADR quando algum ocorrer): coleções de
crescimento contínuo entrarem no produto (snapshot de posições, coleção
`trades`, lançamentos em cache), contenção da trava observada no diagnóstico
ou em relatos, ou consultas que exijam filtro e agregação sobre a memória. O
roadmap já registra SQLite como o degrau seguinte, ainda local e sem
servidor.

### Demais premissas

- Hoje o produto é unificado na instalação, mas separado nos pacotes: o
  assistente registra o servidor (com o ID pela variável de ambiente) e
  instala o plugin, que não declara servidor (ADR-0012, decisão 2), e o
  servidor não inicia sem a variável. Adicionar o plugin atual no Desktop
  entrega o comportamento sem nenhuma tool. Esta spec inverte a decisão: o
  plugin passa a levar o servidor, e a configuração sai da variável de
  ambiente para o arquivo local único.
- A extensão avulsa (Settings > Extensions) fica fora desta spec
  (Clarifications, 01/11/2026). O formato MCPB é usado só como embalagem interna
  do servidor dentro do plugin, invisível ao usuário. O tipo de runtime é
  decisão do plano (FR-003); a extensão avulsa pode voltar como alternativa se
  o plano não achar runtime sem pré-requisito para servidores de plugin.
- Que gerar um link novo no site revoga o link antigo é uma premissa ainda não
  verificada; o Lote 1 testa isso com a carteira fictícia, e os textos ao
  usuário só prometem o que o teste confirmar.
- A variável de ambiente do ID continua aceita nesta versão, para
  instalações anteriores e para CI; a precedência entre ela e a
  configuração local é decisão do plano.
- O Devin Desktop compartilha harness e formato de personalização com o
  Devin CLI segundo a documentação oficial da Cognition (consultada em
  31/10/2026); o caminho exato do arquivo de configuração de MCP do app
  ainda diverge entre fontes e é verificado na US3.
- A trava entre processos, o modo privacidade, o changelog da memória e o
  sinal duplo de erro entregues na 0.3.0 são reusados sem mudança de
  contrato.
- A credencial da carteira restrita fica na mesma configuração local do ID,
  com permissão restrita ao dono; nunca no registro do cliente nem no
  arquivo de memória.
- As pendências da 0.3.1 que não tocam o instalador nem o pipeline de
  release (guarda de profundidade no cliente HTTP, `Content-Length`,
  caminho da memória em mensagens de erro, política de limites, `fdopen`,
  testes que faltam) seguem para a 0.3.1 e não fazem parte desta spec.
- O fluxo de branches é um Git Flow adaptado (Clarifications, 01/11/2026). A
  fundamentação de cada regra, com fontes, está em
  `docs/research/fichamentos/` (modelos de branching e publicação de
  pacotes); a combinação das regras é decisão do projeto e será registrada em
  ADR. Três verificações ficam para a implementação: se o Desktop lê a branch
  padrão do repositório ao adicionar o marketplace (spike), se o ambiente de
  publicação aceita tags criadas fora de `main`, e se a instalação por versão
  exata de pré-lançamento funciona com o runner do projeto.
- Fora desta spec: métricas locais por chamada de tool, avaliação Ollama,
  telemetria remota, multi-carteira, reconciliação corretora × carteira e
  as tools novas da Fase 2 (vão para as specs seguintes, começando pela 006).
