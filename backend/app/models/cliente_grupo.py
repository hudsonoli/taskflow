from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClienteGrupo(Base):
    """Associação Cliente ↔ GrupoCliente (N:N).

    Tabela dedicada, nunca array JSON. Um cliente pode estar em vários grupos e um grupo
    reúne vários clientes; guardar isso como JSON dentro de `clientes` impediria integridade
    referencial e transformaria "quais clientes há no grupo X" numa varredura da tabela
    inteira.

    Guarda **estado atual**, não histórico: entradas e saídas ficam rastreáveis pelos
    eventos `cliente.grupo_adicionado` / `cliente.grupo_removido`. Mesmo desenho de
    `equipe_membros`.

    CASCADE é seguro porque nem Cliente nem GrupoCliente são apagados fisicamente (só
    arquivados); serve apenas para não deixar órfão caso uma remoção real aconteça em
    manutenção. Arquivar o cliente ou o grupo **não** apaga estas linhas — o vínculo
    histórico é preservado.
    """

    __tablename__ = "cliente_grupos"
    __table_args__ = (
        # A PK composta já cobre cliente→grupos; este índice cobre o sentido inverso,
        # "quais clientes pertencem a este grupo".
        Index("ix_cliente_grupos_grupo_cliente_id", "grupo_cliente_id"),
    )

    cliente_id: Mapped[str] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    grupo_cliente_id: Mapped[str] = mapped_column(
        ForeignKey("grupos_cliente.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
