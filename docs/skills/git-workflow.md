# Git Workflow

Sempre trabalhar com commits pequenos.

Antes de commit:

git status

Validar frontend:

docker exec -it taskfloww_front npm run lint

Commit padrão:

git add .
git commit -m "fase X descricao curta"

Exemplos:

git commit -m "fase 2.2 cria rotas base"
git commit -m "fase 3 inicia kanban visual"
git commit -m "fase 4 cria modelos iniciais backend"

Nunca fazer commit sem validar lint quando alterar frontend.
