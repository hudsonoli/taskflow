from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Estados que ABREM um intervalo (a linha do tempo OPERACIONAL da Demanda). Os terminais (`concluida`, `cancelada`, `arquivada`) NÃO têm intervalo próprio: entrar neles
# apenas FECHA o intervalo anterior — uma Demanda concluída não acumula "tempo concluída" por meses.
STATUS_COM_INTERVALO = ("rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente")
STATUS_TERMINAIS = ("concluida", "cancelada", "arquivada")
ORIGENS_INTERVALO = ("criacao", "transicao", "troca_etapa", "restauracao", "expediente", "migracao")
MOTIVOS_FIM_INTERVALO = ("mudanca_status", "mudanca_etapa", "conclusao", "cancelamento", "arquivamento", "fim_expediente")


def _lista_sql(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{valor}'" for valor in valores)


class DemandaStatusIntervalo(Base):
    """Linha do tempo OPERACIONAL da Demanda (Tráfego V2 — Fase 1): um intervalo por ESTADO (e por etapa do workflow) em que ela esteve.

    ## TEMPO OPERACIONAL ≠ TEMPO PESSOAL
    `fim_em - inicio_em` é o tempo DECORRIDO da Demanda/etapa naquele estado (ex.: `em_execucao` das 09:12 às 10:47 = 1h35 operacionais). NÃO é "horas trabalhadas por
    ninguém": o tempo de uma PESSOA continua sendo só `sessoes_trabalho` (evidência explícita), e este modelo nunca o gera nem o infere — não existe `executor`/`horas por
    usuário` aqui. `iniciado_por_usuario_id` é AUDITORIA ("quem provocou a abertura deste intervalo"): um gestor que move a tarefa para `em_execucao` aparece ali, e
    nenhuma hora é atribuída a ele.

    ## Invariantes (no banco)
    - no máximo UM intervalo ABERTO por Demanda (índice único parcial);
    - aberto ⇒ sem fim, sem duração, sem motivo; fechado ⇒ fim ≥ início, duração ≥ 0 e motivo;
    - `workflow_etapa_id` = a ETAPA ATUAL no instante (NULL sem workflow ou com o workflow já concluído); troca de etapa com o status igual fecha e reabre.

    ## Fonte da verdade
    Os eventos continuam sendo AUDITORIA (`evento_inicio_id`/`evento_fim_id` ligam o intervalo ao evento que o causou); as métricas de duração consultam ESTA tabela, nunca
    JSON de eventos. Escrita só por `DemandaIntervaloService`, na mesma transação da mudança de status/etapa.

    "Dados disponíveis desde" = o menor `inicio_em` da empresa (intervalos `origem='migracao'` marcam o início da medição das Demandas que já existiam).
    """

    __tablename__ = "demanda_status_intervalos"
    __table_args__ = (
        CheckConstraint(f"status IN ({_lista_sql(STATUS_COM_INTERVALO)})", name="ck_demanda_status_intervalos_status"),
        CheckConstraint(f"origem IN ({_lista_sql(ORIGENS_INTERVALO)})", name="ck_demanda_status_intervalos_origem"),
        CheckConstraint(f"motivo_fim IS NULL OR motivo_fim IN ({_lista_sql(MOTIVOS_FIM_INTERVALO)})", name="ck_demanda_status_intervalos_motivo_fim"),
        CheckConstraint(
            "(fim_em IS NULL AND duracao_segundos IS NULL AND motivo_fim IS NULL) OR "
            "(fim_em IS NOT NULL AND duracao_segundos IS NOT NULL AND duracao_segundos >= 0 AND fim_em >= inicio_em AND motivo_fim IS NOT NULL)",
            name="ck_demanda_status_intervalos_aberto_ou_fechado",
        ),
        Index(
            "uq_demanda_status_intervalos_aberto_por_demanda",
            "demanda_id",
            unique=True,
            postgresql_where=text("fim_em IS NULL"),
            sqlite_where=text("fim_em IS NULL"),
        ),
        Index(
            "uq_demanda_status_intervalos_evento_inicio",
            "evento_inicio_id",
            unique=True,
            postgresql_where=text("evento_inicio_id IS NOT NULL"),
            sqlite_where=text("evento_inicio_id IS NOT NULL"),
        ),
        Index("ix_demanda_status_intervalos_empresa_demanda_inicio", "empresa_id", "demanda_id", "inicio_em"),
        Index("ix_demanda_status_intervalos_empresa_status_inicio", "empresa_id", "status", "inicio_em"),
        Index("ix_demanda_status_intervalos_workflow_etapa_id", "workflow_etapa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    demanda_id: Mapped[str] = mapped_column(ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_etapa_id: Mapped[str | None] = mapped_column(ForeignKey("demanda_workflow_etapas.id", ondelete="SET NULL"), nullable=True)
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracao_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo_fim: Mapped[str | None] = mapped_column(String(32), nullable=True)
    iniciado_por_usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    origem: Mapped[str] = mapped_column(String(32), nullable=False)
    evento_inicio_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evento_fim_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
