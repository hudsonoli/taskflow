from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Padrões que reproduzem a aparência atual do TaskFloww (escala `indigo` e `violet` do Tailwind):
# primária = indigo-500, secundária = violet-600 — as duas pontas do gradiente da marca.
COR_PRIMARIA_PADRAO = "#6366f1"
COR_SECUNDARIA_PADRAO = "#7c3aed"
TEMA_PADRAO = "claro"
TEMAS_VALIDOS = ("claro", "escuro")


class ConfiguracaoPersonalizacao(Base):
    """Identidade visual da EMPRESA (logo, cores de marca, tema) — singleton por Empresa, aplicado a
    TODOS os usuários dela. Não existe preferência por usuário.

    Mesmo padrão de `ConfiguracaoEmail`/`RegraExpediente`: a leitura nunca cria a linha (sem linha =
    padrões acima, ver `ConfiguracaoPersonalizacaoService.get_ou_default`); o registro físico só
    nasce na primeira alteração.

    Só duas cores são persistidas. Fundo, superfície, texto, borda, erro etc. NÃO são configuráveis:
    derivam do design system, para que uma cor escolhida nunca quebre o contraste.

    O binário do logo NUNCA fica no banco: `logo_storage_key` é o caminho relativo gerado pelo
    sistema (`personalizacao/<empresa_id>/<uuid>.<ext>`) dentro do volume de uploads.
    """

    __tablename__ = "configuracoes_personalizacao"
    __table_args__ = (
        CheckConstraint("cor_primaria ~ '^#[0-9a-fA-F]{6}$'", name="ck_configuracoes_personalizacao_cor_primaria"),
        CheckConstraint("cor_secundaria ~ '^#[0-9a-fA-F]{6}$'", name="ck_configuracoes_personalizacao_cor_secundaria"),
        CheckConstraint("tema IN ('claro', 'escuro')", name="ck_configuracoes_personalizacao_tema"),
        CheckConstraint(
            "(logo_storage_key IS NULL) = (logo_mime_type IS NULL)",
            name="ck_configuracoes_personalizacao_logo_completo",
        ),
        UniqueConstraint("empresa_id", name="uq_configuracoes_personalizacao_empresa_id"),
        Index("ix_configuracoes_personalizacao_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Sem ondelete: Empresa nunca é apagada fisicamente (mesmo raciocínio de ConfiguracaoEmail).
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    logo_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_mime_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    cor_primaria: Mapped[str] = mapped_column(String(7), nullable=False, default=COR_PRIMARIA_PADRAO)
    cor_secundaria: Mapped[str] = mapped_column(String(7), nullable=False, default=COR_SECUNDARIA_PADRAO)
    tema: Mapped[str] = mapped_column(String(16), nullable=False, default=TEMA_PADRAO)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
