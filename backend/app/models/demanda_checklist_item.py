from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaChecklistItem(Base):
    """Item de checklist de uma Demanda — primeira versão (Fase 2E.3).

    Sem `empresa_id` próprio: o isolamento de tenant vem de `demanda_id` (mesmo padrão de
    `DemandaWorkflowEtapa`) — toda leitura/escrita passa antes pela resolução escopada da
    própria Demanda (`resolver_escopo_demanda`), então uma segunda coluna de empresa aqui
    seria dado redundante, nunca consultado isoladamente.

    Deliberadamente **sem** responsável, departamento, prazo, SLA ou dependência entre itens
    — essas regras não estão definidas ainda (ver instrução da Fase 2E.3). `ordem` é a única
    forma de sequenciamento, reatribuída inteira a cada reordenação (0..n-1), nunca esparsa.

    Exclusão é **física**, não segue o padrão de arquivamento das entidades centrais — um item
    de checklist é um subitem operacional, não um registro auditável por si (o evento de
    domínio `demanda.checklist_item_excluido` é o que fica).
    """

    __tablename__ = "demanda_checklist_itens"
    __table_args__ = (
        Index("ix_demanda_checklist_itens_demanda_ordem", "demanda_id", "ordem"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)

    texto: Mapped[str] = mapped_column(String(500), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    concluido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SET NULL: usuário concluído/removido depois não pode derrubar o item nem seu histórico.
    concluido_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
