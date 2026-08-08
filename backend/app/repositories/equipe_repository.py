from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.equipe import Equipe
from app.models.equipe_membro import EquipeMembro

STATUS_ARQUIVADO = "arquivado"


class EquipeRepository:
    """Só persistência e consultas — regras de líder, membros, duplicidade, transição e
    eventos ficam no service."""

    def create(self, db: Session, equipe: Equipe) -> Equipe:
        db.add(equipe)
        db.flush()
        return equipe

    def get_by_id(self, db: Session, equipe_id: str) -> Equipe | None:
        return db.get(Equipe, equipe_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Equipe | None:
        statement = select(Equipe).where(
            Equipe.empresa_id == empresa_id,
            Equipe.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_nome_normalizado(self, db: Session, *, empresa_id: str, nome_normalizado: str) -> Equipe | None:
        """Qualquer status — a unicidade de nome vale entre ativas, inativas e arquivadas."""
        statement = select(Equipe).where(
            Equipe.empresa_id == empresa_id,
            Equipe.nome_normalizado == nome_normalizado,
        )
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Equipe]:
        statement = select(Equipe).where(Equipe.empresa_id == empresa_id)

        if status:
            statement = statement.where(Equipe.status == status)
        else:
            statement = statement.where(Equipe.status != STATUS_ARQUIVADO)
        if departamento_id:
            statement = statement.where(Equipe.departamento_id == departamento_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Equipe.nome.ilike(term),
                    Equipe.codigo_referencia.ilike(term),
                    Equipe.codigo_interno.ilike(term),
                )
            )

        statement = statement.order_by(Equipe.nome.asc()).limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Equipe]:
        statement = select(Equipe).where(Equipe.empresa_id == empresa_id).order_by(Equipe.nome.asc())
        return list(db.scalars(statement).all())

    def update(self, db: Session, equipe: Equipe) -> Equipe:
        db.add(equipe)
        db.flush()
        return equipe

    # ---------------------------------------------------------------------------------
    # Membros
    # ---------------------------------------------------------------------------------

    def listar_membro_ids(self, db: Session, equipe_id: str) -> list[str]:
        statement = select(EquipeMembro.usuario_id).where(EquipeMembro.equipe_id == equipe_id)
        return list(db.scalars(statement).all())

    def adicionar_membro(self, db: Session, *, equipe_id: str, usuario_id: str, created_at) -> None:
        db.add(EquipeMembro(equipe_id=equipe_id, usuario_id=usuario_id, created_at=created_at))
        db.flush()

    def remover_membro(self, db: Session, *, equipe_id: str, usuario_id: str) -> None:
        db.execute(
            delete(EquipeMembro).where(
                EquipeMembro.equipe_id == equipe_id,
                EquipeMembro.usuario_id == usuario_id,
            )
        )
        db.flush()
