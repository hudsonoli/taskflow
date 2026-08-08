"""fornecedor (Fase 2C)

Último cadastro comercial a sair do mock. Mesmo desenho de Cliente: UUID técnico +
`codigo_referencia` (F26000001) + `codigo_interno` — que aqui existe por um motivo só, ser a
chave de idempotência do seed, já que nenhum outro domínio referencia fornecedor.

Sem UNIQUE de nome nem de documento (ver docstring do model). Sem tabela de histórico: as
mudanças viram eventos de domínio `fornecedor.*`.

Revision ID: 4e8b2f7c10a3
Revises: 7a4e2d0b91c5
Create Date: 2026-08-08 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e8b2f7c10a3'
down_revision: Union[str, None] = '7a4e2d0b91c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fornecedores',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_interno', sa.String(length=64), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('nome_normalizado', sa.String(length=255), nullable=False),
        sa.Column('tipo_documento', sa.String(length=8), nullable=False),
        sa.Column('documento', sa.String(length=32), nullable=True),
        sa.Column('documento_normalizado', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('categoria', sa.String(length=255), nullable=True),
        sa.Column('contato_nome', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('whatsapp', sa.String(length=32), nullable=True),
        sa.Column('site', sa.String(length=255), nullable=True),
        sa.Column('cep', sa.String(length=9), nullable=True),
        sa.Column('bairro', sa.String(length=255), nullable=True),
        sa.Column('endereco_completo', sa.String(length=500), nullable=True),
        sa.Column('cidade', sa.String(length=255), nullable=True),
        sa.Column('uf', sa.String(length=2), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('cor_identificacao', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        # Sem 'suspenso': a interface de Fornecedor sempre ofereceu ativo e inativo, e
        # 'arquivado' entra porque o soft-delete exige. Estado novo só com regra de negócio.
        sa.CheckConstraint(
            "status IN ('ativo', 'inativo', 'arquivado')", name='ck_fornecedores_status'
        ),
        sa.CheckConstraint("tipo_documento IN ('cnpj', 'cpf')", name='ck_fornecedores_tipo_documento'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_interno', name='uq_fornecedores_empresa_codigo_interno'),
        sa.UniqueConstraint(
            'empresa_id', 'codigo_referencia', name='uq_fornecedores_empresa_codigo_referencia'
        ),
        sa.UniqueConstraint(
            'empresa_id',
            'ano_referencia',
            'sequencial_referencia',
            name='uq_fornecedores_empresa_ano_sequencial',
        ),
        # NÃO há UNIQUE de nome nem de documento — mesmo princípio de `clientes`, registrado
        # em docs/padrao-entidades-externas.md. A base importada tem 16 dos 133 registros sem
        # documento e documento repetido entre cadastros distintos; a restrição obrigaria a
        # distorcer o dado real. Possível duplicidade vira AVISO na API, nunca bloqueio.
    )
    op.create_index('ix_fornecedores_empresa_id', 'fornecedores', ['empresa_id'])
    op.create_index('ix_fornecedores_status', 'fornecedores', ['status'])
    op.create_index('ix_fornecedores_codigo_referencia', 'fornecedores', ['codigo_referencia'])
    op.create_index('ix_fornecedores_codigo_interno', 'fornecedores', ['codigo_interno'])
    op.create_index('ix_fornecedores_nome_normalizado', 'fornecedores', ['nome_normalizado'])
    op.create_index('ix_fornecedores_documento_normalizado', 'fornecedores', ['documento_normalizado'])


def downgrade() -> None:
    op.drop_index('ix_fornecedores_documento_normalizado', table_name='fornecedores')
    op.drop_index('ix_fornecedores_nome_normalizado', table_name='fornecedores')
    op.drop_index('ix_fornecedores_codigo_interno', table_name='fornecedores')
    op.drop_index('ix_fornecedores_codigo_referencia', table_name='fornecedores')
    op.drop_index('ix_fornecedores_status', table_name='fornecedores')
    op.drop_index('ix_fornecedores_empresa_id', table_name='fornecedores')
    op.drop_table('fornecedores')
