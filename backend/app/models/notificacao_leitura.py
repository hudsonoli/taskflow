from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificacaoLeitura(Base):
    """Estado "lida" de uma notificação PARA UM usuário.

    As notificações não são registros próprios: são uma visão tipada dos eventos de domínio (`eventos`)
    que dizem respeito às demandas do usuário. O que não existia — e é a única coisa persistida aqui — é
    saber QUEM já leu QUAL evento. Sem linha = não lida. Marcar uma ou todas como lidas só insere linhas;
    nunca duplica nem altera o evento.
    """

    __tablename__ = "notificacao_leituras"
    __table_args__ = (
        Index("ix_notificacao_leituras_empresa_id", "empresa_id"),
        Index("ix_notificacao_leituras_evento_id", "evento_id"),
    )

    usuario_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    evento_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("eventos.id", ondelete="CASCADE"), primary_key=True
    )
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False)
    lida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
