# Feature Specification: Agente de Investimentos conectado à Carteira Investidor10

**Feature Branch**: `001-mcp-investidor10-wallet`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Criar integração de um agente para uma carteira de investimentos no Investidor10. O agente deve ver a carteira, gerar insights e reflexões a partir de dados, consultar cotações em tempo quase real, ler eventos sobre os ativos, entender o racional de investimento do usuário, ativar alertas de preços, sugerir rebalanceamento, gerar relatórios a partir de buscas na web sobre os ativos. Em suma: um assistente de investimentos completo que cuida da carteira. Sem frontend — a interface é o cliente de agente (Claude Desktop/Code/Desktop, Devin) via conector MCP."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visão completa da carteira sob demanda (Priority: P1)

O usuário abre uma conversa com o agente e pergunta "como está minha carteira?". O agente responde com patrimônio total, valor aplicado, rentabilidade (total e 12 meses), alocação por classe de ativos e por ativo, e a lista de posições com preço médio, cotação atual, rentabilidade e indicadores fundamentalistas — cobrindo todas as classes da carteira (ações BR, FIIs, ETFs internacionais, Tesouro Direto e criptomoedas).

**Why this priority**: É o fundamento de todas as demais capacidades. Sem acesso confiável e completo aos dados da carteira, nenhum insight, alerta ou relatório é possível. Entrega valor imediato mesmo sozinho (MVP).

**Independent Test**: Pode ser testado perguntando ao agente "qual o resumo da minha carteira?" e conferindo se os números apresentados batem exatamente com os exibidos na página pública da carteira, para todas as classes de ativos.

**Acceptance Scenarios**:

1. **Given** o agente configurado com uma carteira pública válida, **When** o usuário pede o resumo da carteira, **Then** o agente apresenta patrimônio, valor aplicado, variação e rentabilidade total e de 12 meses, com valores idênticos aos da fonte.
2. **Given** uma carteira com posições em múltiplas classes, **When** o usuário pede as posições, **Then** o agente lista todas as classes com todos os ativos de cada uma, incluindo preço médio, cotação, equity, rentabilidade e indicadores (P/L, P/VP, DY, ROE quando aplicável).
3. **Given** uma carteira com ativos em moeda estrangeira, **When** o usuário pede a alocação consolidada, **Then** o agente apresenta valores consolidados e sinaliza a conversão cambial quando relevante.
4. **Given** a fonte de dados temporariamente indisponível, **When** o usuário pede o resumo, **Then** o agente informa claramente a indisponibilidade e, se houver dados em cache recentes, os apresenta com indicação explícita da idade dos dados.

---

### User Story 2 - Insights de rebalanceamento e aporte (Priority: P2)

O usuário pergunta "onde devo aportar este mês?" ou "minha carteira está desbalanceada?". O agente compara a alocação atual de cada ativo e classe contra a alocação ideal definida na carteira, identifica concentrações excessivas (ex.: ativo com o dobro do peso ideal) e indica candidatos a aporte cruzando a distância do percentual ideal com a recomendação de compra disponível na fonte de dados.

**Why this priority**: É o principal insight acionável que os dados da carteira já permitem gerar sem dependências externas. Transforma dados em decisão.

**Independent Test**: Pode ser testado perguntando "quais ativos estão acima do peso ideal?" e verificando se a resposta corresponde exatamente à diferença entre percentual atual e percentual ideal de cada ativo, incluindo o caso conhecido de concentração excessiva.

**Acceptance Scenarios**:

1. **Given** uma carteira com pelo menos um ativo acima do percentual ideal, **When** o usuário pede análise de rebalanceamento, **Then** o agente lista os desvios por ativo e por classe, ordenados por magnitude.
2. **Given** um valor disponível para aporte informado pelo usuário, **When** o usuário pede sugestão de aporte, **Then** o agente sugere uma distribuição priorizando ativos abaixo do peso ideal e com recomendação de compra positiva, sem sugerir venda de ativos a menos que solicitado.
3. **Given** uma carteira perfeitamente alinhada ao ideal, **When** o usuário pede análise de rebalanceamento, **Then** o agente informa que não há desvios relevantes e não força sugestões.

---

### User Story 3 - Memória de longo prazo e contexto do investidor (Priority: P2)

