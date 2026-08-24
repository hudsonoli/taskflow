from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.modelo_campanha import ModeloCampanha, ModeloCampanhaItem
from app.models.peca import Peca
from app.models.tipo_tarefa import TipoTarefa
from app.models.usuario import Usuario
from app.models.workflow_modelo import WorkflowModelo
from app.repositories.modelo_campanha_repository import ModeloCampanhaRepository
from app.schemas.modelo_campanha import (
    ModeloCampanhaCreate,
    ModeloCampanhaDiretorioRead,
    ModeloCampanhaItemInput,
    ModeloCampanhaItemRead,
    ModeloCampanhaRead,
    ModeloCampanhaUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "modelo_campanha"

STATUS_ATIVO = "ativo"
STATUS_ARQUIVADO = "arquivado"

# Usuário: reproduz STATUS_USUARIO_INVALIDO de ProjetoService/DemandaService — arquivado,
# inativo e bloqueado recusam vínculo NOVO; só ativo aceita.
_STATUS_USUARIO_INVALIDO = {"arquivado", "inativo", "bloqueado"}


class ModeloCampanhaNotFoundError(ValueError):
    pass


class ModeloCampanhaConflictError(ValueError):
    pass


class ModeloCampanhaArquivadoConflictError(ValueError):
    """Nome já pertence a um Modelo arquivado — a UI oferece restaurar em vez de mostrar erro
    de duplicidade (ver docs/padrao-arquivamento.md)."""

    def __init__(self, message: str, *, modelo_campanha_arquivado_id: str) -> None:
        super().__init__(message)
        self.modelo_campanha_arquivado_id = modelo_campanha_arquivado_id


class ModeloCampanhaInvalidTransitionError(ValueError):
    pass


class ModeloCampanhaReferenciaInvalidaError(ValueError):
    """Peça/TipoTarefa/Workflow/Usuário/Departamento inexistente, de outra Empresa, ou cujo
    status não aceita vínculo NOVO. Nunca levantado pra uma referência que já existia sem
    mudança no item — ver ModeloCampanhaService._preparar_itens."""

    pass


class ModeloCampanhaService:
    def __init__(
        self,
        repository: ModeloCampanhaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ModeloCampanhaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_modelo(
        self,
        db: Session,
        data: ModeloCampanhaCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> ModeloCampanha:
        now = agora_utc()
        nome_normalizado = self._normalizar_nome(data.nome)

        try:
            self._ensure_nome_disponivel(db, empresa_id, nome_normalizado)

            # Todo item de criação é NOVO — nenhuma referência histórica a preservar.
            itens_objetos = self._preparar_itens(db, empresa_id=empresa_id, itens_novos=data.itens, itens_atuais=[])

            modelo = ModeloCampanha(
                id=str(uuid4()),
                empresa_id=empresa_id,
                nome=data.nome,
                nome_normalizado=nome_normalizado,
                descricao=data.descricao,
                status=STATUS_ATIVO,
                created_at=now,
                updated_at=now,
            )
            self.repository.create(db, modelo)
            for item in itens_objetos:
                item.modelo_campanha_id = modelo.id
            self.repository.replace_itens(db, modelo_campanha_id=modelo.id, itens=itens_objetos)

            self._publish_event(db, modelo, DomainEventType.MODELO_CAMPANHA_CRIADO, actor_usuario_id, occurred_at=now)
            db.commit()
            db.refresh(modelo)
            return modelo
        except IntegrityError:
            db.rollback()
            existente = self.repository.get_by_nome_normalizado(
                db, empresa_id=empresa_id, nome_normalizado=nome_normalizado
            )
            if existente is not None and existente.status == STATUS_ARQUIVADO:
                raise ModeloCampanhaArquivadoConflictError(
                    "Já existe um Modelo de Campanha arquivado com este nome",
                    modelo_campanha_arquivado_id=existente.id,
                ) from None
            raise ModeloCampanhaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def list_modelos(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModeloCampanha]:
        return self.repository.list(db, empresa_id=empresa_id, status=status, search=search, limit=limit, offset=offset)

    def get_modelo(self, db: Session, modelo_id: str) -> ModeloCampanha:
        modelo = self.repository.get_by_id(db, modelo_id)
        if modelo is None:
            raise ModeloCampanhaNotFoundError("Modelo de Campanha não encontrado")
        return modelo

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[ModeloCampanha]:
        return self.repository.list_diretorio(db, empresa_id=empresa_id)

    # ----------------------------------------------------------------------------------
    # Alteração e ciclo de vida
    # ----------------------------------------------------------------------------------

    def update_modelo(
        self,
        db: Session,
        modelo_id: str,
        data: ModeloCampanhaUpdate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> ModeloCampanha:
        try:
            modelo = self.get_modelo(db, modelo_id)
            changed_fields: list[str] = []
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            now = agora_utc()

            if "nome" in updates and updates["nome"] != modelo.nome:
                nome_normalizado = self._normalizar_nome(updates["nome"])
                if nome_normalizado != modelo.nome_normalizado:
                    self._ensure_nome_disponivel(db, modelo.empresa_id, nome_normalizado, exclude_id=modelo.id)
                modelo.nome = updates["nome"]
                modelo.nome_normalizado = nome_normalizado
                changed_fields.append("nome")

            if "descricao" in updates and updates["descricao"] != modelo.descricao:
                modelo.descricao = updates["descricao"]
                changed_fields.append("descricao")

            if "status" in updates and updates["status"] is not None and updates["status"] != modelo.status:
                if modelo.status == STATUS_ARQUIVADO:
                    raise ModeloCampanhaInvalidTransitionError(
                        "Modelo de Campanha arquivado deve ser restaurado antes de mudar de status"
                    )
                modelo.status = updates["status"]
                changed_fields.append("status")

            if data.itens is not None:
                itens_atuais = self.repository.list_itens(db, modelo.id)
                itens_objetos = self._preparar_itens(
                    db, empresa_id=modelo.empresa_id, itens_novos=data.itens, itens_atuais=itens_atuais
                )
                for item in itens_objetos:
                    item.modelo_campanha_id = modelo.id
                self.repository.replace_itens(db, modelo_campanha_id=modelo.id, itens=itens_objetos)
                changed_fields.append("itens")

            if changed_fields:
                modelo.updated_at = now
                self.repository.update(db, modelo)
                self._publish_event(
                    db,
                    modelo,
                    DomainEventType.MODELO_CAMPANHA_ALTERADO,
                    actor_usuario_id,
                    extra_payload={"camposAlterados": changed_fields},
                    occurred_at=now,
                )

            db.commit()
            db.refresh(modelo)
            return modelo
        except IntegrityError:
            db.rollback()
            raise ModeloCampanhaConflictError("nome já cadastrado para esta Empresa") from None
        except Exception:
            db.rollback()
            raise

    def arquivar_modelo(
        self,
        db: Session,
        modelo_id: str,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str,
    ) -> ModeloCampanha:
        try:
            modelo = self.get_modelo(db, modelo_id)
            if modelo.status == STATUS_ARQUIVADO:
                raise ModeloCampanhaInvalidTransitionError("Modelo de Campanha já está arquivado")

            now = agora_utc()
            modelo.status_anterior_arquivamento = modelo.status
            modelo.status = STATUS_ARQUIVADO
            modelo.updated_at = now
            modelo.arquivado_at = now
            modelo.arquivado_por_usuario_id = actor_usuario_id
            modelo.motivo_arquivamento = motivo_arquivamento
            self.repository.update(db, modelo)
            self._publish_event(
                db, modelo, DomainEventType.MODELO_CAMPANHA_ARQUIVADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(modelo)
            return modelo
        except Exception:
            db.rollback()
            raise

    def restaurar_modelo(
        self,
        db: Session,
        modelo_id: str,
        *,
        actor_usuario_id: str,
    ) -> ModeloCampanha:
        """Restaura sempre para `ativo` — mesmo comportamento de TipoTarefa/WorkflowModelo/Peça
        (não tenta reconstruir o status anterior a arquivar, mesmo havendo a coluna
        `status_anterior_arquivamento` — ela é só registro histórico, não fonte de restauração)."""
        try:
            modelo = self.get_modelo(db, modelo_id)
            if modelo.status != STATUS_ARQUIVADO:
                raise ModeloCampanhaInvalidTransitionError("Somente Modelo de Campanha arquivado pode ser restaurado")

            now = agora_utc()
            modelo.status = STATUS_ATIVO
            modelo.updated_at = now
            modelo.restaurado_at = now
            modelo.restaurado_por_usuario_id = actor_usuario_id
            self.repository.update(db, modelo)
            self._publish_event(
                db, modelo, DomainEventType.MODELO_CAMPANHA_RESTAURADO, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(modelo)
            return modelo
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, modelo: ModeloCampanha) -> ModeloCampanhaRead:
        itens = self.repository.list_itens(db, modelo.id)
        pecas, tipos, workflows, usuarios, departamentos = self._resolver_nomes_itens(db, itens)
        return ModeloCampanhaRead(
            id=modelo.id,
            empresaId=modelo.empresa_id,
            nome=modelo.nome,
            descricao=modelo.descricao,
            status=modelo.status,
            itens=[
                self._montar_item_read(item, pecas, tipos, workflows, usuarios, departamentos) for item in itens
            ],
            createdAt=modelo.created_at,
            updatedAt=modelo.updated_at,
            arquivadoAt=modelo.arquivado_at,
            arquivadoPorUsuarioId=modelo.arquivado_por_usuario_id,
            motivoArquivamento=modelo.motivo_arquivamento,
            restauradoAt=modelo.restaurado_at,
            restauradoPorUsuarioId=modelo.restaurado_por_usuario_id,
        )

    def to_diretorio_read(self, modelo: ModeloCampanha) -> ModeloCampanhaDiretorioRead:
        return ModeloCampanhaDiretorioRead(id=modelo.id, nome=modelo.nome)

    def _resolver_nomes_itens(
        self, db: Session, itens: list[ModeloCampanhaItem]
    ) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
        """Resolve os nomes de todas as referências dos itens em lote — uma query por tipo de
        entidade, nunca uma por item (evita N+1)."""

        def _mapa(model_cls, ids: set[str]) -> dict[str, str]:
            if not ids:
                return {}
            linhas = db.scalars(select(model_cls).where(model_cls.id.in_(ids))).all()
            return {linha.id: linha.nome for linha in linhas}

        return (
            _mapa(Peca, {item.peca_id for item in itens if item.peca_id}),
            _mapa(TipoTarefa, {item.tipo_tarefa_id for item in itens if item.tipo_tarefa_id}),
            _mapa(WorkflowModelo, {item.workflow_modelo_id for item in itens if item.workflow_modelo_id}),
            _mapa(Usuario, {item.responsavel_usuario_id for item in itens if item.responsavel_usuario_id}),
            _mapa(
                Departamento,
                {item.responsavel_departamento_id for item in itens if item.responsavel_departamento_id},
            ),
        )

    def _montar_item_read(
        self,
        item: ModeloCampanhaItem,
        pecas: dict[str, str],
        tipos: dict[str, str],
        workflows: dict[str, str],
        usuarios: dict[str, str],
        departamentos: dict[str, str],
    ) -> ModeloCampanhaItemRead:
        return ModeloCampanhaItemRead(
            id=item.id,
            ordem=item.ordem,
            nome=item.nome,
            briefingPadrao=item.briefing_padrao,
            prioridadePadrao=item.prioridade_padrao,
            pecaId=item.peca_id,
            pecaNome=pecas.get(item.peca_id) if item.peca_id else None,
            tipoTarefaId=item.tipo_tarefa_id,
            tipoTarefaNome=tipos.get(item.tipo_tarefa_id) if item.tipo_tarefa_id else None,
            workflowModeloId=item.workflow_modelo_id,
            workflowModeloNome=workflows.get(item.workflow_modelo_id) if item.workflow_modelo_id else None,
            responsavelUsuarioId=item.responsavel_usuario_id,
            responsavelUsuarioNome=usuarios.get(item.responsavel_usuario_id) if item.responsavel_usuario_id else None,
            responsavelDepartamentoId=item.responsavel_departamento_id,
            responsavelDepartamentoNome=(
                departamentos.get(item.responsavel_departamento_id) if item.responsavel_departamento_id else None
            ),
        )

    # ----------------------------------------------------------------------------------
    # Itens — preparação, com preservação de referência histórica
    # ----------------------------------------------------------------------------------

    def _preparar_itens(
        self,
        db: Session,
        *,
        empresa_id: str,
        itens_novos: list[ModeloCampanhaItemInput],
        itens_atuais: list[ModeloCampanhaItem],
    ) -> list[ModeloCampanhaItem]:
        """Valida e monta os objetos `ModeloCampanhaItem` prontos pro replace.

        Cada campo de referência (`pecaId`/`tipoTarefaId`/`workflowModeloId`/
        `responsavelUsuarioId`/`responsavelDepartamentoId`) só é validado como vínculo NOVO
        quando o valor MUDOU em relação ao item existente (casado por `id`) — se o item já
        existia e o campo não mudou, a referência é preservada mesmo que a entidade tenha
        sido arquivada/inativada depois (padrão consolidado na Fase 2G.4 pra
        Peça↔CategoriaPeca, replicado aqui pros 5 tipos de referência). Item sem `id`, ou com
        `id` que não bate com nenhum item de `itens_atuais` (escopado a ESTE Modelo — um id de
        outro Modelo, de outra Empresa, ou simplesmente inventado nunca aparece aí), é tratado
        como NOVO — toda referência presente é validada.

        Identidade do item: o `id` persistido SÓ é reaproveitado quando bate com um item
        existente deste mesmo Modelo (`existente is not None`). Em qualquer outro caso —
        inclusive um `id` sintaticamente válido mas de outro Modelo/Empresa/inexistente — um
        UUID novo é gerado aqui, no service, e o valor enviado pelo cliente é descartado. Isso
        é deliberado: `id` nunca atravessa Modelo/tenant, e nunca colide com a PK de uma linha
        que pertence a outro agregado (o `DELETE` do replace só atinge as linhas do Modelo
        atual — reaproveitar um `id` alheio geraria um `IntegrityError` de PK duplicada em vez
        de uma rejeição limpa).

        `ordem` nunca vem do cliente (não existe no schema de entrada) — é sempre
        `enumerate(itens_novos, start=1)`, determinístico e sem confiar em valor arbitrário.
        """
        existentes_por_id = {item.id: item for item in itens_atuais}
        now = agora_utc()
        objetos: list[ModeloCampanhaItem] = []

        for ordem, item_novo in enumerate(itens_novos, start=1):
            item_id_str = str(item_novo.id) if item_novo.id else None
            existente = existentes_por_id.get(item_id_str) if item_id_str else None

            peca_id = self._validar_campo_referencia(
                db,
                empresa_id=empresa_id,
                novo_valor=str(item_novo.peca_id) if item_novo.peca_id else None,
                valor_existente=existente.peca_id if existente else None,
                model_cls=Peca,
                nome_entidade="Peça",
                invalido=lambda entidade: entidade.status != STATUS_ATIVO,
            )
            tipo_tarefa_id = self._validar_campo_referencia(
                db,
                empresa_id=empresa_id,
                novo_valor=str(item_novo.tipo_tarefa_id) if item_novo.tipo_tarefa_id else None,
                valor_existente=existente.tipo_tarefa_id if existente else None,
                model_cls=TipoTarefa,
                nome_entidade="Tipo de Tarefa",
                invalido=lambda entidade: entidade.status != STATUS_ATIVO,
            )
            workflow_modelo_id = self._validar_campo_referencia(
                db,
                empresa_id=empresa_id,
                novo_valor=str(item_novo.workflow_modelo_id) if item_novo.workflow_modelo_id else None,
                valor_existente=existente.workflow_modelo_id if existente else None,
                model_cls=WorkflowModelo,
                nome_entidade="Modelo de Workflow",
                invalido=lambda entidade: entidade.status != STATUS_ATIVO,
            )
            responsavel_usuario_id = self._validar_campo_referencia(
                db,
                empresa_id=empresa_id,
                novo_valor=str(item_novo.responsavel_usuario_id) if item_novo.responsavel_usuario_id else None,
                valor_existente=existente.responsavel_usuario_id if existente else None,
                model_cls=Usuario,
                nome_entidade="Usuário responsável",
                invalido=lambda entidade: entidade.status in _STATUS_USUARIO_INVALIDO,
            )
            responsavel_departamento_id = self._validar_campo_referencia(
                db,
                empresa_id=empresa_id,
                novo_valor=(
                    str(item_novo.responsavel_departamento_id) if item_novo.responsavel_departamento_id else None
                ),
                valor_existente=existente.responsavel_departamento_id if existente else None,
                model_cls=Departamento,
                nome_entidade="Departamento responsável",
                invalido=lambda entidade: entidade.status == STATUS_ARQUIVADO,
            )

            objetos.append(
                ModeloCampanhaItem(
                    # Só reaproveita o `id` do cliente quando ele bate com um item existente
                    # DESTE Modelo (`existente is not None`) — nunca com base só no formato do
                    # UUID recebido. Ver docstring do método para o porquê.
                    id=existente.id if existente is not None else str(uuid4()),
                    modelo_campanha_id="",  # setado pelo chamador após criar/carregar o pai
                    ordem=ordem,
                    nome=item_novo.nome,
                    briefing_padrao=item_novo.briefing_padrao,
                    prioridade_padrao=item_novo.prioridade_padrao,
                    peca_id=peca_id,
                    tipo_tarefa_id=tipo_tarefa_id,
                    workflow_modelo_id=workflow_modelo_id,
                    responsavel_usuario_id=responsavel_usuario_id,
                    responsavel_departamento_id=responsavel_departamento_id,
                    created_at=now,
                    updated_at=now,
                )
            )

        return objetos

    def _validar_campo_referencia(
        self,
        db: Session,
        *,
        empresa_id: str,
        novo_valor: str | None,
        valor_existente: str | None,
        model_cls,
        nome_entidade: str,
        invalido,
    ) -> str | None:
        """Um campo de referência de um item. Preserva sem validar se o valor não mudou em
        relação ao item existente (histórico); valida como vínculo NOVO em qualquer outro
        caso (item novo, ou campo alterado — inclusive troca por outro id, ou remoção)."""
        if novo_valor == valor_existente:
            return novo_valor
        if novo_valor is None:
            return None

        entidade = db.get(model_cls, novo_valor)
        if entidade is None or entidade.empresa_id != empresa_id:
            raise ModeloCampanhaReferenciaInvalidaError(f"{nome_entidade} inválido(a) para esta Empresa")
        if invalido(entidade):
            raise ModeloCampanhaReferenciaInvalidaError(
                f"{nome_entidade} com status '{entidade.status}' não aceita vínculo novo"
            )
        return novo_valor

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
        existente = self.repository.get_by_nome_normalizado(db, empresa_id=empresa_id, nome_normalizado=nome_normalizado)
        if existente is not None and existente.id != exclude_id:
            if existente.status == STATUS_ARQUIVADO:
                raise ModeloCampanhaArquivadoConflictError(
                    "nome já pertence a um Modelo de Campanha arquivado",
                    modelo_campanha_arquivado_id=existente.id,
                )
            raise ModeloCampanhaConflictError("nome já cadastrado para esta Empresa")

    def _publish_event(
        self,
        db: Session,
        modelo: ModeloCampanha,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or agora_utc()
        # Payload enxuto — nunca serializa os itens (ver instrução da Fase 2G.5A).
        payload = {
            "empresa_id": modelo.empresa_id,
            "modelo_campanha_id": modelo.id,
            "timestamp": timestamp.isoformat(),
            "status": modelo.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=modelo.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=modelo.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        return nome.strip().lower()
