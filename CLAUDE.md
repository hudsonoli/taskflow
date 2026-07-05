# TaskFloww V2

TaskFloww é uma plataforma SaaS de gestão operacional desenvolvida para agências, equipes de marketing, comunicação e operações.

O foco do sistema é centralizar processos, tarefas, projetos, fluxos de trabalho, indicadores operacionais e produtividade em uma única plataforma moderna, escalável e multiempresa.

---

# Stack

## Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* dnd-kit

## Backend

* FastAPI
* Python
* PostgreSQL
* Redis
* Docker

---

# Arquitetura

O TaskFloww é um sistema SaaS multiempresa.

## Regras obrigatórias de modelagem

* Toda entidade principal deve possuir `empresaId`.
* Quando aplicável, utilizar também `clienteId`.
* Toda entidade principal deve possuir `id`.
* Toda entidade principal deve possuir `createdAt` e `updatedAt`.
* Sempre utilizar IDs para relacionamentos.
* Nunca utilizar nomes como referência principal entre entidades.
* Exemplo: utilizar `departamentoId` em vez de armazenar o nome do departamento.
* Sempre que possível, preparar a modelagem para auditoria futura.

O sistema deverá ser preparado desde o início para:

* Auditoria
* Controle de permissões
* Histórico de alterações
* Escalabilidade multiempresa
* APIs futuras
* Inteligência Artificial integrada

---

# Objetivo do Sistema

O TaskFloww serve para:

* Gestão de tarefas
* Gestão de projetos
* Workflow
* Kanban
* Controle de refações
* SLA
* Produtividade
* Equipes e Squads
* Controle operacional
* Relatórios operacionais
* Indicadores de desempenho

---

# Fora do Escopo

O TaskFloww não é um ERP financeiro.

Não implementar sem solicitação explícita:

* Financeiro
* Estoque
* Emissão fiscal
* Faturamento
* Módulo contábil
* Folha de pagamento
* Controle bancário

---

# Referência de Interface

A principal referência visual e funcional do projeto é o iClips.

Utilizar como inspiração:

* Navegação
* Fluxos operacionais
* Estrutura de cadastros
* Permissões
* Organização de módulos

Não copiar código, layout ou interface literalmente.

Utilizar apenas como referência funcional, estrutural e de experiência do usuário.

---

# Estado Atual do Projeto

## Fase 1

* Docker funcionando
* Next.js operacional
* FastAPI operacional
* PostgreSQL operacional
* Redis operacional

## Fase 2

* Shell Boxx criado
* Sidebar criada
* Header criado
* Dashboard inicial criado

## Fase 2.1

Estrutura inicial organizada em:

* `src/components/layout`
* `src/components/dashboard`

## Fase 2.2

Módulo de Usuários iniciado:

* Cadastro de usuários
* Perfis
* Permissões
* Endereços
* Informações complementares
* Histórico
* Estrutura preparada para multiempresa
* Estrutura preparada para auditoria

---

# Cadastro de Clientes

Referência funcional: iClips.

Fluxo previsto:

1. Informar CPF ou CNPJ.
2. Validar documento.
3. Buscar dados automaticamente (quando a integração estiver disponível).
4. Gerar código interno no formato `#0000`.
5. Gerar sigla automática do cliente.
6. Abrir cadastro completo.

Abas previstas:

* Dados
* Endereço
* Contatos
* Equipe
* Histórico

---

# Regras de Desenvolvimento

Sempre respeitar a fase atual do projeto.

Não criar funcionalidades fora do escopo da fase sem solicitação explícita.

Antes de alterar arquivos:

1. Ler `PROJECT_STATUS.md`.
2. Ler `CLAUDE.md`.
3. Analisar a estrutura atual do projeto.
4. Utilizar componentes já existentes sempre que possível.
5. Realizar alterações pequenas e incrementais.
6. Validar TypeScript.
7. Executar lint.
8. Executar build.
9. Exibir diff final.
10. Solicitar aprovação antes de aplicar alterações relevantes.

---

# Processo de Validação

Antes de aplicar qualquer alteração relevante:

1. Gerar arquivos em sandbox.
2. Validar TypeScript.
3. Validar imports.
4. Executar lint.
5. Executar build.
6. Exibir diff consolidado.
7. Solicitar aprovação.

Nunca aplicar alterações grandes diretamente no projeto sem validação prévia.

---

# Regras de Permissão

O sistema utilizará RBAC (Role Based Access Control).

Perfis previstos:

* SuperAdmin
* Admin
* Diretoria
* Gestor
* Operador
* Cliente

---

# Configurações

Configurações é uma área administrativa.

Não deve ser exibida para:

* Operador
* Cliente

Deve ser exibida para:

* SuperAdmin
* Admin
* Diretoria
* Gestor
* Usuários com permissão explícita

Enquanto não existir autenticação, as telas podem ser criadas normalmente, porém todas as decisões de interface devem considerar as futuras regras de permissão.

---

# Auditoria

O sistema deverá possuir futuramente um módulo de Auditoria.

Toda modelagem nova deve considerar:

* Usuário responsável
* Data e hora da alteração
* Histórico de alterações
* IP de origem
* Dispositivo de origem
* Logs de ações críticas

---

# Integrações Futuras

Planejadas para fases futuras:

* Importação de dados do iClips
* Inteligência Artificial integrada ao TaskFloww
* Relatórios avançados
* Dashboard executivo
* Automações
* APIs externas

Nenhuma dessas integrações deve ser implementada sem definição explícita da fase correspondente.
