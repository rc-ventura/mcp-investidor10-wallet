# `Referrer-Policy: no-referrer` faz o navegador mandar `Origin: null`: a página local recusava todo envio real

**Context:** Descoberto no Lote 4 da spec 005, ao abrir num navegador real (Chromium, via Playwright) a página local de configuração da carteira (`src/investidor10_wallet/setup_page.py`). Toda a suíte passava, inclusive os testes de segurança da página, mas o primeiro envio do formulário feito por um navegador de verdade voltou 403.
**Date:** 2026-11-06
**Future intent:** Toda proteção que depende de um cabeçalho que o navegador preenche sozinho (`Origin`, `Referer`, `Sec-Fetch-*`, cookies) precisa de pelo menos um teste com navegador real, além dos testes com cliente HTTP.

---

## O que aconteceu

A página confere `Host` e `Origin` em todo `POST`, para barrar envio vindo de outro site (ADR-0019). As respostas da página traziam também `Referrer-Policy: no-referrer`, posto para não vazar o token da URL (`/?t=<token>`) em nenhum `Referer`.

Pela especificação Fetch, quando a política de referrer da requisição é `no-referrer`, o navegador serializa a origem como `null` no cabeçalho `Origin` dos pedidos que não são `GET` nem `HEAD`. O formulário herdava a política da página, então o envio chegava com `Origin: null`, a checagem não casava com `http://127.0.0.1:<porta>` e a página respondia 403 a qualquer envio legítimo.

```text
página (Referrer-Policy: no-referrer)
   │  usuário envia o formulário
   ▼
POST /   Origin: null            <- o navegador, não o código, decide isso
   │
   ▼
checagem de Origin: "null" != "http://127.0.0.1:<porta>"  ->  403
```

## Por que os testes não pegaram

Os testes de integração (`tests/integration/test_setup_page.py`) usam `http.client` e **montam o `Origin` à mão**, com o valor que o código espera. Eles provavam que a checagem recusa origem errada e aceita a certa. Não provavam que um navegador manda a certa. O cabeçalho em disputa é justamente o que o cliente de teste não reproduz.

| Camada | O que cobre | O que não cobre |
|---|---|---|
| Teste com `http.client` | Lógica da checagem: token, `Host`, `Origin`, prazo, corpo | Os cabeçalhos que o navegador escolhe por política |
| Navegador real | O pedido como o usuário o envia | Casos de ataque (origem forjada, token vencido) |

## Correção

- `Referrer-Policy: same-origin`: o `Referer` com o token continua sem sair para outro site, e o `Origin` do próprio formulário volta a ser enviado. A página não carrega nenhum recurso externo, então nada muda na exposição do token.
- Comentário de uma linha no código explicando por que não `no-referrer`.
- Teste de regressão: a resposta do formulário traz `Referrer-Policy: same-origin`.
- Conferido de novo no Chromium: o envio de um link inválido passa pela checagem e mostra o aviso de link inválido.

## Relação com ADRs e próximos passos

- **ADR-0019** (página local): a defesa por `Host` + `Origin` + token continua a mesma; esta lição só registra a política de referrer compatível com ela.
- O roteiro S5 da spec 005 (envio sem token, com token usado, vencido e com `Origin` de outro site) deve ser feito num navegador real, não só com `curl`.
- Se a página ganhar mais formulários, manter um teste automatizado com navegador (Playwright) para o caminho feliz do envio.
