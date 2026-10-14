"""Tráfego V2 — Fase 1: `demanda_status_intervalos` (linha do tempo OPERACIONAL das Demandas).

ADITIVA: cria a tabela, os índices e os CHECKs, e abre UM intervalo para cada Demanda NÃO terminal já existente. NÃO altera `sessoes_trabalho`, `demandas`, `eventos` nem o
workflow; nenhum dado existente é reescrito.

TEMPO OPERACIONAL ≠ TEMPO PESSOAL: a duração de um intervalo é o tempo DECORRIDO da Demanda naquele estado — nunca "horas trabalhadas" por alguém.

Demandas já existentes: não se sabe quando o estado atual começou historicamente, então (sem inventar) o intervalo inicial nasce com `inicio_em = now()` da migration e
`origem = 'migracao'` — esse é o marcador do INÍCIO da medição ("dados disponíveis a partir de..." = menor `inicio_em` da empresa). Demandas terminais
(`concluida`, `cancelada`, `arquivada`) não ganham intervalo. A etapa do intervalo inicial é a etapa ATUAL (menor `ordem` não concluída) ou NULL.

Downgrade: remove SÓ a tabela nova (Demandas, sessões, eventos e workflow não são tocados).
"""
import sqlalchemy as sa
from alembic import op

revision = "d7f3b91e4a58"
down_revision = "c6e1a38d5b92"
branch_labels = None
depends_on = None

STATUS_COM_INTERVALO = ("rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente")
ORIGENS = ("criacao", "transicao", "troca_etapa", "restauracao", "expediente", "migracao")
MOTIVOS_FIM = ("mudanca_status", "mudanca_etapa", "conclusao", "cancelamento", "arquivamento", "fim_expediente")


def _lista(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    op.create_table(
        "demanda_status_intervalos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("empresa_id", sa.String(36), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("demanda_id", sa.String(36), sa.ForeignKey("demandas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("workflow_etapa_id", sa.String(36), sa.ForeignKey("demanda_workflow_etapas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracao_segundos", sa.Integer(), nullable=True),
        sa.Column("motivo_fim", sa.String(32), nullable=True),
        sa.Column("iniciado_por_usuario_id", sa.String(36), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("origem", sa.String(32), nullable=False),
        sa.Column("evento_inicio_id", sa.String(36), nullable=True),
        sa.Column("evento_fim_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"status IN ({_lista(STATUS_COM_INTERVALO)})", name="ck_demanda_status_intervalos_status"),
        sa.CheckConstraint(f"origem IN ({_lista(ORIGENS)})", name="ck_demanda_status_intervalos_origem"),
        sa.CheckConstraint(f"motivo_fim IS NULL OR motivo_fim IN ({_lista(MOTIVOS_FIM)})", name="ck_demanda_status_intervalos_motivo_fim"),
        sa.CheckConstraint(
            "(fim_em IS NULL AND duracao_segundos IS NULL AND motivo_fim IS NULL) OR "
            "(fim_em IS NOT NULL AND duracao_segundos IS NOT NULL AND duracao_segundos >= 0 AND fim_em >= inicio_em AND motivo_fim IS NOT NULL)",
            name="ck_demanda_status_intervalos_aberto_ou_fechado",
        ),
    )
    op.create_index(
        "uq_demanda_status_intervalos_aberto_por_demanda", "demanda_status_intervalos", ["demanda_id"], unique=True, postgresql_where=sa.text("fim_em IS NULL")
    )
    op.create_index(
        "uq_demanda_status_intervalos_evento_inicio", "demanda_status_intervalos", ["evento_inicio_id"], unique=True, postgresql_where=sa.text("evento_inicio_id IS NOT NULL")
    )
    op.create_index("ix_demanda_status_intervalos_empresa_demanda_inicio", "demanda_status_intervalos", ["empresa_id", "demanda_id", "inicio_em"])
    op.create_index("ix_demanda_status_intervalos_empresa_status_inicio", "demanda_status_intervalos", ["empresa_id", "status", "inicio_em"])
    op.create_index("ix_demanda_status_intervalos_workflow_etapa_id", "demanda_status_intervalos", ["workflow_etapa_id"])

    # Início da medição: UM intervalo aberto por Demanda NÃO terminal, a partir do instante da migration (nada é "reconstruído").
    op.execute(
        f"""
        INSERT INTO demanda_status_intervalos
            (id, empresa_id, demanda_id, status, workflow_etapa_id, inicio_em, origem, created_at, updated_at)
        SELECT
            md5(random()::text || clock_timestamp()::text || d.id)::uuid::text,
            d.empresa_id,
            d.id,
            d.status,
            (SELECT e.id FROM demanda_workflow_etapas e WHERE e.demanda_id = d.id AND e.status <> 'concluida' ORDER BY e.ordem ASC LIMIT 1),
            now(),
            'migracao',
            now(),
            now()
        FROM demandas d
        WHERE d.status IN ({_lista(STATUS_COM_INTERVALO)})
        """
    )


def downgrade() -> None:
    op.drop_table("demanda_status_intervalos")
