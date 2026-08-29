from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModeloCampanha(Base):
    """Biblioteca reutilizável de Modelo de Campanha (Fase 2G.5A) — cabeçalho.

    Isto é só a BIBLIOTECA: nenhum vínculo com Projeto ainda nesta fase — a materialização de
    um Modelo num Projeto (snapshot, sem FK de origem — mesmo padrão de `DemandaWorkflowEtapa`)
    é a Fase 2G.5C. O JSONB legado que existia em `Projeto.modelo_campanha`/`modelo_campanha_id`
    foi removido fisicamente na Fase 2G.5D — nunca teve relação com esta biblioteca.

    Sem `workflow_modelo_id` aqui de propósito: o comportamento real observado (Fase 2G.5,
    item 3/5 do relatório de análise) mostra Workflow sempre selecionado POR ITEM, nunca por
    modelo inteiro — ver `ModeloCampanhaItem.workflow_modelo_id`.
    """

    __tablename__ = "modelos_campanha"
    __table_args__ = (
        CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name="ck_modelos_campanha_status"),
        UniqueConstraint("empresa_id", "nome_normalizado", name="uq_modelos_campanha_empresa_nome_normalizado"),
        Index("ix_modelos_campanha_empresa_id", "empresa_id"),
        Index("ix_modelos_campanha_status", "status"),
        Index("ix_modelos_campanha_nome_normalizado", "nome_normalizado"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Mesmo padrão de
    # TipoTarefa/WorkflowModelo/Peca: 3 estados, "inativo" reversível via PATCH, "arquivado"
    # só via arquivar/restaurar.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ModeloCampanhaItem(Base):
    """Item (linha de backlog padrão) de um Modelo de Campanha — sempre substituído por
    completo a cada edição do agregado (mesmo padrão de `WorkflowModeloRepository.replace_etapas`),
    nunca via endpoint próprio.

    Sem soft-delete/status individual: o item não tem identidade fora do Modelo (não é
    referenciado de fora) — pertence ao agregado, histórico fica no evento
    `modelo_campanha.alterado` (ver `ModeloCampanhaService`).

    Nenhuma FK aqui usa CASCADE (exceto pra `modelos_campanha`, o pai) — Peça/TipoTarefa/
    Workflow/Usuário/Departamento arquivados NUNCA derrubam um item que já os referencia
    (mesma filosofia de `Peca.categoria_id`); a validação de "só ativo aceita vínculo NOVO"
    é do service, não do banco (ver `ModeloCampanhaService._ensure_referencias_validas`).

    `responsavel_usuario_id`/`responsavel_departamento_id`: divergência deliberada do padrão
    many-to-many usado em WorkflowModeloEtapa/Projeto/Demanda (onde múltiplos responsáveis
    convivem) — aqui é uma SUGESTÃO singular no momento de definição do template, não uma
    atribuição operacional real, daí duas FKs nullable com CHECK mutuamente exclusivo em vez
    de tabela de associação.
    """

    __tablename__ = "modelos_campanha_itens"
    __table_args__ = (
        CheckConstraint(
            "prioridade_padrao IN ('baixa', 'media', 'alta')", name="ck_modelos_campanha_itens_prioridade"
        ),
        CheckConstraint("ordem >= 1", name="ck_modelos_campanha_itens_ordem"),
        CheckConstraint(
            "NOT (responsavel_usuario_id IS NOT NULL AND responsavel_departamento_id IS NOT NULL)",
            name="ck_modelos_campanha_itens_responsavel_unico",
        ),
        UniqueConstraint("modelo_campanha_id", "ordem", name="uq_modelos_campanha_itens_modelo_ordem"),
        Index("ix_modelos_campanha_itens_modelo_id", "modelo_campanha_id"),
        Index("ix_modelos_campanha_itens_peca_id", "peca_id"),
        Index("ix_modelos_campanha_itens_tipo_tarefa_id", "tipo_tarefa_id"),
        Index("ix_modelos_campanha_itens_workflow_modelo_id", "workflow_modelo_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    modelo_campanha_id: Mapped[str] = mapped_column(
        ForeignKey("modelos_campanha.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    briefing_padrao: Mapped[str | None] = mapped_column(Text, nullable=True)
    prioridade_padrao: Mapped[str] = mapped_column(String(16), nullable=False, default="media")

    peca_id: Mapped[str | None] = mapped_column(ForeignKey("pecas.id"), nullable=True)
    tipo_tarefa_id: Mapped[str | None] = mapped_column(ForeignKey("tipos_tarefa.id"), nullable=True)
    workflow_modelo_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_modelos.id"), nullable=True)
    responsavel_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    responsavel_departamento_id: Mapped[str | None] = mapped_column(ForeignKey("departamentos.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
