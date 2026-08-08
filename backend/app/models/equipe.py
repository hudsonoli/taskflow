from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Equipe(Base):
    """Equipe (squad) da empresa.

    `departamento_id` é **nullable de propósito**: equipe sem departamento é *transversal*
    (gente de várias áreas em um squad de projeto) e é um caso legítimo, não um dado
    faltando. O departamento nunca é inferido pelo nome da equipe.

    Regra de exibição: Equipe aparece na interface **somente pelo nome**.
    """

    __tablename__ = "equipes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')",
            name="ck_equipes_status",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_equipes_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_equipes_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id", "ano_referencia", "sequencial_referencia", name="uq_equipes_empresa_ano_sequencial"
        ),
        # Nome único por EMPRESA (não por departamento) — decisão registrada no plano.
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_equipes_empresa_nome_normalizado"),
        Index("ix_equipes_empresa_id", "empresa_id"),
        Index("ix_equipes_status", "status"),
        Index("ix_equipes_codigo_referencia", "codigo_referencia"),
        Index("ix_equipes_codigo_interno", "codigo_interno"),
        Index("ix_equipes_nome_normalizado", "nome_normalizado"),
        Index("ix_equipes_departamento_id", "departamento_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    codigo_referencia: Mapped[str] = mapped_column(String(16), nullable=False)
    ano_referencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequencial_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    # NULL = equipe transversal. Arquivar o departamento NÃO arquiva a equipe nem rompe
    # este vínculo — apenas impede que novas equipes apontem para ele.
    departamento_id: Mapped[str | None] = mapped_column(
        ForeignKey("departamentos.id", ondelete="SET NULL"), nullable=True
    )
    # Garantido como membro pelo service (ver EquipeService._sincronizar_membros).
    lider_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    cor_identificacao: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento — ver docs/padrao-arquivamento.md.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
