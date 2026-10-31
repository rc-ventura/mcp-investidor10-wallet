# Contract — documento de privacidade, `instructions=` e changelog

Cobre FR-007, FR-008, FR-032…FR-034, FR-037.

## `docs/PRIVACY.md` (PT-BR)

Seções obrigatórias:

1. **O que vai para onde** — tabela: Investidor10 (requisições com o ID da
   carteira; a fonte já tem os dados) · provedor do modelo de linguagem
   (todo resultado de tool entra no contexto — dados da carteira e da
   memória) · arquivo local (`memory.json`, `.log`, `.lock`, backups).
2. **A credencial é o link** — o ID/link público dá acesso a todos os
   valores via API; o botão de mascarar do site é só visual (verificado em
   17/10/2026). Tratar o ID como senha.
3. **Modo privacidade** — como ligar; o que preserva (alocação,
   rebalanceamento por %, fundamentos); o que perde (valores em R$,
   histórico de patrimônio, proventos); que texto livre da memória não é
   mascarado.
4. **Privacidade total** — exige também modelo de linguagem local; sem
   promessa de suporte nesta versão.
5. **Memória em pasta sincronizada** — segura na mesma máquina; uso
   simultâneo em duas máquinas não é protegido (cópia em conflito); usar uma
   máquina por vez.
6. **Telemetria** — o produto não envia telemetria.

Links: topo do `README.md` e linha final do relatório do assistente de
instalação (`Privacidade: veja docs/PRIVACY.md no repositório`, com URL
absoluta do GitHub).

## `instructions=` (inglês, propósito + índice)

Conteúdo-alvo (≤ 600 caracteres):

> Read-only access to one public Investidor10 wallet plus a persistent
> investor memory (theses, rules, decisions, price alerts). Start every
> session with get_session_context. Wallet tools return a data envelope
> {cached, fetched_at, data}; errors return {error: {code, message}} with
> isError set. B3 quotes carry ~15 minutes of delay. When privacy.masked is
> true, the operator withheld monetary amounts.

Sem persona, idioma, tom ou regras de recomendação (Constituição III.2).
Teste: `FastMCP.instructions` não vazio e sem as palavras proibidas
(`Portuguese`, `persona`, `you are`).

## ADR 0016 — regra de validação para tools novas

Conteúdo mínimo: um `BaseModel` por endpoint novo usado só para
`model_validate` (validate-then-passthrough; o envelope devolve o payload
cru, ADR-0007); `Strict` para bool-vs-int; `FiniteFloat` para NaN/inf;
falha → `unexpected_format`; **sem** retrofit das tools existentes e
**sem** pydantic no schema do `memory.json`; pydantic segue transitiva do
FastMCP (se deixar de ser, a regra exige emenda da Constituição V.1).

## `CHANGELOG.md` — 0.3.0

Entradas obrigatórias: trava da memória multi-processo e suporte Windows;
changelog `memory.json.log`; erros com `isError`; 3 códigos novos; modo
privacidade; `instructions`; **remoção da migração `./memory.json`** com a
instrução para quem ainda usa memória no diretório do repositório
(`mv ./memory.json ~/.investidor10/memory.json` ou definir
`WALLET_MEMORY_PATH`).
