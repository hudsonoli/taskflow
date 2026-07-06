# AGENTS.md — TaskFloww v2

## Papel do agente

Você está trabalhando no projeto TaskFloww v2, uma plataforma SaaS de gestão operacional para agências.

O objetivo é ajudar na implementação com segurança, mantendo consistência, histórico limpo no Git e validações antes de qualquer commit.

## Stack

Frontend:
- Next.js
- React
- TypeScript
- Tailwind CSS

Backend:
- FastAPI
- Python
- PostgreSQL
- Redis

Infraestrutura:
- Docker Compose

## Escopo do produto

TaskFloww é uma plataforma de gestão operacional, focada em:

- tarefas
- projetos
- workflow
- kanban
- clientes
- grupos de clientes
- fornecedores
- equipes
- usuários
- SLA
- produtividade
- relatórios operacionais

TaskFloww não é ERP.

Não implementar sem aprovação explícita:
- financeiro
- estoque
- emissão fiscal
- faturamento
- folha de pagamento

## Workflow obrigatório

Antes de alterar qualquer arquivo:

1. Leia este AGENTS.md.
2. Leia PROJECT_STATUS.md.
3. Mostre um plano curto.
4. Liste os arquivos que pretende alterar.
5. Aguarde aprovação.
6. Aplique mudanças pequenas.
7. Valide.
8. Mostre status e diff.
9. Não faça commit sem aprovação explícita.

## Regras de edição

- Não usar `perl`, `sed`, `python` ou scripts grandes para reescrever arquivos, salvo autorização explícita.
- Preferir patches pequenos e auditáveis.
- Se um patch falhar, parar e mostrar o erro.
- Não tentar várias correções automáticas em sequência.
- Não alterar arquivos fora do escopo aprovado.
- Não alterar backend, API, banco ou tipos se a tarefa for apenas visual.
- Não criar integrações reais sem aprovação.

## Validações

Para alterações no frontend, rodar dentro do container:

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
docker compose exec taskfloww_front npm run build