# TaskFloww v2

## Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* dnd-kit

### Backend

* FastAPI
* Python

### Banco de Dados

* PostgreSQL

### Cache/Fila

* Redis

### Infraestrutura

* Docker

---

## Objetivo

TaskFloww é uma plataforma SaaS de gestão operacional para agências.

### Foco

* Tarefas
* Projetos
* Workflow
* Kanban
* Refações
* SLA
* Produtividade
* Relatórios Operacionais

### Fora de Escopo

TaskFloww não é ERP.

Não implementar:

* Financeiro
* Estoque
* Emissão Fiscal
* Faturamento
* Folha de Pagamento

---

## Ambiente

Diretório principal:

```text
/docker/taskfloww
```

Containers:

* taskfloww_front
* taskfloww_api
* taskfloww_db
* taskfloww_redis

Portas:

* Frontend: 3010
* API: 8010

---

## Estado Atual

### Fase 1 — Infraestrutura

Concluído.

Entregas:

* Estrutura inicial criada
* Docker configurado
* Next.js operacional
* FastAPI operacional
* PostgreSQL operacional
* Redis operacional
* Healthcheck validado

Endpoints:

* /health OK
* /status OK

---

### Fase 2 — Shell Boxx

Concluído.

Entregas:

* Shell principal criado
* Sidebar criada
* Header criado
* Dashboard inicial criado

Commit:

* 01c8d4c

---

### Fase 2.1 — Componentização

Concluído.

Entregas:

* Componentes de layout separados
* Componentes de dashboard separados
* Estrutura reutilizável criada

Estrutura:

```text
src/components/
├── dashboard/
│   ├── DashboardView.tsx
│   └── StatCard.tsx
│
└── layout/
    ├── Header.tsx
    ├── Shell.tsx
    └── Sidebar.tsx
```

Commit:

* 7a4a76c

---

### Fase 2.2 — Navegação

Concluído.

Entregas:

* Rotas criadas
* Navegação funcional
* Sidebar navegável
* Destaque automático da rota ativa
* Header dinâmico
* Layout persistente

Rotas:

* /
* /tarefas
* /projetos
* /clientes
* /equipe
* /relatorios
* /configuracoes

Commit:

* fase 2.2 cria navegacao e rotas base

---

### Documentação Claude Code

Concluído.

Arquivos:

* CLAUDE.md
* docs/skills/architecture.md
* docs/skills/ui-boxx.md
* docs/skills/coding-standards.md
* docs/skills/taskflow-rules.md
* docs/skills/git-workflow.md
* docs/skills/database-rules.md

Commit:

* 545122a

---

## Próxima Fase

### Fase 2.3 — Design System Boxx

Objetivos:

* Componentes UI reutilizáveis
* Card
* Button
* Input
* Badge
* Empty State
* Page Header
* Section

---

### Fase 3 — Kanban Visual

Objetivos:

* Colunas
* Cards
* Drag and Drop
* dnd-kit
* Estrutura visual sem banco

---

### Fase 4 — Backend

Objetivos:

* PostgreSQL
* Models
* SQLAlchemy
* API FastAPI

---

### Fase 5 — Autenticação

Objetivos:

* Empresas
* Usuários
* Permissões
* Login
* Sessões
