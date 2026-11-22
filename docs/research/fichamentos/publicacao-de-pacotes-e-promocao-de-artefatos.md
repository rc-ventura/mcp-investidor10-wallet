# Fichamento: publicação de pacotes e promoção de artefatos

- **Pesquisado em**: 2026-11-01
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (fluxo de release)

## Por que esta pesquisa

O plugin no repositório aponta para uma versão no PyPI. Isso criou um problema de ordem: testar antes de
publicar, e não deixar o repositório apontar para uma versão que ainda não existe. O mantenedor pediu boas
práticas de pipeline antes de decidir.

## Perguntas

1. Como o guia oficial do Python organiza a publicação por CI/CD?
2. Em que ordem publicar um pacote e atualizar o que aponta para ele?
3. Como funcionam pré-lançamentos e promoção do mesmo artefato?
4. Como o `uv` trata pré-lançamentos?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Publishing package distribution releases using GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) | Oficial | 2026-11-01 |
| F2 | [uv: Resolution](https://docs.astral.sh/uv/concepts/resolution/) | Oficial | 2026-11-01 |
| F3 | [Tuist: release channels](https://tuist.dev/en/docs/cli/release-channels) | Oficial | 2026-11-01 |
| F4 | [Snap channels (oneuptime)](https://oneuptime.com/blog/post/2026-03-02-how-to-understand-snap-channels-stable-candidate-beta-and-edge/view) | Comunidade | 2026-11-01 |
| F5 | [Promotion, GitOps, and "Build Once, Deploy Many"](https://thefrenchdevsecops.substack.com/p/promotion-gitops-and-build-once-deploy) | Comunidade | 2026-11-01 |
| F6 | [Immutable artefacts (UK Home Office)](https://development-segas.staticsite.core.homeoffice.gov.uk/patterns/immutable-artefacts) | Referência | 2026-11-01 |
| F7 | [Exemplo: bump do Homebrew depois do PyPI (regshape)](https://github.com/toddysm/regshape/pull/64) | Comunidade | 2026-11-01 |
| F8 | [Automatically maintaining Homebrew formulas (Simon Willison)](https://til.simonwillison.net/homebrew/auto-formulas-github-actions) | Comunidade | 2026-11-01 |
| F9 | [Build once or per environment (Stack Exchange)](https://backiee.wasmer.app/https_programmers_stackexchange_com/questions/350863/continues-delivery-build-once-or-build-per-environment) | Comunidade | 2026-11-01 |

As afirmações de F3 a F9 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### Pipeline do guia oficial do Python

- "Keep the build job separate from the publishing jobs." Os jobs de publicação só "download the already-built
  artifacts and upload them". [F1]
- A publicação no PyPI roda só em "tag pushes". [F1]
- "For security reasons, you must require manual approval on each run for the pypi environment." [F1]
- Publicação confiável: "the generated tokens are created for each of your projects individually and expire
  automatically". [F1]
- A ação de publicação gera atestados PEP 740 por padrão. [F1]
- TestPyPI serve para builds de testadores alfa e é "often used to indicate a healthy release publishing
  pipeline"; costuma publicar a cada push, sem aprovação manual. [F1]

### Ordem entre pacote e ponteiro

- Um projeto abre o PR de bump da fórmula do Homebrew depois do passo de publicação no PyPI, em vez de enviar
  direto. [F7]
- Outros condicionam a atualização ao resultado da publicação (`needs: release`). Um guia recomenda conferir URL
  e SHA no JSON do PyPI antes de mudar a fórmula. [F7]
- O padrão de Simon Willison usa um workflow disparado manualmente, e falhou numa ferramenta cuja dependência
  precisava de compilador Rust. [F8]
- A busca não encontrou documento normativo sobre essa ordem: as fontes são repositórios e páginas de comunidade.

### Pré-lançamento e promoção

- Tuist: candidato `X.Y.0-rc.N` sai de `main` e fica em observação por cerca de uma semana; a versão estável só
  sai depois de um candidato limpo. Correções críticas incrementam o `rc`. [F3]
- Snap: canais `edge`, `beta`, `candidate` e `stable`; `candidate` é para builds que o desenvolvedor considera
  prontos, antes de uma última rodada de teste. [F4]
- "Build once, promote": um único artefato imutável é promovido por todos os estágios, sem reconstrução. [F5]
  [F6]
- Diferenças entre ambientes ficam na configuração, não no artefato. [F5]
- Argumento minoritário: se os builds são reproduzíveis, a regra importa menos. [F9]

### `uv` e pré-lançamentos

- O padrão é `if-necessary`: "prefers stable versions over pre-releases" e recorre a pré-lançamentos só quando
  todos os candidatos estáveis são rejeitados. [F2]
- O modo `explicit` "considers pre-releases only for first-party requirements that contain a pre-release
  identifier". [F2]
- `--prerelease allow` e `--prerelease-package foo=allow` mudam a estratégia. [F2]

## O que as fontes não cobrem

- Regra separada para pin exato de pré-lançamento no `uv`, inclusive em `uvx`: F2 não trata desse caso.
- Se a publicação confiável do PyPI restringe a branch de onde vem a tag: F1 não trata disso.
- Promoção em que o ponteiro é o próprio repositório de marketplace: nenhuma fonte lida trata desse arranjo.

## Divergências entre fontes

- **Build once:** F5 e F6 tratam a regra como padrão; F9 argumenta que depende da reprodutibilidade.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D13 e D18
