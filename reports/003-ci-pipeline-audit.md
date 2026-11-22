# Auditoria do pipeline CI — GitHub Actions

Data: 2026-11-07. Executor: auditoria sob demanda do mantenedor.
Escopo: `.github/workflows/ci.yml`, `.github/workflows/main-gate.yml`,
`.github/workflows/release.yml` e os scripts que eles invocam
(`scripts/check_promotion.py`, `scripts/check_release_tag.py`,
`scripts/smoke_mcp.py`, `scripts/check-no-wallet-id`).
Critério: documentação oficial de security hardening do GitHub Actions
(`docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions`),
avaliando eficiência, simplicidade e segurança.

## Veredito

Acima da média de mercado em segurança; gaps pontuais em hardening do gate,
manutenção de dependências e eficiência. O desenho é deliberado e consistente
com ADR-0020 (main só contém versões publicadas) e ADR-0011 (PyPI via OIDC
trusted publishing, sem segredo de longa duração).

## O que já está alinhado com a doc oficial

| Prática da doc | Status |
|---|---|
| Pin de actions por SHA completo | ✅ todos os `uses:` pinados, com comentário de versão |
| Least privilege do `GITHUB_TOKEN` | ✅ `contents: read` no topo; `id-token: write` só no job `publish` |
| OIDC em vez de secret de longa duração | ✅ trusted publishing PyPI, zero secrets no pipeline |
| Variável intermediária para contexto não confiável | ✅ `HEAD_REF`/`HEAD_SHA`/`TAG` via `env:` — sem script injection |
| Não usar `pull_request_target` com checkout de código não confiável | ✅ usa `pull_request` puro |
| `if-no-files-found: error` em artifact | ✅ |
| Dependências travadas | ✅ `uv sync --locked`, `uv export --frozen`, `pip-audit@2.10.1` pinado |
| Gate fail-closed | ✅ `check_promotion.py` falha se o índice de pacotes não responde |
| `defaults.run.shell: bash` cross-platform | ✅ no job `verify` do `release.yml` |
| Verificação pós-publicação | ✅ instalação real do índice em Linux, macOS e Windows, via pip e uvx |

## Findings — Segurança

### S1 (médio) — `main-gate` executa o script do gate a partir da árvore não confiável do PR

Em evento `pull_request`, `actions/checkout` faz checkout do merge commit
(base + head). O próprio PR `promote/vX.Y.Z` pode modificar
`scripts/check_promotion.py`, e o gate rodaria a versão adulterada —
auto-anulação do controle. Com `permissions: contents: read` o blast radius é
limitado, mas o gate deixa de garantir o que promete.

Correção proposta: executar o script a partir da ref base (os objetos git —
tags e head do PR — já estão no clone com `fetch-depth: 0`):

```yaml
      - name: Only a published final version may reach main
        env:
          HEAD_REF: ${{ github.head_ref }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          git show "origin/${GITHUB_BASE_REF}:scripts/check_promotion.py" > /tmp/gate.py
          python3 /tmp/gate.py --head-ref "$HEAD_REF" --head-sha "$HEAD_SHA"
```

### S2 (médio, fora dos arquivos) — o caminho tag→PyPI depende inteiro de settings do repo

Qualquer identidade com write access que faça `git push --tags v9.9.9` dispara
o `release.yml` e o OIDC do environment `pypi` emite token para publicar. A
doc recomenda "requiring review for access to secrets". Verificar e
documentar (ADR-0020 ou `SECURITY.md`):

1. environment `pypi` com required reviewers ou deployment branches
   restritos a tags `v*`;
2. ruleset restringindo a criação de tags `v*`;
3. trusted publisher no PyPI escopado a repo + workflow + environment.

### S3 (baixo) — scan de wallet ID é só local

`scripts/check-no-wallet-id` roda via pre-commit, mas commit com
`--no-verify` ou feito pela web UI pula o check — e o vazamento iria para o
índice público. O script aceita `WALLET_ID`/`WALLET_HASH` por env: dá para
adicionar um job no CI com `secrets.WALLET_ID`/`secrets.WALLET_HASH`. O
`GITHUB_TOKEN` read-only não expõe nada.

### S4 (baixo) — `persist-credentials: false` ausente

O `actions/checkout` persiste o `GITHUB_TOKEN` em `.git/config` por padrão;
nenhum dos jobs precisa de auth git após o clone. Hardening barato e
recomendado pelo próprio README do checkout.

### S5 (higiene) — sem Dependabot nem CODEOWNERS

A doc recomenda ambos. Falta `.github/dependabot.yml` para os ecossistemas
`github-actions` (os SHAs pinados envelhecem e nunca recebem update) e `uv`/
`pip` (deps hard-pinadas em `pyproject.toml`/`uv.lock`). Já existe item
próprio no ROADMAP (Fase 1, "Dependabot para actions e dependências").
CODEOWNERS cobrindo `.github/workflows` faz mudança em workflow exigir
review — relevante se o repo ganhar colaboradores.

## Findings — Eficiência

### E1 (maior ganho) — sem cache do uv

9 jobs de matrix baixam as dependências toda vez. `astral-sh/setup-uv`
suporta nativamente:

```yaml
        with:
          python-version: ${{ matrix.python }}
          enable-cache: true
          cache-dependency-glob: uv.lock
```

### E2 — sem `concurrency`

Pushes em sequência rodam a matrix de 9 jobs em paralelo até o fim. Para
`ci.yml`:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

### E3 — sem `timeout-minutes`

O default é 6h; um `pip-audit` ou install travado consome isso de minutos.
Sugerido: 15 (test), 10 (audit e main-gate), 25 (verify — os loops de retry
chegam a ~10 min no pior caso).

### E4 — `retention-days: 1` no artifact `dist`

O artifact só precisa viver até o job `publish`, minutos depois do upload;
hoje segue a retenção default do repo (90 dias).

### E5 — `fail-fast: false` (consciente)

Escolha legítima: ver as falhas de todos os OS/Python de uma vez. Custa
minutos quando a falha é determinística, mas é trade-off deliberado. Sem ação.

## Simplicidade

Muito boa: 3 arquivos pequenos, single-responsibility, e a lógica de domínio
vive em scripts Python testáveis fora do runner — o que é o padrão
recomendado. Único ponto: o par `checkout + setup-uv` se repete 5×; um
composite action reduziria a duplicação, mas adiciona indireção — recomendo
manter como está.

## Priorização sugerida

| Ordem | Item | Esforço | Ganho |
|---|---|---|---|
| 1 | S1 — gate a partir da ref base | ~4 linhas | fecha a auto-anulação do gate |
| 2 | S2 — verificar environment/tag/ruleset | settings do repo | protege o único caminho com privilégio real |
| 3 | E1+E2+E3+E4 — cache, concurrency, timeouts, retenção | ~15 linhas | eficiência em todos os runs |
| 4 | S3 — scan de wallet ID no CI | job novo (~10 linhas) + 2 secrets | fecha bypass do pre-commit |
| 5 | S4 — `persist-credentials: false` | 5 linhas | higiene barata |
| 6 | S5 — Dependabot | já no ROADMAP | manutenção dos pins |

Itens 1, 3, 4, 5 somam ~30 linhas de mudança nos workflows.

## Referências

- GitHub Docs — Security hardening for GitHub Actions:
  `https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions`
- GitHub Docs — OpenID Connect / trusted publishing:
  `https://docs.github.com/en/actions/concepts/security/openid-connect`
- ADR-0011 — estratégia de distribuição e release (PyPI via `uvx`, OIDC)
- ADR-0020 — fluxo de branches e release (main só contém versões publicadas)
