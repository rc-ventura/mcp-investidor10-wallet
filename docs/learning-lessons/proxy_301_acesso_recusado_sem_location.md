# Proxy da carteira responde 301 sem `Location` para acesso recusado

**Context:** Em 31/10/2026 foi observado que o proxy da carteira responde **HTTP 301, sem cabeçalho `Location`, com o corpo "Acesso não autorizado"** quando a carteira é restrita e a credencial falta ou não vale, e também quando é privada. O cliente HTTP não segue redirecionamento e tratava qualquer status abaixo de 400 como sucesso: lia o corpo como JSON, falhava e levantava `unexpected_format`. A mensagem mandava o modelo dizer que a fonte "mudou de formato", e o usuário saía procurando um problema que não existia.
**Date:** 2026-11-04
**Future intent:** Uma resposta que a fonte usa para dizer "não" nunca é classificada como formato inesperado. 3xx, 401 e 403 do proxy da carteira são `access_denied`, decididos antes de ler o corpo e antes de tocar no cache.

---

## O que a fonte faz

| Situação | Resposta do proxy | Código no produto |
|---|---|---|
| Carteira pública | 200 com JSON | sucesso |
| Carteira restrita, credencial correta (`hash=<credencial>`) | 200 com JSON (esperado; a confirmar no roteiro S4 do Lote 3) | sucesso |
| Carteira restrita sem credencial | 301 sem `Location`, corpo "Acesso não autorizado" | `access_denied` |
| Carteira privada | a mesma resposta | `access_denied` |
| Carteira inexistente | 404 | `source_unavailable` (validação: `not_found`) |

A fonte **não distingue** restrita sem credencial de privada: as duas dão o mesmo 301. Por isso a mensagem de `access_denied` nomeia as duas causas e as duas ações (informar o link restrito atual ou deixar a carteira pública), e diz que tentar de novo não adianta.

O parâmetro da credencial é `hash` na chamada ao proxy e `h` no link que o site mostra ao compartilhar. O link é só a entrada: o servidor guarda e envia a credencial já separada.

---

## Como ficou no código

- `WalletClient.request` levanta `access_denied` para 3xx, 401 e 403 do proxy antes de ler o corpo (`follow_redirects=False` continua). A resposta recusada não entra no cache e não faz o servidor devolver cache vencido: dado de uma carteira que deixou de ser acessível não é "dado recente".
- O 301 vem de uma fixture anonimizada (`tests/fixtures/proxy_301_access_denied.json`): só status, tipo de conteúdo e corpo, sem ID, credencial nem cookie.
- A credencial vai só nas requisições ao proxy da carteira. A API de cotações nunca a recebe.
- `check_wallet` devolve `valid`, `access_denied`, `not_found` ou `unavailable`, e é a mesma classificação para o assistente de instalação, o `configure` e a sonda de inicialização.
- A sonda de inicialização só avisa em acesso recusado: abortar deixaria o usuário sem servidor para corrigir a própria configuração.

---

## Limites

- Um 301 sem `Location` hoje significa acesso recusado. Se o Investidor10 passar a redirecionar de verdade (por exemplo, mudança de domínio), o produto vai acusar acesso recusado para uma carteira acessível. O `Location` ausente é a pista que o teste de regressão fixa; se ele aparecer, a classificação precisa ser revista.
- Esta lição não afirma que gerar um link novo no site invalida o link antigo. Isso continua sem verificação (spec 005, D16).

---

## Relation to ADRs and next steps

- **ADR-0014**, emenda de 01/11/2026: o conjunto fechado de códigos passa a incluir `access_denied`.
- **ADR-0005**: mais um comportamento da API interna que não é documentado e que o teste semanal contra a API real precisa vigiar.
- **ADR-0019**: a página local e o `configure` usam a mesma validação.
