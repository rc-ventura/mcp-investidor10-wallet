#!/bin/bash
set -euo pipefail

HOOK_INPUT=$(cat)

TRANSCRIPT=$(echo "$HOOK_INPUT" | grep -o '"transcript_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

if grep -qiE "comprar|vender|aportar|alocar|decis[ãa]o|rebalancear" "$TRANSCRIPT" && ! grep -q "log_decision\|log_insight" "$TRANSCRIPT"; then
  echo "Lembrete da memória do investidor: esta sessão discutiu decisões de investimento sem registrá-las na memória."
  echo "Se o usuário confirmar, chame log_decision (ou log_insight) com um resumo objetivo da decisão."
  echo "Nunca grave na memória sem confirmação explícita do usuário."
fi

exit 0