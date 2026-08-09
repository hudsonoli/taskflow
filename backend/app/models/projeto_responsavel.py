from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjetoResponsavel(Base):
    """Associação Projeto ↔ Usuário responsável (`responsavelIds` no mock).

    Estado atual, não histórico: entradas e saídas ficam rastreáveis pelos eventos
    `projeto.responsavel_adicionado` / `projeto.responsavel_removido`.

    Distinta de `projeto_equipe_membros`: responsável responde pelo projeto, membro trabalha
    nele. A mesma pessoa pode ser as duas coisas, e o mock já tratava as duas listas
    separadamente.
    """

    __tablename__ = "projeto_responsaveis"
    __table_args__ = (
        # A PK composta cobre projeto→responsáveis; este índice cobre o inverso
        # ("de quais projetos esta pessoa é responsável").
        Index("ix_projeto_responsaveis_usuario_id", "usuario_id"),
    )

    # CASCADE é seguro: projeto nunca é apagado fisicamente (só arquivado). Serve para não
    # deixar órfão numa remoção real de manutenção.
    projeto_id: Mapped[str] = mapped_column(
        ForeignKey("projetos.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
