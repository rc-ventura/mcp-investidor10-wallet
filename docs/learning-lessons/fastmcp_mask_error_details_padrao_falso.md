# FastMCP: `mask_error_details` vem desligado e a exceção inesperada chega crua ao cliente

**Context:** Descoberto na revisão final da spec 004 (ciclo 1): o QA apontou e o Tech Leader reproduziu uma exceção interna chegando ao cliente com o texto original.
**Date:** 2026-10-28
**Future intent:** Manter `mask_error_details=True` e o teste de contrato que o protege.

---

## Mental Model: três destinos para uma falha

| Falha | Caminho | O que o cliente recebe |
|---|---|---|
| Erro previsto (fonte, parâmetro, memória) | A tool devolve o envelope `{error: {code, message}}`; o middleware marca `isError` | Código estruturado e mensagem acionável |
| Argumento inválido | `ValidationError` do framework, convertido pelo middleware | `invalid_params` com `isError` |
| **Exceção inesperada (bug)** | Sobe da tool para o framework | Com `mask_error_details=False` (padrão): `Error calling tool 'x': <texto da exceção>`. Com `True`: `Error calling tool 'x'` |

## Reprodução

Uma tool que levanta `RuntimeError("detalhe-interno")`, num servidor criado sem a opção, devolve esse texto ao cliente (e portanto ao modelo e ao provedor). Com `FastMCP(..., mask_error_details=True)` o cliente recebe só `Error calling tool 'boom'` e o traceback completo continua sendo impresso no stderr do servidor.

## Impacto no projeto

A Constituição (II.3) manda que exceção inesperada seja sanitizada e logada no servidor, e a spec 004 repete isso como caso de borda. O servidor era criado sem a opção, então caminhos de arquivo, nomes de chave e trechos de payload podiam vazar num bug.

## Como evitar

- `FastMCP("investidor10-wallet", instructions=..., mask_error_details=True)` em `server.py`.
- `tests/contract/test_error_signal.py` provoca uma exceção arbitrária e confere que o texto do cliente não a contém e que o stderr do servidor a contém.

---

## Relation to ADRs and next steps

- **ADR-0014** — sinal duplo de erro: exceções inesperadas ficam fora do conjunto fechado de códigos e passam pelo canal do framework, agora sanitizado.
- **Constituição II.3** — bug é bug: sanitiza, loga no servidor, reporta como falha.
- Ao subir o FastMCP, revalidar o padrão da opção.
