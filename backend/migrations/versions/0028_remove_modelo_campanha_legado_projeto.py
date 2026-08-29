"""remove_modelo_campanha_legado_projeto

Fase 2G.5D — remoção física do JSONB legado de Modelo de Campanha em Projeto
(`projetos.modelo_campanha`/`modelo_campanha_id`, criados na migration 0012). O snapshot
relacional (`projeto_modelo_campanha`/`projeto_modelo_campanha_itens`, migration 0027) é a
única implementação de Modelo de Campanha em Projeto a partir daqui.

Pré-condição validada antes desta migration (não reforçada em código aqui — decisão humana,
não constraint de banco): produção tinha 0 Projetos; localmente, o único Projeto de QA com
JSONB legado não-vazio e sem snapshot (`TESTE 2G.1 - workflow real`) foi materializado pela
CLI `app.cli.migrar_modelo_campanha_projetos` (modo real, `--projeto-id` restrito a ele) antes
desta migration rodar — ver relatório da Fase 2G.5D.

Só remove as 2 colunas. Nenhuma outra alteração de schema.

## Downgrade

Recria a ESTRUTURA das colunas (mesmos tipos/nullability de 0012) — nunca o conteúdo. Uma vez
que o upgrade roda, o dado que estava em `modelo_campanha`/`modelo_campanha_id` é apagado pelo
Postgres no DROP COLUMN; não existe cópia de segurança implícita nesta migration nem tentativa
de reconstruí-lo. Downgrade sem dado renovado nesses campos é o comportamento correto e
esperado — não é um bug do downgrade.

Revision ID: ffbeb0e786e8
Revises: 2cb9f5dcaba9
Create Date: 2026-08-29 11:44:39.726299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ffbeb0e786e8'
down_revision: Union[str, None] = '2cb9f5dcaba9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('projetos', 'modelo_campanha')
    op.drop_column('projetos', 'modelo_campanha_id')


def downgrade() -> None:
    # Mesmos tipos exatos de 0012_projeto.py — só estrutura, sem dado (ver docstring acima).
    op.add_column('projetos', sa.Column('modelo_campanha_id', sa.String(length=64), nullable=True))
    op.add_column(
        'projetos',
        sa.Column(
            'modelo_campanha',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
            nullable=True,
        ),
    )
