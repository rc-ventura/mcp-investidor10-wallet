# Implementation Plan: Distribuição Desktop — plugin único, página local de configuração e carteira restrita

> **Revisão de 08/11/2026:** o servidor do plugin não é mais um `.mcpb`; o plugin declara `mcpServers` inline com `uvx` e o `uv` é pré-requisito do Desktop (research.md D1, spec.md Clarifications, learning lesson do spike). Trechos abaixo sobre `.mcpb`, `build_mcpb.py` e `servers/carteira.mcpb` estão substituídos.

**Branch**: `005-desktop-distribution` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-desktop-distribution/spec.md`

## Summary

Levar o produto ao Claude Desktop (Claude unificado) para o usuário leigo:
ele adiciona o marketplace do repositório, instala **um plugin só** e
configura a carteira numa **página local**, aberta pelo assistente, sem o link
passar pelo modelo. É um produto só, sem flag por superfície; `--mcp-only`
continua como escape. Abordagem técnica (research.md):

1. **Plugin completo** (US1, P1): o manifesto Claude do plugin passa a
   apontar `mcpServers` para o servidor empacotado dentro do plugin
   (`plugin/servers/carteira.mcpb`, tipo `uv`, em que o app instala Python e
   dependências). Esse pacote só aponta para a versão publicada no PyPI e muda
   só na release; o usuário não vê esse arquivo. Um **spike numa máquina
   limpa** é a primeira tarefa e decide entre esse caminho e as reservas
   (executável por plataforma; `uvx` como pré-requisito).
2. **Servidor sem configuração** (US1): sobe sempre; tools de carteira
   devolvem `wallet_not_configured`; a tool nova `open_wallet_setup` (20ª),
   sem parâmetros, abre a página em `127.0.0.1`, que interpreta o link, valida,
   protege a troca de carteira e grava a **configuração local única**
   `~/.investidor10/config.json`, relida por todos os clientes sem reinício.
   O formulário dentro da conversa (MCP Apps) é só testado no spike.
3. **Três camadas que conduzem a configuração**: erro estruturado
   (garantia), hook de início de sessão reescrito como JSON estático (roda
   no Bash e no PowerShell) e skill nova `configurar-carteira`.
4. **Carteira restrita** (US2, P1): link com `?h=` vira credencial enviada
   como `hash` só ao proxy da carteira; HTTP 3xx vira `access_denied`
   (fim do falso `unexpected_format`); credencial redigida em todo texto.
5. **Instalador, `configure` e `doctor`** (US2, US5): `--link`, pergunta do
   mascaramento, Claude Code pelo plugin (sem registro em dobro, respeita o
   plugin sincronizado; `--mcp-only` registra só o servidor), outros CLIs sem
   variável da carteira.
6. **Devin Desktop e matriz de máquinas limpas** (US3, US4): verificação
   real, sem suposição de caminho.
7. **Release e cadeia de suprimentos** (US6): Git Flow adaptado em que `main`
   só recebe versões já publicadas (ADR-0020); jobs `build`, `publish` e
   `verify`, promoção automática por `promote/vX.Y.Z` com portão de CI,
   pré-lançamento `rc` para validar no Desktop, teste de consistência de
   versões e tools, testes semanais contra a API real, Dependabot.
8. **Marketplace próprio** (US7): README com o passo a passo do Desktop;
   nenhuma submissão a diretório.

Versão alvo **0.4.0** (mudança de contrato: tool nova, dois códigos de
erro, servidor que sobe sem configuração, página local).

## Technical Context

**Language/Version**: Python ≥3.11 (CI: 3.11, 3.12, 3.13; macOS, Linux,
Windows).

**Primary Dependencies**: `fastmcp==4.1.2`, `httpx==0.28.1`,
`filelock==4.2.4`, sem dependência de runtime nova (a página local usa só a
biblioteca padrão: `http.server`, `secrets`, `webbrowser`). Ferramentas de build
novas, só na CI: CLI `@anthropic-ai/mcpb` pinado (validação do pacote) e,
apenas se o spike cair na reserva 2, PyInstaller pinado.

**Storage**: `memory.json` v1 inalterado; novo `config.json` (v1) no mesmo
diretório 0700 — ver data-model.md §1.

**Testing**: pytest + pytest-asyncio + respx (existente). Novos: contratos
de `open_wallet_setup` e dos dois códigos via `fastmcp.Client`
(`raise_on_error=False`); página local com requisições HTTP reais (resultados
e segurança); fixture anonimizada da resposta 301 real;
interpretação de link por tabela; recarga da configuração entre processos;
consistência de versões, tools e MCPB; JSON do hook só ASCII; spike e
matriz manuais registrados.

**Target Platform**: servidor MCP stdio local. Claude Desktop em macOS e
Windows (sessão Cowork no computador); Claude Code, Devin CLI/Desktop,
Codex e Gemini CLI em macOS, Linux e Windows.

**Project Type**: pacote Python (servidor MCP + CLI de instalação) +
plugin com servidor empacotado + marketplace no repositório.

**Performance Goals**: conferência da identidade do arquivo de
configuração por chamada < 1 ms (um `stat`); primeira resposta com dados
no Desktop em até 5 minutos desde a instalação (SC-001).

**Constraints**: nada de terminal nem edição de arquivo para o usuário do
Desktop; link e credencial nunca passam pelo modelo; página só em `127.0.0.1`,
com token de uso único e prazo de 10 minutos; plugin sem `bin/` no topo;
mensagens ao operador em PT-BR e ao modelo em inglês (ADR-0009);
conjunto fechado de códigos de erro (15).

**Scale/Scope**: usuário único por máquina, 2 a 5 processos do servidor
(Desktop + CLIs); 36 FRs, 7 USs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Resultado |
|---|---|---|
| I. Documentação oficial primeiro | research.md cita docs da Anthropic (plugins, platform-support, Desktop 3P, MCPB), Claude Code (components, install), MCPB MANIFEST.md, gofastmcp.com (annotations, Apps) e a spec MCP 2026-07-28 (elicitation). O tipo `uv` do MCPB é experimental e a doc não diz se o app traz o uv nem se a sessão Cowork abre o navegador: verificação empírica S1 é a primeira tarefa, com resultado registrado em learning lesson. Fontes não oficiais marcadas e só como contexto | PASS (com spike registrado) |
| II.1 Erros nunca como sucesso | Dois códigos novos saem pelo mesmo middleware com `isError`; `open_manually` é resultado legítimo (a página está pronta), não erro | PASS |
| II.2 Valores nunca fabricados | Estado pendente devolve erro, nunca dados vazios; 3xx não serve cache vencido | PASS |
| II.3 Exceção inesperada é bug | Nenhuma mudança no canal de exceções; configuração corrompida vira estado pendente com causa, não exceção engolida | PASS |
| II.4 Trigger-phrase | `wallet_not_configured` e `access_denied` nomeiam `open_wallet_setup` | PASS |
| III. Uso, não comportamento | Regras de configuração nas docstrings de `open_wallet_setup` e `get_session_context`; persona e condução da conversa no hook e na skill; nenhuma invariante depende de hook ou de `instructions=` (o erro do servidor é a garantia) | PASS |
| IV. Estado explícito | Configuração é estado explícito em arquivo, relida por identidade; nenhuma dependência de sessão de protocolo | PASS |
| V.1 Deps de runtime | Nenhuma nova; a página usa a biblioteca padrão; o pacote MCPB pina as mesmas três | PASS |
| V.2 Upgrade consciente | Nenhum upgrade de FastMCP | PASS |
| Formato e estilo | TDD por tarefa; sem emojis; comentários de uma linha; nada de referência a ADR/FR no código | PASS |
| Governança | ADR-0012, ADR-0004 e ADR-0015 emendados por ADRs novos (0018, 0019); ADR-0014 emendado; ADR-0011 emendado pelo ADR-0018 (o PyPI segue como único canal de código); ADR-0020 (fluxo de branches e release) no Lote 0 e ADR-0019 no Lote 2, antes do código que descrevem; learning lessons dos fatos novos do upstream (301, spike, sincronização, Devin Desktop) | PASS |

**Re-check após o design (Phase 1)**: contratos e data-model mantêm os
mesmos resultados. Ponto de atenção
registrado, não violação: um agente com controle do navegador poderia abrir a
página; o token de uso único e o prazo curto reduzem o risco, a limitação entra
no ADR-0019 e a FR-008a é o gatilho de revisão se o Claude Desktop passar a
documentar elicitation (research D15).

## Project Structure

### Documentation (this feature)

```text
specs/005-desktop-distribution/
├── plan.md                       # este arquivo
├── research.md                   # Phase 0
├── data-model.md                 # Phase 1
├── quickstart.md                 # Phase 1
├── contracts/
│   ├── wallet-setup.md
│   ├── error-envelope.md
│   ├── cli.md
│   └── plugin-package.md
├── validation-matrix.md          # preenchida na US4 (implementação)
├── checklists/requirements.md
└── tasks.md                      # /speckit-tasks
```

### Source Code (repository root)

```text
src/investidor10_wallet/
├── bootstrap.py          # load_config sem abortar por WALLET_ID ausente; mensagens PT-BR novas
├── wallet_config.py      # novo: link -> campos, arquivo config.json (ler por fd, gravar atômico), estado e recarga por identidade
├── setup_page.py         # novo: página local temporária (formulário, token, gravação)
├── wallet_client.py      # 3xx -> access_denied; parâmetro hash só no proxy; redação da credencial; troca de carteira limpa o cache; validação reutilizável
├── server.py             # open_wallet_setup; bloco configuration no contexto; wallet_not_configured nas tools de carteira; sonda só com configuração
├── privacy.py            # mascaramento efetivo = arquivo OR ambiente
└── installer/
    ├── cli.py            # --link, --mask/--no-mask; subcomandos configure e doctor
    ├── clients.py        # Claude via plugin (pin #v, @synced, remover registro antigo); outros sem WALLET_ID
    └── doctor.py         # novo: checagens e saída sanitizada