O agente aprende e lembra o racional do usuário: teses de investimento por ativo, regras pessoais (ex.: "só compro se a recomendação for positiva", "DY mínimo de X%"), objetivo da carteira (ex.: aposentadoria), decisões passadas com data e justificativa, e alertas já comunicados. No início de cada sessão, o agente consegue responder "o que mudou desde nossa última conversa" e não repete alertas ou insights já dados.

**Why this priority**: É o que diferencia um assistente "que cuida da carteira" de um simples consultor de dados. Sem memória, cada sessão recomeça do zero e insights se repetem.

**Independent Test**: Pode ser testado registrando uma tese e uma decisão em uma sessão, encerrando-a, abrindo nova sessão e verificando se o agente recupera espontaneamente o contexto ao ser perguntado sobre o ativo ou sobre mudanças recentes.

**Acceptance Scenarios**:

1. **Given** que o usuário explicou uma tese de investimento para um ativo, **When** uma nova sessão é iniciada dias depois, **Then** o agente recupera a tese ao discutir o ativo, citando data do registro.
2. **Given** uma recomendação feita e recusada pelo usuário com justificativa, **When** o agente analisa a carteira novamente, **Then** ele não repete a mesma recomendação sem novo fundamento e reconhece a recusa anterior.
3. **Given** um alerta de concentração já comunicado, **When** a condição persiste na sessão seguinte, **Then** o agente menciona a persistência sem reapresentar o alerta como novidade.

---

### User Story 4 - Cotações e fundamentos em tempo quase real (Priority: P2)

O usuário pergunta sobre um ativo específico (da carteira ou não): "vale a pena comprar PETR4 hoje?". O agente consulta cotação atual, variação do dia e de 12 meses, indicadores de valuation (preço justo de Graham e Bazin, P/L, P/VP), dividend yield, setor e, se necessário, a página fundamentalista completa do ativo.

**Why this priority**: Complementa a visão estática da carteira com dados de mercado para decisões no presente. Depende da Story 1 apenas para contextualizar posição existente.

**Independent Test**: Pode ser testado perguntando a cotação e indicadores de um ticker conhecido e conferindo se os valores batem com os exibidos na fonte no mesmo momento, com indicação da defasagem inerente (até ~15 min na B3).

**Acceptance Scenarios**:

1. **Given** um ticker válido, **When** o usuário pede a cotação, **Then** o agente apresenta preço, variações e principais indicadores, sinalizando a defasagem da fonte.
2. **Given** um ticker inexistente ou inválido, **When** o usuário pede a cotação, **Then** o agente informa que o ativo não foi encontrado e, quando possível, sugere grafias similares.
3. **Given** um ativo da carteira, **When** o usuário pede análise, **Then** o agente cruza a cotação atual com o preço médio da posição e o percentual na carteira.

---

### User Story 5 - Renda passiva e evolução patrimonial (Priority: P3)

O usuário pergunta "quanto recebi de proventos nos últimos 12 meses?" ou "como meu patrimônio evoluiu?". O agente apresenta proventos por período (com filtro por datas), yield on cost por ativo, projeção de renda passiva e a evolução mensal do patrimônio separando valor aplicado de ganho de capital.

**Why this priority**: Alto valor para o objetivo de aposentadoria, mas depende das stories anteriores para contextualização e é menos crítico que visão geral e rebalanceamento.

**Independent Test**: Pode ser testado pedindo os proventos de um período conhecido e conferindo o total contra o valor exibido na fonte para as mesmas datas.

**Acceptance Scenarios**:

1. **Given** um período informado, **When** o usuário pede os proventos recebidos, **Then** o agente apresenta o total e o detalhamento disponível para exatamente aquele intervalo.
2. **Given** um período sem proventos, **When** o usuário consulta, **Then** o agente informa ausência de proventos sem tratar como erro.
3. **Given** uma solicitação de evolução patrimonial, **When** o usuário escolhe o horizonte (ex.: 12, 24, 60 meses), **Then** o agente apresenta a série mensal separando aportes de valorização.

---

### User Story 6 - Alertas de preço e relatórios enriquecidos (Priority: P3)

O usuário pede "me avise quando PETR4 cair abaixo de R$ 30" ou "gere um relatório sobre VALE3 com as últimas notícias". O agente registra alertas de preço e gera relatórios combinando dados da carteira, indicadores fundamentalistas e pesquisa na web sobre eventos recentes do ativo (resultados, notícias, fatos relevantes).

**Why this priority**: Completa a visão de "assistente completo", mas depende de mecanismos de entrega/pesquisa que vão além dos dados da carteira. Alertas de preço são persistidos e verificados no início de cada sessão de conversa (não há monitoramento contínuo fora do chat neste escopo).

