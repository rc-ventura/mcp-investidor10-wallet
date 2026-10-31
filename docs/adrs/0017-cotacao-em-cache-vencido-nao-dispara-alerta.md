# ADR-0017: Cotação em cache vencido não dispara alerta — `stale_quote` em `pending_check`

- **Status**: Accepted (amended 2026-10-29)
- **Date**: 2026-10-28
- **Deciders**: Tech Leader + User (pendência da revisão final da spec 004, ciclo 1)
- **Related spec**: [`specs/004-hardening/`](../../specs/004-hardening/)
- **Code**: `src/investidor10_wallet/server.py` (`get_session_context`), `src/investidor10_wallet/wallet_client.py` (`WalletClient.is_stale`)
- **Research**: `reports/sdd-final-review/004/cycle-1-20261028-0741.md` (achado MEDIUM de QA); ADR-0003

---

## Context

O ADR-0003 decidiu que, numa queda da fonte (HTTP 5xx ou erro de transporte),
`request()` serve o cache vencido com `cached=true` e `fetched_at` explícitos,
até `WALLET_CACHE_MAX_STALE_SECONDS` (24 h por padrão). Para as tools de
consulta isso está certo: o modelo recebe a idade do dado e a informa ao
usuário.

O `get_session_context` usa o mesmo cliente para avaliar os alertas de preço,
mas só lia `data`. Com isso, uma cotação de até 24 h servida durante a queda
podia satisfazer um alerta. Como o disparo é **terminal** (ADR-0002: um alerta
disparado nunca volta a ser avaliado), um preço velho podia consumir o alerta
de forma permanente e ainda ser apresentado ao usuário como "preço atual". O
risco é de uma via só: o alerta perdido não volta.

## Decision

1. **Cotação vencida não dispara alerta.** Antes de avaliar os alertas de um
   ticker, `get_session_context` pergunta ao cliente se o envelope está vencido
   (`WalletClient.is_stale`). Vencido quer dizer `cached=true` e idade da
   entrada no cache maior ou igual ao TTL, medida no mesmo relógio monotônico
   que `request()` usa para decidir TTL e cache vencido. Nesse caso o ticker vai
   para `pending_check` com `reason: "stale_quote"` e seus alertas continuam
   ativos para a próxima sessão.
2. **Cache dentro do TTL continua valendo.** Um acerto normal de cache (mais
   novo que o TTL de 10 min) é tão fresco quanto a fonte permite, dado o atraso
   de ~15 min da B3, e dispara normalmente. Só o dado servido além do TTL, que
   `request()` só entrega quando a fonte falha, é bloqueado.
3. **Na dúvida, vencido.** Um envelope em cache cuja entrada não está mais no
   cache deste cliente tem idade desconhecida e é tratado como vencido.
4. **Sem mudança no envelope.** O contrato `{cached, fetched_at, data}` das
   tools de consulta fica igual. A regra mora no ponto que toma a decisão
   terminal, não no cliente HTTP.

## Alternatives considered

### Alternative A: gravar `fetched_at` em cada disparo e disparar mesmo assim

**Why not chosen**:
- Só documenta o erro. O alerta continua consumido por um preço que pode não
  valer mais, e o usuário recebe a notícia como se fosse atual.

### Alternative B: não usar cache nenhum na avaliação de alertas

**Why not chosen**:
- Repetiria uma requisição já feita na mesma sessão (por exemplo, logo depois
  de um `get_asset_quote`) sem ganho de frescor dentro do TTL. Além disso, em
  queda da fonte o resultado seria o mesmo da decisão escolhida: o alerta fica
  pendente.

### Alternative C: campo `stale` no envelope de todas as tools

**Why not chosen**:
- Muda o contrato de todas as tools de consulta para resolver um problema de uma. `cached` e
  `fetched_at` já deixam o modelo calcular a idade nas tools de consulta.

## Consequences

### Accepted

- Nenhum alerta é consumido por cotação velha. Em queda prolongada da fonte,
  os alertas ficam em `pending_check` com um motivo claro (`stale_quote`), que o
  modelo repassa ao usuário.
- A semântica do ADR-0003 (servir cache vencido com idade explícita) segue
  intacta nas tools de consulta.

### Trade-offs

- Um alerta que de fato foi atingido durante a queda só dispara quando a fonte
  voltar e a cotação ainda satisfizer o limite. Se o preço já voltou, o evento
  passa sem notificação. É preferível perder um evento a inventar um.
- A idade vem da entrada do cache (relógio monotônico), não de `fetched_at`.
  Ajustes do relógio de parede não afetam a classificação.

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. Os alertas passarem a ser avaliados continuamente (não só na abertura da
   sessão), o que pediria uma fonte de cotação própria.
2. O TTL do cache subir para perto do atraso aceitável de uma cotação.

### Migration path when needed

1. Trocar `is_stale` por uma idade máxima específica para alertas, mantendo
   `pending_check` como saída.

## References

- ADR-0002 (persistência da memória e entrega de alertas; disparo terminal)
- ADR-0003 (idade do cache vencido)
- ADR-0007 (envelope de dados)
- `docs/ROADMAP.md` (pendência "Frescor das cotações nos alertas")

## Emenda 2026-10-29 (revisão final da spec 004, ciclo 3)

A primeira versão calculava a idade como "agora menos `fetched_at`" no relógio
de parede, e a seção de trade-offs dizia que um ajuste de relógio erraria
"sempre em favor de não disparar". Isso estava errado: um relógio atrasado
encolhe a idade e faz uma cotação vencida parecer fresca, que é exatamente o
disparo terminal que este ADR proíbe. A idade agora é a da entrada do cache, no
relógio monotônico que `request()` usa. Assim, uma única fonte decide TTL,
cache vencido e alerta, e o relógio de parede só aparece no `fetched_at`
mostrado ao usuário. Os itens 1 e 3 e o trade-off foram corrigidos no texto.
