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

Rotas base:

* /
* /tarefas
* /projetos
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

### Fase 3.5 — Estrutura Base de Configurações

Concluído.

Entregas:

* Área administrativa de Configurações criada
* Estrutura preparada para módulos administrativos
* Organização inicial do menu de configurações

Commit:

* 7a75287

---

### Fase 3.7 — Agências e Usuários

Concluído.

Entregas:

* Cadastro mock de Agências
* Cadastro mock de Usuários
* Estrutura administrativa inicial

Commit:

* a062e69

---

### Fase 3.8 — Equipes

Concluído.

Entregas:

* Cadastro administrativo de Equipes
* Estrutura inicial para organização interna

Commit:

* d1a9961

---

### Fase 3.9 — Workflows

Concluído.

Entregas:

* Tela administrativa de Workflows
* Estrutura mock inicial
* Preparação para automações futuras

Commit:

* a9cd9c7

---

### Fase 3.10 — Configurações Operacionais

Concluído.

Entregas:

* Reorganização da área administrativa
* Estrutura operacional das configurações
* Ajustes de navegação

Commit:

* aaba63c

---

### Fase 3.11 — Usuários V2

Concluído.

Entregas:

* Cadastro completo de usuários
* Controle de permissões
* Histórico
* Estrutura multiempresa
* Relacionamentos por ID

Commit:

* 4120221

---

### Fase 3.12 — Equipes V2

Concluído.

Entregas:

* Cadastro completo de equipes
* Membros
* Permissões
* Histórico
* Estrutura multiempresa
* Relacionamentos por ID

Commit:

* 1a2a3d4

---

### Fase 3.13 — Clientes V2

Concluído.

Entregas:

* ClienteDraft reescrito com clienteId e empresaId
* Relacionamentos por ID:

  * equipeResponsavelId
  * responsavelComercialId
  * responsavelAtendimentoId
* Remoção de referências por nome
* Remoção de dados financeiros fora do escopo do TaskFloww
* Aba "Equipe" substitui "Informações Complementares"
* Cadastro migrado de /clientes para /configuracoes/clientes
* Remoção do item "Clientes" do menu principal
* Inclusão do card "Clientes" em Configurações
* TypeScript validado
* ESLint validado
* Build validado

Commit:

* fce0a08

---

### TF-ORG-002.2 — Departamentos

Concluída.

Entregas:

* Bloqueio da inativação de Departamento com vínculos ativos de Usuários
* Bloqueio da inativação de Departamento com SessaoTrabalho ativa vinculada
* HTTP 409 confirmado para os cenários de conflito
* Testes específicos adicionados e aprovados
* Suíte completa aprovada com 611 testes
* 20 warnings de depreciação preexistentes
* Nenhuma regressão encontrada

Pendência exclusiva da TF-ORG-002.3:

* Validação de Equipes ativas após a criação de departamento_id em Equipe

---

## Próxima Fase

### Fase 3.14 — Departamentos V2

Objetivos:

* departamentoId
* codigoInterno
* sigla
* responsável pelo departamento
* vínculo com equipes
* vínculo com usuários
* histórico de alterações
* permissões
* padrão visual alinhado a Usuários, Equipes e Clientes

---

## Fases Futuras

### Workflows Reais

Objetivos:

* Substituir estruturas mock
* Workflow por cliente
* Workflow por departamento
* Regras operacionais

---

### Projetos

Objetivos:

* Cliente → Projeto → Tarefas
* Integração com workflow
* Kanban operacional

---

### Backend

Objetivos:

* PostgreSQL
* SQLAlchemy
* FastAPI
* APIs reais

---

### Autenticação

Objetivos:

* Empresas
* Usuários
* Permissões
* Login
* Sessões

---

## Regras de Permissão

O TaskFloww utilizará controle de acesso por perfil.

Perfis previstos:

* SuperAdmin
* Admin
* Diretoria
* Gestor
* Operador
* Cliente

### Configurações

O menu Configurações não será visível para todos os usuários.

Terão acesso:

* SuperAdmin
* Admin
* Diretoria
* Gestor
* Usuários com permissão específica

Não terão acesso:

* Operador
* Cliente

### Observação

Nesta fase ainda não existe autenticação.

As permissões serão implementadas futuramente após a criação do módulo de usuários e autenticação.
