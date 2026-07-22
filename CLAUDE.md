# TaskFloww V2

TaskFloww é uma plataforma SaaS de gestão operacional desenvolvida para agências, equipes de marketing, comunicação e operações.

O objetivo é centralizar processos, tarefas, projetos, workflows, indicadores e produtividade em uma plataforma moderna, escalável e multiempresa.

---

# Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- dnd-kit

## Backend

- FastAPI
- Python
- PostgreSQL
- Redis
- Docker

---

# Arquitetura

O TaskFloww é um sistema SaaS multiempresa.

## Regras obrigatórias de modelagem

Toda entidade principal deverá possuir:

- id
- empresaId
- createdAt
- updatedAt

Quando aplicável:

- clienteId
- usuarioId

Sempre utilizar IDs para relacionamentos.

Nunca utilizar nomes como chave entre entidades.

Exemplo:

✅ departamentoId

❌ nomeDepartamento

Toda modelagem deve estar preparada para:

- Multiempresa
- Auditoria
- Histórico
- Permissões
- APIs
- Inteligência Artificial

---

# Estrutura do Frontend

## src/app

Responsável APENAS pelas rotas do Next.js.

Cada módulo deve obrigatoriamente possuir um:

page.tsx

Exemplo:

```tsx
import { UsuariosView } from "@/components/usuarios/UsuariosView";

export default function UsuariosPage() {
  return <UsuariosView />;
}
```

Nunca colocar regras de negócio dentro do page.tsx.

---

## src/components

Responsável por:

- Views
- Modais
- Formulários
- Componentes reutilizáveis

Exemplo:

```
components/
    usuarios/
        UsuariosView.tsx
        NovoUsuarioModal.tsx
        UsuarioFormSections.tsx
```

---

## src/types

Todos os tipos devem ficar em:

```
src/types/
```

Nunca declarar grandes tipos dentro dos componentes.

---

## src/lib

Responsável por:

- mocks
- helpers
- geração de IDs
- máscaras
- utilidades
- buscas mock

Nunca colocar componentes React dentro de lib.

---

# Estrutura obrigatória de um módulo

Todo novo módulo deve possuir:

```
src/app/.../<modulo>/page.tsx

src/components/<modulo>/

src/types/<modulo>.ts

src/lib/<modulo>-mock.ts
```

Quando aplicável.

---

# Checklist obrigatório

Antes de considerar qualquer módulo concluído:

□ Criar a rota page.tsx

□ Criar a View

□ Criar os componentes

□ Criar os tipos

□ Criar os mocks

□ Adicionar ao menu correspondente

□ Adicionar ao hub de Configurações (quando necessário)

□ Validar acesso direto à URL

□ npm run lint

□ npm run build

□ Mostrar git status

□ Mostrar git diff --stat

Nunca considerar um módulo concluído apenas porque os componentes foram criados.

---

# Organização dos Cadastros

Todo cadastro deve seguir o padrão:

```
Página
    ↓
View
    ↓
Tabela
    ↓
Modal
    ↓
Sections
```

Exemplo:

```
UsuariosPage

↓

UsuariosView

↓

NovoUsuarioModal

↓

UsuarioFormSections
```

---

# Componentes UI

Sempre reutilizar componentes existentes.

Priorizar:

- Badge
- Button
- Card
- EmptyState
- Input
- Modal
- PageHeader
- Section
- Select
- Tabs
- Textarea

Evitar criar componentes duplicados.

---

# Estado Atual

## Infraestrutura

- Docker
- Next.js
- FastAPI
- PostgreSQL
- Redis

## Interface

- Shell Boxx
- Sidebar
- Header
- Dashboard

## Configurações

Implementados:

- Usuários
- Agências
- Clientes
- Grupos de Clientes
- Equipes
- Workflows
- Permissões
- SLA
- Prioridades
- Tipos de Tarefa

Todos atualmente utilizando mocks.

---

# Desenvolvimento

Sempre respeitar a fase atual do projeto.

Durante a fase de prototipação:

NÃO criar:

- migrations
- banco
- APIs reais
- autenticação
- integrações externas

Utilizar apenas:

- mocks
- estados React
- dados locais

---

# Fluxo de Desenvolvimento

Antes de alterar qualquer arquivo:

1. Ler PROJECT_STATUS.md
2. Ler CLAUDE.md
3. Analisar estrutura existente
4. Reutilizar componentes
5. Apresentar plano
6. Mostrar diff
7. Aguardar aprovação
8. Aplicar alterações
9. Validar TypeScript
10. Executar lint
11. Executar build
12. Mostrar git status
13. Mostrar git diff --stat

Nunca realizar commit automaticamente.

---

# Processo de Validação

Toda alteração relevante deverá:

1. Ser criada em sandbox
2. Validar TypeScript
3. Validar imports
4. Executar lint
5. Executar build
6. Mostrar diff consolidado
7. Solicitar aprovação

Nunca aplicar grandes alterações diretamente no projeto.

---

# Objetivo do Sistema

O TaskFloww possui foco operacional.

Módulos principais:

- Gestão de Tarefas
- Projetos
- Workflows
- Kanban
- SLA
- Refações
- Equipes
- Squads
- Produtividade
- Relatórios
- Indicadores

---

# Fora do Escopo

Não implementar sem solicitação explícita:

- ERP Financeiro
- Estoque
- Emissão Fiscal
- Contabilidade
- Folha
- Controle Bancário

---

# Referência de Interface

A principal referência funcional é o iClips.

Utilizar como inspiração:

- Fluxos
- Organização
- Navegação
- Cadastros
- Permissões

Nunca copiar código ou layout.

---

# Cadastro de Clientes

Fluxo previsto:

1. CPF/CNPJ
2. Validação
3. Busca automática (quando existir integração)
4. Código interno (#0000)
5. Sigla automática
6. Cadastro completo

Abas:

- Dados
- Endereço
- Contatos
- Equipe
- Histórico

---

# Permissões

Modelo RBAC.

Perfis:

- SuperAdmin
- Admin
- Diretoria
- Gestor
- Operador
- Cliente

---

# Configurações

Área administrativa.

Não exibir para:

- Operador
- Cliente

Exibir para:

- SuperAdmin
- Admin
- Diretoria
- Gestor
- Usuários com permissão explícita

---

# Auditoria

Toda modelagem deverá prever:

- Usuário
- Data/Hora
- Histórico
- IP
- Dispositivo

Ainda não implementar.

Preparar a estrutura.

---

# Integrações Futuras

Planejadas:

- Importação iClips
- Inteligência Artificial
- Dashboard Executivo
- APIs
- Relatórios avançados
- Automações

Somente implementar quando a fase correspondente for iniciada.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
