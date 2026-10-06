"""personalizacao_visual

Identidade visual por Empresa (logo, cor principal, cor secundária e tema claro/escuro), aplicada a
todos os usuários da empresa. Migration ADITIVA: uma tabela nova, nenhuma coluna ou dado existente
alterado, sem necessidade de downtime. Sem linha para uma Empresa = padrões atuais do TaskFloww
(a linha só nasce na primeira alteração), então nenhuma Empresa existente muda de aparência.

  configuracoes_personalizacao
    empresa_id          UNIQUE (singleton por Empresa)
    logo_storage_key    caminho relativo gerado pelo sistema no volume de uploads (nunca o binário)
    logo_mime_type      image/png | image/gif (canônico)
    cor_primaria        #RRGGBB
    cor_secundaria      #RRGGBB
    tema                claro | escuro

Reversível: `downgrade` remove a tabela (o volume de uploads não é tocado).

Revision ID: 48bd07aba026
Revises: 3b7f1a9c52d4
Create Date: 2026-10-06 11:06:36.869121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48bd07aba026'
down_revision: Union[str, None] = '3b7f1a9c52d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'configuracoes_personalizacao',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('logo_storage_key', sa.String(length=255), nullable=True),
        sa.Column('logo_mime_type', sa.String(length=32), nullable=True),
        sa.Column('cor_primaria', sa.String(length=7), nullable=False),
        sa.Column('cor_secundaria', sa.String(length=7), nullable=False),
        sa.Column('tema', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cor_primaria ~ '^#[0-9a-fA-F]{6}$'", name='ck_configuracoes_personalizacao_cor_primaria'),
        sa.CheckConstraint("cor_secundaria ~ '^#[0-9a-fA-F]{6}$'", name='ck_configuracoes_personalizacao_cor_secundaria'),
        sa.CheckConstraint("tema IN ('claro', 'escuro')", name='ck_configuracoes_personalizacao_tema'),
        sa.CheckConstraint(
            '(logo_storage_key IS NULL) = (logo_mime_type IS NULL)',
            name='ck_configuracoes_personalizacao_logo_completo',
        ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', name='uq_configuracoes_personalizacao_empresa_id'),
    )
    op.create_index(
        'ix_configuracoes_personalizacao_empresa_id', 'configuracoes_personalizacao', ['empresa_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_configuracoes_personalizacao_empresa_id', table_name='configuracoes_personalizacao')
    op.drop_table('configuracoes_personalizacao')
