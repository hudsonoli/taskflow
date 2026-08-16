"""demanda_workflow

Ver app/models/workflow_modelo_etapa_departamento_responsavel.py,
demanda_workflow_etapa.py, demanda_workflow_etapa_responsavel.py,
demanda_workflow_etapa_departamento_responsavel.py, e a coluna nova em
app/models/demanda.py (workflow_modelo_id). Não toca em nenhuma tabela existente.

Revision ID: 89ff6c49ff70
Revises: 370addf85190
Create Date: 2026-08-16 00:10:12.312320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89ff6c49ff70'
down_revision: Union[str, None] = '370addf85190'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Departamentos responsáveis por etapa de WorkflowModelo (template) — mesma forma de
    # workflow_modelo_etapa_responsaveis (usuário), lado departamento.
    op.create_table(
        'workflow_modelo_etapa_departamentos_responsaveis',
        sa.Column('workflow_modelo_etapa_id', sa.String(length=36), nullable=False),
        sa.Column('departamento_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workflow_modelo_etapa_id'], ['workflow_modelo_etapas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workflow_modelo_etapa_id', 'departamento_id'),
    )
    op.create_index(
        'ix_workflow_modelo_etapa_dep_resp_departamento_id',
        'workflow_modelo_etapa_departamentos_responsaveis',
        ['departamento_id'],
    )

    # Qual WorkflowModelo originou a Demanda — só informativo, ver docstring do model.
    op.add_column('demandas', sa.Column('workflow_modelo_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'demandas_workflow_modelo_id_fkey', 'demandas', 'workflow_modelos',
        ['workflow_modelo_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_demandas_workflow_modelo_id', 'demandas', ['workflow_modelo_id'])

    # Etapas de workflow materializadas na Demanda — snapshot, sem FK de origem para
    # workflow_modelo_etapas (ver docstring do model).
    op.create_table(
        'demanda_workflow_etapas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=32), nullable=False),
        sa.Column('quantidade_antes_deadline', sa.Integer(), nullable=False),
        sa.Column('unidade_prazo', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('execucao', 'aprovacao')", name='ck_demanda_workflow_etapas_tipo'),
        sa.CheckConstraint(
            "unidade_prazo IN ('dias_corridos', 'dias_uteis', 'horas')",
            name='ck_demanda_workflow_etapas_unidade_prazo',
        ),
        sa.CheckConstraint(
            "status IN ('pendente', 'em_execucao', 'pausada', 'concluida')",
            name='ck_demanda_workflow_etapas_status',
        ),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_demanda_workflow_etapas_demanda_ordem', 'demanda_workflow_etapas', ['demanda_id', 'ordem']
    )

    op.create_table(
        'demanda_workflow_etapa_responsaveis',
        sa.Column('demanda_workflow_etapa_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_workflow_etapa_id'], ['demanda_workflow_etapas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('demanda_workflow_etapa_id', 'usuario_id'),
    )
    op.create_index(
        'ix_demanda_workflow_etapa_responsaveis_usuario_id', 'demanda_workflow_etapa_responsaveis', ['usuario_id']
    )

    op.create_table(
        'demanda_workflow_etapa_departamentos_responsaveis',
        sa.Column('demanda_workflow_etapa_id', sa.String(length=36), nullable=False),
        sa.Column('departamento_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_workflow_etapa_id'], ['demanda_workflow_etapas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('demanda_workflow_etapa_id', 'departamento_id'),
    )
    op.create_index(
        'ix_demanda_workflow_etapa_dep_resp_departamento_id',
        'demanda_workflow_etapa_departamentos_responsaveis',
        ['departamento_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_demanda_workflow_etapa_dep_resp_departamento_id',
        table_name='demanda_workflow_etapa_departamentos_responsaveis',
    )
    op.drop_table('demanda_workflow_etapa_departamentos_responsaveis')

    op.drop_index('ix_demanda_workflow_etapa_responsaveis_usuario_id', table_name='demanda_workflow_etapa_responsaveis')
    op.drop_table('demanda_workflow_etapa_responsaveis')

    op.drop_index('ix_demanda_workflow_etapas_demanda_ordem', table_name='demanda_workflow_etapas')
    op.drop_table('demanda_workflow_etapas')

    op.drop_index('ix_demandas_workflow_modelo_id', table_name='demandas')
    op.drop_constraint('demandas_workflow_modelo_id_fkey', 'demandas', type_='foreignkey')
    op.drop_column('demandas', 'workflow_modelo_id')

    op.drop_index(
        'ix_workflow_modelo_etapa_dep_resp_departamento_id',
        table_name='workflow_modelo_etapa_departamentos_responsaveis',
    )
    op.drop_table('workflow_modelo_etapa_departamentos_responsaveis')
