# DT-007: Endurecer a página local de configuração

**Status**: Open
**Priority**: Low
**Date**: 2026-11-20
**Origin**: revisão final da spec 005, ciclo 1 (`reports/sdd-final-review/005/cycle-1-20261120-1004.md`, achados #2, #3, #4, #10 e #43, classe B)
**Related**: [ADR-0019](../adrs/0019-configuracao-local-e-pagina-local.md) (emenda de 2026-11-20), [lição sobre dígitos Unicode](../learning-lessons/digitos_unicode_isdigit_e_d_aceitam_alem_de_ascii.md), `src/investidor10_wallet/setup_page.py:195-198,267-283`, `src/investidor10_wallet/local_files.py:30-38`

---

## Debt

O handler da página local foi escrito para o caminho feliz. Ficaram para a 0.4.1:

- **`Content-Length` com dígito Unicode** (por exemplo `²`) passa em `isdigit()` e o `int()` levanta `ValueError` sem tratamento: traceback no stderr e conexão fechada, sem resposta 411.
- **Sem timeout de leitura no socket:** um cliente local que declare `Content-Length` e envie menos bytes prende uma thread até o processo terminar.
- **O `do_POST` lê o corpo antes de validar Host e Origin.**
- **Exceções que não são `OSError`** no handler derrubam a conexão sem resposta.
- **`read_bytes_no_follow` não confere que o arquivo é regular:** um FIFO no lugar do `config.json` travaria o `os.open` e, com ele, o `resolve_state`, que roda em cada chamada de tool. Exige escrita local na pasta do usuário.

## Cause

Achados da revisão final do ciclo 1, classificados para a 0.4.1: a 0.4.0 já estava publicada, e no modelo de um único mantenedor e uso pessoal (ADR-0004) o impacto é baixo.

## Impact

A porta é só de loopback, efêmera e fica aberta no máximo 10 minutos. Nada vaza e nenhum dado da carteira está em jogo: o pior caso é uma thread parada até o processo terminar, ou um traceback no stderr.

## How to pay

1. Testes primeiro: `Content-Length: ²` responde 411, um corpo curto expira no timeout, Host ou Origin inválido recusa antes de ler o corpo, e uma exceção inesperada no handler responde 500.
2. Validar `Content-Length` com `isascii() and isdigit()`, definir `timeout` no handler, mover a checagem de Host e Origin para antes da leitura do corpo e tratar as exceções.
3. Acrescentar a conferência de arquivo regular (`S_ISREG`) em `read_bytes_no_follow`.
4. Entrar na 0.4.1, com ciclo próprio de revisão sobre o diff `v0.4.0..0.4.1`.
5. Resolver com `/tech-debt resolve DT-007`.

## Revisit trigger

Subir se a porta local passar a ficar aberta por mais tempo ou a aceitar conexões que não sejam de loopback.
