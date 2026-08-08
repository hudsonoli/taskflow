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


class Departamento(Base):
    """Departamento da empresa.

    Três identificadores convivem de propósito (ver docs/padrao-migracao-dominio.md):
    - `id`: UUID técnico, usado em PK/FK e rotas. Nunca exibido;
    - `codigo_referencia` (D26000001): código oficial de negócio, imutável e pesquisável;
    - `codigo_interno` (`dep-criacao`): **ponte transitória** para os mocks de Projeto e
      Demanda, que ainda referenciam esses valores. Sai quando esses domínios migrarem.

    Regra de exibição: Departamento aparece na interface **somente pelo nome** — sem
    `#sequencial`, sem código concatenado.
    """

    __tablename__ = "departamentos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')",
            name="ck_departamentos_status",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_departamentos_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_departamentos_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id",
            "ano_referencia",
            "sequencial_referencia",
            name="uq_departamentos_empresa_ano_sequencial",
        ),
        # Unicidade de nome case-insensitive valendo entre ativos, inativos E arquivados.
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_departamentos_empresa_nome_normalizado"),
        Index("ix_departamentos_empresa_id", "empresa_id"),
        Index("ix_departamentos_status", "status"),
        Index("ix_departamentos_codigo_referencia", "codigo_referencia"),
        Index("ix_departamentos_codigo_interno", "codigo_interno"),
        Index("ix_departamentos_nome_normalizado", "nome_normalizado"),
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
    # Opcional: Tráfego e Orçamento/Produção não têm responsável definido hoje. Sem
    # ForeignKey com cascade — inativar o responsável não pode derrubar o departamento.
    responsavel_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    cor_identificacao: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Colunas de
    # ator são String(36) sem FK, como em usuario.py e grupo_cliente.py: são auditoria
    # solta, não relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
