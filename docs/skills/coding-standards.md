# Coding Standards

## Frontend

- Usar TypeScript.
- Usar componentes funcionais.
- Usar Tailwind.
- Usar App Router do Next.js.
- Não usar CSS inline, exceto cores específicas do design.
- Não colocar telas grandes diretamente em page.tsx.

## Componentes

Nomear componentes em PascalCase.

Exemplos:
- Sidebar.tsx
- Header.tsx
- DashboardView.tsx
- StatCard.tsx

## Imports

Usar alias quando possível:

import { Shell } from "@/components/layout/Shell";

## Validação

Depois de alterar frontend:

docker exec -it taskfloww_front npm run lint

Depois reiniciar:

docker restart taskfloww_front
