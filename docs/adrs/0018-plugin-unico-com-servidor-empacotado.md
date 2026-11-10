# ADR-0018: Plugin único com servidor via `uvx` — fonte única da conexão no Claude Desktop e no Claude Code

- **Status**: Accepted
- **Date**: 2026-11-08
- **Deciders**: Tech Leader + User (spec 005, decisão de D1 no Lote 1)
- **Related spec**: [`specs/005-desktop-distribution/`](../../specs/005-desktop-distribution/)
- **Code**: `plugin/.claude-plugin/plugin.json`, `plugin/hooks/`, `plugin/skills/configurar-carteira/`, `src/investidor10_wallet/installer/clients.py`
- **Research**: `specs/005-desktop-distribution/research.md` D1; `docs/learning-lessons/mcpb_uv_dentro_de_plugin_no_desktop.md`
- **Amends**: [ADR-0012](./0012-integracao-automatica-de-clientes.md) §2 e §6 (para o Claude); [ADR-0011](./0011-estrategia-de-distribuicao-e-release.md)

---

## Context

O ADR-0012 fez do plugin um pacote só de comportamento (nenhum manifesto
declarava `mcpServers`) e deixou o registro do servidor a cargo do assistente
de instalação (`claude mcp add`). Isso exige terminal e não alcança o Claude
Desktop, onde o público da spec 005 não tem terminal. A aposta inicial era um
servidor `.mcpb` do tipo `uv` dentro do plugin, que dispensaria Python e `uv`.
O spike do Lote 1 mediu o contrário: o Desktop usa o `uv` do próprio usuário
e não traz um embutido, e o Claude Code CLI 2.1.317 rejeita o tipo `uv`
(`Expected 'python' | 'node' | 'binary'`). O binário por plataforma foi
descartado por assinatura, notarização e Gatekeeper.

## Decision

1. **Um plugin só, fonte única da conexão** no Claude Desktop e no Claude
   Code: `plugin/.claude-plugin/plugin.json` declara o servidor `carteira`
   inline, com `command` `uvx` e `args` `--from mcp-investidor10-wallet==<versão> mcp-investidor10-wallet`.
   A versão fixada é sempre `__version__` e só muda no pedido de revisão de
   release. Os outros três manifestos (Codex, Devin, Gemini) continuam sem
   `mcpServers` e só mudam a `version`.
2. **O plugin não leva código.** O PyPI segue como único canal de código
   (ADR-0011): o plugin só aponta para a versão publicada e testada pelo
   `verify` do release. Não existem `plugin/servers/`, `.mcpb` nem
   `scripts/build_mcpb.py`.
3. **`uv` é pré-requisito do Claude Desktop**, instalado uma vez no terminal
   conforme `docs/INSTALACAO-DESKTOP.md`. O resto do fluxo é feito no app.
4. **Hook de início de sessão estático**: `hooks/session-start.json`
   (ASCII, escapes `\u`) lido por `cat`, com a persona e a regra de conduzir a
   configuração pendente pela skill `configurar-carteira`. Sai o script Bash,
   que não depende mais de interpretador no Windows.
5. **O subagente herda as tools da sessão**: a lista `tools` do guardião foi
   removida, porque o nome da tool muda por superfície (no Cowork:
   `mcp__remote-devices__plugin_…`).
6. **Claude Code pelo plugin**: `install` instala o plugin (marketplace
   fixado em `#v<versão>`) e não roda `claude mcp add`; `--mcp-only` é o
   escape e registra só o servidor. Com `investidor10-carteira@synced` o
   assistente não instala cópia local. Registro antigo `carteira`,
   marketplace da 0.3.x e cópia local viram **uma** pergunta (`[s/N]`); na
   recusa o plugin é instalado e o relatório avisa da duplicação.
7. **Teste de fumaça** do release deixa de exigir saída 1 sem carteira
   (já feito no Lote 4, ADR-0019).

## Alternatives considered

### Alternative A: `.mcpb` tipo `uv` dentro do plugin

**Why not chosen**:
- O Desktop não traz `uv`, então o tipo `uv` não elimina o pré-requisito.
- O Claude Code CLI rejeita o tipo `uv` e o servidor não sobe.

### Alternative B: binário por plataforma (PyInstaller ou similar)

**Why not chosen**:
- Exige Developer ID, notarização e lida com o Gatekeeper no macOS.
- Custo de build e manutenção em três sistemas desproporcional à 0.x.

### Alternative C: manter o plugin só de comportamento (ADR-0012)

**Why not chosen**:
- Não entrega o produto ao usuário do Desktop sem terminal para `mcp add`.

## Consequences

### Accepted

- Uma conexão só em cada cliente; o plugin vira a unidade de instalação.
- Nenhum artefato binário novo na cadeia de suprimentos.

### Trade-offs

- O usuário do Desktop abre o terminal uma vez para instalar o `uv`
  (FR-002 revista).
- O plugin só funciona depois que a versão fixada existir no índice; um
  release que mude `plugin/` sem a versão publicada quebra o servidor.
- Quem já tem o registro da 0.3.x precisa responder à pergunta de migração.

### Conditions that invalidate this decision

1. O Claude Desktop passar a embutir `uv` ou aceitar o tipo `uv` com `uv`
   próprio, medido em máquina sem `uv`.
2. O Claude Code passar a aceitar `.mcpb` tipo `uv`.
3. O Desktop deixar de ler `mcpServers` inline do `plugin.json`.

### Migration path when needed

1. Trocar o `command` para o executor novo mantendo a versão fixada.
2. Se o app embutir o runtime, remover o pré-requisito de
   `docs/INSTALACAO-DESKTOP.md`.
3. Em último caso, reabrir o ramo do binário assinado.

## References

- [ADR-0011](./0011-estrategia-de-distribuicao-e-release.md), [ADR-0012](./0012-integracao-automatica-de-clientes.md), [ADR-0019](./0019-configuracao-local-e-pagina-local.md), [ADR-0020](./0020-fluxo-de-branches-e-release.md)
- `specs/005-desktop-distribution/contracts/plugin-package.md`, `contracts/cli.md`
- Learning lesson: [mcpb_uv_dentro_de_plugin_no_desktop](../learning-lessons/mcpb_uv_dentro_de_plugin_no_desktop.md)
