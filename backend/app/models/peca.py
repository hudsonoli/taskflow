from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Peca(Base):
    """Peça do catálogo (Fase 2G.4) — modelo reutilizável de peça/serviço: tempo, valor de
    tabela, valores de sindicato e briefing padrão. É CATÁLOGO, não execução: sem vínculo com
    Demanda/Projeto/Modelo de Campanha nesta fase (ver docstring da migration).

    Sem UNIQUE(empresa_id, nome) de propósito — o catálogo importado tem nomes que se repetem
    legitimamente (variação histórica de nomenclatura); não normalizar nem mesclar.

    `categoria_id` nullable: o catálogo importado (Fase 2G.4) não trouxe categoria nenhuma —
    fica para classificação manual, via a API real, depois do import.

    `codigo_legado`: identidade do catálogo importado original (`peca-imp-NNN` em
    app/cli/data/pecas_seed.json) — existe só para o import ser idempotente por
    empresa+código, nunca por nome (ver app/cli/importar_pecas.py). Peça criada pela UI não
    recebe um.
    """

    __tablename__ = "pecas"
    __table_args__ = (
        CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name="ck_pecas_status"),
        UniqueConstraint("empresa_id", "codigo_legado", name="uq_pecas_empresa_codigo_legado"),
        Index("ix_pecas_empresa_id", "empresa_id"),
        Index("ix_pecas_categoria_id", "categoria_id"),
        Index("ix_pecas_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    categoria_id: Mapped[str | None] = mapped_column(ForeignKey("categorias_peca.id"), nullable=True)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_legado: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tempo_estimado_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tempo_medio_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Sempre NULL nesta fase — só é preenchido a partir de sessões de trabalho reais vinculadas
    # a esta Peça, e esse vínculo (Demanda↔Peça) ainda não existe (ver docstring da migration).
    tempo_calculado_execucao_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    valor_tabela_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sindicato_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valor_sindicato_criacao_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    valor_sindicato_adaptacao_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    valor_sindicato_finalizacao_centavos: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    briefing_padrao: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Mesmo padrão de
    # TipoTarefa: 3 estados (ativo/inativo/arquivado), "inativo" é reversível via PATCH,
    # "arquivado" só via arquivar/restaurar.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
