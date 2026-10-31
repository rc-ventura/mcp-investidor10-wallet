# FastMCP descarta o texto da docstring que vem depois do bloco `Args:`

**Context:** Descoberto na spec 004 (Hardening), ao validar que as notas do modo privacidade chegavam ao modelo: a descrição de `get_wallet_positions` servida pelo servidor tinha 52 caracteres, contra 1457 da docstring.
**Date:** 2026-10-28
**Future intent:** Manter o teste `tests/contract/test_tool_descriptions.py`, que impede texto depois do `Args:` em qualquer tool.

---

## Mental Model: a docstring tem duas saídas

O FastMCP interpreta a docstring no estilo Google (`fastmcp/utilities/docstring_parsing.py`):

| Parte da docstring | Para onde vai |
|---|---|
| Texto antes de `Args:` | `description` da tool, enviada ao modelo |
| Linhas do bloco `Args:` | `description` de cada parâmetro no `inputSchema` |
| Texto depois do bloco `Args:` | **descartado** |

## Reprodução mínima

```python
@m.tool
async def t(x: int) -> dict:
    """First paragraph.

    Args:
        x: the x.

    After-args rules that the model should see.
    """
```

`description` servida: `'First paragraph.'`. O parágrafo final não aparece em lugar nenhum.

## Impacto no projeto

Cinco tools tinham regras de uso depois do `Args:` que o modelo nunca recebia: `get_wallet_positions` (915 caracteres), `get_asset_quote` (782, incluindo o aviso de que cotações da B3 têm atraso de ~15 minutos), `get_earnings`, `get_patrimony_history` e `create_price_alert`. O ADR-0007 §4 e a Constituição III.1 tratam as docstrings como a camada confiável de regras de uso; para essas cinco, ela estava vazia. Sessões com o plugin recebiam parte das regras pela persona do hook, mas clientes sem o plugin não.

## Como evitar

- Em docstring de tool, escrever `Args:` **por último**.
- `tests/contract/test_tool_descriptions.py` falha se alguma tool tiver texto depois do bloco `Args:` e confere que as frases-chave chegam na descrição servida.

---

## Relation to ADRs and next steps

- **ADR-0007 §4** — docstrings como contrato com o modelo; emendado com esta regra de posição.
- **Constituição III.1** — regras de uso moram nas descrições das tools.
- Ao subir o FastMCP, revalidar o comportamento do parser de docstring.
