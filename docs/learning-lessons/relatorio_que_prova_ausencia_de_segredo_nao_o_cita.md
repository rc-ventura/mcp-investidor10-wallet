# Um relatório que prova a ausência de um segredo não pode citá-lo

**Context:** No ciclo 5 da revisão da spec 004, o relatório verificou "o ID real da carteira não está mais em arquivo versionado" e escreveu, na própria linha de verificação, o comando com o ID literal (`git grep "<o ID>"` ... 0 hits). A frase fez o ID voltar para um arquivo versionado, depois da reescrita do histórico de 29/10/2026. Os ciclos 5 e 6 não notaram (a busca do ciclo 6 procurava números perto das palavras "wallet" ou "carteira", e a linha não tinha nenhuma); o ciclo 7 achou. Como o `pyproject.toml` não limitava o sdist, a tag `v0.3.0` teria publicado esse relatório no PyPI.
**Date:** 2026-10-31
**Future intent:** Quem verifica a ausência de um segredo prova com um comando que lê o valor do ambiente, nunca o escreve, e deixa uma trava mecânica para o valor não voltar.

---

## Mental Model

Verificar "o segredo não está aqui" tem duas partes, e a segunda é fácil de esquecer:

1. **A busca** precisa do valor. Ela pode ler o valor de uma variável de ambiente (`git grep -F -- "$WALLET_ID"`) e imprimir só nomes de arquivo.
2. **O registro da busca** é texto que vai para o repositório. Se ele contém o valor, o registro vira o vazamento que ele diz ter eliminado.

A regra: **o texto que prova a ausência usa um placeholder (`<id>`) ou o nome da variável, nunca o valor.** E a prova de que o valor não voltou tem que ser uma checagem automática, não uma leitura humana: uma revisão confere os exemplos que conhece, e o ciclo 5 mostrou que o vazamento estava num lugar que nenhuma revisão olhou.

Duas armadilhas ligadas a esta:

- **Busca por vizinhança não é busca por valor.** Procurar dígitos perto de "wallet" deixa passar o valor numa frase sem a palavra.
- **O que o empacotador inclui não é o que o `.gitignore` ignora.** O Hatchling usa só o `.gitignore`; um arquivo local excluído por `.git/info/exclude` (como a config local do Devin) entra no sdist de um build local. O sdist precisa de uma lista explícita do que entra.

---

## Como ficou no código

- `scripts/check-no-wallet-id` lê `WALLET_ID` do ambiente e falha se `git grep -F` achar o valor em arquivo versionado. Imprime só os nomes dos arquivos, nunca o valor, e se a variável não existe avisa e sai com sucesso (forks e outras máquinas não quebram). Roda como hook local do pre-commit.
- `[tool.hatch.build.targets.sdist]` inclui só `/src` e `/CHANGELOG.md` (mais `pyproject.toml`, `README.md` e `LICENSE`, que o Hatchling sempre leva). `test_sdist_ships_only_the_source_and_the_changelog` fixa a lista.
- Testes em `tests/unit/test_check_no_wallet_id.py` cobrem: passa limpo, falha e nomeia o arquivo sem imprimir o valor, só arquivos versionados contam, variável ausente vira aviso, e o próprio script não carrega um ID.

---

## Relation to ADRs and next steps

- **ADR-0004**, emenda de 31/10/2026 (ciclo 7): o ID reapareceu num relatório e foi trocado por `<id>`; a decisão sobre reescrever o histórico fica com o mantenedor.
- O guarda no CI exigiria guardar o ID como secret do repositório; não foi ligado. O hook do pre-commit cobre quem usa `pre-commit`.
- Ao registrar uma verificação de segredo em relatório, escreva `<id>` e o nome da variável.
