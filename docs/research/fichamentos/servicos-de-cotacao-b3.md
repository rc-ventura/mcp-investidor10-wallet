# Fichamento: serviços de cotação de ações da B3 (atraso, licença e redistribuição)

- **Pesquisado em**: 2026-11-10
- **Atualizado em**: 2026-11-10
- **Origem**: pergunta do mantenedor sobre uma fonte de preços em tempo real, possivelmente a mesma que o Investidor10 usa

## Por que esta pesquisa

O `get_asset_quote` depende do endpoint do Investidor10 e só cobre ações da B3. O mantenedor quer
saber que serviços entregam cotação em tempo real e sob que condições, e se dá para descobrir a
fonte do próprio Investidor10. Este fichamento só registra o que as fontes dizem.

## Perguntas

1. De onde o Investidor10 tira as cotações e com que atraso?
2. Quais serviços oferecem cotação da B3, com que atraso e com que limites?
3. O que a B3 exige para distribuir cotações em tempo real ou com atraso?
4. Esses serviços permitem usar os dados num produto aberto?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | Página pública de uma ação do Investidor10 (HTML baixado) | Oficial do site | 2026-11-10 |
| F2 | [brapi.dev: não é distribuidora licenciada](https://brapi.dev/faq/a-brapi-e-distribuidora-licenciada-da-b3) | Oficial do provedor | 2026-11-10 |
| F3 | [brapi.dev: atraso por plano](https://brapi.dev/faq/qual-a-diferenca-real-no-atraso-delay-dos-dados-entre-os-planos) | Oficial do provedor | 2026-11-10 |
| F4 | [brapi.dev: termos de uso](https://brapi.dev/legal/terms-of-use) | Oficial do provedor | 2026-11-10 |
| F5 | [Partnr: market data B3](https://partnr.ai/api/market-data) | Oficial do provedor | 2026-11-10 |
| F6 | [HG Brasil Finance](https://hgbrasil.com/finance) | Oficial do provedor | 2026-11-10 |
| F7 | Resumos de busca sobre a Política Comercial de Market Data da B3 (2026 e 2027) | Secundária; os PDFs não foram abertos e o site da B3 respondeu HTTP 520 | 2026-11-10 |
| F8 | Resumos de busca (limites da brapi, EODHD, fórum TabNews) | Secundária | 2026-11-10 |

## Achados

### Fonte do Investidor10 (F1)

- A página de uma ação não carrega nenhum domínio de cotação de terceiros; os domínios externos são de
  fontes, anúncios, análise e redes sociais. Os preços vêm do servidor do próprio Investidor10.
- O texto do rodapé diz que o conteúdo traz "informações de fontes públicas (B3, CVM e RI das
  empresas, etc.)". Não há nome de fornecedor de cotações nem aviso de atraso no que foi visto.
- Não foi encontrada fonte que diga de onde o Investidor10 obtém as cotações nem com que atraso.

### B3 (F7, secundária)

- O Market Data da B3 é distribuído pela plataforma UMDF, em tempo real ou com atraso de 15 minutos;
  exige contrato, direto ou por um distribuidor autorizado.
- A licença separa distribuição, plataformas de negociação e desenvolvimento de produtos. As taxas
  variáveis incidem só sobre dados em tempo real, conforme nível (L1 ou L2), usuário e mídia.
- Distribuidores e redistribuidores enviam relatórios periódicos de consumo à B3.
- Um fórum de usuários afirma que a B3 não oferece API pública, gratuita e em tempo real; é opinião.

### Provedores

- **brapi.dev** (F2, F3, F4): "não é Distribuidora nem Redistribuidora licenciada pela B3", sem contrato
  de market data com a B3, e diz trabalhar "exclusivamente com dados abertos e públicos". Atraso
  aproximado de **30 min no plano gratuito, 15 min no Startup e 5 min no Pro**. Sem SLA. A licença
  permite exibir, guardar em cache e cobrar pelas próprias funcionalidades; **não permite** entregar os
  dados a terceiros "como feed, API ou base bruta" nem montar proxy ou espelho; para tempo real de nível
  profissional recomenda um provedor licenciado ou contrato direto com a B3. Os termos não citam uso por
  agentes de IA nem projetos de código aberto. Uma busca indica plano gratuito de 15.000 requisições por
  mês (F8, não confirmado na página).
- **Partnr** (F5): "redistribuidora autorizada de market data da B3". Modalidades: intraday com 15
  minutos de atraso, fechamento D-1 e "sem atraso", esta última "depende do produto contratado, do caso
  de uso e das condições de licenciamento". Sem tabela de preços: teste gratuito e contratação por
  proposta. Oferece servidor MCP.
- **HG Brasil Finance** (F6): API de ações, FIIs e câmbio da B3; a resposta de exemplo traz `updated_at` e
  `market.is_open`; a página não informa atraso, plano gratuito nem termos de redistribuição.
- **EODHD** (F8): planos a partir de US$ 19,99 por mês, com ações brasileiras; detalhes de atraso não vistos.
- **Alpha Vantage** e **Twelve Data**: sem informação útil sobre a B3 nos resultados.

## Lacunas

- Política Comercial de Market Data da B3 não lida (o site respondeu HTTP 520 ao acesso automático).
- Fornecedor e atraso reais das cotações do Investidor10 não identificados.
- Preços e limites do HG Brasil, do EODHD, do Alpha Vantage e do Twelve Data não confirmados.
- Termos de redistribuição do Partnr não detalhados na página.
