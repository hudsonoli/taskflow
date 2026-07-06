cat > backend/AGENTS.md <<'EOF'
# TaskFloww Backend - FastAPI

## Escopo

Este diretório contém o backend do TaskFloww.

Use:
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Redis quando necessário

## Regras

- Não alterar contratos JSON existentes sem autorização.
- Não alterar autenticação sem pedido explícito.
- Não alterar permissões sem pedido explícito.
- Não criar migration sem autorização.
- Não remover campos existentes.
- Não quebrar compatibilidade com o frontend.
- Validar tipos com Pydantic.
- Manter endpoints claros e previsíveis.

## Validação

Sempre executar testes disponíveis.

Se não houver testes, informar isso no resumo final.
EOF