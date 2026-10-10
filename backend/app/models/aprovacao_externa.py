from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DECISOES_APROVACAO_EXTERNA = ("aprovada", "ajustes_solicitados")
MOTIVOS_REVOGACAO = ("manual", "substituida", "etapa_decidida_internamente")


class AprovacaoExterna(Base):
    """Solicitação de aprovação EXTERNA (Fase 9B): um link-capability que deixa um CLIENTE aprovar ou pedir ajustes de artefatos da Demanda, sem
    conta, sem sessão e sem `Usuario`.

    - O token (256 bits, `secrets.token_urlsafe(32)`) NUNCA é persistido: só o SHA-256 (`token_hash`). Vale como capability: resolve internamente empresa,
      Demanda, etapa e artefatos — o cliente não escolhe ID nenhum;
    - vinculada a UMA etapa de aprovação (`workflow_etapa_id`); só decide enquanto a etapa for a atual;
    - estado DERIVADO (sem coluna `status`): decidida (`decisao`) > revogada (`revogada_em`) > expirada (`expira_em`) > obsoleta (a etapa deixou de ser a atual)
      > pendente. Decisão e revogação são mutuamente exclusivas: decisão é final;
    - no máximo UMA não decidida/não revogada por etapa (índice único parcial; expirada continua "aberta" até ser revogada/substituída — `NOW()` não entra
      em índice, a expiração é derivada);
    - identidade externa DECLARADA, não verificada (`nome_aprovador`, `email_aprovador`); `destinatario_*` é só "para quem o link foi destinado". Sem IP,
      user-agent ou geolocalização;
    - evidência: retenção operacional inicial de 5 anos (sem job de purge nesta fase — ver docs/aprovacao-externa.md).
    """

    __tablename__ = "aprovacoes_externas"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_aprovacoes_externas_token_hash"),
        CheckConstraint("decisao IS NULL OR decisao IN ('aprovada', 'ajustes_solicitados')", name="ck_aprovacoes_externas_decisao"),
        CheckConstraint("(decisao IS NULL) = (decidida_em IS NULL)", name="ck_aprovacoes_externas_decidida_em"),
        CheckConstraint("decisao IS NULL OR nome_aprovador IS NOT NULL", name="ck_aprovacoes_externas_nome_aprovador"),
        CheckConstraint(
            "decisao IS DISTINCT FROM 'ajustes_solicitados' OR motivo IS NOT NULL", name="ck_aprovacoes_externas_motivo_ajustes"
        ),
        CheckConstraint("decisao IS NULL OR revogada_em IS NULL", name="ck_aprovacoes_externas_decisao_ou_revogada"),
        CheckConstraint("(revogada_em IS NULL) = (revogada_motivo IS NULL)", name="ck_aprovacoes_externas_revogada_motivo"),
        CheckConstraint(
            "revogada_motivo IS NULL OR revogada_motivo IN ('manual', 'substituida', 'etapa_decidida_internamente')",
            name="ck_aprovacoes_externas_revogada_motivo_valores",
        ),
        CheckConstraint("expira_em > criada_em", name="ck_aprovacoes_externas_expira_em"),
        # Uma solicitação em aberto (nem decidida nem revogada) por etapa. A expiração é derivada, então uma expirada ainda ocupa o índice
        # até ser revogada — criar um novo link revoga a anterior na mesma transação.
        Index(
            "uq_aprovacoes_externas_aberta_por_etapa",
            "workflow_etapa_id",
            unique=True,
            postgresql_where=text("decisao IS NULL AND revogada_em IS NULL"),
        ),
        Index("ix_aprovacoes_externas_empresa_id", "empresa_id"),
        Index("ix_aprovacoes_externas_demanda_id", "demanda_id"),
        Index("ix_aprovacoes_externas_workflow_etapa_id", "workflow_etapa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id"), nullable=False)
    workflow_etapa_id: Mapped[str] = mapped_column(ForeignKey("demanda_workflow_etapas.id"), nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    instrucao: Mapped[str | None] = mapped_column(Text, nullable=True)

    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criada_por_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revogada_por_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    revogada_motivo: Mapped[str | None] = mapped_column(String(40), nullable=True)

    decisao: Mapped[str | None] = mapped_column(String(24), nullable=True)
    decidida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nome_aprovador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email_aprovador: Mapped[str | None] = mapped_column(String(255), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "Para quem o link foi destinado" — NÃO é quem decidiu nem foi autenticado.
    destinatario_nome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destinatario_email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AprovacaoExternaArquivo(Base):
    """Artefato da solicitação: SNAPSHOT imutável (nome, tamanho, MIME, SHA-256) do arquivo no momento da criação. `arquivo_id` é só a referência viva:
    vira NULL se o arquivo for excluído (permitido apenas para solicitação revogada sem decisão — ver DemandaArquivoService), e o snapshot preserva a evidência.
    PK por `(aprovacao_externa_id, ordem)`: o cliente só enxerga a ORDEM (1..N), nunca o UUID do arquivo."""

    __tablename__ = "aprovacao_externa_arquivos"
    __table_args__ = (
        CheckConstraint("ordem >= 1", name="ck_aprovacao_externa_arquivos_ordem"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_aprovacao_externa_arquivos_sha256"),
        # o mesmo arquivo não entra duas vezes na mesma solicitação (NULLs, de arquivos já excluídos, não colidem)
        UniqueConstraint("aprovacao_externa_id", "arquivo_id", name="uq_aprovacao_externa_arquivos_arquivo"),
        Index("ix_aprovacao_externa_arquivos_arquivo_id", "arquivo_id"),
    )

    aprovacao_externa_id: Mapped[str] = mapped_column(ForeignKey("aprovacoes_externas.id", ondelete="CASCADE"), primary_key=True)
    ordem: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    arquivo_id: Mapped[str | None] = mapped_column(ForeignKey("demanda_arquivos.id", ondelete="SET NULL"), nullable=True)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
