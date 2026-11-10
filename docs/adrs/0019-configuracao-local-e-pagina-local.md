# ADR-0019: Configuração local única, carteira restrita, servidor sem configuração e página local

- **Status**: Accepted (amended 2026-11-06)
- **Date**: 2026-11-03
- **Deciders**: Mantenedor + Claude (spec 005, Lote 2)
- **Related spec**: [`specs/005-desktop-distribution/`](../../specs/005-desktop-distribution/) (FR-004 a FR-008a, FR-011, FR-012; research D2 a D6, D8, D15)
- **Code**: `src/investidor10_wallet/wallet_config.py`, `src/investidor10_wallet/local_files.py`, `src/investidor10_wallet/bootstrap.py`, `src/investidor10_wallet/setup_page.py`, `src/investidor10_wallet/server.py` (`open_wallet_setup`, `_resolve_configuration`), `src/investidor10_wallet/privacy.py`
- **Research**: [`docs/research/fichamentos/entrada-de-dados-do-usuario-em-mcp.md`](../research/fichamentos/entrada-de-dados-do-usuario-em-mcp.md), [`docs/research/fichamentos/plugins-claude-componentes-e-instalacao.md`](../research/fichamentos/plugins-claude-componentes-e-instalacao.md)

---

## Context

Até a spec 004 a carteira era configurada pela variável de ambiente
`WALLET_ID`, registrada no cliente por quem instalava (assistente de
terminal, ADR-0012). O servidor abortava sem ela. Isso serve a quem usa
terminal e não serve ao investidor que instala o plugin no Claude Desktop:
não há onde digitar a variável, o Cowork não pergunta valores do plugin, e um
servidor que aborta deixa a conversa sem por onde começar.

A spec 005 também acrescenta a carteira restrita, cujo link traz uma
credencial (`?h=<hash>`). Essa credencial tem o mesmo peso do ID no ADR-0004:
quem a tem lê a carteira. Ela não pode passar pelo modelo nem pelo provedor,
não pode ficar em um registro de cliente copiado por cliente, e não pode
aparecer em log, mensagem ou arquivo versionado.

Por fim, o mascaramento de valores (ADR-0015) hoje só liga por variável de
ambiente, o que o usuário leigo também não consegue fazer.

## Decision

1. **Configuração local única.** A carteira passa a ser configurada em
   `~/.investidor10/config.json`, no diretório canônico da memória (0700), com
   arquivo 0600. Todos os clientes leem o mesmo arquivo. Campos: `version`,
   `wallet_id`, `share_hash`, `mode` (`public` ou `restricted`), `mask_values`,
   `validated_at`, `source`. O arquivo é aberto por descritor com `O_NOFOLLOW` e
   gravado de forma atômica (temporário no mesmo diretório, `fsync`,
   `os.replace` com o retry do Windows), pelo mesmo ponto único de arquivo local
   (`local_files.py`) que a memória usa. Nunca entra em log, no changelog da
   memória nem em mensagem.
2. **Precedência e relido por identidade.** Arquivo válido vence o ambiente;
   sem arquivo, vale `WALLET_ID` do ambiente (instalações anteriores e CI); sem
   nenhum, o estado é pendente. O servidor relê o arquivo só quando a
   identidade dele muda (inode, tamanho, `mtime_ns`), conferida no início de
   cada chamada, de modo que a configuração feita no Desktop vale no Claude
   Code já aberto, sem reiniciar. Arquivo que existe mas está ilegível,
   corrompido, é link simbólico, passa do limite de tamanho ou tem versão
   futura deixa o estado pendente com a causa, sem apagar nem reescrever o
   arquivo, e **não cai para o ambiente**: trocar de carteira em silêncio por
   causa de um arquivo quebrado seria pior que pedir a correção.
3. **Servidor sem configuração.** `load_config` deixa de abortar sem
   `WALLET_ID`; o servidor sempre sobe e só pula a sonda de inicialização
   quando não há carteira. `WALLET_ID` inválido e números inválidos continuam
   abortando (erro de quem registrou o servidor). As tools de carteira
   devolverão o erro `wallet_not_configured`, que nomeia `open_wallet_setup`
   (Lote 4); os erros estruturados são a camada que vale em qualquer cliente,
   inclusive sem hooks.
4. **Página local e `open_wallet_setup`.** A configuração acontece numa página
   temporária servida pelo próprio servidor (biblioteca padrão), aberta pela
   tool sem parâmetros `open_wallet_setup`. Escuta só em `127.0.0.1`, exige
   token aleatório de uso único com prazo de 10 minutos, confere `Host` e
   `Origin`, não grava o corpo do envio em log e não põe o link na URL. Nenhuma
   tool recebe link, credencial, carteira ou mascaramento.
