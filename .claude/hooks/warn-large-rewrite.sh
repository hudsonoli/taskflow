#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash) — avisa (não bloqueia) quando o comando
# parece ser uma reescrita grande de arquivo via sed/perl/script, o que
# AGENTS.md proíbe sem autorização explícita ("Não usar perl, sed, python ou
# scripts grandes para reescrever arquivos, salvo autorização explícita" /
# "Preferir patches pequenos e auditáveis").
#
# `sed -i`/`perl -i` (edição in-place) bloqueiam de fato — são inequívocos.
# Qualquer outro padrão (ex.: python3 -c manipulando arquivos) só avisa,
# porque o próprio graphify usa `python3 -c "..."` extensivamente para JSON
# e um bloqueio amplo quebraria o pipeline do graphify.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

# Ignora linhas que são apenas echo/printf de texto literal — evita falso
# positivo quando o padrão aparece só como string de exemplo/teste.
scanned="$(printf '%s\n' "$command" | grep -Ev '^\s*(echo|printf)\b')"

if printf '%s' "$scanned" | grep -Eq '\b(sed|perl)\s+.*-i\b'; then
  echo "Bloqueado: edição in-place com sed/perl (-i) não é permitida sem autorização explícita do usuário (AGENTS.md: preferir patches pequenos e auditáveis via Edit/Write, não scripts de reescrita em massa). Se o usuário já autorizou explicitamente este script, avise-o de que precisa desativar este hook temporariamente." >&2
  exit 2
fi

if printf '%s' "$scanned" | grep -Eq 'python3? +-c' && printf '%s' "$scanned" | grep -Eq "(backend/app|frontend/src)" && ! printf '%s' "$scanned" | grep -Eq 'graphify'; then
  # stdout (não stderr) com exit 0: vira contexto adicional para o agente,
  # sem bloquear — mesmo mecanismo usado pelo guard do graphify.
  echo "AVISO AGENTS.md: comando Python inline tocando código-fonte (backend/app ou frontend/src) fora do graphify. Confirme que isso é um patch pequeno e auditável, não uma reescrita em massa — scripts grandes de reescrita exigem autorização explícita. Prefira Edit/Write."
fi

exit 0
