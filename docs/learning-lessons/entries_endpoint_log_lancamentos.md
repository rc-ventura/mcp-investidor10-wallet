# Endpoint de lançamentos existe: `/entries/{id}/{seção}`

**Context:** Descoberto em sessão de 26/10/2026. O usuário perguntou "o que eu
comprei hoje" e o catálogo da API não tinha endpoint transacional — o
`contribution-consolidation` só agrega BUY/SELL por mês. O usuário apontou a
página pública `/wallet/public/{id}/entries?h={hash}`; inspecionando os chunks
JS do app foi encontrado o fetch real.

**Lição:**

- `GET /wallet/api/proxy/wallet-app/entries/{wallet_id}/{seção}` com
  `?length&start&orderBy=date&raw=1` retorna o log de lançamentos ordem a
  ordem: `date`, `type` (Compra/Venda), `ticker`, `qty`, `price`, `total`,
  `source` (MANUAL/BÔNUS/integração corretora), `currency`.
- `{seção}` é um índice numérico, não nome: `1` = renda variável (ações +
  FIIs + ETFs internacionais juntos), `2` = cripto, `4` = outros/caixa,
  `5` = tesouro, `6` = renda fixa privada/fundos. `3` retornou `{"data":[],
  "total":0}` na carteira testada. Strings (`list`, `all`, `Ticker`)
  retornam 500 — a rota existe e falha por tipo inválido.
- A URL pública da página (`/wallet/public/{id}/entries?h={hash}`) serve só
  para achar o hash e os chunks; o fetch real vai para
  `/api/proxy/wallet-app/entries/...` — que responde 404 HTML; o proxy
  correto é o `/wallet/api/proxy/wallet-app` já usado pelo client.
- O fluxo de `contribution-consolidation` bate centavo a centavo com a soma
  dos lançamentos do mês (verificado em 26/10: ações R$5.405 =
  CMIG4 2.428 + B3SA3 1.280 + BBAS3 1.697).

**Future intent:** tool `get_entries` (roadmap Fase 2) + snapshot de
posições para diff entre sessões. O `ticker_img` vem com HTML embutido —
decidir strip/passthrough ao implementar.
