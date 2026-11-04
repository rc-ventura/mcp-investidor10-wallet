# Roteiro da máquina sem `uv` (spike S1, parte decisiva)

Objetivo: descobrir se o Claude Desktop consegue iniciar o servidor do plugin quando o `uv` **não** está
instalado. Na máquina do desenvolvedor o app usou o `uv` que já existia, então o resultado ali não prova nada.

Máquina: conta paga do Claude, só o Claude Desktop (com Cowork), sem Claude Code e sem `uv`.

## 1. Conferir que a máquina está limpa (antes de tudo)

macOS ou Linux, no terminal:

```bash
which uv uvx; echo "saída acima vazia = sem uv"
```

Windows, no PowerShell:

```powershell
where.exe uv; where.exe uvx
```

Esperado: nenhum caminho. Anote o que apareceu. Se aparecer um `uv`, a máquina não serve para este teste.

## 2. Baixar o plugin

Arquivo: `specs/005-desktop-distribution/spike/download/ping-plugin.zip` na branch `spec-005/spike-mcpb`.

Link direto: https://github.com/rc-ventura/mcp-investidor10-wallet/raw/spec-005/spike-mcpb/specs/005-desktop-distribution/spike/download/ping-plugin.zip

Não descompacte o zip.

## 3. Instalar e testar

1. Claude Desktop > Customize > Plugins > Add > Upload plugin, e escolha o zip.
   Se o app recusar, anote a mensagem exata.
2. Abra a aba Connectors do plugin `spike-ping`. Anote o estado do servidor `ping`
   (conectado, falhou, pedindo algo) e a mensagem, se houver.
3. Numa conversa nova da tela inicial (sessão Cowork), escreva: `use a tool ping`.
   Esperado, se funcionar: `pong`.
4. Se o `ping` funcionou, escreva: `use a tool abrir_pagina`, digite `TESTE-LIMPA` na página e envie.
   O valor não deve aparecer na conversa.

## 4. O que enviar de volta

1. A saída do passo 1 (sem `uv` confirmado).
2. O estado do servidor na aba Connectors e qualquer mensagem de erro (texto ou print).
3. O resultado do `ping` e do `abrir_pagina`.
4. Se o `ping` falhou: o trecho do log do app com "Using MCP server command" ou o erro de conexão.
   macOS: `~/Library/Logs/Claude/main.log`. Windows: procure a pasta `Claude\logs` dentro de `%APPDATA%`.
5. Versão do Claude Desktop e sistema operacional.

## 5. O que o resultado significa

| Resultado | Leitura |
|---|---|
| `ping` responde `pong` sem `uv` | O Desktop traz ou instala o que precisa. O tipo `uv` serve para o usuário leigo. |
| Servidor falha, erro de comando `uv` não encontrado | O Desktop depende do `uv` da máquina. O tipo `uv` não ajuda o usuário leigo; a escolha cai para binário por plataforma ou `uv` como pré-requisito. |
| Falha por outro motivo | Anotar a mensagem; pode ser outro problema (permissão, rede, antivírus). |

## 6. Limpeza

Desinstale o plugin `spike-ping` e apague a pasta `.investidor10-spike` do seu usuário.
