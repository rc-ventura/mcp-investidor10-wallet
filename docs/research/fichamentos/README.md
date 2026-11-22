# Fichamentos de pesquisa

Registro do que as fontes dizem, agrupado por tema: por que a pesquisa foi
feita, o que se encontrou e o que ficou sem resposta.

## Fichamento, learning lesson e ADR

| Documento | Responde a | Contém |
|---|---|---|
| **Fichamento** (aqui) | O que as fontes dizem? | Fatos e citações, sem reflexão nem recomendação |
| **Learning lesson** (`docs/learning-lessons/`) | O que aprendemos fazendo? | Fato verificado no projeto e o que muda daqui em diante |
| **ADR** (`docs/adrs/`) | O que decidimos e por quê? | A decisão, as alternativas e as consequências |

As pesquisas de plataforma mais antigas seguem em `docs/research/`.

## Como criar

Rode `/research <tema, pergunta ou afirmação a testar> [-- motivo]`. A skill é de
usuário (`~/.claude/skills/research/`): monta um brief a partir da conversa, cruza
com o que o projeto já registrou, consulta as fontes e cria ou atualiza os arquivos
desta pasta. Os fichamentos abaixo foram escritos antes do modelo atual e recebem as
seções novas quando forem atualizados.

## Limites

- As citações vieram de ferramentas que extraem o trecho da página. Antes de
  basear uma decisão crítica nelas, confira a página original.
- Documentação muda. A data de consulta está em cada fonte.
- Nunca escreva aqui o ID ou a credencial de uma carteira real.

## Índice

| Fichamento | Tema | Atualizado em |
|---|---|---|
| [claude-desktop-superficies](claude-desktop-superficies.md) | Claude unificado, Chat, Cowork, aba Code e diferença entre desktop e web | 2026-11-01 |
| [plugins-claude-componentes-e-instalacao](plugins-claude-componentes-e-instalacao.md) | O que cada superfície carrega de um plugin, instalação, sincronização e hooks | 2026-11-01 |
| [marketplace-e-versoes-de-plugin](marketplace-e-versoes-de-plugin.md) | Hospedagem de marketplace, versões, atualizações, refs e canais | 2026-11-01 |
| [mcpb-e-runtime-do-servidor-local](mcpb-e-runtime-do-servidor-local.md) | Formato MCPB, tipos de servidor, runtime e PATH em apps gráficos | 2026-11-01 |
| [entrada-de-dados-do-usuario-em-mcp](entrada-de-dados-do-usuario-em-mcp.md) | `userConfig`, elicitation, MCP Apps e anotações de tool | 2026-11-01 |
| [devin-desktop](devin-desktop.md) | Devin Desktop: origem, configuração de MCP e recursos | 2026-11-01 |
| [modelos-de-branching](modelos-de-branching.md) | Git Flow, GitLab Flow, trunk-based e branch padrão | 2026-11-01 |
| [publicacao-de-pacotes-e-promocao-de-artefatos](publicacao-de-pacotes-e-promocao-de-artefatos.md) | Pipeline de publicação, pré-lançamentos e ordem entre pacote e ponteiro | 2026-11-01 |
| [skills-e-subagentes-do-claude-code](skills-e-subagentes-do-claude-code.md) | Formato de skills e subagentes de projeto | 2026-11-01 |
| [distribuicao-de-servidores-mcp-em-plugins-e-extensoes](distribuicao-de-servidores-mcp-em-plugins-e-extensoes.md) | Como Anthropic e terceiros empacotam servidores MCP locais, plugins e extensões | 2026-11-06 |
