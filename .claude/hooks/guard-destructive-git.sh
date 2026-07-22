#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash) — bloqueia operações destrutivas de git
# além do já coberto pelas instruções padrão do agente (defesa em
# profundidade, útil sobretudo se o modo de permissão estiver mais permissivo
# que o normal). Cobre: reset --hard, push --force(-with-lease incluso),
# branch -D, clean -f, checkout/restore que descartam mudanças no working
# tree inteiro.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

# Ignora linhas que são apenas echo/printf de texto literal (ex.: exemplos,
# mensagens de teste) — evita falso positivo quando o comando perigoso
# aparece só como string, não como invocação real.
scanned="$(printf '%s\n' "$command" | grep -Ev '^\s*(echo|printf)\b')"

pattern='git\s+reset\s+.*--hard'
pattern="$pattern|git\s+push\s+.*(--force|-f)\b"
pattern="$pattern|git\s+branch\s+.*-D\b"
pattern="$pattern|git\s+clean\s+.*-f"
pattern="$pattern|git\s+(checkout|restore)\s+\.\s*$"

if printf '%s' "$scanned" | grep -Eq "$pattern"; then
  echo "Bloqueado: comando git destrutivo detectado ('$command'). Operações como reset --hard, push --force, branch -D, clean -f e checkout/restore de todo o working tree não podem ser executadas pelo agente sem confirmação explícita e recente do usuário para esta ação específica. Peça para o usuário rodar manualmente com '!' no prompt, ou confirme explicitamente e peça para desativar este guard temporariamente em .claude/settings.json." >&2
  exit 2
fi

exit 0
