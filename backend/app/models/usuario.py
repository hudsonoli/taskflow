from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "perfil_base IN ('admin', 'gestor', 'operador')",
            name="ck_usuarios_perfil_base",
        ),
        CheckConstraint(
            "status IN ('ativo', 'inativo', 'bloqueado', 'arquivado')",
            name="ck_usuarios_status",
        ),
        CheckConstraint(
            "(foto_perfil_storage_key IS NULL) = (foto_perfil_mime_type IS NULL)",
            name="ck_usuarios_foto_perfil_par",
        ),
        CheckConstraint(
            "tema_preferencia IS NULL OR tema_preferencia IN ('claro', 'escuro', 'sistema')",
            name="ck_usuarios_tema_preferencia",
        ),
        UniqueConstraint("empresa_id", "codigo_interno", name="uq_usuarios_empresa_codigo_interno"),
        UniqueConstraint("empresa_id", "email", name="uq_usuarios_empresa_email"),
        # Global, não por empresa: um `sub` do Google é único no mundo — ver migration 0035.
        UniqueConstraint("google_sub", name="uq_usuarios_google_sub"),
        Index("ix_usuarios_empresa_id", "empresa_id"),
        Index("ix_usuarios_status", "status"),
        Index("ix_usuarios_perfil_base", "perfil_base"),
        Index("ix_usuarios_created_at", "created_at"),
        Index("ix_usuarios_is_system_account", "is_system_account"),
        Index("ix_usuarios_departamento_id", "departamento_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    codigo_interno: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil_base: Mapped[str] = mapped_column(String(32), nullable=False)
    acesso_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Perfil rico (portado do cadastro mock — ver frontend/src/types/usuario.ts).
    telefone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    cep: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco_completo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    # Lista de {id, nome, email, telefone, relacao}.
    contatos: Mapped[list[dict[str, Any]] | None] = mapped_column(json_type, nullable=True)
    # Nullable de propósito (usuário sem departamento é legítimo) e SET NULL em vez de
    # cascade — apagar um departamento nunca pode apagar usuário.
    departamento_id: Mapped[str | None] = mapped_column(
        ForeignKey("departamentos.id", ondelete="SET NULL"), nullable=True
    )
    cargo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lider_departamento: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    valor_recebido_mensal_centavos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horas_trabalho_aproximadas: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cor_identificacao: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Conta de sistema (bootstrap/recuperação) — nunca aceita via API pública, ver
    # UsuarioRepository.list()/list_diretorio()/get_by_id (admin) e UsuarioService, que a
    # excluem/protegem incondicionalmente. Não concede privilégio extra além de perfil_base
    # (sempre "admin" nesta conta) — é só proteção de visibilidade/imutabilidade.
    is_system_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inativado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inativado_por_usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    motivo_inativacao: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Arquivamento (soft-delete permanente) — ver docs/padrao-arquivamento.md. Campos
    # representam só o último ciclo de arquivar/restaurar; histórico completo de ciclos
    # anteriores fica nos eventos de domínio, não no registro. arquivado_por_usuario_id e
    # restaurado_por_usuario_id são String(36) (não sqlalchemy.Uuid) porque usuarios.id já é
    # String(36) — um tipo físico diferente pro mesmo identificador seria incompatível. Sem
    # ForeignKey: são campos de auditoria soltos, não uma relação obrigatória.
    arquivado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arquivado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo_arquivamento: Mapped[str | None] = mapped_column(String(500), nullable=True)
    restaurado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restaurado_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status_anterior_arquivamento: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Login Google Workspace — vínculo com identidade pré-cadastrada (ver AuthService.login_google).
    # Nenhum destes campos é aceito via UsuarioCreate/UsuarioUpdate nem participa de RBAC: são
    # auxiliares, preenchidos somente pelo próprio fluxo de login Google. `google_sub` é a
    # chave estável de logins seguintes (não o e-mail, que pode mudar depois do vínculo).
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_google_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    google_given_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_family_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_locale: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Preferência PESSOAL de tema (claro | escuro | sistema). NULL = "usar o padrão da empresa"
    # (configuracoes_personalizacao.tema) — é o estado de todo usuário existente. Só o próprio usuário
    # altera (PATCH /usuarios/me/preferencias); logo e cores continuam globais por empresa.
    tema_preferencia: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Foto de perfil enviada pelo próprio usuário (PNG/JPEG validado pelos bytes). Só a referência fica
    # aqui; o arquivo mora no volume de uploads, em usuarios/<empresa>/<usuario>/<nome gerado>. `foto_url`
    # (acima) segue existindo para a foto externa do Google e para o cadastro administrativo.
    foto_perfil_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    foto_perfil_mime_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
