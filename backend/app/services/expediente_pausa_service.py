"""Pausa automática no fim dos períodos do expediente — Fase Expediente 3 (o TICK do backend).

O que faz, por empresa com `ativo` e `pausar_no_fim_periodo` ligados, quando há um CORTE pendente (`cutoff_pendente`: o fim de período mais recente, posterior à
"armadura" da pausa e sem nenhum período novo já iniciado):

1. encerra as sessões pessoais ativas das Demandas em execução cujos donos estão SUJEITOS à política (motivo `fim_expediente`, fim = o CORTE, não o instante do tick);
2. se sobrou sessão ativa VÁLIDA de uma pessoa ISENTA na mesma Demanda, a Demanda continua em execução (não se infere atividade só porque o gestor é responsável);
3. senão, pausa a Demanda: `pausa_origem='expediente'`, `pausada_em = corte`, evento `demanda.status_alterado` (de=em_execucao, para=pausada) SEM usuário ator
   (ação do sistema), todos com o mesmo `correlation_id` da execução;
4. grava, por pessoa afetada, UM evento-resumo (`expediente.pausa_automatica_aplicada`) — só se alguma Demanda foi de fato pausada — e, por fim, o registro de conclusão do
   corte (`expediente.pausa_automatica_executada`).

Garantias:
- **Sem logout, sem retomada, sem relógio do cliente.** Quem chama é um loop de backend (`app/core/expediente_tick.py`).
- **Idempotência**: chave determinística `expediente:<empresa>:<dia-local>:<HH:MM>` → `correlation_id` UUID v5. O registro de conclusão impede repetir o corte depois de
  restart/retry (retry nunca pausa duas vezes, fecha sessão duas vezes, duplica evento ou aviso). Sem ele, reprocessar às 18:30 repausaria o que um isento reabriu.
- **Multi-instância**: `pg_try_advisory_xact_lock` por (empresa, corte) — solta sozinho no commit/rollback/queda da conexão (sucesso, erro ou cancelamento).
- **Granularidade**: UMA transação por empresa+corte, com um SAVEPOINT por Demanda. Atomicidade por Demanda (sessões fechadas + pausa + evento nunca ficam pela metade) sem
  uma transação por demanda solta; uma Demanda que falha NÃO impede as outras e o registro de conclusão só é gravado se todas deram certo (a próxima rodada refaz só as
  que ficaram). Tradeoff: o lock de linhas dura o tempo do corte (dezenas de Demandas, milissegundos) em vez de commits intermediários.
- **Serialização com o usuário**: as Demandas em execução são lidas `FOR UPDATE`; `update_demanda` (mudança de status) e `abrir sessão` travam a linha ANTES de decidir
  e conferem o gate de horário depois do lock — 11:59:59 × tick das 12:00 nunca deixa "sessão ativa + Demanda pausada".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.expediente import (
    chave_de_execucao,
    correlation_id_da_execucao,
    cutoff_pendente,
    momento_local,
    usuario_sujeito_ao_expediente,
)
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.evento import Evento
from app.models.regra_expediente import RegraExpediente as RegraExpedienteModel
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.services.demanda_service import DemandaService
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.regra_expediente_service import RegraExpedienteService
from app.services.sessao_trabalho_service import MOTIVO_FIM_EXPEDIENTE, STATUS_USUARIO_INVALIDO, SessaoTrabalhoService

logger = logging.getLogger(__name__)

ORIGEM_PAUSA_EXPEDIENTE = "expediente"
# Um corte processado com atraso maior que isto (restart/queda do tick) vira aviso de observabilidade — ainda pode ser processado enquanto nenhum período novo começou.
LIMITE_ATRASO_SEM_AVISO = timedelta(minutes=5)


@dataclass
class ResultadoCorte:
    empresa_id: str
    status: str  # sem_corte | lock_ocupado | ja_executado | executado | parcial
    corte: datetime | None = None
    chave: str | None = None
    demandas_pausadas: list[str] = field(default_factory=list)
    demandas_preservadas: list[str] = field(default_factory=list)
    sessoes_encerradas: int = 0
    falhas: int = 0
    avisos: dict[str, int] = field(default_factory=dict)  # usuario_id -> quantidade pausada relevante


class ExpedientePausaService:
    def __init__(
        self,
        regra_service: RegraExpedienteService | None = None,
        sessao_service: SessaoTrabalhoService | None = None,
        demanda_service: DemandaService | None = None,
        event_publisher: DomainEventPublisher | None = None,
        sessao_repository: SessaoTrabalhoRepository | None = None,
    ) -> None:
        self.regra_service = regra_service or RegraExpedienteService()
        self.sessao_service = sessao_service or SessaoTrabalhoService()
        self.demanda_service = demanda_service or DemandaService()
        self.event_publisher = event_publisher or DomainEventPublisher()
        self.sessao_repository = sessao_repository or SessaoTrabalhoRepository()

    # ------------------------------------------------------------------------------------------------------------------
    # Entrada do tick
    # ------------------------------------------------------------------------------------------------------------------

    def executar_tick(self, session_factory: Callable[[], Session], agora: datetime | None = None) -> list[ResultadoCorte]:
        """Uma rodada do tick: todas as empresas com a pausa ligada. Cada empresa numa sessão/transação própria; o erro de uma não derruba as outras."""
        db = session_factory()
        try:
            empresas = list(
                db.scalars(
                    select(RegraExpedienteModel.empresa_id).where(
                        RegraExpedienteModel.ativo.is_(True), RegraExpedienteModel.pausar_no_fim_periodo.is_(True)
                    )
                ).all()
            )
        finally:
            db.close()
        resultados: list[ResultadoCorte] = []
        for empresa_id in empresas:
            db = session_factory()
            try:
                resultados.append(self.processar_empresa(db, empresa_id, agora))
            except Exception:  # noqa: BLE001 — uma empresa com problema nunca derruba o tick das outras
                logger.exception("expediente_pausa_erro empresa=%s", empresa_id)
                db.rollback()
            finally:
                db.close()
        return resultados

    def processar_empresa(self, db: Session, empresa_id: str, agora: datetime | None = None) -> ResultadoCorte:
        regra = self.regra_service.get_regra_calculo(db, empresa_id=empresa_id)
        momento = momento_local(agora, regra)
        corte = cutoff_pendente(momento, regra)
        if corte is None:
            db.rollback()  # fecha a transação de leitura aberta
            return ResultadoCorte(empresa_id=empresa_id, status="sem_corte")
        chave = chave_de_execucao(empresa_id, corte)
        correlation_id = correlation_id_da_execucao(chave)

        # Lock por (empresa, corte): outra instância processando o MESMO corte faz esta desistir (ela terminará ou o próximo tick reavalia). Solta no commit/rollback.
        if not self._travar(db, chave):
            db.rollback()
            logger.info("expediente_pausa_lock_ocupado chave=%s", chave)
            return ResultadoCorte(empresa_id=empresa_id, status="lock_ocupado", corte=corte, chave=chave)
        try:
            # Relê TUDO depois do lock: a regra pode ter sido desligada/rearmada e outra instância pode ter concluído o corte enquanto esta esperava.
            db.expire_all()
            regra = self.regra_service.get_regra_calculo(db, empresa_id=empresa_id)
            if cutoff_pendente(momento, regra) != corte:
                db.rollback()
                return ResultadoCorte(empresa_id=empresa_id, status="sem_corte")
            if self._ja_executado(db, empresa_id, correlation_id):
                db.rollback()
                return ResultadoCorte(empresa_id=empresa_id, status="ja_executado", corte=corte, chave=chave)

            atraso = momento - corte
            if atraso > LIMITE_ATRASO_SEM_AVISO:
                logger.warning(
                    "expediente_corte_perdido_processado_em_catch_up empresa=%s corte=%s atraso_s=%d",
                    empresa_id, corte.isoformat(), int(atraso.total_seconds()),
                )

            resultado = ResultadoCorte(empresa_id=empresa_id, status="executado", corte=corte, chave=chave)
            demandas = list(
                db.scalars(
                    select(Demanda)
                    .where(Demanda.empresa_id == empresa_id, Demanda.status == "em_execucao")
                    .order_by(Demanda.id.asc())
                    .with_for_update()
                    .execution_options(populate_existing=True)
                ).all()
            )
            afetados_por_demanda: dict[str, set[str]] = {}
            for demanda in demandas:
                savepoint = db.begin_nested()
                try:
                    pausou, afetados, fechadas = self._processar_demanda(db, demanda, corte, chave, correlation_id)
                    savepoint.commit()
                except Exception:  # noqa: BLE001 — a Demanda que falha volta ao estado anterior (savepoint) e o corte NÃO é dado como concluído
                    savepoint.rollback()
                    resultado.falhas += 1
                    logger.exception("expediente_pausa_demanda_falhou empresa=%s demanda=%s chave=%s", empresa_id, demanda.id, chave)
                    continue
                resultado.sessoes_encerradas += fechadas
                if pausou:
                    resultado.demandas_pausadas.append(demanda.id)
                    afetados_por_demanda[demanda.id] = afetados
                else:
                    resultado.demandas_preservadas.append(demanda.id)

            self._resumo_por_pessoa(db, empresa_id, corte, chave, correlation_id, afetados_por_demanda, resultado)
            if resultado.falhas == 0:
                self.event_publisher.publish(
                    db,
                    tipo=DomainEventType.EXPEDIENTE_PAUSA_AUTOMATICA_EXECUTADA,
                    empresa_id=empresa_id,
                    entidade_tipo="empresa",
                    entidade_id=empresa_id,
                    usuario_id=None,
                    correlation_id=correlation_id,
                    metadata={"origem": "sistema", "fonte": ORIGEM_PAUSA_EXPEDIENTE},
                    payload={
                        "chaveExecucao": chave,
                        "cutoff": corte.isoformat(),
                        "demandasPausadas": len(resultado.demandas_pausadas),
                        "demandasPreservadas": len(resultado.demandas_preservadas),
                        "sessoesEncerradas": resultado.sessoes_encerradas,
                    },
                    occurred_at=corte,
                )
            else:
                resultado.status = "parcial"
            db.commit()
            return resultado
        except Exception:
            db.rollback()
            raise

    # ------------------------------------------------------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _travar(db: Session, chave: str) -> bool:
        return bool(db.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:chave, 0))"), {"chave": chave}).scalar())

    @staticmethod
    def _ja_executado(db: Session, empresa_id: str, correlation_id: str) -> bool:
        return (
            db.scalar(
                select(Evento.id)
                .where(
                    Evento.empresa_id == empresa_id,
                    Evento.tipo == DomainEventType.EXPEDIENTE_PAUSA_AUTOMATICA_EXECUTADA.value,
                    Evento.correlation_id == correlation_id,
                )
                .limit(1)
            )
            is not None
        )

    def _processar_demanda(
        self, db: Session, demanda: Demanda, corte: datetime, chave: str, correlation_id: str
    ) -> tuple[bool, set[str], int]:
        """(pausou?, pessoas afetadas, sessões encerradas). Tudo dentro do SAVEPOINT da Demanda."""
        sessoes = self.sessao_repository.listar_ativas_para_encerramento(db, empresa_id=demanda.empresa_id, demanda_id=demanda.id)
        usuarios = {
            u.id: u
            for u in db.scalars(select(Usuario).where(Usuario.id.in_([s.usuario_id for s in sessoes if s.usuario_id] or [""]))).all()
        }
        fechadas_de_usuarios: set[str] = set()
        total_fechadas = 0
        isento_ativo_valido = False
        a_fechar_apos_decidir: list[SessaoTrabalho] = []
        for sessao in sessoes:
            usuario = usuarios.get(sessao.usuario_id) if sessao.usuario_id else None
            sujeito = usuario is None or usuario_sujeito_ao_expediente(
                perfil_base=usuario.perfil_base,
                is_system_account=bool(usuario.is_system_account),
                acesso_fora_expediente=bool(usuario.acesso_fora_expediente),
            )
            if sujeito:
                self.sessao_service.encerrar_por_expediente(db, sessao, corte=corte, chave=chave, correlation_id=correlation_id)
                total_fechadas += 1
                if sessao.usuario_id:
                    fechadas_de_usuarios.add(sessao.usuario_id)
            elif usuario is not None and usuario.status not in STATUS_USUARIO_INVALIDO:
                isento_ativo_valido = True  # trabalhador isento ATIVO (sessão pessoal real): a Demanda continua em execução
            else:
                a_fechar_apos_decidir.append(sessao)  # isento inativo/arquivado/bloqueado não segura a Demanda

        if isento_ativo_valido:
            return False, set(), total_fechadas

        # Sem isento ativo: pausa. Qualquer sessão restante (isento inválido) acaba junto — nunca "sessão ativa + Demanda pausada".
        for sessao in a_fechar_apos_decidir:
            self.sessao_service.encerrar_por_expediente(db, sessao, corte=corte, chave=chave, correlation_id=correlation_id)
            total_fechadas += 1
        db.flush()

        agora = agora_utc()
        demanda.status = "pausada"
        demanda.pausa_origem = ORIGEM_PAUSA_EXPEDIENTE
        demanda.pausada_em = corte  # o instante do CORTE (12:00), não o do tick (12:00:42)
        demanda.updated_at = agora
        self.demanda_service.repository.update(db, demanda)
        evento_status = self.demanda_service.publicar_evento_demanda(
            db,
            demanda,
            DomainEventType.DEMANDA_STATUS_ALTERADO,
            None,  # ação do SISTEMA: nunca se finge um usuário
            extra_payload={
                "de": "em_execucao",
                "para": "pausada",
                "pausaOrigem": ORIGEM_PAUSA_EXPEDIENTE,
                "automatico": True,
                "origem": ORIGEM_PAUSA_EXPEDIENTE,
                "cutoff": corte.isoformat(),
                "chaveExecucao": chave,
            },
            occurred_at=corte,
            correlation_id=correlation_id,
            metadata={"origem": "sistema", "fonte": ORIGEM_PAUSA_EXPEDIENTE},
        )
        # Linha do tempo operacional (Tráfego V2): a pausa passa pelo MESMO mecanismo de qualquer transição, com o instante EFETIVO = o CORTE (12:00:00), não o do tick.
        # Sem integração especial do scheduler: fecha o intervalo `em_execucao` e abre `pausada` a partir do corte.
        self.demanda_service.intervalo_service.sincronizar(
            db, demanda, quando=corte, origem="expediente", ator_usuario_id=None, evento_id=evento_status.id, motivo_fim="fim_expediente"
        )
        afetados = self._pessoas_afetadas(db, demanda) | fechadas_de_usuarios
        return True, afetados, total_fechadas

    def _pessoas_afetadas(self, db: Session, demanda: Demanda) -> set[str]:
        """Quem tem essa Demanda como trabalho SEU, por evidência real: responsáveis atuais da Demanda e da ETAPA ATUAL (workflow). Nada global."""
        ids = set(db.scalars(select(DemandaResponsavel.usuario_id).where(DemandaResponsavel.demanda_id == demanda.id)).all())
        etapa = self.sessao_repository.get_etapa_atual(db, demanda.id)
        if etapa is not None:
            ids |= set(
                db.scalars(
                    select(DemandaWorkflowEtapaResponsavel.usuario_id).where(DemandaWorkflowEtapaResponsavel.demanda_workflow_etapa_id == etapa.id)
                ).all()
            )
        return ids

    def _resumo_por_pessoa(
        self,
        db: Session,
        empresa_id: str,
        corte: datetime,
        chave: str,
        correlation_id: str,
        afetados_por_demanda: dict[str, set[str]],
        resultado: ResultadoCorte,
    ) -> None:
        """UM evento por pessoa afetada — só com quantidade > 0. Pessoa cuja sessão foi encerrada mas cuja Demanda CONTINUOU em execução (isento ativo) não entra: o
        aviso fala de TAREFA pausada, não de sessão fechada."""
        contagem: dict[str, list[str]] = {}
        for demanda_id, pessoas in afetados_por_demanda.items():
            for usuario_id in pessoas:
                contagem.setdefault(usuario_id, []).append(demanda_id)
        if not contagem:
            return
        ativos = {
            u.id for u in db.scalars(select(Usuario).where(Usuario.id.in_(list(contagem)), Usuario.empresa_id == empresa_id)).all()
            if u.status not in STATUS_USUARIO_INVALIDO
        }
        for usuario_id in sorted(contagem):
            if usuario_id not in ativos:
                continue
            demanda_ids = sorted(contagem[usuario_id])
            self.event_publisher.publish(
                db,
                tipo=DomainEventType.EXPEDIENTE_PAUSA_AUTOMATICA_APLICADA,
                empresa_id=empresa_id,
                entidade_tipo="usuario",
                entidade_id=usuario_id,
                usuario_id=None,
                correlation_id=correlation_id,
                metadata={"origem": "sistema", "fonte": ORIGEM_PAUSA_EXPEDIENTE},
                payload={
                    "quantidade": len(demanda_ids),
                    "demandaIds": demanda_ids,
                    "cutoff": corte.isoformat(),
                    "chaveExecucao": chave,
                    "automatico": True,
                    "origem": ORIGEM_PAUSA_EXPEDIENTE,
                },
                occurred_at=corte,
            )
            resultado.avisos[usuario_id] = len(demanda_ids)
