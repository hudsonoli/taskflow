"""demanda + vínculos N:N + sequencias_operacionais (Fase 2E.1)

Demanda é a unidade de trabalho da operação — a interface chama de Tarefa. Não são entidades
diferentes: `/tarefas` renderiza `DemandasView`.

## Dois números visíveis

- `codigo_referencia` (T26000001) — identidade oficial, **reinicia por ano**, emitido por
  `sequencias_referencia` como em D/E/C/F/P;
- `numero_operacional` (2063) — identificação de trabalho, **contínuo**, emitido por
  `sequencias_operacionais`, criada aqui.

São independentes: a primeira demanda é `T26000001` e `2063` ao mesmo tempo; em 2027 a
primeira é `T27000001` e `15843`.

`sequencias_operacionais` não tem `ano` de propósito — é o que a distingue de
`sequencias_referencia`, cuja chave inclui o ano justamente para reiniciar. Nasce **vazia**:
o número de go-live entra por `app/cli/inicializar_numero_operacional.py`, nunca pelo
`seed_all`, porque continuidade com o iClips é dado de produção, não de reconstrução.

Sem `codigo_interno`: não haverá importação histórica de Demandas.

Revision ID: 5f1c9e73b204
Revises: 9c2f8ab41d63
Create Date: 2026-08-09 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f1c9e73b204'
down_revision: Union[str, None] = '9c2f8ab41d63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sequencias_operacionais',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('tipo_entidade', sa.String(length=32), nullable=False),
        sa.Column('ultimo_numero', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        # Reforça no banco a regra que o CLI aplica: número operacional nunca é negativo.
        sa.CheckConstraint('ultimo_numero >= 0', name='ck_sequencias_operacionais_ultimo_numero'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        # SEM `ano` — é o que diferencia este contador do de `sequencias_referencia`.
        sa.UniqueConstraint('empresa_id', 'tipo_entidade', name='uq_sequencias_operacionais_empresa_tipo'),
    )

    op.create_table(
        'demandas',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('empresa_id', sa.String(length=36), nullable=False),
        sa.Column('codigo_referencia', sa.String(length=16), nullable=False),
        sa.Column('ano_referencia', sa.SmallInteger(), nullable=False),
        sa.Column('sequencial_referencia', sa.Integer(), nullable=False),
        # Inteiro, não texto: é número, e será ordenado e comparado como tal. O `#` é
        # apresentação.
        sa.Column('numero_operacional', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        # Campo legado sem semântica formal documentada — migra como texto livre.
        sa.Column('pit', sa.String(length=64), nullable=True),
        sa.Column('briefing', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('prioridade', sa.String(length=16), nullable=False),
        sa.Column('sinalizada', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('motivo_bloqueio', sa.String(length=500), nullable=True),
        sa.Column('cliente_id', sa.String(length=36), nullable=True),
        sa.Column('projeto_id', sa.String(length=36), nullable=True),
        sa.Column('criado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('data_inicio', sa.Date(), nullable=True),
        sa.Column('data_fim_prevista', sa.Date(), nullable=True),
        sa.Column('prazo_etapa_atual', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enviado_cliente_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('prazo_retorno_cliente', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retorno_recebido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_conclusao_enviado', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_conclusao_data', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arquivado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('motivo_arquivamento', sa.String(length=500), nullable=True),
        sa.Column('restaurado_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restaurado_por_usuario_id', sa.String(length=36), nullable=True),
        sa.Column('status_anterior_arquivamento', sa.String(length=32), nullable=True),
        # `arquivada` no feminino acompanha o vocabulário do próprio domínio (concluida,
        # cancelada, pausada) — os demais domínios usam masculino, e cada service tem sua
        # constante local, então não há código genérico que dependa da grafia.
        sa.CheckConstraint(
            "status IN ('rascunho', 'planejada', 'em_execucao', 'pausada', 'bloqueada', "
            "'aguardando_cliente', 'concluida', 'cancelada', 'arquivada')",
            name='ck_demandas_status',
        ),
        sa.CheckConstraint("prioridade IN ('baixa', 'media', 'alta')", name='ck_demandas_prioridade'),
        sa.CheckConstraint(
            'data_inicio IS NULL OR data_fim_prevista IS NULL OR data_fim_prevista >= data_inicio',
            name='ck_demandas_periodo',
        ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        # SET NULL nos três: arquivar cliente, projeto ou usuário nunca derruba a demanda.
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['projeto_id'], ['projetos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'codigo_referencia', name='uq_demandas_empresa_codigo_referencia'),
        sa.UniqueConstraint(
            'empresa_id', 'ano_referencia', 'sequencial_referencia', name='uq_demandas_empresa_ano_sequencial'
        ),
        # O piso real do número operacional: mesmo com o contador adulterado direto no banco,
        # o INSERT falha em vez de reemitir um número já usado.
        sa.UniqueConstraint('empresa_id', 'numero_operacional', name='uq_demandas_empresa_numero_operacional'),
        # NÃO há UNIQUE de nome — duas tarefas "Ajuste banner" no mesmo dia são rotina.
    )
    op.create_index('ix_demandas_empresa_id', 'demandas', ['empresa_id'])
    op.create_index('ix_demandas_status', 'demandas', ['status'])
    op.create_index('ix_demandas_codigo_referencia', 'demandas', ['codigo_referencia'])
    op.create_index('ix_demandas_numero_operacional', 'demandas', ['numero_operacional'])
    op.create_index('ix_demandas_cliente_id', 'demandas', ['cliente_id'])
    op.create_index('ix_demandas_projeto_id', 'demandas', ['projeto_id'])
    op.create_index('ix_demandas_criado_por_usuario_id', 'demandas', ['criado_por_usuario_id'])
    # A Pauta ordena por este campo — índice evita sort em memória a cada abertura.
    op.create_index('ix_demandas_prazo_etapa_atual', 'demandas', ['prazo_etapa_atual'])

    # CASCADE: demanda nunca é apagada fisicamente (só arquivada); serve para não deixar
    # órfão numa remoção real de manutenção.
    op.create_table(
        'demanda_responsaveis',
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('demanda_id', 'usuario_id'),
    )
    # Sustenta o escopo "Meu Dia": de quais demandas esta pessoa é responsável.
    op.create_index('ix_demanda_responsaveis_usuario_id', 'demanda_responsaveis', ['usuario_id'])

    op.create_table(
        'demanda_departamentos',
        sa.Column('demanda_id', sa.String(length=36), nullable=False),
        sa.Column('departamento_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['demanda_id'], ['demandas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['departamento_id'], ['departamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('demanda_id', 'departamento_id'),
    )
    # Sustenta o escopo "Meu Departamento".
    op.create_index(
        'ix_demanda_departamentos_departamento_id', 'demanda_departamentos', ['departamento_id']
    )


def downgrade() -> None:
    op.drop_index('ix_demanda_departamentos_departamento_id', table_name='demanda_departamentos')
    op.drop_table('demanda_departamentos')

    op.drop_index('ix_demanda_responsaveis_usuario_id', table_name='demanda_responsaveis')
    op.drop_table('demanda_responsaveis')

    op.drop_index('ix_demandas_prazo_etapa_atual', table_name='demandas')
    op.drop_index('ix_demandas_criado_por_usuario_id', table_name='demandas')
    op.drop_index('ix_demandas_projeto_id', table_name='demandas')
    op.drop_index('ix_demandas_cliente_id', table_name='demandas')
    op.drop_index('ix_demandas_numero_operacional', table_name='demandas')
    op.drop_index('ix_demandas_codigo_referencia', table_name='demandas')
    op.drop_index('ix_demandas_status', table_name='demandas')
    op.drop_index('ix_demandas_empresa_id', table_name='demandas')
    op.drop_table('demandas')

    op.drop_table('sequencias_operacionais')
