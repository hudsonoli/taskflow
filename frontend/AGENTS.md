cat > frontend/AGENTS.md <<'EOF'
# TaskFloww Frontend - React / Next.js

## Escopo

Este diretório contém o frontend do TaskFloww.

Use:
- React
- Next.js App Router
- TypeScript
- Tailwind

## Regras

- Alterar somente arquivos relacionados à tarefa.
- Preservar layout existente.
- Preservar padrão visual do TaskFloww.
- Não modificar Sidebar, Header ou Dashboard se a tarefa não pedir.
- Não criar CSS separado.
- Usar Tailwind.
- Não usar `any`.
- Preferir componentes pequenos e legíveis.
- Não criar estado global se estado local resolver.
- Reutilizar componentes existentes antes de criar novos.

## CRUDs

Para telas de cadastro, seguir o padrão:

- listagem
- busca
- filtros quando necessário
- botão de novo cadastro
- modal ou tela de edição
- validação básica
- estado vazio
- feedback visual

## Validação

Sempre executar:

npm run build

Se o build falhar, corrigir antes de concluir.
EOF