# `str.isdigit()` e `\d` aceitam dígitos que não são ASCII: validar número de entrada com `[0-9]`

**Context:** Revisão final da spec 005 (ciclo 1, 20/11/2026). Os revisores de QA e Segurança acharam, de forma independente, que o código novo da 0.4.0 repetia um padrão que a ADR-0010 §5 já proibia ("rejeitar dígitos Unicode"): a página local valida o `Content-Length` com `str.isdigit()` (`setup_page.py`), e os scripts de release usam `\d` nas expressões de tag e de referência (`check_release_tag.py`, `plan_promotion.py`, `check_promotion.py`).
**Date:** 2026-11-20
**Future intent:** Todo número vindo de fora (cabeçalho HTTP, tag, argumento) é validado como ASCII antes de virar `int()`. Quando a validação for por expressão regular, `[0-9]` ou `re.ASCII`; quando for por método de string, `isascii() and isdigit()`.

---

## O que acontece

Verificado em 20/11/2026, no Python da máquina do mantenedor:

| Entrada | Teste | Resultado |
|---|---|---|
| `"²"` (sobrescrito) | `"²".isdigit()` | `True` |
| `"²"` | `int("²")` | `ValueError: invalid literal for int() with base 10` |
| `"٣"` (dígito arábico) | `re.match(r"\d", "٣")` | casa |
| `"٣"` | `re.match(r"\d", "٣", re.ASCII)` | não casa |
| `"²"` | `"²".isascii() and "²".isdigit()` | `False` |

Ou seja, `isdigit()` deixa passar caracteres que `int()` não converte, e `\d` numa `str` casa com os dígitos de qualquer alfabeto.

## Onde apareceu

- **`Content-Length` na página local:** um valor como `²` passa em `isdigit()`, e o `int()` seguinte levanta `ValueError` sem tratamento. O handler imprime um traceback e fecha a conexão, em vez de responder 411. Reproduzido pelos dois revisores. O impacto é só da página local (loopback), sem vazamento.
- **Expressões de tag e de referência nos scripts de release:** `\d` aceita dígitos Unicode. Hoje o efeito é nulo, porque a versão ainda precisa bater com `__version__` e os valores vão entre aspas no shell, mas a regra da ADR não está cumprida.

## Por que repetiu

A ADR-0010 §5 trata disso para o bootstrap e para a leitura de variáveis. O código novo entrou por outro caminho (servidor HTTP, scripts de CI) e a regra não estava no lugar onde se escreve a validação. Faltou uma lição curta para ser lembrada na hora.

## Regra

1. Entrada externa que vira número: `isascii() and isdigit()`, ou `re.fullmatch(r"[0-9]+", valor)`, ou um `try/except ValueError` que responde com o erro certo (411, 400).
2. Expressão regular sobre `str` com `\d`: trocar por `[0-9]` ou acrescentar `re.ASCII`.
3. Nunca deixar `int()` sobre entrada externa sem um caminho de erro.

## Relation to ADRs and next steps

- **ADR-0010 §5** — rejeitar dígitos Unicode. Esta lição estende a regra à página local e aos scripts de release.
- **ADR-0019** — emenda de 20/11/2026 registra o `Content-Length` e a ausência de timeout na página.
- **Próximo passo:** corrigir em 0.4.1, com testes primeiro, em [DT-007](../technical-debt/DT-007-endurecer-a-pagina-local-de-configuracao.md) (`Content-Length`) e [DT-008](../technical-debt/DT-008-higiene-de-scripts-e-workflows-de-release.md) (`\d` nos scripts).
- Relatório de origem: `reports/sdd-final-review/005/cycle-1-20261120-1004.md`.