**Independent Test**: Pode ser testado registrando um alerta para um preço já atingido (condição imediatamente verdadeira) e verificando se o agente o dispara no próximo ponto de verificação definido, e pedindo um relatório de um ativo e conferindo se ele combina dados quantitativos da carteira com eventos recentes citados com fontes.

**Acceptance Scenarios**:

1. **Given** um alerta de preço registrado, **When** uma nova sessão é iniciada e a condição de preço está satisfeita, **Then** o agente informa o alerta no início da sessão com data/hora do registro e preço atual, e o alerta é marcado como disparado (não dispara novamente).
2. **Given** um pedido de relatório sobre um ativo, **When** o agente gera o relatório, **Then** ele inclui posição na carteira (se houver), indicadores fundamentalistas atuais e eventos recentes encontrados na web com referências.
3. **Given** ausência de notícias recentes relevantes, **When** o relatório é gerado, **Then** o agente declara explicitamente a ausência em vez de preencher com conteúdo genérico.

---

### Edge Cases

- Fonte de dados da carteira indisponível, fora do ar ou com formato de resposta alterado: o agente deve falhar de forma explícita e informativa, nunca inventando valores.
- Carteira configurada torna-se privada ou o identificador é inválido: o agente deve detectar a falha de acesso e orientar o usuário a verificar a configuração.
- Classe de ativos sem posições: listagens devem retornar vazio de forma clara, sem erro.
- Datas de proventos invertidas (início posterior ao fim): o agente deve corrigir ou questionar o usuário em vez de retornar resultado vazio silencioso.
- Memória corrompida ou arquivo inacessível: o agente deve operar em modo sem memória, avisando o usuário, sem perder as demais capacidades.
- Ativos com indicadores não aplicáveis (ex.: P/L de FII, DY de Tesouro Prefixado): omissão explícita, nunca valor inventado.
- Múltiplas consultas em sequência na mesma sessão: respostas devem usar dados recentes sem martelar a fonte (reuso de dados dentro da janela de cache).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O agente MUST consultar e apresentar o resumo da carteira: valor aplicado, patrimônio (equity), variação e rentabilidade total e de 12 meses.
- **FR-002**: O agente MUST consultar e apresentar a alocação da carteira por ativo e por classe de ativos.
- **FR-003**: O agente MUST listar posições detalhadas por classe — cobrindo ações BR, FIIs, ETFs internacionais, Tesouro Direto e criptomoedas — incluindo quantidade, preço médio, cotação atual, equity, rentabilidade, percentual na carteira, percentual ideal e indicadores fundamentalistas disponíveis por classe.
- **FR-004**: O agente MUST consultar a evolução patrimonial mensal, separando valor aplicado de ganho de capital, para horizonte de meses parametrizável.
- **FR-005**: O agente MUST consultar proventos recebidos em um período arbitrário definido por datas de início e fim, com padrão de últimos 12 meses quando não informado.
- **FR-006**: O agente MUST consultar cotação e indicadores de mercado de um ticker individual (preço, variações, indicadores de valuation, DY, setor), sinalizando a defasagem inerente da fonte.
- **FR-007**: O agente MUST comparar alocação atual versus ideal por ativo e por classe e identificar desvios, ordenados por magnitude, para suportar sugestões de rebalanceamento e aporte.
- **FR-008**: O agente MUST persistir memória de longo prazo contendo: teses de investimento por ativo, regras pessoais do usuário, objetivo da carteira, decisões/recomendações com data e racional, e alertas já comunicados.
- **FR-009**: O agente MUST carregar a memória persistida no início de cada sessão e usá-la para contextualizar respostas e evitar repetição de insights já comunicados.
- **FR-010**: O agente MUST registrar recomendações dadas e o desfecho informado pelo usuário (aceita, recusada, postergada), permitindo avaliação histórica do acerto das recomendações.
- **FR-011**: O agente MUST permitir registrar alertas de preço (ativo, condição, limite) e MUST verificar alertas ativos no início de cada sessão, notificando o usuário sobre condições satisfeitas, sem disparos repetidos para o mesmo alerta. Monitoramento contínuo fora de sessões está fora do escopo.
- **FR-012**: O agente MUST gerar relatórios sob demanda sobre um ativo combinando dados quantitativos (posição, indicadores) com eventos recentes obtidos via pesquisa na web, citando as fontes.
- **FR-013**: A carteira alvo MUST ser configurável pelo usuário (identificador da carteira via configuração), sem necessidade de alterar código para trocar de carteira.
- **FR-014**: O agente MUST minimizar chamadas repetidas à fonte de dados reutilizando respostas recentes dentro de uma janela de cache configurável (padrão ~10 minutos), e MUST indicar quando apresentar dados de cache.
- **FR-015**: O agente MUST operar sem interface própria, integrando-se a clientes de agente existentes por meio de conector padrão; nenhum frontend é desenvolvido neste escopo.
- **FR-016**: O agente MUST falhar de forma explícita e informativa quando a fonte de dados estiver indisponível ou com formato inesperado, nunca fabricando valores.

