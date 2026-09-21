from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_permissao import UsuarioPermissao


class UsuarioPermissaoRepository:
    """Leitura desde a Fase 2G.10A; escrita (upsert/delete) desde a Fase 2G.10C-C1 — ver
    app/services/usuario_permissao_service.py para quem chama e app/api/routes/
    usuario_permissao.py para o endpoint administrativo por trás.
    """

    def list_by_usuario(self, db: Session, *, empresa_id: str, usuario_id: str) -> list[UsuarioPermissao]:
        """As exceções de UM usuário. Filtra por `usuario_id` (a consulta real) e também por
        `empresa_id` (defesa em profundidade contra cruzar tenant, mesmo que `usuario_id`
        já implique a empresa por construção — mesmo princípio de `ensure_resource_empresa`
        em app/dependencies/authorization.py: nunca confiar em um único sinal de tenant)."""
        statement = select(UsuarioPermissao).where(
            UsuarioPermissao.usuario_id == usuario_id,
            UsuarioPermissao.empresa_id == empresa_id,
        )
        return list(db.scalars(statement).all())

    def get_by_usuario_e_permissao(
        self, db: Session, *, empresa_id: str, usuario_id: str, permissao: str
    ) -> UsuarioPermissao | None:
        """Uma linha específica — usada pelo PUT/DELETE administrativos. Mesma defesa em
        profundidade de `list_by_usuario`: filtra por `empresa_id` E `usuario_id`, nunca só
        um dos dois."""
        statement = select(UsuarioPermissao).where(
            UsuarioPermissao.usuario_id == usuario_id,
            UsuarioPermissao.empresa_id == empresa_id,
            UsuarioPermissao.permissao == permissao,
        )
        return db.scalars(statement).first()

    def upsert(self, db: Session, override: UsuarioPermissao) -> UsuarioPermissao:
        """`db.add` cobre os dois casos: `override` novo (sem `id` já persistido) vira
        INSERT; `override` obtido de `get_by_usuario_e_permissao` e mutado pelo service vira
        UPDATE (SQLAlchemy já rastreia a instância). Sem commit aqui — mesmo padrão de
        `UsuarioRepository.create`/`.update`: quem commita é o service, na mesma transação
        do evento de domínio."""
        db.add(override)
        db.flush()
        return override

    def delete(self, db: Session, override: UsuarioPermissao) -> None:
        db.delete(override)
        db.flush()
