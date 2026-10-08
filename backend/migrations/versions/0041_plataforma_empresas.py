"""plataforma_empresas

Fundação da Administração da Plataforma (Fase 1B). Migration ADITIVA e reversível (expand → backfill → constraint);
nada existente é removido nem reescrito, `codigo_interno` não é tocado:

  empresas.slug  (NOT NULL, único, 3–40 `[a-z0-9-]`, fora de uma lista mínima de reservados)
      identificador público de URL para o futuro login multiempresa. Backfill: o slug da empresa existente sai do
      `codigo_interno` ("DEMO" → "demo"), com sufixo numérico em colisão. Só depois vira NOT NULL + UNIQUE + CHECK.
  empresas.nome_fantasia  (opcional)
  administradores_plataforma
      autoridade da plataforma, SEPARADA do RBAC tenant (`usuarios.perfil_base` não muda). Uma linha por usuário
      (UNIQUE), `ativo`, quem criou/revogou e quando. Nenhuma linha é criada aqui: a autoridade nasce pelo CLI
      `python -m app.cli.seed_platform_admin`. A linha do usuário atual (conta de sistema) NÃO é alterada.

Revision ID: c5b2e8a91d47
Revises: 9a3d4e6f1b28
Create Date: 2026-10-08 10:00:00.000000

"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5b2e8a91d47'
down_revision: Union[str, None] = '9a3d4e6f1b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Cópia DELIBERADA (uma migration é imutável): a lista/formato de app/core/empresa_slug.py no momento desta revisão.
RESERVADOS = ('plataforma', 'api', 'login', 'logout', 'admin', 'suporte')
FORMATO_SQL = "^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$"


def _slug_base(codigo_interno: str) -> str:
    sem_acentos = unicodedata.normalize('NFKD', codigo_interno).encode('ascii', 'ignore').decode('ascii')
    base = re.sub(r'[^a-z0-9]+', '-', sem_acentos.lower()).strip('-')[:40].strip('-')
    if len(base) < 3 or base in RESERVADOS:
        base = (f'{base}-empresa' if base else 'empresa')[:40].strip('-')
    return base


def _slug_livre(base: str, usados: set[str]) -> str:
    candidato = base
    sufixo = 2
    while candidato in usados or candidato in RESERVADOS or len(candidato) < 3:
        sobra = f'-{sufixo}'
        candidato = f"{base[:40 - len(sobra)].strip('-')}{sobra}"
        sufixo += 1
    return candidato


def upgrade() -> None:
    # 1) expand: colunas nulas
    op.add_column('empresas', sa.Column('slug', sa.String(length=40), nullable=True))
    op.add_column('empresas', sa.Column('nome_fantasia', sa.String(length=255), nullable=True))

    # 2) backfill (determinístico: da mais antiga para a mais nova)
    conexao = op.get_bind()
    linhas = conexao.execute(sa.text('SELECT id, codigo_interno FROM empresas ORDER BY created_at, id')).fetchall()
    usados: set[str] = set()
    for empresa_id, codigo_interno in linhas:
        slug = _slug_livre(_slug_base(codigo_interno), usados)
        usados.add(slug)
        conexao.execute(sa.text('UPDATE empresas SET slug = :slug WHERE id = :id'), {'slug': slug, 'id': empresa_id})

    # 3) constraints
    op.alter_column('empresas', 'slug', existing_type=sa.String(length=40), nullable=False)
    op.create_unique_constraint('uq_empresas_slug', 'empresas', ['slug'])
    op.create_check_constraint('ck_empresas_slug_formato', 'empresas', f"slug ~ '{FORMATO_SQL}'")
    lista = ', '.join(f"'{r}'" for r in RESERVADOS)
    op.create_check_constraint('ck_empresas_slug_reservado', 'empresas', f'slug NOT IN ({lista})')

    op.create_table(
        'administradores_plataforma',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('criado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('revogado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revogado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['revogado_por_usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario_id', name='uq_administradores_plataforma_usuario_id'),
        sa.CheckConstraint('ativo OR revogado_em IS NOT NULL', name='ck_administradores_plataforma_revogacao'),
    )
    op.create_index('ix_administradores_plataforma_ativo', 'administradores_plataforma', ['ativo'])


def downgrade() -> None:
    op.drop_index('ix_administradores_plataforma_ativo', table_name='administradores_plataforma')
    op.drop_table('administradores_plataforma')
    op.drop_constraint('ck_empresas_slug_reservado', 'empresas', type_='check')
    op.drop_constraint('ck_empresas_slug_formato', 'empresas', type_='check')
    op.drop_constraint('uq_empresas_slug', 'empresas', type_='unique')
    op.drop_column('empresas', 'nome_fantasia')
    op.drop_column('empresas', 'slug')
