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
