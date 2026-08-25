from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.modelo_campanha import ModeloCampanhaItem
from app.models.peca import Peca
from app.models.projeto import Projeto
from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem
from app.models.tipo_tarefa import TipoTarefa
from app.models.usuario import Usuario
from app.models.workflow_modelo import WorkflowModelo
from app.repositories.modelo_campanha_repository import ModeloCampanhaRepository
from app.repositories.projeto_modelo_campanha_repository import ProjetoModeloCampanhaRepository
from app.schemas.projeto_modelo_campanha import (
    ProjetoModeloCampanhaItemInput,
    ProjetoModeloCampanhaItemRead,
    ProjetoModeloCampanhaSnapshotRead,
    ProjetoModeloCampanhaUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "projeto"
STATUS_MODELO_ATIVO = "ativo"

# Mesma regra de ModeloCampanhaService/ProjetoService/DemandaService: arquivado, inativo e
# bloqueado recusam vínculo NOVO de Usuário; só ativo aceita.
_STATUS_USUARIO_INVALIDO = {"arquivado", "inativo", "bloqueado"}
_STATUS_DEPARTAMENTO_INVALIDO = "arquivado"


class ProjetoModeloCampanhaModeloInvalidoError(ValueError):
    """Modelo de Campanha inexistente, de outra Empresa, ou não ativo — o Modelo escolhido
    pra aplicar/reaplicar é, na prática, mais uma referência de payload do que uma entidade
    "buscada por id" (mesmo tratamento de Peça/TipoTarefa/etc — 422, não 404)."""


class ProjetoModeloCampanhaReferenciaInvalidaError(ValueError):
    """Peça/TipoTarefa/Workflow/Usuário/Departamento inexistente, de outra Empresa, ou cujo
    status não aceita vínculo novo. Nunca levantado pra uma referência que já existia sem
    mudança no item durante uma edição — ver
    ProjetoModeloCampanhaService._preparar_itens_edicao."""


class ProjetoModeloCampanhaNaoAplicadoError(ValueError):
    """PATCH tentado num Projeto que ainda não tem snapshot — aplicação só acontece via
    POST /projetos/{id}/modelo-campanha/aplicar, nunca implicitamente pelo PATCH."""


class ProjetoModeloCampanhaService:
    def __init__(
        self,
        repository: ProjetoModeloCampanhaRepository | None = None,
        modelo_campanha_repository: ModeloCampanhaRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or ProjetoModeloCampanhaRepository()
        self.modelo_campanha_repository = modelo_campanha_repository or ModeloCampanhaRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Aplicar / reaplicar
    # ----------------------------------------------------------------------------------

    def aplicar_modelo(
        self,
        db: Session,
        *,
        projeto: Projeto,
        modelo_campanha_id: str,
        actor_usuario_id: str,
    ) -> ProjetoModeloCampanha:
        """Aplica (primeira vez) ou reaplica (substitui) um Modelo de Campanha num Projeto.

        Identidade do cabeçalho: se o Projeto já tem snapshot, o cabeçalho EXISTENTE é
        atualizado (mesmo id, proveniência/metadados sobrescritos) — nunca apagado/recriado
        (ver docstring de `ProjetoModeloCampanha`). Os itens são sempre substituídos por
        inteiro, materializados NOVOS a partir do Modelo atual: mesmo numa reaplicação, não
        há preservação histórica de referência aqui (isso só existe na edição via PATCH) —
        toda referência do Modelo é revalidada como vínculo novo no momento da aplicação,
        porque o Modelo pode ter sido editado depois de criado (item 9 da Fase 2G.5C2).
        """
        try:
            modelo = self.modelo_campanha_repository.get_by_id(db, modelo_campanha_id)
            if modelo is None or modelo.empresa_id != projeto.empresa_id:
                raise ProjetoModeloCampanhaModeloInvalidoError("Modelo de Campanha inválido para esta Empresa")
            if modelo.status != STATUS_MODELO_ATIVO:
                raise ProjetoModeloCampanhaModeloInvalidoError(
                    f"Modelo de Campanha com status '{modelo.status}' não aceita aplicação"
                )

            itens_origem = self.modelo_campanha_repository.list_itens(db, modelo.id)
            itens_objetos = self._preparar_itens_materializados(
                db, empresa_id=projeto.empresa_id, itens_origem=itens_origem
            )

            now = agora_utc()
            cabecalho = self.repository.get_by_projeto_id(db, projeto.id)
            origem_anterior_id = cabecalho.modelo_campanha_origem_id if cabecalho is not None else None

            if cabecalho is None:
                cabecalho = ProjetoModeloCampanha(id=str(uuid4()), projeto_id=projeto.id, created_at=now, updated_at=now)
                criar_cabecalho = True
            else:
                criar_cabecalho = False

            cabecalho.modelo_campanha_origem_id = modelo.id
            cabecalho.modelo_campanha_nome_snapshot = modelo.nome
            cabecalho.aplicado_at = now
            cabecalho.aplicado_por_usuario_id = actor_usuario_id
            cabecalho.updated_at = now

            if criar_cabecalho:
                self.repository.create(db, cabecalho)
            else:
                self.repository.update(db, cabecalho)

            for item in itens_objetos:
                item.projeto_modelo_campanha_id = cabecalho.id
            self.repository.replace_itens(db, projeto_modelo_campanha_id=cabecalho.id, itens=itens_objetos)

            self._publish_evento_aplicado(
                db,
                projeto=projeto,
                modelo_campanha_origem_id=modelo.id,
                modelo_campanha_origem_anterior_id=origem_anterior_id,
                quantidade_itens=len(itens_objetos),
                actor_usuario_id=actor_usuario_id,
                occurred_at=now,
            )

            db.commit()
            db.refresh(cabecalho)
            return cabecalho
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta
    # ----------------------------------------------------------------------------------

    def get_snapshot(self, db: Session, *, projeto_id: str) -> ProjetoModeloCampanha | None:
        return self.repository.get_by_projeto_id(db, projeto_id)

    def to_snapshot_read(self, db: Session, cabecalho: ProjetoModeloCampanha) -> ProjetoModeloCampanhaSnapshotRead:
        """Monta o DTO direto das colunas persistidas — sem nenhum JOIN pra resolver nome.
        Os `*_nome_snapshot` SÃO o dado a ser lido; recalculá-los aqui reintroduziria a
        entidade viva na leitura do que é, por definição, uma fotografia (ver docstring de
        `ProjetoModeloCampanhaItem`)."""
        itens = self.repository.list_itens(db, cabecalho.id)
        return ProjetoModeloCampanhaSnapshotRead(
            id=cabecalho.id,
            modeloCampanhaOrigemId=cabecalho.modelo_campanha_origem_id,
            modeloCampanhaNomeSnapshot=cabecalho.modelo_campanha_nome_snapshot,
            aplicadoAt=cabecalho.aplicado_at,
            aplicadoPorUsuarioId=cabecalho.aplicado_por_usuario_id,
            itens=[self._montar_item_read(item) for item in itens],
            createdAt=cabecalho.created_at,
            updatedAt=cabecalho.updated_at,
        )

    def _montar_item_read(self, item: ProjetoModeloCampanhaItem) -> ProjetoModeloCampanhaItemRead:
        return ProjetoModeloCampanhaItemRead(
            id=item.id,
            ordem=item.ordem,
            nome=item.nome,
            briefingPadrao=item.briefing_padrao,
            prioridadePadrao=item.prioridade_padrao,
            pecaId=item.peca_id,
            pecaNomeSnapshot=item.peca_nome_snapshot,
            tipoTarefaId=item.tipo_tarefa_id,
            tipoTarefaNomeSnapshot=item.tipo_tarefa_nome_snapshot,
            workflowModeloId=item.workflow_modelo_id,
            workflowModeloNomeSnapshot=item.workflow_modelo_nome_snapshot,
            responsavelUsuarioId=item.responsavel_usuario_id,
            responsavelUsuarioNomeSnapshot=item.responsavel_usuario_nome_snapshot,
            responsavelDepartamentoId=item.responsavel_departamento_id,
            responsavelDepartamentoNomeSnapshot=item.responsavel_departamento_nome_snapshot,
        )

    # ----------------------------------------------------------------------------------
    # Edição (sem reaplicar)
    # ----------------------------------------------------------------------------------

    def atualizar_itens(
        self,
        db: Session,
        *,
        projeto: Projeto,
        data: ProjetoModeloCampanhaUpdate,
        actor_usuario_id: str,
    ) -> ProjetoModeloCampanha:
        try:
            cabecalho = self.repository.get_by_projeto_id(db, projeto.id)
            if cabecalho is None:
                raise ProjetoModeloCampanhaNaoAplicadoError("Projeto ainda não possui Modelo de Campanha aplicado")

            itens_atuais = self.repository.list_itens(db, cabecalho.id)
            itens_objetos = self._preparar_itens_edicao(
                db, empresa_id=projeto.empresa_id, itens_novos=data.itens, itens_atuais=itens_atuais
            )
            for item in itens_objetos:
                item.projeto_modelo_campanha_id = cabecalho.id
            self.repository.replace_itens(db, projeto_modelo_campanha_id=cabecalho.id, itens=itens_objetos)

            now = agora_utc()
            cabecalho.updated_at = now
            self.repository.update(db, cabecalho)

            # Reaproveita PROJETO_ALTERADO (mesma forma de payload de toda alteração de
            # Projeto) — editar os itens do snapshot não é uma aplicação/substituição de
            # Modelo, é edição pontual; não merece um evento dedicado (ver item 25 da 2G.5C2).
            self._publish_evento_alterado(db, projeto=projeto, actor_usuario_id=actor_usuario_id, occurred_at=now)

            db.commit()
            db.refresh(cabecalho)
            return cabecalho
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Itens — materialização (aplicar/reaplicar) e edição (PATCH)
    # ----------------------------------------------------------------------------------

    def _preparar_itens_materializados(
        self, db: Session, *, empresa_id: str, itens_origem: list[ModeloCampanhaItem]
    ) -> list[ProjetoModeloCampanhaItem]:
        """Copia os itens do Modelo de biblioteca pra novos `ProjetoModeloCampanhaItem` — id
        PRÓPRIO sempre gerado aqui, nunca reaproveita `modelos_campanha_itens.id` (a
        proveniência do Modelo fica só no cabeçalho, ver `ProjetoModeloCampanha`). Toda
        referência é validada como vínculo NOVO, mesmo numa reaplicação: os itens antigos são
        descartados por inteiro (não editados), então não existe "referência que não mudou"
        aqui — isso só faz sentido na edição via PATCH (`_preparar_itens_edicao`)."""
        now = agora_utc()
        objetos: list[ProjetoModeloCampanhaItem] = []

        for ordem, item_origem in enumerate(itens_origem, start=1):
            peca_id, peca_nome = self._validar_e_resolver(
                db, empresa_id=empresa_id, valor=item_origem.peca_id, model_cls=Peca, nome_entidade="Peça",
                invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            tipo_tarefa_id, tipo_tarefa_nome = self._validar_e_resolver(
                db, empresa_id=empresa_id, valor=item_origem.tipo_tarefa_id, model_cls=TipoTarefa,
                nome_entidade="Tipo de Tarefa", invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            workflow_modelo_id, workflow_modelo_nome = self._validar_e_resolver(
                db, empresa_id=empresa_id, valor=item_origem.workflow_modelo_id, model_cls=WorkflowModelo,
                nome_entidade="Modelo de Workflow", invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            responsavel_usuario_id, responsavel_usuario_nome = self._validar_e_resolver(
                db, empresa_id=empresa_id, valor=item_origem.responsavel_usuario_id, model_cls=Usuario,
                nome_entidade="Usuário responsável", invalido=lambda entidade: entidade.status in _STATUS_USUARIO_INVALIDO,
            )
            responsavel_departamento_id, responsavel_departamento_nome = self._validar_e_resolver(
                db, empresa_id=empresa_id, valor=item_origem.responsavel_departamento_id, model_cls=Departamento,
                nome_entidade="Departamento responsável",
                invalido=lambda entidade: entidade.status == _STATUS_DEPARTAMENTO_INVALIDO,
            )

            objetos.append(
                ProjetoModeloCampanhaItem(
                    id=str(uuid4()),
                    projeto_modelo_campanha_id="",  # setado pelo chamador após criar/carregar o cabeçalho
                    ordem=ordem,
                    nome=item_origem.nome,
                    briefing_padrao=item_origem.briefing_padrao,
                    prioridade_padrao=item_origem.prioridade_padrao,
                    peca_id=peca_id,
                    peca_nome_snapshot=peca_nome,
                    tipo_tarefa_id=tipo_tarefa_id,
                    tipo_tarefa_nome_snapshot=tipo_tarefa_nome,
                    workflow_modelo_id=workflow_modelo_id,
                    workflow_modelo_nome_snapshot=workflow_modelo_nome,
                    responsavel_usuario_id=responsavel_usuario_id,
                    responsavel_usuario_nome_snapshot=responsavel_usuario_nome,
                    responsavel_departamento_id=responsavel_departamento_id,
                    responsavel_departamento_nome_snapshot=responsavel_departamento_nome,
                    created_at=now,
                    updated_at=now,
                )
            )

        return objetos

    def _preparar_itens_edicao(
        self,
        db: Session,
        *,
        empresa_id: str,
        itens_novos: list[ProjetoModeloCampanhaItemInput],
        itens_atuais: list[ProjetoModeloCampanhaItem],
    ) -> list[ProjetoModeloCampanhaItem]:
        """Mesma lógica de `ModeloCampanhaService._preparar_itens` (Fase 2G.5A), adaptada pro
        snapshot: cada referência só é validada como vínculo NOVO quando o valor MUDOU em
        relação ao item existente (casado por `id`, escopado a ESTE snapshot); se não mudou,
        FK e nome snapshot são preservados tal como estão, mesmo que a entidade tenha sido
        arquivada/inativada depois. `id` só é reaproveitado quando bate com um item existente
        DESTE snapshot — id de outro Projeto, de outra Empresa, ou inexistente é tratado como
        item novo (UUID gerado aqui, nunca o valor do cliente)."""
        existentes_por_id = {item.id: item for item in itens_atuais}
        now = agora_utc()
        objetos: list[ProjetoModeloCampanhaItem] = []

        for ordem, item_novo in enumerate(itens_novos, start=1):
            item_id_str = str(item_novo.id) if item_novo.id else None
            existente = existentes_por_id.get(item_id_str) if item_id_str else None

            peca_id, peca_nome = self._validar_campo_com_snapshot(
                db, empresa_id=empresa_id,
                novo_valor=str(item_novo.peca_id) if item_novo.peca_id else None,
                valor_existente=existente.peca_id if existente else None,
                nome_existente=existente.peca_nome_snapshot if existente else None,
                model_cls=Peca, nome_entidade="Peça",
                invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            tipo_tarefa_id, tipo_tarefa_nome = self._validar_campo_com_snapshot(
                db, empresa_id=empresa_id,
                novo_valor=str(item_novo.tipo_tarefa_id) if item_novo.tipo_tarefa_id else None,
                valor_existente=existente.tipo_tarefa_id if existente else None,
                nome_existente=existente.tipo_tarefa_nome_snapshot if existente else None,
                model_cls=TipoTarefa, nome_entidade="Tipo de Tarefa",
                invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            workflow_modelo_id, workflow_modelo_nome = self._validar_campo_com_snapshot(
                db, empresa_id=empresa_id,
                novo_valor=str(item_novo.workflow_modelo_id) if item_novo.workflow_modelo_id else None,
                valor_existente=existente.workflow_modelo_id if existente else None,
                nome_existente=existente.workflow_modelo_nome_snapshot if existente else None,
                model_cls=WorkflowModelo, nome_entidade="Modelo de Workflow",
                invalido=lambda entidade: entidade.status != STATUS_MODELO_ATIVO,
            )
            responsavel_usuario_id, responsavel_usuario_nome = self._validar_campo_com_snapshot(
                db, empresa_id=empresa_id,
                novo_valor=str(item_novo.responsavel_usuario_id) if item_novo.responsavel_usuario_id else None,
                valor_existente=existente.responsavel_usuario_id if existente else None,
                nome_existente=existente.responsavel_usuario_nome_snapshot if existente else None,
                model_cls=Usuario, nome_entidade="Usuário responsável",
                invalido=lambda entidade: entidade.status in _STATUS_USUARIO_INVALIDO,
            )
            responsavel_departamento_id, responsavel_departamento_nome = self._validar_campo_com_snapshot(
                db, empresa_id=empresa_id,
                novo_valor=(
                    str(item_novo.responsavel_departamento_id) if item_novo.responsavel_departamento_id else None
                ),
                valor_existente=existente.responsavel_departamento_id if existente else None,
                nome_existente=existente.responsavel_departamento_nome_snapshot if existente else None,
                model_cls=Departamento, nome_entidade="Departamento responsável",
                invalido=lambda entidade: entidade.status == _STATUS_DEPARTAMENTO_INVALIDO,
            )

            objetos.append(
                ProjetoModeloCampanhaItem(
                    id=existente.id if existente is not None else str(uuid4()),
                    projeto_modelo_campanha_id="",
                    ordem=ordem,
                    nome=item_novo.nome,
                    briefing_padrao=item_novo.briefing_padrao,
                    prioridade_padrao=item_novo.prioridade_padrao,
                    peca_id=peca_id,
                    peca_nome_snapshot=peca_nome,
                    tipo_tarefa_id=tipo_tarefa_id,
                    tipo_tarefa_nome_snapshot=tipo_tarefa_nome,
                    workflow_modelo_id=workflow_modelo_id,
                    workflow_modelo_nome_snapshot=workflow_modelo_nome,
                    responsavel_usuario_id=responsavel_usuario_id,
                    responsavel_usuario_nome_snapshot=responsavel_usuario_nome,
                    responsavel_departamento_id=responsavel_departamento_id,
                    responsavel_departamento_nome_snapshot=responsavel_departamento_nome,
                    created_at=now,
                    updated_at=now,
                )
            )

        return objetos

    def _validar_e_resolver(
        self, db: Session, *, empresa_id: str, valor: str | None, model_cls, nome_entidade: str, invalido
    ) -> tuple[str | None, str | None]:
        """Vínculo sempre NOVO (materialização) — sem noção de "valor existente". Retorna
        `(id, nome)` já resolvidos, ou `(None, None)` se o campo de origem for nulo."""
        if valor is None:
            return None, None
        entidade = db.get(model_cls, valor)
        if entidade is None or entidade.empresa_id != empresa_id:
            raise ProjetoModeloCampanhaReferenciaInvalidaError(f"{nome_entidade} inválido(a) para esta Empresa")
        if invalido(entidade):
            raise ProjetoModeloCampanhaReferenciaInvalidaError(
                f"{nome_entidade} com status '{entidade.status}' não aceita vínculo novo"
            )
        return entidade.id, entidade.nome

    def _validar_campo_com_snapshot(
        self,
        db: Session,
        *,
        empresa_id: str,
        novo_valor: str | None,
        valor_existente: str | None,
        nome_existente: str | None,
        model_cls,
        nome_entidade: str,
        invalido,
    ) -> tuple[str | None, str | None]:
        """Preserva FK + nome snapshot sem revalidar se o valor não mudou (histórico); valida
        como vínculo NOVO e recaptura o nome atual em qualquer outro caso (item novo, campo
        alterado — inclusive troca por outro id, ou remoção explícita)."""
        if novo_valor == valor_existente:
            return novo_valor, nome_existente
        if novo_valor is None:
            return None, None

        entidade = db.get(model_cls, novo_valor)
        if entidade is None or entidade.empresa_id != empresa_id:
            raise ProjetoModeloCampanhaReferenciaInvalidaError(f"{nome_entidade} inválido(a) para esta Empresa")
        if invalido(entidade):
            raise ProjetoModeloCampanhaReferenciaInvalidaError(
                f"{nome_entidade} com status '{entidade.status}' não aceita vínculo novo"
            )
        return entidade.id, entidade.nome

    # ----------------------------------------------------------------------------------
    # Eventos
    # ----------------------------------------------------------------------------------

    def _publish_evento_aplicado(
        self,
        db: Session,
        *,
        projeto: Projeto,
        modelo_campanha_origem_id: str,
        modelo_campanha_origem_anterior_id: str | None,
        quantidade_itens: int,
        actor_usuario_id: str | None,
        occurred_at: datetime,
    ) -> None:
        # Payload enxuto — nunca serializa os itens (mesmo padrão de modelo_campanha.*).
        payload = {
            "empresa_id": projeto.empresa_id,
            "projeto_id": projeto.id,
            "modelo_campanha_origem_id": modelo_campanha_origem_id,
            "modelo_campanha_origem_anterior_id": modelo_campanha_origem_anterior_id,
            "quantidade_itens": quantidade_itens,
            "timestamp": occurred_at.isoformat(),
        }
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.PROJETO_MODELO_CAMPANHA_APLICADO,
            empresa_id=projeto.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=projeto.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )

    def _publish_evento_alterado(
        self, db: Session, *, projeto: Projeto, actor_usuario_id: str | None, occurred_at: datetime
    ) -> None:
        # Mesma forma de payload de `ProjetoService._publish_event` — mantém o evento
        # PROJETO_ALTERADO consistente entre todas as origens de alteração de Projeto.
        payload = {
            "empresa_id": projeto.empresa_id,
            "projeto_id": projeto.id,
            "codigo_referencia": projeto.codigo_referencia,
            "timestamp": occurred_at.isoformat(),
            "status": projeto.status,
            "camposAlterados": ["modeloCampanhaSnapshot"],
        }
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.PROJETO_ALTERADO,
            empresa_id=projeto.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=projeto.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )
