# Quickstart: validação end-to-end (spec 003)

Cenários que provam a feature funcionando de ponta a ponta. Pré-requisito de
todos: branch `003-client-integration`, `uv sync` rodado, suíte `uv run
pytest` verde.

## V1 — Publicação (FR-001)

1. Criar o projeto `mcp-investidor10-wallet` no PyPI; configurar trusted
   publishing: owner `rc-ventura`, repo `mcp-investidor10-wallet`, workflow
   `release.yml`, environment `pypi`.
2. No GitHub: Settings → Environments → criar `pypi` (com required reviewer).
3. `git tag v0.1.0 && git push origin v0.1.0`; acompanhar o workflow verde.
4. **Esperado**: `uvx mcp-investidor10-wallet` (fora do repo) baixa do PyPI e
   aborta com a mensagem PT-BR de `WALLET_ID` ausente.

(Concluído em 2026-10-24 — release 0.1.0 publicada com proveniência OIDC.)

## V2 — Assistente detecta e registra nos 4 CLIs (US1, FR-002…005)

1. `uv run mcp-investidor10-wallet install --dry-run`
   → relatório SIMULAÇÃO lista os clientes presentes na máquina; nenhum
   registro executado.
2. `uv run mcp-investidor10-wallet install`
   → pergunta o ID; valida; registra em cada CLI presente; relatório final
   pede reinício dos clientes.
3. Executar o mesmo comando de novo → todos os status são "já registrado"
   (ou o protocolo de colisão pergunta pular/atualizar); nenhuma entrada
   duplicada (SC-003).
4. **Esperado**: `claude mcp list`, `devin mcp list`, `codex mcp list` e
   `gemini mcp list` mostram `carteira`; cada cliente reiniciado expõe as 19
   tools.

## V3 — Plugin nos dois clientes (US2, FR-006…009)

1. Claude Code: `claude plugin marketplace add
   rc-ventura/mcp-investidor10-wallet` seguido de `/plugin install
   investidor10-carteira` (canal canônico via `marketplace.json` do repo);
   durante o desenvolvimento, instalar do diretório local.
2. Devin CLI: `devin plugins install <repo-ou-pasta>` com o mesmo conteúdo.
3. **Esperado em ambos**: os 3 prompts aparecem como comandos; o subagente
   guardião lista-se e executa read-only; o hook `Stop` emite o lembrete de
   registro apenas propondo (nunca gravando) quando aplicável; o servidor
   `carteira` do plugin resolve `${WALLET_ID}` quando a variável existe no
   ambiente e falha visivelmente quando não existe.

## V4 — Degradações (edge cases)

- Sem nenhum cliente: assistente de instalação sai 1 com orientação PT-BR.
- ID inválido/privada: sai 3 antes de qualquer registro; nenhuma configuração
  alterada.
- Cliente já tem `carteira` de outra origem: pergunta interativa sempre
  exibida — pular (default, `skipped_present`) ou atualizar (`updated`) —
  mesmo com `--yes` (protocolo de colisão do contract install-cli.md).
- Runner `uv` ausente: sai 2 com instrução PT-BR de instalação.