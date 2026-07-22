---
name: novo-cadastro
description: "Use ao criar qualquer novo módulo de frontend do TaskFloww (cadastro, tela de workflow, drawer de detalhe). Transforma as seções 'Estrutura obrigatória de um módulo' e 'Organização dos Cadastros' do CLAUDE.md em processo executável, seguindo o padrão real Página → View → Tabela → Drawer → Sections → hooks já usado em Clientes/Grupos de Clientes."
---

# /novo-cadastro

## Passo 0 — Consultar antes de gerar código (obrigatório)

1. Leia `/docker/taskfloww/CLAUDE.md` (raiz) inteiro, ao menos as seções "Estrutura do Frontend", "Estrutura obrigatória de um módulo", "Organização dos Cadastros", "Componentes UI", "Permissões".
2. Leia `frontend/AGENTS.md`.
3. Rode `graphify explain "<nome do módulo>"` e `graphify query "existe algum componente parecido com <módulo>"`. Se o Graphify apontar algo reaproveitável, use-o — nunca duplique.

Não pule este passo achando que "já sabe" o padrão — o padrão real usa **Drawer**, não o "Modal" que o texto do CLAUDE.md ainda menciona; confirme sempre no Graphify/código antes de assumir.

## Passo 1 — Confirmar escopo

Pergunte (ou infira do pedido do usuário): este módulo é só frontend (mock/hook local) ou precisa de backend real? Se precisar de backend, isso é um segundo fluxo — acione a skill `migracao-backend` / agente `backend-module-builder` em paralelo ou antes, conforme dependência.

## Passo 2 — Apresentar o plano

Liste os arquivos exatos a criar (veja estrutura abaixo) e espere aprovação explícita do usuário antes de escrever qualquer coisa — isso é regra do CLAUDE.md ("Fluxo de Desenvolvimento", passos 5-7), não uma sugestão.

## Passo 3 — Estrutura de arquivos (padrão confirmado, não o simplificado do texto)

```
src/app/configuracoes/<modulo>/page.tsx
src/components/<modulo>/
  <Modulo>View.tsx
  <Modulo>CreateDrawer.tsx
  <Modulo>Drawer.tsx
  <Modulo>DadosSection.tsx            (+ outras Sections conforme abas do domínio)
  <Modulo>FormFields.tsx
  use<Modulo>List.ts
  use<Modulo>Create.ts
  use<Modulo>.ts
src/types/<modulo>-domain.ts
src/types/<modulo>-api.ts
src/lib/<modulo>-api-mappers.ts
```

Use os templates de `.claude/templates/frontend/`, `.claude/templates/entity/` e `.claude/templates/drawer/` como base para cada arquivo — adapte nomes, nunca comece do zero se um template cobrir o caso.

Delegue a geração em si para o agente `module-builder`.

## Passo 4 — Pós-scaffold

- Adicionar ao menu correspondente.
- Adicionar ao hub de Configurações, se aplicável (checar visibilidade RBAC: não exibir para Operador/Cliente).
- Validar acesso direto à URL.

## Passo 5 — Handoff para validação

Nunca declare o módulo concluído sozinho. Acione a skill `validar-modulo` (ou o agente `qa-validator`) e só reporte sucesso se todos os itens do checklist passarem.
