"""numeracao_configuravel

Numeração configurável de tarefas (Fase 7D.1). Migration ADITIVA e reversível (expand → backfill → constraint);
`demandas.numero_operacional` (inteiro) e a sua unicidade NÃO são tocados:

  sequencias_operacionais.prefixo / digitos / incluir_ano / separador
      FORMATO das PRÓXIMAS emissões, por (empresa, tipo_entidade). Defaults = comportamento de sempre: `#<n>`.
      (`reinicio_anual` NÃO existe — fase futura.)
  demandas.identificador  (NOT NULL, único por empresa)
      o identificador EMITIDO, gravado no momento da criação e imutável: `#845` continua `#845` mesmo que a empresa passe
      a emitir `BOX-2026-00846`. Backfill: `'#' || numero_operacional` — o formato que existia originalmente, SEM padding e
      SEM consultar a configuração atual. Só depois de validar que não sobrou NULL vira NOT NULL + UNIQUE (empresa_id, identificador).

Revision ID: e4a7c1d93b60
Revises: c5b2e8a91d47
Create Date: 2026-10-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a7c1d93b60'
down_revision: Union[str, None] = 'c5b2e8a91d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) formato das próximas emissões (defaults preservam o comportamento atual)
    op.add_column('sequencias_operacionais', sa.Column('prefixo', sa.String(length=16), nullable=False, server_default='#'))
    op.add_column('sequencias_operacionais', sa.Column('digitos', sa.SmallInteger(), nullable=False, server_default='1'))
    op.add_column('sequencias_operacionais', sa.Column('incluir_ano', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('sequencias_operacionais', sa.Column('separador', sa.String(length=4), nullable=False, server_default=''))
    op.create_check_constraint('ck_sequencias_operacionais_digitos', 'sequencias_operacionais', 'digitos BETWEEN 1 AND 10')

    # 2) expand: identificador nulo → backfill → validação → NOT NULL → UNIQUE por empresa
    op.add_column('demandas', sa.Column('identificador', sa.String(length=40), nullable=True))
    op.execute("UPDATE demandas SET identificador = '#' || CAST(numero_operacional AS text)")
    ausentes = op.get_bind().execute(sa.text('SELECT count(*) FROM demandas WHERE identificador IS NULL')).scalar_one()
    if ausentes:
        raise RuntimeError(f'backfill de demandas.identificador incompleto: {ausentes} linha(s) sem identificador')
    op.alter_column('demandas', 'identificador', existing_type=sa.String(length=40), nullable=False)
    op.create_unique_constraint('uq_demandas_empresa_identificador', 'demandas', ['empresa_id', 'identificador'])


def downgrade() -> None:
    op.drop_constraint('uq_demandas_empresa_identificador', 'demandas', type_='unique')
    op.drop_column('demandas', 'identificador')
    op.drop_constraint('ck_sequencias_operacionais_digitos', 'sequencias_operacionais', type_='check')
    op.drop_column('sequencias_operacionais', 'separador')
    op.drop_column('sequencias_operacionais', 'incluir_ano')
    op.drop_column('sequencias_operacionais', 'digitos')
    op.drop_column('sequencias_operacionais', 'prefixo')
