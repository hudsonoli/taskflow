from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.peca import Peca
from app.repositories.categoria_peca_repository import CategoriaPecaRepository
from app.repositories.peca_repository import PecaRepository
from app.schemas.peca import PecaCreate, PecaDiretorioRead, PecaRead, PecaUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "peca"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"


class PecaNotFoundError(ValueError):
    pass


class PecaCategoriaInvalidaError(ValueError):
    """Categoria inexistente, de outra Empresa, ou arquivada num vínculo NOVO — histórico já
    salvo (Peça já apontando pra uma Categoria que foi arquivada depois) nunca cai aqui, só
    tentativa de setar/trocar para uma categoria_id inválida."""

    pass


class PecaInvalidTransitionError(ValueError):
    pass


class PecaService:
    def __init__(
        self,
        repository: PecaRepository | None = None,
        categoria_repository: CategoriaPecaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or PecaRepository()
        self.categoria_repository = categoria_repository or CategoriaPecaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_peca(
        self,
        db: Session,
        data: PecaCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None,
    ) -> Peca:
        categoria_id = str(data.categoria_id) if data.categoria_id else None
        if categoria_id is not None:
            self._ensure_categoria_valida(db, empresa_id=empresa_id, categoria_id=categoria_id)

        now = agora_utc()
        try:
            peca = Peca(
                id=str(uuid4()),
                empresa_id=empresa_id,
                categoria_id=categoria_id,
                nome=data.nome,
                codigo_legado=None,
                tempo_estimado_minutos=data.tempo_estimado_minutos,
                tempo_medio_minutos=data.tempo_medio_minutos,
                tempo_calculado_execucao_minutos=None,
                valor_tabela_centavos=data.valor_tabela_centavos,
                sindicato_ativo=data.sindicato_ativo,
                valor_sindicato_criacao_centavos=data.valor_sindicato_criacao_centavos,
                valor_sindicato_adaptacao_centavos=data.valor_sindicato_adaptacao_centavos,
                valor_sindicato_finalizacao_centavos=data.valor_sindicato_finalizacao_centavos,
                briefing_padrao=data.briefing_padrao,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, peca)
            self._publish_event(db, peca, DomainEventType.PECA_CRIADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(peca)
            return peca
        except Exception:
            db.rollback()
            raise

    def criar_peca_importada(
        self,
        db: Session,
        *,
        empresa_id: str,
        codigo_legado: str,
        nome: str,
        tempo_estimado_minutos: int | None,
        tempo_medio_minutos: int | None,
        valor_tabela_centavos: int | None,
        sindicato_ativo: bool,
        valor_sindicato_criacao_centavos: int | None,
        valor_sindicato_adaptacao_centavos: int | None,
        valor_sindicato_finalizacao_centavos: int | None,
        briefing_padrao: str,
    ) -> Peca:
        """Único caminho de criação com `codigo_legado` — usado só por
        app/cli/importar_pecas.py. Sem `categoria_id` de propósito: o catálogo importado não
        traz categoria (ver docstring do import), sempre nasce `None`. Sem `actor_usuario_id`
        real: roda fora de uma sessão HTTP autenticada, mesmo padrão de
        TipoTarefaService.create_tipo_tarefa quando chamada pelo seed.
        """
        now = agora_utc()
        try:
            peca = Peca(
                id=str(uuid4()),
                empresa_id=empresa_id,
                categoria_id=None,
                nome=nome,
                codigo_legado=codigo_legado,
                tempo_estimado_minutos=tempo_estimado_minutos,
                tempo_medio_minutos=tempo_medio_minutos,
                tempo_calculado_execucao_minutos=None,
                valor_tabela_centavos=valor_tabela_centavos,
                sindicato_ativo=sindicato_ativo,
                valor_sindicato_criacao_centavos=valor_sindicato_criacao_centavos,
                valor_sindicato_adaptacao_centavos=valor_sindicato_adaptacao_centavos,
                valor_sindicato_finalizacao_centavos=valor_sindicato_finalizacao_centavos,
                briefing_padrao=briefing_padrao,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, peca)
            self._publish_event(db, peca, DomainEventType.PECA_CRIADA, None, occurred_at=now)
            db.commit()
            db.refresh(peca)
            return peca
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_pecas(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        categoria_id: str | None = None,
        search: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Peca]:
        return self.repository.list(
            db,
            empresa_id=empresa_id,
            status=status,
            categoria_id=categoria_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_peca(self, db: Session, peca_id: str) -> Peca:
        peca = self.repository.get_by_id(db, peca_id)
        if peca is None:
            raise PecaNotFoundError("Peça não encontrada")
        return peca

    def get_by_codigo_legado(self, db: Session, *, empresa_id: str, codigo_legado: str) -> Peca | None:
        """Usado só por app/cli/importar_pecas.py, pra decidir criar vs. ignorar."""
        return self.repository.get_by_codigo_legado(db, empresa_id=empresa_id, codigo_legado=codigo_legado)

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Peca]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_peca(
        self,
        db: Session,
        peca_id: str,
        data: PecaUpdate,
        *,
        actor_usuario_id: str,
    ) -> Peca:
        try:
            peca = self.get_peca(db, peca_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "categoria_id" in updates:
                novo_categoria_id = str(updates["categoria_id"]) if updates["categoria_id"] else None
                if novo_categoria_id != peca.categoria_id:
                    if novo_categoria_id is not None:
                        self._ensure_categoria_valida(
                            db, empresa_id=peca.empresa_id, categoria_id=novo_categoria_id
                        )
                    peca.categoria_id = novo_categoria_id
                    changed_fields.append("categoriaId")

            for campo, alias in (
                ("nome", "nome"),
                ("tempo_estimado_minutos", "tempoEstimadoMinutos"),
                ("tempo_medio_minutos", "tempoMedioMinutos"),
                ("valor_tabela_centavos", "valorTabelaCentavos"),
                ("sindicato_ativo", "sindicatoAtivo"),
                ("valor_sindicato_criacao_centavos", "valorSindicatoCriacaoCentavos"),
                ("valor_sindicato_adaptacao_centavos", "valorSindicatoAdaptacaoCentavos"),
                ("valor_sindicato_finalizacao_centavos", "valorSindicatoFinalizacaoCentavos"),
                ("briefing_padrao", "briefingPadrao"),
            ):
                if campo in updates and updates[campo] != getattr(peca, campo):
                    setattr(peca, campo, updates[campo])
                    changed_fields.append(alias)

            if "status" in updates and updates["status"] != peca.status:
                if peca.status == STATUS_ARQUIVADO:
                    raise PecaInvalidTransitionError("Peça arquivada deve ser restaurada antes de mudar de status")
                peca.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                peca.updated_at = now
                self.repository.update(db, peca)
                self._publish_event(
                    db,
                    peca,
                    DomainEventType.PECA_ALTERADA,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(peca)
            return peca
        except IntegrityError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    def arquivar_peca(
        self,
        db: Session,
        peca_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> Peca:
        try:
            peca = self.get_peca(db, peca_id)
            if peca.status == STATUS_ARQUIVADO:
                raise PecaInvalidTransitionError("Peça já está arquivada")

            now = agora_utc()
            peca.status_anterior_arquivamento = peca.status
            peca.status = STATUS_ARQUIVADO
            peca.updated_at = now
            peca.arquivado_at = now
            peca.arquivado_por_usuario_id = actor_usuario_id
            peca.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, peca)
            self._publish_event(db, peca, DomainEventType.PECA_ARQUIVADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(peca)
            return peca
        except Exception:
            db.rollback()
            raise

    def restaurar_peca(
        self,
        db: Session,
        peca_id: str,
        *,
        actor_usuario_id: str,
    ) -> Peca:
        """Restaura sempre para `ativo` — mesmo comportamento de TipoTarefa/WorkflowModelo."""
        try:
            peca = self.get_peca(db, peca_id)
            if peca.status != STATUS_ARQUIVADO:
                raise PecaInvalidTransitionError("Somente Peça arquivada pode ser restaurada")

            now = agora_utc()
            peca.status = STATUS_ATIVO
            peca.updated_at = now
            peca.restaurado_at = now
            peca.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, peca)
            self._publish_event(db, peca, DomainEventType.PECA_RESTAURADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(peca)
            return peca
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, peca: Peca) -> PecaRead:
        nomes = self._resolver_nomes_categoria(db, [peca])
        return self._montar_read(peca, nomes)

    def to_read_lote(self, db: Session, pecas: list[Peca]) -> list[PecaRead]:
        """Resolve `categoriaNome` em lote — uma query pra todas as categorias distintas da
        página, não uma por Peça (evita N+1 numa listagem de centenas de itens)."""
        nomes = self._resolver_nomes_categoria(db, pecas)
        return [self._montar_read(peca, nomes) for peca in pecas]

    def to_diretorio_read(self, peca: Peca) -> PecaDiretorioRead:
        return PecaDiretorioRead(id=peca.id, nome=peca.nome)

    def _resolver_nomes_categoria(self, db: Session, pecas: list[Peca]) -> dict[str, str]:
        ids = list({peca.categoria_id for peca in pecas if peca.categoria_id is not None})
        categorias = self.categoria_repository.list_by_ids(db, ids=ids)
        return {categoria.id: categoria.nome for categoria in categorias}

    def _montar_read(self, peca: Peca, nomes_categoria: dict[str, str]) -> PecaRead:
        return PecaRead(
            id=peca.id,
            empresaId=peca.empresa_id,
            nome=peca.nome,
            categoriaId=peca.categoria_id,
            categoriaNome=nomes_categoria.get(peca.categoria_id) if peca.categoria_id else None,
            tempoEstimadoMinutos=peca.tempo_estimado_minutos,
            tempoMedioMinutos=peca.tempo_medio_minutos,
            tempoCalculadoExecucaoMinutos=peca.tempo_calculado_execucao_minutos,
            valorTabelaCentavos=peca.valor_tabela_centavos,
            sindicatoAtivo=peca.sindicato_ativo,
            valorSindicatoCriacaoCentavos=peca.valor_sindicato_criacao_centavos,
            valorSindicatoAdaptacaoCentavos=peca.valor_sindicato_adaptacao_centavos,
            valorSindicatoFinalizacaoCentavos=peca.valor_sindicato_finalizacao_centavos,
            briefingPadrao=peca.briefing_padrao,
            status=peca.status,
            createdAt=peca.created_at,
            updatedAt=peca.updated_at,
            arquivadoAt=peca.arquivado_at,
            arquivadoPorUsuarioId=peca.arquivado_por_usuario_id,
            motivoArquivamento=peca.motivo_arquivamento,
            restauradoAt=peca.restaurado_at,
            restauradoPorUsuarioId=peca.restaurado_por_usuario_id,
        )

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _ensure_categoria_valida(self, db: Session, *, empresa_id: str, categoria_id: str) -> None:
        categoria = self.categoria_repository.get_by_id(db, categoria_id)
        if categoria is None or categoria.empresa_id != empresa_id:
            raise PecaCategoriaInvalidaError("Categoria inválida para esta Empresa")
        if categoria.status == "arquivado":
            raise PecaCategoriaInvalidaError("Categoria arquivada não aceita novo vínculo")

    def _publish_event(
        self,
        db: Session,
        peca: Peca,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        # Payload enxuto de propósito — sem valores financeiros (ver instrução da Fase 2G.4):
        # quem precisa do valor exato consulta GET /pecas/{id}, com RBAC completo, não o
        # evento (auditoria tem RBAC próprio, mais frouxo).
        payload = {
            "empresa_id": peca.empresa_id,
            "peca_id": peca.id,
            "timestamp": timestamp.isoformat(),
            "status": peca.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=peca.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=peca.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )
