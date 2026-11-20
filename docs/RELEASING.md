# Como lançar uma versão

Passo a passo do mantenedor. O fluxo e o motivo de cada regra estão no
[ADR-0020](adrs/0020-fluxo-de-branches-e-release.md). Em resumo: `main` só
contém versões já publicadas no PyPI e é o que o marketplace entrega; a tag
fica em `develop`; o lançamento é a publicação, não o merge em `main`.

Quem faz o quê: tags, aprovação da publicação e merges são do mantenedor. A
automação cria branches e abre pedidos de revisão, nunca faz merge.

## Antes de começar (uma vez por repositório)

- **Ambiente `pypi`** com aprovação manual a cada execução e implantação
  permitida só para tags `v*` (Settings > Environments).
- **Conjuntos de regras** de `main` (pedido de revisão obrigatório,
  verificações `main-gate` e CI obrigatórias, sem push direto) e de `develop`
  (pedido de revisão e CI).
- **Settings > Actions > General**: marcar "Allow GitHub Actions to create
  and approve pull requests", senão o `promote.yml` não consegue abrir o
  pedido de promoção.
- **Segredo `LIVE_WALLET_ID`** (Settings > Secrets and variables > Actions)
  com o ID da carteira pública fictícia, usado pelo `live.yml`. Nunca a
  carteira pessoal.

`promote.yml`, `live.yml` e o `dependabot.yml` só passam a valer depois de
chegarem a `main`, a branch padrão: o GitHub só dispara `workflow_run`,
`schedule` e `workflow_dispatch` a partir de workflows que existem na branch
padrão, e o Dependabot lê a configuração dela. Até lá, a promoção é feita
como na seção "Promoção à mão".

## Pré-lançamento (`X.Y.ZrcN`)

Serve para validar o plugin no Claude Desktop antes da versão final. Nunca
chega a `main`.

1. Em `develop`, por pedido de revisão: `__version__` em
   `src/investidor10_wallet/__init__.py` e `version` nos quatro manifestos do
   plugin (`plugin/.claude-plugin/plugin.json`, `.codex-plugin`,
   `.devin-plugin`, `gemini-extension.json`) e no `args` do servidor no
   manifesto do Claude (`mcp-investidor10-wallet==X.Y.ZrcN`). O changelog não
   precisa de seção própria do `rcN`, mas a seção da versão base `[X.Y.Z]`
   tem de existir (pode estar como "não lançado"): o `build` confere.
2. Depois do merge, criar e enviar a tag a partir de `develop`:

   ```bash
   git switch develop && git pull
   git tag vX.Y.ZrcN && git push origin vX.Y.ZrcN
   ```

3. Em Actions > Release, aprovar o job `publish` (ambiente `pypi`).
4. Conferir o `verify` verde nos três sistemas. O `promote.yml` roda e
   responde "nada a promover".

## Versão final (`X.Y.Z`)

1. Pedido de preparação em `develop` (branch `spec-NNN/versao-X.Y.Z`): a
   versão nos mesmos lugares do pré-lançamento e a seção `## [X.Y.Z]` no
   `CHANGELOG.md`. Rodar antes:

   ```bash
   uv run pytest && uv run ruff check . && uv run ruff format --check .
   uv run pytest -k consistency
   ```

2. Depois do merge, a tag a partir de `develop`:

   ```bash
   git switch develop && git pull
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```

3. Aprovar o `publish` e conferir o `verify` verde nos três sistemas.
4. Quando o `Release` termina com sucesso, o `promote.yml` cria
   `promote/vX.Y.Z` no commit da tag e abre o pedido para `main`.
5. **Aprovar os runs do pedido.** Como o pedido é aberto pelo
   `GITHUB_TOKEN`, o GitHub cria os runs do `pull_request` em estado de
   aprovação; na aba Checks do pedido, aprovar a execução do `main-gate` e da
   CI.
6. Com o `main-gate` verde, aprovar e fazer o merge. Só então o marketplace
   entrega a versão nova.
7. Conferir: adicionar o marketplace num cliente limpo (ou **Update** no
   Claude Desktop) e ver a versão nova no plugin.

### Promoção à mão

Quando o `promote.yml` ainda não está em `main`, ou falhou:

```bash
git fetch origin --tags
python3 scripts/plan_promotion.py --tag vX.Y.Z           # simulação
python3 scripts/plan_promotion.py --tag vX.Y.Z --apply   # cria a branch e o pedido
```

Também dá para disparar o workflow à mão, em Actions > Promote > Run
workflow, com a tag e `dry-run` marcado para só ver as ações.

## Hotfix

1. `hotfix/X.Y.Z` sai de `main`; a correção entra com teste, a versão sobe nos
   mesmos lugares e o changelog ganha a seção `[X.Y.Z]`.
2. Tag `vX.Y.Z` no commit da `hotfix/X.Y.Z`, publicação e `verify` como numa
   versão final.
3. O `promote.yml` percebe que o commit da tag não está em `develop` e abre
   dois pedidos a partir de `promote/vX.Y.Z`: um para `main` e outro para
   `develop`, para a correção não se perder. Os dois seguem o passo 5 da
   versão final.
4. Registrar aqui, na primeira vez, como foi.

## Quando a publicação falha

- **Falhou antes do `publish`** (tag, changelog, build ou smoke): corrigir em
  `develop`, apagar a tag local e remota e criar de novo no commit novo.
  Nada foi publicado.

  ```bash
  git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z
  ```

- **Falhou depois do `publish`** (no `verify`, ou a versão saiu errada): o
  número já existe no PyPI e **não pode ser reutilizado**, nem depois de
  apagado lá. Subir a versão (`X.Y.Z+1`, ou o próximo `rcN`) e lançar de novo.
  A versão com defeito nunca é promovida para `main`.
- **O `main-gate` recusou a promoção**: a mensagem diz a causa (origem que não
  é `promote/vX.Y.Z`, commit que não é o da tag, manifesto com outra versão,
  versão ausente no índice ou índice inacessível). Corrigir a causa e rodar o
  gate de novo; nunca contornar a regra.

## Testes contra a API real

O `live.yml` roda toda segunda-feira e sob demanda (Actions > Live API > Run
workflow), com a carteira fictícia do segredo `LIVE_WALLET_ID`. Uma falha
mostra só o código do erro. Falha repetida sem mudança no código é sinal de
que a API do Investidor10 mudou: abrir uma issue e conferir o mapeamento em
`src/investidor10_wallet/wallet_client.py`.
