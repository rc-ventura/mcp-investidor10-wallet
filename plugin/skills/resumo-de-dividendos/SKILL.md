---
name: resumo-de-dividendos
description: Resumo de proventos e renda passiva da carteira usando o rendimento recorrente atual
---

1. Chame `get_session_context` para carregar o contexto do investidor.
2. Obtenha `get_earnings` para o período desejado (pergunte ao usuário se não vier especificado).
3. Apresente o total de proventos do período e a renda passiva mensal equivalente, usando o rendimento recorrente atual — nunca um dividend yield médio histórico.
4. Compare com a meta salva na memória (`get_wallet_goal`) quando houver.
5. Mencione que `get_earnings` retorna o total agregado do período e que cotações têm atraso de aproximadamente 15 minutos.