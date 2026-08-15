"""projetos: remove codigo_interno (microfase 2D.1)

`codigo_interno` entrou na Fase 2D como "chave estável de importação/integração". A decisão
de arquitetura que veio depois eliminou a premissa: **não haverá importação histórica de
Projetos** — eles nascem vazios e são criados pela interface.

Sem importação, o campo perdeu a função e o levantamento confirmou que nunca teve uma:

- o valor gravado era `codigo_interno = codigo_referencia`, **cópia literal** — o único
  caminho de escrita da coluna;
- diferente de Cliente e Fornecedor, Projeto **nunca teve** o método
  `create_projeto_com_codigo_legado`, porque nunca houve seed nem importador para chamá-lo;
- nenhum componente de Projeto o exibia;
- a busca fazia `OR codigo_interno ILIKE`, condição sempre redundante com a do
  `codigo_referencia` por serem o mesmo valor.

Ou seja: uma coluna NOT NULL, com UNIQUE e índice próprios, duplicando outra coluna para
servir a um cenário que não existe. Removê-la agora evita que Demanda copie o padrão por
simetria — Demanda nasce só com UUID + `codigo_referencia`.

Projeto passa a ter dois identificadores: `id` (UUID técnico) e `codigo_referencia`
(P26000001, identidade de negócio).

Revision ID: 9c2f8ab41d63
Revises: b1d5f30c8e72
Create Date: 2026-08-09 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2f8ab41d63'
down_revision: Union[str, None] = 'b1d5f30c8e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_projetos_codigo_interno', table_name='projetos')
    op.drop_constraint('uq_projetos_empresa_codigo_interno', 'projetos', type_='unique')
    op.drop_column('projetos', 'codigo_interno')


def downgrade() -> None:
    # Recria a coluna preenchendo-a com `codigo_referencia` — exatamente o que o código
    # gravava antes da remoção. Sem isso, o NOT NULL falharia em qualquer base com dados.
    op.add_column('projetos', sa.Column('codigo_interno', sa.String(length=64), nullable=True))
    op.execute('UPDATE projetos SET codigo_interno = codigo_referencia')
    op.alter_column('projetos', 'codigo_interno', nullable=False)
    op.create_unique_constraint(
        'uq_projetos_empresa_codigo_interno', 'projetos', ['empresa_id', 'codigo_interno']
    )
    op.create_index('ix_projetos_codigo_interno', 'projetos', ['codigo_interno'])
