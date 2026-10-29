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
| **Investidor10** (API pública) | Requisições com o ID da sua carteira e os tickers que você consulta | A fonte já tem os seus dados. O servidor não envia mais nada além do ID e dos tickers |
| **Provedor do modelo** (o agente que você usa) | Tudo que as ferramentas devolvem: valores, posições e proventos da carteira, e o conteúdo da memória (teses, regras, decisões, alertas) | É aqui que a exposição acontece. Cada resposta de ferramenta entra no contexto do modelo |
| **Arquivos na sua máquina** | `memory.json` (sua memória), `memory.json.log` (histórico de mudanças da memória), `memory.json.lock` (controle de acesso) e cópias `memory.json.broken-*` (só se o arquivo ficar corrompido) | Ficam em `~/.investidor10/`, com acesso restrito ao seu usuário. Nada disso é enviado a outro lugar pelo servidor |

O cache de respostas da API existe só na memória do processo e some quando o
servidor termina.

## A credencial é o link

O ID da sua carteira (o número que aparece no link público) funciona como uma
**senha**: quem o tem consegue ler todos os valores da carteira pela API,
sem precisar de login.

O botão de mascarar valores do site Investidor10 é só visual: ele esconde os
números na tela, mas a API continua devolvendo tudo (verificado em 17/10/2026).
Por isso:

- não publique o ID nem o link da carteira em issues, prints ou repositórios;
- trate o ID como você trataria uma senha;
- se o ID vazar, deixe a carteira privada nas configurações do site.

## Modo privacidade

O modo privacidade impede que **valores em reais e quantidades** cheguem ao
modelo. Para ligar, defina a variável de ambiente `WALLET_MASK_VALUES=1` no
servidor, junto do `WALLET_ID` (os valores aceitos são `1`, `true`, `yes`
e `on`; qualquer outro valor desconhecido faz o servidor se recusar a
iniciar). Não há como ligar ou desligar pelo chat: de propósito, o próprio
modelo não consegue desativar a proteção.

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
