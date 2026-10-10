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
from app.core.workflow_autoridade import departamentos_head_para_workflow, pode_avancar_etapa
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
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

    def _avancar_etapa(
        self, db: Session, demanda: Demanda, *, etapa_id: str, acao: AcaoEtapa, actor: Usuario
    ) -> Demanda:
        """Recebe a Demanda JÁ resolvida no escopo-base pela rota (nunca um id solto)."""
        tipo_esperado, tipo_evento = _ACAO[acao]
        try:
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
                # Nenhum fluxo cria/retoma pausa hoje; conservador: não avança uma etapa pausada.
                raise DemandaWorkflowConflitoError("ETAPA_PAUSADA", "A etapa atual está pausada")

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
            db.commit()
            db.refresh(demanda)
            return demanda
        except Exception:
            db.rollback()
            raise

