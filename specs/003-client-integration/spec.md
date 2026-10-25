# Feature Specification: Integração automática com clientes de agente (CLIs)

**Feature Branch**: `003-client-integration`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Publicar o pacote no PyPI não integra o MCP com as LLMs — hoje a configuração é manual por cliente. A ideia: ao rodar um comando, o usuário tem setup automático de integração nos quatro CLIs de agente (Claude Code, Devin CLI, Codex, Gemini CLI), com opção de plugin que empacota MCP + prompts + subagentes + hooks (ex.: check da disciplina de investimento como guardião do trabalho principal). Escopo revisado em 2026-10-24: apenas CLIs — o Desktop (Claude Desktop, extensão .mcpb, apps desktop) fica para uma spec futura dedicada."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Técnico conecta o MCP a todos os seus CLIs com um comando (Priority: P1)

Um usuário técnico que tem o produto rodando via command-line quer deixar de
fazer a configuração manual por cliente (hoje cada CLI tem formato e
peculiaridades próprias). Ele roda **um** assistente de instalação, responde
uma pergunta (o identificador público da carteira) e o assistente detecta
quais CLIs de agente existem na máquina — **Claude Code, Devin CLI, Codex e
Gemini CLI** — e registra o servidor em cada um encontrado, usando o comando
nativo de gestão de MCP de cada CLI.

**Why this priority**: É o MVP de distribuição — sem ele, cada usuário
técnico repete 4 configurações manuais com formatos diferentes. Desbloqueia
todo o resto (o plugin depende de o MCP estar registrado).

**Independent Test**: Instalar o pacote, rodar o assistente numa máquina com
pelo menos um dos quatro CLIs instalado, e verificar que o cliente
reiniciado descobre as 19 tools do servidor sem nenhuma edição manual de
arquivo. Funciona mesmo se só um CLI existir na máquina.

**Acceptance Scenarios**:

1. **Given** uma máquina com Claude Code e Gemini CLI instalados, **When** o
   usuário roda o assistente e informa o ID da carteira, **Then** ambos os
   clientes passam a enxergar o servidor com suas tools após reinício, sem
   edição manual.
2. **Given** uma máquina com Codex instalado, **When** o assistente registra
   o servidor, **Then** `codex mcp list` exibe `carteira` e o Codex
   reiniciado descobre as tools.
3. **Given** o assistente rodado duas vezes na mesma máquina, **When** a
   segunda execução identifica o servidor já registrado, **Then** nenhuma
   entrada duplicada é criada e a configuração existente permanece íntegra
   (idempotência).
4. **Given** nenhum CLI de agente instalado, **When** o usuário roda o
   assistente, **Then** ele recebe orientação clara em PT-BR de que nenhum
   cliente foi detectado e o que fazer em seguida.

---

### User Story 2 - Técnico avançado instala o plugin de comportamento (Priority: P2)

Um usuário que já tem o MCP conectado (via User Story 1) quer os
**superpoderes de comportamento**: o plugin empacota junto ao servidor um
conjunto de ativos — prompts reutilizáveis (ex.: "/análise da carteira",
"/check de tese", "/resumo de dividendos"), subagentes especializados (ex.:
"analista de dividendos"; "guardião de disciplina", que confronta uma decisão
de compra com as regras salvas pelo investidor — o check do trabalho
principal) e hooks de sessão (ex.: no fim da sessão, lembrar o agente de
registrar decisões/insights na memória do investidor — **sempre sugerindo e
pedindo confirmação, nunca gravando sozinho**). A instalação do plugin no
Claude Code e no Devin CLI usa o mesmo artefato, sem dupla manutenção.

**Why this priority**: O diferencial do produto não são os dados da carteira
(qualquer MCP de dados oferece isso) — é a memória de longo prazo do
investidor. O plugin materializa esse diferencial como comportamento do
agente. É P2 porque entrega valor que se soma ao P1 (na jornada típica o MCP
já foi conectado pelo assistente), sem que sua implementação ou teste
dependam dele.

**Independent Test**: Instalar somente o plugin num cliente compatível e
verificar que os prompts, subagentes e hooks ficam disponíveis e
funcionais — independentemente de como o MCP foi registrado antes.

**Acceptance Scenarios**:

1. **Given** o plugin instalado, **When** o usuário lista os comandos do
   agente, **Then** os prompts do pacote aparecem como comandos utilizáveis.
2. **Given** o plugin instalado e regras salvas na memória do investidor,
   **When** o usuário discute uma decisão de investimento e aciona o
   subagente guardião, **Then** ele recebe uma verificação da decisão contra
   as regras registradas.
3. **Given** o plugin instalado, **When** uma sessão termina com decisões
   discutidas e não registradas, **Then** o hook faz o agente propor o
   registro na memória e **aguarda confirmação do usuário** antes de gravar.
4. **Given** o mesmo artefato de plugin, **When** instalado no Claude Code e
   no Devin CLI, **Then** ambos os clientes carregam os mesmos ativos de
   comportamento sem variantes específicas por cliente.

---

### Edge Cases

- O runner de execução (`uv`/`uvx`) não está instalado na máquina: o
  assistente detecta e orienta a instalação em PT-BR antes de prosseguir
  (degradação explícita, nunca silenciosa).
- O identificador da carteira não existe ou a carteira é privada: validação na
  hora da pergunta, com instrução concreta de tornar a carteira pública —
  regras das atuais mensagens do servidor não se repetem silenciosamente.
- O alias `carteira` já está registrado no CLI (por este assistente ou por
  outra origem): o assistente avisa e oferece atualizar ou pular, nunca
  sobrescreve cego.
