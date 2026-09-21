from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissoes import (
    DEFAULTS_POR_PERFIL,
    EFEITO_CONCEDER,
    EFEITOS_VALIDOS,
    LABELS_PERMISSOES,
    TODAS_AS_PERMISSOES,
    permissoes_efetivas,
    validar_permissao_existente,
)
from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository
from app.schemas.usuario_permissao import PermissaoAdminItem
from app.services.domain_event_publisher import DomainEventPublisher

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

    def __init__(
        self,
        repository: UsuarioPermissaoRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioPermissaoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

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

    def montar_visao_administrativa(self, db: Session, usuario: Usuario) -> list[PermissaoAdminItem]:
        """Visão completa (Fase 2G.10C-C1, GET /usuarios/{id}/permissoes) — uma linha por
        chave em `TODAS_AS_PERMISSOES`, não só as que têm override, para a tela mostrar
        "Herdado" nas demais. Reaproveita a MESMA leitura/validação de
        `obter_permissoes_efetivas` (linha inválida vira warning + é ignorada, nunca derruba
        a tela) e o mesmo resolver puro (`permissoes_efetivas`) — nenhuma regra de
        precedência nova, só uma projeção do que já existe."""
        overrides = self.repository.list_by_usuario(db, empresa_id=usuario.empresa_id, usuario_id=usuario.id)

        override_por_permissao: dict[str, str] = {}
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
            override_por_permissao[override.permissao] = override.efeito
            pares.append((override.permissao, override.efeito))

        efetivas = permissoes_efetivas(usuario.perfil_base, pares)
        herdadas = DEFAULTS_POR_PERFIL[usuario.perfil_base]

        itens = [
            PermissaoAdminItem(
                permissao=permissao,
                modulo=permissao.split(".", 1)[0],
                label=LABELS_PERMISSOES[permissao],
                herdado=permissao in herdadas,
                override=override_por_permissao.get(permissao),
                efetivo=permissao in efetivas,
            )
            for permissao in TODAS_AS_PERMISSOES
        ]
        itens.sort(key=lambda item: (item.modulo, item.label, item.permissao))
        return itens

    def definir_override(
        self,
        db: Session,
        *,
        usuario: Usuario,
        permissao: str,
        efeito: str,
        motivo: str | None,
        concedido_por_usuario_id: str,
    ) -> UsuarioPermissao:
        """Upsert por `(usuario_id, permissao)` — cria a exceção se não existir, atualiza
        `efeito`/`motivo`/`concedido_por_usuario_id` se já existir (conceder→negar e
        negar→conceder passam pelo mesmo caminho, sem apagar e recriar a linha). Publica
        evento e commita na MESMA transação — sem commit intermediário, mesmo padrão de
        `UsuarioService.create_usuario`."""
        validar_permissao_existente(permissao)
        now = datetime.now(timezone.utc)

        try:
            existente = self.repository.get_by_usuario_e_permissao(
                db, empresa_id=usuario.empresa_id, usuario_id=usuario.id, permissao=permissao
            )
            if existente is not None:
                existente.efeito = efeito
                existente.motivo = motivo
                existente.concedido_por_usuario_id = concedido_por_usuario_id
                existente.updated_at = now
                override = self.repository.upsert(db, existente)
            else:
                override = self.repository.upsert(
                    db,
                    UsuarioPermissao(
                        id=str(uuid4()),
                        empresa_id=usuario.empresa_id,
                        usuario_id=usuario.id,
                        permissao=permissao,
                        efeito=efeito,
                        motivo=motivo,
                        concedido_por_usuario_id=concedido_por_usuario_id,
                        created_at=now,
                        updated_at=now,
                    ),
                )

            tipo = (
                DomainEventType.USUARIO_PERMISSAO_CONCEDIDA
                if efeito == EFEITO_CONCEDER
                else DomainEventType.USUARIO_PERMISSAO_NEGADA
            )
            self._publish_permissao_event(
                db, usuario, tipo, concedido_por_usuario_id, permissao=permissao, efeito=efeito, occurred_at=now
            )
            db.commit()
            db.refresh(override)
            return override
        except IntegrityError:
            # Corrida: duas escritas concorrentes na mesma chave (usuario_id, permissao) —
            # o SELECT acima não viu a linha que a outra transação acabou de commitar.
            db.rollback()
            existente = self.repository.get_by_usuario_e_permissao(
                db, empresa_id=usuario.empresa_id, usuario_id=usuario.id, permissao=permissao
            )
            if existente is None:
                raise
            existente.efeito = efeito
            existente.motivo = motivo
            existente.concedido_por_usuario_id = concedido_por_usuario_id
            existente.updated_at = datetime.now(timezone.utc)
            override = self.repository.upsert(db, existente)
            tipo = (
                DomainEventType.USUARIO_PERMISSAO_CONCEDIDA
                if efeito == EFEITO_CONCEDER
                else DomainEventType.USUARIO_PERMISSAO_NEGADA
            )
            self._publish_permissao_event(
                db, usuario, tipo, concedido_por_usuario_id, permissao=permissao, efeito=efeito,
                occurred_at=existente.updated_at,
            )
            db.commit()
            db.refresh(override)
            return override
        except Exception:
            db.rollback()
            raise

    def remover_override(
        self,
        db: Session,
        *,
        usuario: Usuario,
        permissao: str,
        actor_usuario_id: str,
    ) -> bool:
        """"Herdar" = DELETE da linha — nunca um terceiro valor de `efeito` (o CHECK do
        banco já impede isso). Idempotente: se não existir override, não é erro — devolve
        `False` sem publicar evento (nunca um evento descrevendo algo que não aconteceu)."""
        validar_permissao_existente(permissao)
        try:
            existente = self.repository.get_by_usuario_e_permissao(
                db, empresa_id=usuario.empresa_id, usuario_id=usuario.id, permissao=permissao
            )
            if existente is None:
                return False

            self.repository.delete(db, existente)
            self._publish_permissao_event(
                db,
                usuario,
                DomainEventType.USUARIO_PERMISSAO_REMOVIDA,
                actor_usuario_id,
                permissao=permissao,
                efeito=None,
                occurred_at=datetime.now(timezone.utc),
            )
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise

    def _publish_permissao_event(
        self,
        db: Session,
        usuario: Usuario,
        tipo: DomainEventType,
        actor_usuario_id: str,
        *,
        permissao: str,
        efeito: str | None,
        occurred_at: datetime,
    ) -> None:
        payload: dict[str, str] = {
            "empresa_id": usuario.empresa_id,
            "usuario_id": usuario.id,
            "permissao": permissao,
            "concedido_por_usuario_id": actor_usuario_id,
        }
        if efeito is not None:
            payload["efeito"] = efeito

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=usuario.empresa_id,
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )
