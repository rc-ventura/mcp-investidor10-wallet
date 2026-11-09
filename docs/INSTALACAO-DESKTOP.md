# Instalação no Claude Desktop

> **Rascunho a validar.** Os passos marcados com *(a validar)* dependem do teste em
> máquina sem `uv` (spec 005, Lote 1). Não publique este texto como definitivo antes
> de rodar o roteiro no macOS e no Windows.

O servidor da carteira roda com o `uv`, um programa gratuito que baixa e executa
o servidor. O Claude Desktop **não traz o `uv`** (verificado em máquina sem `uv`, em
2026-11-08, nos dois formatos de plugin testados), então você instala o `uv` uma única
vez, no terminal. Depois disso, o resto é feito dentro do Claude Desktop.

Você precisa de uma conta paga do Claude com o Claude Desktop instalado.

## Passo a passo

1. **Abra o terminal.**
   - Mac: pressione `Cmd + Espaço`, digite `Terminal` e pressione Enter.
   - Windows: abra o menu Iniciar, digite `PowerShell` e pressione Enter.

2. **Instale o `uv`.** Copie o comando do seu sistema, cole no terminal e pressione Enter.
   - Mac ou Linux:

     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

   - Windows (PowerShell):

     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

3. **Confira a instalação.** *(a validar)* Feche o terminal, abra um novo e digite
   `uv --version`. Deve aparecer um número de versão. Se aparecer "comando não
   encontrado", repita o passo 2 e abra um terminal novo.

4. **Feche o Claude Desktop por completo e abra de novo.** *(a validar)*
   - Mac: `Cmd + Q` (fechar só a janela não basta).
   - Windows: clique com o botão direito no ícone do Claude na bandeja e escolha Sair.

5. **Instale o plugin.** No Claude Desktop, vá em Customize > Plugins, adicione o
   marketplace colando `rc-ventura/mcp-investidor10-wallet` e instale o plugin
   `investidor10-carteira`.

6. **Abra uma conversa nova** na tela inicial e escreva: `Configure minha carteira`.

7. **Configure.** O navegador abre uma página local. Cole o link da sua carteira do
   Investidor10, escolha se quer esconder os valores em reais do modelo e salve.
   - Carteira pública: o link `https://investidor10.com.br/wallet/public/<número>`.
   - Carteira restrita: o link de compartilhamento completo, que termina em `?h=...`.

8. **Teste.** Volte à conversa e peça: `Faça um resumo da minha carteira`.

## Se não funcionar

- O servidor `carteira` não aparece conectado em Customize > Plugins: repita o passo 3.
  Se o `uv --version` funciona no terminal mas o Claude não encontra o `uv`, reinicie
  o computador e abra o Claude Desktop de novo. *(a validar)*
- O navegador não abre na etapa 7: copie o endereço que o Claude mostrar na conversa
  e cole no navegador.
- A página recusa o link: confira se é o link da carteira, sem texto extra, e se o
  link restrito inclui o `?h=`.

## Para registrar nos testes

Ao validar este roteiro, anote por passo: sistema, versão do Claude Desktop, se foi
preciso reiniciar o Desktop ou o computador, e a mensagem exata de erro, se houver.
