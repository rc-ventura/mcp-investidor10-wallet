---
name: check-de-tese
description: Verificação de uma tese de investimento contra os dados atuais da carteira e do mercado
---

1. Chame `get_session_context` para carregar o contexto do investidor.
2. Liste as teses salvas com `get_theses` e identifique a tese relacionada ao ativo em questão (ou peça ao usuário que indique qual).
3. Obtenha os dados atuais do ativo com `get_asset_quote` (apenas ações B3) ou `get_wallet_positions` para demais classes.
4. Compare a premissa central da tese com os dados atuais: preço, indicadores disponíveis e proventos via `get_earnings` quando relevante.
5. Reporte objetivamente se a tese segue válida, enfraquecida ou invalidada, citando números. Lembre que cotações têm atraso de aproximadamente 15 minutos.
6. Sugira registrar o desfecho na memória com `record_decision_outcome` ou atualizar a tese — somente se o usuário confirmar.