from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EquipeMembro(Base):
    """Associação Equipe ↔ Usuário.

    Guarda **estado atual**, não histórico temporal: entradas e saídas ficam rastreáveis
    pelos eventos `equipe.membro_adicionado` / `equipe.membro_removido`. Se um dia for
    preciso responder "quem estava na equipe em março" direto em SQL, acrescentam-se
    `entrou_em`/`saiu_em` — mudança aditiva, sem quebrar consultas existentes.

    Membros podem pertencer a departamentos diferentes entre si e diferentes do
    departamento da equipe. Arquivar a equipe **não** apaga estas linhas.
    """

    __tablename__ = "equipe_membros"
    __table_args__ = (
        # Consulta "de quais equipes esta pessoa faz parte" — a PK composta já cobre o
        # sentido equipe→membros, este índice cobre o inverso.
        Index("ix_equipe_membros_usuario_id", "usuario_id"),
    )

    # CASCADE aqui é seguro porque equipe nunca é apagada fisicamente (só arquivada); serve
    # apenas para não deixar órfão caso uma remoção real aconteça em manutenção.
    equipe_id: Mapped[str] = mapped_column(
        ForeignKey("equipes.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
