from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaComentario(Base):
    """Comentário de uma Demanda — primeira versão (Fase 2E.4).

    Sem `empresa_id` próprio, mesmo raciocínio de `DemandaChecklistItem`/`DemandaArquivo`
    (Fase 2E.3): isolamento via `demanda_id`, resolvido sempre através do escopo da Demanda.

    Deliberadamente **sem** anexo, @mention, reação, thread ou distinção interno/externo —
    essas regras não estão definidas ainda (ver instrução da Fase 2E.4). `editado_em` guarda
    só o timestamp da última edição, não um histórico de versões do texto.

    Exclusão é física (mesmo padrão de checklist) — o evento de domínio
    `demanda.comentario_removido` é o que preserva o rastro, mesmo com a linha apagada.
    """

    __tablename__ = "demanda_comentarios"
    __table_args__ = (
        Index("ix_demanda_comentarios_demanda_id", "demanda_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)
    # SET NULL: autor removido/inativado depois não pode derrubar o comentário nem seu
    # histórico — o evento de remoção/edição já carrega o id no payload quando necessário.
    autor_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    texto: Mapped[str] = mapped_column(String(4000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    editado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
