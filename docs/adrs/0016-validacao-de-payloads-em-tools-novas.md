# ADR-0016: Regra de validação de payloads para tools novas — pydantic validate-then-passthrough

- **Status**: Accepted
- **Date**: 2026-10-28
- **Deciders**: Tech Leader + User (ciclo spec 004; item da Fase 1 do ROADMAP)
- **Related spec**: [`specs/004-hardening/`](../../specs/004-hardening/)
- **Code**: nenhum (decisão de design; nenhuma tool nova é implementada na spec 004)
- **Research**: `specs/004-hardening/contracts/ops-and-docs.md`; `docs/api/README.md` ("As duas fronteiras de validação")

---

## Context

Hoje a validação do payload da fonte é manual, em `wallet_client.request`:
`required_keys`, `required_types`, `NUMERIC`, `expected_type`. Funciona, mas a
regra é implícita e cada endpoint a reimplementa. A Fase 2 do ROADMAP prevê
várias tools novas (`get_entries`, `get_earnings_detailed`, projeção de renda,
entre outras), todas sobre uma API não documentada e não versionada, onde o
risco nº 1 é o formato mudar sem aviso. `pydantic` já está na árvore de
dependências como transitiva do FastMCP, então adotá-lo não cria superfície nova
de supply chain.

## Decision

1. **Um `BaseModel` leve por endpoint novo**, usado só para validar
   (`model_validate`), em modo **validate-then-passthrough**: o envelope continua
   devolvendo o **payload cru**, preservando a decisão de passthrough do ADR-0007.
   O modelo não transforma, agrega nem renomeia campos.
2. **`Strict` para o caso booleano-versus-inteiro** (um `bool` nunca vale como
   número) e **`FiniteFloat` para NaN e infinito**. Materializa a "regra uniforme
   de validação" que o ciclo 3 de revisão diagnosticou.
3. **Falha de validação vira `unexpected_format`**, antes de qualquer cache, como
   já ocorre hoje. Nunca valor fabricado.
4. **Escopo: só tools novas da Fase 2.** Não há retrofit das tools existentes
   (já passaram quatro ciclos verdes sem outro motivo para tocá-las) nem
   pydantic no schema do `memory.json`: lá o formato é a parte fácil, e a
   semântica de degradação (backup `.broken-*`, modo indisponível, somente-leitura)
   continua customizada.
5. **`pydantic` segue transitiva do FastMCP**, não é dependência direta. Se deixar
   de ser transitiva, a regra exige emenda da Constituição V.1 antes de qualquer
   adoção.

## Alternatives considered

### Alternative A: retrofit de todas as tools existentes

**Why not chosen**:
- Risco sem ganho: o código atual está estável e coberto por testes de contrato.

### Alternative B: pydantic também para o `memory.json`

**Why not chosen**:
- Troca uma validação simples por outra sem resolver o difícil, que é a
  semântica de degradação.

### Alternative C: manter só a validação manual

**Why not chosen**:
- Cada tool nova reimplementaria checagens ad hoc, e a regra continuaria implícita.

## Consequences

### Accepted

- Tools novas nascem com validação declarativa e uniforme, fácil de testar com
  fixtures anonimizadas.
- O passthrough e a auditabilidade (o que o usuário vê é o que a fonte devolveu)
  são preservados.

### Trade-offs

- Dois estilos de validação convivem até o fim da Fase 2 (manual nas tools
  existentes, pydantic nas novas).
- Dependência indireta de uma transitiva: coberta pela condição 1 abaixo.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. O FastMCP deixar de depender de `pydantic`.
2. As tools existentes precisarem de mudança de contrato por outro motivo (aí o
   retrofit passa a ter justificativa).

### Migration path when needed

1. Migrar uma tool por vez, mantendo o teste de contrato como rede de segurança.

## References

- ADR-0005 (dependência da API não documentada), ADR-0007 (passthrough)
- Constituição, Princípio V.1
- `docs/ROADMAP.md` (item "Validação de payloads via pydantic")
