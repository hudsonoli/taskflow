---
description: Roda o checklist obrigatório e o processo de validação do TaskFloww (typecheck, lint, build, git status/diff) antes de considerar um módulo concluído
---

Invoque a skill `validar-modulo` (ou dispare o agente `qa-validator`) para o escopo "$ARGUMENTS" (ou o diff atual, se nenhum argumento for dado). Reporte cada item do checklist como passou/falhou — nunca declare sucesso parcial como conclusão.
