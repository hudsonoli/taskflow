# TaskFloww v2

TaskFloww é uma plataforma SaaS de gestão operacional para agências.

## Stack

Frontend:
- Next.js
- React
- TypeScript
- Tailwind
- dnd-kit

Backend:
- FastAPI
- Python
- PostgreSQL
- Redis
- Docker

## Objetivo do sistema

O TaskFloww serve para:
- tarefas
- projetos
- workflow
- kanban
- refações
- SLA
- produtividade
- relatórios operacionais

O TaskFloww não é ERP financeiro.

Não implementar:
- financeiro
- estoque
- emissão fiscal
- faturamento
- módulo contábil

## Estado atual

Fase 1:
- Docker funcionando
- Next.js na porta 3010
- FastAPI na porta 8010
- PostgreSQL OK
- Redis OK

Fase 2:
- Shell Boxx criado
- Sidebar criada
- Header criado
- Dashboard inicial criado

Fase 2.1:
- Componentes organizados em:
  - src/components/layout
  - src/components/dashboard

## Regra principal

Sempre respeitar a fase atual do projeto.

Não criar banco, autenticação, Kanban ou APIs novas sem solicitação explícita.

Antes de alterar arquivos:
1. Ler PROJECT_STATUS.md
2. Ler CLAUDE.md
3. Verificar estrutura atual
4. Fazer alterações pequenas
5. Validar com lint
6. Commitar com mensagem clara

## Regras de Permissão

O sistema utilizará RBAC (Role Based Access Control).

Perfis previstos:

- SuperAdmin
- Admin
- Diretoria
- Gestor
- Operador
- Cliente

### Configurações

Configurações é uma área administrativa.

Não deve ser exibida para:

- Operador
- Cliente

Deve ser exibida para:

- SuperAdmin
- Admin
- Diretoria
- Gestor
- Usuários com permissão explícita

Importante:

Enquanto não existir autenticação, as telas podem ser criadas normalmente, porém as regras de permissão devem ser consideradas no design futuro.
