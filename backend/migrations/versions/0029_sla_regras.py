"""sla_regras

Fase 2G.6B — cadastro real de Regra de SLA (ver app/models/sla_regra.py). Cria só a tabela do
domínio SLA — não toca em `demandas`, `workflow_modelos`, `workflow_modelo_etapas`,
`demanda_workflow_etapas` nem `regra_expediente`. Nenhum cálculo de prazo/resolução
automática ainda (isso é Fase 2G.6C); nenhum campo de snapshot em Demanda (Fase 2G.6D).

Revision ID: a17fbbef4ad8
Revises: ffbeb0e786e8
Create Date: 2026-08-29 13:44:27.676033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a17fbbef4ad8'
down_revision: Union[str, None] = 'ffbeb0e786e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sla_regras',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('prioridade_alvo', sa.String(length=16), nullable=True),
        sa.Column('departamento_id', sa.String(length=36), nullable=True),
        sa.Column('cliente_id', sa.String(length=36), nullable=True),
        sa.Column('prioridade_regra', sa.Integer(), nullable=False),
        sa.Column('prazo_primeira_resposta_quantidade', sa.Integer(), nullable=False),
        sa.Column('prazo_primeira_resposta_unidade', sa.String(length=16), nullable=False),
        sa.Column('prazo_resolucao_quantidade', sa.Integer(), nullable=False),
        sa.Column('prazo_resolucao_unidade', sa.String(length=16), nullable=False),
        sa.Column('considerar_apenas_expediente', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "prioridade_alvo IS NULL OR prioridade_alvo IN ('baixa', 'media', 'alta')",
            name='ck_sla_regras_prioridade_alvo',
        ),
        sa.CheckConstraint('prioridade_regra >= 1', name='ck_sla_regras_prioridade_regra'),
        sa.CheckConstraint(
            'prazo_primeira_resposta_quantidade > 0', name='ck_sla_regras_prazo_primeira_resposta_quantidade'
        ),
        sa.CheckConstraint(
            "prazo_primeira_resposta_unidade IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
            name='ck_sla_regras_prazo_primeira_resposta_unidade',
        ),
        sa.CheckConstraint('prazo_resolucao_quantidade > 0', name='ck_sla_regras_prazo_resolucao_quantidade'),
        sa.CheckConstraint(
            "prazo_resolucao_unidade IN ('minutos', 'horas', 'dias_corridos', 'dias_uteis')",
            name='ck_sla_regras_prazo_resolucao_unidade',
        ),
        sa.CheckConstraint("status IN ('ativo', 'inativo', 'arquivado')", name='ck_sla_regras_status'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        # Sem ondelete: Cliente/Departamento nunca são apagados fisicamente (soft-delete via
        # status) — ver docstring de app/models/sla_regra.py pra por que SET NULL seria errado
        # aqui (mutaria uma regra específica em genérica silenciosamente).
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id']),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.PrimaryKeyConstraint('id'),
        # Deliberadamente SEM UNIQUE(empresa_id, prioridade_regra) — duas regras podem
        # compartilhar precedência; o desempate é da Fase 2G.6C.
        sa.UniqueConstraint('empresa_id', 'nome_normalizado', name='uq_sla_regras_empresa_nome_normalizado'),
    )
    op.create_index('ix_sla_regras_empresa_id', 'sla_regras', ['empresa_id'])
    op.create_index('ix_sla_regras_status', 'sla_regras', ['status'])
    op.create_index('ix_sla_regras_nome_normalizado', 'sla_regras', ['nome_normalizado'])
    op.create_index('ix_sla_regras_empresa_status', 'sla_regras', ['empresa_id', 'status'])
    op.create_index('ix_sla_regras_departamento_id', 'sla_regras', ['departamento_id'])
    op.create_index('ix_sla_regras_cliente_id', 'sla_regras', ['cliente_id'])


def downgrade() -> None:
    op.drop_index('ix_sla_regras_cliente_id', table_name='sla_regras')
    op.drop_index('ix_sla_regras_departamento_id', table_name='sla_regras')
    op.drop_index('ix_sla_regras_empresa_status', table_name='sla_regras')
    op.drop_index('ix_sla_regras_nome_normalizado', table_name='sla_regras')
    op.drop_index('ix_sla_regras_status', table_name='sla_regras')
    op.drop_index('ix_sla_regras_empresa_id', table_name='sla_regras')
    op.drop_table('sla_regras')
