from datetime import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.core.expediente import REGRA_PADRAO, RegraExpediente, esta_dentro_expediente
from app.core.referencias import gerar_proxima_referencia
from app.core.relogio import agora_utc
from app.core.sequencias_operacionais import reservar_proximo_operacional
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_departamento import DemandaDepartamento
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_departamento_responsavel import (
    DemandaWorkflowEtapaDepartamentoResponsavel,
)
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.evento import Evento
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.demanda_repository import DemandaRepository
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.projeto_repository import ProjetoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.workflow_modelo_repository import WorkflowModeloRepository
from app.schemas.demanda import DemandaCreate, DemandaRead, DemandaUpdate, DemandaWorkflowEtapaRead
from app.services.domain_event_publisher import DomainEventPublisher

# `tarefa` no gerador de referência (prefixo T) e `demanda` no contador operacional: são
# vocabulários de sistemas diferentes e ambos estão certos. A interface chama de Tarefa, o
# domínio se chama Demanda — ver a docstring de app/models/demanda.py.
TIPO_REFERENCIA = "tarefa"
TIPO_OPERACIONAL = "demanda"
TIPO_ENTIDADE = "demanda"

STATUS_ARQUIVADA = "arquivada"
STATUS_PADRAO = "rascunho"
STATUS_EM_EXECUCAO = "em_execucao"
STATUS_BLOQUEADA = "bloqueada"
STATUS_CONCLUIDA = "concluida"

# Mesma regra de Cliente, Projeto e Departamento: um usuário nestes estados não pode ser
# DEFINIDO como responsável novo. Vínculo histórico continua valendo.
STATUS_USUARIO_INVALIDO = {"arquivado", "inativo", "bloqueado"}

# Toda etapa materializada nasce pendente — não há automação de avanço nesta fase (ver
# docstring de DemandaWorkflowEtapa e a decisão de etapa_atual ser derivada, não persistida).
STATUS_ETAPA_WORKFLOW_PENDENTE = "pendente"
STATUS_ETAPA_WORKFLOW_CONCLUIDA = "concluida"
WORKFLOW_MODELO_STATUS_ATIVO = "ativo"

_CAMPOS_SIMPLES = (
    "pit",
    "briefing",
    "prioridade",
    "sinalizada",
    "data_inicio",
    "data_fim_prevista",
    "prazo_etapa_atual",
    "enviado_cliente_em",
    "prazo_retorno_cliente",
    "retorno_recebido_em",
    "email_conclusao_enviado",
    "email_conclusao_data",
)


class DemandaNotFoundError(ValueError):
    """Inexistente, de outra empresa **ou fora do escopo** de quem pediu.

    Um erro único para os três casos é deliberado: distinguir "não existe" de "existe mas não
    é sua" confirmaria a existência do registro a quem variasse o UUID.
    """


class DemandaInvalidTransitionError(ValueError):
    pass


class DemandaMotivoBloqueioObrigatorioError(ValueError):
    """`bloqueada` sem motivo. 422 — é campo faltando, não conflito de estado."""


class DemandaForaDeExpedienteError(ValueError):
    """Tentativa de entrar em execução fora do expediente. Vira 409 estruturado.

    Carrega a janela vigente para a interface conseguir dizer *quando* poderá — sem repetir
    a regra no cliente.
    """

    def __init__(self, message: str, *, regra: RegraExpediente) -> None:
        super().__init__(message)
        self.regra = regra


class DemandaClienteInvalidoError(ValueError):
    """Cliente inexistente, de outra empresa ou arquivado (vínculo novo)."""


class DemandaProjetoInvalidoError(ValueError):
    """Projeto inexistente, de outra empresa ou arquivado (vínculo novo)."""


class DemandaUsuarioInvalidoError(ValueError):
    """Responsável inexistente, de outra empresa ou em status inválido."""


class DemandaDepartamentoInvalidoError(ValueError):
    """Departamento inexistente, de outra empresa ou arquivado (vínculo novo)."""


class DemandaWorkflowModeloInvalidoError(ValueError):
    """WorkflowModelo inexistente, de outra empresa ou não ativo (aplicação nova)."""


