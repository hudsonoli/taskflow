from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class Cliente(Base):
    """Cliente da agência — primeira entidade comercial real.

    ## Identidade

    Três identificadores convivem, no mesmo padrão de Departamento e Equipe:
    - `id`: UUID técnico, usado em PK/FK e rotas. Nunca exibido;
    - `codigo_referencia` (C26000001): código oficial de negócio, imutável e pesquisável —
      **a única identidade funcional**;
    - `codigo_interno` (`#2001`): **ponte transitória** para os mocks de Projeto e Demanda,
      que ainda referenciam clientes por esse valor. Sai quando esses domínios migrarem.

    **Não há UNIQUE de `nome` nem de `documento`** — diferente de Departamento e Equipe, e
    de propósito. Departamento é entidade organizacional interna, onde nome único é regra
    real; Cliente é entidade externa, onde nome é rótulo comercial. A base real prova os
    dois casos: filiais com o mesmo nome e CNPJ diferente (BRETAS CENTRO em duas unidades) e
    empreendimentos com nomes diferentes sob o mesmo CNPJ (os três "CMO – Varandas"). Ambos
    são cadastros legítimos, e distorcer o dado para caber numa constraint seria pior que a
    duplicidade.

    Coincidência de nome e/ou documento gera **aviso de possível duplicidade** na resposta
    da API (ver ClienteService._detectar_possiveis_duplicidades), nunca bloqueio.
    Deduplicação de verdade é funcionalidade futura, com revisão humana — regra de negócio,
    não constraint de banco.

    ## Por que `contatos` é JSONB e Grupo é tabela

    `contatos` são **value objects**: só existem dentro do cliente, não são referenciados
    de fora, não têm ciclo de vida próprio e ninguém consulta "todos os contatos do
    sistema". Promovê-los a tabela criaria FK, migrations e joins sem nenhum ganho.

    Grupo de Cliente é o oposto: entidade própria, com código de referência, arquivável,
    consultada isoladamente e compartilhada entre clientes. A associação é N:N em tabela
    dedicada (`cliente_grupos`) — nunca um array JSON, que impediria integridade
    referencial e tornaria "quais clientes há no grupo X" uma varredura.

    ## Histórico

    Não há tabela de histórico. Toda mudança relevante vira evento de domínio
    (`cliente.*` em app/domain/event_types.py), publicado na mesma transação da escrita.
    """

    __tablename__ = "clientes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'suspenso', 'inativo', 'arquivado')",
            name="ck_clientes_status",
        ),
        CheckConstraint("tipo_documento IN ('cnpj', 'cpf')", name="ck_clientes_tipo_documento"),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_clientes_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_clientes_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id",
            "ano_referencia",
            "sequencial_referencia",
            name="uq_clientes_empresa_ano_sequencial",
        ),
        # NÃO há UNIQUE de nome nem de documento — ver "Identidade" na docstring acima.
        Index("ix_clientes_empresa_id", "empresa_id"),
        Index("ix_clientes_status", "status"),
        Index("ix_clientes_codigo_referencia", "codigo_referencia"),
        Index("ix_clientes_codigo_interno", "codigo_interno"),
        Index("ix_clientes_nome_normalizado", "nome_normalizado"),
        Index("ix_clientes_documento_normalizado", "documento_normalizado"),
        Index("ix_clientes_responsavel_comercial_id", "responsavel_comercial_id"),
    )

    # --- identidade técnica -------------------------------------------------------
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    # --- identidade de negócio ----------------------------------------------------
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    codigo_referencia: Mapped[str] = mapped_column(String(16), nullable=False)
    ano_referencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequencial_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    razao_social: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_documento: Mapped[str] = mapped_column(String(8), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Só dígitos — permite localizar "12.345.678/0001-90" digitando "12345678".
    # Não é UNIQUE: a base importada tem 123 clientes com documento em branco, e a
    # duplicidade de documento é regra de negócio a decidir, não invariante de schema.
    documento_normalizado: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- estado -------------------------------------------------------------------
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # --- dados comerciais ---------------------------------------------------------
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco_completo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    segmento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origem: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Sem cascade: inativar o responsável comercial não pode derrubar o cliente.
    responsavel_comercial_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    cliente_referencial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    avisar_conclusao_por_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Financeiro — visível só a perfis com acesso financeiro (regra de apresentação).
    # Centavos como inteiro: dinheiro nunca em float.
    fee_mensal_centavos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horas_contratadas_mes: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cor_identificacao: Mapped[str] = mapped_column(String(32), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Value objects: lista de {id, nome, email, telefone, cargo, recebeEntregas}.
    contatos: Mapped[list[dict[str, Any]] | None] = mapped_column(json_type, nullable=True)

    # --- auditoria ----------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Colunas de
    # ator são String(36) sem FK: auditoria solta, não relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)
