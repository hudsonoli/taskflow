from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_permissao import UsuarioPermissao


class UsuarioPermissaoRepository:
    """Só leitura nesta fase (2G.10A) — não existe ainda nenhum caminho de escrita (isso é
    trabalho da Fase 2G.10C, quando houver endpoint de administrador para conceder/negar).
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