class DemandaService:
    def __init__(
        self,
        repository: DemandaRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
        projeto_repository: ProjetoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
        workflow_modelo_repository: WorkflowModeloRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
        regra_expediente: RegraExpediente | None = None,
    ) -> None:
        self.repository = repository or DemandaRepository()
        self.cliente_repository = cliente_repository or ClienteRepository()
        self.projeto_repository = projeto_repository or ProjetoRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()
        self.workflow_modelo_repository = workflow_modelo_repository or WorkflowModeloRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()
        # Injetável para o teste conseguir fixar a janela sem depender do relógio da máquina.
        self.regra_expediente = regra_expediente or REGRA_PADRAO

    # ----------------------------------------------------------------------------------
    # Criação
    # ----------------------------------------------------------------------------------

    def create_demanda(
        self,
        db: Session,
        data: DemandaCreate,
        *,
        empresa_id: str,
        actor_usuario_id: str | None = None,
    ) -> Demanda:
        now = agora_utc()
        cliente_id = str(data.cliente_id) if data.cliente_id else None
        projeto_id = str(data.projeto_id) if data.projeto_id else None
        workflow_modelo_id = str(data.workflow_modelo_id) if data.workflow_modelo_id else None
        responsavel_ids = [str(uid) for uid in (data.responsavel_ids or [])]
        departamento_ids = [str(did) for did in (data.departamento_responsavel_ids or [])]
        status = data.status or STATUS_PADRAO

        try:
            self._ensure_regras_de_status(status, data.motivo_bloqueio)

            if cliente_id is not None:
                self._ensure_cliente_valido(db, empresa_id, cliente_id)
            if projeto_id is not None:
                self._ensure_projeto_valido(db, empresa_id, projeto_id)
            if workflow_modelo_id is not None:
                self._ensure_workflow_modelo_valido(db, empresa_id, workflow_modelo_id)
            for usuario_id in responsavel_ids:
                self._ensure_usuario_valido(db, empresa_id, usuario_id)
            for departamento_id in departamento_ids:
                self._ensure_departamento_valido(db, empresa_id, departamento_id)

            # Os DOIS contadores, a entidade, os vínculos e os eventos na MESMA transação.
            # Se qualquer coisa abaixo falhar, ambos os incrementos sofrem rollback juntos e
            # nenhum dos dois números é queimado — é o motivo de nenhum deles commitar por si.
            referencia = gerar_proxima_referencia(
                db, empresa_id=empresa_id, tipo_entidade=TIPO_REFERENCIA
            )
            numero_operacional = reservar_proximo_operacional(
                db, empresa_id=empresa_id, tipo_entidade=TIPO_OPERACIONAL
            )

            demanda = Demanda(
                id=str(uuid4()),
                empresa_id=empresa_id,
                codigo_referencia=referencia.codigo_referencia,
                ano_referencia=referencia.ano_referencia,
                sequencial_referencia=referencia.sequencial_referencia,
                numero_operacional=numero_operacional,
                nome=data.nome,
                status=status,
                motivo_bloqueio=data.motivo_bloqueio if status == STATUS_BLOQUEADA else None,
                cliente_id=cliente_id,
                projeto_id=projeto_id,
                criado_por_usuario_id=actor_usuario_id,
                workflow_modelo_id=workflow_modelo_id,
                created_at=now,
                updated_at=now,
                **{campo: getattr(data, campo) for campo in _CAMPOS_SIMPLES},
            )
            self.repository.create(db, demanda)

            if workflow_modelo_id is not None:
                self._materializar_workflow(
                    db, demanda, workflow_modelo_id=workflow_modelo_id, empresa_id=empresa_id, now=now
                )

            for usuario_id in responsavel_ids:
                self.repository.adicionar_responsavel(
                    db, DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario_id, created_at=now)
                )
            for departamento_id in departamento_ids:
                self.repository.adicionar_departamento(
                    db,
                    DemandaDepartamento(
                        demanda_id=demanda.id, departamento_id=departamento_id, created_at=now
                    ),
                )

            self._publish_event(db, demanda, DomainEventType.DEMANDA_CRIADA, actor_usuario_id, occurred_at=now)
            if workflow_modelo_id is not None:
                # Completa a timeline com o marco que só existia como coluna
                # (`demandas.workflow_modelo_id`) até a Fase 2E.4 — payload minimal de
                # propósito: buscar nome/código do WorkflowModelo aqui duplicaria a consulta
                # que `_ensure_workflow_modelo_valido` já fez, só para um dado que a UI
                # consegue resolver localmente a partir do id (mesmo padrão usado para
                # usuarioId/departamentoId nos outros eventos desta função).
                self._publish_event(
                    db, demanda, DomainEventType.DEMANDA_WORKFLOW_APLICADO, actor_usuario_id,
                    extra_payload={"workflowModeloId": workflow_modelo_id}, occurred_at=now,
                )
            if status == STATUS_BLOQUEADA:
                self._publish_event(
                    db, demanda, DomainEventType.DEMANDA_BLOQUEADA, actor_usuario_id,
                    extra_payload={"motivoBloqueio": demanda.motivo_bloqueio}, occurred_at=now,
                )
            for usuario_id in responsavel_ids:
                self._publish_event(
                    db, demanda, DomainEventType.DEMANDA_RESPONSAVEL_ADICIONADO, actor_usuario_id,
                    extra_payload={"usuarioId": usuario_id}, occurred_at=now,
                )
            for departamento_id in departamento_ids:
                self._publish_event(
                    db, demanda, DomainEventType.DEMANDA_DEPARTAMENTO_ADICIONADO, actor_usuario_id,
                    extra_payload={"departamentoId": departamento_id}, occurred_at=now,
                )

            db.commit()
            db.refresh(demanda)
            return demanda
        except IntegrityError:
            # Só há uma unicidade alcançável por corrida aqui: `numero_operacional`. Os dois
            # contadores serializam pelo lock da própria linha, então isto significa contador
            # adulterado fora da aplicação — o UNIQUE fez o papel de piso.
            db.rollback()
            raise DemandaInvalidTransitionError(
                "Falha ao emitir número operacional — contador fora de sincronia com as demandas emitidas"
            ) from None
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Consulta — sempre escopada
    # ----------------------------------------------------------------------------------

    def list_demandas(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        status: str | None = None,
        search: str | None = None,
        cliente_id: str | None = None,
        projeto_id: str | None = None,
        departamento_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Demanda]:
        return self.repository.list(
            db,
            escopo=escopo,
            status=status,
            search=search,
            cliente_id=cliente_id,
            projeto_id=projeto_id,
            departamento_id=departamento_id,
            limit=limit,
            offset=offset,
        )

    def get_demanda(self, db: Session, demanda_id: str, *, escopo: EscopoDemanda) -> Demanda:
        """**Único** caminho de acesso por UUID nas rotas.

        Recebe o escopo por parâmetro obrigatório — não há assinatura que permita esquecê-lo,
        que é o que garante a regra também no acesso direto, e não só na listagem.
        """
        demanda = self.repository.get_no_escopo(db, demanda_id=demanda_id, escopo=escopo)
        if demanda is None:
            raise DemandaNotFoundError("Demanda não encontrada")
        return demanda

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def update_demanda(
        self,
        db: Session,
        demanda: Demanda,
        data: DemandaUpdate,
        *,
        actor_usuario_id: str | None = None,
    ) -> Demanda:
        """Recebe a Demanda **já resolvida dentro do escopo** pela rota — nunca um id solto."""
        updates = data.model_dump(exclude_unset=True)
        campos_alterados: list[str] = []
        eventos: list[tuple[DomainEventType, dict]] = []

        try:
            if demanda.status == STATUS_ARQUIVADA:
                raise DemandaInvalidTransitionError(
                    "Demanda arquivada não pode ser editada — restaure-a antes"
                )

            status_anterior = demanda.status
            status_final = updates.get("status") or demanda.status
            # Motivo final considera os DOIS valores: mudar só o status para `bloqueada` sem
            # enviar motivo tem de falhar mesmo que o campo já estivesse preenchido antes.
            motivo_final = updates.get("motivo_bloqueio", demanda.motivo_bloqueio)
            if "status" in updates and updates["status"] is not None:
                self._ensure_regras_de_status(
                    status_final, updates.get("motivo_bloqueio") if "motivo_bloqueio" in updates else motivo_final
                )

            if status_final != status_anterior:
                # Expediente só barra a ENTRADA em execução. Criar rascunho, planejar,
                # concluir e cancelar seguem livres a qualquer hora — o que a regra protege é
                # o início do trabalho, não o registro dele.
                if status_final == STATUS_EM_EXECUCAO:
                    self._ensure_dentro_expediente()

                demanda.status = status_final
                campos_alterados.append("status")
                eventos.append(
                    (
                        DomainEventType.DEMANDA_STATUS_ALTERADO,
                        {"de": status_anterior, "para": status_final},
                    )
                )

                if status_final == STATUS_BLOQUEADA:
                    demanda.motivo_bloqueio = motivo_final
                    eventos.append(
                        (DomainEventType.DEMANDA_BLOQUEADA, {"motivoBloqueio": motivo_final})
                    )
                elif status_anterior == STATUS_BLOQUEADA:
                    # Sai de bloqueada: o campo é limpo, mas o motivo NÃO se perde — vai no
                    # payload do evento, que é o histórico desta fase.
                    eventos.append(
                        (
                            DomainEventType.DEMANDA_DESBLOQUEADA,
                            {"motivoBloqueioAnterior": demanda.motivo_bloqueio},
                        )
                    )
                    demanda.motivo_bloqueio = None
                    campos_alterados.append("motivoBloqueio")

            elif "motivo_bloqueio" in updates and demanda.status == STATUS_BLOQUEADA:
                # Continua bloqueada, motivo reescrito.
                if motivo_final != demanda.motivo_bloqueio:
                    eventos.append(
                        (DomainEventType.DEMANDA_BLOQUEADA, {"motivoBloqueio": motivo_final})
                    )
                    demanda.motivo_bloqueio = motivo_final
                    campos_alterados.append("motivoBloqueio")

            if "nome" in updates and updates["nome"] is not None and updates["nome"] != demanda.nome:
                demanda.nome = updates["nome"]
                campos_alterados.append("nome")

            if "cliente_id" in updates:
                cliente_final = str(updates["cliente_id"]) if updates["cliente_id"] else None
                if cliente_final != demanda.cliente_id:
                    if cliente_final is not None:
                        self._ensure_cliente_valido(db, demanda.empresa_id, cliente_final)
                    demanda.cliente_id = cliente_final
                    campos_alterados.append("clienteId")

            if "projeto_id" in updates:
                projeto_final = str(updates["projeto_id"]) if updates["projeto_id"] else None
                if projeto_final != demanda.projeto_id:
                    if projeto_final is not None:
                        self._ensure_projeto_valido(db, demanda.empresa_id, projeto_final)
                    demanda.projeto_id = projeto_final
                    campos_alterados.append("projetoId")

            # Capturado ANTES do loop genérico sobrescrever o campo — é a única forma de
            # detectar a transição None -> valor (cliente respondeu) depois.
            retorno_recebido_em_anterior = demanda.retorno_recebido_em

            for campo in _CAMPOS_SIMPLES:
                if campo not in updates:
                    continue
                if updates[campo] != getattr(demanda, campo):
                    setattr(demanda, campo, updates[campo])
                    campos_alterados.append(campo)

            if retorno_recebido_em_anterior is None and demanda.retorno_recebido_em is not None:
                # Marco sem ambiguidade — só existe UM motivo real para este campo sair de
                # None (cliente respondeu), ao contrário do par enviado/dispensado de e-mail
                # de conclusão (mesmo estado final, duas intenções — por isso aquele tem
                # ação dedicada em vez de detecção por diff, ver registrar_conclusao_email).
                eventos.append((DomainEventType.DEMANDA_RETORNO_CLIENTE_REGISTRADO, {}))

            if "responsavel_ids" in updates:
                eventos += self._sincronizar_responsaveis(
                    db, demanda, [str(uid) for uid in (updates["responsavel_ids"] or [])]
                )
            if "departamento_responsavel_ids" in updates:
                eventos += self._sincronizar_departamentos(
                    db, demanda, [str(did) for did in (updates["departamento_responsavel_ids"] or [])]
                )

            if eventos and not campos_alterados:
                campos_alterados.append("vinculos")

            if campos_alterados:
                now = agora_utc()
                demanda.updated_at = now
                self.repository.update(db, demanda)
                self._publish_event(
                    db, demanda, DomainEventType.DEMANDA_ALTERADA, actor_usuario_id,
                    extra_payload={"camposAlterados": campos_alterados}, occurred_at=now,
                )
                for tipo, payload in eventos:
                    self._publish_event(db, demanda, tipo, actor_usuario_id, extra_payload=payload, occurred_at=now)

            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Arquivamento — ver docs/padrao-arquivamento.md. Nunca há delete físico.
    # ----------------------------------------------------------------------------------

    def arquivar_demanda(
        self,
        db: Session,
        demanda: Demanda,
        *,
        motivo_arquivamento: str,
        actor_usuario_id: str | None = None,
    ) -> Demanda:
        try:
            if demanda.status == STATUS_ARQUIVADA:
                raise DemandaInvalidTransitionError("Demanda já está arquivada")

            now = agora_utc()
            demanda.status_anterior_arquivamento = demanda.status
            demanda.status = STATUS_ARQUIVADA
            demanda.arquivado_at = now
            demanda.arquivado_por_usuario_id = actor_usuario_id
            demanda.motivo_arquivamento = motivo_arquivamento
            demanda.restaurado_at = None
            demanda.restaurado_por_usuario_id = None
            demanda.updated_at = now

            self.repository.update(db, demanda)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_ARQUIVADA, actor_usuario_id,
                extra_payload={"motivoArquivamento": motivo_arquivamento}, occurred_at=now,
            )
            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    def restaurar_demanda(
        self, db: Session, demanda: Demanda, *, actor_usuario_id: str | None = None
    ) -> Demanda:
        try:
            if demanda.status != STATUS_ARQUIVADA:
                raise DemandaInvalidTransitionError("Somente demanda arquivada pode ser restaurada")

            # Volta ao status de antes SEM passar pela checagem de expediente: restaurar não é
            # iniciar trabalho, é desfazer um arquivamento. Barrar aqui deixaria uma demanda
            # arquivada por engano fora do ar até o dia seguinte.
            now = agora_utc()
            demanda.status = demanda.status_anterior_arquivamento or STATUS_PADRAO
            demanda.restaurado_at = now
            demanda.restaurado_por_usuario_id = actor_usuario_id
            demanda.arquivado_at = None
            demanda.arquivado_por_usuario_id = None
            demanda.motivo_arquivamento = None
            demanda.status_anterior_arquivamento = None
            demanda.updated_at = now

            self.repository.update(db, demanda)
            self._publish_event(
                db, demanda, DomainEventType.DEMANDA_RESTAURADA, actor_usuario_id, occurred_at=now
            )
            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Ações que só publicam evento — sem tabela própria (Fase 2E.4)
    # ----------------------------------------------------------------------------------

    _EVENTO_POR_TIPO_AJUSTE: dict[str, DomainEventType] = {
        "ajuste_interno": DomainEventType.DEMANDA_AJUSTE_INTERNO_REGISTRADO,
        "ajuste_cliente": DomainEventType.DEMANDA_AJUSTE_CLIENTE_REGISTRADO,
        "refacao": DomainEventType.DEMANDA_REFACAO_REGISTRADA,
    }

    def registrar_ajuste(
        self, db: Session, demanda: Demanda, tipo: str, *, actor_usuario_id: str | None = None
    ) -> Evento:
        """Não muda nenhum campo da Demanda — só produz um evento na timeline. Os três tipos
        (`ajuste_interno`/`ajuste_cliente`/`refacao`) vêm da UI existente (RegistrarAjusteCard),
        mantidos diferenciados a pedido explícito em vez de um único evento genérico."""
        try:
            now = agora_utc()
            evento = self._publish_event(
                db, demanda, self._EVENTO_POR_TIPO_AJUSTE[tipo], actor_usuario_id, occurred_at=now
            )
            db.commit()
            return evento
        except Exception:
            db.rollback()
            raise

    def registrar_conclusao_email(
        self, db: Session, demanda: Demanda, *, enviado: bool, actor_usuario_id: str | None = None
    ) -> Demanda:
        """`enviado=True`: e-mail de conclusão foi enviado ao cliente. `enviado=False`:
        usuário dispensou o aviso. As duas ações gravam os MESMOS campos reais — só o evento
        publicado muda, porque é o único jeito de diferenciar as duas intenções depois (ver
        docstring de DemandaConclusaoEmailRegistrar)."""
        try:
            if demanda.status != STATUS_CONCLUIDA:
                raise DemandaInvalidTransitionError(
                    "Aviso de conclusão só se aplica a demanda com status 'concluida'"
                )

            now = agora_utc()
            demanda.email_conclusao_enviado = True
            demanda.email_conclusao_data = now
            demanda.updated_at = now
            self.repository.update(db, demanda)

            tipo_evento = (
                DomainEventType.DEMANDA_EMAIL_CONCLUSAO_ENVIADO
                if enviado
                else DomainEventType.DEMANDA_EMAIL_CONCLUSAO_DISPENSADO
            )
            self._publish_event(db, demanda, tipo_evento, actor_usuario_id, occurred_at=now)

            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Serialização
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, demanda: Demanda) -> DemandaRead:
        etapas_por_demanda = self._etapas_workflow_por_demanda(db, [demanda.id])
        etapas = etapas_por_demanda.get(demanda.id, [])
        return DemandaRead.model_validate(
            {
                **self._campos_base(demanda),
                "usuarioResponsavelIds": self.repository.listar_responsavel_ids(db, demanda.id),
                "departamentoResponsavelIds": self.repository.listar_departamento_ids(db, demanda.id),
                "workflowEtapas": etapas,
                "etapaAtualId": self._derivar_etapa_atual_id(etapas),
            }
        )

    def to_read_lote(self, db: Session, demandas: list[Demanda]) -> list[DemandaRead]:
        """Poucas queries para a página inteira, em vez de N por linha."""
        ids = [d.id for d in demandas]
        responsaveis = self.repository.listar_responsavel_ids_em_lote(db, ids)
        departamentos = self.repository.listar_departamento_ids_em_lote(db, ids)
        etapas_por_demanda = self._etapas_workflow_por_demanda(db, ids)
        return [
            DemandaRead.model_validate(
                {
                    **self._campos_base(demanda),
                    "usuarioResponsavelIds": responsaveis.get(demanda.id, []),
                    "departamentoResponsavelIds": departamentos.get(demanda.id, []),
                    "workflowEtapas": (etapas := etapas_por_demanda.get(demanda.id, [])),
                    "etapaAtualId": self._derivar_etapa_atual_id(etapas),
                }
            )
            for demanda in demandas
        ]

    def _etapas_workflow_por_demanda(
        self, db: Session, demanda_ids: list[str]
    ) -> dict[str, list[DemandaWorkflowEtapaRead]]:
        """Materializa `DemandaWorkflowEtapaRead` em lote — etapas + responsáveis (usuário e
        departamento) de todas as Demandas pedidas, em poucas queries."""
        etapas_por_demanda = self.repository.listar_etapas_workflow_em_lote(db, demanda_ids)
        etapa_ids = [etapa.id for etapas in etapas_por_demanda.values() for etapa in etapas]
        usuarios_por_etapa = self.repository.listar_etapa_responsavel_ids_em_lote(db, etapa_ids)
        departamentos_por_etapa = self.repository.listar_etapa_departamento_ids_em_lote(db, etapa_ids)

        return {
            demanda_id: [
                DemandaWorkflowEtapaRead(
                    id=etapa.id,
                    ordem=etapa.ordem,
                    nome=etapa.nome,
                    tipo=etapa.tipo,
                    quantidadeAntesDeadline=etapa.quantidade_antes_deadline,
                    unidadePrazo=etapa.unidade_prazo,
                    status=etapa.status,
                    usuarioResponsavelIds=usuarios_por_etapa.get(etapa.id, []),
                    departamentoResponsavelIds=departamentos_por_etapa.get(etapa.id, []),
                )
                for etapa in etapas
            ]
            for demanda_id, etapas in etapas_por_demanda.items()
        }

    @staticmethod
    def _derivar_etapa_atual_id(etapas: list[DemandaWorkflowEtapaRead]) -> str | None:
        """Etapa atual = menor `ordem` com `status != 'concluida'`. Derivado sempre em
        runtime, nunca persistido (ver docstring de DemandaWorkflowEtapa)."""
        pendentes = [etapa for etapa in etapas if etapa.status != STATUS_ETAPA_WORKFLOW_CONCLUIDA]
        if not pendentes:
            return None
        return str(min(pendentes, key=lambda etapa: etapa.ordem).id)

    @staticmethod
    def _campos_base(demanda: Demanda) -> dict:
        # `checklist`/`arquivos` (2E.3) e `comentarios`/`historico` (2E.4) NÃO aparecem
        # aqui: todos têm tabela e endpoint dedicado agora, fora do payload de Demanda —
        # embuti-los de novo infligiria em toda listagem um dado que só é necessário ao
        # abrir uma Demanda específica.
        return {
            "id": demanda.id,
            "empresaId": demanda.empresa_id,
            "codigoReferencia": demanda.codigo_referencia,
            "anoReferencia": demanda.ano_referencia,
            "sequencialReferencia": demanda.sequencial_referencia,
            "numeroOperacional": demanda.numero_operacional,
            "nome": demanda.nome,
            "pit": demanda.pit,
            "briefing": demanda.briefing,
            "status": demanda.status,
            "prioridade": demanda.prioridade,
            "sinalizada": demanda.sinalizada,
            "motivoBloqueio": demanda.motivo_bloqueio,
            "clienteId": demanda.cliente_id,
            "projetoId": demanda.projeto_id,
            "criadoPorUsuarioId": demanda.criado_por_usuario_id,
            "workflowModeloId": demanda.workflow_modelo_id,
            "dataInicio": demanda.data_inicio,
            "dataFimPrevista": demanda.data_fim_prevista,
            "prazoEtapaAtual": demanda.prazo_etapa_atual,
            "enviadoClienteEm": demanda.enviado_cliente_em,
            "prazoRetornoCliente": demanda.prazo_retorno_cliente,
            "retornoRecebidoEm": demanda.retorno_recebido_em,
            "emailConclusaoEnviado": demanda.email_conclusao_enviado,
            "emailConclusaoData": demanda.email_conclusao_data,
            "createdAt": demanda.created_at,
            "updatedAt": demanda.updated_at,
            "arquivadoAt": demanda.arquivado_at,
            "arquivadoPorUsuarioId": demanda.arquivado_por_usuario_id,
            "motivoArquivamento": demanda.motivo_arquivamento,
            "restauradoAt": demanda.restaurado_at,
            "restauradoPorUsuarioId": demanda.restaurado_por_usuario_id,
            "statusAnteriorArquivamento": demanda.status_anterior_arquivamento,
        }

    # ----------------------------------------------------------------------------------
    # Regras
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _ensure_regras_de_status(status: str, motivo_bloqueio: str | None) -> None:
        """Não há máquina de estados: qualquer transição entre valores válidos é aceita.

        A única regra é o acoplamento `bloqueada` ⇄ motivo. O schema já rejeita motivo
        só-espaços; aqui se verifica a **presença**.
        """
        if status == STATUS_BLOQUEADA and not (motivo_bloqueio or "").strip():
            raise DemandaMotivoBloqueioObrigatorioError(
                "motivoBloqueio é obrigatório para status 'bloqueada'"
            )

    def _ensure_dentro_expediente(self) -> None:
        if esta_dentro_expediente(regra=self.regra_expediente):
            return
        regra = self.regra_expediente
        raise DemandaForaDeExpedienteError(
            "Fora do expediente: execução permitida das "
            f"{regra.manha_inicio} às {regra.manha_fim} e das {regra.tarde_inicio} às {regra.tarde_fim}",
            regra=regra,
        )

    def _ensure_cliente_valido(self, db: Session, empresa_id: str, cliente_id: str) -> None:
        cliente = self.cliente_repository.get_by_id(db, cliente_id)
        if cliente is None or cliente.empresa_id != empresa_id:
            raise DemandaClienteInvalidoError("Cliente não encontrado para esta empresa")
        if cliente.status == "arquivado":
            raise DemandaClienteInvalidoError(
                "Cliente arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _ensure_projeto_valido(self, db: Session, empresa_id: str, projeto_id: str) -> None:
        projeto = self.projeto_repository.get_by_id(db, projeto_id)
        if projeto is None or projeto.empresa_id != empresa_id:
            raise DemandaProjetoInvalidoError("Projeto não encontrado para esta empresa")
        if projeto.status == "arquivado":
            raise DemandaProjetoInvalidoError(
                "Projeto arquivado não aceita novos vínculos — restaure-o antes"
            )

    def _ensure_workflow_modelo_valido(self, db: Session, empresa_id: str, workflow_modelo_id: str) -> None:
        workflow_modelo = self.workflow_modelo_repository.get_by_id(db, workflow_modelo_id)
        if workflow_modelo is None or workflow_modelo.empresa_id != empresa_id:
            raise DemandaWorkflowModeloInvalidoError("Modelo de workflow não encontrado para esta empresa")
        if workflow_modelo.status != WORKFLOW_MODELO_STATUS_ATIVO:
            raise DemandaWorkflowModeloInvalidoError(
                "Modelo de workflow precisa estar ativo para ser aplicado a uma nova tarefa"
            )

    def _materializar_workflow(
        self,
        db: Session,
        demanda: Demanda,
        *,
        workflow_modelo_id: str,
        empresa_id: str,
        now: datetime,
    ) -> None:
        """Copia as etapas (e responsáveis) do WorkflowModelo pra Demanda — snapshot, não
        referência viva. Roda dentro da MESMA transação de `create_demanda`: qualquer erro
        aqui (ex.: responsável do template que ficou inválido nesse meio-tempo) sobe e o
        rollback do método chamador desfaz a Demanda inteira junto — nenhuma etapa órfã.

        Reaproveita `_ensure_usuario_valido`/`_ensure_departamento_valido` (as mesmas regras
        já usadas pros responsáveis diretos da Demanda) em vez de confiar cegamente no que o
        template tinha — um responsável pode ter sido arquivado depois da última edição do
        WorkflowModelo.
        """
        etapas_modelo = self.workflow_modelo_repository.list_etapas(db, workflow_modelo_id)
        etapa_ids_modelo = [etapa.id for etapa in etapas_modelo]
        usuarios_por_etapa = self.workflow_modelo_repository.get_responsavel_ids_por_etapa(
            db, etapa_ids_modelo
        )
        departamentos_por_etapa = self.workflow_modelo_repository.get_departamento_responsavel_ids_por_etapa(
            db, etapa_ids_modelo
        )

        etapas_objetos = [
            DemandaWorkflowEtapa(
                id=str(uuid4()),
                demanda_id=demanda.id,
                ordem=etapa_modelo.ordem,
                nome=etapa_modelo.nome,
                tipo=etapa_modelo.tipo,
                quantidade_antes_deadline=etapa_modelo.quantidade_antes_deadline,
                unidade_prazo=etapa_modelo.unidade_prazo,
                status=STATUS_ETAPA_WORKFLOW_PENDENTE,
                created_at=now,
                updated_at=now,
            )
            for etapa_modelo in etapas_modelo
        ]
        self.repository.criar_etapas_workflow(db, etapas_objetos)

        responsavel_rows: list[DemandaWorkflowEtapaResponsavel] = []
        departamento_responsavel_rows: list[DemandaWorkflowEtapaDepartamentoResponsavel] = []
        for etapa_modelo, etapa_objeto in zip(etapas_modelo, etapas_objetos):
            for usuario_id in usuarios_por_etapa.get(etapa_modelo.id, []):
                self._ensure_usuario_valido(db, empresa_id, usuario_id)
                responsavel_rows.append(
                    DemandaWorkflowEtapaResponsavel(
                        demanda_workflow_etapa_id=etapa_objeto.id, usuario_id=usuario_id, created_at=now
                    )
                )
            for departamento_id in departamentos_por_etapa.get(etapa_modelo.id, []):
                self._ensure_departamento_valido(db, empresa_id, departamento_id)
                departamento_responsavel_rows.append(
                    DemandaWorkflowEtapaDepartamentoResponsavel(
                        demanda_workflow_etapa_id=etapa_objeto.id,
                        departamento_id=departamento_id,
                        created_at=now,
                    )
                )

        self.repository.criar_etapa_responsaveis(db, responsavel_rows)
        self.repository.criar_etapa_departamentos_responsaveis(db, departamento_responsavel_rows)

    def _ensure_usuario_valido(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise DemandaUsuarioInvalidoError("Usuário não encontrado para esta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO:
            raise DemandaUsuarioInvalidoError(
                f"Usuário em status '{usuario.status}' não aceita novos vínculos"
            )

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise DemandaDepartamentoInvalidoError("Departamento não encontrado para esta empresa")
        if departamento.status == "arquivado":
            raise DemandaDepartamentoInvalidoError(
                "Departamento arquivado não aceita novos vínculos — restaure-o antes"
            )

    # ----------------------------------------------------------------------------------
    # Vínculos
    # ----------------------------------------------------------------------------------

    def _sincronizar_responsaveis(
        self, db: Session, demanda: Demanda, desejados: list[str]
    ) -> list[tuple[DomainEventType, dict]]:
        atuais = set(self.repository.listar_responsavel_ids(db, demanda.id))
        alvo = set(desejados)
        adicionar, remover = sorted(alvo - atuais), sorted(atuais - alvo)

        # Só o que ENTRA é validado: vínculo histórico com alguém depois inativado é
        # preservado, mas não pode ser criado de novo.
        for usuario_id in adicionar:
            self._ensure_usuario_valido(db, demanda.empresa_id, usuario_id)

        now = agora_utc()
        for usuario_id in adicionar:
            self.repository.adicionar_responsavel(
                db, DemandaResponsavel(demanda_id=demanda.id, usuario_id=usuario_id, created_at=now)
            )
        for usuario_id in remover:
            self.repository.remover_responsavel(db, demanda_id=demanda.id, usuario_id=usuario_id)

        return [
            (DomainEventType.DEMANDA_RESPONSAVEL_ADICIONADO, {"usuarioId": uid}) for uid in adicionar
        ] + [(DomainEventType.DEMANDA_RESPONSAVEL_REMOVIDO, {"usuarioId": uid}) for uid in remover]

    def _sincronizar_departamentos(
        self, db: Session, demanda: Demanda, desejados: list[str]
    ) -> list[tuple[DomainEventType, dict]]:
        atuais = set(self.repository.listar_departamento_ids(db, demanda.id))
        alvo = set(desejados)
        adicionar, remover = sorted(alvo - atuais), sorted(atuais - alvo)

        for departamento_id in adicionar:
            self._ensure_departamento_valido(db, demanda.empresa_id, departamento_id)

        now = agora_utc()
        for departamento_id in adicionar:
            self.repository.adicionar_departamento(
                db,
                DemandaDepartamento(
                    demanda_id=demanda.id, departamento_id=departamento_id, created_at=now
                ),
            )
        for departamento_id in remover:
            self.repository.remover_departamento(
                db, demanda_id=demanda.id, departamento_id=departamento_id
            )

        return [
            (DomainEventType.DEMANDA_DEPARTAMENTO_ADICIONADO, {"departamentoId": did})
            for did in adicionar
        ] + [
            (DomainEventType.DEMANDA_DEPARTAMENTO_REMOVIDO, {"departamentoId": did})
            for did in remover
        ]

    def _publish_event(
        self,
        db: Session,
        demanda: Demanda,
        tipo: DomainEventType,
        actor_usuario_id: str | None,
        *,
        extra_payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> Evento:
        timestamp = occurred_at or agora_utc()
        payload = {
            "empresa_id": demanda.empresa_id,
            "demanda_id": demanda.id,
            "codigo_referencia": demanda.codigo_referencia,
            # No payload também, porque é por ele que a operação identifica a demanda ao ler
            # uma auditoria — `T26000001` é oficial, `#2063` é o que a pessoa reconhece.
            "numero_operacional": demanda.numero_operacional,
            "timestamp": timestamp.isoformat(),
            "status": demanda.status,
        }
        if extra_payload:
            payload.update(extra_payload)

        return self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=demanda.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=demanda.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=timestamp,
        )
