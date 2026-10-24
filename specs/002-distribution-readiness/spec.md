# Feature Specification: Prontidão para distribuição do produto (Fase 0 do ROADMAP)

**Feature Branch**: `002-distribution-readiness`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "Continuar o próximo ciclo de implementações do ROADMAP (Fase 0 — correções de produto que bloqueiam distribuição): remover o WALLET_ID pessoal do default, empacotar no PyPI com install de uma linha, path de memória estável por usuário e onboarding de primeira execução. Contexto: ADRs 0001–0008, research de comportamento de agente e canais de erro, e learning lessons de paginação/cotação/proventos/bola de neve."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalação e execução em uma linha, sem clonar repositório (Priority: P1)

Um novo usuário descobre o projeto e quer conectar seu agente (Claude Desktop/Code, Devin) à própria carteira do Investidor10. Ele **não clona repositório**: instala e executa o servidor com um único comando a partir de um registro público de pacotes e configura o cliente do agente com esse comando. Ao atualizar, repete o mesmo fluxo e recebe a versão nova.

**Why this priority**: É o que reduz fricção de verdade (ROADMAP Fase 0) — hoje a adoção exige clonar o repo e conhecer `uv --directory`. Sem distribuição empacotada, nenhum dos outros ganhos de produto alcança usuários novos. Depende do caminho de memória estável (US3), pois sem repo dir o default relativo quebra.

**Independent Test**: Em uma máquina limpa (sem o repositório clonado), seguir apenas a documentação de instalação e chegar a uma sessão de agente funcionando contra a própria carteira, usando exclusivamente o comando publicado.

**Acceptance Scenarios**:

1. **Given** uma máquina sem o repositório clonado, **When** o usuário executa o comando de instalação/execução de uma linha documentado, **Then** o servidor inicia e responde às tools do agente sem nenhum checkout de código.
2. **Given** uma versão anterior instalada, **When** o usuário atualiza pelo mecanismo padrão do comando, **Then** a nova versão assume e a memória existente continua legível e íntegra.
3. **Given** uma nova versão publicada, **When** o usuário consulta o histórico de mudanças do produto, **Then** existe um changelog descrevendo o que mudou naquela versão.

---

### User Story 2 - O produto nunca opera com a carteira de outra pessoa (Priority: P1)

Um usuário configura o servidor pela primeira vez. Se ele esquecer de informar o identificador da própria carteira (`WALLET_ID`), o servidor **não inicia** — em vez de silenciosamente usar a carteira do autor do projeto — e exibe uma mensagem clara explicando o que configurar e onde encontrar o ID (está na URL pública da carteira no site).

**Why this priority**: Produto não pode nascer com a carteira do autor como default (ROADMAP Fase 0): expõe dados financeiros alheios e produz análises sobre a carteira errada sem que o usuário perceba. É requisito de confiança básica que bloqueia distribuição.

**Independent Test**: Iniciar o servidor sem `WALLET_ID` definido e verificar que a inicialização aborta imediatamente com instrução acionável (não um traceback), sem realizar nenhuma chamada à fonte de dados.

**Acceptance Scenarios**:

1. **Given** `WALLET_ID` ausente ou vazio, **When** o servidor é iniciado, **Then** a inicialização aborta com código de saída de erro e mensagem nomeando a variável faltante e como obter o ID na URL pública da carteira.
2. **Given** `WALLET_ID` com valor não numérico, **When** o servidor é iniciado, **Then** a falha segue o comportamento já decidido no ADR-0003 §3 (erro estruturado de startup, sem traceback).
3. **Given** `WALLET_ID` válido, **When** o servidor inicia, **Then** nenhum dado de carteira alheia é acessível — todas as consultas têm como alvo exclusivamente a carteira configurada.

---

### User Story 3 - Memória confiável e compartilhada entre todos os clientes (Priority: P2)

O usuário usa o mesmo servidor a partir de clientes diferentes (Claude Desktop no GUI, Claude Code/Devin no terminal). Independentemente do diretório de trabalho de cada cliente, todos leem e escrevem **o mesmo arquivo de memória**, em um local estável do usuário que não depende de onde o código está instalado. Quem já usava o produto com a memória no diretório do repositório tem seus dados migrados sem perda.

**Why this priority**: Sem isso, cada cliente cria uma memória própria e o recurso central do produto (memória persistente do investidor, ADR-0006) diverge silenciosamente por cliente. Também é pré-requisito explícito do empacotamento: com instalação sem repo dir, o default relativo deixa de existir.

**Independent Test**: Registrar uma tese via um cliente, abrir sessão em outro cliente com diretório de trabalho diferente e verificar que a tese aparece no contexto de bootstrap — sem nenhuma configuração de caminho adicional.