5. **Link interpretado, não adivinhado.** Formas aceitas: link de carteira
   restrita (`/wallet/public/<id>?h=<hash>`), de carteira pública
   (`/wallet/public/<id>` sem `?h=`, e `/carteira/<id>`) e só dígitos.
   *Emenda de 2026-11-08:* a rota pública real do site é `/wallet/public/<id>`
   sem credencial, descoberta no teste do plugin no Claude Desktop; a primeira
   redação assumia só `/carteira/<id>` e recusava o link público como
   credencial ausente. `?h=` presente e vazio continua recusado. Um link de
   carteira restrita colado sem o `?h=` é aceito como público e falha na
   validação com `access_denied`. Host diferente, mais de um link, ID não
   numérico e credencial fora de `[A-Za-z0-9_-]{1,256}` são recusados com
   orientação que nunca repete o texto recebido. A credencial vai à fonte como
   parâmetro `hash`, só nas requisições do proxy da carteira (Lote 3).
6. **Mascaramento também pelo arquivo.** O mascaramento efetivo é
   `mask_values` do arquivo OU `WALLET_MASK_VALUES` ligado. Isso emenda o
   ADR-0015 §1 (ativação só por variável); o que continua valendo é que
   nenhuma tool altera o mascaramento, e o modelo não pode desligá-lo.
7. **Credencial fora de todo texto visível.** O estado exposto mostra o ID
   mascarado (`…` mais os dois últimos dígitos) e nunca a credencial, nem em
   `repr`/`str`. Uma flag de mascaramento ilegível no ambiente falha fechada
   (mascara).
8. **Elicitation fica de fora.** A spec MCP recomenda o modo URL para
   interações sensíveis, mas não há suporte documentado no Claude Desktop. A
   página local é o caminho; quando a Anthropic documentar o suporte, a mesma
   página passa a ser aberta por URL mode, sem mudar o fluxo do usuário (gatilho
   de revisão, FR-008a).

## Alternatives considered

### Alternative A: `userConfig` do plugin com campo sensível

Funciona no Claude Code, mas o Cowork ignora o campo quando não há valor padrão
e não pergunta ao usuário.

**Why not chosen**:
- Não alcança o Claude Desktop, que é o público desta spec.
- Mantém uma cópia da credencial por cliente.

### Alternative B: variável de ambiente por cliente

É o modelo atual.

**Why not chosen**:
- Exige terminal e uma cópia da credencial em cada registro de cliente.
- Reconfigurar significa reescrever o registro de cada cliente.

### Alternative C: guardar na memória

**Why not chosen**:
- Mistura credencial com dado do investidor e a faria entrar no changelog da
  memória.

### Alternative D: cofre do sistema (keychain)

**Why not chosen**:
- Sem acesso documentado para um servidor de plugin e sem dependência pinada
  para isso (Constituição V.1).

### Alternative E: receber o link por parâmetro de tool

**Why not chosen**:
- A credencial passaria pelo modelo e pelo provedor, e o modelo passaria a
  poder trocar a carteira; contradiz a fronteira do ADR-0004 e o ADR-0015 §1.

## Consequences

### Accepted

- Um lugar só para a carteira, igual em todo cliente; reconfigurar é reescrever
  um arquivo.
- O usuário leigo configura sem terminal, e a credencial não passa pelo modelo.
- A memória e a configuração compartilham o mesmo endurecimento de arquivo
  local (descritor sem seguir link, gravação atômica, 0700 e 0600).
- Quem usa `WALLET_ID` continua funcionando sem mudança.

### Trade-offs

- **Nova superfície de ameaça (emenda ao ADR-0004):** uma porta local em
  `127.0.0.1` por até 10 minutos e uma credencial em arquivo no disco do
  usuário. A defesa é o token de uso único, a conferência de `Host` e `Origin`
  e o arquivo 0600; um processo do mesmo usuário já lê a memória, então o
  arquivo não amplia o que ele alcança.
- **Limite conhecido:** um agente com controle do navegador (computer use,
  Claude in Chrome) poderia abrir a página e preencher o formulário. O token de
  uso único e o prazo curto reduzem o risco, mas não o eliminam. A troca para
  outra carteira exige confirmação na própria página, uma barreira que o modelo
  não alcança pela conversa.
- Escrita concorrente (dois clientes configurando ao mesmo tempo): o último a
  gravar vence, sem trava; o arquivo é pequeno e a gravação é atômica.
