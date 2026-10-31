# Arquivo local: abrir por descritor com `O_NOFOLLOW`, num ponto só, e não arquivo por arquivo

**Context:** A revisão final da spec 004 encontrou o mesmo defeito três vezes seguidas. No ciclo 1 foram os modos dos arquivos laterais (`.lock`, `.log`, temporário). No ciclo 2, o `chmod` por caminho do changelog seguia symlink. No ciclo 3, a leitura do próprio `memory.json` e o backup de arquivo corrompido seguiam symlink, e o `chmod` da trava continuava por caminho.
**Date:** 2026-10-29
**Future intent:** Todo arquivo local novo do `MemoryStore` é aberto pelos auxiliares existentes (`_read_file`, `_tighten`, `_tighten_by_path`) ou por um novo com as mesmas regras. Nenhum `open(self.path)` nem `os.chmod(path)` direto.

---

## Mental Model: cada abertura por caminho é uma nova chance de seguir um link

| Operação | Por caminho (errado) | Por descritor (certo) |
|---|---|---|
| Ler o `memory.json` | `open(path)` segue o link a cada leitura | `os.open(path, O_RDONLY \| O_NOFOLLOW \| O_BINARY)` e leitura pelo fd |
| Backup de arquivo corrompido | reabrir `path` para copiar | gravar os bytes **já lidos** no `_reload` |
| Apertar a permissão | `os.chmod(path, 0o600)` segue o link | `os.fchmod(fd, 0o600)` no fd aberto com `O_NOFOLLOW` |
| Acrescentar ao log | `open(path, "a")` | `os.open(..., O_APPEND \| O_NOFOLLOW, 0o600)` e `fdopen` |

Uma checagem de symlink na partida (`_ensure_not_symlink`) não protege as aberturas seguintes: o link pode ser criado depois dela (TOCTOU). Só a flag na própria abertura fecha a janela.

---

## Fatos verificados

- `O_NOFOLLOW` sobre um link falha com `OSError` (`ELOOP` no Linux e no macOS). Trate como indisponível, nunca como corrupção: não há conteúdo para copiar.
- `O_NOFOLLOW` e `O_BINARY` não existem em todas as plataformas. Use `getattr(os, "O_NOFOLLOW", 0)`. No Windows, sem `O_BINARY`, o descritor fica em modo texto e a leitura traduz quebras de linha.
- `os.fchmod` só existe no Windows a partir do Python 3.13. Use `hasattr(os, "fchmod")` e caia para `os.chmod` por caminho, onde não há link a seguir.
- Abrir o arquivo de trava num segundo fd só para o `fchmod` é seguro com o `filelock` no Unix, que usa `fcntl.flock`: a trava pertence à descrição de arquivo e fechar outro fd não a solta. Com `fcntl.lockf` (travas POSIX de registro), fechar **qualquer** fd do arquivo soltaria a trava.
- `os.replace` sobre um link troca o link por um arquivo comum: um `WALLET_MEMORY_PATH` que é link ficava desligado do alvo na primeira gravação.

---

## Relation to ADRs and next steps

- **ADR-0013**, emendas de 28/10 e 29/10/2026: changelog, leitura e trava sem seguir link.
- **ADR-0010**, emenda de 29/10/2026: `WALLET_MEMORY_PATH` como link fica indisponível desde a partida.
- Próximo arquivo local (por exemplo, um cache em disco): reutilizar os auxiliares e escrever primeiro o teste com um symlink no lugar.
