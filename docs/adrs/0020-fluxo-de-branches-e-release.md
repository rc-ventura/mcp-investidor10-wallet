# ADR-0020: Fluxo de branches e release — `main` só contém versões publicadas no índice

- **Status**: Accepted
- **Date**: 2026-11-02
- **Deciders**: Mantenedor + Claude (spec 005, Lote 0)
- **Related spec**: [`specs/005-desktop-distribution/`](../../specs/005-desktop-distribution/) (FR-032 a FR-034, research D18)
- **Code**: `scripts/check_promotion.py`, `.github/workflows/main-gate.yml`, `.github/workflows/ci.yml`
- **Research**: [`docs/research/fichamentos/modelos-de-branching.md`](../research/fichamentos/modelos-de-branching.md), [`docs/research/fichamentos/publicacao-de-pacotes-e-promocao-de-artefatos.md`](../research/fichamentos/publicacao-de-pacotes-e-promocao-de-artefatos.md)

---

## Context

O marketplace do produto é o próprio repositório: o que está na branch padrão
chega ao usuário. A partir da spec 005 o plugin deixa de carregar código e
passa a apontar para uma versão publicada no PyPI (servidor empacotado, ADR
a ser escrito no Lote 5). Se `main` receber um plugin antes de a versão
existir no índice, o usuário instala um plugin que manda baixar uma versão que
ainda não existe.

Até a spec 004 o fluxo era `main` mais branches de lote (`spec-NNN/*`,
`etapa-*`), com a tag criada sobre `main` e a publicação logo depois (ADR-0011).
Isso funcionava porque `main` não apontava para nada externo. Com o plugin
apontando para o índice, a ordem precisa ser outra: publicar primeiro,
mover o ponteiro depois.

Outras duas necessidades: validar o plugin no Claude Desktop real antes da
versão final (FR-034), o que exige uma versão instalável sem passar por `main`;
e permitir correção urgente enquanto há trabalho inacabado em integração.

## Decision

1. **Princípio:** `main` só contém versões já publicadas no índice. O
   lançamento é a publicação, não o merge em `main`.
2. **Branches:**
   - `main`: versões lançadas; é o que o marketplace entrega.
   - `develop`: integração. Cada lote de uma spec sai de `develop`, na branch
     `spec-NNN/<assunto>`, e volta por pedido de revisão contra `develop`.
   - `hotfix/X.Y.Z`: sai de `main`, para correção urgente.
   - Não há `release/*`.
3. **Pré-lançamento:** tag `vX.Y.ZrcN` criada em `develop`, publicada e
   verificada como uma versão final, nunca promovida para `main`. É a base da
   validação no Desktop por Upload plugin. A checagem de changelog da tag usa a
   seção da versão base `[X.Y.Z]`.
4. **Versão final:** pedido de preparação em `develop` (versão, pacote
   empacotado, changelog); tag `vX.Y.Z` em `develop`; publicação, depois de
   aprovação do ambiente `pypi`; job `verify`; criação de `promote/vX.Y.Z` no
   commit da tag; pedido de revisão dessa branch para `main`, aprovado e
   mesclado pelo mantenedor.
5. **Hotfix:** `hotfix/X.Y.Z` sai de `main`; tag, publicação, `verify`,
   promoção para `main` e pedido da tag para `develop`, para a correção não se
   perder.
6. **Portão:** a verificação `main-gate`, obrigatória em `main`, executa
   `scripts/check_promotion.py` e só aceita um pedido cuja origem seja
   `promote/vX.Y.Z` (versão final, sem sufixo de pré-lançamento), cujo commit
   seja o da tag `vX.Y.Z`, cuja versão esteja igual nos quatro manifestos do
   plugin e no manifesto do servidor empacotado (quando existir) e cuja versão
   exista no índice. Índice inacessível falha fechado.
7. **CI:** `ci.yml` roda em `push` e em pedido de revisão para `main` e para
   `develop`.
8. **Quem faz o quê:** tags, aprovação da publicação e merges são do
   mantenedor. A automação cria branches e abre pedidos, nunca faz merge. As
   regras de proteção de `main` e `develop` e o ambiente `pypi` (aprovação
   manual a cada execução, implantação permitida para tags `v*`) são
   configurados pelo mantenedor no GitHub.

### Diferenças em relação ao Git Flow padrão

- Não há `release/*`: com um mantenedor só, a preparação é um pedido comum em
  `develop`.
