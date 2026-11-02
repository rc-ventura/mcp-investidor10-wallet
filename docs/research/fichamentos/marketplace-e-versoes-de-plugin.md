# Fichamento: marketplace, versões e canais de plugin

- **Pesquisado em**: 2026-11-01
- **Atualizado em**: 2026-11-01
- **Origem**: spec 005 (distribuição Desktop e fluxo de release)

## Por que esta pesquisa

O produto passou a ser entregue por um marketplace no próprio repositório. Era
preciso saber como o usuário encontra o plugin sem o diretório da Anthropic, o que
ele recebe do repositório, quando recebe atualizações e se dá para prendê-lo a uma
versão.

## Perguntas

1. Como um marketplace próprio é adicionado e hospedado?
2. Qual conteúdo o usuário recebe, e quando recebe atualizações?
3. Como fixar uma versão ou oferecer canais diferentes?
4. O que acontece ao adicionar ou remover um marketplace com o mesmo nome?

## Fontes

| ID | Fonte | Tipo | Consultada em |
|---|---|---|---|
| F1 | [Host and maintain a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace.md) | Oficial | 2026-11-01 |
| F2 | [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference.md) | Oficial | 2026-11-01 |
| F3 | [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish.md) | Oficial | 2026-11-01 |
| F4 | [Install and manage plugins](https://code.claude.com/docs/en/plugins/install) | Oficial | 2026-11-01 |
| F5 | [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference.md) | Oficial | 2026-11-01 |
| F6 | [Install plugins (Cowork)](https://claude.com/docs/cowork/guide/plugins.md) | Oficial | 2026-11-01 |
| F7 | [Plugins (overview)](https://claude.com/docs/plugins/overview.md) | Oficial | 2026-11-01 |
| F8 | [MCP, plugins, skills, and hooks (Desktop 3P)](https://claude.com/docs/third-party/claude-desktop/extensions) | Oficial | 2026-11-01 |
| F9 | [Build a desktop extension with MCPB](https://claude.com/docs/connectors/building/mcpb) | Oficial | 2026-11-01 |
| F10 | [Issue #61271: Add marketplace com plugin em repositório privado](https://github.com/anthropics/claude-code/issues/61271) | Comunidade | 2026-11-01 |

As afirmações de F10 vieram de trechos do resultado da busca; as páginas não foram abertas, e a atribuição a cada uma delas é aproximada.

## Achados

### Publicar e adicionar

- "Your own marketplace is a `.claude-plugin/marketplace.json` file that lists your
  plugin, added to a git repository. Once the file is in the repository, the plugin
  is published, with no submission form." [F3]
- No Cowork, **Add marketplace** aceita `https://github.com/owner/repo` e
  `owner/repo`. [F6]
- A fonte de plugin por caminho relativo resolve a partir da raiz do marketplace.
  [F2]
- O diretório da Anthropic não aceita mais MCPB: para listar um servidor local lá,
  "include it in a plugin". [F9]
- Submeter ao diretório "requires a paid claude.ai plan". [F3]

### Versões e atualizações

- "Users get a new copy only when the plugin's computed version differs from the
  one they have." A versão vem primeiro do `plugin.json`, depois da entrada do
  marketplace. [F1]
- "If you set `\"version\": \"1.0.0\"` and push new commits without changing it,
  users don't receive them." Omitir a versão faz o usuário seguir os commits. [F1]
- "Setting it keeps users on that version until you change it." [F5]
- No Claude Code, a atualização automática vem desligada para marketplace de
  terceiros. Sem ela, o usuário roda `/plugin marketplace update <name>` ou `claude
  plugin update`. [F1]
- Não declarar `version` nos dois lugares: `plugin.json` vence, sem aviso em tempo de
  execução. [F1]
- No Cowork, **Check for updates** puxa "the latest plugins from its repository", ou
  o usuário liga **Sync automatically**. [F6]
- Depois que uma versão nova sincroniza da fonte, "you get it on your account
  automatically, with nothing to accept". [F7]
- Se o usuário editou arquivos do plugin, o Cowork avisa antes de sobrescrever. [F6]

### Fixar versão e canais

- "One marketplace serves one version of each plugin at a time." [F1]
- `#<ref>` no comando prende o catálogo a uma branch ou tag: `your-org/your-marketplace#stable`.
  [F1]
- A entrada do plugin aceita `ref` e `sha` em fontes `github`, `url` e `git-subdir`.
  `ref` usa como padrão "the repository's default branch". [F1] [F2]
- "Claude Code has no release-channel concept"; a orientação é hospedar dois
  marketplaces, com nomes diferentes, cujas entradas apontam para refs diferentes.
  [F1]
- "Give the two refs different `plugin.json` versions, or omit `version`." [F1]

### Nomes e remoção

- "A user can't have two marketplaces with the same name registered at once." O nome
  vem do campo `name` de `marketplace.json`. [F2]
- "When you remove a marketplace, Claude Code uninstalls every plugin you installed
  from it." [F4]
- Nunca renomear um plugin publicado; o mapa `renames` existe para migrar. [F1] [F3]

### Marketplaces no Desktop 3P

- "When Claude Desktop syncs the marketplace, it doesn't fetch or auto-install a
  plugin whose `source` points at a different repository", e submódulos não são
  buscados. A orientação é colocar o conteúdo no repositório do marketplace com
  caminho relativo. [F8]
- `repo` ou `url` mais `path` identificam o marketplace: mudar um deles conta como
  remover e adicionar. "Changing `ref` is an update, not a move." [F8]

### Relato de comunidade

- Um relato registra falha genérica de sincronização no Cowork quando um marketplace
  público referencia plugin em repositório privado. A issue está fechada. [F10]

## O que as fontes não cobrem

- Se **Add marketplace** do Cowork aceita `owner/repo#ref`: F6 e F7 citam só a URL e a
  forma `owner/repo`.
- Qual branch o Cowork lê por padrão: F2 fala do Claude Code, e F6 diz apenas "its
  repository".
- Se o Cowork respeita o campo `version` como o Claude Code: F1 trata só do Claude
  Code.
- Se o marketplace pessoal do Desktop aceita fontes `github` ou `git-subdir` com `ref`:
  F8 trata de marketplaces de organização no Desktop 3P.

## Divergências entre fontes

- **Regra de fonte do plugin:** F2 documenta fontes em outro repositório para o Claude
  Code. F8 diz que o Desktop não busca plugin cuja fonte está em outro repositório, no
  contexto de marketplaces de organização no 3P.

## Usado em

- [Research da spec 005](../../../specs/005-desktop-distribution/research.md), D11 e D18
- [Contrato do plugin](../../../specs/005-desktop-distribution/contracts/plugin-package.md)
