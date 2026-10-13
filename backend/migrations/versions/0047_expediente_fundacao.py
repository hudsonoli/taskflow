"""Expediente — fundação (Fase Expediente 1): períodos, flags, fuso, dias especiais, isenção por usuário e origem da pausa.

TUDO NASCE INATIVO / COMPATÍVEL: as duas flags críticas (`bloquear_fora_expediente`, `pausar_no_fim_periodo`) nascem FALSE e nada as lê ainda; nenhum acesso é bloqueado
e nenhuma demanda é pausada por esta migration.

Estratégia de compatibilidade ("expand", sem "contract" agora):
- `regra_expediente_periodos` nasce COPIANDO os horários atuais: `manha_*` → período 1, `tarde_*` → período 2 (só dias ativos com a janela completa e início < fim). Os
  horários nominais são preservados byte a byte; NENHUM horário é deslocado.
- `tolerancia_retomada_minutos` (semântica antiga: a ENTRADA em execução é aceita X min antes do início do 2º período) NÃO é renomeada, convertida nem somada aos
  períodos: continua na coluna e continua sendo honrada por `esta_dentro_expediente`. Assim o gate atual, o SLA e os prazos se comportam exatamente como antes. A nova
  `antecedencia_acesso_minutos` (default 30) é OUTRA coisa (acesso, não trabalho) e ainda não é lida por nada.
- As colunas legadas `regra_expediente_dias.manha_*/tarde_*` e `ativo` ficam (o código novo as mantém espelhadas quando o dia tem exatamente 2 períodos); só o CHECK
  antigo (4 horários obrigatórios em dia ativo) é removido, porque um dia pode ter 1, 3 ou mais períodos. Remoção das colunas = fase futura.
- `regra_expediente.timezone` é preenchido com o fuso atual da aplicação (APP_TIMEZONE, padrão America/Sao_Paulo).
- Demandas hoje `pausada` ganham `pausa_origem='manual'` (nunca existiu pausa automática), `pausada_em` fica NULL (desconhecido; nada é inventado).

Downgrade: reconstrói `manha_*/tarde_*` a partir dos 2 primeiros períodos de cada dia (dia com 1 período ou com 0 volta como inativo; períodos além do 2º são
descartados — perda documentada), recria o CHECK antigo e remove tudo o que foi criado aqui.
"""
import os
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op

revision = "a3c8e5f17d24"
down_revision = "f2c6a9d41b87"
branch_labels = None
depends_on = None

CHECK_LEGADO = "ck_regra_expediente_dias_janelas_validas"
CHECK_LEGADO_SQL = (
    "NOT ativo OR ("
    "manha_inicio IS NOT NULL AND manha_fim IS NOT NULL AND "
    "tarde_inicio IS NOT NULL AND tarde_fim IS NOT NULL AND "
    "manha_inicio < manha_fim AND tarde_inicio < tarde_fim AND manha_fim <= tarde_inicio"
    ")"
)


def _fuso_atual() -> str:
    nome = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    try:
        ZoneInfo(nome)
    except Exception:  # noqa: BLE001 — fuso inválido no ambiente: cai no padrão do produto (o app também recusaria subir)
        return "America/Sao_Paulo"
    return nome