- A tag fica em `develop`, não em `main`.
- O lançamento é a publicação, não o merge em `main`.
- A CI impede que `main` aponte para o que ainda não existe no índice.

## Alternatives considered

### Alternative A: Git Flow estrito

Branch `release/*`, merge em `main` antes da publicação.

**Why not chosen**:
- O merge em `main` antes da publicação deixa uma janela com `main` apontando
  para uma versão inexistente, e o plugin em `main` depende de um artefato
  externo (fichamento `modelos-de-branching`, F1: no Git Flow cada merge em
  `master` é "a new production release by definition").
- A validação no Desktop só aconteceria depois de todos os lotes, porque o
  pré-lançamento sairia de `release/*`.

### Alternative B: `main` + `develop` sem `hotfix/*`

**Why not chosen**:
- Sem caminho limpo para uma correção urgente enquanto `develop` tem trabalho
  inacabado.

### Alternative C: `stable` como branch padrão e trabalho em `main`

**Why not chosen**:
- Só há apoio em relatos de comunidade (graphql-js, Kotlin), e o GitHub usa uma
  única configuração para a visão padrão e a base dos pedidos de revisão
  (`modelos-de-branching`, F4, F6, F7, F8).

### Alternative D: ponteiro por `ref` ou `sha` no `marketplace.json`

**Why not chosen**:
- É documentado para o Claude Code (`modelos-de-branching`, F5), mas o caso do
  marketplace pessoal no Desktop não está documentado.

### Alternative E: repositório separado só para o marketplace

**Why not chosen**:
- Um repositório e um token de escrita a mais, sem ganho para um mantenedor só.

### Alternative F: release por tag no tronco, sem `develop` (trunk-based)

**Why not chosen**:
- "Release from a tag on the trunk" é uma otimização reconhecida
  (`modelos-de-branching`, F3), mas colocaria o plugin novo em `main` antes da
  publicação. O fluxo adotado aproveita a ideia de tag sem branch de release e
  acrescenta o portão.

## Consequences

### Accepted

- `main` nunca aponta para uma versão que não existe no índice, e a CI impede
  isso mecanicamente.
- O pré-lançamento é construído uma vez e validado no Desktop antes da versão
  final (padrão "build once, promote", `publicacao-de-pacotes-e-promocao-de-artefatos`,
  F3 a F6).
- A correção urgente tem caminho próprio, sem arrastar trabalho de `develop`.

### Trade-offs

- Sem `release/*`, `develop` fica parado entre o pré-lançamento e a versão
  final, ou cada correção gera um novo pré-lançamento.
- Um passo humano a mais por versão final: o merge de `promote/vX.Y.Z`.
- A combinação Git Flow sem `release/*`, tag em `develop` e publicação antes do
  merge em `main` não apareceu em nenhuma fonte lida; a ordem publicar antes de
  mover o ponteiro aparece em exemplos reais de automação, sem norma formal
  (`publicacao-de-pacotes-e-promocao-de-artefatos`, F7).

### Verificações pendentes

1. O Claude Desktop lê a branch padrão ao adicionar o marketplace (spike do
   Lote 1). Se não ler, a premissa de que `main` é o que o usuário recebe muda.
2. O ambiente `pypi` aceita tags criadas em `develop` e em `hotfix/*`.
3. A instalação por versão exata de pré-lançamento funciona com pip e com
   `uvx` (a documentação do `uv` não cobre o caso: `uv`, Resolution, F2).

### Conditions that invalidate this decision

This decision should be **revisited** if:

1. O plugin voltar a carregar o código (deixando de apontar para o índice): a
   razão do portão desaparece.
2. O Claude Desktop passar a ler outra branch ou um `ref` do marketplace de forma
   documentada, o que permitiria separar o ponteiro de `main`.
3. O projeto passar a ter mais de um mantenedor ou várias versões mantidas em
   paralelo, o que pede `release/*`.

### Migration path when needed

- Adotar `release/*`: criar a branch no pedido de preparação e mover a tag para
  ela; o `main-gate` continua valendo.
- Trocar a fonte do ponteiro (`ref` no `marketplace.json`): remover o passo de
  promoção e manter só o job `verify`.

## References

- ADR-0011 (pipeline de release; emendado por este ADR quanto à ordem publicar antes de promover)
- `specs/005-desktop-distribution/research.md` D18
- `docs/research/fichamentos/modelos-de-branching.md`
- `docs/research/fichamentos/publicacao-de-pacotes-e-promocao-de-artefatos.md`

