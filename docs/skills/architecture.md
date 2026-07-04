# Architecture Skill

## Organização frontend

Usar Next.js App Router.

Estrutura esperada:

src/
├── app/
├── components/
│   ├── layout/
│   ├── dashboard/
│   ├── kanban/
│   ├── forms/
│   └── ui/
├── lib/
├── types/
└── hooks/

## Regras

- page.tsx deve ser simples.
- Componentes reutilizáveis ficam em src/components.
- Lógica auxiliar fica em src/lib.
- Tipos TypeScript ficam em src/types.
- Hooks ficam em src/hooks.
- Não misturar regra de negócio com componente visual.
- Não criar banco sem fase aprovada.
- Não criar autenticação sem fase aprovada.
