# `RecursionError` não é `ValueError`: profundidade de aninhamento é uma falha à parte do JSON malformado

**Context:** O `_reload` do `memory_store` tratava a corrupção com `except (ValueError, UnicodeDecodeError)`. A revisão final da spec 004 (ciclo 4) mostrou que um `memory.json` aninhado demais faz `json.loads` levantar `RecursionError`, que deriva de `RuntimeError`. A exceção escapava, o store continuava `available=True` com dados velhos, nenhum `.broken-*` era criado e toda operação seguinte falhava com erro genérico mascarado. Toda a contenção do ADR-0002 era contornada.
**Date:** 2026-10-29
**Future intent:** Quem interpreta um arquivo que o usuário pode editar à mão limita a profundidade antes de usar o conteúdo e trata `RecursionError` como corrupção.

---

## Mental Model

Medido em Python 3.13.5, com listas aninhadas:

| Profundidade | `json.loads` | `json.dumps` (C) | `copy.deepcopy` | `json.dump(indent=2)` |
|---|---|---|---|---|
| 40 | ok | ok | ok | ok |
| 500 | ok | ok | **`RecursionError`** | ok |
| 1 500 | ok | ok | **`RecursionError`** | **`RecursionError`** |
| 10 000 | **`RecursionError`** | n/a | n/a | n/a |

Há duas armadilhas, não uma:

1. **A exceção é de outra família.** O `JSONDecodeError` é `ValueError`; o estouro de pilha do parser C é `RecursionError`. Um `except ValueError` não pega o segundo.
2. **Passar no parser não basta.** O codificador C e o parser C aguentam milhares de níveis. O `copy.deepcopy` e o `json.dump` com `indent` recursam em Python e quebram em poucas centenas. Um arquivo que carrega sem erro pode derrubar a primeira gravação.

A defesa é um teto de profundidade verificado **de forma iterativa** (pilha explícita, sem recursão), bem abaixo de qualquer limite do interpretador, mais `RecursionError` no mesmo `except` da corrupção, para o caso que estoura no próprio parser.

---

## Como ficou no código

- `memory_store.MAX_NESTING_DEPTH = 32` (o esquema usa 4 níveis) e `_nests_deeper_than()`, iterativa.
- `_reload` rejeita o arquivo fundo demais com `ValueError` e captura `(ValueError, UnicodeDecodeError, RecursionError)`. Os dois casos fazem backup `.broken-*`, `available=False` e `memory_unavailable`.
- `test_deeply_nested_file_takes_the_corruption_path` cobre as três faixas: 40, 600 e 100 000 níveis.

---

## Relation to ADRs and next steps

- **ADR-0002**, emenda de 29/10/2026: toda falha de interpretação segue o caminho de corrupção. O arquivo local não ganha teto de bytes.
- As tools recebem só escalares, então estrutura funda só entra por edição manual. Uma tool futura que aceite `dict`/`list` livre precisa do mesmo teto na validação (ADR-0016).
