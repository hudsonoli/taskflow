# Reformulação do Fluxo de Criação de Tarefas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer a Tarefa nascer completamente configurada (Workflow → Etapa inicial → Departamento derivado → Responsável principal → Colaboradores), resolver o nome do Cliente na listagem, adicionar visualização Kanban por Workflow, e reduzir "Visualizar" a consulta + pequenas ações.

**Architecture:** Ver `docs/superpowers/specs/2026-07-22-tarefas-creation-flow-design.md` (spec aprovado). Refinamento descoberto durante o detalhamento do plano: a regra de RBAC por status (§6 do spec) vive em `TarefaService.associar_workflow` (endpoint dedicado já existente, `POST /tarefas/{id}/workflow/associar`), não em `update_tarefa` — é a operação que já existe especificamente para trocar Workflow/Etapa, e ganha evento (`TAREFA_ATUALIZADA`, reaproveitado) que hoje não publica nenhum. No frontend, os campos de Workflow/Etapa/Responsável/Colaboradores entram em `TarefaFormFields.tsx` (componente já compartilhado entre criação e edição) — mas a **reatribuição** de Workflow em modo edição continua usando `TarefaWorkflowSelectModal.tsx` (já existe), só realocado de dentro do Peek para dentro do Edit.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + Pydantic (backend), Next.js + React + TypeScript (frontend), pytest (backend tests), `node --test` (frontend tests, roda em `docker compose exec taskfloww_front npm test`).

## Global Constraints

- Toda entidade tem `id`/`empresaId`/`createdAt`/`updatedAt`; toda relação é por ID, nunca por nome (CLAUDE.md).
- Nenhum evento de domínio novo — reaproveitar `TAREFA_CRIADA`, `TAREFA_ATUALIZADA`, `TAREFA_WORKFLOW_ETAPA_ALTERADA` (spec §10).
- Checklist, campos obrigatórios por etapa, regras de aprovação, documentos, automações, notificações: **fora de escopo**. Só preparar o ponto de extensão (`_aplicar_template_etapa`), nunca implementar esses recursos agora (spec §5/§12).
- Departamento responsável nunca é campo próprio da Tarefa — sempre derivado de `workflow_etapa.departamento_id` (spec §4).
- Nunca rodar `alembic upgrade` automaticamente — gerar a migração e apresentar para revisão antes de aplicar (AGENTS.md / `.claude/skills/migracao-backend`).
- Validar sempre com `docker compose exec taskfloww_api pytest` (backend) e `docker compose exec taskfloww_front npm run typecheck / lint / test / build` (frontend) — nomes de serviço confirmados em `docker-compose.yml` (`taskfloww_api`, `taskfloww_front`).
- Nunca commitar sem aprovação explícita do usuário para cada commit.

---

## File Structure

**Backend (novo/alterado):**
- `backend/app/models/tarefa.py` — `+responsavel_principal_usuario_id`
- `backend/app/models/tarefa_colaborador.py` — **novo**, tabela de vínculo N:N Tarefa↔Usuario
- `backend/alembic/versions/<timestamp>_<slug>_adiciona_responsaveis_tarefa.py` — **novo**
- `backend/app/repositories/tarefa_colaborador_repository.py` — **novo**
- `backend/app/repositories/tarefa_repository.py` — join com Cliente, `cliente_nome_exibicao`
- `backend/app/schemas/tarefa.py` — `TarefaCreate`/`TarefaResponse`/`TarefaWorkflowAssociar` (RBAC não muda schema, mas o service precisa do perfil do ator)
- `backend/app/services/tarefa_service.py` — `create_tarefa`, novo `_aplicar_template_etapa`, novo `_selecionar_etapa_inicial`, `associar_workflow` (regra de RBAC + evento), `to_response`
- `backend/app/api/routes/tarefas.py` — `create_tarefa` (nenhuma mudança de payload, `TarefaCreate` já muda), novos endpoints de colaboradores, `handle_tarefa_error` (novo erro)

**Frontend (novo/alterado):**
- `frontend/src/types/tarefa-api.ts`, `frontend/src/types/tarefa-domain.ts` — novos campos
- `frontend/src/lib/tarefa-api-mappers.ts` — propaga novos campos
- `frontend/src/components/tarefas/tarefa-form-value.ts` — `TarefaFormValue` ganha 4 campos
- `frontend/src/components/tarefas/TarefaFormFields.tsx` — seção Workflow/Etapa/Responsável/Colaboradores
- `frontend/src/components/tarefas/TarefaCreateDrawer.tsx` — payload de criação
- `frontend/src/components/tarefas/TarefaEditDrawer.tsx` — botão "Alterar Workflow" (relocado do Peek), responsável/colaboradores no PATCH
- `frontend/src/components/tarefas/TarefaWorkflowSection.tsx` — reduzido a leitura + avançar etapa, remove branch morto de evento
- `frontend/src/components/tarefas/TarefaPeekDrawer.tsx` — mostra responsáveis/departamento/SLA
- `frontend/src/components/tarefas/TarefasView.tsx` — nome do Cliente, toggle Lista/Kanban
- `frontend/src/components/tarefas/TarefaKanbanBoard.tsx` — **novo**
- `frontend/src/components/tarefas/useTarefaColaboradores.ts` — **novo**

---

## PARTE 1 — BACKEND

### Task 1: Migração — responsável principal + tabela de colaboradores

**Files:**
- Create: `backend/alembic/versions/20260723_1a27_adiciona_responsaveis_tarefa.py`
- Test: `backend/tests/test_tarefa_model.py` (arquivo já existe — confirmar com `ls backend/tests/test_tarefa*.py`; se não existir, criar `backend/tests/test_tarefa_colaborador_model.py`)

**Interfaces:**
- Produces: coluna `tarefas.responsavel_principal_usuario_id` (nullable, FK `usuarios.id`, `ondelete=SET NULL`); tabela `tarefa_colaboradores` (`id`, `empresa_id`, `tarefa_id`, `usuario_id`, `created_at`), unique `(tarefa_id, usuario_id)`.

- [ ] **Step 1: Rodar `alembic heads` para obter o `down_revision` correto**

```bash
docker compose exec taskfloww_api alembic heads
```
Anote o revision id retornado — será o `down_revision` da nova migração.

- [ ] **Step 2: Escrever a migração**

```python
"""adiciona responsaveis tarefa

Revision ID: 20260723_1a27
Revises: <REVISION_ID_DO_HEADS_ACIMA>
Create Date: 2026-07-23 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_1a27"
down_revision: Union[str, None] = "<REVISION_ID_DO_HEADS_ACIMA>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tarefas",
        sa.Column("responsavel_principal_usuario_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_tarefas_responsavel_principal_usuario_id",
        "tarefas",
        "usuarios",
        ["responsavel_principal_usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tarefas_responsavel_principal_usuario_id",
        "tarefas",
        ["responsavel_principal_usuario_id"],
        unique=False,
    )

    op.create_table(
        "tarefa_colaboradores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("tarefa_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["tarefa_id"], ["tarefas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tarefa_id", "usuario_id", name="uq_tarefa_colaboradores_tarefa_usuario"),
    )
    op.create_index("ix_tarefa_colaboradores_empresa_id", "tarefa_colaboradores", ["empresa_id"], unique=False)
    op.create_index("ix_tarefa_colaboradores_tarefa_id", "tarefa_colaboradores", ["tarefa_id"], unique=False)
    op.create_index("ix_tarefa_colaboradores_usuario_id", "tarefa_colaboradores", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tarefa_colaboradores_usuario_id", table_name="tarefa_colaboradores")
    op.drop_index("ix_tarefa_colaboradores_tarefa_id", table_name="tarefa_colaboradores")
    op.drop_index("ix_tarefa_colaboradores_empresa_id", table_name="tarefa_colaboradores")
    op.drop_table("tarefa_colaboradores")

    op.drop_index("ix_tarefas_responsavel_principal_usuario_id", table_name="tarefas")
    op.drop_constraint("fk_tarefas_responsavel_principal_usuario_id", "tarefas", type_="foreignkey")
    op.drop_column("tarefas", "responsavel_principal_usuario_id")
```

- [ ] **Step 3: Apresentar a migração para revisão do usuário — NÃO rodar `alembic upgrade` sozinho.**

Pare aqui e peça confirmação explícita antes de aplicar. Só prossiga para a Task 2 depois de aprovação.

---

### Task 2: Models — `Tarefa.responsavel_principal_usuario_id` + `TarefaColaborador`

**Files:**
- Modify: `backend/app/models/tarefa.py`
- Create: `backend/app/models/tarefa_colaborador.py`
- Modify: `backend/app/models/__init__.py` (registrar o novo model, mesmo padrão dos demais)
- Test: `backend/tests/test_tarefa_model.py`

**Interfaces:**
- Consumes: migração da Task 1 já aplicada.
- Produces: `Tarefa.responsavel_principal_usuario_id: str | None`; classe `TarefaColaborador` (`id`, `empresa_id`, `tarefa_id`, `usuario_id`, `created_at`).

- [ ] **Step 1: Escrever o teste (falha porque a coluna/model ainda não existe)**

Em `backend/tests/test_tarefa_model.py`, adicionar:

```python
def test_responsavel_principal_usuario_id_aceita_usuario_e_pode_ser_nulo(session_factory):
    emp = persist(session_factory, empresa())
    usuario = persist(session_factory, make_usuario(emp.id))
    tarefa_com_responsavel = persist(session_factory, tarefa(emp.id, responsavel_principal_usuario_id=usuario.id))
    tarefa_sem_responsavel = persist(session_factory, tarefa(emp.id, responsavel_principal_usuario_id=None))

    assert tarefa_com_responsavel.responsavel_principal_usuario_id == usuario.id
    assert tarefa_sem_responsavel.responsavel_principal_usuario_id is None
```

(Use os helpers `persist`, `empresa`, `tarefa`, `make_usuario` já existentes em `backend/tests/conftest.py`/`test_tarefa_model.py` — conferir os nomes exatos com `grep -n "^def make_usuario\|^def tarefa(" backend/tests/conftest.py backend/tests/test_tarefa_model.py` antes de escrever, e ajustar a chamada para o nome real.)

- [ ] **Step 2: Rodar o teste, confirmar que falha**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_model.py -k responsavel_principal -v
```
Esperado: `TypeError: 'responsavel_principal_usuario_id' is an invalid keyword argument for Tarefa` (ou erro equivalente de coluna inexistente).

- [ ] **Step 3: Adicionar a coluna ao model**

Em `backend/app/models/tarefa.py`, dentro de `__table_args__`, adicionar o índice:

```python
        Index("ix_tarefas_workflow_etapa_id", "workflow_etapa_id"),
        Index("ix_tarefas_responsavel_principal_usuario_id", "responsavel_principal_usuario_id"),
```

E logo abaixo de `workflow_etapa_id`, adicionar a coluna e o relationship:

```python
    workflow_etapa_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_etapas.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Responsável principal (reformulação do fluxo de criação) — sempre
    # opcional, mesmo padrão de criada_por_usuario_id/inativado_por_usuario_id.
    # Departamento responsável NÃO é campo aqui: é sempre derivado de
    # workflow_etapa.departamento_id (ver TarefaService._aplicar_template_etapa).
    responsavel_principal_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
```

E no bloco de `relationship`:

```python
    responsavel_principal_usuario = relationship("Usuario", foreign_keys=[responsavel_principal_usuario_id])
