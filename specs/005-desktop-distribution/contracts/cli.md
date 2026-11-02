# Contract — linha de comando (`install`, `configure`, `doctor`)

Emenda `specs/003-client-integration/contracts/install-cli.md`. Mensagens
ao operador em PT-BR (ADR-0009).

## `mcp-investidor10-wallet install`

Flags novas, mantendo as atuais (`--clients`, `--wallet-id`, `--mcp-only`,
`--dry-run`, `--yes`):

| Flag | Efeito |
|---|---|
| `--link URL` | link da carteira (pública ou restrita); sem ela e sem `--wallet-id`, o assistente pergunta |
| `--mask` / `--no-mask` | resposta não interativa da pergunta do mascaramento |

Fluxo:

1. Confere o runner (`uv`), como hoje.
2. Lê o link (flag, `--wallet-id` como forma antiga, ou pergunta),
   interpreta e valida contra a fonte (data-model.md §3 e §4). Fonte fora do
   ar: pergunta se salva mesmo assim (`[s/N]`); `--yes` não responde essa
   pergunta.
3. Modo público: avisa que a carteira é indexável e recomenda a restrita.
4. Pergunta o mascaramento (o que se preserva, o que se perde).
5. Grava a configuração local e mostra o resumo (modo, mascaramento).
6. Por cliente detectado:
   - **Claude Code**: se `claude plugin list` mostra
     `investidor10-carteira@synced`, não instala localmente e diz por quê;
     senão, `claude plugin marketplace add rc-ventura/mcp-investidor10-wallet#v<versão>`
     e `claude plugin install investidor10-carteira@investidor10`. Se
     existir o registro antigo `carteira` em escopo de usuário, pergunta se
     remove (`claude mcp remove carteira -s user`), porque o plugin já traz
     o servidor. Na recusa, instala o plugin e o relatório avisa da duplicação,
     que o `doctor` também aponta. **Migração da 0.3.x**: com o marketplace
     `investidor10` já adicionado, a mesma pergunta cobre remover e readicionar
     na versão certa e reinstalar o plugin; com `@synced` e cópia local, oferece
     desinstalar a cópia local.
   - **Devin, Codex, Gemini**: registra o servidor sem variável da carteira
     (o servidor lê a configuração local) e instala o plugin, pinado na
     versão quando o comando do cliente aceitar referência.
7. Relatório: uma linha por cliente pedido, pareada com o resultado,
   inclusive cliente citado e ausente.

`--mcp-only` é o escape para quem quer só o servidor, em todos os clientes:
registra o servidor sem variável da carteira e não instala o plugin. No Claude
Code usa `claude mcp add`; se já houver o plugin, o relatório avisa da
duplicação.

## `mcp-investidor10-wallet configure`

Refaz os passos 2 a 5 do `install` e para. Não registra, não instala, não
remove nada. Aceita `--link`, `--mask`/`--no-mask`, `--yes`. Trocar para
outra carteira pede confirmação (`[s/N]`), com o aviso sobre a memória.
Execução repetida com as mesmas respostas não muda o arquivo (idempotente).

Códigos de saída: 0 configurado ou inalterado; 2 entrada inválida; 3 acesso
recusado ou carteira inexistente; 4 fonte indisponível sem confirmação.

## `mcp-investidor10-wallet doctor`

Sem flags obrigatórias. Imprime as checagens de data-model.md §8, uma por
linha (`ok`, `aviso`, `falha`), com causa e ação, e termina com um bloco
pronto para colar numa issue. Nunca imprime ID, credencial, valores,
conteúdo da memória nem caminhos com o nome do usuário (home vira `~`).

Códigos de saída: 0 sem falhas; 1 com alguma falha.

## Flags e compatibilidade

- `--wallet-id` continua aceita nesta versão (FR-017) e equivale a um link
  público.
- O servidor sem subcomando continua sendo o servidor MCP (stdio).
