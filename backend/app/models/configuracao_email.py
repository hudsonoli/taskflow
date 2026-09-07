from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConfiguracaoEmail(Base):
    """Configuração de disparo SMTP da Empresa (Fase 2G.7B1) — singleton: uma linha por
    Empresa, mesmo padrão de `RegraExpediente` (ver app/models/regra_expediente.py).

    Diferente de `RegraExpediente`, o `GET` desta configuração é read-only: nenhuma leitura
    administrativa cria a linha (ver `ConfiguracaoEmailService.get_ou_default`) — o registro
    físico só nasce no primeiro `PATCH`. Isso evita que uma tela de configurações nunca
    visitada gere uma linha "vazia" por Empresa só por ter sido aberta.

    ## `smtp_senha_criptografada` é campo interno

    Guarda só o ciphertext Fernet do segredo SMTP — NUNCA texto puro, nunca hash irreversível.
    Nenhum schema de resposta de API deve incluir esta coluna nem ler este model diretamente
    como shape de resposta; toda serialização passa por `ConfiguracaoEmailRead`, que expõe só
    `smtpSenhaConfigurada: bool`. Criptografia/descriptografia é responsabilidade exclusiva de
    `ConfiguracaoEmailCryptoService` — este model nunca importa Fernet nem conhece a chave
    mestra (`EMAIL_CONFIG_ENCRYPTION_KEY`, variável de ambiente, nunca persistida).

    ## V1 é SMTP manual apenas

    Sem OAuth (Google/M365), sem envio real de e-mail ainda — isso é a próxima subfase
    (2G.7B2/C). Este model só persiste o que a configuração precisa guardar.
    """

    __tablename__ = "configuracoes_email"
    __table_args__ = (
        CheckConstraint(
            "smtp_port IS NULL OR (smtp_port >= 1 AND smtp_port <= 65535)",
            name="ck_configuracoes_email_smtp_port",
        ),
        CheckConstraint(
            "smtp_host IS NULL OR trim(smtp_host) <> ''",
            name="ck_configuracoes_email_smtp_host",
        ),
        CheckConstraint(
            "remetente_email IS NULL OR trim(remetente_email) <> ''",
            name="ck_configuracoes_email_remetente_email",
        ),
        # TLS explícito (STARTTLS) e SSL implícito são mecanismos de negociação mutuamente
        # exclusivos no mesmo socket — nunca os dois ativos ao mesmo tempo (ver Fase 2G.7A,
        # item 8). Ambos False = conexão sem criptografia (aceitável em relay interno).
        CheckConstraint("NOT (usar_tls AND usar_ssl)", name="ck_configuracoes_email_tls_ssl_exclusivos"),
        UniqueConstraint("empresa_id", name="uq_configuracoes_email_empresa_id"),
        Index("ix_configuracoes_email_empresa_id", "empresa_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Sem ondelete: Empresa nunca é apagada fisicamente (mesmo raciocínio de SlaRegra sobre
    # cliente_id/departamento_id — ver docstring de app/models/sla_regra.py).
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_usuario: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_senha_criptografada: Mapped[str | None] = mapped_column(Text, nullable=True)

    remetente_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remetente_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usar_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    usar_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