plugin/
├── .claude-plugin/plugin.json    # version + mcpServers
├── servers/carteira.mcpb         # novo, gerado
├── hooks/hooks.json, session-start.json (novo), stop-memory-reminder.sh
└── skills/configurar-carteira/SKILL.md (novo)

scripts/
├── build_mcpb.py         # novo: zip determinístico do servidor
├── check_promotion.py    # novo: portão de promoção para main
└── plan_promotion.py     # novo: decide as ações de promoção de uma tag

tests/
├── unit/                 # wallet_config (link, arquivo, estado), redação, privacy efetivo, doctor
├── contract/             # open_wallet_setup, códigos novos, contexto, consistência versões/tools/MCPB, hook ASCII
├── integration/          # página local, recarga entre processos, 301 real anonimizado, instalador por cliente
└── fixtures/             # resposta 301 anonimizada

.github/
├── workflows/release.yml # jobs build, publish e verify
├── workflows/promote.yml # novo: promove a versão publicada para main
├── workflows/main-gate.yml # novo: recusa para main o que não é versão publicada
├── workflows/live.yml    # novo: semanal + manual
└── dependabot.yml        # novo

docs/
├── adrs/0018-*.md, 0019-*.md, 0020-*.md (novos); 0014 e 0011 emendados
├── research/fichamentos/ # achados por fonte, sem reflexão (skill research)
├── RELEASING.md          # novo: pré-lançamento, versão final e hotfix
├── learning-lessons/     # 301 acesso recusado; spike MCPB; plugin sincronizado; Devin Desktop
├── PRIVACY.md            # restrita como padrão; link na conversa
└── README.md (raiz)      # passo a passo do Desktop
```

**Structure Decision**: projeto único existente (src layout). Um módulo
novo de configuração (`wallet_config.py`) concentra link, arquivo e estado
porque são uma coisa só; `setup_page.py` isola o servidor HTTP temporário, que
tem superfície de segurança própria; `doctor.py` fica no pacote do instalador,
que já reúne os subcomandos de terminal. Nenhum outro módulo novo (Constituição,
modularização com parcimônia).

## Ordem de execução sugerida

0. Fluxo de branches (Lote 0): `develop`, ADR-0020, portão de promoção e
   proteção de `main`.
1. S1 (spike), S1b (revogação do link) e learning lesson; decisão final de D1.
2. Configuração local e ADR-0019. Depois, US2 núcleo: 3xx -> `access_denied`,
   interpretação do link, credencial, redação (independe do resto e protege os
   usuários atuais).
3. Servidor sem configuração, página local e `open_wallet_setup`; pipeline
   mínima (`release.yml` em três jobs) e publicação da `0.4.0rc1` a partir de
   `develop`.
4. Plugin completo (MCPB apontando para a rc), validado no Desktop por Upload
   plugin.
5. Instalador, `configure`, `doctor`, README.
6. Promoção automática, testes semanais contra a API real e Dependabot.
7. Devin Desktop e matriz; versão final: pedido de preparação, tag,
   publicação, verificação, promoção e validação com o marketplace em `main`.

## Complexity Tracking

Nenhuma violação da constituição a justificar.
