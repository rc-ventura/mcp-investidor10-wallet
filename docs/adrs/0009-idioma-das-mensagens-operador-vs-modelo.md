# ADR-0009: Idioma das mensagens — operador em PT-BR, modelo em inglês

- **Status**: Accepted
- **Date**: 2026-10-18
- **Deciders**: User (constitution v1.1.0, seção "Formato e Estilo de Código" e
  spec 002 FR-006/FR-007)

## Context

A decisão de 2026-10-10 registrada no plano da spec 001 dizia: "código,
docstrings e mensagens de erro em inglês (interação com o usuário permanece
pt-BR)". A Fase 0 do ROADMAP introduziu um novo consumidor das mensagens do
servidor: o **operador** que configura o produto na primeira execução
(onboarding), para quem a doc é PT-BR e o erro precisa ser amigável — sem
traceback e sem inglês técnico. O ROADMAP é explícito: "validar o WALLET_ID
(fetch + erro amigável) ... docs PT-BR".

A constituição (v1.1.0) passou a reger também o formato de código, mas não
havia registro decisório do idioma por audiência — cada ciclo re-derivaria a
regra.

## Decision

1. **Mensagens de operador em PT-BR**: erros de configuração no startup
   (`WALLET_ID` ausente/inválido, TTL inválido), avisos e erros de migração da
   memória, resultado da validação da carteira e documentação de onboarding
   (README, troubleshooting) são escritos em PT-BR, com o estilo
   trigger-phrase (recurso + causa + próximo passo) já adotado no projeto.

2. **Contrato com o modelo permanece em inglês**: docstrings das tools MCP,
   erros estruturados `error.message` das tools e logs técnicos seguem em
   inglês — são o contrato que o LLM lê (ADR-0007 §4) e não mudam.

3. **Fronteira por audiência, não por canal**: a regra não é "stderr em PT-BR,
   stdout em EN" — é "mensagem lida pelo operador humano → PT-BR; mensagem
   lida pelo modelo → EN". Avisos de stderr sobre fonte indisponível são PT-BR
   (operador); o envelope `error.message` da mesma falha segue EN (modelo).

4. **Sem bilinguismo duplicado**: cada mensagem existe em um idioma, para uma
   audiência. Não se duplica a mesma mensagem nos dois idiomas.

## Consequences

- A decisão de 2026-10-10 fica parcialmente revisada: o escopo do desvio é
  apenas mensagens operador-facing do bootstrap; docstrings e erros de tools
  permanecem como antes.
- Desenvolvedores de novas mensagens de startup/onboarding devem escrevê-las
  em PT-BR e reusar os esqueletos de `bootstrap.py` (spec 002, contrato C6).
- Esta decisão deve ser **revisitada** se: o público-alvo mudar de idioma, as
  mensagens de operador passarem a ser consumidas por máquina (ex.: parser de
  CI), ou a spec MCP formalizar idioma de tool descriptions.
- Related: ADR-0003 §3 (falha de startup estruturada), ADR-0007 §4 (docstrings
  como contrato), spec 002 contracts/packaging-and-config.md C6.