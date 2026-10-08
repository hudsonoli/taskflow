from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdministradorPlataforma(Base):
    """Autoridade da PLATAFORMA — separada do RBAC tenant (`usuarios.perfil_base`).

    Uma linha aqui diz que aquele usuário (que continua pertencendo à empresa dele) é Administrador da Plataforma:
    cadastra e administra empresas, branding e o primeiro Gestor de cada uma. NÃO é um perfil (`perfil_base` segue
    `admin|gestor|operador`), NÃO é superadmin de tenant e NÃO se decide por e-mail: a autorização consulta esta
    tabela a cada requisição (`require_platform_admin`), então revogar (`ativo=false`) vale já na requisição seguinte.

    O e-mail só aparece no CLI de bootstrap (`python -m app.cli.seed_platform_admin`), que localiza o usuário e cria
    a linha — nunca em runtime.

    Revogação é registrada (`revogado_em/por`), não apagada: o histórico de quem foi administrador fica. Reativar
    limpa a revogação (e o CHECK impede um estado incoerente).
    """

    __tablename__ = "administradores_plataforma"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_administradores_plataforma_usuario_id"),
        CheckConstraint("ativo OR revogado_em IS NOT NULL", name="ck_administradores_plataforma_revogacao"),
        Index("ix_administradores_plataforma_ativo", "ativo"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_por_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revogado_por_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
