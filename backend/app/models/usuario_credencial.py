from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsuarioCredencial(Base):
    __tablename__ = "usuario_credenciais"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_usuario_credenciais_usuario_id"),
        # Token de redefinição é aleatório de alta entropia (32 bytes): colisão é inviável, e a
        # UNIQUE também é o índice do lookup `SHA-256(token) -> credencial` (ver migration 0037).
        # Múltiplos NULL são permitidos (a imensa maioria nunca tem reset pendente).
        UniqueConstraint("reset_senha_token_hash", name="uq_usuario_credenciais_reset_senha_token_hash"),
        Index("ix_usuario_credenciais_usuario_id", "usuario_id"),
        Index("ix_usuario_credenciais_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    senha_definida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    senha_alterada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tentativas_falhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Senha temporária (definida por seed/reset) — usuário fica bloqueado do restante da
    # aplicação (ver dependency get_current_user_password_ready) até trocar via /auth/alterar-senha.
    senha_deve_ser_alterada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Recuperação de senha self-service ("Esqueci minha senha"). No máximo UM reset ativo por
    # credencial: nova solicitação substitui o anterior. NUNCA o token em si — só o SHA-256 em
    # hexadecimal (64 caracteres). `solicitado_em` também é o relógio do cooldown entre pedidos
    # e sobrevive à limpeza do token quando o envio do e-mail falha. Os três voltam a NULL no uso
    # com sucesso e na troca/definição de senha por qualquer outro caminho.
    reset_senha_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reset_senha_expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_senha_solicitado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
