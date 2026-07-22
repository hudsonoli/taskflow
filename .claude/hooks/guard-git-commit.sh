#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash) — bloqueia o agente de executar `git commit`
# diretamente. Formaliza CLAUDE.md ("Nunca realizar commit automaticamente")
# e AGENTS.md ("Não faça commit sem aprovação explícita").
#
# Isso é um bloqueio incondicional, não condicionado a "o usuário aprovou no
# chat" — um hook não consegue verificar isso com segurança. Se o usuário já
# aprovou o commit na conversa, ele mesmo deve rodá-lo com o prefixo "!" no
# prompt (roda no shell da sessão, fora do agente). Para desativar
# temporariamente este guard, comente o bloco correspondente em
# .claude/settings.json.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

# Ignora linhas que são apenas echo/printf de texto literal (ex.: exemplos,
# mensagens de teste) — evita falso positivo quando "git commit" aparece só
# como string, não como invocação real.
scanned="$(printf '%s\n' "$command" | grep -Ev '^\s*(echo|printf)\b')"

if printf '%s' "$scanned" | grep -Eq '(^|[;&|]\s*)git\s+commit(\s|$)'; then
  echo "Bloqueado: este projeto proíbe o agente de rodar 'git commit' diretamente (CLAUDE.md/AGENTS.md: nunca commitar automaticamente). Se o commit já foi aprovado pelo usuário nesta conversa, peça para ele rodar o comando manualmente com '! git commit ...' no prompt." >&2
  exit 2
fi

exit 0