- Um CLI muda o formato do seu comando de gestão ou o local da configuração
  em versão nova: o assistente falha com erro explícito (degradação segura)
  em vez de registrar por adivinhação; a divergência vira learning lesson.
- Hook de memória falha ou não é suportado pelo cliente: degrada para "chega
  nada" — recusa de plugin é fail-open, nunca bloqueia a sessão do usuário e
  nunca tenta gravar em fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O pacote DEVE estar instalável e executável de uma linha, sem
  clone do repositório (completar a publicação: projeto registrado no índice
  público de pacotes, trusted publishing configurado, environment de release
  criado no repositório, tag publicada — pipeline já existente).
- **FR-002**: O produto DEVE oferecer um assistente de instalação
  em PT-BR (mensagens ao operador seguem o ADR-0009) que seja acionado como
  subcomando do próprio pacote.
- **FR-003**: O assistente DEVE detectar automaticamente quais dos quatro
  clientes alvo (**Claude Code, Devin CLI, Codex, Gemini CLI**) estão
  presentes na máquina e registrar o servidor apenas nos encontrados,
  relatando os pulados.
- **FR-004**: O assistente DEVE validar o identificador da carteira
  (existência e publicidade) antes de registrar em qualquer cliente,
  exibindo instrução de correção em caso de falha.
- **FR-005**: O assistente DEVE ser idempotente: reexecução na mesma máquina
  não duplica entradas e não corrompe configurações existentes.
- **FR-006**: O produto DEVE empacotar um plugin único (manifesto + ativos)
  que atenda ao mesmo tempo Claude Code e Devin CLI — o formato escolhido
  DEVE ser legível por ambos (formato Claude de plugin ou spec aberta
  Agent Plugins), sem manutenção de duas variantes.
- **FR-007**: O plugin DEVE empacotar: o registro do servidor MCP, prompts do
  produto, ao menos um subagente de verificação ao trabalho principal
  (guardião de disciplina) e um hook de fim de sessão que **propõe** registro
  na memória do investidor.
- **FR-008**: Nenhum hook ou subagente DEVE gravar na memória do investidor
  sem confirmação explícita do usuário na mesma interação (a memória é do
  usuário — ADR-0002).
- **FR-009**: O plugin DEVE existir no **mesmo repositório** do motor —
  manifesto e ativos em pastas próprias ao lado do pacote — garantindo uma
  única fonte de verdade, versionamento alinhado e um único repositório que o
  marketplace do Claude Code e o instalador do Devin CLI apontam.
- **FR-010**: O assistente de instalação DEVE, por padrão, registrar **apenas
  o servidor MCP**; a instalação do plugin de comportamento DEVE ser opt-in
  explícito (ex.: flag no assistente ou instalação pelo mecanismo de
  marketplace do cliente), sem surpresa para quem só quer os dados.

### Key Entities *(include if feature involves data)*

- **Registro de servidor por cliente**: representa a entrada do servidor num
  CLI (nome/alias, comando do runner com argumentos, variáveis de ambiente
  como o ID da carteira). Existe uma por cliente por máquina; operações sobre
  ela são idempotentes e delegadas ao comando nativo do cliente.
- **Identificador público da carteira**: único dado exigido do usuário no
  onboarding; validado contra a fonte pública (existência + publicidade)
  antes de persistir em qualquer configuração.
- **Manifesto do plugin**: descreve os ativos de comportamento distribuídos
  (servidor, prompts, subagentes, hooks) e é a unidade de instalação para
  técnicos avançados; um mesmo conteúdo serve os dois CLIs.
- **Sessão do assistente**: o que o assistente fez na máquina (clientes
  detectados, registrados, pulados) — relatado ao usuário em PT-BR ao final.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário técnico conecta o servidor a pelo menos um cliente
  em **até 3 minutos** e **um único comando/chamada** do assistente,
  respondendo no máximo uma pergunta de entrada (o ID da carteira).
- **SC-002**: Usuários técnicos com os 4 CLIs instalados conectam **todos
  eles pela mesma execução** do assistente — zero edição manual de
  configuração restante.
- **SC-003**: Duas execuções consecutivas do assistente na mesma máquina
  produzem configurações finais idênticas (idempotência mensurável: nenhuma
  entrada duplicada, nenhuma configuração corrompida).
- **SC-004**: Um usuário com o plugin instalado tem pelo menos 1 prompt e 1
  subagente utilizáveis imediatamente após a instalação, em ambos os CLIs
  alvo.

## Assumptions

- O pipeline de release já existente é o veículo da FR-001; o trabalho de
  publicação é operacional (criação do projeto, trusted publishing,
  environment, tag) e não muda o pipeline em si.
- O runner oficial de instalação/execução continua `uv`/`uvx` (ADR-0011);
  outros runners são deriváveis pelo usuário mas não alvo do assistente.
- **Claude Desktop (app GUI), extensão `.mcpb`, Devin Desktop e demais apps
  desktop ficam FORA desta feature** — serão tratados numa spec futura
  dedicada (decisão 2026-10-24), porque exigem estudo próprio de
  distribuição (conector/extensão oficial, runtime, memória e subagentes no
  app).
- A identidade do alias do servidor em todos os clientes permanece
  "carteira", sem underscores (restrição do Gemini CLI a aliases com
  underscore causam parse silenciosamente errado de políticas).
- Sempre que um cliente de agente rejeitar um formato novo, a resposta é
  degradação explícita, nunca configuração fabricada (Constitution II.2).
- O subagente guardião e o hook de memória são lembretes/verificações para o
  agente, não mecanismos de protocolo.