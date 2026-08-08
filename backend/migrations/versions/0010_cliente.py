"""cliente + associação N:N com grupo_cliente (Fase 2B)

Primeira entidade comercial real. Segue o mesmo desenho de Departamento e Equipe:
UUID técnico + `codigo_referencia` (C26000001) + `codigo_interno` como ponte transitória
para os mocks de Projeto e Demanda.

`cliente_grupos` é tabela de associação dedicada — nunca array JSON. `contatos` fica em
JSONB porque são value objects (só existem dentro do cliente, ninguém os consulta de fora).
Não há tabela de histórico: as mudanças viram eventos de domínio `cliente.*`.

Revision ID: 7a4e2d0b91c5
Revises: 3c1a7be59d24
Create Date: 2026-08-08 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a4e2d0b91c5'
down_revision: Union[str, None] = '3c1a7be59d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'clientes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('razao_social', sa.String(length=255), nullable=True),
        sa.Column('tipo_documento', sa.String(length=8), nullable=False),
        sa.Column('documento', sa.String(length=32), nullable=True),
        sa.Column('documento_normalizado', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('whatsapp', sa.String(length=32), nullable=True),
        sa.Column('cep', sa.String(length=9), nullable=True),
        sa.Column('bairro', sa.String(length=255), nullable=True),
        sa.Column('endereco_completo', sa.String(length=500), nullable=True),
        sa.Column('cidade', sa.String(length=255), nullable=True),
        sa.Column('uf', sa.String(length=2), nullable=True),
        sa.Column('segmento', sa.String(length=255), nullable=True),
        sa.Column('origem', sa.String(length=255), nullable=True),
        sa.Column('responsavel_comercial_id', sa.String(length=36), nullable=True),
        sa.Column('cliente_referencial', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('avisar_conclusao_por_email', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('fee_mensal_centavos', sa.Integer(), nullable=True),
        sa.Column('horas_contratadas_mes', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('cor_identificacao', sa.String(length=32), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column(
            'contatos',
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
            "status IN ('ativo', 'suspenso', 'inativo', 'arquivado')", name='ck_clientes_status'
        ),
        sa.CheckConstraint("tipo_documento IN ('cnpj', 'cpf')", name='ck_clientes_tipo_documento'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        # SET NULL: inativar/remover o responsável comercial nunca pode derrubar o cliente.
        sa.ForeignKeyConstraint(['responsavel_comercial_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_clientes_empresa_codigo_interno'),
        sa.UniqueConstraint('empresa_id', 'codigo_referencia', name='uq_clientes_empresa_codigo_referencia'),
        sa.UniqueConstraint(
            'empresa_id', 'ano_referencia', 'sequencial_referencia', name='uq_clientes_empresa_ano_sequencial'
        ),
        # NÃO há UNIQUE de nome nem de documento — decisão deliberada, ver docstring do
        # model (app/models/cliente.py). A base real tem filiais de mesmo nome com CNPJ
        # diferente e empreendimentos de nomes diferentes sob o mesmo CNPJ; ambos são
        # cadastros legítimos. Possível duplicidade vira AVISO na API, nunca bloqueio.
    )
    op.create_index('ix_clientes_empresa_id', 'clientes', ['empresa_id'])
    op.create_index('ix_clientes_status', 'clientes', ['status'])
    op.create_index('ix_clientes_codigo_referencia', 'clientes', ['codigo_referencia'])
    op.create_index('ix_clientes_codigo_interno', 'clientes', ['codigo_interno'])
    op.create_index('ix_clientes_nome_normalizado', 'clientes', ['nome_normalizado'])
    op.create_index('ix_clientes_documento_normalizado', 'clientes', ['documento_normalizado'])
    op.create_index('ix_clientes_responsavel_comercial_id', 'clientes', ['responsavel_comercial_id'])

    op.create_table(
        'cliente_grupos',
        sa.Column('cliente_id', sa.String(length=36), nullable=False),
        sa.Column('grupo_cliente_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        # CASCADE é seguro: nem Cliente nem GrupoCliente são apagados fisicamente (só
        # arquivados). Serve para não deixar órfão numa remoção real de manutenção.
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grupo_cliente_id'], ['grupos_cliente.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cliente_id', 'grupo_cliente_id'),
    )
    # A PK composta cobre cliente→grupos; este índice cobre o sentido inverso.
    op.create_index('ix_cliente_grupos_grupo_cliente_id', 'cliente_grupos', ['grupo_cliente_id'])


def downgrade() -> None:
    op.drop_index('ix_cliente_grupos_grupo_cliente_id', table_name='cliente_grupos')
    op.drop_table('cliente_grupos')

    op.drop_index('ix_clientes_responsavel_comercial_id', table_name='clientes')
    op.drop_index('ix_clientes_documento_normalizado', table_name='clientes')
    op.drop_index('ix_clientes_nome_normalizado', table_name='clientes')
    op.drop_index('ix_clientes_codigo_interno', table_name='clientes')
    op.drop_index('ix_clientes_codigo_referencia', table_name='clientes')
    op.drop_index('ix_clientes_status', table_name='clientes')
    op.drop_index('ix_clientes_empresa_id', table_name='clientes')
    op.drop_table('clientes')
