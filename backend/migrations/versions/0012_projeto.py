"""projeto + vínculos N:N (Fase 2D)

Projeto é o trabalho contratado, sob o qual as demandas acontecem. Mesmo desenho dos
domínios anteriores: UUID técnico + `codigo_referencia` (P26000001) + `codigo_interno` como
chave de importação.

Unicidade **por cliente**, não por agência: dois "Campanha de Natal" para clientes distintos
são legítimos; dois para o mesmo cliente são erro. Ver docstring de app/models/projeto.py.

`modelo_campanha` fica em JSONB porque referencia TipoTarefa e Workflow, que ainda não têm
tabela — FK para domínio inexistente não se cria. Não há tabela de histórico: as mudanças
viram eventos `projeto.*`.

Revision ID: b1d5f30c8e72
Revises: 4e8b2f7c10a3
Create Date: 2026-08-08 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b1d5f30c8e72'
down_revision: Union[str, None] = '4e8b2f7c10a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'projetos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('campanha', sa.String(length=255), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('resumo', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('prioridade', sa.String(length=16), nullable=False),
        sa.Column('cliente_id', sa.String(length=36), nullable=True),
        sa.Column('data_inicio', sa.Date(), nullable=True),
        sa.Column('data_fim_prevista', sa.Date(), nullable=True),
        sa.Column('modelo_campanha_id', sa.String(length=64), nullable=True),
        sa.Column(
            'modelo_campanha',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "status IN ('planejamento', 'ativo', 'pausado', 'concluido', 'cancelado', 'arquivado')",
            name='ck_projetos_status',
        ),
        sa.CheckConstraint("prioridade IN ('baixa', 'media', 'alta')", name='ck_projetos_prioridade'),
        sa.CheckConstraint(
            'data_inicio IS NULL OR data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio',
            name='ck_projetos_periodo',
        ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        # SET NULL: arquivar ou remover um cliente nunca pode derrubar o histórico do projeto.
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_projetos_empresa_codigo_interno'),
        sa.UniqueConstraint('empresa_id', 'codigo_referencia', name='uq_projetos_empresa_codigo_referencia'),
        sa.UniqueConstraint(
            'empresa_id', 'ano_referencia', 'sequencial_referencia', name='uq_projetos_empresa_ano_sequencial'
        ),
        # Nome único POR CLIENTE. Diferente de Departamento e Equipe (nome único na empresa)
        # e de Cliente e Fornecedor (sem unicidade de nome) — ver docs/padrao-entidades-externas.md.
        sa.UniqueConstraint(
            'empresa_id', 'cliente_id', 'nome_normalizado', name='uq_projetos_empresa_cliente_nome'
        ),
    )
    op.create_index('ix_projetos_empresa_id', 'projetos', ['empresa_id'])
    op.create_index('ix_projetos_status', 'projetos', ['status'])
    op.create_index('ix_projetos_codigo_referencia', 'projetos', ['codigo_referencia'])
    op.create_index('ix_projetos_codigo_interno', 'projetos', ['codigo_interno'])
    op.create_index('ix_projetos_nome_normalizado', 'projetos', ['nome_normalizado'])
    op.create_index('ix_projetos_cliente_id', 'projetos', ['cliente_id'])

    # O Postgres considera NULL distinto de NULL, então a UNIQUE acima NÃO impede dois
    # projetos internos (sem cliente) com o mesmo nome. Este índice parcial fecha o buraco —
    # sem ele a regra valeria para projetos de cliente e sumiria justamente nos internos.
    op.create_index(
        'uq_projetos_empresa_nome_sem_cliente',
        'projetos',
        ['empresa_id', 'nome_normalizado'],
        unique=True,
        postgresql_where=sa.text('cliente_id IS NULL'),
    )

    # CASCADE nas três tabelas de vínculo é seguro: projeto, usuário e departamento nunca são
    # apagados fisicamente (só arquivados). Serve para não deixar órfão numa remoção real.
    op.create_table(
        'projeto_responsaveis',
        sa.Column('projeto_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['projeto_id'], ['projetos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('projeto_id', 'usuario_id'),
    )
    op.create_index('ix_projeto_responsaveis_usuario_id', 'projeto_responsaveis', ['usuario_id'])

    op.create_table(
        'projeto_departamentos',
        sa.Column('projeto_id', sa.String(length=36), nullable=False),
        sa.Column('departamento_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['projeto_id'], ['projetos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('projeto_id', 'departamento_id'),
    )
    op.create_index(
        'ix_projeto_departamentos_departamento_id', 'projeto_departamentos', ['departamento_id']
    )

    op.create_table(
        'projeto_equipe_membros',
        sa.Column('projeto_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        # Atributo do VÍNCULO, não da pessoa: a mesma pessoa pode ter funções diferentes em
        # projetos diferentes.
        sa.Column('funcao', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['projeto_id'], ['projetos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('projeto_id', 'usuario_id'),
    )
    op.create_index('ix_projeto_equipe_membros_usuario_id', 'projeto_equipe_membros', ['usuario_id'])


def downgrade() -> None:
    op.drop_index('ix_projeto_equipe_membros_usuario_id', table_name='projeto_equipe_membros')
    op.drop_table('projeto_equipe_membros')

    op.drop_index('ix_projeto_departamentos_departamento_id', table_name='projeto_departamentos')
    op.drop_table('projeto_departamentos')

    op.drop_index('ix_projeto_responsaveis_usuario_id', table_name='projeto_responsaveis')
    op.drop_table('projeto_responsaveis')

    op.drop_index('uq_projetos_empresa_nome_sem_cliente', table_name='projetos')
    op.drop_index('ix_projetos_cliente_id', table_name='projetos')
    op.drop_index('ix_projetos_nome_normalizado', table_name='projetos')
    op.drop_index('ix_projetos_codigo_interno', table_name='projetos')
    op.drop_index('ix_projetos_codigo_referencia', table_name='projetos')
    op.drop_index('ix_projetos_status', table_name='projetos')
    op.drop_index('ix_projetos_empresa_id', table_name='projetos')
    op.drop_table('projetos')
