# Changelog

Todas as mudanças notáveis do `mcp-investidor10-wallet` são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adota [versionamento semântico](https://semver.org/lang/pt-BR/).
Enquanto a versão for 0.x: mudanças de comportamento (features) incrementam o
minor; correções incrementam o patch.

## [0.3.0] - 2026-10-28

Hardening antes da distribuição Desktop: memória segura com vários clientes,
modo privacidade e erros sinalizados como erro.

### Adicionado

- **Trava da memória entre processos** (macOS, Linux e Windows): vários clientes
  abertos ao mesmo tempo não perdem gravações. Cada operação relê o arquivo sob
  uma trava (`memory.json.lock`); identificadores são únicos e um alerta é
  disparado uma única vez. Se o sistema de arquivos não suporta trava (ex.:
  algumas pastas de rede), as leituras continuam e as gravações são recusadas
  com orientação em PT-BR. Nova dependência de runtime: `filelock`.
- **Histórico de mudanças da memória** (`memory.json.log`, JSONL append-only):
  uma linha por mudança, com estado anterior e novo, para auditar e recuperar
  gravações erradas.
- **Modo privacidade** (`WALLET_MASK_VALUES=1`): valores em R$ e quantidades não
  chegam ao modelo; só campos reconhecidamente não monetários passam, e a
  resposta traz `privacy.omitted`. `get_patrimony_history` e `get_earnings` ficam
  indisponíveis nesse modo.
- **`docs/PRIVACY.md`**: o que vai para onde, o ID da carteira como credencial e
  os limites do modo privacidade. O assistente de instalação aponta para ele.
- **Descrição do servidor** (`instructions`) com propósito e índice de uso.
- Quatro novos códigos de erro: `memory_busy`, `memory_read_only`,
  `privacy_mode_unavailable` e `state_conflict` (12 no total).
- **`truncated` em `get_wallet_positions`**: quando a fonte para de devolver
  linhas novas antes do total declarado, a resposta traz `truncated: true`, e o
  modelo avisa que a lista está incompleta.
- **Job `audit` no CI**: `pip-audit` sobre o lock em todo push e PR.

### Alterado

- **Erros previstos agora chegam com `isError`**, além do envelope
  `{error: {code, message}}`, que continua no conteúdo da resposta. Clientes que
  tratavam erro como sucesso passam a enxergar a falha. Mensagens revisadas com
  a próxima ação.
- Após uma falha de gravação, a memória não fica mais "presa" como indisponível
  no processo: a próxima operação relê o arquivo e se recupera.
- Backup de arquivo corrompido ganha o hash do conteúdo no nome e não é duplicado.
- Skill `resumo-de-dividendos` (plugin 0.1.1) trata o modo privacidade.
- **Cancelar um alerta já disparado ou cancelado** devolve `state_conflict`, e
  não mais `invalid_params`. A mensagem de `invalid_params` passa a nomear o
  argumento inválido.
- **O assistente de instalação registra a versão exata**
  (`uvx mcp-investidor10-wallet@<versão>`), em vez da mais recente do PyPI a cada
  abertura. Para atualizar, rode o assistente da versão nova.
- Dependências: `fastmcp` 4.0.11 → 4.1.2; no lock, `authlib` 1.9.1, `certifi`
  2026.10.19 e `virtualenv` 21.14.13. Isso fecha 2 GHSAs do FastMCP, 7 CVEs do
  `authlib` e o certificado emSign comprometido do `certifi`. As actions do CI
  estão fixadas por SHA.

### Corrigido

- O ID da carteira não aparece mais nas mensagens de erro que chegam ao modelo
  (o caminho da requisição continha o ID, e o `mask_error_details` não cobre
  erros devolvidos como resultado). O ID aparece como `<wallet>`.
- Um JSON da fonte aninhado demais (`RecursionError`) agora é
  `unexpected_format`, e uma única cotação assim não derruba mais o
  `get_session_context`.
- As regras de uso de 5 ferramentas (`get_wallet_positions`, `get_asset_quote`
  com o aviso do atraso de ~15 minutos das cotações, `get_earnings`,
  `get_patrimony_history`, `create_price_alert`) estavam depois do bloco `Args:`
  da docstring e nunca chegavam ao modelo; passaram a ser servidas.

- Exceções inesperadas (bugs) deixam de expor o texto interno ao cliente: ele
  recebe apenas `Error calling tool '<nome>'`, e o detalhe fica no stderr do
  servidor.
- Os arquivos auxiliares `memory.json.lock` e `memory.json.log` ficam com modo
  0600 (um arquivo preexistente com permissão mais aberta é apertado), e o
  arquivo temporário `.memory-*` entra no `.gitignore`.
- **Alertas não disparam com cotação velha.** Durante uma queda da fonte, a
  cotação em cache vencido não dispara mais um alerta, porque o disparo é
  definitivo. O alerta fica em `pending_check` com o motivo `stale_quote` e é
  avaliado na próxima sessão (ADR-0017).
- **Memória apagada com o servidor rodando** não é mais recriada vazia em
  silêncio. Ela fica indisponível, o operador recebe um aviso apontando o
  histórico `memory.json.log`, e restaurar o arquivo traz a memória de volta.
- **Robustez da memória**: `fsync` antes de substituir o arquivo. Um erro de
  leitura passageiro, como antivírus ou sincronização, não é mais tratado como
  corrupção nem gera backup. O modo somente-leitura não grava backup. O
  changelog não segue symlink e é restrito a 0600 pelo descritor, e uma falha
  ao restringir a permissão gera aviso.
- **Modo privacidade**: um campo permitido que chegue com valor aninhado
  (objeto ou lista) é omitido, em vez de passar inteiro.
- **Disponibilidade**: o cache em memória tem limite de 256 entradas e descarta
  as que já passaram da idade máxima, e respostas acima de 10 MB são
  recusadas sem serem lidas inteiras. A paginação de posições para em 400
  páginas e marca `truncated: true`, de modo que uma fonte que devolva linhas
  novas sem fim não prende o servidor.
- **A idade da cotação nos alertas vem do relógio monotônico do cache**, e não
  do `fetched_at`. Um relógio do sistema atrasado não faz mais uma cotação
  vencida parecer fresca.
- **A memória nunca é lida por link simbólico.** Um `memory.json` (ou
  `WALLET_MEMORY_PATH`) que seja link fica indisponível, com aviso em PT-BR, e o
  link não é seguido nem substituído. A trava também é restringida a 0600 sem
  seguir link.
- **`ENOLCK` (tabela de travas do kernel cheia) é tratado como passageiro**:
  falha uma operação, e a memória não fica mais somente-leitura até reiniciar.
- **Trava entre threads**: uma segunda thread do mesmo processo espera a trava
  da memória em vez de passar direto.
- `get_patrimony_history` valida `months` antes de checar o modo privacidade.
  `get_session_context` mantém o `pending_check` quando a memória falha durante
  a avaliação dos alertas.
- O ID real da carteira do mantenedor foi trocado por `<id>` em specs, docs e
  relatórios.
- **Memória aninhada demais é tratada como corrompida.** Um `memory.json`
  editado à mão com estruturas muito fundas derrubava toda operação com erro
  genérico e não gerava backup. Agora ele gera `.broken-*` e a memória fica
  indisponível, como qualquer arquivo corrompido.
- **`get_wallet_positions` não confia num `total` impossível.** Um total zero,
  negativo ou menor que as linhas recebidas encerrava a coleta na primeira
  página sem marcar `truncated`. Agora esse total é ignorado e a coleta segue
  até a última página. Se uma página seguinte declara um total maior, vale o
  maior, e a coleta continua em vez de parar no primeiro.
- `get_patrimony_history` aceita `months` de 1 a 600; um horizonte absurdo é
  `invalid_params`, e não vai para a fonte.
- **Um `memory.json` salvo com BOM** (Bloco de Notas do Windows) é lido
  normalmente, e não tratado como corrompido.
- **Apagar um `memory.json` rejeitado** (corrompido ou de versão futura) com o
  servidor rodando não recria mais a memória vazia: ela segue indisponível até
  o arquivo voltar ou o servidor reiniciar.
- `get_session_context` mantém o resumo da memória quando a leitura dos alertas
  falha, e informa `read_only` (e não `unavailable`) quando a trava deixa de ser
  suportada durante a checagem das cotações.

### Removido

- **Migração automática de `./memory.json`** para `~/.investidor10/memory.json`.
  O servidor deixa de inspecionar o diretório corrente: um `memory.json` solto
  é ignorado. Quem ainda tem a memória no diretório do repositório deve mover o
  arquivo: `mv ./memory.json ~/.investidor10/memory.json`, ou definir
  `WALLET_MEMORY_PATH`.

## [0.2.0] - 2026-10-26

Assistente de instalação e plugin de comportamento — o produto passa a ser o
bundle (MCP + plugin) distribuído por um único comando.

### Adicionado

- **Assistente de instalação** (`mcp-investidor10-wallet install`): detecta
  os CLIs de agente presentes (Claude Code, Devin CLI, Codex, Gemini CLI),
  valida o `WALLET_ID` e registra o servidor `carteira` via comando nativo
  de cada cliente (escopo user), com protocolo interativo de colisão de
  alias, idempotência, `--dry-run` e relatório em PT-BR.
- **Bundle por padrão**: o assistente instala o plugin de comportamento após
  o registro (`--mcp-only` registra apenas o servidor — modo técnico).
- **Plugin de comportamento** (`plugin/`, instalável nos 4 clientes):
  - 3 skills (`/analise-da-carteira`, `/check-de-tese`,
    `/resumo-de-dividendos`) com as regras do produto embutidas;
  - subagente `guardiao-de-disciplina` (read-only, confronta decisões com
    regras/teses salvas);
  - persona do assistente via hook `SessionStart` (`additionalContext`);
  - lembrete de memória via hook `Stop` (propõe `log_decision`/
    `log_insight` com confirmação; fail-open);
  - manifestos finos por cliente (`.claude-plugin`, `.devin-plugin`,
    `.codex-plugin`, `gemini-extension.json`) + `commands/*.toml` para o
    Gemini + marketplace do Claude Code.
- Pesquisa de formato de plugins dos 4 clientes em `docs/research/plugins-*`.

### Alterado

- Configuração manual do Devin CLI documentada com as flags verificadas
  (`devin mcp add -s user carteira -e WALLET_ID=…`) — learning lesson nova.
- README reestruturado: instalação automática como caminho principal,
  configuração manual rebaixada, links relativos corrigidos para URLs
  absolutas (quebravam na página do PyPI).

## [0.1.0] - 2026-10-18

Primeira release pública — prontidão para distribuição (Fase 0 do ROADMAP).

### Adicionado

- Empacotamento no PyPI: pacote `mcp-investidor10-wallet` com console script
  de mesmo nome; instalação/execução em uma linha via `uvx`.
- Validação da carteira no início de cada execução: carteira inexistente ou
  privada aborta com instrução em PT-BR; fonte indisponível apenas avisa e o
  servidor continua.
- Migração automática da memória legada (`./memory.json`) para o local
  canônico `~/.investidor10/memory.json`, com backup identificável em caso de
  conflito e mensagens de operador em PT-BR.
- Onboarding em PT-BR no README: obtenção do `WALLET_ID`, exigência de
  carteira pública, configuração por cliente (Claude Desktop, Claude Code,
  Devin) e tabela de troubleshooting.
- Gates de qualidade: pre-commit (ruff lint + format), CI em matriz de
  Python 3.11/3.12/3.13 × Ubuntu/macOS e workflow de release com smoke test
  do artefato e verificação de changelog.

### Alterado

- `WALLET_ID` deixou de ter valor padrão — o servidor agora exige a variável
  de ambiente e aborta com instrução clara quando ausente (antes usava
  silenciosamente a carteira do autor como default).
- Caminho padrão da memória mudou de `./memory.json` (relativo ao diretório
  de trabalho) para `~/.investidor10/memory.json`; `WALLET_MEMORY_PATH`
  continua como override com precedência total.
- Código reestruturado para layout de pacote (`src/investidor10_wallet/`),
  com entrada única de execução `investidor10_wallet.server:main`.

### Interno

- Formatação do código existente e dos blocos Python em Markdown (`docs/learning-lessons/`) padronizada com ruff (lint + format).