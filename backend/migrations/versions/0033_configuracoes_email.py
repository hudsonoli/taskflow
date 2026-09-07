"""configuracoes_email

Fase 2G.7B1 — configuração de disparo SMTP, singleton por Empresa (mesmo padrão de
`regra_expediente`, ver app/models/regra_expediente.py). Não altera nenhuma tabela existente.

`smtp_senha_criptografada` guarda só o ciphertext Fernet (nunca texto puro) — ver
app/services/configuracao_email_crypto_service.py. A chave mestra (`EMAIL_CONFIG_ENCRYPTION_KEY`)
nunca é persistida, só variável de ambiente.

Revision ID: ba64228ee8e1
Revises: afdf2d44c7b2
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba64228ee8e1'
down_revision: Union[str, None] = 'afdf2d44c7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'configuracoes_email',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('smtp_host', sa.String(length=255), nullable=True),
        sa.Column('smtp_port', sa.Integer(), nullable=True),
        sa.Column('smtp_usuario', sa.String(length=255), nullable=True),
        sa.Column('smtp_senha_criptografada', sa.Text(), nullable=True),
        sa.Column('remetente_email', sa.String(length=255), nullable=True),
        sa.Column('remetente_nome', sa.String(length=255), nullable=True),
        sa.Column('usar_tls', sa.Boolean(), nullable=False),
        sa.Column('usar_ssl', sa.Boolean(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'smtp_port IS NULL OR (smtp_port >= 1 AND smtp_port <= 65535)',
            name='ck_configuracoes_email_smtp_port',
        ),
        sa.CheckConstraint(
            "smtp_host IS NULL OR trim(smtp_host) <> ''",
            name='ck_configuracoes_email_smtp_host',
        ),
        sa.CheckConstraint(
            "remetente_email IS NULL OR trim(remetente_email) <> ''",
            name='ck_configuracoes_email_remetente_email',
        ),
        sa.CheckConstraint(
            'NOT (usar_tls AND usar_ssl)',
            name='ck_configuracoes_email_tls_ssl_exclusivos',
        ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', name='uq_configuracoes_email_empresa_id'),
    )
    op.create_index('ix_configuracoes_email_empresa_id', 'configuracoes_email', ['empresa_id'])


def downgrade() -> None:
    op.drop_index('ix_configuracoes_email_empresa_id', table_name='configuracoes_email')
    op.drop_table('configuracoes_email')
