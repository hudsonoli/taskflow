from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.equipe import Equipe
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.equipe_repository import EquipeRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.equipe import EquipeCreate, EquipeDiretorioRead, EquipeRead, EquipeUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "equipe"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"

# Mesma regra do Departamento: estes status impedem um vínculo NOVO, mas não desfazem
# vínculo histórico já existente.
STATUS_USUARIO_INVALIDO_PARA_VINCULO = {"arquivado", "inativo", "bloqueado"}


class EquipeNotFoundError(ValueError):
    pass


class EquipeConflictError(ValueError):
    pass


class EquipeArquivadaConflictError(ValueError):
    def __init__(self, message: str, *, equipe_arquivada_id: str) -> None:
        super().__init__(message)
        self.equipe_arquivada_id = equipe_arquivada_id


class EquipeInvalidTransitionError(ValueError):
    pass


class EquipeDepartamentoInvalidoError(ValueError):
    """Departamento inexistente, de outra empresa ou arquivado (novo vínculo)."""


class EquipeMembroInvalidoError(ValueError):
    """Membro/líder inexistente, de outra empresa ou em status que não aceita novo vínculo."""


class EquipeService:
    def __init__(
        self,
        repository: EquipeRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or EquipeRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_equipe(
        self,
        db: Session,
        data: EquipeCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> Equipe:
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
            departamento_id=str(data.departamento_id) if data.departamento_id else None,
            lider_usuario_id=str(data.lider_usuario_id) if data.lider_usuario_id else None,
            membro_ids=[str(membro) for membro in data.membro_ids],
            empresa_id=empresa_id,
            codigo_interno=codigo_interno,
            actor_usuario_id=actor_usuario_id,
        )

    def create_equipe_com_codigo_legado(
        self,
        db: Session,
        *,
        nome: str,
        cor_identificacao: str,
        empresa_id: str,
        codigo_interno: str,
        descricao: str | None = None,
        departamento_id: str | None = None,
        lider_usuario_id: str | None = None,
        membro_ids: list[str] | None = None,
        actor_usuario_id: str | None = None,
    ) -> Equipe:
        """Uso interno do seed. Idempotente: `codigo_interno` já existente devolve o
        registro **sem consumir sequência**."""
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
            departamento_id=departamento_id,
            lider_usuario_id=lider_usuario_id,
            membro_ids=membro_ids or [],
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
        departamento_id: str | None,
        lider_usuario_id: str | None,
        membro_ids: list[str],
        empresa_id: str,
        codigo_interno: str,
        actor_usuario_id: str | None,
    ) -> Equipe:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)
            if departamento_id is not None:
                self._ensure_departamento_valido(db, empresa_id, departamento_id)

            # Líder é sempre membro — garantido antes de validar a lista inteira.
            membros_desejados = list(dict.fromkeys(membro_ids))
            if lider_usuario_id is not None and lider_usuario_id not in membros_desejados:
                membros_desejados.append(lider_usuario_id)
            for usuario_id in membros_desejados:
                self._ensure_usuario_valido_para_vinculo(db, empresa_id, usuario_id)

            # Contador, entidade, membros e eventos na MESMA transação.
            referencia = gerar_proxima_referencia(db, empresa_id=empresa_id, tipo_entidade=TIPO_ENTIDADE)

            equipe = Equipe(
                id=str(uuid4()),
                empresa_id=empresa_id,
                codigo_interno=codigo_interno,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                nome=nome,
                nome_normalizado=nome_normalizado,
                descricao=descricao,
                departamento_id=departamento_id,
                lider_usuario_id=lider_usuario_id,
                cor_identificacao=cor_identificacao,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, equipe)

            for usuario_id in membros_desejados:
                self.repository.adicionar_membro(
                    db, equipe_id=equipe.id, usuario_id=usuario_id, created_at=now
                )
                self._publish_event_membro(
                    db, equipe, DomainEventType.EQUIPE_MEMBRO_ADICIONADO, usuario_id, actor_usuario_id, now
                )

            self._publish_event(db, equipe, DomainEventType.EQUIPE_CRIADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except IntegrityError:
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            ) or self.repository.get_by_codigo_interno(db, empresa_id=empresa_id, codigo_interno=codigo_interno)
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise EquipeArquivadaConflictError(
                    "Já existe uma equipe arquivada com este nome",
                    equipe_arquivada_id=existente.id,
                ) from None
            raise EquipeConflictError("nome ou codigoInterno já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_equipes(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Equipe]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            departamento_id=departamento_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Equipe]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    def get_equipe(self, db: Session, equipe_id: str) -> Equipe:
        equipe = self.repository.get_by_id(db, equipe_id)
        if equipe is None:
            raise EquipeNotFoundError("Equipe não encontrada")
        return equipe

    def listar_membro_ids(self, db: Session, equipe_id: str) -> list[str]:
        return self.repository.listar_membro_ids(db, equipe_id)

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def update_equipe(
        self,
        db: Session,
        equipe_id: str,
        data: EquipeUpdate,
        *,
        actor_usuario_id: str,
    ) -> Equipe:
        try:
            equipe = self.get_equipe(db, equipe_id)
            empresa_id = equipe.empresa_id
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != equipe.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != equipe.nome_normalizado:
                    self._ensure_nome_disponivel(db, empresa_id, nome_normalizado, exclude_id=equipe.id)
                equipe.nome = updates["nome"]
                equipe.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "cor_identificacao" in updates and updates["cor_identificacao"] != equipe.cor_identificacao:
                equipe.cor_identificacao = updates["cor_identificacao"]
                changed_fields.append("corIdentificacao")

            if "descricao" in updates and updates["descricao"] != equipe.descricao:
                equipe.descricao = updates["descricao"]
                changed_fields.append("descricao")

            if "departamento_id" in updates:
                novo = str(updates["departamento_id"]) if updates["departamento_id"] else None
                if novo != equipe.departamento_id:
                    # Só valida se está APONTANDO para um departamento novo; virar
                    # transversal (None) é sempre permitido.
                    if novo is not None:
                        self._ensure_departamento_valido(db, empresa_id, novo)
                    equipe.departamento_id = novo
                    changed_fields.append("departamentoId")

            # Membros e líder são resolvidos juntos: o líder precisa terminar na lista.
            membros_atuais = set(self.repository.listar_membro_ids(db, equipe.id))
            lider_desejado = equipe.lider_usuario_id
            if "lider_usuario_id" in updates:
                lider_desejado = str(updates["lider_usuario_id"]) if updates["lider_usuario_id"] else None

            if "membro_ids" in updates and updates["membro_ids"] is not None:
                membros_desejados = set(str(membro) for membro in updates["membro_ids"])
            else:
                membros_desejados = set(membros_atuais)

            # Remover o líder da lista de membros limpa liderUsuarioId — não deixa líder
            # fantasma fora da equipe.
            if lider_desejado is not None and lider_desejado not in membros_desejados:
                if "membro_ids" in updates and updates["membro_ids"] is not None:
                    lider_desejado = None
                else:
                    membros_desejados.add(lider_desejado)

            adicionados = membros_desejados - membros_atuais
            removidos = membros_atuais - membros_desejados

            for usuario_id in adicionados:
                self._ensure_usuario_valido_para_vinculo(db, empresa_id, usuario_id)
            if lider_desejado is not None and lider_desejado != equipe.lider_usuario_id:
                self._ensure_usuario_valido_para_vinculo(db, empresa_id, lider_desejado)

            for usuario_id in sorted(adicionados):
                self.repository.adicionar_membro(
                    db, equipe_id=equipe.id, usuario_id=usuario_id, created_at=now
                )
                self._publish_event_membro(
                    db, equipe, DomainEventType.EQUIPE_MEMBRO_ADICIONADO, usuario_id, actor_usuario_id, now
                )
            for usuario_id in sorted(removidos):
                self.repository.remover_membro(db, equipe_id=equipe.id, usuario_id=usuario_id)
                self._publish_event_membro(
                    db, equipe, DomainEventType.EQUIPE_MEMBRO_REMOVIDO, usuario_id, actor_usuario_id, now
                )
            if adicionados or removidos:
                changed_fields.append("membroIds")

            if lider_desejado != equipe.lider_usuario_id:
                equipe.lider_usuario_id = lider_desejado
                changed_fields.append("liderUsuarioId")

            if "status" in updates and updates["status"] != equipe.status:
                if equipe.status == STATUS_ARQUIVADO:
                    raise EquipeInvalidTransitionError(
                        "Equipe arquivada deve ser restaurada antes de mudar de status"
                    )
                equipe.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                equipe.updated_at = now
                self.repository.update(db, equipe)
                self._publish_event(
                    db,
                    equipe,
                    DomainEventType.EQUIPE_ALTERADA,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(equipe)
            return equipe
        except IntegrityError:
            db.rollback()
            raise EquipeConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_equipe(
        self,
        db: Session,
        equipe_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> Equipe:
        """Arquivar NÃO apaga `equipe_membros` — a composição fica preservada para quando a
        equipe for restaurada."""
        try:
            equipe = self.get_equipe(db, equipe_id)
            if equipe.status == STATUS_ARQUIVADO:
                raise EquipeInvalidTransitionError("Equipe já está arquivada")

            now = agora_utc()
            equipe.status_anterior_arquivamento = equipe.status
            equipe.status = STATUS_ARQUIVADO
            equipe.updated_at = now
            equipe.arquivado_at = now
            equipe.arquivado_por_usuario_id = actor_usuario_id
            equipe.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, equipe)
            self._publish_event(db, equipe, DomainEventType.EQUIPE_ARQUIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    def restaurar_equipe(self, db: Session, equipe_id: str, *, actor_usuario_id: str) -> Equipe:
        try:
            equipe = self.get_equipe(db, equipe_id)
            if equipe.status != STATUS_ARQUIVADO:
                raise EquipeInvalidTransitionError("Somente equipe arquivada pode ser restaurada")

            now = agora_utc()
            equipe.status = STATUS_ATIVO
            equipe.updated_at = now
            equipe.restaurado_at = now
            equipe.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, equipe)
            self._publish_event(db, equipe, DomainEventType.EQUIPE_RESTAURADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(equipe)
            return equipe
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, equipe: Equipe) -> EquipeRead:
        return EquipeRead(
            id=equipe.id,
            empresaId=equipe.empresa_id,
            codigoInterno=equipe.codigo_interno,
            codigoReferencia=equipe.codigo_referencia,
            anoReferencia=equipe.ano_referencia,
            sequencialReferencia=equipe.sequencial_referencia,
            nome=equipe.nome,
            descricao=equipe.descricao,
            departamentoId=equipe.departamento_id,
            liderUsuarioId=equipe.lider_usuario_id,
            membroIds=self.repository.listar_membro_ids(db, equipe.id),
            corIdentificacao=equipe.cor_identificacao,
            status=equipe.status,
            createdAt=equipe.created_at,
            updatedAt=equipe.updated_at,
            arquivadoAt=equipe.arquivado_at,
            arquivadoPorUsuarioId=equipe.arquivado_por_usuario_id,
            motivoArquivamento=equipe.motivo_arquivamento,
            restauradoAt=equipe.restaurado_at,
            restauradoPorUsuarioId=equipe.restaurado_por_usuario_id,
            statusAnteriorArquivamento=equipe.status_anterior_arquivamento,
        )

    def to_diretorio_read(self, db: Session, equipe: Equipe) -> EquipeDiretorioRead:
        return EquipeDiretorioRead(
            id=equipe.id,
            codigoInterno=equipe.codigo_interno,
            codigoReferencia=equipe.codigo_referencia,
            sequencialReferencia=equipe.sequencial_referencia,
            nome=equipe.nome,
            corIdentificacao=equipe.cor_identificacao,
            status=equipe.status,
            departamentoId=equipe.departamento_id,
            membroIds=self.repository.listar_membro_ids(db, equipe.id),
        )

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _ensure_nome_disponivel(
        self, db: Session, empresa_id: str, nome_normalizado: str, *, exclude_id: str | None = None
    ) -> None:
        existente = self.repository.get_by_nome_normalizado(
            db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
        )
        if existente is not None and existente.id != exclude_id:
            if existente.status == STATUS_ARQUIVADO:
                raise EquipeArquivadaConflictError(
                    "nome já pertence a uma equipe arquivada", equipe_arquivada_id=existente.id
                )
            raise EquipeConflictError("nome já cadastrado para esta Empresa")

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        """Departamento precisa existir, ser da mesma empresa e **não estar arquivado**.
        Vínculo histórico com departamento arquivado é preservado (esta checagem só roda
        quando o vínculo está sendo criado ou alterado)."""
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise EquipeDepartamentoInvalidoError("Departamento não encontrado nesta empresa")
        if departamento.status == STATUS_ARQUIVADO:
            raise EquipeDepartamentoInvalidoError(
                "Departamento arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _ensure_usuario_valido_para_vinculo(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise EquipeMembroInvalidoError("Usuário não encontrado nesta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO_PARA_VINCULO:
            raise EquipeMembroInvalidoError(
                f"Usuário com status '{usuario.status}' não pode receber novo vínculo de equipe"
            )

    def _publish_event(
        self,
        db: Session,
        equipe: Equipe,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": equipe.empresa_id,
            "equipe_id": equipe.id,
            "codigo_referencia": equipe.codigo_referencia,
            "timestamp": timestamp.isoformat(),
            "status": equipe.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=equipe.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=equipe.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    def _publish_event_membro(
        self,
        db: Session,
        equipe: Equipe,
        tipo: DomainEventType,
        membro_usuario_id: str,
        actor_usuario_id: str | None,
        occurred_at: datetime,
    ) -> None:
        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=equipe.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=equipe.id,
            usuario_id=actor_usuario_id,
            payload={
                "empresa_id": equipe.empresa_id,
                "equipe_id": equipe.id,
                "codigo_referencia": equipe.codigo_referencia,
                "membro_usuario_id": membro_usuario_id,
                "timestamp": occurred_at.isoformat(),
            },
            occurred_at=occurred_at,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
