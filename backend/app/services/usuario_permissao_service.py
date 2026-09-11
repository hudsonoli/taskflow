from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.permissoes import permissoes_efetivas
from app.models.usuario import Usuario
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository


class UsuarioPermissaoService:
    """Fundação de permissões (Fase 2G.10A) — carrega as exceções de um usuário e calcula o
    conjunto efetivo. **Não decide autorização de nenhuma rota ainda**: o resultado desta
    classe não é consultado por nenhum guard hoje, só exposto em `/auth/me` e `/usuarios/me`
    para o frontend passar a ter a informação disponível antes de a Fase 2G.10B migrar
    enforcement de verdade.

    Nunca vira uma "engine" — a única responsabilidade daqui pra frente continua sendo:
    carregar overrides do tenant certo, e delegar o cálculo para a função pura
    `permissoes_efetivas` (app/core/permissoes.py).
    """

    def __init__(self, repository: UsuarioPermissaoRepository | None = None) -> None:
        self.repository = repository or UsuarioPermissaoRepository()

    def obter_permissoes_efetivas(self, db: Session, usuario: Usuario) -> list[str]:
        """Lista ordenada (determinística — ver Fase 2G.10A item 14) das permissões efetivas
        de `usuario`, considerando o default do `perfil_base` dele e as exceções gravadas
        para ele **na própria empresa** (o filtro de tenant vive no repository)."""
        overrides = self.repository.list_by_usuario(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
        pares = [(override.permissao, override.efeito) for override in overrides]
        efetivas = permissoes_efetivas(usuario.perfil_base, pares)
        return sorted(efetivas)
