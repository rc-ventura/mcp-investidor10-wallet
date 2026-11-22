# Checklist: publicar o bundle nos registries de servidores MCP

**Criado em**: 2026-11-10. **Escopo**: o registry oficial do MCP, o PulseMCP e o Smithery. **Nada
foi publicado**: este documento só prepara. A publicação é permanente no registry oficial e é
passo do mantenedor.

**Fontes**: `docs/research/fichamentos/diretorios-de-plugins-e-registries-requisitos.md` (F13, F8,
F14) e `specs/005-desktop-distribution/directory-preflight.md`. O esquema do `server.json` foi baixado
de `static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json` em 2026-11-10.

## Situação de cada destino

| Destino | Situação em 2026-11-10 | O que fazer |
|---|---|---|
| **Registry oficial do MCP** (`registry.modelcontextprotocol.io`) | Aberto, em preview. Só confere nome e pacote. **Permanente**: não apaga nem despublica; versão imutável | Seguir as seções 1 a 6 |
| **PulseMCP** | Envios e alterações **pausados**, sem data. A página oficial diz que coletará do registry oficial quando reabrir | Nenhuma ação própria; depende da seção 6 |
| **Smithery** | **Sem caminho de publicação**: em 2026-10-31 encerrou contas, chaves de API, CLI e SDKs; segue só como registry público curado, "now part of Arcade". As páginas de documentação respondem 404 | Seção 7: acompanhar, não publicar |

O diretório de plugins da **Anthropic** é outro assunto e está bloqueado pela leitura da política
(`directory-preflight.md`); este checklist não o cobre.

## 0. Decisões do mantenedor, antes de qualquer passo

- [ ] **ADR sobre os termos de uso do Investidor10 e a API não documentada** (ADR-0005, critério 3 da
      FR-030). O registry não cobra isso, mas a publicação é permanente e o risco continua nosso.
- [ ] **Nome do servidor e marca.** O nome precisa começar com `io.github.rc-ventura/` (login pelo
      GitHub) e casa com `^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$`. Uma sugestão é
      `io.github.rc-ventura/investidor10-wallet`, mas ele usa a marca do Investidor10, que não é nossa
      (mesma questão da A8 do preflight). Decidir se mantém e se acrescenta o aviso "não afiliado".
- [ ] **Aceitar a permanência.** Sem apagar nem despublicar; só se publica uma versão nova. Publicar
      **apenas a versão final `0.4.0` ou posterior**, nunca uma `rcN`.
- [ ] **Texto público** do `server.json` revisado (título e descrição), sem prometer recomendação de
      investimento e dizendo que é somente leitura (regras 1B e 2B da política da Anthropic valem como
      boa prática mesmo fora dela).

## 1. Pré-requisitos do pacote

- [ ] A versão **final** está publicada no PyPI e o `verify` do release passou nos três sistemas.
- [ ] A `0.4.0` foi **promovida para `main`** (ADR-0020). Hoje o `main` ainda carrega `0.3.0` e o plugin
      antigo `0.1.1`; o `server.json` e a divulgação devem apontar para o que o usuário de fato recebe.
- [ ] O repositório do GitHub é público e tem **descrição e tópicos** (hoje não tem nenhum).
- [ ] O `README.md` do pacote ganha o marcador de posse, que muda o **pacote publicado** e portanto só
      entra numa versão nova:

      ```markdown
      <!-- mcp-name: io.github.rc-ventura/investidor10-wallet -->
      ```

      O nome no marcador precisa ser **idêntico** ao `name` do `server.json`. O PyPI preserva comentário
      HTML no README.
- [ ] O marcador chegou ao PyPI: abrir a página do pacote e conferir a descrição renderizada.
- [ ] O `README.md` continua passando em `tests/contract/test_readme_desktop.py` e na guarda de ID e
      credencial (`scripts/check-no-wallet-id`).

## 2. O `server.json`

Campos obrigatórios do esquema: `name`, `description`, `version`. Em cada pacote: `registryType`,
`identifier`, `transport`. A `description` tem **no máximo 100 caracteres**, e o `title`, também. Versão
não aceita faixa (`^1.2.3`, `>=1.2.3`).

