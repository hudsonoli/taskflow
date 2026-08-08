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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Fornecedor(Base):
    """Fornecedor da agência — gráficas, produtoras, freelancers, mídia.

    ## Identidade

    Mesmo padrão de Departamento, Equipe e Cliente:
    - `id`: UUID técnico, usado em PK/FK e rotas. Nunca exibido;
    - `codigo_referencia` (F26000001): código oficial de negócio, imutável e pesquisável —
      **a única identidade funcional**;
    - `codigo_interno` (`fornecedor-imp-001`): valor que o mock já usava. Diferente de
      Cliente e Departamento, **nenhum outro domínio referencia fornecedor hoje** — não há
      `fornecedorId` em Demanda, Projeto ou SLA. Ele é mantido por um motivo só: é a chave
      estável que torna `seed_fornecedores` idempotente entre execuções e entre ambientes,
      onde o UUID muda. Some quando a base deixar de ser reconstruída a partir do seed.

    **Não há UNIQUE de `nome` nem de `documento`**, pelo mesmo princípio já registrado em
    Cliente e em docs/padrao-entidades-externas.md: fornecedor é entidade externa, onde nome
    é rótulo comercial e não identidade. A base importada confirma que a restrição seria
    hostil ao dado real — 16 dos 133 registros não têm documento, e há documento repetido
    entre cadastros distintos.

    Coincidência de nome e/ou documento gera **aviso de possível duplicidade** na resposta da
    API (ver FornecedorService.detectar_possiveis_duplicidades), nunca bloqueio. Deduplicação
    é regra de negócio com revisão humana, não constraint de banco.

    ## Status

    `ativo | inativo | arquivado`. Deliberadamente **sem `suspenso`**: a interface de
    Fornecedor sempre ofereceu apenas ativo e inativo, e `arquivado` entra porque o
    arquivamento (soft-delete) exige. Introduzir `suspenso` só por simetria com Cliente
    criaria estado sem regra de negócio. Se a suspensão de fornecedor virar necessidade
    funcional, entra como evolução própria do domínio.

    ## Contato e categoria

    `contato_nome` é escalar, não lista: o cadastro tem um único campo "Pessoa de contato".
    Não se replica aqui o `contatos` JSONB de Cliente, que existe porque lá são vários
    interlocutores com papéis distintos.

    `categoria` é texto livre com sugestões na interface — não é entidade. Ninguém consulta
    "todos os fornecedores da categoria X" como recurso próprio, não há ciclo de vida, e nos
    133 registros importados ela vem vazia.

    ## Histórico

    Não há tabela de histórico. Toda mudança relevante vira evento de domínio
    (`fornecedor.*` em app/domain/event_types.py), publicado na mesma transação da escrita.
    """

    __tablename__ = "fornecedores"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')",
            name="ck_fornecedores_status",
        ),
        CheckConstraint("tipo_documento IN ('cnpj', 'cpf')", name="ck_fornecedores_tipo_documento"),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_fornecedores_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "codigo_referencia", name="uq_fornecedores_empresa_codigo_referencia"),
        UniqueConstraint(
            "empresa_id",
            "ano_referencia",
            "sequencial_referencia",
            name="uq_fornecedores_empresa_ano_sequencial",
        ),
        # NÃO há UNIQUE de nome nem de documento — ver "Identidade" na docstring acima.
        Index("ix_fornecedores_empresa_id", "empresa_id"),
        Index("ix_fornecedores_status", "status"),
        Index("ix_fornecedores_codigo_referencia", "codigo_referencia"),
        Index("ix_fornecedores_codigo_interno", "codigo_interno"),
        Index("ix_fornecedores_nome_normalizado", "nome_normalizado"),
        Index("ix_fornecedores_documento_normalizado", "documento_normalizado"),
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
    tipo_documento: Mapped[str] = mapped_column(String(8), nullable=False)
    documento: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Só dígitos — permite localizar "12.345.678/0001-90" digitando "12345678". Não é UNIQUE:
    # 16 dos 133 registros importados vêm sem documento.
    documento_normalizado: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- estado -------------------------------------------------------------------
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # --- dados cadastrais ---------------------------------------------------------
    categoria: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contato_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco_completo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cor_identificacao: Mapped[str] = mapped_column(String(32), nullable=False)

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
