# Teste que troca o `HOME` muda o Python do `uvx`: o `verify` do release só falhava no Ubuntu

**Context:** Descoberto no Lote 4 da spec 005, ao publicar as pré-versões `0.4.0rc1` e `0.4.0rc2`. Nas duas, `build` e `publish` passaram e o pacote chegou ao PyPI, mas o job `verify (ubuntu-latest)` do `.github/workflows/release.yml` falhou no último passo (servidor iniciado via `uvx` dentro do `scripts/smoke_mcp.py`). No macOS e no Windows o mesmo passo passou. A primeira correção (PR #21, tirar o `--offline`) atacou o sintoma e não resolveu; a causa só apareceu na `rc2`.
**Date:** 2026-11-07
**Future intent:** Todo teste que isola o processo filho (troca de `HOME`, proxy morto, variáveis removidas) precisa conferir que **as ferramentas que iniciam o filho** (`uv`, `uvx`, `npx`, `pipx`) continuam achando o que achavam antes. E, quando um erro de CI só aparece num sistema, comparar primeiro **qual interpretador** cada sistema está usando, antes de mexer em flags.

---

## O que aconteceu

O `verify` instala a versão publicada de dois jeitos e, nos dois, sobe o servidor com o `smoke_mcp.py` para conferir o `initialize` e as 20 tools:

```text
passo 4  uv venv --python 3.13          -> baixa o CPython 3.13 gerenciado
         pip install ==versão; smoke    -> verde nos três sistemas
passo 5  uvx --from ==versão python -c  -> verde (HOME real)
         smoke_mcp.py -- uvx --from ==versão mcp-investidor10-wallet
                                        -> vermelho só no Ubuntu
```

Os erros do passo 5 mudaram de uma tag para a outra, mas tinham a mesma origem:

| Tag | Comando do smoke | Erro no log |
|---|---|---|
| `v0.4.0rc1` | `uvx --offline ...` | `No solution found when resolving tool dependencies` (pydantic "needs to be downloaded") |
| `v0.4.0rc2` | `uvx ...` (sem `--offline`) | `Failed to fetch ... pyyaml-6.0.3-cp314-...whl.metadata` / `tunnel error ... Connection refused` |

O detalhe que entrega a causa é o **`cp314`** no nome da wheel: o servidor deveria rodar em Python 3.13.

---

## Mental Model: o smoke isola o filho, e o `uvx` é o filho

O `smoke_mcp.py` monta o ambiente do processo filho de propósito assim (`_child_env`):

- `HOME` (e `USERPROFILE`) apontam para um diretório temporário, para o servidor não ler nem gravar a memória e a configuração reais em `~/.investidor10/`;
- `HTTPS_PROXY` e `HTTP_PROXY` apontam para `http://127.0.0.1:1`, um proxy que não existe, para o servidor não alcançar a API real;
- `WALLET_ID`, `WALLET_HASH` e `WALLET_MEMORY_PATH` são removidas.

Isso foi pensado para o servidor. Mas quando o comando do smoke é `uvx ...`, **o filho direto é o `uvx`**, e ele herda o mesmo isolamento antes de iniciar o servidor:

```text
smoke_mcp.py
  └─ filho: uvx  (HOME=/tmp/smoke-home-xxx, HTTPS_PROXY=127.0.0.1:1)
       │
       ├─ 1. procura um Python 3.11+ para o ambiente da ferramenta
       │     · Pythons gerenciados pelo uv ficam em  $HOME/.local/share/uv/python
       │     · com o HOME trocado, esse diretório está VAZIO
       │     · então cai no Python do sistema do runner
       │
       ├─ 2. resolve as dependências para ESSE Python
       │     · Ubuntu: sistema = 3.14.4  ->  precisa de wheels cp314
       │     · o cache (UV_CACHE_DIR, variável fora do HOME) só tem as cp313
       │
       └─ 3. busca no PyPI o que falta
             · passa pelo proxy morto  ->  Connection refused  ->  smoke vermelho
```

Por que só o Ubuntu: o runner Ubuntu tem **3.14** como Python do sistema, e o 3.13 que o job usa é o gerenciado, baixado pelo `uv` no passo 4 (`Downloading cpython-3.13.18-linux-x86_64-gnu`). Os runners macOS e Windows já trazem um **3.13 no sistema**, e o `uv` o usa desde o passo 4 sem baixar nada (`Using CPython 3.13.17 interpreter at: /usr/local/bin/python3.13` e `C:\hostedtoolcache\windows\Python\3.13.17\x64\python.exe`). Lá não existe Python gerenciado para perder: com ou sem o `HOME` trocado, o `uvx` acha o mesmo 3.13 do sistema, e o cache serve.

| Sistema | Python do passo 4 | `uvx` com `HOME` real | `uvx` com `HOME` trocado | Resultado do smoke antigo |
|---|---|---|---|---|
| Ubuntu | 3.13.18 gerenciado (baixado no `HOME` real) | 3.13.18 | **3.14.4** (sistema) | vermelho (wheels cp314 fora do cache) |
| macOS | 3.13.17 do sistema | 3.13.17 | 3.13.17 | verde |
| Windows | 3.13.17 do sistema | 3.13.17 | 3.13.17 | verde |

As colunas do Ubuntu foram medidas no runner com os passos antigos. As do macOS e do Windows vêm do passo 4 e dos passos corrigidos; os passos antigos não foram rodados com diagnóstico nesses dois sistemas, mas passaram na `rc1` e na `rc2`.

### Por que a primeira correção não funcionou

Na `rc1` o smoke usava `uvx --offline`. Offline, o `uv` não pode baixar nada e só resolve com o que está no cache. Para Python 3.14 o cache não tinha o necessário, e o erro saiu como "No solution found". Tirar o `--offline` (PR #21) só fez o `uv` **tentar** baixar, e a tentativa morreu no proxy morto. A mensagem mudou, mas a causa (outro Python) continuou igual. O `--offline` nunca foi o problema: ele só deixou o sintoma com outra cara.

### Por que não reproduzia na máquina do mantenedor nem no primeiro contêiner

No macOS local e no contêiner `uv:python3.13-bookworm`, o Python do sistema também era 3.13, a mesma situação dos runners macOS e Windows. O defeito só aparece quando o **Python do sistema tem outra versão menor** que a do Python gerenciado que o job usa. Com o contêiner `uv:python3.14-bookworm` (sistema 3.14, como o runner Ubuntu), a falha reproduziu na primeira tentativa.

---

## A correção (PR #24)

Dois ajustes no job `verify` do `release.yml`. O isolamento do smoke não muda.

```yaml
- uses: astral-sh/setup-uv@... # v5
# smoke_mcp.py troca o HOME do filho; sem este diretório fixo o uvx do
# smoke não vê o Python gerenciado baixado abaixo e cai no Python do sistema.
- name: Share one uv Python install dir across the steps
  run: echo "UV_PYTHON_INSTALL_DIR=$RUNNER_TEMP/uv-python" >> "$GITHUB_ENV"
...
uvx --refresh --python 3.13 --from "mcp-investidor10-wallet==$version" python -c "import investidor10_wallet"
...
"$py" scripts/smoke_mcp.py --expected-tools 20 -- uvx --python 3.13 --from "mcp-investidor10-wallet==$version" mcp-investidor10-wallet
```

O que cada parte faz:

1. **`UV_PYTHON_INSTALL_DIR` fixo.** Diz ao `uv` onde ficam os Pythons gerenciados, em vez de deduzir do `HOME`. Gravada em `$GITHUB_ENV`, vale para todos os passos seguintes do job. O `smoke_mcp.py` copia o ambiente do pai para o filho (só troca `HOME`, proxies e as variáveis da carteira), então o `uvx` do smoke recebe a variável e acha o mesmo 3.13 que o passo 4 baixou. É o mesmo motivo pelo qual o cache já funcionava: o `setup-uv` define `UV_CACHE_DIR`, que também independe do `HOME`.
2. **`--python 3.13` nos dois `uvx`.** Pede a versão de forma explícita, em vez de aceitar "qualquer Python compatível". Sem isso, mesmo achando o diretório, o `uv` poderia preferir outro interpretador que encontrasse. Com isso, os dois `uvx` do passo 5 e o `uv venv` do passo 4 usam a mesma versão, e o cache serve para todos.

O que **não** foi feito, e por quê:

- **Liberar o PyPI no proxy (`NO_PROXY=pypi.org,...`).** Fazia o smoke passar, mas só porque o `uvx` baixaria as wheels do 3.14. O servidor continuaria sendo testado num Python diferente do pretendido, e o isolamento do smoke ganharia um furo para tratar um sintoma. Foi implementado e descartado.
- **Voltar o `--offline`.** Não muda nada: o problema é o interpretador, não a rede.

---

## Como a causa foi provada no runner real

Uma correção de `release.yml` só roda numa tag, e cada tag de teste custa uma versão no PyPI. Para não gastar a `rc3` às cegas, um workflow **temporário** (`verify-probe.yml`, `on: pull_request`) rodou os passos do `verify` contra a `0.4.0rc2` já publicada, dentro do próprio PR #24, e saiu do PR antes do merge:

- job `old-ubuntu`: os passos antigos, com o smoke **antes** do diagnóstico. Resultado (run 42387445884): Python do sistema `3.14.4`, `uvx` com `HOME` real `3.13.18`, smoke vermelho com `websockets-17.4-cp314 ... Connection refused`, e `uvx` com `HOME` trocado `3.14.4`;
- job `fixed`, matriz Ubuntu/macOS/Windows: os passos corrigidos, todos verdes, com o `uvx` em 3.13 mesmo com o `HOME` trocado.

Na primeira versão do probe, o diagnóstico com o `HOME` trocado rodou **antes** do smoke e **sem** o proxy morto. Ele baixou as wheels do 3.14, esquentou o cache, e o smoke antigo passou. Era um falso verde causado pelo próprio teste. Lição dentro da lição: um diagnóstico que acessa a rede pode alterar o cache que o teste seguinte usa.

Um teste de contrato guarda a regra: `tests/contract/test_release_workflow.py::test_verify_uvx_uses_the_same_python_as_the_rest_of_the_job` exige `UV_PYTHON_INSTALL_DIR` em `$GITHUB_ENV`, `--python 3.13` em todo `uvx --from` do `verify`, e nenhum `--offline`.

---

## Relação com ADRs e próximos passos

- **ADR-0011 / ADR-0020** (release por tag e `verify` depois da publicação): a regra continua; esta lição explica por que a `0.4.0rc1` e a `0.4.0rc2` estão no PyPI com o `verify` do Ubuntu vermelho sem defeito no pacote, e por que existe a `0.4.0rc3`.
- **Spec 005, research D18**, verificação (3): corrigida para a causa real.
- O mesmo cuidado vale para o servidor empacotado do Lote 5: o MCPB `server.type: "uv"` faz o app iniciar o servidor via `uv`. Se o app também trocar ou isolar o `HOME`, o Python escolhido pode mudar. Isso deve entrar no spike S1.
- Ao diagnosticar falha de CI que só aparece num sistema, imprimir a versão do interpretador em cada passo antes de mexer em flags da ferramenta.
