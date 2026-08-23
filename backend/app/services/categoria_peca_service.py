from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.categoria_peca import CategoriaPeca
from app.repositories.categoria_peca_repository import CategoriaPecaRepository
from app.schemas.categoria_peca import (
    CategoriaPecaCreate,
    CategoriaPecaDiretorioRead,
    CategoriaPecaRead,
    CategoriaPecaUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "categoria_peca"

STATUS_ATIVO = "ativo"
STATUS_ARQUIVADO = "arquivado"


class CategoriaPecaNotFoundError(ValueError):
    pass


class CategoriaPecaConflictError(ValueError):
    pass


class CategoriaPecaArquivadaConflictError(ValueError):
    """Nome já pertence a uma Categoria arquivada — a UI oferece restaurar em vez de mostrar
    erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, categoria_peca_arquivada_id: str) -> None:
        super().__init__(message)
        self.categoria_peca_arquivada_id = categoria_peca_arquivada_id


class CategoriaPecaInvalidTransitionError(ValueError):
    pass


class CategoriaPecaService:
    def __init__(
        self,
        repository: CategoriaPecaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or CategoriaPecaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_categoria(
        self,
        db: Session,
        data: CategoriaPecaCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None,
    ) -> CategoriaPeca:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)

            categoria = CategoriaPeca(
                id=str(uuid4()),
                empresa_id=empresa_id,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                ordem=data.ordem,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, categoria)
            self._publish_event(
                db, categoria, DomainEventType.CATEGORIA_PECA_CRIADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(categoria)
            return categoria
        except IntegrityError:
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            )
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise CategoriaPecaArquivadaConflictError(
                    "Já existe uma Categoria arquivada com este nome",
                    categoria_peca_arquivada_id=existente.id,
                ) from None
            raise CategoriaPecaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_categorias(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CategoriaPeca]:
        return self.repository.list(
            db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset
        )

    def get_categoria(self, db: Session, categoria_id: str) -> CategoriaPeca:
        categoria = self.repository.get_by_id(db, categoria_id)
        if categoria is None:
            raise CategoriaPecaNotFoundError("Categoria de Peça não encontrada")
        return categoria

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[CategoriaPeca]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_categoria(
        self,
        db: Session,
        categoria_id: str,
        data: CategoriaPecaUpdate,
        *,
        actor_usuario_id: str,
    ) -> CategoriaPeca:
        try:
            categoria = self.get_categoria(db, categoria_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != categoria.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != categoria.nome_normalizado:
                    self._ensure_nome_disponivel(
                        db, categoria.empresa_id, nome_normalizado, exclude_id=categoria.id
                    )
                categoria.nome = updates["nome"]
                categoria.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "ordem" in updates and updates["ordem"] != categoria.ordem:
                categoria.ordem = updates["ordem"]
                changed_fields.append("ordem")

            if changed_fields:
                categoria.updated_at = now
                self.repository.update(db, categoria)
                self._publish_event(
                    db,
                    categoria,
                    DomainEventType.CATEGORIA_PECA_ALTERADA,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(categoria)
            return categoria
        except IntegrityError:
            db.rollback()
            raise CategoriaPecaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_categoria(
        self,
        db: Session,
        categoria_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> CategoriaPeca:
        """Arquivar não apaga nada, e não desvincula Peças já classificadas com esta
        Categoria (`Peca.categoria_id` sem CASCADE) — só passa a recusar novo vínculo (a
        Categoria some do diretório). Peça existente continua mostrando o nome via join em
        PecaRead.categoriaNome."""
        try:
            categoria = self.get_categoria(db, categoria_id)
            if categoria.status == STATUS_ARQUIVADO:
                raise CategoriaPecaInvalidTransitionError("Categoria já está arquivada")

            now = agora_utc()
            categoria.status_anterior_arquivamento = categoria.status
            categoria.status = STATUS_ARQUIVADO
            categoria.updated_at = now
            categoria.arquivado_at = now
            categoria.arquivado_por_usuario_id = actor_usuario_id
            categoria.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, categoria)
            self._publish_event(
                db, categoria, DomainEventType.CATEGORIA_PECA_ARQUIVADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(categoria)
            return categoria
        except Exception:
            db.rollback()
            raise

    def restaurar_categoria(
        self,
        db: Session,
        categoria_id: str,
        *,
        actor_usuario_id: str,
    ) -> CategoriaPeca:
        """Restaura sempre para `ativo` — único estado não-arquivado que existe."""
        try:
            categoria = self.get_categoria(db, categoria_id)
            if categoria.status != STATUS_ARQUIVADO:
                raise CategoriaPecaInvalidTransitionError("Somente Categoria arquivada pode ser restaurada")

            now = agora_utc()
            categoria.status = STATUS_ATIVO
            categoria.updated_at = now
            categoria.restaurado_at = now
            categoria.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, categoria)
            self._publish_event(
                db, categoria, DomainEventType.CATEGORIA_PECA_RESTAURADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(categoria)
            return categoria
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, categoria: CategoriaPeca) -> CategoriaPecaRead:
        return CategoriaPecaRead(
            id=categoria.id,
            empresaId=categoria.empresa_id,
            nome=categoria.nome,
            ordem=categoria.ordem,
            status=categoria.status,
            createdAt=categoria.created_at,
            updatedAt=categoria.updated_at,
            arquivadoAt=categoria.arquivado_at,
            arquivadoPorUsuarioId=categoria.arquivado_por_usuario_id,
            motivoArquivamento=categoria.motivo_arquivamento,
            restauradoAt=categoria.restaurado_at,
            restauradoPorUsuarioId=categoria.restaurado_por_usuario_id,
        )

    def to_diretorio_read(self, categoria: CategoriaPeca) -> CategoriaPecaDiretorioRead:
        return CategoriaPecaDiretorioRead(id=categoria.id, nome=categoria.nome)

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
                raise CategoriaPecaArquivadaConflictError(
                    "nome já pertence a uma Categoria arquivada",
                    categoria_peca_arquivada_id=existente.id,
                )
            raise CategoriaPecaConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        categoria: CategoriaPeca,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": categoria.empresa_id,
            "categoria_peca_id": categoria.id,
            "timestamp": timestamp.isoformat(),
            "status": categoria.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=categoria.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=categoria.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