---

## Emenda 2026-11-14 (spec 005, Lote 7: promoção automática, Dependabot e primeira versão final)

O Lote 7 implementou a promoção do passo 4 (`.github/workflows/promote.yml` e
`scripts/plan_promotion.py`) e acrescentou o `dependabot.yml`. Duas decisões
ficaram de fora do texto original:

1. **A primeira versão final é promovida à mão.** O GitHub só dispara
   `workflow_run`, `schedule` e `workflow_dispatch` a partir de workflows que
   existem na branch padrão (`main`), e o Dependabot lê a configuração dela.
   Enquanto `promote.yml` só existir em `develop`, a criação de
   `promote/vX.Y.Z` e do pedido para `main` é feita com
   `python3 scripts/plan_promotion.py --tag vX.Y.Z --apply`
   (`docs/RELEASING.md`, "Promoção à mão"). Essa primeira promoção, a da
   0.4.0, é a que leva os workflows para `main`. Daí em diante vale o passo 4
   como escrito. O `dry-run` do `promote.yml` e o primeiro disparo do
   `live.yml` passam para depois dela (tasks T091/T092). A automação continua
   só criando branches e abrindo pedidos, nunca fazendo merge (passo 8).
   Lição: [`workflows_de_evento_so_valem_na_branch_padrao`](../learning-lessons/workflows_de_evento_so_valem_na_branch_padrao.md).
2. **O Dependabot abre pedidos contra `develop`, não contra `main`.** O
   `dependabot.yml` usa `target-branch: develop` nos ecossistemas `uv` e
   `github-actions`, com intervalo semanal e `cooldown` de 7 dias, para que
   atualização de dependência siga o mesmo caminho de qualquer outra mudança e
   nenhum pedido de origem diferente de `promote/v*` chegue a `main` (o
   `main-gate` o recusaria). O `cooldown` mantém a postura de dependências
   fixadas do ADR-0001: uma versão recém-publicada não vira pedido no mesmo dia.

Além disso, o `plan_promotion.py` aceita `--sha` e acha a tag final no commit
do release, porque a documentação do GitHub não define o `head_branch` de um
`workflow_run` disparado por tag. Quando o commit da tag não é ancestral de
`origin/develop` (hotfix), ele devolve também a ação de abrir o pedido da tag
para `develop`, que é o passo 5 deste ADR.

---

## Emenda 2026-11-20 (spec 005, revisão final: configurações reais e limites do `main-gate`)

A revisão final da spec 005 (ciclo 1, `reports/sdd-final-review/005/cycle-1-20261120-1004.md`)
comparou este ADR com o que está de fato configurado no GitHub e com o que o
`main-gate` garante. Ficam registrados:

1. **Configuração real, lida em 2026-11-20.**
   - Rulesets `develop-protegida` e `main-protegida`: pedido de revisão
     obrigatório com **0 aprovações** (há um só mantenedor, e aprovar o próprio
     pedido não é possível), 11 verificações obrigatórias em `develop` (os 9
     `test`, `plugin` e `audit`) e 12 em `main` (as mesmas, mais `main-gate`),
     sem force push, sem exclusão e **lista de bypass vazia**.
   - Ambiente `pypi`: um revisor obrigatório (o mantenedor),
     `prevent_self_review: false`, porque o revisor é o único mantenedor, e
     implantação **restrita a tags `v*`**. A restrição de tag foi acrescentada
     em 2026-11-20: até então o ambiente não tinha política de implantação, em
     divergência com o §8.
   - **Publisher no PyPI:** confirmado pelo mantenedor em 2026-11-25; aponta para
     este repositório, para `release.yml` e para o ambiente `pypi`.
2. **O `main-gate` é guarda contra erro, não contra um escritor hostil.** Ele
   roda `scripts/check_promotion.py` a partir do checkout do próprio pedido, então
   um pedido que altere o script ou o workflow pode neutralizá-lo. Quem consegue
   isso já tem escrita no repositório, e aqui é o mantenedor. O controle real são
   os rulesets e a segurança da conta do mantenedor. `CODEOWNERS` não acrescenta
   nada com 0 aprovações e um mantenedor; reavaliar junto com a condição 3 de
   "Conditions that invalidate this decision" (mais de um mantenedor).
