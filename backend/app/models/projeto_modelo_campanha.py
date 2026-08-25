from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjetoModeloCampanha(Base):
    """Snapshot relacional do Modelo de Campanha aplicado a um Projeto (Fase 2G.5C1) —
    cabeçalho. Só schema/model nesta subfase: nenhuma rota, service operacional ou frontend
    ainda — ver Fase 2G.5C2 em diante.

    `ModeloCampanha` (biblioteca) é uma entidade VIVA; este cabeçalho + `ProjetoModeloCampanhaItem`
    são o SNAPSHOT — a cópia aplicada a um Projeto num momento específico. Editar o Modelo de
    biblioteca depois (nome, itens, referências) nunca muda um Projeto que já aplicou — mesma
    filosofia de `DemandaWorkflowEtapa` em relação a `WorkflowModelo`.

    `UNIQUE(projeto_id)` garante estruturalmente **0 ou 1** cabeçalho por Projeto — sem
    histórico estrutural de múltiplas aplicações nesta primeira versão (ver relatório de
    análise da Fase 2G.5C). O cabeçalho tem UUID próprio e estável: a futura ação de
    "reaplicar outro Modelo" (Fase 2G.5C2) deve ATUALIZAR este registro existente (nome
    snapshot, origem, timestamps) e substituir os itens, nunca apagar/recriar o cabeçalho —
    o schema aqui não impede nem exige isso, só não atrapalha.

    `modelo_campanha_origem_id`/`modelo_campanha_nome_snapshot`/`aplicado_at`/
    `aplicado_por_usuario_id` são todos nullable. Para uma aplicação NOVA (Fase 2G.5C2), o
    service deve preencher os quatro — mas o banco permite NULL porque a futura migração do
    JSONB legado (`projetos.modelo_campanha`, Fase 2G.5C4) vai materializar snapshots
    históricos que não têm de qual Modelo de biblioteca vieram, nem quando, nem quem aplicou
    (esses dados nunca existiram no JSONB). Nunca inventar valor nesses casos — nem um
    Modelo de origem falso, nem uma data aproximada, nem um usuário "sistema", nem strings
    como "Legado"/"Migrado"/"Desconhecido" no lugar de um nome ausente: os quatro campos
    ficam genuinamente NULL, e a ausência É a informação.

    `modelo_campanha_origem_id` usa `ondelete="SET NULL"` (não CASCADE, não RESTRICT) —
    mesmo padrão de `Demanda.workflow_modelo_id`: é uma referência de PROVENIÊNCIA
    (informativa — "de qual Modelo este Projeto nasceu"), não um dado do snapshot em si.
    Arquivar o Modelo de origem nunca derruba nem altera o snapshot (o nome já foi copiado
    para `modelo_campanha_nome_snapshot` no momento da aplicação); a coluna só viraria NULL
    se o Modelo fosse fisicamente apagado — o que o domínio não faz (soft-delete apenas), mas
    a constraint fica defensiva mesmo assim.
    """

    __tablename__ = "projeto_modelo_campanha"
    __table_args__ = (
        UniqueConstraint("projeto_id", name="uq_projeto_modelo_campanha_projeto_id"),
        Index("ix_projeto_modelo_campanha_origem_id", "modelo_campanha_origem_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id", ondelete="CASCADE"), nullable=False)

    modelo_campanha_origem_id: Mapped[str | None] = mapped_column(
        ForeignKey("modelos_campanha.id", ondelete="SET NULL"), nullable=True
    )
    modelo_campanha_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    aplicado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Auditoria solta, sem FK — mesmo padrão de arquivado_por_usuario_id/restaurado_por_usuario_id
    # em todo o projeto (ver docs/padrao-arquivamento.md).
    aplicado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjetoModeloCampanhaItem(Base):
    """Item materializado do snapshot — sempre substituído por completo a cada reaplicação
    ou edição do agregado (mesmo padrão de `ModeloCampanhaRepository.replace_itens`), nunca
    via endpoint próprio.

    Identidade própria, SEM FK para `modelos_campanha_itens.id` (de propósito — ver
    `ProjetoModeloCampanha` e o precedente de `DemandaWorkflowEtapa`/`WorkflowModeloEtapa`):
    o Modelo de biblioteca faz full-replace dos seus itens a cada edição, então o id de um
    item de template não é estável — uma FK de origem por item viraria NULL na primeira
    edição trivial do Modelo, mesmo sem nenhuma relação com este Projeto. A proveniência fica
    só no cabeçalho (`ProjetoModeloCampanha.modelo_campanha_origem_id`), nunca por item.

    Os 5 campos `*_nome_snapshot` NÃO são cache: são dado histórico, escrito uma única vez no
    momento em que o vínculo correspondente é criado ou TROCADO, nunca recalculado por JOIN.
    Referência não alterada entre edições preserva FK e nome snapshot originais, mesmo que a
    entidade tenha sido arquivada/inativada depois (mesma regra de preservação histórica da
    `ModeloCampanhaItem`/Fase 2G.5A — a validação de "só ativo aceita vínculo NOVO" pertence
    ao service futuro, não ao banco). Referência trocada grava o nome atual da nova entidade
    como o novo snapshot.

    Nenhuma FK de referência (Peça/TipoTarefa/Workflow/Usuário/Departamento) usa CASCADE —
    mesmo padrão de `ModeloCampanhaItem`: arquivar/inativar a entidade referenciada nunca
    derruba um item que já a referencia.

    `responsavel_usuario_id`/`responsavel_departamento_id`: mesma divergência deliberada do
    padrão many-to-many de `WorkflowModeloEtapa`/Projeto/Demanda — aqui é o responsável
    sugerido herdado do item do Modelo (ou editado depois no Projeto), nunca os dois ao mesmo
    tempo.
    """

    __tablename__ = "projeto_modelo_campanha_itens"
    __table_args__ = (
        CheckConstraint(
            "prioridade_padrao IN ('baixa', 'media', 'alta')", name="ck_projeto_modelo_campanha_itens_prioridade"
        ),
        CheckConstraint("ordem >= 1", name="ck_projeto_modelo_campanha_itens_ordem"),
        CheckConstraint(
            "NOT (responsavel_usuario_id IS NOT NULL AND responsavel_departamento_id IS NOT NULL)",
            name="ck_projeto_modelo_campanha_itens_responsavel_unico",
        ),
        UniqueConstraint("projeto_modelo_campanha_id", "ordem", name="uq_projeto_modelo_campanha_itens_ordem"),
        Index("ix_projeto_modelo_campanha_itens_cabecalho_id", "projeto_modelo_campanha_id"),
        Index("ix_projeto_modelo_campanha_itens_peca_id", "peca_id"),
        Index("ix_projeto_modelo_campanha_itens_tipo_tarefa_id", "tipo_tarefa_id"),
        Index("ix_projeto_modelo_campanha_itens_workflow_modelo_id", "workflow_modelo_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    projeto_modelo_campanha_id: Mapped[str] = mapped_column(
        ForeignKey("projeto_modelo_campanha.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    briefing_padrao: Mapped[str | None] = mapped_column(Text, nullable=True)
    prioridade_padrao: Mapped[str] = mapped_column(String(16), nullable=False, default="media")

    peca_id: Mapped[str | None] = mapped_column(ForeignKey("pecas.id"), nullable=True)
    peca_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tipo_tarefa_id: Mapped[str | None] = mapped_column(ForeignKey("tipos_tarefa.id"), nullable=True)
    tipo_tarefa_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    workflow_modelo_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_modelos.id"), nullable=True)
    workflow_modelo_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    responsavel_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    responsavel_usuario_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    responsavel_departamento_id: Mapped[str | None] = mapped_column(ForeignKey("departamentos.id"), nullable=True)
    responsavel_departamento_nome_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
