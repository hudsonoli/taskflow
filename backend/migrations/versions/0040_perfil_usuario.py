"""perfil_usuario

Perfil do usuário + central de notificações. Migration ADITIVA e reversível (nada existente é alterado,
nenhuma linha é reescrita, sem downtime):

  usuarios.foto_perfil_storage_key / foto_perfil_mime_type
      foto de perfil enviada pelo próprio usuário (PNG/JPEG). Só a referência; o arquivo fica no volume de
      uploads. Os dois nascem juntos ou nulos (CHECK). Todo usuário existente fica sem foto própria
      (continua valendo `foto_url`, a foto externa do Google).

  notificacao_leituras (usuario_id, evento_id) PK
      quem já leu qual evento. As notificações em si NÃO são registros novos: são uma visão tipada dos
      eventos de domínio (`eventos`) das demandas do usuário; sem linha aqui = não lida.

`telefone` já existia em `usuarios` e é reaproveitado como o contato editável do perfil.

Revision ID: 9a3d4e6f1b28
Revises: 7c1e9b4d2a50
Create Date: 2026-10-07 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3d4e6f1b28'
down_revision: Union[str, None] = '7c1e9b4d2a50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('foto_perfil_storage_key', sa.String(length=255), nullable=True))
    op.add_column('usuarios', sa.Column('foto_perfil_mime_type', sa.String(length=32), nullable=True))
    op.create_check_constraint(
        'ck_usuarios_foto_perfil_par',
        'usuarios',
        '(foto_perfil_storage_key IS NULL) = (foto_perfil_mime_type IS NULL)',
    )

    op.create_table(
        'notificacao_leituras',
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('evento_id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('lida_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evento_id'], ['eventos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.PrimaryKeyConstraint('usuario_id', 'evento_id'),
    )
    op.create_index('ix_notificacao_leituras_empresa_id', 'notificacao_leituras', ['empresa_id'])
    op.create_index('ix_notificacao_leituras_evento_id', 'notificacao_leituras', ['evento_id'])


def downgrade() -> None:
    op.drop_index('ix_notificacao_leituras_evento_id', table_name='notificacao_leituras')
    op.drop_index('ix_notificacao_leituras_empresa_id', table_name='notificacao_leituras')
    op.drop_table('notificacao_leituras')
    op.drop_constraint('ck_usuarios_foto_perfil_par', 'usuarios', type_='check')
    op.drop_column('usuarios', 'foto_perfil_mime_type')
    op.drop_column('usuarios', 'foto_perfil_storage_key')
