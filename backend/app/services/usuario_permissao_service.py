from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.permissoes import (
    EFEITOS_VALIDOS,
    TODAS_AS_PERMISSOES,
    permissoes_efetivas,
    validar_permissao_existente,
)
from app.models.usuario import Usuario
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository

logger = logging.getLogger(__name__)


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
        para ele **na própria empresa** (o filtro de tenant vive no repository).

        Overrides com `permissao`/`efeito` inválidos são **ignorados e registrados como
        warning**, nunca propagados como exceção (revisão pré-merge, item 16): não existe
        hoje nenhum caminho de escrita que grave uma linha assim (a validação estrita fica em
        `permissoes_efetivas`, para quando 2G.10C criar esse caminho), mas se uma linha
        inválida chegar a existir — intervenção manual no banco, dado de uma versão anterior
        do catálogo — `/auth/me` e `/usuarios/me` não podem quebrar por causa dela: isso
        derrubaria o próprio login de quem precisa corrigir o problema. `permissoes_efetivas`
        continua estrita (levanta `PermissaoInvalidaError`) para quem grava um override novo,
        porque ali o dado ainda não existe e pode ser recusado sem custo."""
        overrides = self.repository.list_by_usuario(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)

        pares: list[tuple[str, str]] = []
        for override in overrides:
            if override.permissao not in TODAS_AS_PERMISSOES or override.efeito not in EFEITOS_VALIDOS:
                logger.warning(
                    "Ignorando usuario_permissao inválido: usuario_id=%s permissao=%r efeito=%r",
                    usuario.id,
                    override.permissao,
                    override.efeito,
                )
                continue
            pares.append((override.permissao, override.efeito))

        efetivas = permissoes_efetivas(usuario.perfil_base, pares)
        return sorted(efetivas)

    def obter_efeito_override(self, db: Session, *, usuario: Usuario, permissao: str) -> str | None:
        """Efeito EXPLÍCITO de um override para uma permissão específica — `"conceder"`,
        `"negar"` ou `None` se não houver override para essa chave nesta empresa.

        Nenhuma lógica de default aqui — quem quer o conjunto efetivo completo (default do
        perfil + overrides) usa `obter_permissoes_efetivas`. Este método existe para helpers
        que precisam decidir algo ANTES/INDEPENDENTE do default, tipicamente quando a
        autorização também pode vir de uma relação (não só de perfil/override) e um `negar`
        explícito precisa continuar valendo mesmo assim — hoje só
        `require_demandas_criar()` (Fase 2G.10B, D1.1): Head/Atendimento são autorizados por
        relação, não por perfil, então "ausente do conjunto efetivo" não distingue "nunca teve
        override" de "foi negado explicitamente" — só a linha crua resolve essa ambiguidade.

        Reaproveita a MESMA consulta de `obter_permissoes_efetivas` (`list_by_usuario`) — não
        introduz um segundo caminho de leitura à tabela.
        """
        validar_permissao_existente(permissao)
        overrides = self.repository.list_by_usuario(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)
        for override in overrides:
            if override.permissao != permissao:
                continue
            if override.efeito not in EFEITOS_VALIDOS:
                logger.warning(
                    "Ignorando usuario_permissao inválido: usuario_id=%s permissao=%r efeito=%r",
                    usuario.id,
                    override.permissao,
                    override.efeito,
                )
                return None
            return override.efeito
        return None