3. **Qualquer tag `v*` que passe nas checagens chega ao clique de aprovação do
   `pypi`.** O `check_release_tag.py` confere formato, `__version__` e changelog,
   mas não confere que o commit da tag seja alcançável a partir de `develop` ou
   `main`. O portão é a aprovação humana do ambiente, e isso é aceito.

---

## Emenda 2026-11-26 (integração do Claude no GitHub Actions)

O mantenedor instalou a integração com `/install-github-app` (PR #61). O modelo
do instalador não conhece as regras deste repositório. Entra com os ajustes
abaixo.

1. **Escopo.** São dois workflows.
   - `claude.yml`, sob demanda: `@claude` em comentários, em revisões e em issues
     novas. Pela documentação, só quem tem escrita no repositório o aciona. O
     gatilho `issues: assigned` foi removido, porque atribuir uma issue de
     terceiro poderia fazer o texto dela valer como pedido.
   - `claude-code-review.yml`, revisão automática de pedidos. Pula pedidos de
     forks, do Dependabot e de `promote/*`.
2. **O fluxo deste ADR não muda.** `claude.yml` usa `base_branch: develop`, porque
   o padrão da action é criar branches a partir da branch padrão (`main`). O
   trabalho do Claude entra por pedido para `develop`, como qualquer outro. **O
   merge é sempre do mantenedor**; isto é regra de uso, não bloqueio técnico
   (item 5). `claude-review` **não é verificação obrigatória**: pode ficar verde
   sem ter revisado. Ele também não substitui a revisão final antes do release.
3. **Ativação.** A action exige que o arquivo do workflow seja idêntico ao da
   branch padrão, e os eventos `issue_comment` e `issues` só disparam a partir
   dela. Os arquivos chegam a `main` pela próxima promoção; até lá, não se conta
   com a integração. Pela mesma regra, um pedido que altere esses arquivos não é
   revisado, e uma mudança neles volta a depender de promoção. Lição
   relacionada:
   [`workflows_de_evento_so_valem_na_branch_padrao`](../learning-lessons/workflows_de_evento_so_valem_na_branch_padrao.md).
4. **Versões.** As actions são fixadas por SHA, como nos demais workflows:
   `actions/checkout` no mesmo SHA do restante do repositório e
   `anthropics/claude-code-action` na v1.0.283, publicada em 2026-11-19 e, na
   data desta emenda, com mais de 7 dias (carência do ADR-0001). As atualizações
   seguem o Dependabot (`github-actions`).
   - **Exceção aceita:** o plugin `code-review` vem do repositório
     `anthropics/claude-code` **sem versão fixa** e pode mudar sem commit aqui.
     Aceito porque a origem é o fornecedor da própria action e a revisão é só
     consultiva. Não foi verificado se o campo aceita uma referência fixa.
5. **Acesso e riscos aceitos.**
   - Há um secret novo no repositório, `CLAUDE_CODE_OAUTH_TOKEN`, ligado à
     assinatura do mantenedor.
   - O bloco `permissions:` limita o token do workflow, mas não o token do app do
     Claude, que a action usa quando o app está instalado. Pela documentação, o
     app pede escrita em conteúdo, issues e pedidos. As permissões concedidas na
     instalação não foram conferidas.
   - Os rulesets impedem push direto e force push em `develop` e `main`. Com
     **0 aprovações**, porém, um token com escrita poderia fazer o merge de um
     pedido com as verificações verdes. Para `main` ainda valeria o `main-gate`,
     que é guarda contra erro, não contra um escritor hostil (emenda de
     2026-11-20).
   - Não há ruleset de tags, então um token com escrita poderia criar uma tag
     `v*`. A publicação continua dependendo da aprovação no ambiente `pypi`.
     **Não se aprova publicação que o mantenedor não iniciou.**
   - Ao chamar `@claude` em um pedido ou issue de terceiro, o texto dessa pessoa
     é lido pelo agente e pode conter instruções escondidas.
6. **Revisão do que o Claude produzir.** Segue o mesmo caminho de qualquer
   pedido, com atenção especial a mudanças em `.github/`, dependências e
   tratamento da credencial ou do ID da carteira.

**Revisitar** se o repositório ganhar outro colaborador com escrita, se o Claude
passar a aprovar ou fazer merge, se houver incidente na action ou no plugin, ou
se passar a ser possível fixar a versão do plugin.

**Como desfazer:** apagar os dois workflows, apagar o secret e desinstalar o app.

