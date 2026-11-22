# Fichamento: modelos de branching

- **Pesquisado em**: 2026-11-01
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (fluxo de release)

## Por que esta pesquisa

O marketplace do produto é o próprio repositório: o que está na branch padrão chega ao usuário. O
plugin passou a apontar para uma versão do PyPI, então `main` não podia receber um plugin antes de a
versão existir. O mantenedor pediu fontes sobre como separar desenvolvimento e versão lançada, e
sobre o Git Flow em particular.

## Perguntas

1. Como o Git Flow organiza branches e versões, e para quem ele serve?
2. O que GitLab Flow e trunk-based dizem sobre branch de produção e release?
3. O que o GitHub diz sobre branch padrão?
4. Há exemplos de usar uma branch estável como padrão?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [A successful Git branching model (Vincent Driessen)](https://nvie.com/posts/a-successful-git-branching-model/) | Oficial | 2026-11-01 |
| F2 | [What is GitLab Flow](https://about.gitlab.com/topics/version-control/what-is-gitlab-flow/) | Oficial | 2026-11-01 |
| F3 | [Trunk-based development: Branch for release](https://trunkbaseddevelopment.com/branch-for-release/) | Referência | 2026-11-01 |
| F4 | [GitHub: changing the default branch](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch) | Oficial | 2026-11-01 |
| F5 | [Host and maintain a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace.md) | Oficial | 2026-11-01 |
| F6 | [GitHub community discussion #7834](https://github.com/orgs/community/discussions/7834) | Comunidade | 2026-11-01 |
| F7 | [graphql-js #4131](https://github.com/graphql/graphql-js/issues/4131) | Comunidade | 2026-11-01 |
| F8 | [Kotlin Slack: mudar a branch padrão](https://slack-chats.kotlinlang.org/t/517145/i-would-like-to-switch-the-default-branch-on-github-from-dev) | Comunidade | 2026-11-01 |
| F9 | [Outpost2: development branch](https://forum.outpost2.net/index.php/topic,6070.0.html) | Comunidade | 2026-11-01 |

As afirmações de F6 a F9 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### Git Flow

- `master` é "the main branch where the source code of HEAD always reflects a production-ready
  state". `develop` reflete "the latest delivered development changes for the next release". [F1]
- Quando `develop` "reaches a stable point and is ready to be released", as mudanças vão para `master`
  e recebem tag com o número da versão. [F1]
- Cada merge em `master` é "a new production release by definition". [F1]
- Nota de 2020 do autor: "If your team is doing continuous delivery of software, I would suggest to
  adopt a much simpler workflow". Ainda serve "if you are building software that is explicitly
  versioned" ou "if you need to support multiple versions of your software in the wild". [F1]

### GitLab Flow

- "Whenever the 'main' branch is ready to be deployed, users merge it into the production branch and
  release." [F2]
- "Teams can add as many pre-production branches as needed." [F2]
- É "often used with release branches" para manter versões diferentes, como `v1` e `v2`. [F2]

### Trunk-based

- Branches de release são feitas "on a just in time basis" e não recebem desenvolvimento contínuo;
  correções vão primeiro ao tronco e seguem por cherry-pick. [F3]
- "CD teams do not do release branches." [F3]
- "Release from a tag on the trunk" é "a decent optimization for many teams, if possible", e "the
  branch can be avoided completely". [F3]

### Branch padrão

- "The default branch is the base branch for pull requests and code commits." [F4]
- Mudar exige acesso de administrador e mais de uma branch, e a interface mostra um aviso. [F4]
- Em marketplace de plugins, `#<ref>` permite usar uma branch como `stable`; o exemplo de canais
  aponta entradas para as refs `stable` e `latest`. [F5]

### Branch estável como padrão: relatos

- O GraphQL.js tornou padrão a branch estável 16.x, com o trabalho instável em `main`, para que
  usuários vejam o código estável primeiro. Há preocupação com correções que não voltam para a outra
  branch. [F7]
- O GitHub usa uma só configuração para a visão padrão e a base de pull requests; um comentário relata
  PRs abertos na branch errada. [F6]
- Mantenedor de biblioteca Kotlin queria README igual ao lançado; contribuidor reclamou de ter que
  trocar de branch. [F8]
- Em fórum, um relato favorece `develop` para quem consome por submódulo; outro acha que GitHub Flow
  com `main` protegida basta. [F9]

## O que as fontes não cobrem

- A combinação de Git Flow sem `release/*`, tag em `develop` e publicação antes do merge em `main` não
  apareceu em nenhuma fonte lida.
- Efeitos de mudar a branch padrão em clones, redirecionamentos e Actions: F4 não trata disso.
- Se é boa prática ter branch padrão diferente da de desenvolvimento: F4 não trata, e só há relatos de
  comunidade.

## Divergências entre fontes

- **Branch de release:** F1 e F2 usam ou admitem branches de release e de produção. F3 diz que times de
  entrega contínua não usam branch de release e apresenta a tag no tronco como alternativa.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D18
- ADR-0020 (fluxo de branches e release), previsto no Lote 0 da spec 005
