# CLAUDE.md - TaskFloww v2

## Projeto

TaskFloww v2 é uma reconstrução do TaskFlow com foco em interface moderna e arquitetura mais clara.

## Stack

Frontend:
- Next.js
- React
- TypeScript
- TailwindCSS
- dnd-kit

Backend:
- FastAPI
- Python
- SQLAlchemy
- PostgreSQL
- Redis

## Direção do produto

TaskFloww deve ser uma plataforma operacional para agências.

O objetivo é gerenciar:
- tarefas
- projetos
- workflow
- aprovações
- refações
- prazos
- produtividade
- relatórios operacionais

## O que NÃO fazer

Não transformar o sistema em ERP.

Não implementar agora:
- financeiro
- faturamento
- boletos
- notas fiscais
- DRE
- contas a pagar
- contas a receber
- contratos complexos

## Regra principal

Usar o projeto antigo apenas como referência de negócio.

Não copiar código Laravel/Blade.

A interface deve ser construída nativamente em React/Next.js.

## Design

Referências:
- Claude Design Boxx
- iClips apenas como referência de fluxo
- ClickUp
- Linear
- Asana

Objetivo:
interface SaaS premium, clara, compacta e operacional.

## Processo de trabalho

Antes de alterar código:
1. analisar arquivos relevantes;
2. explicar o plano;
3. listar arquivos que serão alterados;
4. aguardar aprovação.

Depois de alterar:
1. rodar build;
2. informar testes;
3. não fazer commit automático.
