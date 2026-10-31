# ADR-0015: Modo privacidade — `WALLET_MASK_VALUES`, lista de campos permitidos e tools monetárias indisponíveis

- **Status**: Accepted (amended 2026-10-28)
- **Date**: 2026-10-28
- **Deciders**: Tech Leader + User (ciclo spec 004, clarificação de 2026-10-27)
- **Related spec**: [`specs/004-hardening/`](../../specs/004-hardening/)
- **Code**: `src/investidor10_wallet/privacy.py`, `src/investidor10_wallet/server.py`, `src/investidor10_wallet/bootstrap.py` (`_parse_mask`)
- **Research**: `specs/004-hardening/research.md` (D8); `specs/004-hardening/contracts/privacy-mode.md`

---

## Context

O ID da carteira é a credencial: quem o tem lê todos os valores pela API, e o
botão de mascarar do site é só visual (verificado em 17/10/2026: com a carteira
mascarada, `get_wallet_summary` e `get_wallet_positions` devolveram patrimônio,
quantidades e proventos reais). Como todo resultado de tool entra no contexto do
provedor do modelo, quem quer analisar alocação sem expor montantes não tem
proteção do lado da fonte. A fronteira de privacidade é o provedor do LLM, não a
localização do servidor (ROADMAP).

## Decision

1. **Ativação só por variável de ambiente** `WALLET_MASK_VALUES`, lida na
   inicialização. Nenhuma tool aceita parâmetro de privacidade: o schema de
   entrada não muda, e o modelo não pode desligar a proteção. Valores:
   `1/true/yes/on` ligam; `0/false/no/off` ou ausente desligam (sem diferenciar
   maiúsculas, espaços aparados); qualquer outro valor aborta a inicialização
   com mensagem PT-BR. Ligado, uma linha em stderr avisa o operador.
2. **Lista de campos permitidos (fail-closed).** `privacy.py` mantém uma
   allowlist por tool: summary, allocation, topo de posições e cada linha de
   posição. Campo fora da lista é omitido, inclusive campos que a fonte venha a
   adicionar e campos de semântica não confirmada (`weighted`, `gnr`, `gnp`,
   `ranking`), até haver evidência de que não são montantes. Preço unitário
   (`avg_price`, `current_price`), percentuais, razões, notas e dados públicos do
   ativo ou do fundo passam.
3. **Aplicação depois do cache.** O cache guarda o payload cru; a máscara gera
   uma cópia na saída da tool. Alternar o modo nunca serve dado cru em resposta
   mascarada, e o payload em cache nunca é mutado.
4. **Marcador.** O envelope mascarado ganha
   `"privacy": {"masked": true, "omitted": [<campos removidos nesta resposta>]}`,
   para o modelo saber o que não tem sem receber valores. As docstrings das três
   tools mascaráveis instruem a nunca estimar nem reconstruir os valores omitidos.
5. **Tools essencialmente monetárias ficam indisponíveis.**
   `get_patrimony_history` e `get_earnings` devolvem `privacy_mode_unavailable`
   sem chamar a fonte (a validação de datas de `get_earnings` roda antes, para
   `invalid_params` seguir igual). O servidor não substitui por razões derivadas
   calculadas por ele.
6. **Inalterados:** `get_asset_quote` (dado de mercado), tools de memória e
   `get_session_context`.

## Alternatives considered

### Alternative A: parâmetro de tool para ligar/desligar

**Why not chosen**:
- A proteção é contra o dado sair da máquina para o modelo; um parâmetro poderia
  ser desligado pelo próprio modelo.

### Alternative B: denylist de campos monetários

**Why not chosen**:
- Um campo monetário novo da fonte passaria sem aviso. A allowlist falha para o
  lado seguro.

### Alternative C: mascarar no `wallet_client`, antes do cache

**Why not chosen**:
- Acopla privacidade ao transporte e complica os testes; aplicar na saída mantém
  o cache cru e a máscara testável isoladamente.

### Alternative D: razão calculada no servidor para `get_earnings` (proventos ÷ valor aplicado)

**Why not chosen**:
- Introduz um cálculo financeiro no servidor que a spec 006 trata de forma
  própria, e foge de "o servidor não deriva números".

## Consequences

### Accepted

- Análise de alocação, rebalanceamento por percentual, diversificação e
  fundamentos continuam possíveis sem montantes no contexto do modelo.
- Novo campo monetário da fonte nunca vaza por omissão.
- Verificado contra a carteira real em 2026-10-28 (74 valores monetários
  coletados; só nomes e contagens foram impressos): sem a máscara, 75 ocorrências
  na saída; com a máscara, 0 vazamentos reais. A única coincidência numérica foi
  `current_price` igual a `equity_total` numa posição de quantidade 1, que é preço
  de mercado e não revela o total.

### Trade-offs

- Perde-se: valores em R$, aporte sugerido em reais, histórico de patrimônio e
  proventos em R$ (a skill de dividendos degrada para o erro estruturado).
- O modo não é anonimização. Preço unitário e percentuais permitem estimar
  proporções, não montantes. Texto livre da memória (teses, regras, objetivo,
  notas) e o que o próprio usuário digita na conversa não são mascarados.
- O ID da carteira continua sendo a credencial: o modo protege o que vai ao
  modelo, não quem tem o link.
- As descrições das tools só chegam ao modelo até o bloco `Args:` (comportamento
  do FastMCP); por isso as notas de privacidade ficam antes dele.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. A fonte passar a expor montantes em campos hoje na allowlist.
2. Surgir suporte confiável a modelo local (Ollama) que torne o mascaramento
   desnecessário para quem exige privacidade total.

### Migration path when needed

1. Ajustar as allowlists e o contrato `privacy-mode.md`; o teste de vazamento com
   fixtures cobre a regressão.

## References

- ADR-0004 (modelo de ameaça), ADR-0007 (envelope), ADR-0014 (erros; novo código)
- `specs/004-hardening/contracts/privacy-mode.md`
- `docs/ROADMAP.md` (item "Modo privacidade", verificação de 17/10/2026)

## Emenda 2026-10-28 (pendências da revisão final da spec 004)

1. **Campo permitido com valor aninhado é omitido.** A allowlist só vale para
   valores escalares. Se uma chave permitida chegar com um objeto ou uma lista
   (por exemplo, `current_price: {"amount": ...}`), ela é omitida e listada em
   `privacy.omitted`, porque as chaves internas nunca foram verificadas. Isso
   fecha a condição de invalidação nº 1 sem precisar mexer nas allowlists.
2. **`truncated` entra na allowlist do topo de posições.** O sinal de lista
   incompleta (pendência "Posições truncadas") é um booleano sem valor
   monetário e precisa chegar ao modelo também com o modo privacidade ligado.
