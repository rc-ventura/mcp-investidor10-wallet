---
name: configurar-carteira
description: Configura ou troca a carteira do Investidor10 no produto. Use na primeira conversa, quando o usuário pedir "configure minha carteira", "troque o link", "esconda os valores", ou diante de qualquer erro wallet_not_configured ou access_denied
---

0. Se as tools da carteira (como `get_session_context`) não existirem nesta sessão, o servidor não subiu. Diga isso, peça para conferir se o `uv` está instalado conforme `docs/INSTALACAO-DESKTOP.md` e, numa conversa Chat sem tools, explique que as tools só carregam numa sessão Cowork no computador. Não invente valores nem analise nada sem as tools.
1. Explique onde copiar o link no site do Investidor10 (compartilhar a carteira) e que a carteira restrita, com o link completo terminado em `?h=...`, é a opção mais privada.
2. Chame `open_wallet_setup`. Se a resposta trouxer o endereço da página (`open_manually`), mostre-o ao usuário e cite `mcp-investidor10-wallet configure` como alternativa pelo terminal.
3. Peça para colar o link na página que abriu, nunca na conversa. Se o usuário colar o link na conversa, não reutilize o valor e avise que ele ficou no histórico da conversa.
4. Quando o usuário disser que salvou, chame `get_session_context` e confira o bloco `configuration`: mostre o modo (pública ou restrita) e se o mascaramento de valores está ligado, e siga para a pergunta original do usuário.