```

- [ ] **Step 4: Criar `TarefaColaborador`**

```python
# backend/app/models/tarefa_colaborador.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TarefaColaborador(Base):
    __tablename__ = "tarefa_colaboradores"
    __table_args__ = (
        UniqueConstraint("tarefa_id", "usuario_id", name="uq_tarefa_colaboradores_tarefa_usuario"),
        Index("ix_tarefa_colaboradores_empresa_id", "empresa_id"),
        Index("ix_tarefa_colaboradores_tarefa_id", "tarefa_id"),
        Index("ix_tarefa_colaboradores_usuario_id", "usuario_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Denormalizado a partir de tarefa.empresa_id — mesmo padrão já usado
    # por UsuarioEquipe/UsuarioDepartamento/WorkflowEtapa (sub-entidades
    # vinculadas a uma entidade "pai").
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    tarefa_id: Mapped[str] = mapped_column(ForeignKey("tarefas.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    empresa = relationship("Empresa")
    tarefa = relationship("Tarefa")
    usuario = relationship("Usuario")
```

- [ ] **Step 5: Registrar o model em `backend/app/models/__init__.py`**

Seguir o padrão exato já usado para os demais models nesse arquivo (import + inclusão na lista/`__all__`, o que já existir lá — conferir com `cat backend/app/models/__init__.py` antes de editar).

- [ ] **Step 6: Rodar o teste, confirmar que passa**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_model.py -k responsavel_principal -v
```
Esperado: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/tarefa.py backend/app/models/tarefa_colaborador.py backend/app/models/__init__.py backend/tests/test_tarefa_model.py
git commit -m "feat(tarefas): adiciona responsavel_principal_usuario_id e tabela tarefa_colaboradores"
```

---

### Task 3: `TarefaColaboradorRepository`

**Files:**
- Create: `backend/app/repositories/tarefa_colaborador_repository.py`
- Test: `backend/tests/test_tarefa_colaborador_repository.py` (novo)

**Interfaces:**
- Consumes: `TarefaColaborador` (Task 2).
- Produces: `TarefaColaboradorRepository.create(db, vinculo) -> TarefaColaborador`; `.list_by_tarefa(db, *, empresa_id, tarefa_id) -> list[TarefaColaborador]`; `.get_by_tarefa_usuario(db, *, empresa_id, tarefa_id, usuario_id) -> TarefaColaborador | None`; `.delete(db, vinculo) -> None`.

- [ ] **Step 1: Escrever o teste (falha — módulo não existe)**

```python
# backend/tests/test_tarefa_colaborador_repository.py
from uuid import uuid4

from app.models.tarefa_colaborador import TarefaColaborador
from app.repositories.tarefa_colaborador_repository import TarefaColaboradorRepository
from tests.conftest import empresa, make_usuario, persist, tarefa


def make_colaborador(empresa_id: str, tarefa_id: str, usuario_id: str) -> TarefaColaborador:
    from datetime import datetime, timezone

    return TarefaColaborador(
        id=str(uuid4()),
        empresa_id=empresa_id,
        tarefa_id=tarefa_id,
        usuario_id=usuario_id,
        created_at=datetime.now(timezone.utc),
    )


def test_create_list_get_delete(session_factory):
    emp = persist(session_factory, empresa())
    t = persist(session_factory, tarefa(emp.id))
    usuario_a = persist(session_factory, make_usuario(emp.id))
    usuario_b = persist(session_factory, make_usuario(emp.id))
    repository = TarefaColaboradorRepository()

    with session_factory() as db:
        repository.create(db, make_colaborador(emp.id, t.id, usuario_a.id))
        repository.create(db, make_colaborador(emp.id, t.id, usuario_b.id))
        db.commit()

    with session_factory() as db:
        vinculos = repository.list_by_tarefa(db, empresa_id=emp.id, tarefa_id=t.id)
        assert {v.usuario_id for v in vinculos} == {usuario_a.id, usuario_b.id}

        encontrado = repository.get_by_tarefa_usuario(db, empresa_id=emp.id, tarefa_id=t.id, usuario_id=usuario_a.id)
        assert encontrado is not None

        repository.delete(db, encontrado)
        db.commit()

    with session_factory() as db:
        vinculos = repository.list_by_tarefa(db, empresa_id=emp.id, tarefa_id=t.id)
        assert {v.usuario_id for v in vinculos} == {usuario_b.id}
```

Antes de usar `make_usuario`/`tarefa`, confirme os nomes reais dos helpers de `backend/tests/conftest.py` e `test_tarefa_model.py` com `grep -n "^def "`. Ajuste as chamadas para os nomes/assinaturas reais.

- [ ] **Step 2: Rodar, confirmar falha (`ModuleNotFoundError`)**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_colaborador_repository.py -v
```

- [ ] **Step 3: Implementar**

```python
# backend/app/repositories/tarefa_colaborador_repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tarefa_colaborador import TarefaColaborador


class TarefaColaboradorRepository:
    def create(self, db: Session, vinculo: TarefaColaborador) -> TarefaColaborador:
        db.add(vinculo)
        db.flush()
        return vinculo

    def list_by_tarefa(self, db: Session, *, empresa_id: str, tarefa_id: str) -> list[TarefaColaborador]:
        statement = (
            select(TarefaColaborador)
            .where(TarefaColaborador.empresa_id == empresa_id, TarefaColaborador.tarefa_id == tarefa_id)
            .order_by(TarefaColaborador.created_at.asc())
        )
        return list(db.scalars(statement).all())

    def get_by_tarefa_usuario(
        self, db: Session, *, empresa_id: str, tarefa_id: str, usuario_id: str
    ) -> TarefaColaborador | None:
        statement = select(TarefaColaborador).where(
            TarefaColaborador.empresa_id == empresa_id,
            TarefaColaborador.tarefa_id == tarefa_id,
            TarefaColaborador.usuario_id == usuario_id,
        )
        return db.scalars(statement).first()

    def delete(self, db: Session, vinculo: TarefaColaborador) -> None:
        db.delete(vinculo)
        db.flush()
```

- [ ] **Step 4: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_colaborador_repository.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/tarefa_colaborador_repository.py backend/tests/test_tarefa_colaborador_repository.py
git commit -m "feat(tarefas): adiciona TarefaColaboradorRepository"
```

---

### Task 4: `TarefaRepository` — resolver nome do Cliente

**Files:**
- Modify: `backend/app/repositories/tarefa_repository.py`
- Test: `backend/tests/test_tarefa_repository.py` (confirmar nome exato do arquivo com `ls backend/tests/ | grep tarefa_repo`)

**Interfaces:**
- Consumes: `Cliente` model (já existe, campos `nome_fantasia`/`razao_social`/`nome`).
- Produces: `TarefaRepository.list(...)` e `.get_by_id(...)` continuam retornando `Tarefa`, mas o objeto passa a ter o atributo transitório `cliente_nome_exibicao` populado (não-persistido —设置 em Python após a query, não uma coluna nova).

**Decisão de implementação**: em vez de uma coluna computada SQL complexa, o repository faz o `join` com `Cliente`, monta um dict `{tarefa_id: nome_exibicao}` a partir do resultado, e o **service** (Task 6) atribui `tarefa.cliente_nome_exibicao = nome` a cada `Tarefa` antes de `to_response`. `cliente_nome_exibicao` é um atributo Python solto no objeto SQLAlchemy (não mapeado, não persistido) — igual ao padrão já usado para campos calculados que só existem na resposta.

- [ ] **Step 1: Escrever o teste (falha — atributo/comportamento não existe)**

```python
def test_list_resolve_cliente_nome_exibicao(session_factory):
    emp = persist(session_factory, empresa())
    cliente_com_fantasia = persist(session_factory, cliente(emp.id, nome_fantasia="Bretas", razao_social="Bretas Ltda"))
    cliente_so_razao = persist(session_factory, cliente(emp.id, nome_fantasia=None, razao_social="Alfa Comercio Ltda"))
    persist(session_factory, tarefa(emp.id, cliente_id=cliente_com_fantasia.id, titulo="Tarefa A"))
    persist(session_factory, tarefa(emp.id, cliente_id=cliente_so_razao.id, titulo="Tarefa B"))
    persist(session_factory, tarefa(emp.id, cliente_id=None, titulo="Tarefa C"))

    repository = TarefaRepository()
    with session_factory() as db:
        resultados = repository.list(db, empresa_id=emp.id)
        por_titulo = {t.titulo: t for t in resultados}

    assert por_titulo["Tarefa A"].cliente_nome_exibicao == "Bretas"
    assert por_titulo["Tarefa B"].cliente_nome_exibicao == "Alfa Comercio Ltda"
    assert por_titulo["Tarefa C"].cliente_nome_exibicao is None
```

Confirmar nomes exatos dos helpers `cliente(...)`/`tarefa(...)` em `backend/tests/conftest.py`/arquivos de teste de Cliente/Tarefa antes de usar — usar os parâmetros reais (`nome_fantasia`, `razao_social`, `cliente_id`, `titulo`).

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_repository.py -k cliente_nome_exibicao -v
```
Esperado: `AttributeError: 'Tarefa' object has no attribute 'cliente_nome_exibicao'`.

- [ ] **Step 3: Implementar o join no repository**

Abrir `backend/app/repositories/tarefa_repository.py`, localizar o método `list` (linha ~50) e o `get_by_id`. Adicionar no topo do arquivo:

```python
from sqlalchemy import func, or_, outerjoin, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.tarefa import Tarefa
```

(ajustar imports existentes em vez de duplicar — conferir o topo real do arquivo antes de editar.)

Adicionar um método privado reaproveitado por `list` e `get_by_id`:

```python
    def _cliente_nome_exibicao_expr(self):
        return func.coalesce(Cliente.nome_fantasia, Cliente.razao_social, Cliente.nome)

    def _aplicar_cliente_nome_exibicao(self, db: Session, tarefas: list[Tarefa]) -> list[Tarefa]:
        cliente_ids = {t.cliente_id for t in tarefas if t.cliente_id is not None}
        if not cliente_ids:
            for t in tarefas:
                t.cliente_nome_exibicao = None
            return tarefas

        statement = select(Cliente.id, self._cliente_nome_exibicao_expr()).where(Cliente.id.in_(cliente_ids))
        nomes = {row[0]: row[1] for row in db.execute(statement).all()}
        for t in tarefas:
            t.cliente_nome_exibicao = nomes.get(t.cliente_id) if t.cliente_id else None
        return tarefas
```

No método `list(...)`, antes do `return list(db.scalars(statement).all())`, trocar por:

```python
        tarefas = list(db.scalars(statement).all())
        return self._aplicar_cliente_nome_exibicao(db, tarefas)
```

No método `get_by_id(...)`, antes do `return`, trocar:

```python
        tarefa = db.scalars(statement).first()
        if tarefa is not None:
            self._aplicar_cliente_nome_exibicao(db, [tarefa])
        return tarefa
```

(Ler o corpo real de `get_by_id`/`list` primeiro com `sed -n '1,90p' backend/app/repositories/tarefa_repository.py` para adaptar o nome exato das variáveis locais — o esqueleto acima assume `statement`/`db.scalars(statement)`, mesmo padrão de todos os outros repositories já lidos neste projeto.)

- [ ] **Step 4: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_repository.py -k cliente_nome_exibicao -v
```

- [ ] **Step 5: Rodar a suíte completa do repository para checar que nada quebrou**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_repository.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/tarefa_repository.py backend/tests/test_tarefa_repository.py
git commit -m "feat(tarefas): resolve nome de exibicao do Cliente na listagem/detalhe"
```

---

### Task 5: Schemas — `TarefaCreate`, `TarefaResponse`, erro de reassociação

**Files:**
- Modify: `backend/app/schemas/tarefa.py`
- Test: `backend/tests/test_tarefa_model.py` (schemas testados via `model_validate`, mesmo padrão de `test_documento_mascarado_e_normalizado_pelo_schema` em `test_cliente_model.py`)

**Interfaces:**
- Produces: `TarefaCreate.workflow_id: UUID | None`, `.workflow_etapa_id: UUID | None`, `.responsavel_principal_usuario_id: UUID | None`, `.colaboradores_usuario_ids: list[UUID]` (default `[]`); `TarefaResponse.responsavel_principal_usuario_id: str | None`, `.cliente_nome_exibicao: str | None`, `.departamento_id: str | None` (derivado, só leitura), `.sla_horas_esperado: int | None` (derivado, só leitura).

- [ ] **Step 1: Escrever o teste**

```python
def test_tarefa_create_aceita_workflow_etapa_responsaveis(session_factory):
    payload = {
        "empresaId": str(uuid4()),
        "origemIdentificacao": "taskfloww",
        "titulo": "Campanha institucional",
        "workflowId": str(uuid4()),
        "workflowEtapaId": str(uuid4()),
        "responsavelPrincipalUsuarioId": str(uuid4()),
        "colaboradoresUsuarioIds": [str(uuid4()), str(uuid4())],
    }
    tarefa = TarefaCreate.model_validate(payload)

    assert tarefa.workflow_id is not None
    assert tarefa.workflow_etapa_id is not None
    assert tarefa.responsavel_principal_usuario_id is not None
    assert len(tarefa.colaboradores_usuario_ids) == 2


def test_tarefa_create_workflow_etapa_responsaveis_sao_opcionais():
    payload = {
        "empresaId": str(uuid4()),
        "origemIdentificacao": "taskfloww",
        "titulo": "Tarefa avulsa",
    }
    tarefa = TarefaCreate.model_validate(payload)

    assert tarefa.workflow_id is None
    assert tarefa.workflow_etapa_id is None
    assert tarefa.responsavel_principal_usuario_id is None
    assert tarefa.colaboradores_usuario_ids == []
```

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_model.py -k "aceita_workflow_etapa_responsaveis or opcionais" -v
```
Esperado: `pydantic.ValidationError: ... Extra inputs are not permitted` ou `AttributeError`.

- [ ] **Step 3: Editar `TarefaCreate`**

Abrir `backend/app/schemas/tarefa.py`. Dentro de `class TarefaCreate(BaseModel)`, logo após `prazo: datetime | None = None`, adicionar:

```python
    # Reformulação do fluxo de criação (Fase pós-12B): Workflow/Etapa e
    # responsáveis nascem junto com a Tarefa — nunca mais só via
    # associar_workflow (endpoint separado, mantido só para reatribuição
    # pós-criação, com regra de perfil por status — ver TarefaService).
    workflow_id: UUID | None = Field(default=None, alias="workflowId")
    workflow_etapa_id: UUID | None = Field(default=None, alias="workflowEtapaId")
    responsavel_principal_usuario_id: UUID | None = Field(default=None, alias="responsavelPrincipalUsuarioId")
    colaboradores_usuario_ids: list[UUID] = Field(default_factory=list, alias="colaboradoresUsuarioIds")
```

- [ ] **Step 4: Editar `TarefaResponse`**

Dentro de `class TarefaResponse(BaseModel)`, logo após `workflow_etapa_id: str | None = Field(default=None, alias="workflowEtapaId")`, adicionar:

```python
    responsavel_principal_usuario_id: str | None = Field(default=None, alias="responsavelPrincipalUsuarioId")
    # Nunca persistidos na Tarefa — sempre derivados no momento da
    # resposta (ver TarefaService.to_response): departamento vem de
    # workflow_etapa.departamento_id, sla_horas_esperado de
    # workflow_etapa.tempo_esperado_horas. Somente leitura.
    departamento_id: str | None = Field(default=None, alias="departamentoId")
    sla_horas_esperado: int | None = Field(default=None, alias="slaHorasEsperado")
    cliente_nome_exibicao: str | None = Field(default=None, alias="clienteNomeExibicao")
```

- [ ] **Step 5: Adicionar o erro de reassociação (usado na Task 7)**

No topo do arquivo, junto aos outros tipos exportados (ou em `tarefa_service.py`, junto aos demais `TarefaInvalid*Error` — usar o mesmo arquivo/local dos outros erros de `TarefaService`, `backend/app/services/tarefa_service.py`, não em `schemas/tarefa.py`):

```python
class TarefaWorkflowReassociacaoNaoPermitidaError(ValueError):
    pass
```

(Este passo é só a declaração da classe — a lógica que a usa entra na Task 7.)

- [ ] **Step 6: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_model.py -k "aceita_workflow_etapa_responsaveis or opcionais" -v
```

- [ ] **Step 7: Rodar toda a suíte de schema de Tarefa**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_model.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/tarefa.py backend/tests/test_tarefa_model.py
git commit -m "feat(tarefas): schema aceita workflow/etapa/responsaveis na criacao"
```

---

### Task 6: Service — `create_tarefa` aplica Workflow/Etapa/Template/Responsáveis

**Files:**
- Modify: `backend/app/services/tarefa_service.py`
- Test: `backend/tests/test_tarefa_workflow_integracao.py` (já existe — adicionar casos aqui, é o arquivo dedicado a integração Tarefa↔Workflow)

**Interfaces:**
- Consumes: `TarefaCreate` (Task 5), `WorkflowEtapaRepository.get_by_id`/`.list` (já existem — confirmar assinatura exata com `grep -n "def " backend/app/repositories/workflow_etapa_repository.py`), `TarefaColaboradorRepository` (Task 3).
- Produces: `TarefaService._selecionar_etapa_inicial(db, workflow_id) -> WorkflowEtapa | None`; `TarefaService._aplicar_template_etapa(etapa) -> dict`; `create_tarefa` grava `workflow_id`/`workflow_etapa_id`/`responsavel_principal_usuario_id` na Tarefa e os vínculos de colaborador.

- [ ] **Step 1: Escrever o teste — etapa inicial automática**

```python
def test_create_tarefa_com_workflow_seleciona_etapa_de_menor_ordem_automaticamente(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    workflow = persist(client.session_factory, make_workflow(empresa.id))
    etapa_2 = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=2, nome="Revisão"))
    etapa_1 = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=1, nome="Briefing"))

    response = client.post(
        "/tarefas",
        json={
            "empresaId": empresa.id,
            "origemIdentificacao": "taskfloww",
            "titulo": "Campanha institucional",
            "workflowId": workflow.id,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["workflowId"] == workflow.id
    assert body["workflowEtapaId"] == etapa_1.id
    assert body["departamentoId"] == etapa_1.departamento_id


def test_create_tarefa_com_workflow_e_etapa_explicita_respeita_a_escolha(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    workflow = persist(client.session_factory, make_workflow(empresa.id))
    etapa_1 = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=1, nome="Briefing"))
    etapa_2 = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=2, nome="Revisão"))

    response = client.post(
        "/tarefas",
        json={
            "empresaId": empresa.id,
            "origemIdentificacao": "taskfloww",
            "titulo": "Campanha institucional",
            "workflowId": workflow.id,
            "workflowEtapaId": etapa_2.id,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.json()
    assert response.json()["workflowEtapaId"] == etapa_2.id


def test_create_tarefa_com_responsavel_e_colaboradores(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    responsavel = persist(client.session_factory, make_usuario(empresa.id))
    colaborador_1 = persist(client.session_factory, make_usuario(empresa.id))
    colaborador_2 = persist(client.session_factory, make_usuario(empresa.id))

    response = client.post(
        "/tarefas",
        json={
            "empresaId": empresa.id,
            "origemIdentificacao": "taskfloww",
            "titulo": "Campanha institucional",
            "responsavelPrincipalUsuarioId": responsavel.id,
            "colaboradoresUsuarioIds": [colaborador_1.id, colaborador_2.id],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["responsavelPrincipalUsuarioId"] == responsavel.id

    colaboradores = TarefaColaboradorRepository().list_by_tarefa(
        client.session_factory().begin().session, empresa_id=empresa.id, tarefa_id=body["id"]
    )
    assert {c.usuario_id for c in colaboradores} == {colaborador_1.id, colaborador_2.id}
```

Confirmar nomes reais de `make_workflow`, `make_workflow_etapa` em `backend/tests/test_tarefa_workflow_integracao.py`/`test_workflow_etapa.py` (`grep -n "^def make_workflow"`) e ajustar os parâmetros de fato aceitos (ex.: `departamento_id`) antes de rodar.

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py -k "etapa_de_menor_ordem or etapa_explicita or responsavel_e_colaboradores" -v
```
Esperado: `body["workflowId"]` vem `None` (campo ainda ignorado pelo service) ou `AssertionError` no responsavel/colaboradores.

- [ ] **Step 3: Implementar em `TarefaService`**

Adicionar aos imports do topo:

```python
from app.models.tarefa_colaborador import TarefaColaborador
from app.models.workflow_etapa import WorkflowEtapa
from app.repositories.tarefa_colaborador_repository import TarefaColaboradorRepository
```

No `__init__`, adicionar o parâmetro e atribuição (mesmo padrão dos demais repositories):

```python
        tarefa_colaborador_repository: TarefaColaboradorRepository | None = None,
```
```python
        self.tarefa_colaborador_repository = tarefa_colaborador_repository or TarefaColaboradorRepository()
```

Adicionar os dois métodos novos, próximos a `_ensure_workflow_associacao_valida`:

```python
    def _selecionar_etapa_inicial(self, db: Session, workflow_id: str) -> WorkflowEtapa | None:
        """
        Etapa de menor `ordem` do Workflow — usada quando workflowId é
        informado na criação sem workflowEtapaId explícito. Mesma regra
        tanto para quem cria pela UI (que já pré-seleciona) quanto para
        quem cria via API direta (esta é a rede de segurança).
        """
        etapas = self.workflow_etapa_repository.list(db, workflow_id=workflow_id, empresa_id=None, limit=1, offset=0)
        return etapas[0] if etapas else None

    def _aplicar_template_etapa(self, etapa: WorkflowEtapa | None) -> dict:
        """
        Ponto de extensão único para tudo que uma WorkflowEtapa "empresta"
        à Tarefa na criação. Hoje aplica só o que já existe no model
        (departamento derivado, SLA informativo). Quando checklist/campos
        obrigatórios/regras de aprovação/documentos/automações/
        notificações forem implementados como conceitos reais de
        WorkflowEtapa, entram aqui — sem redesenhar create_tarefa.
        """
        if etapa is None:
            return {"departamento_id": None, "sla_horas_esperado": None}
        return {"departamento_id": etapa.departamento_id, "sla_horas_esperado": etapa.tempo_esperado_horas}

    def _ensure_responsavel_principal_valido(self, db: Session, empresa_id: str, usuario_id: str | None) -> None:
        if usuario_id is None:
            return
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise TarefaInvalidDataError("Responsável principal não encontrado ou não pertence à Empresa informada")

    def _ensure_colaboradores_validos(self, db: Session, empresa_id: str, usuario_ids: list[str]) -> None:
        for usuario_id in usuario_ids:
            usuario = self.usuario_repository.get_by_id(db, usuario_id)
            if usuario is None or usuario.empresa_id != empresa_id:
                raise TarefaInvalidDataError(f"Colaborador {usuario_id} não encontrado ou não pertence à Empresa informada")
```

**Nota**: verificar a assinatura real de `WorkflowEtapaRepository.list(...)` (`grep -n "def list" backend/app/repositories/workflow_etapa_repository.py`) — se não existir suporte a `order_by(ordem)` + `limit`, usar em vez disso um método dedicado `get_primeira_etapa(db, *, workflow_id)` que faça `select(WorkflowEtapa).where(workflow_id=...).order_by(WorkflowEtapa.ordem.asc()).limit(1)`. Se não existir, criar esse método em `WorkflowEtapaRepository` como parte deste Step (mesmo arquivo, mesmo padrão dos métodos já lá) antes de usá-lo aqui.

Agora editar `create_tarefa`. Localizar (linha ~136-192, dentro do `try`) e adicionar, logo após `self._ensure_actor_valido(db, empresa_id, actor_usuario_id)`:

```python
            workflow_id = str(data.workflow_id) if data.workflow_id else None
            workflow_etapa_id = str(data.workflow_etapa_id) if data.workflow_etapa_id else None
            self._ensure_workflow_associacao_valida(db, empresa_id, workflow_id, workflow_etapa_id)

            etapa_selecionada: WorkflowEtapa | None = None
            if workflow_id and not workflow_etapa_id:
                etapa_selecionada = self._selecionar_etapa_inicial(db, workflow_id)
                if etapa_selecionada is not None:
                    workflow_etapa_id = etapa_selecionada.id
            elif workflow_etapa_id:
                etapa_selecionada = self.workflow_etapa_repository.get_by_id(db, workflow_etapa_id)

            template = self._aplicar_template_etapa(etapa_selecionada)

            responsavel_principal_usuario_id = (
                str(data.responsavel_principal_usuario_id) if data.responsavel_principal_usuario_id else None
            )
            self._ensure_responsavel_principal_valido(db, empresa_id, responsavel_principal_usuario_id)

            colaboradores_usuario_ids = [str(uid) for uid in data.colaboradores_usuario_ids]
            self._ensure_colaboradores_validos(db, empresa_id, colaboradores_usuario_ids)
```

Na construção do `Tarefa(...)`, adicionar os dois novos campos (logo após `inativado_por_usuario_id=None,`):

```python
                workflow_id=workflow_id,
                workflow_etapa_id=workflow_etapa_id,
                responsavel_principal_usuario_id=responsavel_principal_usuario_id,
```

Depois de `self.repository.create(db, tarefa)` e antes de `self._publish_criada(...)`, adicionar:

```python
            for usuario_id in colaboradores_usuario_ids:
                self.tarefa_colaborador_repository.create(
                    db,
                    TarefaColaborador(
                        id=str(uuid4()),
                        empresa_id=empresa_id,
                        tarefa_id=tarefa.id,
                        usuario_id=usuario_id,
                        created_at=now,
                    ),
                )
            tarefa.departamento_id = template["departamento_id"]
            tarefa.sla_horas_esperado = template["sla_horas_esperado"]
```

- [ ] **Step 4: Atualizar `to_response` para expor os campos derivados**

Localizar `def to_response(self, tarefa: Tarefa) -> TarefaResponse:` e trocar por:

```python
    def to_response(self, tarefa: Tarefa) -> TarefaResponse:
        # departamento_id/sla_horas_esperado/cliente_nome_exibicao são
        # atributos transitórios (não-mapeados) atribuídos pelo próprio
        # Service (create_tarefa) ou pelo Repository (list/get_by_id via
        # _aplicar_cliente_nome_exibicao) — nunca colunas persistidas.
        response = TarefaResponse.model_validate(tarefa)
        response.departamento_id = getattr(tarefa, "departamento_id", None)
        response.sla_horas_esperado = getattr(tarefa, "sla_horas_esperado", None)
        response.cliente_nome_exibicao = getattr(tarefa, "cliente_nome_exibicao", None)
        return response
```

Como `departamento_id`/`sla_horas_esperado` só são setados em `create_tarefa` hoje (não em `get_tarefa`/`list_tarefas`, que vêm do banco sem esses atributos), adicionar a mesma resolução em `get_tarefa` e `list_tarefas`: depois de obter a(s) `Tarefa`, para cada uma, se `tarefa.workflow_etapa_id`, buscar a `WorkflowEtapa` via `self.workflow_etapa_repository.get_by_id(db, tarefa.workflow_etapa_id)` e aplicar `_aplicar_template_etapa` do mesmo jeito. Extrair isso para um helper reaproveitado pelos três métodos:

```python
    def _anexar_dados_derivados(self, db: Session, tarefa: Tarefa) -> Tarefa:
        etapa = self.workflow_etapa_repository.get_by_id(db, tarefa.workflow_etapa_id) if tarefa.workflow_etapa_id else None
        template = self._aplicar_template_etapa(etapa)
        tarefa.departamento_id = template["departamento_id"]
        tarefa.sla_horas_esperado = template["sla_horas_esperado"]
        return tarefa
```

Chamar `self._anexar_dados_derivados(db, tarefa)` no fim de `get_tarefa` (antes do `return`) e para cada item retornado por `list_tarefas` (antes do `return`), e substituir a atribuição manual feita em `create_tarefa` (Step 3) por uma chamada a este mesmo helper, removendo a duplicação:

```python
            self._anexar_dados_derivados(db, tarefa)
```

(no lugar das duas linhas `tarefa.departamento_id = ...` / `tarefa.sla_horas_esperado = ...` escritas no Step 3).

- [ ] **Step 5: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py -k "etapa_de_menor_ordem or etapa_explicita or responsavel_e_colaboradores" -v
```

- [ ] **Step 6: Rodar toda a suíte de Tarefa/Workflow para checar regressão**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py tests/test_tarefas.py tests/test_tarefas_api.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/tarefa_service.py backend/tests/test_tarefa_workflow_integracao.py
git commit -m "feat(tarefas): create_tarefa aplica workflow, etapa inicial automatica, template e responsaveis"
```

---

### Task 7: `associar_workflow` ganha regra de perfil por status + evento

**Files:**
- Modify: `backend/app/services/tarefa_service.py`
- Modify: `backend/app/api/routes/tarefas.py` (mapear o novo erro)
- Test: `backend/tests/test_tarefa_workflow_integracao.py`

**Interfaces:**
- Consumes: `TarefaWorkflowReassociacaoNaoPermitidaError` (declarada na Task 5).
- Produces: `associar_workflow(db, *, empresa_id, tarefa_id, workflow_id, workflow_etapa_id, actor_usuario_id)` — assinatura ganha `actor_usuario_id` (hoje não recebe); publica `TAREFA_ATUALIZADA`.

- [ ] **Step 1: Escrever os testes**

```python
def test_associar_workflow_livre_em_rascunho_e_planejada(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    workflow = persist(client.session_factory, make_workflow(empresa.id))
    etapa = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=1))
    t = persist(client.session_factory, tarefa(empresa.id, status="rascunho"))

    response = client.post(
        f"/tarefas/{t.id}/workflow/associar",
        json={"workflowId": workflow.id, "workflowEtapaId": etapa.id},
        headers=headers,
    )

    assert response.status_code == 200, response.json()
    assert response.json()["workflowId"] == workflow.id


def test_associar_workflow_apos_operacao_exige_admin_ou_gestor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    _, gestor, _ = create_auth_context(client.session_factory, empresa=empresa, perfil_base="gestor")
    admin_headers = auth_headers(client, admin, empresa)
    workflow = persist(client.session_factory, make_workflow(empresa.id))
    etapa = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=1))
    t = persist(client.session_factory, tarefa(empresa.id, status="em_execucao", prazo=None))

    response = client.post(
        f"/tarefas/{t.id}/workflow/associar",
        json={"workflowId": workflow.id, "workflowEtapaId": etapa.id},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.json()
```

Como **todas** as rotas de Tarefa já exigem `require_admin_or_gestor` (achado do spec §6), não existe hoje um perfil "mais amplo" para testar o caminho de rejeição via API real — a regra de rejeição (perfil fora de admin/gestor, tarefa fora de rascunho/planejada) é testada **diretamente no service**, não via rota:

```python
def test_associar_workflow_service_rejeita_perfil_nao_autorizado_fora_de_rascunho_planejada(client):
    from app.services.tarefa_service import TarefaService, TarefaWorkflowReassociacaoNaoPermitidaError

    empresa, _, operador = create_auth_context(client.session_factory, perfil_base="operador")
    workflow = persist(client.session_factory, make_workflow(empresa.id))
    etapa = persist(client.session_factory, make_workflow_etapa(empresa.id, workflow.id, ordem=1))
    t = persist(client.session_factory, tarefa(empresa.id, status="em_execucao"))

    service = TarefaService()
    with client.session_factory() as db:
        with pytest.raises(TarefaWorkflowReassociacaoNaoPermitidaError):
            service.associar_workflow(
                db,
                empresa_id=empresa.id,
                tarefa_id=t.id,
                workflow_id=workflow.id,
                workflow_etapa_id=etapa.id,
                actor_usuario_id=operador.id,
            )
```

Confirmar a assinatura real de `create_auth_context` (aceita `perfil_base=` e devolve `(empresa, usuario, ...)` — conferir `backend/tests/conftest.py`, `grep -n "^def create_auth_context"`) e ajustar o unpacking/parâmetros conforme o retorno real.

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py -k "associar_workflow" -v
```
Esperado: `TypeError: associar_workflow() got an unexpected keyword argument 'actor_usuario_id'`.

- [ ] **Step 3: Implementar a regra no service**

Editar a assinatura de `associar_workflow` (linha ~449):

```python
    def associar_workflow(
        self,
        db: Session,
        *,
        empresa_id: str,
        tarefa_id: str,
        workflow_id: str | None,
        workflow_etapa_id: str | None,
        actor_usuario_id: str | None = None,
    ) -> Tarefa:
```

No corpo, logo após `tarefa = self.get_tarefa(...)` e antes de `self._ensure_workflow_associacao_valida(...)`, adicionar:

```python
            self._ensure_workflow_reassociacao_permitida(db, tarefa, actor_usuario_id)
```

Adicionar o método (perto de `_ensure_actor_valido`):

```python
    ETAPAS_LIVRES_REASSOCIACAO_WORKFLOW = {"rascunho", "planejada"}

    def _ensure_workflow_reassociacao_permitida(self, db: Session, tarefa: Tarefa, actor_usuario_id: str | None) -> None:
        # Nota de escopo (spec 2026-07-22-tarefas-creation-flow-design.md
        # §6): hoje TODAS as rotas de Tarefa já exigem admin/gestor
        # (require_admin_or_gestor) — esta regra não muda nenhum
        # comportamento observável agora. É preparatória para quando o
        # acesso a Tarefa for ampliado (ex.: Operador editando as
        # próprias tarefas em rascunho/planejada).
        if tarefa.status in self.ETAPAS_LIVRES_REASSOCIACAO_WORKFLOW:
            return
        if actor_usuario_id is None:
            raise TarefaWorkflowReassociacaoNaoPermitidaError(
                "Reatribuir Workflow após a Tarefa entrar em operação exige um ator identificado"
            )
        usuario = self.usuario_repository.get_by_id(db, actor_usuario_id)
        if usuario is None or usuario.perfil_base not in {"admin", "gestor"}:
            raise TarefaWorkflowReassociacaoNaoPermitidaError(
                "Após a Tarefa entrar em operação, só Administradores ou Gestores podem trocar o Workflow"
            )
```

E, no final de `associar_workflow`, publicar o evento reaproveitado (a lógica atual só faz `self.repository.update(db, tarefa)` sem publicar nada). Adicionar antes de `db.commit()`:

```python
            if tarefa.workflow_id != workflow_id or tarefa.workflow_etapa_id != workflow_etapa_id:
                campos_alterados = ["workflowId", "workflowEtapaId"]
                tarefa.workflow_id = workflow_id
                tarefa.workflow_etapa_id = workflow_etapa_id
                tarefa.updated_at = datetime.now(timezone.utc)
                self.repository.update(db, tarefa)
                self._publish_atualizada(db, tarefa, actor_usuario_id, occurred_at=tarefa.updated_at, campos_alterados=campos_alterados)
```

(substituindo o bloco `if tarefa.workflow_id != workflow_id or ...` que já existe, que hoje só atualiza sem publicar — conferir o texto exato antes de editar, já lido integralmente na investigação: linhas 472-476 do arquivo original.)

Importar `TarefaWorkflowReassociacaoNaoPermitidaError` da Task 5 (mesmo arquivo `tarefa_service.py`, já fica declarada ali).

- [ ] **Step 4: Mapear o novo erro na rota**

Em `backend/app/api/routes/tarefas.py`, adicionar ao import de `app.services.tarefa_service`:

```python
    TarefaWorkflowReassociacaoNaoPermitidaError,
```

Em `handle_tarefa_error`, adicionar antes do `raise exc` final:

```python
    if isinstance(exc, TarefaWorkflowReassociacaoNaoPermitidaError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
```

No endpoint `associar_workflow_tarefa` (linha ~224), passar `actor_usuario_id=current_user.id` na chamada ao service (hoje provavelmente não passa — conferir e adicionar).

- [ ] **Step 5: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py -k "associar_workflow" -v
```

- [ ] **Step 6: Rodar toda a suíte de Tarefa/Workflow**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefa_workflow_integracao.py tests/test_tarefas_api.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/tarefa_service.py backend/app/api/routes/tarefas.py backend/tests/test_tarefa_workflow_integracao.py
git commit -m "feat(tarefas): regra de perfil por status para reatribuir workflow, publica evento reaproveitado"
```

---

### Task 8: Rotas — endpoints de colaboradores

**Files:**
- Modify: `backend/app/api/routes/tarefas.py`
- Create: `backend/app/schemas/tarefa_colaborador.py`
- Test: `backend/tests/test_tarefas_api.py`

**Interfaces:**
- Produces: `POST /tarefas/{tarefaId}/colaboradores` (body `{usuarioId}`), `GET /tarefas/{tarefaId}/colaboradores`, `DELETE /tarefas/{tarefaId}/colaboradores/{usuarioId}`.

- [ ] **Step 1: Escrever o teste**

```python
def test_colaboradores_crud(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    t = persist(client.session_factory, tarefa(empresa.id))
    colaborador = persist(client.session_factory, make_usuario(empresa.id))

    add = client.post(f"/tarefas/{t.id}/colaboradores", json={"usuarioId": colaborador.id}, headers=headers)
    assert add.status_code == 201, add.json()

    listar = client.get(f"/tarefas/{t.id}/colaboradores", headers=headers)
    assert listar.status_code == 200
    assert [c["usuarioId"] for c in listar.json()] == [colaborador.id]

    remover = client.delete(f"/tarefas/{t.id}/colaboradores/{colaborador.id}", headers=headers)
    assert remover.status_code == 204

    listar_apos = client.get(f"/tarefas/{t.id}/colaboradores", headers=headers)
    assert listar_apos.json() == []
```

- [ ] **Step 2: Rodar, confirmar falha (404 — rota não existe)**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefas_api.py -k colaboradores_crud -v
```

- [ ] **Step 3: Criar o schema**

```python
# backend/app/schemas/tarefa_colaborador.py
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TarefaColaboradorCreate(BaseModel):
    usuario_id: UUID = Field(alias="usuarioId")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TarefaColaboradorResponse(BaseModel):
    id: UUID
    tarefa_id: UUID = Field(alias="tarefaId")
    usuario_id: UUID = Field(alias="usuarioId")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)
```

- [ ] **Step 4: Adicionar as rotas**

Em `backend/app/api/routes/tarefas.py`, adicionar imports:

```python
from app.models.tarefa_colaborador import TarefaColaborador
from app.repositories.tarefa_colaborador_repository import TarefaColaboradorRepository
from app.schemas.tarefa_colaborador import TarefaColaboradorCreate, TarefaColaboradorResponse
```

Instanciar o repositório junto a `tarefa_service`:

```python
tarefa_colaborador_repository = TarefaColaboradorRepository()
```

Adicionar as três rotas ao final do arquivo (depois de `associar_workflow_tarefa`):

```python
@router.post("/{tarefa_id}/colaboradores", response_model=TarefaColaboradorResponse, status_code=status.HTTP_201_CREATED)
def adicionar_colaborador(
    tarefa_id: UUID,
    payload: TarefaColaboradorCreate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        tarefa = tarefa_service.get_tarefa(db, empresa_id=current_user.empresa_id, tarefa_id=str(tarefa_id))
        from datetime import datetime, timezone
        from uuid import uuid4

        vinculo = TarefaColaborador(
            id=str(uuid4()),
            empresa_id=current_user.empresa_id,
            tarefa_id=tarefa.id,
            usuario_id=str(payload.usuario_id),
            created_at=datetime.now(timezone.utc),
        )
        tarefa_colaborador_repository.create(db, vinculo)
        db.commit()
        db.refresh(vinculo)
        return TarefaColaboradorResponse.model_validate(vinculo)
    except Exception as exc:
        db.rollback()
        handle_tarefa_error(exc)


@router.get("/{tarefa_id}/colaboradores", response_model=list[TarefaColaboradorResponse])
def listar_colaboradores(
    tarefa_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        tarefa_service.get_tarefa(db, empresa_id=current_user.empresa_id, tarefa_id=str(tarefa_id))
        vinculos = tarefa_colaborador_repository.list_by_tarefa(db, empresa_id=current_user.empresa_id, tarefa_id=str(tarefa_id))
        return [TarefaColaboradorResponse.model_validate(v) for v in vinculos]
    except Exception as exc:
        handle_tarefa_error(exc)


@router.delete("/{tarefa_id}/colaboradores/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_colaborador(
    tarefa_id: UUID,
    usuario_id: UUID,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        tarefa_service.get_tarefa(db, empresa_id=current_user.empresa_id, tarefa_id=str(tarefa_id))
        vinculo = tarefa_colaborador_repository.get_by_tarefa_usuario(
            db, empresa_id=current_user.empresa_id, tarefa_id=str(tarefa_id), usuario_id=str(usuario_id)
        )
        if vinculo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador não encontrado nesta Tarefa")
        tarefa_colaborador_repository.delete(db, vinculo)
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        handle_tarefa_error(exc)
```

- [ ] **Step 5: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_api pytest tests/test_tarefas_api.py -k colaboradores_crud -v
```

- [ ] **Step 6: Rodar a suíte completa do backend**

```bash
docker compose exec taskfloww_api pytest
```
Esperado: todos os testes passam (nenhuma regressão).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/tarefa_colaborador.py backend/app/api/routes/tarefas.py backend/tests/test_tarefas_api.py
git commit -m "feat(tarefas): endpoints CRUD de colaboradores"
```

---

## PARTE 2 — FRONTEND

### Task 9: Tipos — `tarefa-api.ts` / `tarefa-domain.ts`

**Files:**
- Modify: `frontend/src/types/tarefa-api.ts`
- Modify: `frontend/src/types/tarefa-domain.ts`

**Interfaces:**
- Produces: `TarefaApiResponse`/`Tarefa` ganham `workflowId`/`workflowEtapaId` (já existiam), `responsavelPrincipalUsuarioId`, `departamentoId`, `slaHorasEsperado`, `clienteNomeExibicao`; `TarefaCreatePayload` ganha `workflowId?`, `workflowEtapaId?`, `responsavelPrincipalUsuarioId?`, `colaboradoresUsuarioIds?`.

- [ ] **Step 1: Editar `TarefaApiResponse` em `tarefa-api.ts`**

Localizar o type (linha ~86, mesmo bloco que já tem `workflowId`/`workflowEtapaId` — conferir texto exato com `sed -n '60,95p' frontend/src/types/tarefa-api.ts`) e adicionar:

```typescript
  responsavelPrincipalUsuarioId: string | null;
  departamentoId: string | null;
  slaHorasEsperado: number | null;
  clienteNomeExibicao: string | null;
```

- [ ] **Step 2: Editar `TarefaEditableValues`/`TarefaCreatePayload`**

Localizar `TarefaEditableValues` (a base de `TarefaCreatePayload`/`TarefaUpdatePayload`, `clienteId?: string` aparece em ~linha 70) e adicionar:

```typescript
  workflowId?: string | null;
  workflowEtapaId?: string | null;
  responsavelPrincipalUsuarioId?: string | null;
  colaboradoresUsuarioIds?: string[];
```

- [ ] **Step 3: Editar `Tarefa` (domínio) em `tarefa-domain.ts`**

Adicionar os mesmos campos de exibição:

```typescript
  responsavelPrincipalUsuarioId: string | null;
  departamentoId: string | null;
  slaHorasEsperado: number | null;
  clienteNomeExibicao: string | null;
```

- [ ] **Step 4: Rodar typecheck (deve falhar — mapper ainda não popula os novos campos obrigatórios do type)**

```bash
docker compose exec taskfloww_front npm run typecheck
```
Esperado: erros em `tarefa-api-mappers.ts` (`Property 'responsavelPrincipalUsuarioId' is missing`).

- [ ] **Step 5: Commit (junto com a Task 10, que corrige o typecheck)**

Não commitar ainda — este task fica "vermelho" até a Task 10 completar o mapper. Prosseguir direto.

---

### Task 10: Mapper — `tarefa-api-mappers.ts`

**Files:**
- Modify: `frontend/src/lib/tarefa-api-mappers.ts`
- Test: `frontend/tests/tarefas/mappers.test.ts` (já existe — adicionar caso)

**Interfaces:**
- Consumes: `TarefaApiResponse`/`Tarefa` (Task 9).
- Produces: `parseTarefaApiResponse`, `mapTarefaApiResponseToDomain` propagam os 4 campos novos.

- [ ] **Step 1: Escrever o teste**

```typescript
test("mapeia responsavelPrincipalUsuarioId, departamentoId, slaHorasEsperado e clienteNomeExibicao", () => {
  const response = {
    ...baseTarefaApiResponse(), // usar o helper de fixture já existente no arquivo de teste — conferir nome real
    responsavelPrincipalUsuarioId: "usuario-1",
    departamentoId: "departamento-1",
    slaHorasEsperado: 48,
    clienteNomeExibicao: "Bretas Supermercados",
  };

  const tarefa = mapTarefaApiResponseToDomain(response, response.empresaId);

  assert.equal(tarefa.responsavelPrincipalUsuarioId, "usuario-1");
  assert.equal(tarefa.departamentoId, "departamento-1");
  assert.equal(tarefa.slaHorasEsperado, 48);
  assert.equal(tarefa.clienteNomeExibicao, "Bretas Supermercados");
});
```

Verificar o nome real do helper de fixture usado pelos testes existentes em `frontend/tests/tarefas/mappers.test.ts` (`grep -n "function.*TarefaApiResponse\|const.*base"`) e usá-lo em vez de `baseTarefaApiResponse()` (nome ilustrativo).

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/mappers.test.ts
```

- [ ] **Step 3: Editar `parseTarefaApiResponse`**

No bloco de validação (linha ~104-135), adicionar às checagens:

```typescript
    !isNullableString(value.responsavelPrincipalUsuarioId) ||
    !isNullableString(value.departamentoId) ||
    !(value.slaHorasEsperado === null || isRequiredInteger(value.slaHorasEsperado)) ||
    !isNullableString(value.clienteNomeExibicao) ||
```

No `return` do mesmo bloco, adicionar:

```typescript
    responsavelPrincipalUsuarioId: value.responsavelPrincipalUsuarioId,
    departamentoId: value.departamentoId,
    slaHorasEsperado: value.slaHorasEsperado,
    clienteNomeExibicao: value.clienteNomeExibicao,
```

- [ ] **Step 4: Editar `mapTarefaApiResponseToDomain`**

No `return` (linha ~176-206), adicionar:

```typescript
    responsavelPrincipalUsuarioId: response.responsavelPrincipalUsuarioId,
    departamentoId: response.departamentoId,
    slaHorasEsperado: response.slaHorasEsperado,
    clienteNomeExibicao: response.clienteNomeExibicao,
```

- [ ] **Step 5: Editar `isTarefaDomain`** (usado para validar payloads na direção contrária, se existir esse uso — linha ~223)

Adicionar as mesmas 4 checagens de tipo, mesmo padrão das demais linhas desse bloco.

- [ ] **Step 6: Rodar o teste do mapper, confirmar PASS**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/mappers.test.ts
```

- [ ] **Step 7: Rodar typecheck completo, confirmar limpo (fecha a Task 9)**

```bash
docker compose exec taskfloww_front npm run typecheck
```

- [ ] **Step 8: Commit (Tasks 9 + 10 juntas)**

```bash
git add frontend/src/types/tarefa-api.ts frontend/src/types/tarefa-domain.ts frontend/src/lib/tarefa-api-mappers.ts frontend/tests/tarefas/mappers.test.ts
git commit -m "feat(tarefas): tipos e mapper propagam workflow/etapa/responsaveis/cliente"
```

---

### Task 11: `TarefaFormFields.tsx` — Workflow, Etapa, Responsável, Colaboradores

**Files:**
- Modify: `frontend/src/components/tarefas/tarefa-form-value.ts`
- Modify: `frontend/src/components/tarefas/TarefaFormFields.tsx`
- Test: `frontend/tests/tarefas/view.test.ts` ou novo `frontend/tests/tarefas/form-fields.test.ts` (conferir se já existe algo equivalente antes de criar)

**Interfaces:**
- Consumes: `workflowsBrowserClient.listarWorkflows`/`.listarWorkflowEtapas` (já existem, `frontend/src/lib/api/workflow-client.ts`), `usuariosBrowserClient.listarUsuarios` (já existe, `frontend/src/lib/api/usuarios-client.ts`).
- Produces: `TarefaFormValue` ganha `workflowId: string`, `workflowEtapaId: string`, `responsavelPrincipalUsuarioId: string`, `colaboradoresUsuarioIds: string[]`.

- [ ] **Step 1: Editar `TarefaFormValue`**

Em `tarefa-form-value.ts`, adicionar ao type:

```typescript
  workflowId: string;
  workflowEtapaId: string;
  responsavelPrincipalUsuarioId: string;
  colaboradoresUsuarioIds: string[];
```

- [ ] **Step 2: Escrever teste de comportamento puro — auto-seleção de etapa**

Extrair a regra "workflow mudou → etapa reseta; se havia etapa e o workflow não mudou, mantém" como função pura testável (mesmo raciocínio já usado para `onFieldChangeWithReset` em Cliente). Em `tarefa-form-value.ts`, adicionar:

```typescript
export function withWorkflowReset(value: TarefaFormValue, novoWorkflowId: string): TarefaFormValue {
  if (novoWorkflowId === value.workflowId) return value;
  return { ...value, workflowId: novoWorkflowId, workflowEtapaId: "" };
}
```

Teste (`frontend/tests/tarefas/form-value.test.ts`, criar se não existir):

```typescript
import assert from "node:assert/strict";
import test from "node:test";
import "../auth/helpers.mjs";

const { withWorkflowReset } = await import("../../src/components/tarefas/tarefa-form-value");

function baseValue() {
  return {
    origemIdentificacao: "taskfloww" as const,
    pitCodigo: "",
    titulo: "",
    descricao: "",
    clienteId: "",
    prioridade: "media" as const,
    dataInicio: "",
    prazo: "",
    workflowId: "workflow-antigo",
    workflowEtapaId: "etapa-antiga",
    responsavelPrincipalUsuarioId: "",
    colaboradoresUsuarioIds: [],
  };
}

test("withWorkflowReset limpa a etapa quando o workflow muda", () => {
  const next = withWorkflowReset(baseValue(), "workflow-novo");
  assert.equal(next.workflowId, "workflow-novo");
  assert.equal(next.workflowEtapaId, "");
});

test("withWorkflowReset mantém a etapa quando o workflow não muda", () => {
  const next = withWorkflowReset(baseValue(), "workflow-antigo");
  assert.equal(next.workflowEtapaId, "etapa-antiga");
});
```

- [ ] **Step 3: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/form-value.test.ts
```

- [ ] **Step 4: Rodar, confirmar PASS** (a função do Step 2 já é a implementação completa — TDD aqui é "escrever teste, escrever a função de uma vez", já que é puramente um `if`)

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/form-value.test.ts
```

- [ ] **Step 5: Adicionar a seção de campos em `TarefaFormFields.tsx`**

Ler o arquivo completo primeiro (`sed -n '1,60p' frontend/src/components/tarefas/TarefaFormFields.tsx`) para confirmar a assinatura exata de `TarefaFormFieldsProps` (`formRef`, `value`, `mode`, `disabled`, `error`, `onChange`, `onPitNormalizadoChange?`, `onSubmit`) antes de editar — o componente já existe e segue o mesmo padrão de `ClienteFormFields.tsx` (import de `@/components/ui/{Input,Select}`, `setField` genérico).

Adicionar ao topo do arquivo:

```typescript
import { useEffect, useState } from "react";
import { workflowsBrowserClient } from "@/lib/api/workflow-client";
import { usuariosBrowserClient } from "@/lib/api/usuarios-client";
import type { Workflow, WorkflowEtapa } from "@/types/workflow-domain";
import type { Usuario } from "@/types/usuario-domain";
import { withWorkflowReset } from "./tarefa-form-value";
```

Dentro do componente, adicionar o estado e os efeitos de carregamento (mesmo padrão de `TarefaWorkflowSelectModal.tsx`):

```typescript
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [etapas, setEtapas] = useState<WorkflowEtapa[] | null>(null);
  const [usuarios, setUsuarios] = useState<Usuario[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    void workflowsBrowserClient.listarWorkflows({ status: "ativo", limit: 200 }).then((result) => {
      if (!cancelled && result.ok) setWorkflows(result.data.items);
    });
    void usuariosBrowserClient.listarUsuarios({ limit: 200 }).then((result) => {
      if (!cancelled && result.ok) setUsuarios(result.data.items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!value.workflowId) {
      setEtapas(null);
      return;
    }
    let cancelled = false;
    void workflowsBrowserClient.listarWorkflowEtapas({ workflowId: value.workflowId, status: "ativa" }).then((result) => {
      if (!cancelled && result.ok) setEtapas(result.data.items);
    });
    return () => {
      cancelled = true;
    };
  }, [value.workflowId]);

  const etapaSelecionada = etapas?.find((etapa) => etapa.id === value.workflowEtapaId) ?? null;

  function handleWorkflowChange(novoWorkflowId: string) {
    onChange(withWorkflowReset(value, novoWorkflowId));
  }
```

(`onChange`/`value` já são props existentes do componente — não redeclarar.)

Adicionar a seção JSX (dentro do `return`, como um bloco novo — posicionar depois dos campos já existentes, antes do fechamento):

```tsx
      <div className="mt-6 space-y-3 border-t border-zinc-100 pt-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-400">Workflow e Responsáveis</p>

        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 sm:col-span-6">
            <Select
              label="Workflow"
              density="compact"
              value={value.workflowId}
              onChange={(event) => handleWorkflowChange(event.target.value)}
              disabled={disabled || workflows === null}
              options={[
                { value: "", label: "Nenhum Workflow" },
                ...(workflows ?? []).map((w) => ({ value: w.id, label: `${w.codigoInterno} · ${w.nome}` })),
              ]}
            />
          </div>

          {value.workflowId ? (
            <div className="col-span-12 sm:col-span-6">
              <Select
                label="Etapa inicial"
                density="compact"
                value={value.workflowEtapaId}
                onChange={(event) => onChange({ ...value, workflowEtapaId: event.target.value })}
                disabled={disabled || etapas === null}
                options={[
                  { value: "", label: etapas === null ? "Carregando..." : "Selecione a etapa" },
                  ...(etapas ?? []).map((etapa) => ({ value: etapa.id, label: `${etapa.ordem} · ${etapa.nome}` })),
                ]}
              />
            </div>
          ) : null}

          {etapaSelecionada ? (
            <div className="col-span-12 flex flex-wrap gap-4 rounded-2xl border border-zinc-100 bg-[#faf8f4] px-3 py-2 text-[11px] text-zinc-500">
              <span>Departamento: {etapaSelecionada.departamentoId ?? "-"}</span>
              <span>SLA esperado: {etapaSelecionada.tempoEsperadoHoras != null ? `${etapaSelecionada.tempoEsperadoHoras}h` : "-"}</span>
            </div>
          ) : null}

          <div className="col-span-12 sm:col-span-6">
            <Select
              label="Responsável principal"
              density="compact"
              value={value.responsavelPrincipalUsuarioId}
              onChange={(event) => onChange({ ...value, responsavelPrincipalUsuarioId: event.target.value })}
              disabled={disabled || usuarios === null}
              options={[
                { value: "", label: "Sem responsável definido" },
                ...(usuarios ?? []).map((u) => ({ value: u.id, label: u.nome })),
              ]}
            />
          </div>

          <div className="col-span-12">
            <span className="mb-1 block text-[11px] font-normal text-zinc-500">Colaboradores</span>
            <div className="flex flex-wrap gap-2">
              {(usuarios ?? []).map((usuario) => {
                const checked = value.colaboradoresUsuarioIds.includes(usuario.id);
                return (
                  <label key={usuario.id} className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-2.5 py-1 text-[11px] text-zinc-700">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={(event) => {
                        const next = event.target.checked
                          ? [...value.colaboradoresUsuarioIds, usuario.id]
                          : value.colaboradoresUsuarioIds.filter((id) => id !== usuario.id);
                        onChange({ ...value, colaboradoresUsuarioIds: next });
                      }}
                    />
                    {usuario.nome}
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      </div>
```

Verificar antes de aplicar se `WorkflowEtapa` (tipo, `@/types/workflow-domain`) tem `departamentoId`/`tempoEsperadoHoras` com esses nomes exatos (`grep -n "departamentoId\|tempoEsperadoHoras\|tempo_esperado" frontend/src/types/workflow-domain.ts`) — ajustar para o nome real se divergir.

- [ ] **Step 6: Rodar typecheck e lint**

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/tarefas/tarefa-form-value.ts frontend/src/components/tarefas/TarefaFormFields.tsx frontend/tests/tarefas/form-value.test.ts
git commit -m "feat(tarefas): campos de Workflow/Etapa/Responsavel/Colaboradores no formulario"
```

---

### Task 12: `TarefaCreateDrawer.tsx` — payload de criação

**Files:**
- Modify: `frontend/src/components/tarefas/TarefaCreateDrawer.tsx`
- Test: `frontend/tests/tarefas/client.test.ts` (payload) e/ou `frontend/tests/tarefas/routes.test.ts` (BFF)

**Interfaces:**
- Consumes: `TarefaFormValue` (Task 11), `TarefaCreatePayload` (Task 9).

- [ ] **Step 1: Escrever o teste de payload**

Em `frontend/tests/tarefas/routes.test.ts`, adicionar um teste seguindo o padrão dos já existentes de criação (`authenticatedMutation("/api/tarefas", "POST", {...})`), confirmando que `workflowId`/`workflowEtapaId`/`responsavelPrincipalUsuarioId`/`colaboradoresUsuarioIds` chegam intactos ao `backendBody` quando preenchidos, e que campos vazios (`""`) viram `null`/array vazio, mesmo tratamento de `optional()`/`onlyDigits` já usado em Cliente.

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/routes.test.ts
```

- [ ] **Step 3: Editar `createInitialTarefaFormValue` e `buildCreatePayload`**

```typescript
function createInitialTarefaFormValue(): TarefaFormValue {
  return {
    origemIdentificacao: "taskfloww",
    pitCodigo: "",
    titulo: "",
    descricao: "",
    clienteId: "",
    prioridade: "media",
    dataInicio: "",
    prazo: "",
    workflowId: "",
    workflowEtapaId: "",
    responsavelPrincipalUsuarioId: "",
    colaboradoresUsuarioIds: [],
  };
}

function buildCreatePayload(value: TarefaFormValue, pitNormalizado: string | null): TarefaCreatePayload {
  const isPubli = value.origemIdentificacao === "publi";
  return {
    origemIdentificacao: value.origemIdentificacao,
    pitCodigo: isPubli ? value.pitCodigo.trim() || null : null,
    pitNormalizado: isPubli ? pitNormalizado : null,
    titulo: value.titulo,
    descricao: value.descricao.trim() || null,
    clienteId: value.clienteId.trim() || null,
    agenciaId: null,
    projetoId: null,
    prioridade: value.prioridade,
    dataInicio: datetimeLocalToIso(value.dataInicio),
    prazo: datetimeLocalToIso(value.prazo),
    workflowId: value.workflowId || null,
    workflowEtapaId: value.workflowEtapaId || null,
    responsavelPrincipalUsuarioId: value.responsavelPrincipalUsuarioId || null,
    colaboradoresUsuarioIds: value.colaboradoresUsuarioIds,
  };
}
```

- [ ] **Step 4: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/routes.test.ts
```

**Nota**: a rota BFF (`frontend/src/app/api/tarefas/route.ts`) provavelmente valida os campos aceitos no `POST` (mesmo padrão de `parseClienteCreatePayload` em `lib/api/clientes.ts` — conferir `frontend/src/lib/api/tarefas.ts`, função equivalente a `parseTarefaCreatePayload`). Se existir uma lista de campos permitidos (`EDITABLE_KEYS`/similar), adicionar `workflowId`, `workflowEtapaId`, `responsavelPrincipalUsuarioId`, `colaboradoresUsuarioIds` a ela antes deste teste passar — mesmo padrão já usado na correção do bug de documento mascarado (sessão anterior). Se essa validação existir, ela é parte deste Step 3 (mesmo arquivo `lib/api/tarefas.ts`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/tarefas/TarefaCreateDrawer.tsx frontend/src/lib/api/tarefas.ts frontend/tests/tarefas/routes.test.ts
git commit -m "feat(tarefas): TarefaCreateDrawer envia workflow/etapa/responsaveis na criacao"
```

---

### Task 13: `TarefaEditDrawer.tsx` — reatribuição de Workflow + responsáveis

**Files:**
- Modify: `frontend/src/components/tarefas/TarefaEditDrawer.tsx`
- Modify: `frontend/src/components/tarefas/tarefa-update.ts` (`buildTarefaUpdatePayload`)
- Test: `frontend/tests/tarefas/routes.test.ts`

**Interfaces:**
- Consumes: `TarefaWorkflowSelectModal` (já existe, relocado do Peek).

- [ ] **Step 1: Ler `tarefa-update.ts` por completo** (`cat frontend/src/components/tarefas/tarefa-update.ts`) para entender `buildTarefaUpdatePayload(original, next)` antes de editar — mesmo padrão de diff campo-a-campo já visto em `ClienteDadosSection.buildUpdatePayload`.

- [ ] **Step 2: Escrever o teste**

Em `frontend/tests/tarefas/routes.test.ts`, adicionar um teste de PATCH confirmando que `responsavelPrincipalUsuarioId` é incluído no payload quando alterado (mesmo padrão dos testes de PATCH de Cliente).

- [ ] **Step 3: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/routes.test.ts
```

- [ ] **Step 4: Editar `tarefa-update.ts`**

Adicionar ao `buildTarefaUpdatePayload`, seguindo o padrão de diff já existente para os demais campos:

```typescript
  if (next.responsavelPrincipalUsuarioId !== original.responsavelPrincipalUsuarioId) {
    payload.responsavelPrincipalUsuarioId = next.responsavelPrincipalUsuarioId || null;
  }
```

(Workflow/Etapa **não** entram aqui — reatribuição de Workflow usa o endpoint dedicado `associar_workflow`, via modal, não o PATCH genérico — ver Step 5.)

- [ ] **Step 5: Adicionar o botão "Alterar Workflow" ao `TarefaEditDrawer.tsx`**

Importar:

```typescript
import { useState } from "react";
import { TarefaWorkflowSelectModal } from "./TarefaWorkflowSelectModal";
import { useWorkflowRuntime } from "./useWorkflowRuntime";
```

Dentro de `TarefaEditFormSession`, adicionar:

```typescript
  const runtime = useWorkflowRuntime(tarefa.id, tarefa.workflowId, tarefa.workflowEtapaId);
  const [workflowModalOpen, setWorkflowModalOpen] = useState(false);

  async function handleAssociarWorkflow(workflowId: string | null, workflowEtapaId: string | null): Promise<boolean> {
    const updated = await runtime.associar(workflowId, workflowEtapaId);
    if (!updated) return false;
    setWorkflowModalOpen(false);
    onUpdated();
    return true;
  }
```

No JSX, antes de `<TarefaFormFields .../>`, adicionar:

```tsx
      <div className="mb-3 flex items-center justify-between rounded-2xl border border-zinc-100 bg-[#faf8f4] px-3 py-2">
        <span className="text-[12px] text-zinc-600">
          Workflow atual: {tarefa.workflowId ? `${tarefa.workflowId}` : "Nenhum"}
        </span>
        <Button size="xs" variant="secondary" onClick={() => setWorkflowModalOpen(true)}>
          Alterar Workflow
        </Button>
      </div>

      {workflowModalOpen ? (
        <TarefaWorkflowSelectModal
          mode="workflow"
          currentWorkflowId={tarefa.workflowId}
          currentWorkflowEtapaId={tarefa.workflowEtapaId}
          submitting={runtime.associarStatus === "submitting"}
          error={runtime.associarStatus === "error" ? runtime.associarError : null}
          onClose={() => {
            setWorkflowModalOpen(false);
            runtime.resetAssociarError();
          }}
          onAssociar={handleAssociarWorkflow}
        />
      ) : null}
```

Trocar `tarefa.workflowId` por uma exibição amigável em uma iteração futura (fora de escopo aqui — nome do Workflow exigiria mais um fetch; deixar o ID visível é aceitável nesta tarefa, já que o foco é a ação de reatribuir, não a leitura, que já existe em detalhe no Peek).

Se o backend rejeitar (403 — regra de perfil por status, Task 7), o erro já aparece via `runtime.associarError` dentro do modal (mesmo mecanismo de erro já usado em `TarefaWorkflowSelectModal`, sem mudança necessária no modal).

- [ ] **Step 6: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/routes.test.ts
```

- [ ] **Step 7: Typecheck + lint**

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/tarefas/TarefaEditDrawer.tsx frontend/src/components/tarefas/tarefa-update.ts frontend/tests/tarefas/routes.test.ts
git commit -m "feat(tarefas): TarefaEditDrawer permite reatribuir workflow e responsavel principal"
```

---

### Task 14: `TarefaPeekDrawer.tsx` / `TarefaWorkflowSection.tsx` — reduzir a consulta + pequenas ações

**Files:**
- Modify: `frontend/src/components/tarefas/TarefaWorkflowSection.tsx`
- Modify: `frontend/src/components/tarefas/TarefaPeekDrawer.tsx`
- Test: `frontend/tests/tarefas/view.test.ts` (conferir se há teste específico de Peek/WorkflowSection; se não houver, este task não quebra nenhum teste automatizado além do lint/typecheck — cobertura via os testes já existentes de `useWorkflowRuntime`/`useWorkflowExecution`, que não mudam)

**Interfaces:**
- Consumes: nenhuma nova. Remove os dois botões "Alterar Workflow"/"Trocar etapa inicial" e o `TarefaWorkflowSelectModal` de dentro de `TarefaWorkflowSection` (relocados para `TarefaEditDrawer`, Task 13).

- [ ] **Step 1: Editar `TarefaWorkflowSection.tsx`**

Remover o import de `TarefaWorkflowSelectModal` e o estado `modalMode`/`handleAssociar`. Remover o bloco de botões no header (`<Button ...>Alterar Workflow</Button>`, `<Button ...>Trocar etapa inicial</Button>`) — a seção passa a só exibir `renderSummary()` (incluindo agora departamento derivado e SLA, ver Step 2) e `renderHistorico()`, mais a ação de avançar etapa via `WorkflowRuntimeCard` (que já executa transições, não reatribui Workflow — continua aqui, é "pequena alteração operacional").

Corrigir o branch morto (achado do spec §2/§8):

```typescript
function eventoWorkflowLabel(tipo: string): string {
  if (tipo === "tarefa.workflow_etapa_alterada") return "Executou transição";
  if (tipo === "tarefa.atualizada") return "Mudança de Workflow";
  return tipo;
}
```

(troca de `"tarefa.workflow_associado"`, que nunca era publicado, por `"tarefa.atualizada"`, que passa a ser publicado de fato pela Task 7 quando o campo alterado é Workflow/Etapa. Se o payload do evento tiver `camposAlterados`, uma versão mais precisa seria checar se `"workflowId"` está entre eles — ver o formato real do evento em `useTarefaWorkflowHistorico.ts` antes de decidir; se `camposAlterados` já estiver disponível no evento retornado, preferir essa checagem a um match cru de `tipo`.)

- [ ] **Step 2: Adicionar departamento/SLA/responsáveis ao resumo**

No `renderSummary()`, dentro do `<dl>`, adicionar (usando os novos campos de `tarefa`, já propagados pela Task 10):

```tsx
          <EntityFieldRow label="Departamento (via Etapa)" value={tarefa.departamentoId} density="compact" />
          <EntityFieldRow label="SLA esperado" value={tarefa.slaHorasEsperado != null ? `${tarefa.slaHorasEsperado}h` : null} density="compact" />
          <EntityFieldRow label="Responsável principal" value={tarefa.responsavelPrincipalUsuarioId} density="compact" />
```

- [ ] **Step 3: Rodar typecheck + lint**

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
```

- [ ] **Step 4: Rodar a suíte completa do frontend**

```bash
docker compose exec taskfloww_front npm test
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/tarefas/TarefaWorkflowSection.tsx frontend/src/components/tarefas/TarefaPeekDrawer.tsx
git commit -m "refactor(tarefas): Visualizar vira consulta + pequenas acoes, configuracao de workflow sai do Peek"
```

---

### Task 15: `TarefasView.tsx` — nome do Cliente, toggle Lista/Kanban

**Files:**
- Modify: `frontend/src/components/tarefas/TarefasView.tsx`
- Test: `frontend/tests/tarefas/view.test.ts`

**Interfaces:**
- Consumes: `tarefa.clienteNomeExibicao` (Task 10).

- [ ] **Step 1: Escrever o teste**

Em `frontend/tests/tarefas/view.test.ts`, adicionar (mesmo padrão dos testes de fonte já existentes que fazem asserções sobre o texto do arquivo, ex.: "ClientesView não usa mocks"):

```typescript
test("TarefasView exibe clienteNomeExibicao, nunca clienteId bruto, na coluna Cliente", () => {
  const source = readFileSync(new URL("../../src/components/tarefas/TarefasView.tsx", import.meta.url), "utf-8");
  assert.ok(source.includes("clienteNomeExibicao"));
  assert.ok(!source.includes("tarefa.clienteId ?? \"-\""));
});
```

(Confirmar se o arquivo de teste já importa `readFileSync`/`fileURLToPath` — mesmo padrão usado por outros testes "não referencia X" já vistos nesta suíte; se não, adicionar o import.)

- [ ] **Step 2: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/view.test.ts
```

- [ ] **Step 3: Editar a célula da tabela**

Trocar:

```tsx
                  <td className={`${cell} text-[11px] font-normal text-zinc-500`}>{tarefa.clienteId ?? "-"}</td>
```

por:

```tsx
                  <td className={`${cell} text-[11px] font-normal text-zinc-500`}>{tarefa.clienteNomeExibicao ?? "-"}</td>
```

- [ ] **Step 4: Adicionar o toggle Lista/Kanban**

Adicionar estado:

```typescript
  const [visualizacao, setVisualizacao] = useState<"lista" | "kanban">("lista");
```

No `actions` do `PageHeader`, adicionar antes do botão "Nova Tarefa":

```tsx
            <div className="inline-flex rounded-full border border-zinc-200 p-0.5">
              <button
                type="button"
                onClick={() => setVisualizacao("lista")}
                className={`rounded-full px-3 py-1 text-[12px] ${visualizacao === "lista" ? "bg-zinc-900 text-white" : "text-zinc-500"}`}
              >
                Lista
              </button>
              <button
                type="button"
                onClick={() => setVisualizacao("kanban")}
                className={`rounded-full px-3 py-1 text-[12px] ${visualizacao === "kanban" ? "bg-zinc-900 text-white" : "text-zinc-500"}`}
              >
                Kanban
              </button>
            </div>
```

Envolver o bloco de indicadores + toolbar + tabela + paginação (tudo que hoje é sempre renderizado) em `{visualizacao === "lista" ? (<>...</>) : <TarefaKanbanBoard tarefas={tarefas} onTarefaChanged={refreshTarefas} onTarefaSelect={openTarefaPeek} />}` — import de `TarefaKanbanBoard` fica pendente até a Task 16 existir; **não commitar este Step isolado** — completar junto com a Task 16.

- [ ] **Step 5: Rodar teste do Step 1, confirmar PASS** (depende só da troca de `clienteId` por `clienteNomeExibicao` — pode ser verificado antes da Task 16 estar pronta, comentando temporariamente a referência a `TarefaKanbanBoard` ou avançando direto para a Task 16 antes de rodar)

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/view.test.ts
```

- [ ] **Step 6: Commit** (junto com a Task 16 — ver lá)

---

### Task 16: `TarefaKanbanBoard.tsx` — board por Workflow selecionado

**Files:**
- Create: `frontend/src/components/tarefas/TarefaKanbanBoard.tsx`
- Modify: `frontend/src/components/tarefas/TarefasView.tsx` (conclui a Task 15)
- Test: `frontend/tests/tarefas/kanban.test.ts` (novo)

**Interfaces:**
- Consumes: `KanbanColumn`/`KanbanCard` (`frontend/src/components/kanban/`, já existem — ler as duas props exatas antes de usar: `sed -n '1,40p' frontend/src/components/kanban/KanbanColumn.tsx frontend/src/components/kanban/KanbanCard.tsx`), `useWorkflowExecution.ts` (já existe, usado por `WorkflowRuntimeCard.tsx` — reaproveitar a mesma função de executar transição em vez de reimplementar).
- Produces: `TarefaKanbanBoard({ tarefas, onTarefaChanged, onTarefaSelect })`.

- [ ] **Step 1: Ler as interfaces reais antes de escrever qualquer código**

```bash
sed -n '1,60p' frontend/src/components/kanban/KanbanColumn.tsx
sed -n '1,60p' frontend/src/components/kanban/KanbanCard.tsx
cat frontend/src/components/tarefas/useWorkflowExecution.ts
```

`KanbanColumn`/`KanbanCard` hoje são tipados para `KanbanTask` (mock, campos como `client`/`assignee`/`sla` genéricos) — não vão encaixar diretamente em `Tarefa`. Duas opções, decidir com base no que a leitura acima revelar:
  - (a) Se `KanbanColumn`/`KanbanCard` forem genéricos o suficiente (aceitam `children`/render prop), reaproveitar como container puro.
  - (b) Se forem fortemente tipados para `KanbanTask` (mock), **não forçar reaproveitamento** — construir a coluna/card específicos de Tarefa do zero neste arquivo (mais simples e correto do que adaptar um tipo que não é o do domínio real), usando só o `DndContext`/`useSensor` do `@dnd-kit/core` (mesma biblioteca, já uma dependência do projeto) diretamente, sem depender de `KanbanColumn.tsx`/`KanbanCard.tsx`. Registrar essa decisão no comentário do arquivo novo, com o porquê.

- [ ] **Step 2: Escrever o teste (comportamento de agrupamento por etapa, função pura)**

```typescript
// frontend/tests/tarefas/kanban.test.ts
import assert from "node:assert/strict";
import test from "node:test";
import "../auth/helpers.mjs";

const { agruparTarefasPorEtapa } = await import("../../src/components/tarefas/TarefaKanbanBoard");

test("agruparTarefasPorEtapa agrupa por workflowEtapaId e ignora tarefas de outro workflow", () => {
  const tarefas = [
    { id: "t1", workflowId: "w1", workflowEtapaId: "e1" },
    { id: "t2", workflowId: "w1", workflowEtapaId: "e2" },
    { id: "t3", workflowId: "w1", workflowEtapaId: "e1" },
    { id: "t4", workflowId: "w2", workflowEtapaId: "e1" },
    { id: "t5", workflowId: "w1", workflowEtapaId: null },
  ] as Array<{ id: string; workflowId: string | null; workflowEtapaId: string | null }>;

  const grupos = agruparTarefasPorEtapa(tarefas, "w1");

  assert.deepEqual(grupos.get("e1")?.map((t) => t.id), ["t1", "t3"]);
  assert.deepEqual(grupos.get("e2")?.map((t) => t.id), ["t2"]);
  assert.equal(grupos.has("t4"), false);
});
```

- [ ] **Step 3: Rodar, confirmar falha**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/kanban.test.ts
```

- [ ] **Step 4: Implementar**

```tsx
"use client";

import { DndContext, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { useEffect, useMemo, useState } from "react";
import { Select } from "@/components/ui/Select";
import { workflowsBrowserClient } from "@/lib/api/workflow-client";
import { useWorkflowExecution } from "./useWorkflowExecution";
import type { Tarefa } from "@/types/tarefa-domain";
import type { Workflow, WorkflowEtapa } from "@/types/workflow-domain";

// Reaproveita a mesma execução de transição já usada por WorkflowRuntimeCard
// (useWorkflowExecution) — arrastar um card entre colunas é, semanticamente,
// a mesma ação de "avançar/retroceder etapa" já disponível no Peek, não uma
// implementação nova.
//
// KanbanColumn/KanbanCard (components/kanban/) NÃO são reaproveitados aqui:
// são tipados para KanbanTask (mock, campos client/assignee/sla genéricos
// sem relação com o domínio real de Tarefa) — adaptar o tipo teria mais
// risco de acoplamento incorreto do que construir a coluna/card específicos
// de Tarefa diretamente sobre @dnd-kit/core, que já é dependência do projeto.

export function agruparTarefasPorEtapa(
  tarefas: Array<Pick<Tarefa, "id" | "workflowId" | "workflowEtapaId">>,
  workflowId: string,
): Map<string, Array<Pick<Tarefa, "id" | "workflowId" | "workflowEtapaId">>> {
  const grupos = new Map<string, Array<Pick<Tarefa, "id" | "workflowId" | "workflowEtapaId">>>();
  for (const tarefa of tarefas) {
    if (tarefa.workflowId !== workflowId || !tarefa.workflowEtapaId) continue;
    const lista = grupos.get(tarefa.workflowEtapaId) ?? [];
    lista.push(tarefa);
    grupos.set(tarefa.workflowEtapaId, lista);
  }
  return grupos;
}

type TarefaKanbanCardProps = {
  tarefa: Tarefa;
  onSelect: () => void;
};

function TarefaKanbanCard({ tarefa, onSelect }: TarefaKanbanCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full rounded-2xl border border-zinc-200 bg-white p-3 text-left shadow-sm transition hover:border-zinc-300"
    >
      <p className="text-[11px] text-zinc-400">{tarefa.identificadorExibicao}</p>
      <p className="text-[13px] font-normal text-zinc-900">{tarefa.titulo}</p>
      <p className="mt-1 text-[11px] text-zinc-500">{tarefa.clienteNomeExibicao ?? "-"}</p>
    </button>
  );
}

type TarefaKanbanColumnProps = {
  etapa: WorkflowEtapa;
  tarefas: Tarefa[];
  onTarefaSelect: (tarefaId: string) => void;
};

function TarefaKanbanColumn({ etapa, tarefas, onTarefaSelect }: TarefaKanbanColumnProps) {
  return (
    <div className="flex w-72 shrink-0 flex-col gap-2 rounded-3xl bg-[#faf8f4] p-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
        {etapa.ordem} · {etapa.nome} ({tarefas.length})
      </p>
      <div className="flex flex-col gap-2">
        {tarefas.map((tarefa) => (
          <TarefaKanbanCard key={tarefa.id} tarefa={tarefa} onSelect={() => onTarefaSelect(tarefa.id)} />
        ))}
      </div>
    </div>
  );
}

type TarefaKanbanBoardProps = {
  tarefas: Tarefa[];
  onTarefaChanged: () => void;
  onTarefaSelect: (tarefaId: string) => void;
};

export function TarefaKanbanBoard({ tarefas, onTarefaChanged, onTarefaSelect }: TarefaKanbanBoardProps) {
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [workflowId, setWorkflowId] = useState<string>("");
  const [etapas, setEtapas] = useState<WorkflowEtapa[] | null>(null);
  const execucao = useWorkflowExecution("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  useEffect(() => {
    let cancelled = false;
    void workflowsBrowserClient.listarWorkflows({ status: "ativo", limit: 200 }).then((result) => {
      if (!cancelled && result.ok) setWorkflows(result.data.items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!workflowId) {
      setEtapas(null);
      return;
    }
    let cancelled = false;
    void workflowsBrowserClient.listarWorkflowEtapas({ workflowId, status: "ativa" }).then((result) => {
      if (!cancelled && result.ok) setEtapas(result.data.items.slice().sort((a, b) => a.ordem - b.ordem));
    });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const grupos = useMemo(() => agruparTarefasPorEtapa(tarefas, workflowId), [tarefas, workflowId]);

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const tarefaId = String(active.id);
    const novaEtapaId = String(over.id);
    const tarefa = tarefas.find((t) => t.id === tarefaId);
    if (!tarefa || tarefa.workflowEtapaId === novaEtapaId) return;

    const executou = await execucao.executarParaEtapa(tarefaId, novaEtapaId);
    if (executou) onTarefaChanged();
  }

  if (!workflowId) {
    return (
      <div className="rounded-3xl border border-dashed border-zinc-200 bg-[#faf8f4] p-6 text-center">
        <p className="mb-3 text-[12px] text-zinc-500">Selecione um Workflow para ver o board Kanban.</p>
        <div className="mx-auto max-w-xs">
          <Select
            label="Workflow"
            density="compact"
            value={workflowId}
            onChange={(event) => setWorkflowId(event.target.value)}
            disabled={workflows === null}
            options={[
              { value: "", label: "Selecione..." },
              ...(workflows ?? []).map((w) => ({ value: w.id, label: `${w.codigoInterno} · ${w.nome}` })),
            ]}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="max-w-xs">
        <Select
          label="Workflow"
          density="compact"
          value={workflowId}
          onChange={(event) => setWorkflowId(event.target.value)}
          options={[
            { value: "", label: "Selecione..." },
            ...(workflows ?? []).map((w) => ({ value: w.id, label: `${w.codigoInterno} · ${w.nome}` })),
          ]}
        />
      </div>

      {etapas === null ? (
        <p className="text-[12px] text-zinc-500">Carregando etapas...</p>
      ) : (
        <DndContext id="tarefa-kanban" sensors={sensors} onDragEnd={(event) => void handleDragEnd(event)}>
          <div className="overflow-x-auto">
            <div className="flex gap-4 pb-4">
              {etapas.map((etapa) => (
                <TarefaKanbanColumn
                  key={etapa.id}
                  etapa={etapa}
                  tarefas={tarefas.filter((t) => grupos.get(etapa.id)?.some((g) => g.id === t.id))}
                  onTarefaSelect={onTarefaSelect}
                />
              ))}
            </div>
          </div>
        </DndContext>
      )}
    </div>
  );
}
```

**Nota crítica**: `useWorkflowExecution(tarefaId)` (assinatura lida no Step 1) recebe o `tarefaId` fixo no momento do hook — não serve diretamente para "executar para qualquer tarefa arrastada" dentro de um board com várias tarefas. Ler o corpo completo de `useWorkflowExecution.ts` (Step 1) e decidir: (a) se ele expõe uma função `executar(transicaoId)` que poderia ser generalizada para aceitar `tarefaId` como parâmetro em vez de fixo no hook — nesse caso, refatorar `useWorkflowExecution` para aceitar o id por chamada (mudança pequena, mantém os demais consumidores como `WorkflowRuntimeCard` funcionando via um valor fixo); ou (b) criar uma função standalone em `useWorkflowExecution.ts` (`executarTransicaoParaTarefa(tarefaId, etapaDestinoId)`) que o hook e o Kanban board chamam. **Não inventar `execucao.executarParaEtapa` como texto solto** — este nome é um placeholder de design a resolver com o código real de `useWorkflowExecution.ts` antes de implementar; ajuste a Step 4 acima com a assinatura real encontrada no Step 1.

- [ ] **Step 5: Rodar, confirmar PASS**

```bash
docker compose exec taskfloww_front npm test -- tests/tarefas/kanban.test.ts
```

- [ ] **Step 6: Concluir a Task 15 — ligar `TarefaKanbanBoard` em `TarefasView.tsx`**

```typescript
import { TarefaKanbanBoard } from "./TarefaKanbanBoard";
```

```tsx
      {visualizacao === "kanban" ? (
        <TarefaKanbanBoard tarefas={visibleTarefas} onTarefaChanged={refreshTarefas} onTarefaSelect={openTarefaPeek} />
      ) : (
        <>
          {/* bloco existente: CadastroIndicators, CadastroToolbar, renderTarefasContent(), paginação */}
        </>
      )}
```

- [ ] **Step 7: Typecheck, lint, testes completos, build**

```bash
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
docker compose exec taskfloww_front npm test
docker compose exec taskfloww_front npm run build
```

- [ ] **Step 8: Commit (fecha Tasks 15 + 16)**

```bash
git add frontend/src/components/tarefas/TarefaKanbanBoard.tsx frontend/src/components/tarefas/TarefasView.tsx frontend/tests/tarefas/kanban.test.ts frontend/tests/tarefas/view.test.ts
git commit -m "feat(tarefas): Kanban por Workflow selecionado, arrastar card executa transicao de etapa"
```

---

## Verificação final (rodar tudo antes de considerar o plano concluído)

```bash
docker compose exec taskfloww_api pytest
docker compose exec taskfloww_front npm run typecheck
docker compose exec taskfloww_front npm run lint
docker compose exec taskfloww_front npm test
docker compose exec taskfloww_front npm run build
git status
git diff --stat
```

## Self-Review

**1. Cobertura do spec:**
- §3 (workflow+etapa na criação) → Tasks 5, 6, 11, 12.
- §4 (responsáveis, departamento derivado) → Tasks 2, 3, 6, 11, 13.
- §5 (template/ponto de extensão, SLA exibido) → Task 6 (`_aplicar_template_etapa`).
- §6 (RBAC por status) → Task 7.
- §7 (cliente sem UUID) → Tasks 4, 6 (`to_response`), 9, 10, 15.
- §8 (Lista+Kanban mesma fonte) → Task 16.
- §9 (Visualizar reduzido) → Task 14.
- §10 (reaproveitar eventos) → Task 7 (`TAREFA_ATUALIZADA`), nenhum evento novo criado em nenhuma task.
- §12 (fora de escopo: checklist etc.) → nenhuma task cria essas entidades; ponto de extensão isolado na Task 6.

**2. Placeholder scan:** Task 16 contém uma nota explícita marcando `execucao.executarParaEtapa` como não-confirmado — não é um placeholder típico ("TBD"), é uma decisão de design que depende de ler `useWorkflowExecution.ts` real antes de codar (marcado como Step 1 obrigatório antes do Step 4). Mantido assim deliberadamente porque escrever uma assinatura fictícia sem ter lido o arquivo real seria pior (código que não compila) do que documentar exatamente o que precisa ser resolvido e como decidir.

**3. Consistência de tipos:** `TarefaFormValue` (Task 11) usado identicamente em `TarefaCreateDrawer` (Task 12) e `TarefaEditDrawer` (Task 13) — mesmos 4 campos novos em ambos. `cliente_nome_exibicao`/`departamento_id`/`sla_horas_esperado` nomeados de forma consistente entre schema (Task 5), repository (Task 4), service (Task 6), tipos frontend (Task 9) e mapper (Task 10) — `snake_case` alias `camelCase` em todos, mesmo padrão do resto do projeto.

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-22-tarefas-creation-flow.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
