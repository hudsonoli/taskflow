from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.workflow_modelo import WorkflowModelo
from app.models.workflow_modelo_etapa import WorkflowModeloEtapa
from app.models.workflow_modelo_etapa_departamento_responsavel import (
    WorkflowModeloEtapaDepartamentoResponsavel,
)
from app.models.workflow_modelo_etapa_responsavel import WorkflowModeloEtapaResponsavel

STATUS_ARQUIVADO = "arquivado"


class WorkflowModeloRepository:
    """Só persistência e consultas — regras de duplicidade, transição, arquivamento e
    eventos ficam no service."""

    def create(self, db: Session, workflow_modelo: WorkflowModelo) -> WorkflowModelo:
        db.add(workflow_modelo)
        db.flush()
        return workflow_modelo

    def get_by_id(self, db: Session, workflow_modelo_id: str) -> WorkflowModelo | None:
        return db.get(WorkflowModelo, workflow_modelo_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> WorkflowModelo | None:
        statement = select(WorkflowModelo).where(
            WorkflowModelo.empresa_id == empresa_id,
            WorkflowModelo.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome_normalizado(
        self, db: Session, *, empresa_id: str, nome_normalizado: str
    ) -> WorkflowModelo | None:
        """Qualquer status — a unicidade de nome vale entre ativos, inativos e arquivados."""
        statement = select(WorkflowModelo).where(
            WorkflowModelo.empresa_id == empresa_id,
            WorkflowModelo.nome_normalizado == nome_normalizado,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowModelo]:
        statement = select(WorkflowModelo).where(WorkflowModelo.empresa_id == empresa_id)

        if status:
            statement = statement.where(WorkflowModelo.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(WorkflowModelo.status != STATUS_ARQUIVADO)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    WorkflowModelo.nome.ilike(term),
                    WorkflowModelo.codigo_referencia.ilike(term),
                    WorkflowModelo.codigo_interno.ilike(term),
                )
            )

        statement = statement.order_by(WorkflowModelo.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def update(self, db: Session, workflow_modelo: WorkflowModelo) -> WorkflowModelo:
        db.add(workflow_modelo)
        db.flush()
        return workflow_modelo

    def list_etapas(self, db: Session, workflow_modelo_id: str) -> list[WorkflowModeloEtapa]:
        statement = (
            select(WorkflowModeloEtapa)
            .where(WorkflowModeloEtapa.workflow_modelo_id == workflow_modelo_id)
            .order_by(WorkflowModeloEtapa.ordem.asc())
        )
        return list(db.scalars(statement).all())

    def replace_etapas(
        self, db: Session, *, workflow_modelo_id: str, etapas: list[WorkflowModeloEtapa]
    ) -> list[WorkflowModeloEtapa]:
        """Substitui o conjunto inteiro de etapas do modelo.

        Apaga as existentes — o `ON DELETE CASCADE` do banco carrega junto os responsáveis
        de cada etapa apagada — e insere as novas, já com id/ordem definidos pelo chamador.
        Não há endpoint incremental de adicionar/remover etapa; o form sempre edita o array
        inteiro.
        """
        db.execute(delete(WorkflowModeloEtapa).where(WorkflowModeloEtapa.workflow_modelo_id == workflow_modelo_id))
        db.flush()
        for etapa in etapas:
            db.add(etapa)
        db.flush()
        return etapas

    def create_etapa_responsaveis(
        self, db: Session, responsaveis: list[WorkflowModeloEtapaResponsavel]
    ) -> None:
        for responsavel in responsaveis:
            db.add(responsavel)
        db.flush()

    def get_responsavel_ids_por_etapa(self, db: Session, etapa_ids: list[str]) -> dict[str, list[str]]:
        """Agrupa `usuario_id` por etapa — usado para montar `WorkflowModeloEtapaRead.usuarioResponsavelIds`
        sem depender de relationship ORM (o padrão do projeto é FK pura, sem relationship())."""
        resultado: dict[str, list[str]] = {etapa_id: [] for etapa_id in etapa_ids}
        if not etapa_ids:
            return resultado
        statement = select(
            WorkflowModeloEtapaResponsavel.workflow_modelo_etapa_id,
            WorkflowModeloEtapaResponsavel.usuario_id,
        ).where(WorkflowModeloEtapaResponsavel.workflow_modelo_etapa_id.in_(etapa_ids))
        for etapa_id, usuario_id in db.execute(statement):
            resultado[etapa_id].append(usuario_id)
        return resultado

    def create_etapa_departamentos_responsaveis(
        self, db: Session, responsaveis: list[WorkflowModeloEtapaDepartamentoResponsavel]
    ) -> None:
        for responsavel in responsaveis:
            db.add(responsavel)
        db.flush()

    def get_departamento_responsavel_ids_por_etapa(
        self, db: Session, etapa_ids: list[str]
    ) -> dict[str, list[str]]:
        """Mesma forma de `get_responsavel_ids_por_etapa`, lado departamento."""
        resultado: dict[str, list[str]] = {etapa_id: [] for etapa_id in etapa_ids}
        if not etapa_ids:
            return resultado
        statement = select(
            WorkflowModeloEtapaDepartamentoResponsavel.workflow_modelo_etapa_id,
            WorkflowModeloEtapaDepartamentoResponsavel.departamento_id,
        ).where(WorkflowModeloEtapaDepartamentoResponsavel.workflow_modelo_etapa_id.in_(etapa_ids))
        for etapa_id, departamento_id in db.execute(statement):
            resultado[etapa_id].append(departamento_id)
        return resultado

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[WorkflowModelo]:
        """Só ativo — sem referência histórica a resolver aqui (ver docstring do schema)."""
        statement = (
            select(WorkflowModelo)
            .where(WorkflowModelo.empresa_id == empresa_id, WorkflowModelo.status == "ativo")
            .order_by(WorkflowModelo.nome.asc())
        )
        return list(db.scalars(statement).all())