**Acceptance Scenarios**:

1. **Given** nenhum arquivo de memória existente, **When** o servidor inicia a partir de qualquer diretório, **Then** a memória é criada no local estável e canônico do usuário, com as mesmas permissões restritas já decididas (ADR-0004 §6).
2. **Given** dois clientes configurados sem nenhum override de caminho, **When** um deles registra memória e o outro abre sessão, **Then** o segundo cliente enxerga o registro.
3. **Given** uma instalação legada com memória no diretório do repositório e nenhum arquivo no local canônico, **When** a nova versão inicia, **Then** os dados legados passam a valer no local canônico sem perda de nenhuma coleção, e o usuário é informado da migração.
4. **Given** memória existente tanto no local legado quanto no canônico, **When** o servidor inicia, **Then** o arquivo canônico prevalece, o legado não é apagado (preservado como backup identificável) e o usuário é avisado da divergência.
5. **Given** um override explícito de caminho configurado pelo usuário, **When** o servidor inicia, **Then** o override é respeitado e a migração automática não interfere.

---

### User Story 4 - Primeira execução guiada e sem armadilhas (Priority: P2)

Um usuário não técnico conclui a configuração seguindo a documentação em PT-BR. O onboarding valida a carteira configurada na primeira execução (ela existe e é pública) e, se algo está errado — ID inválido, carteira privada — o erro é amigável e ensina a corrigir. A documentação antecipa a armadilha nº 1 dos apps GUI no macOS: eles não herdam o PATH do shell, então a configuração precisa do **caminho absoluto do executável**, e o erro clássico "MCP failed to connect" é explicado.

**Why this priority**: É o que transforma "instalou" em "funcionou" para o público-alvo. Sem onboarding validado, o produto distribuído gera frustração (carteira privada, PATH do Desktop) nos dois primeiros minutos de uso.

**Independent Test**: Executar o fluxo de primeira execução com (a) carteira pública válida, (b) ID inexistente e (c) carteira privada, e verificar que cada caso produz orientação específica e correta, em PT-BR, sem inspeção de logs.

**Acceptance Scenarios**:

1. **Given** uma carteira pública válida, **When** o usuário completa a configuração e inicia a primeira sessão, **Then** a validação inicial confirma a carteira e o agente já responde com dados reais.
2. **Given** um ID de carteira inexistente ou uma carteira privada, **When** ocorre a primeira execução, **Then** o usuário recebe mensagem clara distinguindo os dois casos e orientando a tornar a carteira pública ou corrigir o ID.
3. **Given** um usuário de app GUI (Claude Desktop) no macOS, **When** ele segue a documentação de configuração do cliente, **Then** a doc o instrui a usar o caminho absoluto do executável e ele não depende de PATH de shell.
4. **Given** qualquer falha de configuração no onboarding, **When** ela ocorre, **Then** a mensagem nomeia o recurso que falhou, a causa provável e o próximo passo — nunca um traceback cru (coerente com ADR-0003 §3 e a pesquisa de canais de erro).

---

### Edge Cases

