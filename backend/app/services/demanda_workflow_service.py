"""Progressão do snapshot de Workflow de uma Demanda (Fase 8A): concluir (execução) / aprovar (aprovação) a etapa ATUAL e ativar a
próxima — tudo na MESMA transação.

Regras centrais:
- o snapshot (`demanda_workflow_etapas`) é a ÚNICA fonte; o template (`WorkflowModelo`) não é consultado aqui;
- a etapa atual é DERIVADA (menor `ordem` com `status != 'concluida'`); `UNIQUE (demanda_id, ordem)` a torna inequívoca;
- o servidor decide a próxima (menor `ordem` seguinte) — o cliente só diz QUAL etapa quer concluir/aprovar, nunca o destino;
- a Demanda é travada (`SELECT … FOR UPDATE`) antes de ler as etapas: duas ações simultâneas na mesma etapa são serializadas e a
  segunda, ao obter o lock, vê a etapa já concluída → 409, sem avançar de novo nem gravar evento;
- UM evento por ação (`demanda.workflow_etapa_concluida` / `demanda.workflow_etapa_aprovada`), gravado na mesma transação, com a próxima
  etapa no payload;
- concluir o ÚLTIMO passo encerra o workflow (derivado: todas `concluida`) e NÃO conclui a Demanda;
- prazo (`prazo_etapa_atual`) não é tocado: é um campo manual e independente.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.core.workflow_destinatarios import destinatarios_da_etapa
from app.core.workflow_autoridade import departamentos_head_para_workflow, pode_avancar_etapa
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.usuario import Usuario
from app.repositories.demanda_repository import DemandaRepository
from app.services.demanda_service import DemandaService

AcaoEtapa = Literal["concluir", "aprovar"]

STATUS_ETAPA_CONCLUIDA = "concluida"
STATUS_ETAPA_PAUSADA = "pausada"
STATUS_DEMANDA_ARQUIVADA = "arquivada"

# ação → (tipo de etapa que ela atende, evento publicado)
_ACAO: dict[str, tuple[str, DomainEventType]] = {
    "concluir": ("execucao", DomainEventType.DEMANDA_WORKFLOW_ETAPA_CONCLUIDA),
    "aprovar": ("aprovacao", DomainEventType.DEMANDA_WORKFLOW_ETAPA_APROVADA),
}


class DemandaWorkflowEtapaNaoEncontradaError(LookupError):
    """A etapa não pertence a esta Demanda (ou não existe). Vira 404 — sem confirmar existência em outra demanda/empresa."""


class DemandaWorkflowAcaoInvalidaError(ValueError):
    """Ação incompatível com o tipo da etapa (concluir uma etapa de aprovação, aprovar uma de execução). Vira 422."""


class DemandaWorkflowSemAutoridadeError(PermissionError):
    """O usuário não é responsável pela etapa, nem admin/gestor do tenant, nem Head de um departamento da etapa. Vira 403."""


class DemandaWorkflowConflitoError(RuntimeError):
    """Estado que impede a transição. Vira 409, com `codigo` estável para a interface."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class DemandaWorkflowService:
    def __init__(
        self,
        repository: DemandaRepository | None = None,
        demanda_service: DemandaService | None = None,
    ) -> None:
        self.repository = repository or DemandaRepository()
        self.demanda_service = demanda_service or DemandaService(repository=self.repository)

    # ----------------------------------------------------------------------------------
    # Entradas públicas: só validam a AÇÃO e delegam ao mesmo mecanismo transacional
    # ----------------------------------------------------------------------------------

    def concluir_etapa(self, db: Session, demanda: Demanda, *, etapa_id: str, actor: Usuario) -> Demanda:
        return self._avancar_etapa(db, demanda, etapa_id=etapa_id, acao="concluir", actor=actor)

    def aprovar_etapa(self, db: Session, demanda: Demanda, *, etapa_id: str, actor: Usuario) -> Demanda:
        return self._avancar_etapa(db, demanda, etapa_id=etapa_id, acao="aprovar", actor=actor)

    # ----------------------------------------------------------------------------------
    # Transição central
    # ----------------------------------------------------------------------------------

    def rejeitar_etapa(self, db: Session, demanda: Demanda, *, etapa_id: str, motivo: str, actor: Usuario) -> Demanda:
        """Fase 8D — rejeita a etapa ATUAL de APROVAÇÃO e DEVOLVE o workflow para a etapa imediatamente anterior (decidida aqui, nunca pelo cliente).

        Mesmo preâmbulo/lock/autoridade da ação Aprovar. A aprovação rejeitada volta a `pendente` sem início (será feita de novo); a anterior é
        REABERTA (`pendente`, `iniciada_em` = agora, conclusão e ator zerados). O histórico é append-only: o evento de rejeição guarda quem, quando, o
        motivo e a etapa de retorno, e os eventos de conclusão anteriores continuam intactos. Retry/concorrência (aprovar × rejeitar, rejeitar ×
        rejeitar) → 409 para quem perde o lock, sem evento nem notificação. Não toca status/prazo/responsáveis da Demanda."""
        try:
            etapas, etapa = self._preparar_etapa_atual(db, demanda, etapa_id=etapa_id, tipo_esperado="aprovacao", acao="rejeitar", actor=actor)
            anterior = max((item for item in etapas if item.ordem < etapa.ordem), key=lambda item: item.ordem, default=None)
            if anterior is None:
                raise DemandaWorkflowConflitoError(
                    "SEM_ETAPA_ANTERIOR", "Esta é a primeira etapa do workflow: não há etapa anterior para devolver"
                )

            now = agora_utc()
            # a aprovação que não passou volta a ser uma etapa a fazer — sem início, sem conclusão, sem ator
            etapa.status = "pendente"
            etapa.iniciada_em = None
            etapa.concluida_em = None
            etapa.concluida_por_usuario_id = None
            etapa.updated_at = now
            # a etapa de retorno é reaberta: volta a ser a atual (derivada) e recomeça agora
            anterior.status = "pendente"
            anterior.concluida_em = None
            anterior.concluida_por_usuario_id = None
            anterior.iniciada_em = now
            anterior.updated_at = now
            demanda.updated_at = now
            db.flush()

            self.demanda_service.publicar_evento_demanda(
                db,
                demanda,
                DomainEventType.DEMANDA_WORKFLOW_ETAPA_REJEITADA,
                actor.id,
                extra_payload={
                    "workflowModeloId": demanda.workflow_modelo_id,
                    "etapaId": etapa.id,
                    "etapaNome": etapa.nome,
                    "etapaOrdem": etapa.ordem,
                    "etapaTipo": etapa.tipo,
                    "motivo": motivo,
                    "atorUsuarioId": actor.id,
                    "etapaRetornoId": anterior.id,
                    "etapaRetornoNome": anterior.nome,
                    "etapaRetornoOrdem": anterior.ordem,
                },
                occurred_at=now,
            )
            # Notifica quem precisa agir na etapa REABERTA (mesmo mecanismo da 8C, texto de devolução; o motivo fica só no histórico).
            self._notificar_proxima_etapa(db, demanda, anterior, actor, now, devolvida=True)
            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    # ----------------------------------------------------------------------------------
    # Preâmbulo compartilhado (lock, snapshot, ação × tipo, autoridade, etapa atual)
    # ----------------------------------------------------------------------------------

    def _preparar_etapa_atual(
        self, db: Session, demanda: Demanda, *, etapa_id: str, tipo_esperado: str, acao: str, actor: Usuario
    ) -> tuple[list[DemandaWorkflowEtapa], DemandaWorkflowEtapa]:
        """Trava a Demanda, relê o snapshot e valida a etapa pedida: 404 (não é desta demanda) → 422 (tipo × ação) → 403 (autoridade) → 409 (não é a
        atual / workflow concluído / pausada / demanda arquivada). Devolve `(etapas ordenadas, etapa)`; quem chama muta e comita na MESMA transação."""
        # 1) trava a Demanda e recarrega o estado COMMITADO mais recente (quem esperou o lock vê o resultado do vencedor)
        self.repository.bloquear_demanda_para_atualizacao(db, demanda)
        if demanda.status == STATUS_DEMANDA_ARQUIVADA:
            raise DemandaWorkflowConflitoError(
                "DEMANDA_ARQUIVADA", "Demanda arquivada não pode ter o workflow alterado — restaure-a antes"
            )

        # 2) snapshot atual (já com o lock; `populate_existing` ignora cópias antigas do identity map)
        etapas = self.repository.listar_etapas_workflow_travadas(db, demanda.id)
        if not etapas:
            if demanda.workflow_modelo_id is None:
                raise DemandaWorkflowConflitoError("SEM_WORKFLOW", "Esta tarefa não possui workflow")
            raise DemandaWorkflowConflitoError(
                "WORKFLOW_SEM_ETAPAS", "O workflow desta tarefa não possui etapas materializadas"
            )

        etapa = next((item for item in etapas if item.id == etapa_id), None)
        if etapa is None:
            raise DemandaWorkflowEtapaNaoEncontradaError("Etapa não encontrada nesta tarefa")

        # 3) ação × tipo, e autoridade — ANTES de revelar o estado do fluxo
        if etapa.tipo != tipo_esperado:
            if acao == "rejeitar":
                raise DemandaWorkflowAcaoInvalidaError("Só uma etapa de aprovação pode ser rejeitada")
            rotulo = "aprovada" if etapa.tipo == "aprovacao" else "concluída"
            raise DemandaWorkflowAcaoInvalidaError(f"Esta etapa deve ser {rotulo}, não usar a ação '{acao}'")
        usuarios_por_etapa = self.repository.listar_etapa_responsavel_ids_em_lote(db, [etapa.id])
        departamentos_por_etapa = self.repository.listar_etapa_departamento_ids_em_lote(db, [etapa.id])
        if not pode_avancar_etapa(
            actor,
            usuario_responsavel_ids=usuarios_por_etapa.get(etapa.id, []),
            departamento_responsavel_ids=departamentos_por_etapa.get(etapa.id, []),
            departamentos_head=departamentos_head_para_workflow(db, actor),
        ):
            raise DemandaWorkflowSemAutoridadeError("Você não tem autoridade para avançar esta etapa")

        # 4) a etapa precisa ser a ATUAL (derivada) — retry/duplo clique/concorrência caem aqui
        atual = next((item for item in etapas if item.status != STATUS_ETAPA_CONCLUIDA), None)
        if atual is None:
            raise DemandaWorkflowConflitoError("WORKFLOW_CONCLUIDO", "O workflow desta tarefa já foi concluído")
        if atual.id != etapa.id:
            codigo = "ETAPA_JA_CONCLUIDA" if etapa.status == STATUS_ETAPA_CONCLUIDA else "ETAPA_NAO_ATUAL"
            raise DemandaWorkflowConflitoError(codigo, "Esta não é a etapa atual do workflow")
        if etapa.status == STATUS_ETAPA_PAUSADA:
            # Nenhum fluxo cria/retoma pausa hoje; conservador: não avança nem rejeita uma etapa pausada.
            raise DemandaWorkflowConflitoError("ETAPA_PAUSADA", "A etapa atual está pausada")
        return etapas, etapa

    def _avancar_etapa(
        self, db: Session, demanda: Demanda, *, etapa_id: str, acao: AcaoEtapa, actor: Usuario
    ) -> Demanda:
        """Recebe a Demanda JÁ resolvida no escopo (base ou derivado do Workflow) pela rota (nunca um id solto)."""
        tipo_esperado, tipo_evento = _ACAO[acao]
        try:
            etapas, etapa = self._preparar_etapa_atual(db, demanda, etapa_id=etapa_id, tipo_esperado=tipo_esperado, acao=acao, actor=actor)

            # 5) conclui a atual e ativa a próxima (menor `ordem` seguinte — decidida aqui, nunca pelo cliente)
            now = agora_utc()
            etapa.status = STATUS_ETAPA_CONCLUIDA
            etapa.concluida_em = now
            etapa.concluida_por_usuario_id = actor.id
            etapa.updated_at = now

            proxima = next(
                (item for item in etapas if item.ordem > etapa.ordem and item.status != STATUS_ETAPA_CONCLUIDA), None
            )
            if proxima is not None:
                if proxima.iniciada_em is None:
                    proxima.iniciada_em = now
                proxima.updated_at = now
            demanda.updated_at = now
            db.flush()

            # 6) UM evento por ação, na mesma transação
            self.demanda_service.publicar_evento_demanda(
                db,
                demanda,
                tipo_evento,
                actor.id,
                extra_payload={
                    "workflowModeloId": demanda.workflow_modelo_id,
                    "etapaId": etapa.id,
                    "etapaNome": etapa.nome,
                    "etapaOrdem": etapa.ordem,
                    "etapaTipo": etapa.tipo,
                    "atorUsuarioId": actor.id,
                    "proximaEtapaId": proxima.id if proxima else None,
                    "proximaEtapaNome": proxima.nome if proxima else None,
                    "proximaEtapaOrdem": proxima.ordem if proxima else None,
                    "workflowConcluido": proxima is None,
                },
                occurred_at=now,
            )
            # 7) Fase 8C — notificação da PRÓXIMA etapa, na mesma transação (só o vencedor chega aqui: retry/concorrência → 409 antes).
            # Um único evento com a lista de destinatários; sem destinatário (etapa sem responsável) não há evento e o avanço segue.
            if proxima is not None:
                self._notificar_proxima_etapa(db, demanda, proxima, actor, now)
            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

    def _notificar_proxima_etapa(
        self, db: Session, demanda: Demanda, proxima: DemandaWorkflowEtapa, actor: Usuario, now, *, devolvida: bool = False
    ) -> None:
        usuarios = self.repository.listar_etapa_responsavel_ids_em_lote(db, [proxima.id]).get(proxima.id, [])
        departamentos = self.repository.listar_etapa_departamento_ids_em_lote(db, [proxima.id]).get(proxima.id, [])
        destinatarios = destinatarios_da_etapa(
            db,
            empresa_id=demanda.empresa_id,  # da Demanda (tenant do token), nunca de dado do cliente
            usuario_responsavel_ids=usuarios,
            departamento_responsavel_ids=departamentos,
        )
        if not destinatarios:
            return
        self.demanda_service.publicar_evento_demanda(
            db,
            demanda,
            DomainEventType.DEMANDA_WORKFLOW_ETAPA_ATUALIZADA,
            actor.id,
            extra_payload={
                "workflowEtapaId": proxima.id,
                "etapaNome": proxima.nome,
                "etapaOrdem": proxima.ordem,
                "etapaTipo": proxima.tipo,
                "destinatarioUsuarioIds": destinatarios,
                # Fase 8D: a etapa voltou a ser a atual por DEVOLUÇÃO (rejeição). Só muda o texto da notificação; o motivo fica no histórico.
                **({"devolvida": True} if devolvida else {}),
            },
            occurred_at=now,
        )
