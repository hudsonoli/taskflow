from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaComentarioMencao(Base):
    """Quem está @mencionado, de forma ESTRUTURADA, em um comentário (identidade = `usuario_id`, nunca o nome digitado).

    A chave (comentário, usuário) é a deduplicação: cada pessoa é mencionada UMA vez por comentário e só a inserção efetiva (`ON CONFLICT DO NOTHING … RETURNING`)
    gera notificação — retry, duplo clique e edições concorrentes não duplicam. Remover a menção do texto apaga a linha (o estado da origem reflete o texto); a notificação
    já entregue é histórico e fica. Mencionar de novo depois de removida é uma NOVA menção explícita e notifica de novo.

    A notificação em si NÃO é uma tabela daqui: é o evento `demanda.usuarios_mencionados` (central de notificações existente). Apagar o comentário ou o usuário apaga as linhas (CASCADE).
    """

    __tablename__ = "demanda_comentario_mencoes"
    __table_args__ = (
        Index("ix_demanda_comentario_mencoes_empresa_id", "empresa_id"),
        Index("ix_demanda_comentario_mencoes_usuario_id", "usuario_id"),
    )

    comentario_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("demanda_comentarios.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
