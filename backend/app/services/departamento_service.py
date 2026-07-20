from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.repositories.usuario_departamento_repository import UsuarioDepartamentoRepository
from app.schemas.departamento import DepartamentoCreate, DepartamentoResponse, DepartamentoUpdate
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA

STATUS_ATIVA = "ativa"
STATUS_INATIVA = "inativa"
STATUS_ARQUIVADA = "arquivada"


class DepartamentoNotFoundError(ValueError):
    pass


class DepartamentoConflictError(ValueError):
    pass


class DepartamentoInvalidTransitionError(ValueError):
    pass


class DepartamentoInvalidEmpresaError(ValueError):
    pass


class DepartamentoInvalidDataError(ValueError):
    pass


class DepartamentoService:
    def __init__(
        self,
        repository: DepartamentoRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
        usuario_departamento_repository: UsuarioDepartamentoRepository | None = None,
        sessao_trabalho_repository: SessaoTrabalhoRepository | None = None,
    ) -> None:
        self.repository = repository or DepartamentoRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.usuario_departamento_repository = usuario_departamento_repository or UsuarioDepartamentoRepository()
        self.sessao_trabalho_repository = sessao_trabalho_repository or SessaoTrabalhoRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def create_departamento(
        self,
        db: Session,
        data: DepartamentoCreate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Departamento:
        empresa_id = str(data.empresa_id)
        codigo_interno = self._normalize_codigo_interno(data.codigo_interno)
        nome = self._normalize_nome(data.nome)
        descricao = self._normalize_descricao(data.descricao)
        self._ensure_required("codigoInterno", codigo_interno)
        self._ensure_required("nome", nome)
        now = datetime.now(timezone.utc)
        departamento = Departamento(
            id=str(uuid4()),
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            nome=nome,
            descricao=descricao,
            status=STATUS_ATIVA,
            created_at=now,
            updated_at=now,
            inativado_at=None,
            motivo_inativacao=None,
            inativado_por_usuario_id=None,
        )

        try:
            self._ensure_empresa_accepts_departamento(db, empresa_id)
            self._ensure_codigo_interno_available(db, empresa_id, departamento.codigo_interno)
            self._ensure_nome_available(db, empresa_id, departamento.nome)
            self.repository.create(db, departamento)
            self._publish_event(db, departamento, DomainEventType.DEPARTAMENTO_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    def list_departamentos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Departamento]:
        return self.repository.list(db, empresa_id=empresa_id, status=status, busca=busca, limit=limit, offset=offset)

    def get_departamento(self, db: Session, departamento_id: str) -> Departamento:
        departamento = self.repository.get_by_id(db, departamento_id)
        if departamento is None:
            raise DepartamentoNotFoundError("Departamento não encontrado")
        return departamento

    def update_departamento(
        self,
        db: Session,
        departamento_id: str,
        data: DepartamentoUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Departamento:
        try:
            departamento = self.get_departamento(db, departamento_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "codigo_interno" in updates:
                codigo_interno = self._normalize_codigo_interno(updates["codigo_interno"])
                self._ensure_required("codigoInterno", codigo_interno)
                if codigo_interno != departamento.codigo_interno:
                    self._ensure_codigo_interno_available(
                        db,
                        departamento.empresa_id,
                        codigo_interno,
                        exclude_id=departamento.id,
                    )
                    departamento.codigo_interno = codigo_interno
                    changed_fields.append("codigoInterno")

            if "nome" in updates:
                nome = self._normalize_nome(updates["nome"])
                self._ensure_required("nome", nome)
                if nome != departamento.nome:
                    self._ensure_nome_available(db, departamento.empresa_id, nome, exclude_id=departamento.id)
                    departamento.nome = nome
                    changed_fields.append("nome")

            if "descricao" in updates:
                descricao = self._normalize_descricao(updates["descricao"])
                if descricao != departamento.descricao:
                    departamento.descricao = descricao
                    changed_fields.append("descricao")

            if changed_fields:
                now = datetime.now(timezone.utc)
                departamento.updated_at = now
                self.repository.update(db, departamento)
                self._publish_event(
                    db,
                    departamento,
                    DomainEventType.DEPARTAMENTO_ALTERADO,
                    actor_usuario_id,
                    occurred_at=now,
                    campos_alterados=changed_fields,
                )

            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    def inativar_departamento(
        self,
        db: Session,
        departamento_id: str,
        *,
        motivo_inativacao: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Departamento:
        try:
            departamento = self.get_departamento(db, departamento_id)
            if departamento.status == STATUS_INATIVA:
                raise DepartamentoInvalidTransitionError("Departamento já está inativo")
            if departamento.status == STATUS_ARQUIVADA:
                raise DepartamentoInvalidTransitionError("Departamento arquivado não pode ser inativado")

            # Equipe ainda não possui departamento_id; a validação de Equipes ativas pertence à TF-ORG-002.3.
            vinculos_ativos = self.usuario_departamento_repository.list_by_departamento(
                db,
                empresa_id=departamento.empresa_id,
                departamento_id=departamento.id,
                status="ativo",
            )
            if vinculos_ativos:
                raise DepartamentoConflictError("Departamento possui vínculos ativos de Usuários")

            sessoes_ativas = self.sessao_trabalho_repository.list(
                db,
                empresa_id=departamento.empresa_id,
                departamento_id=departamento.id,
                status="ativa",
                limit=1,
            )
            if sessoes_ativas:
                raise DepartamentoConflictError("Departamento possui sessões de trabalho ativas")

            now = datetime.now(timezone.utc)
            departamento.status = STATUS_INATIVA
            departamento.updated_at = now
            departamento.inativado_at = now
            departamento.motivo_inativacao = self._normalize_descricao(motivo_inativacao)
            departamento.inativado_por_usuario_id = actor_usuario_id
            self.repository.update(db, departamento)
            self._publish_event(db, departamento, DomainEventType.DEPARTAMENTO_INATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    def reativar_departamento(
        self,
        db: Session,
        departamento_id: str,
        *,
        actor_usuario_id: str | None = None,
    ) -> Departamento:
        try:
            departamento = self.get_departamento(db, departamento_id)
            if departamento.status == STATUS_ATIVA:
                raise DepartamentoInvalidTransitionError("Departamento já está ativo")
            if departamento.status == STATUS_ARQUIVADA:
                raise DepartamentoInvalidTransitionError("Departamento arquivado não pode ser reativado")

            now = datetime.now(timezone.utc)
            departamento.status = STATUS_ATIVA
            departamento.updated_at = now
            departamento.inativado_at = None
            departamento.motivo_inativacao = None
            departamento.inativado_por_usuario_id = None
            self.repository.update(db, departamento)
            self._publish_event(db, departamento, DomainEventType.DEPARTAMENTO_REATIVADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    def to_response(self, departamento: Departamento) -> DepartamentoResponse:
        return DepartamentoResponse(
            id=departamento.id,
            empresaId=departamento.empresa_id,
            codigoInterno=departamento.codigo_interno,
            nome=departamento.nome,
            descricao=departamento.descricao,
            status=departamento.status,
            createdAt=departamento.created_at,
            updatedAt=departamento.updated_at,
            inativadoAt=departamento.inativado_at,
            motivoInativacao=departamento.motivo_inativacao,
            inativadoPorUsuarioId=departamento.inativado_por_usuario_id,
        )

    def _ensure_empresa_accepts_departamento(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise DepartamentoInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise DepartamentoInvalidEmpresaError("Empresa inativa não permite criação de Departamento")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise DepartamentoInvalidEmpresaError("Empresa arquivada não permite criação de Departamento")

    def _ensure_codigo_interno_available(
        self,
        db: Session,
        empresa_id: str,
        codigo_interno: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
        if existing is not None and existing.id != exclude_id:
            raise DepartamentoConflictError("codigoInterno já cadastrado para esta Empresa")

    def _ensure_nome_available(
        self,
        db: Session,
        empresa_id: str,
        nome: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existing = self.repository.get_by_nome(db, empresa_id=empresa_id, nome=nome)
        if existing is not None and existing.id != exclude_id:
            raise DepartamentoConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        departamento: Departamento,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        occurred_at: datetime | None = None,
        campos_alterados: list[str] | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload = {
            "empresa_id": departamento.empresa_id,
            "departamento_id": departamento.id,
            "timestamp": timestamp.isoformat(),
            "actor_usuario_id": actor_usuario_id,
        }
        if campos_alterados is not None:
            payload["campos_alterados"] = campos_alterados

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=departamento.empresa_id,
            entidade_tipo="departamento",
            entidade_id=departamento.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_codigo_interno(codigo_interno: str) -> str:
        return codigo_interno.strip().upper()

    @staticmethod
    def _normalize_nome(nome: str) -> str:
        return " ".join(nome.strip().split())

    @staticmethod
    def _normalize_descricao(descricao: str | None) -> str | None:
        if descricao is None:
            return None
        normalized = " ".join(descricao.strip().split())
        return normalized or None

    @staticmethod
    def _ensure_required(field: str, value: str) -> None:
        if not value:
            raise DepartamentoInvalidDataError(f"{field} é obrigatório")
