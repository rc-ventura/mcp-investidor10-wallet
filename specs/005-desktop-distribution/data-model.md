# Data Model — Spec 005

O schema da memória (`memory.json` v1) não muda. As entidades novas são a
configuração local, o estado de configuração, o link interpretado e os
artefatos de distribuição (plugin e servidor empacotado).

## 1. Configuração local (`~/.investidor10/config.json`)

Arquivo único por usuário da máquina, lido por todos os clientes.

| Campo | Tipo | Regra |
|---|---|---|
| `version` | int | `1`. Versão maior que a suportada: estado pendente com causa "configuração de versão futura", arquivo intocado |
| `wallet_id` | string | Só dígitos (`[0-9]+`) |
| `share_hash` | string ou `null` | `null` no modo público; no restrito, `[A-Za-z0-9_-]{1,256}` |
| `mode` | `"public"` ou `"restricted"` | Coerente com `share_hash` (restrito exige credencial) |
| `mask_values` | bool | Escolha do usuário; o efetivo é `mask_values OR WALLET_MASK_VALUES` |
| `validated_at` | string ISO 8601 | Momento da última validação bem-sucedida contra a fonte |
| `source` | `"setup_page"`, `"installer"` ou `"configure"` | Quem gravou por último (diagnóstico) |

Armazenamento:

- Diretório `~/.investidor10/` (0700, regular, nunca link), o mesmo da
  memória; arquivo 0600, aberto por descritor com `O_NOFOLLOW`.
- Gravação atômica: arquivo temporário no mesmo diretório, `fsync`,
  `os.replace`; no Windows, o mesmo retry de `os.replace` da memória.
- Nunca entra no changelog da memória, em logs nem em mensagens.
- Desinstalar ou atualizar o plugin não toca no arquivo (FR-009c).

Exemplo (valores fictícios):

```json
{
  "version": 1,
  "wallet_id": "<id>",
  "share_hash": "<hash>",
  "mode": "restricted",
  "mask_values": false,
  "validated_at": "2026-11-01T10:00:00-03:00",
  "source": "setup_page"
}
```

## 2. Estado de configuração (em processo)

Resolvido no início de cada chamada de tool de carteira e de
`get_session_context`, relendo o arquivo só quando a identidade dele muda
(inode, tamanho, `mtime_ns`).

```text
            arquivo válido
pendente  ─────────────────▶  configurado (fonte: arquivo)
   │  ▲                           │
   │  │ arquivo removido,         │ página de configuração / configure
   │  │ ilegível ou corrompido    ▼ (outra carteira exige confirmação)
   │  └────────────────────── configurado (nova carteira)
   │
   │ sem arquivo, WALLET_ID válido no ambiente
   ▼
configurado (fonte: ambiente, legado)
```

| Estado | Tools de carteira | `get_session_context.configuration` |
|---|---|---|
| `pending` | erro `wallet_not_configured` | `status: "pending"`, `reason` (`missing`, `unreadable`, `future_version`), `next_action` nomeando `open_wallet_setup` |
| `configured` | normais | `status: "configured"`, `mode`, `mask_values`, `wallet` mascarado, `origin` (`file` ou `environment`) |

Regras:

- Arquivo válido vence o ambiente; o ambiente só vale sem arquivo.
- `WALLET_ID` inválido no ambiente continua abortando a inicialização
  (comportamento atual, erro de quem registrou).
- Mudança de configuração entre chamadas troca a carteira dos clientes HTTP
  e esvazia o cache deles (o cache não pode servir dados da carteira
  anterior).

## 3. Link da carteira (entrada)

Valor transitório: nunca persistido como texto, só os campos extraídos.

| Forma | Resultado |
|---|---|
| `https://[www.]investidor10.com.br/wallet/public/<id>?h=<hash>` | `mode=restricted`, `wallet_id`, `share_hash` |
| `https://[www.]investidor10.com.br/carteira/<id>[/...]` | `mode=public`, `wallet_id` |
| `<id>` (só dígitos) | `mode=public`, `wallet_id` |
| qualquer outra coisa, host diferente, dois IDs, credencial fora do alfabeto | recusa com orientação, na página ou no terminal |

Pré-processamento: remove espaços, aspas e sinais em volta; aceita texto ao
redor quando há exatamente uma URL do host; ignora parâmetros de
rastreamento (`utm_*` e afins).

## 4. Resultado da validação contra a fonte

| Resposta da fonte (`/summary/metrics/<id>`, com `hash` no modo restrito) | Resultado | Grava? |
|---|---|---|
| 200 | `valid` | sim |
| 3xx, 401, 403 | `access_denied` | não |
| 404 | `not_found` | não |
| 5xx, timeout, transporte | `unavailable` | página: não; terminal: só com confirmação explícita |

## 5. Página de configuração (em processo)

Sessão temporária, uma por processo do servidor; nada dela vai para disco.

| Campo | Regra |
|---|---|
| `token` | `secrets.token_urlsafe`, de uso único |
| `expires_at` | 10 minutos depois de abrir, no relógio monotônico |
| endereço | `http://127.0.0.1:<porta livre>/?t=<token>`; só `127.0.0.1` |
| estado | `open` → `saved` ou `expired`; nos dois casos a página encerra |

O envio (`POST`) exige o token, `Host` local e `Origin` da própria página. A
troca para outra carteira pede uma confirmação na página antes de gravar. O
corpo do envio nunca vai para log, e o link nunca aparece na URL.

## 6. Pacote do servidor dentro do plugin (`plugin/servers/carteira.mcpb`)

Zip determinístico (ordem fixa, datas fixas, permissões fixas), gerado por
script do repositório, commitado e atualizado só no PR de release. Não leva o
código do servidor.

| Conteúdo | Origem |
|---|---|
| `manifest.json` | gerado: `manifest_version` 0.4, `name` `carteira`, `version` = versão do pacote, `server.type` `uv`, `server.entry_point`, `compatibility.platforms` `["darwin", "win32", "linux"]`, `tools` = lista do servidor, sem `user_config` |
| `pyproject.toml` | gerado: `requires-python` igual ao da raiz e a dependência única `mcp-investidor10-wallet==<versão>` |
| `server/main.py` | ponto de entrada que chama o `main` do servidor instalado |

Invariantes:

- A cada build: versões iguais (pacote, manifestos do plugin, manifesto MCPB);
  nenhum ID ou credencial no conteúdo; no PR para a branch padrão, `plugin/` só
  muda com a versão.
- Na release (`--check`): zip commitado = zip gerado; tools do manifesto = tools
  do servidor.

## 7. Manifesto do plugin (Claude)

`plugin/.claude-plugin/plugin.json` passa a ter `version` igual à do pacote
(hoje 0.1.1, independente) e `mcpServers: "./servers/carteira.mcpb"`. Os
manifestos de Devin, Codex e Gemini mudam só a versão.

## 8. Relatório de diagnóstico (`doctor`)

Lista ordenada de checagens; cada uma com `id`, `status`
(`ok`, `warn`, `fail`), `cause` e `action` em PT-BR. Checagens: runner,
configuração (presença, permissões, versão, modo, mascaramento efetivo),
validação contra a fonte, memória (leitura, escrita, trava), clientes
(registro ou plugin, `@synced`, duplicação do servidor, entrada manual antiga em
`claude_desktop_config.json`), carteira restrita que responde sem a credencial
(ficou pública e indexável), versões (pacote, plugin). Sanitização:
home vira `~`, sem ID (só "configurado"), sem credencial (só
"presente/ausente"), sem valores nem conteúdo da memória.
