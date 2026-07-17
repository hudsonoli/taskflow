from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.usuario_equipe import UsuarioEquipe
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.equipe_repository import EquipeRepository
from app.repositories.usuario_equipe_repository import UsuarioEquipeRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario_equipe import (
    UsuarioEquipeCreate,
    UsuarioEquipeEncerrar,
    UsuarioEquipeResponse,
    UsuarioEquipeUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ATIVA as EMPRESA_STATUS_ATIVA
from app.services.equipe_service import STATUS_ATIVA as EQUIPE_STATUS_ATIVA
from app.services.usuario_service import STATUS_ATIVO as USUARIO_STATUS_ATIVO

STATUS_ATIVO = "ativo"
STATUS_ENCERRADO = "encerrado"
PAPEL_LIDER = "lider"


class UsuarioEquipeNotFoundError(ValueError):
    pass


class UsuarioEquipeConflictError(ValueError):
    pass


class UsuarioEquipeInvalidDataError(ValueError):
    pass


class UsuarioEquipeInvalidTransitionError(ValueError):
    pass


class UsuarioEquipeService:
    def __init__(
        self,
        repository: UsuarioEquipeRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        equipe_repository: EquipeRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioEquipeRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.equipe_repository = equipe_repository or EquipeRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def vincular_usuario_equipe(
        self,
        db: Session,
        data: UsuarioEquipeCreate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioEquipe:
        empresa_id = str(data.empresa_id)
        usuario_id = str(data.usuario_id)
        equipe_id = str(data.equipe_id)
        now = datetime.now(timezone.utc)
        vinculo = UsuarioEquipe(
            id=str(uuid4()),
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            equipe_id=equipe_id,
            papel=data.papel,
            principal=data.principal,
            status=STATUS_ATIVO,
            inicio_em=now,
            fim_em=None,
            motivo_encerramento=None,
            criado_por_usuario_id=actor_usuario_id,
            encerrado_por_usuario_id=None,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_payload_entities_active(db, empresa_id, usuario_id, equipe_id)
            self._ensure_no_active_duplicate(db, empresa_id, usuario_id, equipe_id)
            self._ensure_lider_available(db, empresa_id, equipe_id, vinculo.papel)
            previous_principal = None
            if vinculo.principal:
                previous_principal = self.repository.get_active_principal_by_usuario(
                    db,
                    empresa_id=empresa_id,
                    usuario_id=usuario_id,
                )
                if previous_principal is not None:
                    previous_principal.principal = False
                    previous_principal.updated_at = now
                    self.repository.update(db, previous_principal)

            self.repository.create(db, vinculo)

            if previous_principal is not None:
                self._publish_event(
                    db,
                    previous_principal,
                    DomainEventType.USUARIO_EQUIPE_ALTERADO,
                    actor_usuario_id,
                    campos_alterados=["principal"],
                    occurred_at=now,
                )
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_EQUIPE_VINCULADO,
                actor_usuario_id,
                campos_alterados=[],
                occurred_at=now,
            )
            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def listar_vinculos(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_id: str | None = None,
        equipe_id: str | None = None,
        papel: str | None = None,
        status: str | None = None,
        principal: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UsuarioEquipe]:
        self._ensure_filter_entities_active_and_belong_to_empresa(db, empresa_id, usuario_id, equipe_id)
        return self.repository.list_by_empresa(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            equipe_id=equipe_id,
            papel=papel,
            status=status,
            principal=principal,
            limit=limit,
            offset=offset,
        )

    def obter_vinculo(self, db: Session, vinculo_id: str) -> UsuarioEquipe:
        vinculo = self.repository.get_by_id(db, vinculo_id)
        if vinculo is None:
            raise UsuarioEquipeNotFoundError("Vínculo não encontrado")
        return vinculo

    def alterar_vinculo(
        self,
        db: Session,
        vinculo_id: str,
        data: UsuarioEquipeUpdate,
        *,
        actor_usuario_id: str,
    ) -> UsuarioEquipe:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioEquipeInvalidTransitionError("Vínculo encerrado não pode ser alterado")

            updates = data.model_dump(exclude_unset=True, by_alias=False)
            changed_fields: list[str] = []
            now = datetime.now(timezone.utc)
            previous_principal = None

            if "papel" in updates and updates["papel"] != vinculo.papel:
                self._ensure_lider_available(
                    db,
                    vinculo.empresa_id,
                    vinculo.equipe_id,
                    updates["papel"],
                    exclude_id=vinculo.id,
                )
                vinculo.papel = updates["papel"]
                changed_fields.append("papel")

            if "principal" in updates and updates["principal"] != vinculo.principal:
                if updates["principal"] is True:
                    previous_principal = self.repository.get_active_principal_by_usuario(
                        db,
                        empresa_id=vinculo.empresa_id,
                        usuario_id=vinculo.usuario_id,
                    )
                    if previous_principal is not None and previous_principal.id != vinculo.id:
                        previous_principal.principal = False
                        previous_principal.updated_at = now
                        self.repository.update(db, previous_principal)
                vinculo.principal = updates["principal"]
                changed_fields.append("principal")

            if changed_fields:
                vinculo.updated_at = now
                self.repository.update(db, vinculo)
                if previous_principal is not None and previous_principal.id != vinculo.id:
                    self._publish_event(
                        db,
                        previous_principal,
                        DomainEventType.USUARIO_EQUIPE_ALTERADO,
                        actor_usuario_id,
                        campos_alterados=["principal"],
                        occurred_at=now,
                    )
                self._publish_event(
                    db,
                    vinculo,
                    DomainEventType.USUARIO_EQUIPE_ALTERADO,
                    actor_usuario_id,
                    campos_alterados=changed_fields,
                    occurred_at=now,
                )

            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def encerrar_vinculo(
        self,
        db: Session,
        vinculo_id: str,
        data: UsuarioEquipeEncerrar,
        *,
        actor_usuario_id: str,
    ) -> UsuarioEquipe:
        try:
            vinculo = self.obter_vinculo(db, vinculo_id)
            if vinculo.status != STATUS_ATIVO:
                raise UsuarioEquipeInvalidTransitionError("Vínculo já está encerrado")

            now = datetime.now(timezone.utc)
            fim_em = now
            if fim_em < self._as_utc(vinculo.inicio_em):
                fim_em = self._as_utc(vinculo.inicio_em)

            vinculo.status = STATUS_ENCERRADO
            vinculo.fim_em = fim_em
            vinculo.motivo_encerramento = self._normalize_motivo(data.motivo_encerramento)
            vinculo.principal = False
            vinculo.encerrado_por_usuario_id = actor_usuario_id
            vinculo.updated_at = now
            self.repository.encerrar(db, vinculo)
            self._publish_event(
                db,
                vinculo,
                DomainEventType.USUARIO_EQUIPE_ENCERRADO,
                actor_usuario_id,
                campos_alterados=["status", "fim_em", "principal", "encerrado_por_usuario_id"],
                occurred_at=now,
            )
            db.commit()
            db.refresh(vinculo)
            return vinculo
        except Exception:
            db.rollback()
            raise

    def to_response(self, vinculo: UsuarioEquipe) -> UsuarioEquipeResponse:
        return UsuarioEquipeResponse(
            id=vinculo.id,
            empresaId=vinculo.empresa_id,
            usuarioId=vinculo.usuario_id,
            equipeId=vinculo.equipe_id,
            papel=vinculo.papel,
            principal=vinculo.principal,
            status=vinculo.status,
            inicioEm=vinculo.inicio_em,
            fimEm=vinculo.fim_em,
            motivoEncerramento=vinculo.motivo_encerramento,
            criadoPorUsuarioId=vinculo.criado_por_usuario_id,
            encerradoPorUsuarioId=vinculo.encerrado_por_usuario_id,
            createdAt=vinculo.created_at,
            updatedAt=vinculo.updated_at,
        )

    def _ensure_payload_entities_active(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str,
        equipe_id: str,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioEquipeInvalidDataError("Empresa não encontrada ou inativa")

        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id or usuario.status != USUARIO_STATUS_ATIVO:
            raise UsuarioEquipeInvalidDataError("Usuário não encontrado ou inativo")

        equipe = self.equipe_repository.get_by_id(db, equipe_id)
        if equipe is None or equipe.empresa_id != empresa_id or equipe.status != EQUIPE_STATUS_ATIVA:
            raise UsuarioEquipeInvalidDataError("Equipe não encontrada ou inativa")

    def _ensure_filter_entities_active_and_belong_to_empresa(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str | None,
        equipe_id: str | None,
    ) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None or empresa.status != EMPRESA_STATUS_ATIVA:
            raise UsuarioEquipeInvalidDataError("Empresa não encontrada ou inativa")

        if usuario_id is not None:
            usuario = self.usuario_repository.get_by_id(db, usuario_id)
            if usuario is None or usuario.empresa_id != empresa_id or usuario.status != USUARIO_STATUS_ATIVO:
                raise UsuarioEquipeInvalidDataError("Usuário não encontrado ou inativo")

        if equipe_id is not None:
            equipe = self.equipe_repository.get_by_id(db, equipe_id)
            if equipe is None or equipe.empresa_id != empresa_id or equipe.status != EQUIPE_STATUS_ATIVA:
                raise UsuarioEquipeInvalidDataError("Equipe não encontrada ou inativa")

    def _ensure_no_active_duplicate(
        self,
        db: Session,
        empresa_id: str,
        usuario_id: str,
        equipe_id: str,
    ) -> None:
        existing = self.repository.get_active_by_usuario_equipe(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            equipe_id=equipe_id,
        )
        if existing is not None:
            raise UsuarioEquipeConflictError("Vínculo ativo já existe para Usuário e Equipe")

    def _ensure_lider_available(
        self,
        db: Session,
        empresa_id: str,
        equipe_id: str,
        papel: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        if papel != PAPEL_LIDER:
            return
        existing = self.repository.get_active_lider_by_equipe(
            db,
            empresa_id=empresa_id,
            equipe_id=equipe_id,
        )
        if existing is not None and existing.id != exclude_id:
            raise UsuarioEquipeConflictError("Equipe já possui líder ativo")

    def _publish_event(
        self,
        db: Session,
        vinculo: UsuarioEquipe,
        tipo: DomainEventType,
        actor_usuario_id: str,
        *,
        campos_alterados: list[str],
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": vinculo.empresa_id,
            "usuario_equipe_id": vinculo.id,
            "usuario_id": vinculo.usuario_id,
            "equipe_id": vinculo.equipe_id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
            "campos_alterados": campos_alterados,
        }

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=vinculo.empresa_id,
            entidade_tipo="usuario_equipe",
            entidade_id=vinculo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_motivo(motivo: str | None) -> str | None:
        if motivo is None:
            return None
        normalized = " ".join(motivo.strip().split())
        return normalized or None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
