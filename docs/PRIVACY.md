# Privacidade — o que vai para onde

Este documento explica, sem jargão, quais dados saem da sua máquina quando você
usa o `mcp-investidor10-wallet`, para onde vão e como reduzir a exposição.
Leia antes de instalar ou de recomendar a alguém.

## O que vai para onde

O servidor roda na sua máquina, mas "local" não significa "os dados não saem
dela". O agente (Claude, Devin, Codex, Gemini) usa as respostas do servidor
como parte da conversa, e a conversa vai para o provedor do modelo.

| Destino | O que recebe | Observação |
|---|---|---|
| **Investidor10** (API pública) | Requisições com o ID da sua carteira, a credencial do link (só na carteira restrita) e os tickers que você consulta | A fonte já tem os seus dados. O servidor não envia mais nada além do ID, da credencial e dos tickers. A credencial vai só nas requisições da carteira, nunca nas de cotação |
| **Provedor do modelo** (o agente que você usa) | Tudo que as ferramentas devolvem: valores, posições e proventos da carteira, e o conteúdo da memória (teses, regras, decisões, alertas) | É aqui que a exposição acontece. Cada resposta de ferramenta entra no contexto do modelo |
| **Arquivos na sua máquina** | `config.json` (a configuração: ID, credencial do link, modo e mascaramento), `memory.json` (sua memória), `memory.json.log` (histórico de mudanças da memória), `memory.json.lock` (controle de acesso) e cópias `memory.json.broken-*` (só se o arquivo ficar corrompido) | Ficam em `~/.investidor10/`, com acesso restrito ao seu usuário (0600). Nada disso é enviado a outro lugar pelo servidor |

O cache de respostas da API existe só na memória do processo e some quando o
servidor termina.

## A credencial é o link

O ID da sua carteira (o número que aparece no link) funciona como uma
**senha**: quem o tem consegue ler todos os valores da carteira pela API,
sem precisar de login.

O botão de mascarar valores do site Investidor10 é só visual: ele esconde os
números na tela, mas a API continua devolvendo tudo (verificado em 17/10/2026).

### Carteira pública ou restrita

- **Pública** (`investidor10.com.br/carteira/<ID>`): qualquer pessoa com o
  número lê a carteira, e a página pode ser **indexada por buscadores**.
- **Restrita** (o link de compartilhamento, que termina em `?h=...`): só quem
  tem o link completo lê a carteira. **É a escolha recomendada.** O trecho
  `?h=...` é a credencial: ele é tão sensível quanto o ID, e os dois juntos são
  a senha.

### O que o produto faz com o link

- A credencial é separada do link, enviada **só** ao Investidor10 (nas
  requisições da carteira) e guardada em `~/.investidor10/config.json`, com
  acesso restrito ao seu usuário. Desinstalar ou atualizar o plugin não apaga
  esse arquivo.
- Você informa o link na página local de configuração, aberta no seu
  navegador, ou no comando `mcp-investidor10-wallet configure`. Nos dois casos
  o link **não passa pelo modelo**.
- O produto não escreve o ID nem a credencial em mensagens de erro, logs, saída
  de diagnóstico, na memória ou em arquivos do projeto.

### O que você precisa fazer

- **Não cole o link na conversa.** Se colar, ele fica no histórico da conversa
  e vai ao provedor do modelo; o assistente é instruído a não repeti-lo nem
  reutilizá-lo, mas o histórico já o tem. Use a página local ou o `configure`.
- Não publique o ID, o link nem a credencial em issues, prints ou repositórios.
- Se o link vazar, deixe a carteira privada nas configurações do site: sem
  acesso, o servidor passa a mostrar "acesso recusado". **Não confirmamos** que
  gerar um link novo no site cancela o antigo; só a carteira privada garante
  que o link vazado deixa de servir.

## Modo privacidade

O modo privacidade impede que **valores em reais e quantidades** cheguem ao
modelo. Para ligar, responda "sim" à pergunta do assistente de instalação, use
`mcp-investidor10-wallet configure --mask` ou defina a variável de ambiente
`WALLET_MASK_VALUES=1` no servidor (os valores aceitos são `1`, `true`, `yes`
e `on`; qualquer outro valor desconhecido faz o servidor se recusar a
iniciar). O modo fica ligado se **qualquer** das duas fontes o ligar. Não há
como ligar ou desligar pelo chat: de propósito, o próprio modelo não consegue
desativar a proteção.

**O que continua funcionando** (porque usa só percentuais, razões e
indicadores): análise de alocação, rebalanceamento por percentual,
diversificação, fundamentos e notas dos ativos, dividend yield por ativo,
cotações de mercado, memória e alertas.

**O que deixa de existir enquanto o modo está ligado:**

- patrimônio, valor aplicado, lucro e quantidades em reais;
- o histórico de patrimônio (`get_patrimony_history`);
- o total de proventos (`get_earnings`) e, por consequência, o resumo de
  proventos em reais;
- sugestão de aporte em reais.

**Limites que você precisa conhecer:**

- O modo **não é anonimização**. Preços unitários e percentuais permitem
  estimar proporções, não montantes.
- Entre os preços unitários está o **seu preço médio de compra** por ativo
  (`avg_price`). Diferente da cotação, ele é seu: mostra quanto você pagou por
  cota ou ação, mas não quantas você tem nem quanto investiu.
- O **texto livre** que você escreve (teses, regras, objetivo, notas de decisão)
  e o que você digita na conversa **não são mascarados**. Se você escrever
  "quero chegar a R$ 1 milhão", isso vai ao modelo.
- Ele protege o que vai ao modelo; não protege contra quem tem o link da carteira.

## Privacidade total

Para que **nada** saia da sua máquina, além do modo privacidade você precisaria
de um modelo de linguagem rodando localmente (por exemplo, via Ollama), porque
o provedor do modelo é quem recebe o contexto. Esta versão não avaliou nem
promete suporte a modelos locais.

## Memória em pasta sincronizada

Se você apontar `WALLET_MEMORY_PATH` para uma pasta sincronizada (Dropbox,
iCloud, OneDrive):

- **na mesma máquina**, com vários clientes abertos, funciona e é seguro: o
  servidor controla o acesso ao arquivo e nenhuma gravação confirmada se perde;
- **em duas máquinas ao mesmo tempo**, a proteção não vale. Cada máquina controla
  só a cópia local, e o serviço de sincronização pode criar uma "cópia em
  conflito". Use uma máquina por vez e espere a sincronização terminar.

Se o arquivo estiver num sistema de arquivos sem suporte a trava (por exemplo,
algumas pastas de rede), o servidor avisa na inicialização, continua lendo a
memória e recusa gravações para não perder dados. Aponte `WALLET_MEMORY_PATH`
para um disco local.

## Telemetria

O produto **não envia telemetria**: não há contagem de uso, relatório de erro
automático nem contato com servidores do mantenedor. As únicas conexões de rede
do servidor são as requisições ao Investidor10 descritas acima.
