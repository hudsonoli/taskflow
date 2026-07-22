---
name: migracao-backend
description: "Use ao adicionar um novo módulo de backend do TaskFloww (model, schema, repository, service, routes, migração Alembic). Encodes as regras obrigatórias de modelagem do CLAUDE.md e o padrão real confirmado em Cliente/WorkflowEtapa (exceções tipadas, DomainEventPublisher, escopo por empresa_id)."
---

# /migracao-backend

## Passo 0 — Consultar antes de gerar código (obrigatório)

1. Leia `/docker/taskfloww/CLAUDE.md` (raiz) — seção "Regras obrigatórias de modelagem" e "Fora do Escopo".
2. Leia `/docker/taskfloww/AGENTS.md` — regras de edição (nada de `sed`/`perl`/scripts grandes sem autorização explícita, patches pequenos e auditáveis, parar se um patch falhar em vez de tentar várias correções em sequência).
3. Rode `graphify explain "<entidade>"` e, se a entidade se relaciona com outra existente, `graphify path "<entidade nova>" "<entidade existente>"` — para não redesenhar uma FK/relação que já existe em outro lugar do domínio.

## Passo 1 — Confirmar modelagem obrigatória

Antes de desenhar colunas, confirme:
- `id` (str(36), PK), `empresa_id` (FK obrigatória para `empresas.id`), `created_at`/`updated_at` (DateTime timezone=True).
- `clienteId`/`usuarioId` quando aplicável ao domínio.
- Toda relação por ID — nunca nome como chave.
- Campos técnicos gerados (ex.: `codigo_interno`) nunca entram no schema de entrada (`extra="forbid"` no Pydantic garante isso).

## Passo 2 — Apresentar o plano

Liste model, schema, repository, service (com as exceções tipadas que ele vai expor), rotas, e o esboço da migração. Espere aprovação antes de escrever.

## Passo 3 — Estrutura de arquivos (padrão confirmado em `cliente.py`/`workflow_etapa_service.py`)

```
backend/app/models/<entidade>.py
backend/app/schemas/<entidade>.py
backend/app/repositories/<entidade>_repository.py
backend/app/services/<entidade>_service.py
backend/app/api/routes/<entidade>.py
backend/alembic/versions/<timestamp>_<slug>_cria_tabela_<entidade>.py
```

Use os templates de `.claude/templates/backend/` como base (e `.claude/templates/workflow/` se a entidade fizer parte de um motor de estados com transições, como Etapa/Transição de Workflow).

Delegue a geração em si para o agente `backend-module-builder`.

## Passo 4 — Migração

Gere a migração Alembic espelhando o model 1:1 (colunas, constraints, índices). **Nunca rode `alembic upgrade` automaticamente** — apresente a migração para revisão do usuário antes de qualquer aplicação.

## Passo 5 — Handoff para validação

Acione a skill `validar-modulo` (ou o agente `qa-validator`) para rodar testes/lint do backend antes de reportar conclusão. Nunca faça commit.