Rascunho para revisão (não está no repositório):

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.rc-ventura/investidor10-wallet",
  "title": "Carteira Investidor10",
  "description": "Leitura da carteira do Investidor10 com memória do investidor e alertas de preço",
  "repository": {
    "url": "https://github.com/rc-ventura/mcp-investidor10-wallet",
    "source": "github"
  },
  "version": "<versão final>",
  "websiteUrl": "https://github.com/rc-ventura/mcp-investidor10-wallet",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "mcp-investidor10-wallet",
      "version": "<versão final>",
      "runtimeHint": "uvx",
      "transport": { "type": "stdio" }
    }
  ]
}
```

A descrição acima tem 80 caracteres.

- [ ] `name` idêntico ao marcador do README (seção 1).
- [ ] `version` do `server.json` igual à do pacote no PyPI, sem faixa.
- [ ] `identifier` é o nome do pacote no PyPI (`mcp-investidor10-wallet`).
- [ ] `transport.type` é `stdio`.
- [ ] Sem `environmentVariables` obrigatórias: o servidor lê a carteira de `~/.investidor10/config.json` e
      sobe sem `WALLET_ID`. Se for listar variáveis opcionais, nenhuma pode conter valor real.
- [ ] O arquivo **não contém** ID da carteira, credencial `?h=` nem caminho de usuário.
- [ ] `runtimeHint` `uvx` conferido contra o esquema: ele aparece como exemplo no campo (`npx`, `uvx`,
      `docker`, `dnx`).

## 3. Ferramenta e autenticação (mantenedor)

- [ ] Instalar `mcp-publisher` (binário pré-compilado ou Homebrew), conforme o quickstart oficial.
- [ ] Comandos da fonte oficial: `init`, `login`, `logout`, `publish`. (O subcomando `validate`
      aparece só em guias de terceiros; conferir com `mcp-publisher --help` antes de contar com ele.)
- [ ] `mcp-publisher login github` com a conta dona do repositório, `rc-ventura`. O nome do servidor
      **precisa** começar com `io.github.rc-ventura/`, senão a publicação é recusada ("You do not have
      permission to publish this server").

## 4. Publicar (mantenedor, irreversível)

- [ ] Todas as seções 0 a 3 marcadas.
- [ ] Revisar o `server.json` uma última vez, linha por linha: **não dá para apagar nem despublicar**.
- [ ] `mcp-publisher publish`.
- [ ] Guardar a saída (nome e versão publicados) no `specs/005-desktop-distribution/validation-matrix.md`.

## 5. Conferir

- [ ] A consulta à API do registry devolve o servidor:

      ```bash
      curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.rc-ventura/investidor10-wallet"
      ```

- [ ] Nome, descrição e versão aparecem como no `server.json`.
- [ ] Erros conhecidos da fonte oficial: "Registry validation failed for package" (marcador ausente ou
      diferente do `name`), "Invalid or expired Registry JWT token" (refazer o login) e "You do not have
      permission to publish this server" (namespace diferente da conta do GitHub).

## 6. PulseMCP

- [ ] Nenhuma submissão própria: a página oficial diz que coleta do registry oficial **quando reabrir**.
- [ ] Depois da seção 5, abrir `pulsemcp.com/submit` de tempos em tempos e anotar a data em que reabrir.
- [ ] Se reabrir e pedir dados, preencher **uma vez**, com o mesmo texto do `server.json`.

## 7. Smithery

- [ ] **Não publicar:** não há conta, CLI nem SDK, e a documentação de publicação não existe mais.
- [ ] Anotar como gatilho de reabertura: a página `smithery.ai/future` (ou outra oficial) passar a dizer
      como indicar um servidor à curadoria.
- [ ] Se isso acontecer, reabrir este item. O Smithery curado mostra a **URL MCP direta** do fornecedor,
      e o nosso servidor é local por `stdio`, sem URL; então um modo remoto não está nos planos
      (ADR-0004) e a inclusão pode simplesmente não se aplicar.

## 8. Depois de publicado: cada versão nova

- [ ] Nova versão do pacote exige **novo `server.json`** com versão única; a anterior fica imutável.
- [ ] Acrescentar ao fluxo de release (spec 005, Lote 7) um passo opcional que confira
      `server.json` = `__version__` e o marcador no README. A documentação oficial tem uma página de
      automação por GitHub Actions; avaliar antes de adotar.
- [ ] Mudanças materiais de endpoint ou de prática de dados: lembrar que a política da Anthropic (3H)
      pede aviso, caso o diretório dela seja reaberto um dia.

## 9. Divulgação no LinkedIn (alternativa sem diretório)

Uma publicação no LinkedIn apresenta o produto **sem depender de nenhum registry**, e dá para editar ou
apagar depois, ao contrário do registry. É um bom primeiro passo. Condições:

- [ ] **Esperar a `0.4.0` final promovida para `main`.** O caminho do Claude Desktop adiciona o
      marketplace pelo `main`, que hoje tem o plugin antigo `0.1.1`. Quem tentar agora recebe o plugin
      sem servidor.
- [ ] Dizer o que foi validado: hoje macOS (S2, S5, S6). **Windows ainda não** (T085). Não prometer o
      que não foi testado.
- [ ] **Nada de dado real** em imagens ou texto: ID da carteira, link `?h=`, valores, nome de usuário. O
      ID de carteira já vazou ao histórico uma vez; passar a captura de tela pela guarda antes.
- [ ] Tom de **ferramenta pessoal, somente leitura**: não promete rentabilidade nem recomendação de
      compra ou venda; deixar claro que é "não afiliado ao Investidor10" e que usa uma API interna não
      documentada, que pode mudar. Honestidade aqui também protege no ADR de termos de uso.
- [ ] Link para o `README` do repositório e para `docs/PRIVACY.md`.
- [ ] Publicar o texto em PT-BR e, se quiser, uma versão curta em inglês.

## Ordem sugerida

1. Decisões da seção 0 e o ADR dos termos de uso.
2. Anotações das 19 tools (regra 5E da política; ajuda em qualquer caminho).
3. `0.4.0` final: marcador no README, promoção para `main`.
4. LinkedIn (seção 9).
5. Registry oficial (seções 2 a 5), só com tudo marcado. PulseMCP vem depois, sozinho.
6. Smithery: só acompanhar.