- **Duas instalações convivendo** (repositório clonado + pacote instalado): ambas convergem para o mesmo arquivo de memória canônico; a instalação legada migra na primeira execução da versão nova (US3, cenários 3–4).
- **Diretório de dados do usuário não gravável ou inexistente**: a criação da memória falha com mensagem acionável indicando o caminho tentado e a permissão necessária, sem traceback.
- **Usuário com necessidades de múltiplas memórias** (ex.: mais de uma carteira no futuro): o override explícito de caminho continua disponível e documentado.
- **Atualização com memória em schema antigo**: o comportamento de degrade/backup já decidido (ADR-0002) segue valendo; a migração de caminho não altera o schema.
- **Ambiente sem acesso à rede na primeira execução**: a validação da carteira reporta indisponibilidade da fonte distinta de "carteira inválida".
- **Publicação com número de versão já usado**: o processo de release rejeita duplicatas — cada release tem versão semântica única e changelog correspondente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O produto MUST ser publicado em registro público de pacotes, instalável e executável com um único comando documentado, sem exigir clone do repositório.
- **FR-002**: O produto MUST remover qualquer identificador de carteira embutido como default; sem `WALLET_ID` definido, a inicialização MUST abortar com código de erro e mensagem acionável explicando como obter o ID na URL pública da carteira.
- **FR-003**: O caminho default da memória MUST ser `~/.investidor10/memory.json` — local estável por usuário, independente do diretório de trabalho do processo, de modo que todos os clientes locais compartilhem o mesmo arquivo por padrão. A escolha mantém o runtime sem novas dependências (coerente com ADR-0001) e um caminho previsível e idêntico em todo SO, fácil de o usuário inspecionar.
- **FR-004**: O override explícito do caminho da memória via configuração MUST continuar funcionando e ter precedência sobre o novo default e sobre a migração.
- **FR-005**: Na primeira execução com o novo default, memória legada existente no diretório do repositório MUST ser migrada para o local canônico sem perda de dados; se o destino já existir, o canônico prevalece e o legado é preservado como backup identificável, com aviso ao usuário.
- **FR-006**: A primeira execução MUST incluir validação da carteira configurada (existe e é pública), com erro amigável em PT-BR distinguindo ID inexistente, carteira privada e fonte indisponível.
- **FR-007**: A documentação de onboarding MUST estar em PT-BR e MUST cobrir: obtenção do `WALLET_ID`, exigência de carteira pública e a configuração de clientes GUI no macOS com caminho absoluto do executável (a principal causa de "MCP failed to connect").
- **FR-008**: Cada release público MUST ter versão semântica única e entrada correspondente em changelog mantido no projeto.
- **FR-009**: Verificações automatizadas de qualidade (testes, hooks pré-commit e integração contínua) MUST rodar em cada alteração proposta antes de qualquer publicação.
- **FR-010**: Nenhuma tool existente, o envelope `{cached, fetched_at, data}`, o conjunto fechado de erros (ADR-0007) ou a semântica de memória/alertas (ADRs 0002/0006) MUST mudar de comportamento observável — as únicas mudanças deliberadas de contrato são a exigência do `WALLET_ID` e o novo caminho default da memória.
- **FR-011**: Arquivos de memória, backup e log locais MUST manter as permissões restritas por usuário já decididas (ADR-0004 §6), inclusive no novo local canônico.

### Key Entities

- **Configuração do cliente do agente**: o par comando + variáveis (`WALLET_ID`, overrides) que o usuário registra em cada cliente (Desktop, Code, Devin); unificada pelo caminho canônico da memória.
- **Arquivo de memória**: único, versionado, compartilhado entre clientes; existe em no máximo dois lugares durante a transição (legado no repo dir, canônico no local estável).
- **Release**: versão semântica publicada no registro de pacotes, acompanhada de changelog e dos gates de qualidade.
- **Carteira alvo**: identificada exclusivamente pelo `WALLET_ID` configurado pelo usuário; precisa ser pública; validada na primeira execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário novo vai de "conheceu o projeto" a "sessão funcionando com a própria carteira" em menos de 10 minutos seguindo apenas a documentação, sem clonar repositório.
- **SC-002**: 100% das inicializações sem carteira configurada abortam com instrução acionável (não traceback) e zero chamadas à fonte de dados; em nenhum cenário dados de carteira de terceiros são exibidos.
- **SC-003**: Memória registrada por um cliente é visível em outro cliente em 100% dos casos sem configuração adicional de caminho.
- **SC-004**: 100% das falhas de configuração previstas no onboarding (ID ausente, ID inválido, carteira privada, executável fora do PATH em GUI) produzem orientação específica documentada — nenhuma exige inspeção de logs para diagnosticar.
- **SC-005**: A migração do caminho de memória preserva 100% das coleções e entradas do arquivo legado em todos os cenários (destino ausente, destino presente, override ativo).
- **SC-006**: 100% dos releases públicos têm versão semântica única e entrada de changelog; nenhuma publicação ocorre com os gates de qualidade falhando.

## Assumptions

- O escopo deste ciclo é a Fase 0 completa do ROADMAP; itens da Fase 1 (file lock na memória, changelog append-only, sinal duplo `is_error`, modo privacidade) ficam para o ciclo seguinte.
- A publicação no registro de pacotes é executada pelo mantenedor com credenciais próprias; a spec cobre o produto empacotável/publicável, não a gestão de credenciais do registro.
- Usuários-alvo têm Python/`uv` disponível ou seguem o passo único de instalação documentado; o comando de uma linha assume um executor de pacotes por demanda (modelo `uvx`).
- O nome do pacote já definido no projeto (`mcp-investidor10-wallet`) é mantido.
- O escopo continua single-user, local e stdio, e a única fonte de dados segue sendo a carteira pública do Investidor10 (ADRs 0004/0005) — nada neste ciclo abre transporte de rede, multiusuário ou novos destinos de dados.
- Mensagens voltadas ao operador/usuário final seguem em PT-BR; textos de contrato com o modelo (docstrings) permanecem em inglês, conforme decisão já registrada (ADR-0007 §4).
- Integração contínua usa o serviço padrão gratuito da plataforma onde o repositório já está hospedado.