- Arquivo quebrado bloqueia as tools de carteira até ser corrigido, em vez de
  cair no ambiente.

### Conditions that invalidate this decision

Esta decisão deve ser **revisitada** se:

1. O Claude Desktop passar a documentar elicitation com modo URL: a página
   passa a ser aberta por ele, e o ponto 8 deixa de ser um limite.
2. Um servidor de plugin ganhar acesso documentado ao cofre do sistema, com
   dependência aceitável: a credencial sai do arquivo.
3. Um segundo usuário do sistema ou um processo não confiável passar a rodar na
   conta do usuário com acesso a `~/.investidor10/`: o modelo de ameaça de
   usuário único (ADR-0004) deixa de valer.

### Migration path when needed

1. Trocar a origem da credencial (cofre) mantendo `config.json` para o resto.
2. Subir `version` e converter na leitura; versão maior que a suportada já
   deixa o estado pendente com `future_version`, sem tocar no arquivo.

## References

- Fronteira de segurança emendada: [ADR-0004](./0004-threat-model-and-security-boundary.md)
- Ativação do mascaramento emendada: [ADR-0015](./0015-modo-privacidade-wallet-mask-values.md)
- Distribuição por cliente: [ADR-0012](./0012-integracao-automatica-de-clientes.md)
- Abertura de arquivo local: `docs/learning-lessons/arquivo_local_abrir_por_fd_sem_seguir_link.md`
- Contrato da página e da tool: `specs/005-desktop-distribution/contracts/wallet-setup.md`
- Esquema do arquivo e do estado: `specs/005-desktop-distribution/data-model.md`

## Emenda 2026-11-06 (spec 005, Lote 4: implementação da página e do servidor)

O Lote 2 decidiu e o Lote 4 implementou. Ficam registrados os pontos que a
decisão deixava em aberto e como foram resolvidos:

1. **Estado resolvido a cada chamada.** As cinco tools de carteira e o
   `get_session_context` resolvem o estado no início da chamada: aplicam a
   carteira e a credencial aos clientes HTTP (o cache só é esvaziado quando uma
   das duas muda) e o mascaramento efetivo. Sem carteira, as tools de carteira
   devolvem `wallet_not_configured` antes de qualquer requisição, inclusive
   antes da validação de argumentos e do modo privacidade. A memória e a
   cotação funcionam sem carteira.
2. **"Uso único" do token.** O token deixa de valer quando a configuração é
   gravada ou quando o prazo de 10 minutos (relógio monotônico) vence. Envios
   que não gravam (link inválido, acesso recusado, fonte fora do ar, "nada
   mudou", falha ao gravar) não consomem o token, para o usuário poder corrigir
   e reenviar na mesma página. Depois de gravar ou vencer, a página encerra.
3. **Troca de carteira sem repetir o link.** A confirmação de outra carteira
   guarda o link já interpretado na memória do processo, ligado à sessão da
   página; o envio de confirmação leva só o token. Nenhuma resposta da página
   repete o link ou a credencial.
4. **Cabeçalhos das respostas.** `Cache-Control: no-store`,
   `Content-Security-Policy` sem recurso externo (`default-src 'none'`, script só
   por nonce, `form-action 'self'`, `frame-ancestors 'none'`),
   `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e
   `Referrer-Policy: same-origin`. Não `no-referrer`: com ele o navegador manda
   `Origin: null` no envio do formulário e a conferência de `Origin` recusa todo
   envio legítimo (learning lesson
   `referrer_policy_no_referrer_manda_origin_null.md`). O token da URL continua
   sem sair para outro site.
5. **Respostas da tool.** `opened`, `already_open` (a mesma página, com o
   navegador acionado de novo) e `open_manually` (só então com `setup_url` e
   `terminal_alternative`). Porta local indisponível devolve `setup_unavailable`.
   A abertura roda fora do loop de eventos.
6. **Mascaramento efetivo.** Liga se o arquivo, a variável no início do
   processo ou a variável no momento da chamada ligar. Nenhum dos três é
   alterado por tool.
7. **Sonda de inicialização.** Com o `config.json`, uma carteira inexistente só
   avisa, para o servidor subir e a página poder corrigir (emenda de 2026-11-06
   ao ADR-0010).

**Limite verificado depois desta decisão:** a documentação da Anthropic diz que
um servidor local roda no Claude Code e numa sessão Cowork no computador do
usuário, "not in chat" (fichamento
`distribuicao-de-servidores-mcp-em-plugins-e-extensoes.md`). A página local, por
depender do servidor rodando no host, segue o mesmo limite: na conversa Chat não
há servidor nem página.