def upgrade() -> None:
    fuso = _fuso_atual()

    # ── regra: flags, antecedência, fuso ────────────────────────────────────────────────────────────────────────
    op.add_column("regra_expediente", sa.Column("bloquear_fora_expediente", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("regra_expediente", sa.Column("pausar_no_fim_periodo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("regra_expediente", sa.Column("antecedencia_acesso_minutos", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("regra_expediente", sa.Column("timezone", sa.String(length=64), nullable=False, server_default=fuso))
    op.add_column("regra_expediente", sa.Column("feriados_automaticos", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint(
        "ck_regra_expediente_antecedencia_acesso",
        "regra_expediente",
        "antecedencia_acesso_minutos >= 0 AND antecedencia_acesso_minutos <= 720",
    )

    # ── períodos (cópia fiel dos horários atuais) ───────────────────────────────────────────────────────────────
    op.create_table(
        "regra_expediente_periodos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("regra_expediente_id", sa.String(length=36), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("inicio", sa.Time(), nullable=False),
        sa.Column("fim", sa.Time(), nullable=False),
        sa.CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_regra_expediente_periodos_dia_semana"),
        sa.CheckConstraint("ordem >= 1", name="ck_regra_expediente_periodos_ordem"),
        sa.CheckConstraint("inicio < fim", name="ck_regra_expediente_periodos_inicio_fim"),
        sa.ForeignKeyConstraint(["regra_expediente_id"], ["regra_expediente.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regra_expediente_id", "dia_semana", "ordem", name="uq_regra_expediente_periodos_regra_dia_ordem"),
    )
    op.create_index("ix_regra_expediente_periodos_regra_id", "regra_expediente_periodos", ["regra_expediente_id"])
    conexao = op.get_bind()
    conexao.execute(
        sa.text(
            "INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) "
            "SELECT gen_random_uuid()::text, regra_expediente_id, dia_semana, 1, manha_inicio, manha_fim "
            "FROM regra_expediente_dias "
            "WHERE ativo AND manha_inicio IS NOT NULL AND manha_fim IS NOT NULL AND manha_inicio < manha_fim"
        )
    )
    conexao.execute(
        sa.text(
            "INSERT INTO regra_expediente_periodos (id, regra_expediente_id, dia_semana, ordem, inicio, fim) "
            "SELECT gen_random_uuid()::text, d.regra_expediente_id, d.dia_semana, "
            "CASE WHEN d.manha_inicio IS NOT NULL AND d.manha_fim IS NOT NULL AND d.manha_inicio < d.manha_fim THEN 2 ELSE 1 END, "
            "d.tarde_inicio, d.tarde_fim "
            "FROM regra_expediente_dias d "
            "WHERE d.ativo AND d.tarde_inicio IS NOT NULL AND d.tarde_fim IS NOT NULL AND d.tarde_inicio < d.tarde_fim"
        )
    )
    # o CHECK antigo (4 horários obrigatórios) não cabe mais: um dia pode ter 1, 3 ou mais períodos
    op.drop_constraint(CHECK_LEGADO, "regra_expediente_dias", type_="check")

    # ── dias especiais ──────────────────────────────────────────────────────────────────────────────────────────
    op.create_table(
        "regra_expediente_dias_especiais",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("regra_expediente_id", sa.String(length=36), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("origem", sa.String(length=16), nullable=False),
        sa.Column("tipo", sa.String(length=24), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origem IN ('automatico', 'manual')", name="ck_regra_expediente_dias_especiais_origem"),
        sa.CheckConstraint(
            "tipo IN ('feriado', 'recesso', 'trabalho_excepcional', 'ignorado')", name="ck_regra_expediente_dias_especiais_tipo"
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["regra_expediente_id"], ["regra_expediente.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regra_expediente_id", "data", "origem", name="uq_regra_expediente_dias_especiais_regra_data_origem"),
    )
    op.create_index("ix_regra_expediente_dias_especiais_regra_data", "regra_expediente_dias_especiais", ["regra_expediente_id", "data"])
    op.create_index("ix_regra_expediente_dias_especiais_empresa_id", "regra_expediente_dias_especiais", ["empresa_id"])
    op.create_table(
        "regra_expediente_dias_especiais_periodos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dia_especial_id", sa.String(length=36), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("inicio", sa.Time(), nullable=False),
        sa.Column("fim", sa.Time(), nullable=False),
        sa.CheckConstraint("ordem >= 1", name="ck_regra_expediente_dias_especiais_periodos_ordem"),
        sa.CheckConstraint("inicio < fim", name="ck_regra_expediente_dias_especiais_periodos_inicio_fim"),
        sa.ForeignKeyConstraint(["dia_especial_id"], ["regra_expediente_dias_especiais.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dia_especial_id", "ordem", name="uq_regra_expediente_dias_especiais_periodos_dia_ordem"),
    )
    op.create_index("ix_regra_expediente_dias_especiais_periodos_dia_id", "regra_expediente_dias_especiais_periodos", ["dia_especial_id"])

    # ── usuário: isenção individual (só o campo) ────────────────────────────────────────────────────────────────
    op.add_column("usuarios", sa.Column("acesso_fora_expediente", sa.Boolean(), nullable=False, server_default=sa.false()))

    # ── demanda: origem da pausa ────────────────────────────────────────────────────────────────────────────────
    op.add_column("demandas", sa.Column("pausa_origem", sa.String(length=16), nullable=True))
    op.add_column("demandas", sa.Column("pausada_em", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_demandas_pausa_origem", "demandas", "pausa_origem IS NULL OR pausa_origem IN ('manual', 'expediente')")
    conexao.execute(sa.text("UPDATE demandas SET pausa_origem = 'manual' WHERE status = 'pausada'"))


def downgrade() -> None:
    conexao = op.get_bind()

    op.drop_constraint("ck_demandas_pausa_origem", "demandas", type_="check")
    op.drop_column("demandas", "pausada_em")
    op.drop_column("demandas", "pausa_origem")

    op.drop_column("usuarios", "acesso_fora_expediente")

    op.drop_index("ix_regra_expediente_dias_especiais_periodos_dia_id", table_name="regra_expediente_dias_especiais_periodos")
    op.drop_table("regra_expediente_dias_especiais_periodos")
    op.drop_index("ix_regra_expediente_dias_especiais_empresa_id", table_name="regra_expediente_dias_especiais")
    op.drop_index("ix_regra_expediente_dias_especiais_regra_data", table_name="regra_expediente_dias_especiais")
    op.drop_table("regra_expediente_dias_especiais")

    # reconstrói o legado a partir dos 2 primeiros períodos de cada dia (dia com 0 ou 1 período volta INATIVO; do 3º em diante é descartado)
    conexao.execute(
        sa.text(
            "UPDATE regra_expediente_dias d SET ativo = false, manha_inicio = NULL, manha_fim = NULL, tarde_inicio = NULL, tarde_fim = NULL"
        )
    )
    conexao.execute(
        sa.text(
            "UPDATE regra_expediente_dias d SET ativo = true, "
            "manha_inicio = p1.inicio, manha_fim = p1.fim, tarde_inicio = p2.inicio, tarde_fim = p2.fim "
            "FROM regra_expediente_periodos p1, regra_expediente_periodos p2 "
            "WHERE p1.regra_expediente_id = d.regra_expediente_id AND p1.dia_semana = d.dia_semana AND p1.ordem = 1 "
            "AND p2.regra_expediente_id = d.regra_expediente_id AND p2.dia_semana = d.dia_semana AND p2.ordem = 2 "
            "AND p1.fim <= p2.inicio"
        )
    )
    op.create_check_constraint(CHECK_LEGADO, "regra_expediente_dias", CHECK_LEGADO_SQL)

    op.drop_index("ix_regra_expediente_periodos_regra_id", table_name="regra_expediente_periodos")
    op.drop_table("regra_expediente_periodos")

    op.drop_constraint("ck_regra_expediente_antecedencia_acesso", "regra_expediente", type_="check")
    op.drop_column("regra_expediente", "feriados_automaticos")
    op.drop_column("regra_expediente", "timezone")
    op.drop_column("regra_expediente", "antecedencia_acesso_minutos")
    op.drop_column("regra_expediente", "pausar_no_fim_periodo")
    op.drop_column("regra_expediente", "bloquear_fora_expediente")
