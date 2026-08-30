from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.cliente import Cliente
from app.models.departamento import Departamento
from app.models.sla_regra import SlaRegra
from app.repositories.sla_regra_repository import SlaRegraRepository
from app.schemas.sla_regra import SlaRegraCreate, SlaRegraRead, SlaRegraUpdate
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "sla_regra"

STATUS_ATIVO = "ativo"
STATUS_INATIVO = "inativo"
STATUS_ARQUIVADO = "arquivado"


class SlaRegraNotFoundError(ValueError):
    pass


class SlaRegraConflictError(ValueError):
    pass


class SlaRegraArquivadaConflictError(ValueError):
    """Nome já pertence a uma Regra de SLA arquivada — a UI oferece restaurar em vez de
    mostrar erro de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, sla_regra_arquivada_id: str) -> None:
        super().__init__(message)
        self.sla_regra_arquivada_id = sla_regra_arquivada_id


class SlaRegraInvalidTransitionError(ValueError):
    pass


class SlaRegraClienteInvalidoError(ValueError):
    """Cliente inexistente, de outra Empresa, ou arquivado (vínculo novo)."""


class SlaRegraDepartamentoInvalidoError(ValueError):
    """Departamento inexistente, de outra Empresa, ou arquivado (vínculo novo)."""


class SlaRegraService:
    def __init__(
        self,
        repository: SlaRegraRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or SlaRegraRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_sla_regra(
        self,
        db: Session,
        data: SlaRegraCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> SlaRegra:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)
        departamento_id = str(data.departamento_id) if data.departamento_id else None
        cliente_id = str(data.cliente_id) if data.cliente_id else None

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)
            if departamento_id is not None:
                self._ensure_departamento_valido(db, empresa_id, departamento_id)
            if cliente_id is not None:
                self._ensure_cliente_valido(db, empresa_id, cliente_id)

            sla_regra = SlaRegra(
                id=str(uuid4()),
                empresa_id=empresa_id,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                descricao=data.descricao,
                prioridade_alvo=data.prioridade_alvo,
                departamento_id=departamento_id,
                cliente_id=cliente_id,
                prioridade_regra=data.prioridade_regra,
                prazo_primeira_resposta_quantidade=data.prazo_primeira_resposta_quantidade,
                prazo_primeira_resposta_unidade=data.prazo_primeira_resposta_unidade,
                prazo_resolucao_quantidade=data.prazo_resolucao_quantidade,
                prazo_resolucao_unidade=data.prazo_resolucao_unidade,
                considerar_apenas_expediente=data.considerar_apenas_expediente,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, sla_regra)
            self._publish_event(db, sla_regra, DomainEventType.SLA_REGRA_CRIADA, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(sla_regra)
            return sla_regra
        except IntegrityError:
            # Corrida: dois inserts concorrentes passaram pelo check antes de qualquer commit.
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            )
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise SlaRegraArquivadaConflictError(
                    "Já existe uma Regra de SLA arquivada com este nome",
                    sla_regra_arquivada_id=existente.id,
                ) from None
            raise SlaRegraConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_sla_regras(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SlaRegra]:
        return self.repository.list(
            db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset
        )

    def get_sla_regra(self, db: Session, sla_regra_id: str) -> SlaRegra:
        sla_regra = self.repository.get_by_id(db, sla_regra_id)
        if sla_regra is None:
            raise SlaRegraNotFoundError("Regra de SLA não encontrada")
        return sla_regra

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_sla_regra(
        self,
        db: Session,
        sla_regra_id: str,
        data: SlaRegraUpdate,
        *,
        actor_usuario_id: str,
    ) -> SlaRegra:
        try:
            sla_regra = self.get_sla_regra(db, sla_regra_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != sla_regra.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != sla_regra.nome_normalizado:
                    self._ensure_nome_disponivel(
                        db, sla_regra.empresa_id, nome_normalizado, exclude_id=sla_regra.id
                    )
                sla_regra.nome = updates["nome"]
                sla_regra.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "descricao" in updates and updates["descricao"] != sla_regra.descricao:
                sla_regra.descricao = updates["descricao"]
                changed_fields.append("descricao")

            if "prioridade_alvo" in updates and updates["prioridade_alvo"] != sla_regra.prioridade_alvo:
                sla_regra.prioridade_alvo = updates["prioridade_alvo"]
                changed_fields.append("prioridadeAlvo")

            # Referência só é revalidada quando o valor MUDA — preserva histórico se a
            # entidade já vinculada ficar inativa/arquivada depois (ver docstring do model e
            # relatório 2G.6A, item 14/32). Mesmo padrão de ProjetoService.update_projeto.
            if "departamento_id" in updates:
                novo_departamento_id = str(updates["departamento_id"]) if updates["departamento_id"] else None
                if novo_departamento_id != sla_regra.departamento_id:
                    if novo_departamento_id is not None:
                        self._ensure_departamento_valido(db, sla_regra.empresa_id, novo_departamento_id)
                    sla_regra.departamento_id = novo_departamento_id
                    changed_fields.append("departamentoId")

            if "cliente_id" in updates:
                novo_cliente_id = str(updates["cliente_id"]) if updates["cliente_id"] else None
                if novo_cliente_id != sla_regra.cliente_id:
                    if novo_cliente_id is not None:
                        self._ensure_cliente_valido(db, sla_regra.empresa_id, novo_cliente_id)
                    sla_regra.cliente_id = novo_cliente_id
                    changed_fields.append("clienteId")

            if "prioridade_regra" in updates and updates["prioridade_regra"] != sla_regra.prioridade_regra:
                sla_regra.prioridade_regra = updates["prioridade_regra"]
                changed_fields.append("prioridadeRegra")

            if (
                "prazo_primeira_resposta_quantidade" in updates
                and updates["prazo_primeira_resposta_quantidade"] != sla_regra.prazo_primeira_resposta_quantidade
            ):
                sla_regra.prazo_primeira_resposta_quantidade = updates["prazo_primeira_resposta_quantidade"]
                changed_fields.append("prazoPrimeiraRespostaQuantidade")

            if (
                "prazo_primeira_resposta_unidade" in updates
                and updates["prazo_primeira_resposta_unidade"] != sla_regra.prazo_primeira_resposta_unidade
            ):
                sla_regra.prazo_primeira_resposta_unidade = updates["prazo_primeira_resposta_unidade"]
                changed_fields.append("prazoPrimeiraRespostaUnidade")

            if (
                "prazo_resolucao_quantidade" in updates
                and updates["prazo_resolucao_quantidade"] != sla_regra.prazo_resolucao_quantidade
            ):
                sla_regra.prazo_resolucao_quantidade = updates["prazo_resolucao_quantidade"]
                changed_fields.append("prazoResolucaoQuantidade")

            if (
                "prazo_resolucao_unidade" in updates
                and updates["prazo_resolucao_unidade"] != sla_regra.prazo_resolucao_unidade
            ):
                sla_regra.prazo_resolucao_unidade = updates["prazo_resolucao_unidade"]
                changed_fields.append("prazoResolucaoUnidade")

            if (
                "considerar_apenas_expediente" in updates
                and updates["considerar_apenas_expediente"] != sla_regra.considerar_apenas_expediente
            ):
                sla_regra.considerar_apenas_expediente = updates["considerar_apenas_expediente"]
                changed_fields.append("considerarApenasExpediente")

            if "status" in updates and updates["status"] is not None and updates["status"] != sla_regra.status:
                if sla_regra.status == STATUS_ARQUIVADO:
                    raise SlaRegraInvalidTransitionError(
                        "Regra de SLA arquivada deve ser restaurada antes de mudar de status"
                    )
                sla_regra.status = updates["status"]
                changed_fields.append("status")

            if changed_fields:
                sla_regra.updated_at = now
                self.repository.update(db, sla_regra)
                self._publish_event(
                    db,
                    sla_regra,
                    DomainEventType.SLA_REGRA_ALTERADA,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(sla_regra)
            return sla_regra
        except IntegrityError:
            db.rollback()
            raise SlaRegraConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_sla_regra(
        self,
        db: Session,
        sla_regra_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> SlaRegra:
        """Arquivar não apaga nada — só passa a ficar fora da futura resolução automática
        (2G.6C considera só `status='ativo'`). Demanda que já resolveu esta regra antes
        (2G.6D) preserva o snapshot — arquivar não altera histórico já gravado."""
        try:
            sla_regra = self.get_sla_regra(db, sla_regra_id)
            if sla_regra.status == STATUS_ARQUIVADO:
                raise SlaRegraInvalidTransitionError("Regra de SLA já está arquivada")

            now = agora_utc()
            sla_regra.status_anterior_arquivamento = sla_regra.status
            sla_regra.status = STATUS_ARQUIVADO
            sla_regra.updated_at = now
            sla_regra.arquivado_at = now
            sla_regra.arquivado_por_usuario_id = actor_usuario_id
            sla_regra.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, sla_regra)
            self._publish_event(
                db, sla_regra, DomainEventType.SLA_REGRA_ARQUIVADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(sla_regra)
            return sla_regra
        except Exception:
            db.rollback()
            raise

    def restaurar_sla_regra(
        self,
        db: Session,
        sla_regra_id: str,
        *,
        actor_usuario_id: str,
    ) -> SlaRegra:
        """Restaura sempre para `ativo` — mesmo comportamento de TipoTarefa/WorkflowModelo/
        Departamento. Não precisa checar conflito de nome: a unicidade vale entre todos os
        status."""
        try:
            sla_regra = self.get_sla_regra(db, sla_regra_id)
            if sla_regra.status != STATUS_ARQUIVADO:
                raise SlaRegraInvalidTransitionError("Somente Regra de SLA arquivada pode ser restaurada")

            now = agora_utc()
            sla_regra.status = STATUS_ATIVO
            sla_regra.updated_at = now
            sla_regra.restaurado_at = now
            sla_regra.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, sla_regra)
            self._publish_event(
                db, sla_regra, DomainEventType.SLA_REGRA_RESTAURADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(sla_regra)
            return sla_regra
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, sla_regra: SlaRegra) -> SlaRegraRead:
        return SlaRegraRead(
            id=sla_regra.id,
            empresaId=sla_regra.empresa_id,
            nome=sla_regra.nome,
            descricao=sla_regra.descricao,
            prioridadeAlvo=sla_regra.prioridade_alvo,
            departamentoId=sla_regra.departamento_id,
            clienteId=sla_regra.cliente_id,
            prioridadeRegra=sla_regra.prioridade_regra,
            prazoPrimeiraRespostaQuantidade=sla_regra.prazo_primeira_resposta_quantidade,
            prazoPrimeiraRespostaUnidade=sla_regra.prazo_primeira_resposta_unidade,
            prazoResolucaoQuantidade=sla_regra.prazo_resolucao_quantidade,
            prazoResolucaoUnidade=sla_regra.prazo_resolucao_unidade,
            considerarApenasExpediente=sla_regra.considerar_apenas_expediente,
            status=sla_regra.status,
            createdAt=sla_regra.created_at,
            updatedAt=sla_regra.updated_at,
            arquivadoAt=sla_regra.arquivado_at,
            arquivadoPorUsuarioId=sla_regra.arquivado_por_usuario_id,
            motivoArquivamento=sla_regra.motivo_arquivamento,
            restauradoAt=sla_regra.restaurado_at,
            restauradoPorUsuarioId=sla_regra.restaurado_por_usuario_id,
            statusAnteriorArquivamento=sla_regra.status_anterior_arquivamento,
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
                raise SlaRegraArquivadaConflictError(
                    "nome já pertence a uma Regra de SLA arquivada",
                    sla_regra_arquivada_id=existente.id,
                )
            raise SlaRegraConflictError("nome já cadastrado para esta Empresa")

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        departamento = db.get(Departamento, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise SlaRegraDepartamentoInvalidoError("Departamento não encontrado nesta Empresa")
        if departamento.status == STATUS_ARQUIVADO:
            raise SlaRegraDepartamentoInvalidoError(
                "Departamento arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _ensure_cliente_valido(self, db: Session, empresa_id: str, cliente_id: str) -> None:
        cliente = db.get(Cliente, cliente_id)
        # Cross-tenant é tratado como "não encontrado" — não vaza existência.
        if cliente is None or cliente.empresa_id != empresa_id:
            raise SlaRegraClienteInvalidoError("Cliente não encontrado nesta Empresa")
        if cliente.status == STATUS_ARQUIVADO:
            raise SlaRegraClienteInvalidoError("Cliente arquivado não aceita novos vínculos — restaure-o antes")

    def _publish_event(
        self,
        db: Session,
        sla_regra: SlaRegra,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": sla_regra.empresa_id,
            "sla_regra_id": sla_regra.id,
            "timestamp": timestamp.isoformat(),
            "status": sla_regra.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=sla_regra.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=sla_regra.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
