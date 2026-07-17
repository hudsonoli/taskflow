from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.event_types import DomainEventType
from app.models.cliente import Cliente, ClienteStatus, ClienteTipoPessoa
from app.repositories.agencia_repository import AgenciaRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import STATUS_ARQUIVADA as EMPRESA_STATUS_ARQUIVADA
from app.services.empresa_service import STATUS_INATIVA as EMPRESA_STATUS_INATIVA

STATUS_ATIVO = ClienteStatus.ATIVO.value
STATUS_SUSPENSO = ClienteStatus.SUSPENSO.value
STATUS_INATIVO = ClienteStatus.INATIVO.value
TIPO_FISICA = ClienteTipoPessoa.FISICA.value
TIPO_JURIDICA = ClienteTipoPessoa.JURIDICA.value


class ClienteNotFoundError(ValueError):
    pass


class ClienteConflictError(ValueError):
    pass


class ClienteInvalidTransitionError(ValueError):
    pass


class ClienteInvalidEmpresaError(ValueError):
    pass


class ClienteInvalidDataError(ValueError):
    pass


class ClienteInvalidAgenciaError(ValueError):
    pass


class ClienteInvalidActorError(ValueError):
    pass


class ClienteService:
    def __init__(
        self,
        repository: ClienteRepository | None = None,
        empresa_repository: EmpresaRepository | None = None,
        agencia_repository: AgenciaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ClienteRepository()
        self.empresa_repository = empresa_repository or EmpresaRepository()
        self.agencia_repository = agencia_repository or AgenciaRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def criar_cliente(
        self,
        db: Session,
        data: ClienteCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        context_empresa_id = str(empresa_id)
        payload_empresa_id = str(data.empresa_id)
        if payload_empresa_id != context_empresa_id:
            raise ClienteInvalidEmpresaError("Empresa do payload diverge da Empresa do contexto")

        codigo_interno = self._normalize_codigo_interno(data.codigo_interno)
        documento = self._normalize_optional(data.documento)
        now = datetime.now(timezone.utc)
        cliente = Cliente(
            id=str(uuid4()),
            empresa_id=context_empresa_id,
            agencia_id=str(data.agencia_id) if data.agencia_id else None,
            codigo_interno=codigo_interno,
            tipo_pessoa=data.tipo_pessoa.value,
            documento=documento,
            razao_social=self._normalize_text(data.razao_social),
            nome_fantasia=self._normalize_text(data.nome_fantasia),
            nome=self._normalize_text(data.nome),
            sigla=self._normalize_sigla(data.sigla),
            email=self._normalize_optional(data.email),
            telefone=self._normalize_optional(data.telefone),
            celular=self._normalize_optional(data.celular),
            site=self._normalize_optional(data.site),
            codigo_externo=self._normalize_optional(data.codigo_externo),
            observacoes=self._normalize_text(data.observacoes),
            status=STATUS_ATIVO,
            status_alterado_at=None,
            status_alterado_por_usuario_id=None,
            motivo_status=None,
            created_at=now,
            updated_at=now,
        )

        try:
            self._ensure_empresa_accepts_cliente(db, context_empresa_id)
            self._ensure_agencia_valid(db, context_empresa_id, cliente.agencia_id)
            self._ensure_codigo_interno_available(db, context_empresa_id, cliente.codigo_interno)
            self._ensure_documento_available(db, context_empresa_id, cliente.documento)
            self._validate_final_state(
                tipo_pessoa=cliente.tipo_pessoa,
                documento=cliente.documento,
                nome=cliente.nome,
                razao_social=cliente.razao_social,
                nome_fantasia=cliente.nome_fantasia,
            )
            self.repository.create(db, cliente)
            self._publish_event(db, cliente, DomainEventType.CLIENTE_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception:
            db.rollback()
            raise

    def obter_cliente(self, db: Session, *, empresa_id: str, cliente_id: str) -> Cliente:
        cliente = self.repository.get_by_id(db, empresa_id=str(empresa_id), cliente_id=cliente_id)
        if cliente is None:
            raise ClienteNotFoundError("Cliente não encontrado")
        return cliente

    def listar_clientes(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        tipo_pessoa: str | None = None,
        agencia_id: str | None = None,
        busca: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cliente]:
        return self.repository.list(
            db,
            empresa_id=str(empresa_id),
            status=status,
            tipo_pessoa=tipo_pessoa,
            agencia_id=agencia_id,
            busca=busca,
            limit=limit,
            offset=offset,
        )

    def atualizar_cliente(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str,
        data: ClienteUpdate,
        actor_usuario_id: str | None = None,
    ) -> Cliente:
        try:
            cliente = self.obter_cliente(db, empresa_id=str(empresa_id), cliente_id=cliente_id)
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            changed_fields: list[str] = []

            final = {
                "tipo_pessoa": cliente.tipo_pessoa,
                "documento": cliente.documento,
                "nome": cliente.nome,
                "razao_social": cliente.razao_social,
                "nome_fantasia": cliente.nome_fantasia,
            }

            if "agencia_id" in updates:
                agencia_id = str(updates["agencia_id"]) if updates["agencia_id"] is not None else None
                self._ensure_agencia_valid(db, cliente.empresa_id, agencia_id)
                if agencia_id != cliente.agencia_id:
                    cliente.agencia_id = agencia_id
                    changed_fields.append("agencia_id")

            if "codigo_interno" in updates:
                codigo_interno = self._normalize_codigo_interno(updates["codigo_interno"])
                self._ensure_required("codigoInterno", codigo_interno)
                if codigo_interno != cliente.codigo_interno:
                    self._ensure_codigo_interno_available(
                        db,
                        cliente.empresa_id,
                        codigo_interno,
                        exclude_id=cliente.id,
                    )
                    cliente.codigo_interno = codigo_interno
                    changed_fields.append("codigo_interno")

            if "tipo_pessoa" in updates:
                tipo_pessoa = updates["tipo_pessoa"].value if isinstance(updates["tipo_pessoa"], ClienteTipoPessoa) else updates["tipo_pessoa"]
                if tipo_pessoa != cliente.tipo_pessoa:
                    cliente.tipo_pessoa = tipo_pessoa
                    changed_fields.append("tipo_pessoa")
                final["tipo_pessoa"] = tipo_pessoa

            if "documento" in updates:
                documento = self._normalize_optional(updates["documento"])
                if documento != cliente.documento:
                    self._ensure_documento_available(db, cliente.empresa_id, documento, exclude_id=cliente.id)
                    cliente.documento = documento
                    changed_fields.append("documento")
                final["documento"] = documento

            for field in (
                "razao_social",
                "nome_fantasia",
                "nome",
                "email",
                "telefone",
                "celular",
                "site",
                "codigo_externo",
                "observacoes",
            ):
                if field in updates:
                    value = self._normalize_text(updates[field]) if field in {"razao_social", "nome_fantasia", "nome", "observacoes"} else self._normalize_optional(updates[field])
                    if value != getattr(cliente, field):
                        setattr(cliente, field, value)
                        changed_fields.append(field)
                    if field in final:
                        final[field] = value

            if "sigla" in updates:
                sigla = self._normalize_sigla(updates["sigla"])
                if sigla != cliente.sigla:
                    cliente.sigla = sigla
                    changed_fields.append("sigla")

            final["tipo_pessoa"] = cliente.tipo_pessoa
            final["documento"] = cliente.documento
            final["nome"] = cliente.nome
            final["razao_social"] = cliente.razao_social
            final["nome_fantasia"] = cliente.nome_fantasia
            self._validate_final_state(**final)

            if changed_fields:
                now = datetime.now(timezone.utc)
                cliente.updated_at = now
                self.repository.update(db, cliente)
                self._publish_event(
                    db,
                    cliente,
                    DomainEventType.CLIENTE_ALTERADO,
                    actor_usuario_id,
                    occurred_at=now,
                    campos_alterados=changed_fields,
                )

            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception:
            db.rollback()
            raise

    def suspender_cliente(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str,
        motivo: str | None,
        actor_usuario_id: str,
    ) -> Cliente:
        motivo_status = self._normalize_text(motivo)
        self._ensure_required("motivo", motivo_status)
        return self._alterar_status(
            db,
            empresa_id=empresa_id,
            cliente_id=cliente_id,
            novo_status=STATUS_SUSPENSO,
            allowed_current={STATUS_ATIVO},
            motivo=motivo_status,
            actor_usuario_id=actor_usuario_id,
            event_type=DomainEventType.CLIENTE_SUSPENSO,
            invalid_message="Cliente só pode ser suspenso quando está ativo",
        )

    def reativar_cliente(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str,
        motivo: str | None = None,
        actor_usuario_id: str,
    ) -> Cliente:
        return self._alterar_status(
            db,
            empresa_id=empresa_id,
            cliente_id=cliente_id,
            novo_status=STATUS_ATIVO,
            allowed_current={STATUS_SUSPENSO, STATUS_INATIVO},
            motivo=self._normalize_text(motivo),
            actor_usuario_id=actor_usuario_id,
            event_type=DomainEventType.CLIENTE_REATIVADO,
            invalid_message="Cliente só pode ser reativado quando está suspenso ou inativo",
        )

    def inativar_cliente(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str,
        motivo: str | None,
        actor_usuario_id: str,
    ) -> Cliente:
        motivo_status = self._normalize_text(motivo)
        self._ensure_required("motivo", motivo_status)
        return self._alterar_status(
            db,
            empresa_id=empresa_id,
            cliente_id=cliente_id,
            novo_status=STATUS_INATIVO,
            allowed_current={STATUS_ATIVO, STATUS_SUSPENSO},
            motivo=motivo_status,
            actor_usuario_id=actor_usuario_id,
            event_type=DomainEventType.CLIENTE_INATIVADO,
            invalid_message="Cliente só pode ser inativado quando está ativo ou suspenso",
        )

    def to_response(self, cliente: Cliente) -> ClienteResponse:
        return ClienteResponse.model_validate(cliente)

    def _alterar_status(
        self,
        db: Session,
        *,
        empresa_id: str,
        cliente_id: str,
        novo_status: str,
        allowed_current: set[str],
        motivo: str | None,
        actor_usuario_id: str,
        event_type: DomainEventType,
        invalid_message: str,
    ) -> Cliente:
        try:
            cliente = self.obter_cliente(db, empresa_id=str(empresa_id), cliente_id=cliente_id)
            self._ensure_actor_valid(db, cliente.empresa_id, actor_usuario_id)
            if cliente.status not in allowed_current:
                raise ClienteInvalidTransitionError(invalid_message)

            now = datetime.now(timezone.utc)
            status_anterior = cliente.status
            cliente.status = novo_status
            cliente.status_alterado_at = now
            cliente.status_alterado_por_usuario_id = actor_usuario_id
            cliente.motivo_status = motivo
            cliente.updated_at = now
            self.repository.update(db, cliente)
            self._publish_event(
                db,
                cliente,
                event_type,
                actor_usuario_id,
                occurred_at=now,
                status_anterior=status_anterior,
                status_atual=novo_status,
            )
            db.commit()
            db.refresh(cliente)
            return cliente
        except Exception:
            db.rollback()
            raise

    def _ensure_empresa_accepts_cliente(self, db: Session, empresa_id: str) -> None:
        empresa = self.empresa_repository.get_by_id(db, empresa_id)
        if empresa is None:
            raise ClienteInvalidEmpresaError("Empresa não encontrada")
        if empresa.status == EMPRESA_STATUS_INATIVA:
            raise ClienteInvalidEmpresaError("Empresa inativa não permite criação de Cliente")
        if empresa.status == EMPRESA_STATUS_ARQUIVADA:
            raise ClienteInvalidEmpresaError("Empresa arquivada não permite criação de Cliente")

    def _ensure_agencia_valid(self, db: Session, empresa_id: str, agencia_id: str | None) -> None:
        if agencia_id is None:
            return
        agencia = self.agencia_repository.get_by_id(db, agencia_id)
        if agencia is None:
            raise ClienteInvalidAgenciaError("Agência não encontrada")
        if agencia.empresa_id != empresa_id:
            raise ClienteInvalidAgenciaError("Agência não pertence à Empresa informada")

    def _ensure_actor_valid(self, db: Session, empresa_id: str, actor_usuario_id: str | None) -> None:
        self._ensure_required("actorUsuarioId", actor_usuario_id)
        usuario = self.usuario_repository.get_by_id(db, actor_usuario_id)
        if usuario is None:
            raise ClienteInvalidActorError("Ator não encontrado")
        if usuario.empresa_id != empresa_id:
            raise ClienteInvalidActorError("Ator não pertence à Empresa do Cliente")

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
            raise ClienteConflictError("codigoInterno já cadastrado para esta Empresa")

    def _ensure_documento_available(
        self,
        db: Session,
        empresa_id: str,
        documento: str | None,
        *,
        exclude_id: str | None = None,
    ) -> None:
        if documento is None:
            return
        existing = self.repository.get_by_documento(db, empresa_id=empresa_id, documento=documento)
        if existing is not None and existing.id != exclude_id:
            raise ClienteConflictError("documento já cadastrado para esta Empresa")

    def _validate_final_state(
        self,
        *,
        tipo_pessoa: str,
        documento: str | None,
        nome: str | None,
        razao_social: str | None,
        nome_fantasia: str | None,
    ) -> None:
        if tipo_pessoa not in {TIPO_FISICA, TIPO_JURIDICA}:
            raise ClienteInvalidDataError("tipoPessoa inválido")
        if documento is not None and not documento.isdigit():
            raise ClienteInvalidDataError("documento deve conter apenas dígitos")
        if tipo_pessoa == TIPO_FISICA:
            if not nome:
                raise ClienteInvalidDataError("nome é obrigatório para pessoa física")
            if documento is not None and len(documento) != 11:
                raise ClienteInvalidDataError("documento de pessoa física deve conter 11 dígitos")
        if tipo_pessoa == TIPO_JURIDICA:
            if not (razao_social or nome_fantasia):
                raise ClienteInvalidDataError("razão social ou nome fantasia é obrigatório para pessoa jurídica")
            if documento is not None and len(documento) != 14:
                raise ClienteInvalidDataError("documento de pessoa jurídica deve conter 14 dígitos")

    def _publish_event(
        self,
        db: Session,
        cliente: Cliente,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        occurred_at: datetime | None = None,
        campos_alterados: list[str] | None = None,
        status_anterior: str | None = None,
        status_atual: str | None = None,
    ) -> None:
        timestamp = occurred_at or datetime.now(timezone.utc)
        payload: dict[str, object] = {
            "empresa_id": cliente.empresa_id,
            "cliente_id": cliente.id,
        }
        if campos_alterados is not None:
            payload["campos_alterados"] = campos_alterados
        if status_anterior is not None:
            payload["status_anterior"] = status_anterior
        if status_atual is not None:
            payload["status_atual"] = status_atual
        if tipo in {DomainEventType.CLIENTE_SUSPENSO, DomainEventType.CLIENTE_REATIVADO, DomainEventType.CLIENTE_INATIVADO}:
            payload["actor_usuario_id"] = actor_usuario_id

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=cliente.empresa_id,
            entidade_tipo="cliente",
            entidade_id=cliente.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalize_codigo_interno(codigo_interno: str) -> str:
        return codigo_interno.strip().upper()

    @staticmethod
    def _normalize_sigla(sigla: str | None) -> str | None:
        if sigla is None:
            return None
        normalized = sigla.strip().upper()
        return normalized or None

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _ensure_required(field: str, value: str | None) -> None:
        if not value:
            raise ClienteInvalidDataError(f"{field} é obrigatório")
