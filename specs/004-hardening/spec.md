# Feature Specification: Hardening — robustez, privacidade e confiança antes da distribuição Desktop

**Feature Branch**: `004-hardening`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "crie o hardening seguindo o roadmap" — escopo
da spec 004 definido em `docs/ROADMAP.md` (decisão do mantenedor de
27/10/2026): Fase 1 inteira, exceto a avaliação Ollama — file lock na
memória, doc de privacidade, modo privacidade `WALLET_MASK_VALUES`,
changelog append-only da memória, sinal duplo de erro e os itens menores (`instructions=`, regra de
validação de payloads, remoção da migração legada). A execução semanal dos
testes contra a API real foi movida para o roadmap em 27/10/2026. Vem antes da spec 005
(Distribuição Desktop) porque o Desktop aumenta o número de processos
escrevendo no mesmo arquivo de memória.

## Clarifications

### Session 2026-10-27

- Q: No modo privacidade, `get_earnings` (que só devolve o total de proventos em reais) deve ser bloqueado por completo ou devolver uma razão calculada no servidor? → A: Bloqueado — erro estruturado de indisponibilidade no modo privacidade, igual a `get_patrimony_history`.
- Q: A trava da memória entre processos precisa funcionar no Windows já nesta spec? → A: Sim — macOS, Linux e Windows, com biblioteca de trava multiplataforma como dependência de runtime; a Constituição V.1 é emendada (1.2.0) para autorizá-la, e o armazenamento da memória é portado para Windows nesta spec.
- Q: Se o sistema de arquivos não suportar a trava (ex.: montagem de rede), o servidor grava sem proteção, recusa gravações ou aborta? → A: Leituras seguem normais; gravações são recusadas com erro estruturado e orientação ao operador; sem fallback automático para outra memória. Uso simultâneo da mesma memória em duas máquinas via pasta sincronizada é limitação documentada.
- Q: A execução semanal dos testes contra a API real usa carteira de teste dedicada ou a carteira real do mantenedor? → A: Carteira pública dedicada com posições fictícias cobrindo as classes de ativo; ID em segredo do repositório. (Decisão preservada no roadmap: a execução semanal saiu desta spec em 27/10/2026.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Memória não perde gravações com vários clientes abertos (Priority: P1)

O investidor usa o produto em mais de um cliente ao mesmo tempo (ex.: Claude
Code no terminal e, a partir da spec 005, Claude Desktop). Cada cliente
inicia o seu próprio processo do servidor, e todos compartilham o mesmo
arquivo de memória do investidor. Hoje cada processo guarda uma cópia em
memória e regrava o arquivo inteiro: uma regra salva no cliente A some
quando o cliente B grava uma tese logo depois (última gravação vence). O
investidor precisa que **toda** gravação confirmada sobreviva, e que cada
cliente enxergue o que o outro gravou.

**Why this priority**: É perda silenciosa de dado do investidor — o
diferencial do produto é a memória de longo prazo. É Must no roadmap e
pré-requisito direto da spec 005, que multiplica os processos concorrentes.

**Independent Test**: Em macOS, Linux e Windows, iniciar dois processos do
servidor sobre o mesmo arquivo de memória, intercalar gravações (regras,
teses, decisões, alertas) nos dois e verificar que o arquivo final contém
todas, e que cada processo lista as gravações do outro.

**Acceptance Scenarios**:

1. **Given** dois processos do servidor abertos sobre a mesma memória,
   **When** o processo A salva uma regra e em seguida o processo B salva uma
   tese, **Then** o arquivo final contém a regra **e** a tese.
2. **Given** o processo A gravou uma regra, **When** o processo B lista as
   regras, **Then** a regra gravada por A aparece, sem reiniciar B.
3. **Given** duas sessões executando o bootstrap ao mesmo tempo com um
   alerta de preço cujo gatilho foi atingido, **When** ambas avaliam os
   alertas, **Then** o alerta transita para disparado exatamente uma vez e
   é relatado como disparado sem duplicação no histórico.
4. **Given** outro processo segura a memória por mais que o tempo máximo de
   espera, **When** uma gravação é pedida, **Then** a tool devolve o erro
   estruturado de memória ocupada com a orientação de tentar novamente, e
   nada é gravado pela metade.
5. **Given** dois processos gerando o próximo identificador da mesma
   coleção ao mesmo tempo, **When** ambos gravam, **Then** os
   identificadores resultantes são distintos.

---

### User Story 2 - Investidor entende o que sai da máquina antes de adotar (Priority: P1)

Antes de instalar (ou de recomendar a alguém), o investidor quer saber, em
PT-BR e sem jargão, **o que vai para onde**: o que é buscado no Investidor10,
o que entra no contexto do provedor do modelo de linguagem, o que fica no
arquivo local — e qual é a credencial real da carteira. Hoje isso não está
escrito, e o usuário pode supor que "servidor local" significa "dados não
saem da máquina", ou que o botão de mascarar do site protege os valores.

**Why this priority**: Must no roadmap — pré-requisito de divulgar o
produto. O identificador/link da carteira é a credencial (quem o tem vê
todos os valores) e o mascaramento do site é apenas visual (verificado em
17/10/2026); o usuário precisa saber disso para decidir.

**Independent Test**: Um leitor que nunca viu o projeto lê apenas o
documento de privacidade e responde corretamente às três perguntas: o que
vai para o Investidor10, o que vai para o provedor do modelo, o que fica
local; e por que o link da carteira deve ser tratado como senha.

**Acceptance Scenarios**:

1. **Given** o documento de privacidade publicado, **When** o leitor procura
   o destino de cada tipo de dado, **Then** encontra uma tabela com os três
   destinos (fonte pública, provedor do modelo, arquivo local) e o que cada
   um recebe.
2. **Given** o documento, **When** o leitor procura o risco principal,
   **Then** encontra explicitamente que o identificador/link da carteira é a
   credencial e que o botão de mascarar do site não protege os dados da API.
3. **Given** o documento, **When** o leitor procura como reduzir exposição,
   **Then** encontra o modo privacidade (User Story 3) com o que ele
   preserva e o que ele perde, e a nota de que privacidade total exige
   também um modelo de linguagem local.
4. **Given** o README e o assistente de instalação, **When** o usuário chega
   pelo caminho normal de instalação, **Then** encontra um link para o
   documento de privacidade.

---

### User Story 3 - Modo privacidade: análise por percentuais sem expor montantes (Priority: P2)

O investidor quer usar o agente para alocação, rebalanceamento e
diversificação **sem** que patrimônio, valores aplicados, lucros,
quantidades e proventos em reais entrem no contexto do provedor do modelo.
Ele ativa o modo privacidade na configuração do servidor (variável de
ambiente, nunca parâmetro de tool — o próprio modelo não pode desligá-lo) e
passa a receber apenas percentuais, razões e indicadores.

**Why this priority**: Should no roadmap — passa a fazer sentido ao
distribuir. O produto funciona sem; quem precisa dele não tem outra forma
de proteção, pois o site devolve tudo mesmo com a carteira "mascarada".

**Independent Test**: Ativar o modo privacidade, chamar todas as tools de
carteira contra fixtures com todos os campos do payload real e verificar que nenhuma resposta contém
montante em reais nem quantidade, que as respostas indicam explicitamente
que houve mascaramento, e que a análise de alocação por percentual continua
possível.

**Acceptance Scenarios**:

1. **Given** o modo privacidade ativo, **When** o agente pede o resumo da
   carteira, **Then** recebe apenas variações e rentabilidades percentuais,
   sem patrimônio, valor aplicado ou lucro em reais, e com a indicação de que
   montantes foram omitidos pelo modo privacidade.
2. **Given** o modo privacidade ativo, **When** o agente pede posições de
   uma classe, **Then** recebe por ativo o peso na carteira, o peso ideal,
   indicadores (DY, P/VP, notas) e variações percentuais, sem quantidade,
   patrimônio, valor aplicado, lucro ou proventos recebidos.
3. **Given** o modo privacidade ativo, **When** o agente pede o histórico de
   patrimônio ou os proventos do período, **Then** recebe um erro
   estruturado informando que a informação não está disponível no modo
   privacidade — nunca números estimados, zerados ou razões derivadas.
4. **Given** o modo privacidade ativo, **When** a fonte passa a devolver um
   campo novo desconhecido, **Then** esse campo **não** aparece na resposta
   (só campos reconhecidamente não monetários passam).
5. **Given** a variável de ambiente com valor não reconhecido, **When** o
   servidor inicia, **Then** a inicialização é abortada com mensagem em
   PT-BR indicando os valores aceitos (nunca segue com o modo desligado).
6. **Given** o modo privacidade ativo, **When** o agente consulta a cotação
   de um ativo, **Then** a cotação de mercado é devolvida normalmente
   (preço de mercado não é dado pessoal).

---

### User Story 4 - Investidor consegue auditar e desfazer gravações erradas na memória (Priority: P2)

O modelo grava na memória com confirmação do usuário, mas uma gravação
válida pode estar errada (tese mal formulada, regra sobrescrita, resultado
de decisão registrado errado). Hoje não há rastro: o backup de arquivo só
cobre corrupção. O investidor quer um histórico append-only de cada mudança
na memória, com o estado anterior e o novo, para entender o que mudou e
restaurar manualmente o que for preciso.

**Why this priority**: Should no roadmap — escrita válida porém errada é
invisível hoje. Custo baixo, nenhuma mudança de contrato das tools.

**Independent Test**: Executar uma sequência de gravações (criar regra,
atualizar tese, registrar resultado de decisão, definir objetivo, disparar
alerta) e verificar que o histórico tem exatamente um registro por mudança,
cada um com operação, coleção, identificador, estado anterior, estado novo e
horário.

**Acceptance Scenarios**:

1. **Given** uma tese existente, **When** o usuário a atualiza, **Then** o
   histórico ganha um registro com o texto anterior e o novo.
2. **Given** um alerta cujo gatilho é atingido no bootstrap, **When** ele
   transita para disparado, **Then** o histórico ganha um registro para esse
   alerta.
3. **Given** o histórico não pode ser escrito (ex.: sem permissão), **When**
   uma gravação na memória é pedida, **Then** a gravação na memória acontece
   normalmente e o problema do histórico é reportado ao operador, sem
   derrubar a tool.
4. **Given** uma gravação cuja persistência na memória falha, **When** o
   erro é devolvido, **Then** a tentativa fica registrada no histórico (para
   investigação).
5. **Given** o histórico existente, **When** o usuário o inspeciona, **Then**
   ele está ao lado do arquivo de memória, legível linha a linha, com as
   mesmas restrições de permissão do arquivo de memória e fora do controle
   de versão.

---

### User Story 5 - Erros chegam ao agente sinalizados como erro (Priority: P2)

Hoje todo erro previsto chega ao cliente como uma resposta de **sucesso**
cujo conteúdo descreve um erro. Clientes e modelos que olham o sinal de erro
do protocolo não percebem a falha. O agente precisa receber o sinal de erro
do protocolo **e** o código estruturado com a mensagem acionável, para não
tratar falha como dado.

**Why this priority**: Should no roadmap, e exigência da Constituição II.1
(evoluir para sinal duplo). O comportamento de sucesso não muda.

**Independent Test**: Provocar cada código de erro do conjunto fechado
(fonte indisponível, formato inesperado, parâmetros inválidos, memória
indisponível, não encontrado, etc.) e verificar que cada resposta vem
marcada como erro no protocolo e carrega o código e a mensagem.

**Acceptance Scenarios**:

1. **Given** a fonte fora do ar, **When** o agente pede o resumo da
   carteira, **Then** a resposta vem marcada como erro no protocolo e traz o
   código `source_unavailable` com mensagem acionável.
2. **Given** argumentos inválidos para uma tool, **When** a chamada é feita,
   **Then** a resposta vem marcada como erro e traz o código
   `invalid_params`.
3. **Given** um cliente que mostra ao modelo apenas o texto da resposta,
   **When** um erro previsto ocorre, **Then** o código e a mensagem estão
   legíveis nesse texto.
4. **Given** uma chamada bem-sucedida, **When** a resposta é devolvida,
   **Then** ela é idêntica à de antes desta feature (sem sinal de erro).
5. **Given** qualquer mensagem de erro prevista, **When** é lida, **Then**
   nomeia o recurso, a causa e a próxima ação, apontando uma tool do próprio
   servidor quando houver uma aplicável.

---

### User Story 6 - (removida desta spec)

A execução semanal dos testes contra a API real foi movida para o roadmap
(decisão do mantenedor, 27/10/2026): a validação em tempo de execução já
impede que mudança de formato vire dado errado; o aviso antecipado só passa a
valer com usuários além do mantenedor. Numeração mantida para preservar as
referências.

---

### User Story 7 - Inicialização sem inspecionar o diretório corrente (Priority: P3)

A migração de primeira execução (arquivo de memória no diretório corrente →
local canônico do usuário) foi código de transição da distribuição e o
único usuário já migrou em 18/10/2026. Ela mantém uma superfície de risco
(arquivo solto no diretório corrente sendo absorvido, corridas de
verificação, links simbólicos). O mantenedor quer removê-la: o servidor
passa a usar apenas o caminho explícito configurado ou o local canônico.

**Why this priority**: Could no roadmap — dead code de transição; reduz
superfície de ataque e simplifica o bootstrap antes do Desktop.

**Independent Test**: Iniciar o servidor num diretório que contém um arquivo
de memória solto e verificar que ele não é lido, copiado, renomeado nem
alterado, e que o servidor usa o local canônico.

**Acceptance Scenarios**:

1. **Given** um arquivo de memória no diretório corrente e nenhum caminho
   configurado, **When** o servidor inicia, **Then** usa o local canônico e
   o arquivo do diretório corrente permanece intocado.
2. **Given** um caminho de memória configurado explicitamente, **When** o
   servidor inicia, **Then** usa exatamente esse caminho (comportamento
   atual mantido).
3. **Given** o local canônico ausente, **When** o servidor inicia, **Then**
   o diretório é criado com permissão restrita ao usuário e um link
   simbólico no lugar do arquivo canônico continua sendo recusado
   (proteções atuais mantidas).

---

### User Story 8 - Clientes descobrem o propósito do servidor; tools novas seguem uma regra de validação (Priority: P3)

Clientes que leem a descrição geral do servidor (e os registries da spec
005) passam a ver o que o servidor é, por onde começar, o envelope de dados
e o atraso das cotações. Em paralelo, o mantenedor registra a regra de
validação de payloads da fonte para as tools novas da Fase 2, para que elas
nasçam com validação uniforme.

**Why this priority**: Could no roadmap — ganho de descoberta e uma decisão
de design que destrava a Fase 2 sem retrabalho.

**Independent Test**: Listar os metadados do servidor num cliente MCP e
verificar a descrição geral; conferir que a decisão de validação está
registrada como ADR com escopo explícito.

**Acceptance Scenarios**:

1. **Given** um cliente que expõe a descrição geral do servidor, **When**
   ele se conecta, **Then** recebe propósito, ponto de partida
   (`get_session_context`), formato do envelope de dados e atraso das
   cotações — sem persona, idioma ou regras de comportamento do agente.
2. **Given** um cliente que ignora a descrição geral, **When** usa as tools,
   **Then** nenhuma regra do produto se perde (todas continuam nas
   descrições das tools).
3. **Given** a decisão de validação registrada, **When** uma tool nova da
   Fase 2 for desenhada, **Then** a regra diz como validar o payload da
   fonte mantendo o passthrough do dado cru, e diz explicitamente que as
   tools existentes e o schema da memória não são retrofitados.

---

### Edge Cases

- **Processo morre segurando a memória**: a trava é liberada pelo sistema
  operacional com o fim do processo; o próximo processo grava normalmente,
  sem intervenção manual.
- **Arquivo de memória corrompido sob concorrência**: a semântica atual
  (backup `.broken-*` + modo indisponível) continua valendo e é executada uma
  única vez — dois processos não geram dois backups do mesmo arquivo nem
  sobrescrevem o backup um do outro.
- **Arquivo alterado por fora (edição manual)**: a próxima leitura ou
  gravação de qualquer processo parte do conteúdo atual em disco, nunca da
  cópia antiga em memória.
- **Sistema de arquivos sem suporte a trava** (ex.: montagens de rede sem
  serviço de trava): leituras seguem normais; toda gravação é recusada com
  erro estruturado, e o operador recebe mensagem em PT-BR com a causa e o
  conserto (apontar `WALLET_MEMORY_PATH` para um disco local). O servidor
  nunca grava sem proteção nem cria outra memória automaticamente.
- **Memória em pasta sincronizada (Dropbox, iCloud, OneDrive)**: na mesma
  máquina a trava funciona normalmente; entre máquinas a trava não protege
  (cada máquina trava só a cópia local e o serviço de sincronização pode
  gerar cópia em conflito). O servidor não detecta esse caso; a limitação e
  a recomendação de usar uma máquina por vez ficam documentadas.
- **Modo privacidade e memória do investidor**: textos escritos pelo próprio
  usuário (teses, regras, objetivo, notas de decisão) podem conter valores em
  reais; o modo privacidade **não** reescreve texto livre — isso é declarado
  no documento de privacidade.
- **Modo privacidade e contexto de sessão**: os alertas de preço (preços de
  mercado, não montantes da carteira) continuam visíveis; nenhum agregado
  monetário da carteira entra no contexto de sessão.
- **Modo privacidade e cache**: alternar o modo entre execuções nunca faz um
  dado não mascarado em cache aparecer numa resposta mascarada.
- **Histórico de mudanças crescendo**: sem rotação nesta feature
  (usuário único, escrita em escala humana); o crescimento é documentado.
- **Histórico com caminho de memória explícito**: o histórico acompanha o
  arquivo de memória configurado (fica ao lado dele), não o local canônico.
- **Cliente que descarta o conteúdo estruturado em respostas de erro**: o
  texto da resposta continua carregando código e mensagem.
- **Exceção inesperada (bug)**: continua sendo reportada como falha, com
  detalhe sanitizado e log no servidor — não é convertida num código do
  conjunto fechado (Constituição II.3).
- **Usuário que nunca migrou** (instalação antiga via clone, com memória só
  no diretório do repositório): fica sem a memória após atualizar; a nota de
  release explica como apontar o caminho explícito ou mover o arquivo.

## Requirements *(mandatory)*

### Functional Requirements

**Concorrência da memória (US1)**

- **FR-001**: Toda gravação na memória do investidor DEVE ser serializada
  entre processos que compartilham o mesmo arquivo: no máximo um processo
  grava por vez.
- **FR-002**: Toda gravação DEVE partir do conteúdo atual em disco
  (ler-modificar-gravar sob a mesma trava), de forma que nenhuma gravação
  confirmada de outro processo seja descartada.
- **FR-003**: Leituras da memória DEVEM refletir o conteúdo atual em disco
  quando ele tiver mudado desde a última leitura do processo.
- **FR-004**: A geração de identificadores e as transições de estado de
  alertas DEVEM ocorrer sob a mesma trava, garantindo identificadores únicos
  e transições terminais aplicadas uma única vez.
- **FR-005**: Quando a trava não puder ser obtida dentro do tempo máximo de
  espera, a tool DEVE devolver erro estruturado do conjunto fechado
  indicando memória ocupada, com mensagem acionável de nova tentativa, sem
  gravação parcial.
- **FR-006**: A gravação atômica e a semântica de degradação existentes
  (backup de arquivo corrompido, modo indisponível) DEVEM ser preservadas.
- **FR-038**: FR-001 a FR-006 DEVEM valer em macOS, Linux e Windows. No
  Windows, a gravação atômica DEVE funcionar mesmo com outro processo do
  servidor com o arquivo de memória aberto, e a recusa de link simbólico no
  arquivo canônico DEVE ser mantida. Windows entra na matriz de CI.
- **FR-039**: Quando o sistema de arquivos não suportar a trava, as
  leituras DEVEM continuar funcionando e toda gravação DEVE ser recusada com
  erro estruturado do conjunto fechado; o operador DEVE receber mensagem em
  PT-BR com causa e conserto. O servidor NÃO DEVE gravar sem trava nem
  trocar automaticamente para outro arquivo de memória.

**Documento de privacidade (US2)**

- **FR-007**: O produto DEVE publicar um documento de privacidade em PT-BR
  com a tabela "o que vai para onde" (fonte pública, provedor do modelo,
  arquivo local), o modelo de ameaça (o identificador/link da carteira é a
  credencial; o mascaramento do site é apenas visual), o que o modo
  privacidade preserva e perde, e a nota de que privacidade total exige
  modelo de linguagem local. O README DEVE documentar que memória em pasta
  sincronizada é segura na mesma máquina, mas não no uso simultâneo em duas
  máquinas.
- **FR-008**: O README e a saída do assistente de instalação DEVEM apontar
  para o documento de privacidade.

**Modo privacidade (US3)**

- **FR-009**: O modo privacidade DEVE ser ativado exclusivamente por
  configuração de ambiente do servidor (`WALLET_MASK_VALUES`); nenhuma tool
  DEVE aceitar parâmetro que o ligue ou desligue.
- **FR-010**: Com o modo ativo, as respostas das tools de carteira DEVEM
  omitir montantes monetários e quantidades (patrimônio, valor aplicado,
  lucro em reais, quantidade, patrimônio por ativo, proventos recebidos e
  proventos em reais) e preservar percentuais, razões, indicadores e notas.
- **FR-011**: A filtragem DEVE ser por lista de campos permitidos: um campo
  da fonte só aparece mascarado se for reconhecidamente não monetário;
  campos desconhecidos são omitidos.
- **FR-012**: Respostas mascaradas DEVEM indicar explicitamente que
  montantes foram omitidos pelo modo privacidade, e as descrições das tools
  DEVEM instruir o modelo a não estimar nem reconstruir os valores omitidos.
- **FR-013**: Tools cuja informação é essencialmente monetária
  (`get_patrimony_history` e `get_earnings`) DEVEM, com o modo ativo,
  devolver erro estruturado do conjunto fechado indicando indisponibilidade
  no modo privacidade; o servidor NÃO DEVE substituí-las por razões
  derivadas calculadas por ele.
- **FR-014**: Valor não reconhecido na variável de ambiente DEVE abortar a
  inicialização com mensagem em PT-BR listando os valores aceitos.
- **FR-015**: Cotações de mercado de ativos NÃO DEVEM ser afetadas pelo modo
  privacidade.

**Histórico de mudanças da memória (US4)**

- **FR-016**: Toda mutação da memória — criação e atualização em qualquer
  coleção, definição do objetivo da carteira e cada alerta que transita para
  disparado — DEVE gerar exatamente um registro append-only com operação,
  coleção, identificador, estado anterior, estado novo e horário.
- **FR-017**: O registro DEVE ser escrito antes da persistência da memória;
  mutações cuja persistência falha também ficam registradas.
- **FR-018**: Falha ao escrever o histórico NÃO DEVE derrubar a operação de
  memória; o problema é reportado ao operador.
- **FR-019**: O histórico DEVE ficar ao lado do arquivo de memória em uso,
  com as mesmas restrições de permissão dele, e DEVE estar excluído do
  controle de versão do projeto.
- **FR-020**: O histórico NÃO DEVE alterar o schema da memória nem o
  contrato de nenhuma tool.

**Sinal duplo de erro (US5)**

- **FR-021**: Todo erro previsto — devolvido pelas tools ou pela camada de
  validação de parâmetros — DEVE ser marcado como erro no protocolo **e**
  carregar o envelope estruturado com código do conjunto fechado e mensagem.
- **FR-022**: O código e a mensagem do erro DEVEM estar presentes também no
  texto da resposta, para clientes que não exibem conteúdo estruturado.
- **FR-023**: As mensagens de erro previstas DEVEM ser revisadas no estilo
  recurso + causa + próxima ação, nomeando tool do servidor quando aplicável.
- **FR-024**: Respostas de sucesso NÃO DEVEM mudar.
- **FR-025**: A decisão sobre incluir no envelope uma indicação de
  retentabilidade/categoria do erro DEVE ser tomada e registrada (ADR),
  qualquer que seja o resultado.

FR-026 a FR-028 (execução semanal dos testes contra a API real) foram
movidos para o roadmap junto com a US6.

**Remoção da migração legada (US7)**

- **FR-029**: A resolução do caminho da memória DEVE se limitar a: caminho
  explícito configurado (usado como dado) ou local canônico do usuário
  (criado com permissão restrita); o diretório corrente NÃO DEVE ser lido.
- **FR-030**: As proteções do local canônico (diretório restrito ao usuário,
  recusa de link simbólico no arquivo canônico) DEVEM ser mantidas.
- **FR-031**: A remoção DEVE vir acompanhada de: atualização do ADR-0010
  (condição de invalidação nº 1 antecipada), atualização dos contratos da
  spec 002 afetados e nota de release orientando quem ainda tenha memória no
  diretório do repositório.

**Descoberta e regra de validação (US8)**

- **FR-032**: O servidor DEVE expor uma descrição geral com propósito e
  índice de uso (o que é, por onde começar, envelope de dados, atraso das
  cotações) e NÃO DEVE incluir persona, idioma ou comportamento do agente.
- **FR-033**: Nenhuma invariante do produto DEVE depender da descrição geral;
  as regras de uso permanecem nas descrições das tools.
- **FR-034**: A regra de validação de payloads da fonte para tools novas
  DEVE ser registrada como ADR: validação declarativa por endpoint, devolução
  do dado cru (passthrough preservado), cobertura de booleano-vs-inteiro e
  de números não finitos, e não retrofit das tools existentes nem do schema
  da memória.

**Transversais**

- **FR-035**: Mensagens ao operador em PT-BR e ao modelo em inglês
  (ADR-0009).
- **FR-036**: Todo novo código de erro entra no conjunto fechado documentado
  (ADR-0007), com teste de contrato.
- **FR-037**: A versão publicada após esta feature DEVE documentar no
  changelog do projeto cada mudança visível ao usuário (modo privacidade,
  sinal de erro, remoção da migração, histórico da memória).

### Key Entities *(include if feature involves data)*

- **Memória do investidor**: arquivo único por usuário, compartilhado por
  todos os processos do servidor na máquina; schema inalterado nesta
  feature.
- **Trava da memória**: garante exclusão mútua entre processos durante
  ler-modificar-gravar; liberada automaticamente se o processo morre.
- **Registro de mudança**: entrada append-only {operação, coleção,
  identificador, estado anterior, estado novo, horário}; arquivo irmão da
  memória, mesmo nível de sensibilidade.
- **Configuração do modo privacidade**: valor de ambiente lido na
  inicialização; liga/desliga a filtragem de montantes para todo o processo.
- **Lista de campos permitidos no modo privacidade**: por tool, os campos
  não monetários que podem atravessar; tudo fora dela é omitido.
- **Envelope de erro**: código do conjunto fechado + mensagem acionável,
  agora acompanhado do sinal de erro do protocolo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em teste com 2 processos concorrentes realizando 100
  gravações intercaladas cada, 100% das 200 gravações estão presentes no
  arquivo final, com identificadores únicos — em macOS, Linux e Windows.
- **SC-002**: Uma gravação feita num processo aparece na próxima leitura do
  outro processo em 100% dos casos testados, sem reinício.
- **SC-003**: Com o modo privacidade ativo, 0 montantes em reais e 0
  quantidades aparecem nas respostas de todas as tools de carteira contra a
  fixtures com todos os campos do payload real, e 100% dos percentuais de alocação continuam presentes.
- **SC-004**: 100% das mutações da memória exercitadas em teste geram
  exatamente um registro no histórico, e a partir do histórico é possível
  recuperar o valor anterior de qualquer entrada alterada.
- **SC-005**: 100% dos códigos de erro do conjunto fechado chegam marcados
  como erro no protocolo, com código e mensagem legíveis no texto da
  resposta; 0 mudanças nas respostas de sucesso.
- **SC-007**: Um leitor novo responde corretamente, apenas com o documento
  de privacidade, às quatro perguntas: o que vai ao Investidor10, o que vai
  ao provedor do modelo, o que fica local, e por que o link da carteira é a
  credencial.
- **SC-008**: Na inicialização, 0 arquivos fora do caminho configurado ou do
  local canônico são lidos ou alterados.
- **SC-009**: A suíte de testes existente (não live) continua verde, com os
  testes de migração legada removidos e novos testes cobrindo cada FR.

## Assumptions

- **Plataformas**: a trava entre processos cobre macOS, Linux e Windows, via
  biblioteca de trava multiplataforma autorizada pela emenda 1.2.0 da
  Constituição (V.1); a biblioteca específica e a versão pinada são
  escolhidas no plan e registradas em ADR (atualiza o ADR-0001 §4). O porte
  do armazenamento da memória para Windows (gravação atômica com arquivo
  aberto, permissões, links simbólicos) está no escopo desta feature, o que
  adianta parte do trabalho da spec 005.
- **Permissões no Windows**: o local canônico fica no perfil do usuário,
  cujo controle de acesso padrão já restringe ao próprio usuário; o servidor
  não tenta reproduzir as permissões 0700/0600 do POSIX nem altera ACLs.
- **Tempo máximo de espera pela trava**: alguns segundos (padrão de 5 s) —
  gravações são de escala humana e seguram a trava por milissegundos.
- **Valores aceitos para `WALLET_MASK_VALUES`**: equivalentes a ligado
  (`1`, `true`, `yes`, `on`) e desligado (`0`, `false`, `no`, `off`, ausente),
  sem diferenciar maiúsculas; ausente = desligado.
- **Preço médio por ativo** não é montante da carteira (é preço por unidade,
  sem a quantidade não revela o tamanho da posição) e pode atravessar o modo
  privacidade; a lista final de campos permitidos por tool é fechada no plan.
- **Proventos no modo privacidade**: a tool de proventos fica indisponível
  (FR-013); a skill "resumo de dividendos" degrada para o erro estruturado e
  o documento de privacidade lista essa perda. Indicadores de DY por ativo
  em `get_wallet_positions` continuam disponíveis.
- **Avaliação Ollama local fica fora** desta feature (Won't agora no
  roadmap); o documento de privacidade apenas declara que privacidade total
  exige modelo local.
- **Rotação do histórico de mudanças** fica fora (crescimento documentado).
- **Remoção da migração legada antecipada** (em vez de esperar a 1.0.0):
  decisão do mantenedor de 27/10/2026 ao incluir o item na spec 004; único
  usuário conhecido já migrou.
- **Regra de validação** é decisão de design registrada; nenhuma tool nova
  é implementada nesta feature e ela não adiciona dependência de runtime (a
  biblioteca de validação já é transitiva do framework; o ADR trata a
  compatibilidade com a Constituição V.1). A única dependência de runtime
  nova desta feature é a biblioteca de trava.
- Mudanças em canais de erro e no contrato das tools exigem ADR + testes de
  contrato verdes (Constituição, Gates de Compliance); o fundamento de
  protocolo do sinal duplo é a pesquisa
  `docs/research/tool-error-channels.md`, revalidada contra a documentação
  oficial vigente no plan (Constituição I).