### Key Entities *(include if feature involves data)*

- **Carteira**: conjunto de posições do usuário; atributos: identificador, objetivo declarado, alocação ideal por classe e por ativo, valor aplicado, patrimônio, rentabilidade. Configurável pelo usuário.
- **Posição (Ativo em carteira)**: um ativo detido; atributos: ticker/nome, classe, quantidade, preço médio, cotação, equity, rentabilidade, percentual atual e ideal, indicadores fundamentalistas, recomendação de compra da fonte.
- **Cotação**: retrato de mercado de um ticker em um instante; atributos: preço, variações (dia, 12 meses), indicadores de valuation, DY, setor, defasagem conhecida da fonte.
- **Provento**: rendimento recebido; atributos: ativo, tipo, valor, data; consultável por período.
- **Insight/Recomendação**: conclusão gerada pelo agente; atributos: tipo (rebalanceamento, aporte, concentração, renda, performance), conteúdo, data, desfecho (aceita/recusada/pendente), racional.
- **Alerta de preço**: condição registrada pelo usuário; atributos: ativo, direção (acima/abaixo), limite, data de registro, estado (ativo/disparado).
- **Memória do investidor**: conhecimento persistente; atributos: teses por ativo, regras pessoais, histórico de decisões, alertas já comunicados; sobrevive entre sessões.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário obtém uma visão completa da carteira (todas as classes, 100% dos ativos listados) com uma única pergunta ao agente, em menos de 30 segundos de espera.
- **SC-002**: Valores apresentados pelo agente (patrimônio, rentabilidade, posições, proventos) conferem 100% com os exibidos na fonte oficial da carteira no mesmo momento, com tolerância apenas de arredondamento de exibição.
- **SC-003**: Análises de rebalanceamento identificam desvios de alocação com precisão de 0,1 ponto percentual em relação aos percentuais atual e ideal exibidos na fonte.
- **SC-004**: 100% das teses, regras e decisões registradas em uma sessão são recuperáveis em sessões futuras, com data e conteúdo íntegros.
- **SC-005**: O agente não reapresenta como novidade nenhum alerta ou insight já registrado como comunicado (0 repetições indevidas em sessões subsequentes).
- **SC-006**: Alertas de preço cuja condição foi satisfeita são comunicados na abertura da próxima sessão em 100% dos casos, sem disparos duplicados.
- **SC-007**: Consultas de cotação apresentam dados com defasagem não superior à inerente da fonte (até ~15 minutos para ativos da B3) e sempre sinalizam essa defasagem ao usuário.

## Assumptions

- A carteira do usuário é pública (ou acessível sem autenticação) na plataforma de origem; carteiras privadas/protegidas por link estão fora do escopo inicial.
- A fonte de dados da carteira é uma interface interna não documentada da plataforma; sua estabilidade não é garantida e mudanças de formato serão tratadas como falhas explícitas (ver FR-016), não como dados faltantes silenciosos.
- Uso pessoal e educacional; o agente sugere, mas nunca executa ordens de compra/venda — decisões e execução são sempre do usuário.
- O usuário interage em português; relatórios e insights são produzidos em pt-BR por padrão.
- A memória de longo prazo é local ao ambiente do usuário (arquivo local), sem sincronização em nuvem neste escopo.
- O usuário possui um cliente de agente compatível com conectores padrão (ex.: Claude Desktop, Claude Code, Devin) já instalado e configurável.
- Benchmarks externos (CDI, IBOV) para comparação de performance são obtidos via pesquisa na web sob demanda; não há feed dedicado de índices neste escopo.
- Um único usuário e uma única carteira ativa por configuração; suporte a múltiplas carteiras simultâneas está fora do escopo inicial.
