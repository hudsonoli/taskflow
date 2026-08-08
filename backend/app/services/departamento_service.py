from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.departamento import DepartamentoCreate, DepartamentoDiretorioRead, DepartamentoRead, DepartamentoUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "departamento"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"

# Um usuário nestes estados não pode ser DEFINIDO como responsável novo. Vínculo histórico
# (alguém que virou responsável e depois foi inativado) continua valendo — ver
# _ensure_responsavel_valido.
STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL = {"arquivado", "inativo", "bloqueado"}


class DepartamentoNotFoundError(ValueError):
    pass


class DepartamentoConflictError(ValueError):
    pass


class DepartamentoArquivadoConflictError(ValueError):
    """Nome já pertence a um departamento arquivado — a UI oferece restaurar em vez de
    mostrar erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, departamento_arquivado_id: str) -> None:
        super().__init__(message)
        self.departamento_arquivado_id = departamento_arquivado_id


class DepartamentoInvalidTransitionError(ValueError):
    pass


class DepartamentoResponsavelInvalidoError(ValueError):
    """Responsável inexistente, de outra empresa ou em status que não aceita novo vínculo."""


class DepartamentoService:
    def __init__(
        self,
        repository: DepartamentoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or DepartamentoRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_departamento(
        self,
        db: Session,
        data: DepartamentoCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> Departamento:
        """Rota pública: `codigo_interno` é derivado do nome e `codigo_referencia` é emitido
        pela infraestrutura central — nenhum dos dois vem do payload."""
        from app.core.slugify import gerar_codigo_interno

        codigo_interno = gerar_codigo_interno(
            data.nome,
            existe_conflito=lambda candidato: self.repository.get_by_codigo_interno(
                db, empresa_id=empresa_id, codigo_interno=candidato
            )
            is not None,
        )
        return self._criar(
            db,
            nome=data.nome,
            cor_identificacao=data.cor_identificacao,
            descricao=data.descricao,
            responsavel_usuario_id=str(data.responsavel_usuario_id) if data.responsavel_usuario_id else None,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def create_departamento_com_codigo_legado(
        self,
        db: Session,
        *,
        nome: str,
        cor_identificacao: str,
        empresa_id: str,
        codigo_interno: str,
        descricao: str | None = None,
        responsavel_usuario_id: str | None = None,
        actor_usuario_id: str | None = None,
    ) -> Departamento:
        """Uso interno do seed — nunca exposta via HTTP. Idempotente: se o
        `codigo_interno` já existe, devolve o registro **sem consumir sequência**."""
        existente = self.repository.get_by_codigo_interno(
            db, empresa_id=empresa_id, codigo_interno=codigo_interno
        )
        if existente is not None:
            return existente
        return self._criar(
            db,
            nome=nome,
            cor_identificacao=cor_identificacao,
            descricao=descricao,
            responsavel_usuario_id=responsavel_usuario_id,
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def _criar(
        self,
        db: Session,
        *,
        nome: str,
        cor_identificacao: str,
        descricao: str | None,
        responsavel_usuario_id: str | None,
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str | None,
    ) -> Departamento:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)
            if responsavel_usuario_id is not None:
                self._ensure_responsavel_valido(db, empresa_id, responsavel_usuario_id)

            # Contador, entidade e evento na MESMA transação: se a criação falhar abaixo,
            # o incremento da sequência sofre rollback junto e o número não é queimado.
            referencia = gerar_proxima_referencia(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE)

            departamento = Departamento(
                id=str(uuid4()),
                empresa_id=empresa_id,
                codigo_interno=codigo_interno,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=nome,
                nome_normalizado=nome_normalizado,
                descricao=descricao,
                responsavel_usuario_id=responsavel_usuario_id,
                cor_identificacao=cor_identificacao,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, departamento)
            self._publish_event(db, departamento, DomainEventType.DEPARTAMENTO_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(departamento)
            return departamento
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelos checks antes de qualquer
            # commit. Reconsulta para distinguir conflito comum de conflito-arquivado.
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            ) or self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise DepartamentoArquivadoConflictError(
                    "Já existe um departamento arquivado com este nome",
                    departamento_arquivado_id=existente.id,
                ) from None
            raise DepartamentoConflictError("nome ou codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_departamentos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Departamento]:
        return self.repository.list(
            db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Departamento]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_departamento(self, db: Session, departamento_id: str) -> Departamento:
        departamento = self.repository.get_by_id(db, departamento_id)
        if departamento is None:
            raise DepartamentoNotFoundError("Departamento não encontrado")
        return departamento

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_departamento(
        self,
        db: Session,
        departamento_id: str,
        data: DepartamentoUpdate,
        *,
        actor_usuario_id: str,
    ) -> Departamento:
        try:
            departamento = self.get_departamento(db, departamento_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)

            if "nome" in updates and updates["nome"] != departamento.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != departamento.nome_normalizado:
                    self._ensure_nome_disponivel(
                        db, departamento.empresa_id, nome_normalizado, exclude_id=departamento.id
                    )
                departamento.nome = updates["nome"]
                departamento.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "cor_identificacao" in updates and updates["cor_identificacao"] != departamento.cor_identificacao:
                departamento.cor_identificacao = updates["cor_identificacao"]
                changed_fields.append("corIdentificacao")

            if "descricao" in updates and updates["descricao"] != departamento.descricao:
                departamento.descricao = updates["descricao"]
                changed_fields.append("descricao")

            if "responsavel_usuario_id" in updates:
                novo = str(updates["responsavel_usuario_id"]) if updates["responsavel_usuario_id"] else None
                if novo != departamento.responsavel_usuario_id:
                    if novo is not None:
                        self._ensure_responsavel_valido(db, departamento.empresa_id, novo)
                    departamento.responsavel_usuario_id = novo
                    changed_fields.append("responsavelUsuarioId")

            if "status" in updates and updates["status"] != departamento.status:
                if departamento.status == STATUS_ARQUIVADO:
                    raise DepartamentoInvalidTransitionError(
                        "Departamento arquivado deve ser restaurado antes de mudar de status"
                    )
                departamento.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                now = agora_utc()
                departamento.updated_at = now
                self.repository.update(db, departamento)
                self._publish_event(
                    db,
                    departamento,
                    DomainEventType.DEPARTAMENTO_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(departamento)
            return departamento
        except IntegrityError:
            db.rollback()
            raise DepartamentoConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_departamento(
        self,
        db: Session,
        departamento_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> Departamento:
        """Arquivar NÃO cascateia: usuários e equipes vinculados são preservados. O que
        muda é que novos vínculos a este departamento passam a ser recusados."""
        try:
            departamento = self.get_departamento(db, departamento_id)
            if departamento.status == STATUS_ARQUIVADO:
                raise DepartamentoInvalidTransitionError("Departamento já está arquivado")

            now = agora_utc()
            departamento.status_anterior_arquivamento = departamento.status
            departamento.status = STATUS_ARQUIVADO
            departamento.updated_at = now
            departamento.arquivado_at = now
            departamento.arquivado_por_usuario_id = actor_usuario_id
            departamento.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, departamento)
            self._publish_event(
                db, departamento, DomainEventType.DEPARTAMENTO_ARQUIVADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    def restaurar_departamento(
        self,
        db: Session,
        departamento_id: str,
        *,
        actor_usuario_id: str,
    ) -> Departamento:
        """Restaura sempre para `ativo`. Não precisa checar conflito de nome: a unicidade
        vale entre todos os status, então ninguém pôde ocupar o nome nesse meio tempo."""
        try:
            departamento = self.get_departamento(db, departamento_id)
            if departamento.status != STATUS_ARQUIVADO:
                raise DepartamentoInvalidTransitionError("Somente departamento arquivado pode ser restaurado")

            now = agora_utc()
            departamento.status = STATUS_ATIVO
            departamento.updated_at = now
            departamento.restaurado_at = now
            departamento.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, departamento)
            self._publish_event(
                db, departamento, DomainEventType.DEPARTAMENTO_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(departamento)
            return departamento
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, departamento: Departamento) -> DepartamentoRead:
        return DepartamentoRead(
            id=departamento.id,
            empresaId=departamento.empresa_id,
            codigoInterno=departamento.codigo_interno,
            codigoReferencia=departamento.codigo_referencia,
            anoReferencia=departamento.ano_referencia,
            sequencialReferencia=departamento.sequencial_referencia,
            nome=departamento.nome,
            descricao=departamento.descricao,
            responsavelUsuarioId=departamento.responsavel_usuario_id,
            corIdentificacao=departamento.cor_identificacao,
            status=departamento.status,
            createdAt=departamento.created_at,
            updatedAt=departamento.updated_at,
            arquivadoAt=departamento.arquivado_at,
            arquivadoPorUsuarioId=departamento.arquivado_por_usuario_id,
            motivoArquivamento=departamento.motivo_arquivamento,
            restauradoAt=departamento.restaurado_at,
            restauradoPorUsuarioId=departamento.restaurado_por_usuario_id,
            statusAnteriorArquivamento=departamento.status_anterior_arquivamento,
        )

    def to_diretorio_read(self, departamento: Departamento) -> DepartamentoDiretorioRead:
        return DepartamentoDiretorioRead(
            id=departamento.id,
            codigoInterno=departamento.codigo_interno,
            codigoReferencia=departamento.codigo_referencia,
            sequencialReferencia=departamento.sequencial_referencia,
            nome=departamento.nome,
            corIdentificacao=departamento.cor_identificacao,
            status=departamento.status,
            responsavelUsuarioId=departamento.responsavel_usuario_id,
        )

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _ensure_nome_disponivel(
        self,
        db: Session,
        empresa_id: str,
        nome_normalizado: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        existente = self.repository.get_by_nome_normalizado(
            db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
        )
        if existente is not None and existente.id != exclude_id:
            if existente.status == STATUS_ARQUIVADO:
                raise DepartamentoArquivadoConflictError(
                    "nome já pertence a um departamento arquivado",
                    departamento_arquivado_id=existente.id,
                )
            raise DepartamentoConflictError("nome já cadastrado para esta Empresa")

    def _ensure_responsavel_valido(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        """Responsável precisa existir, ser da MESMA empresa e estar apto a receber o
        vínculo. Cross-tenant é tratado aqui como responsável inválido — não vaza a
        existência de usuário de outra empresa."""
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise DepartamentoResponsavelInvalidoError("Responsável não encontrado nesta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO_COMO_RESPONSAVEL:
            raise DepartamentoResponsavelInvalidoError(
                f"Usuário com status '{usuario.status}' não pode ser definido como responsável"
            )

    def _publish_event(
        self,
        db: Session,
        departamento: Departamento,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": departamento.empresa_id,
            "departamento_id": departamento.id,
            "codigo_referencia": departamento.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": departamento.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=departamento.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=departamento.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
