# TaskFloww V2

Plataforma SaaS de gestão operacional multiempresa (agências, equipes de marketing,
comunicação e operações): tarefas, projetos, workflows, indicadores e produtividade.

## Projeto

- **Projeto atual e oficial:** `C:\@PROJETOS\taskfloww-v2` — todo desenvolvimento válido do
  TaskFloww V2 acontece aqui.
- **Projetos de referência (não desenvolver neles):**
  - `C:\@PROJETOS\taskflow` — leitura/base histórica.
  - `C:\@PROJETOS\flowe` — referência visual e de comportamento.
- Nunca modificar os projetos de referência como parte do desenvolvimento do TaskFloww V2.
  Se algo de lá precisar entrar aqui, é reescrito/adaptado neste repositório — não editado na
  origem.

## Stack (detectada no projeto, não presumida)

**Frontend** (`frontend/package.json`):
- Next.js 16.2.12 (App Router) + React 19.2.4
- TypeScript 5, Tailwind CSS 4
- `@dnd-kit/core` 6.3.1, `framer-motion` 12, `lucide-react`

**Backend** (`backend/requirements.txt`, `backend/.venv`):
- Python 3.12
- FastAPI 0.139.0 + Uvicorn 0.50.0
- SQLAlchemy 2.0.51 + Alembic 1.14.0
- Pydantic 2.13.4
- psycopg[binary] 3.2.3 (driver Postgres)
- pwdlib[argon2] (hash de senha), PyJWT (tokens)

**Infra:**
- PostgreSQL 16.4 (Docker, `backend/docker-compose.yml`, container `taskfloww-postgres`,
  porta 5433)
- Redis: mencionado como intenção de arquitetura, **não implementado ainda** — não está em
  `requirements.txt` nem referenciado em código. Não tratar como presente até que exista de
  fato.

## Princípios técnicos

Antes de alterar código, avaliar nesta ordem:

1. Segurança — a mudança abre alguma brecha de acesso?
2. Manutenção — fica claro para o próximo desenvolvedor por que isso existe?
3. Escalabilidade — funciona com 10 empresas? Com 10.000 registros?
4. Impacto de banco — precisa de migration? Quebra dado existente?
5. Impacto de autorização — quem ganha ou perde acesso a quê?
6. Compatibilidade com a arquitetura existente — segue os padrões já estabelecidos
   (repository → service → rota; escopo resolvido em `app/core/escopo.py`; etc.)?

Evitar bibliotecas desnecessárias. Evitar duplicação — reutilizar componentes/helpers
existentes antes de criar novos. Preferir soluções simples e testáveis a abstrações
antecipadas.

## Segurança e autorização

- Autorização relevante é sempre validada no **backend**. Nunca confiar apenas em esconder
  componente/menu no frontend — isso é UX, não segurança.
- Preservar isolamento de **empresa/tenant** em toda consulta (empresa vem do token, nunca de
  parâmetro do cliente sem validação).
- Preservar isolamento de **departamento/escopo** conforme a regra central resolvida em
  `app/core/escopo.py` — não reimplementar a lógica de Head/Atendimento/escopo em outro lugar.
- Minimizar exposição de dados: um endpoint que só precisa de um agregado não deve devolver a
  lista bruta; um payload não deve carregar campo que o consumidor não tem autorização de ver.

## Terminologia de perfis

Usar de forma consistente em código, comentários e conversas:

- **Usuário/Operador** — perfil de execução (`perfil_base = "operador"` no backend).
- **Gerente/Head** — gestão departamental. Não é um `perfil_base` — é uma relação
  (`Departamento.responsavel_usuario_id` ou `Usuario.lider_departamento`), resolvida
  centralmente em `app/core/escopo.py`.
- **Gestor** — gestão ampliada (`perfil_base = "gestor"`).
- **Admin/Dono** — administração superior (`perfil_base = "admin"`).

## Regra de horas

**Usuário/Operador** não deve visualizar:
- horas executadas, horas consumidas, horas estimadas;
- total acumulado / tempo agregado por usuário ou departamento;
- histórico temporal de sessões (início, fim, duração de sessões passadas);
- métricas de produtividade baseadas em tempo.

A interface desse perfil é orientada ao trabalho: tarefas, projetos, pauta, status, checklist,
prazos, prioridades, workflow, comentários, ações de iniciar/pausar/finalizar quando aplicável.

**Gerente/Head, Gestores e superiores autorizados** podem visualizar métricas temporais,
sempre dentro do escopo permitido (próprio departamento para Head; empresa para
Gestor/Admin) — nunca por ocultação de componente, sempre por checagem no backend.

## Fluxo de desenvolvimento

1. Desenvolver localmente.
2. Validar backend e frontend (ver checklist abaixo).
3. Revisar `git status`, `git diff` e os testes antes de organizar qualquer commit.
4. Organizar commits lógicos (um assunto por commit, não um commit gigante misturando
   funcionalidades independentes).
5. Push para o GitHub.
6. Só depois considerar deploy para ambiente remoto.

Não fazer alterações diretas em produção como fluxo normal.

## Banco e migrations

- Migrations são intencionais — nunca geradas "por garantia".
- Rodar sempre, antes de considerar uma etapa fechada: `alembic current`, `alembic heads`,
  `alembic check`.
- Não criar migration quando não há alteração de schema.
- Nunca editar uma migration já aplicada sem necessidade arquitetural explícita e decisão
  deliberada — preferir uma nova migration corretiva.

## Validação mínima antes de fechar uma etapa

Backend:

```powershell
pytest
alembic current
alembic heads
alembic check
```

Frontend:

```powershell
npx tsc --noEmit
npm run lint
npm run build
```

Também, antes de qualquer commit:

```powershell
git diff --check
```

## Versionamento

Este projeto tem sua própria configuração e seu próprio fluxo de versionamento — não depende
mais de `taskflow` nem de `flowe`, e não é necessário reconciliar histórico com essas pastas.
