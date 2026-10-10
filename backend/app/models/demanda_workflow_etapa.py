from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandaWorkflowEtapa(Base):
    """Etapa de workflow materializada numa Demanda — snapshot, não referência viva.

    `WorkflowModelo`/`WorkflowModeloEtapa` são o template; esta tabela é a cópia aplicada a
    uma Demanda no momento da criação. Deliberadamente **sem FK de origem** para
    `workflow_modelo_etapas.id`: `WorkflowModeloService` faz full-replace das etapas do
    template a cada edição (apaga e recria todas), então os ids do template não são
    estáveis — uma FK de origem viraria NULL na primeira edição do template, mesmo trivial.
    A proveniência desta fase é só `demandas.workflow_modelo_id` (qual modelo originou a
    Demanda); rastrear de qual ETAPA/versão específica veio cada registro fica para quando
    houver versionamento explícito de Workflow.

    `etapa_atual` não é coluna aqui nem em Demanda — é derivada em runtime (menor `ordem`
    com `status != 'concluida'`), evitando o ciclo de FK que uma coluna
    `demandas.etapa_atual_id` criaria. Desde a Fase 8A, `UNIQUE (demanda_id, ordem)` garante que
    essa derivação (e a "próxima etapa") seja inequívoca; a transição acontece em
    `DemandaWorkflowService`, com a Demanda travada (`SELECT … FOR UPDATE`).
    """

    __tablename__ = "demanda_workflow_etapas"
    __table_args__ = (
        CheckConstraint("tipo IN ('execucao', 'aprovacao')", name="ck_demanda_workflow_etapas_tipo"),
        CheckConstraint(
            "unidade_prazo IN ('dias_corridos', 'dias_uteis', 'horas')",
            name="ck_demanda_workflow_etapas_unidade_prazo",
        ),
        CheckConstraint(
            "status IN ('pendente', 'em_execucao', 'pausada', 'concluida')",
            name="ck_demanda_workflow_etapas_status",
        ),
        # Fase 8A: ordem única por demanda — torna inequívoca a derivação da etapa atual e da "próxima".
        UniqueConstraint("demanda_id", "ordem", name="uq_demanda_workflow_etapas_demanda_ordem"),
        CheckConstraint(
            "status <> 'concluida' OR concluida_em IS NOT NULL",
            name="ck_demanda_workflow_etapas_concluida_em",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    quantidade_antes_deadline: Mapped[int] = mapped_column(Integer, nullable=False)
    unidade_prazo: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Fase 8A — progressão. `iniciada_em` NULL = início histórico desconhecido (snapshots anteriores à 8A); nunca preenchido
    # com um valor fictício. `concluida_por_usuario_id` é o conceito único de "quem concluiu/aprovou" (o tipo da etapa
    # decide o rótulo): SET NULL se o usuário for removido, e NULL também no backfill histórico.
    iniciada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluida_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
