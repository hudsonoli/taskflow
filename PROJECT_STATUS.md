# TaskFloww v2

## Stack

Frontend:
- Next.js
- React
- Tailwind
- dnd-kit

Backend:
- FastAPI
- Python

Banco:
- PostgreSQL

Cache/Fila:
- Redis

## Objetivo

TaskFloww é uma plataforma SaaS de gestão operacional para agências.

Foco:
- tarefas
- projetos
- workflow
- kanban
- refações
- SLA
- produtividade
- relatórios operacionais

Não é ERP financeiro.

## Estado atual

### Fase 1
Estrutura inicial criada em /docker/taskfloww.

Containers:
- taskfloww_front
- taskfloww_api
- taskfloww_db
- taskfloww_redis

API validada:
- /health OK
- /status OK

Frontend Next.js rodando na porta 3010.

## Próxima fase

Criar layout base Boxx:
- shell principal
- sidebar
- header
- dashboard inicial
- kanban inicial
