from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsuarioPermissao(Base):
    """Exceção individual de permissão (Fase 2G.10A) — fundação, ainda sem nenhum endpoint de
    escrita nem uso em enforcement. Uma linha = uma permissão concedida ou negada para UM
    usuário, por cima do default do perfil (ver `app/core/permissoes.py`).

    `UNIQUE(usuario_id, permissao)` é o que garante que não existe ambiguidade entre
    "conceder" e "negar" para a mesma pessoa+permissão — a resolução (`permissoes_efetivas`)
    não precisa desempatar overrides entre si, só overrides contra o default.

    Sem cascade de exclusão: usuário nunca é DELETE físico (arquivamento — ver
    docs/padrao-arquivamento.md), então a FK de `usuario_id` nunca precisa lidar com remoção.
    `concedido_por_usuario_id` é auditoria solta (String(36) sem FK), mesmo padrão de
    `arquivado_por_usuario_id` nos demais cadastros — quem concedeu pode ter sido
    arquivado/removido depois, e isso não pode quebrar a leitura do override.
    """

    __tablename__ = "usuario_permissao"
    __table_args__ = (
        CheckConstraint("efeito IN ('conceder', 'negar')", name="ck_usuario_permissao_efeito"),
        UniqueConstraint("usuario_id", "permissao", name="uq_usuario_permissao_usuario_permissao"),
        # Dois índices separados, não um composto: são duas formas de consulta distintas.
        # `usuario_id` sozinho é a query real desta fase (resolver as exceções de UMA
        # pessoa — UsuarioPermissaoRepository.list_by_usuario). `empresa_id` sozinho é para a
        # futura tela administrativa (Fase 2G.10E, "todas as exceções desta empresa") — ainda
        # não existe essa consulta, mas a coluna já é NOT NULL e filtrada por tenant em toda
        # leitura, então o índice já vale a pena. Um composto (empresa_id, usuario_id) serviria
        # pior a query de hoje, que não filtra por empresa_id.
        Index("ix_usuario_permissao_empresa_id", "empresa_id"),
        Index("ix_usuario_permissao_usuario_id", "usuario_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Nunca aceito do cliente — sempre derivado do usuário-alvo/tenant da sessão atual. Ver
    # app/core/permissoes.py e UsuarioPermissaoService.
    empresa_id: Mapped[str] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    # Chave do catálogo (`app/core/permissoes.py::TODAS_AS_PERMISSOES`) — validada na
    # aplicação, não em CHECK de banco: o catálogo evolui junto do código, um CHECK/enum SQL
    # exigiria migration toda vez que uma permissão nova nascesse.
    permissao: Mapped[str] = mapped_column(String(80), nullable=False)
    efeito: Mapped[str] = mapped_column(String(10), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    concedido_por_usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
