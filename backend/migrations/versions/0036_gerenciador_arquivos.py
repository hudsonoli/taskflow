"""gerenciador_arquivos

Gerenciador central de Arquivos (MVP) — evolui `demanda_arquivos` in-place, sem nova
arquitetura de storage. Nenhum arquivo físico é reescrito, nenhum registro legado muda de
comportamento: todo registro hoje existente é `ANEXO` (via `server_default`), continua
listando/baixando/excluindo exatamente como antes.

Nullability real inspecionada ANTES desta migration (migration 0021, confirmada idêntica ao
model atual, `app/models/demanda_arquivo.py`):
  nome_original   NOT NULL
  nome_fisico     NOT NULL
  content_type    NULL (já era)
  tamanho_bytes   NOT NULL

`LINK` não tem arquivo físico — por isso `nome_original`/`nome_fisico`/`tamanho_bytes` viram
nullable aqui (passam a ser obrigatórios só para ANEXO/LAYOUT, nunca para LINK, reforçado pelo
CHECK `ck_demanda_arquivos_fisico_ou_link` abaixo, mesmo padrão de
`ck_sessoes_trabalho_ativa_sem_fim`/`ck_sessoes_trabalho_encerrada_com_fim` em
`app/models/sessao_trabalho.py`: coerência entre colunas garantida no banco, não só no
service).

Revision ID: e4464f8f7bb9
Revises: 57c9ac75e1bc
Create Date: 2026-10-02 00:25:07.187917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4464f8f7bb9'
down_revision: Union[str, None] = '57c9ac75e1bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('demanda_arquivos', 'nome_original', existing_type=sa.String(length=255), nullable=True)
    op.alter_column('demanda_arquivos', 'nome_fisico', existing_type=sa.String(length=64), nullable=True)
    op.alter_column('demanda_arquivos', 'tamanho_bytes', existing_type=sa.Integer(), nullable=True)

    op.add_column('demanda_arquivos', sa.Column('tipo', sa.String(length=32), nullable=False, server_default='anexo'))
    op.add_column('demanda_arquivos', sa.Column('status_layout', sa.String(length=32), nullable=True))
    op.add_column('demanda_arquivos', sa.Column('url', sa.String(length=500), nullable=True))
    op.add_column('demanda_arquivos', sa.Column('titulo', sa.String(length=255), nullable=True))
    op.add_column('demanda_arquivos', sa.Column('descricao', sa.Text(), nullable=True))

    op.create_check_constraint(
        'ck_demanda_arquivos_tipo',
        'demanda_arquivos',
        "tipo IN ('anexo', 'layout', 'link')",
    )
    op.create_check_constraint(
        'ck_demanda_arquivos_status_layout',
        'demanda_arquivos',
        "status_layout IS NULL OR status_layout IN ('novo', 'aprovado', 'reprovado', 'solicitar_alteracao')",
    )
    op.create_check_constraint(
        'ck_demanda_arquivos_status_layout_so_em_layout',
        'demanda_arquivos',
        "status_layout IS NULL OR tipo = 'layout'",
    )
    op.create_check_constraint(
        'ck_demanda_arquivos_fisico_ou_link',
        'demanda_arquivos',
        """
        (tipo IN ('anexo', 'layout')
            AND nome_original IS NOT NULL
            AND nome_fisico IS NOT NULL
            AND tamanho_bytes IS NOT NULL
            AND url IS NULL)
        OR
        (tipo = 'link'
            AND nome_original IS NULL
            AND nome_fisico IS NULL
            AND tamanho_bytes IS NULL
            AND url IS NOT NULL
            AND titulo IS NOT NULL)
        """,
    )


def downgrade() -> None:
    op.drop_constraint('ck_demanda_arquivos_fisico_ou_link', 'demanda_arquivos', type_='check')
    op.drop_constraint('ck_demanda_arquivos_status_layout_so_em_layout', 'demanda_arquivos', type_='check')
    op.drop_constraint('ck_demanda_arquivos_status_layout', 'demanda_arquivos', type_='check')
    op.drop_constraint('ck_demanda_arquivos_tipo', 'demanda_arquivos', type_='check')

    op.drop_column('demanda_arquivos', 'descricao')
    op.drop_column('demanda_arquivos', 'titulo')
    op.drop_column('demanda_arquivos', 'url')
    op.drop_column('demanda_arquivos', 'status_layout')
    op.drop_column('demanda_arquivos', 'tipo')

    op.alter_column('demanda_arquivos', 'tamanho_bytes', existing_type=sa.Integer(), nullable=False)
    op.alter_column('demanda_arquivos', 'nome_fisico', existing_type=sa.String(length=64), nullable=False)
    op.alter_column('demanda_arquivos', 'nome_original', existing_type=sa.String(length=255), nullable=False)
