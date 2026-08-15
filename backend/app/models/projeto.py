from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class Projeto(Base):
    """Projeto da agência — o trabalho contratado, sob o qual as demandas acontecem.

    ## Identidade

    **Dois identificadores, não três:**

    - `id`: UUID técnico, usado em PK/FK e rotas. Nunca exibido;
    - `codigo_referencia` (P26000001): identidade de negócio, imutável e pesquisável.

    Não há `codigo_interno`. Ele existiu na Fase 2D como "chave de importação" e foi removido
    na microfase 2D.1 (migration `9c2f8ab41d63`), quando ficou decidido que **não haverá
    importação histórica de Projetos** — eles nascem vazios e são criados pela interface.

    Sem importação a coluna não tinha função, e o levantamento mostrou que nunca teve: o único
    caminho de escrita gravava `codigo_interno = codigo_referencia` (cópia literal), nenhum
    componente a exibia, e a busca fazia um `OR codigo_interno ILIKE` sempre redundante por
    comparar o mesmo valor duas vezes. Diferente de Cliente e Fornecedor, Projeto nunca chegou
    a ter um `create_*_com_codigo_legado` — não havia seed nem importador para chamá-lo.

    Demanda segue o mesmo desenho — UUID + `codigo_referencia`, sem ponte de importação.

    ## Unicidade: por (cliente, nome), não por nome

    Projeto é entidade **interna** — a agência controla o nome, diferente de Cliente e
    Fornecedor, onde o mundo controla (ver docs/padrao-entidades-externas.md). Mas o escopo
    do nome é o cliente, não a agência: dois "Campanha de Natal" para clientes diferentes são
    cadastros legítimos; dois para o **mesmo** cliente são erro.

    Daí `UNIQUE(empresa_id, cliente_id, nome_normalizado)`. Como o Postgres considera `NULL`
    distinto de `NULL`, essa constraint sozinha deixaria de valer justamente nos projetos
    internos (sem cliente) — por isso existe também o índice parcial
    `uq_projetos_empresa_nome_sem_cliente`, com `WHERE cliente_id IS NULL`.

    A regra veio de raciocínio de domínio, não de levantamento: os 3 registros do mock eram
    fabricados, com nomes e clientes todos distintos, e não provam nada. É revisável quando
    houver base real.

    ## modeloCampanha em JSONB

    Os itens do modelo de campanha referenciam TipoTarefa e Workflow, que **ainda não têm
    tabela**. Guardá-los como value objects (mesmo tratamento de `contatos` em Cliente)
    preserva a interface sem criar FK para domínio inexistente. Os ids legados ficam como
    texto e viram relação real em migration própria quando esses domínios migrarem.

    ## O que saiu do mock

    - `agenciaId`: constante `"agencia-principal"`, sem tabela e sem entidade — era resíduo;
    - `historico[]`: virou evento de domínio (`projeto.*`), publicado na transação da escrita;
    - `arquivos[]`: vazio nos três registros e dependente de upload — fica para a fase própria;
    - `equipe[]`: virou `projeto_equipe_membros`, sem replicar nome nem departamento (vem por
      join, como já se faz em Equipe).
    """

    __tablename__ = "projetos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planejamento', 'ativo', 'pausado', 'concluido', 'cancelado', 'arquivado')",
            name="ck_projetos_status",
        ),
        CheckConstraint("prioridade IN ('baixa', 'media', 'alta')", name="ck_projetos_prioridade"),
        # Fim previsto antes do início é dado impossível, não preferência de interface.
        CheckConstraint(
            "data_inicio IS NULL OR data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio",
            name="ck_projetos_periodo",
        ),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_projetos_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id", "ano_referencia", "sequencial_referencia", name="uq_projetos_empresa_ano_sequencial"
        ),
        # Nome único POR CLIENTE — ver "Unicidade" na docstring.
        UniqueConstraint(
            "empresa_id", "cliente_id", "nome_normalizado", name="uq_projetos_empresa_cliente_nome"
        ),
        # O par acima não cobre `cliente_id IS NULL` (o Postgres trata NULL como distinto de
        # NULL), então a regra sumiria justamente nos projetos internos. Este índice parcial
        # fecha o buraco. Precisa estar declarado aqui, não só na migration: sem isso o
        # `alembic check` compara metadata com banco e pede para removê-lo.
        Index(
            "uq_projetos_empresa_nome_sem_cliente",
            "empresa_id",
            "nome_normalizado",
            unique=True,
            postgresql_where=text("cliente_id IS NULL"),
        ),
        Index("ix_projetos_empresa_id", "empresa_id"),
        Index("ix_projetos_status", "status"),
        Index("ix_projetos_codigo_referencia", "codigo_referencia"),
        Index("ix_projetos_nome_normalizado", "nome_normalizado"),
        Index("ix_projetos_cliente_id", "cliente_id"),
    )

    # --- identidade técnica -------------------------------------------------------
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    # --- identidade de negócio ----------------------------------------------------
    codigo_referencia: Mapped[str] = mapped_column(String(16), nullable=False)
    ano_referencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequencial_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    campanha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- estado -------------------------------------------------------------------
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    prioridade: Mapped[str] = mapped_column(String(16), nullable=False)

    # Nullable: projeto interno da agência existe e não tem cliente. SET NULL porque
    # arquivar/remover um cliente nunca pode derrubar o histórico do projeto.
    cliente_id: Mapped[str | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )

    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Value objects — ver "modeloCampanha em JSONB" na docstring.
    modelo_campanha_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    modelo_campanha: Mapped[list[dict[str, Any]] | None] = mapped_column(json_type, nullable=True)

    # --- auditoria ----------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
