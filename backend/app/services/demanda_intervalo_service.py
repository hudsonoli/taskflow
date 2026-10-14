"""Motor de intervalos operacionais da Demanda — Tráfego V2, Fase 1 (a ÚNICA escrita de `demanda_status_intervalos`).

## Um mecanismo, vários pontos de entrada
Toda mudança que altera o ESTADO OPERACIONAL da Demanda chama `sincronizar` DENTRO da transação que a causou (criar, mudar status, arquivar, restaurar, trocar de etapa
no workflow, pausa automática do expediente). `sincronizar` não recebe "o que aconteceu": compara o que a Demanda É agora (status + etapa atual) com o intervalo ABERTO e
faz o mínimo — nada (idempotente), ou fecha o aberto e abre o novo. Por isso retry, mesmo status e chamadas repetidas nunca duplicam tempo, e nenhuma rota decide nada.

## Tempo EFETIVO (`quando`)
O instante é um PARÂMETRO, nunca `datetime.now()` escondido: ação manual = o instante da operação; pausa automática do expediente = o CORTE configurado (12:00:00), não o
instante em que o tick rodou (12:00:07). Se `quando` for anterior ao início do intervalo aberto (ex.: alguém abriu a Demanda às 12:00:03 e o tick aplica o corte das 12:00:00),
usa-se o início do aberto: nunca fim < início, nunca sobreposição, nunca duração negativa — com aviso estruturado.

## Estados terminais
`concluida`, `cancelada` e `arquivada` NÃO têm intervalo: só FECHAM o anterior (motivo `conclusao`/`cancelamento`/`arquivamento`). Reabrir (concluída → em execução) abre um novo.

## TEMPO OPERACIONAL ≠ TEMPO PESSOAL
Nada aqui lê ou escreve `sessoes_trabalho` nem atribui tempo a pessoas. `iniciado_por_usuario_id` é auditoria de quem provocou a abertura.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_status_intervalo import STATUS_COM_INTERVALO, DemandaStatusIntervalo
from app.repositories.demanda_status_intervalo_repository import DemandaStatusIntervaloRepository
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository

logger = logging.getLogger(__name__)

ORIGEM_CRIACAO = "criacao"
ORIGEM_TRANSICAO = "transicao"
ORIGEM_TROCA_ETAPA = "troca_etapa"
ORIGEM_RESTAURACAO = "restauracao"
ORIGEM_EXPEDIENTE = "expediente"

MOTIVO_MUDANCA_STATUS = "mudanca_status"
MOTIVO_MUDANCA_ETAPA = "mudanca_etapa"
MOTIVO_FIM_EXPEDIENTE = "fim_expediente"
# Entrar num estado TERMINAL fecha o intervalo anterior com este motivo.
MOTIVO_POR_STATUS_TERMINAL = {"concluida": "conclusao", "cancelada": "cancelamento", "arquivada": "arquivamento"}


@dataclass(frozen=True)
class ResultadoSincronizacao:
    fechou: DemandaStatusIntervalo | None
    abriu: DemandaStatusIntervalo | None

    @property
    def mudou(self) -> bool:
        return self.fechou is not None or self.abriu is not None


def _utc(valor: datetime) -> datetime:
    if valor.tzinfo is None or valor.tzinfo.utcoffset(valor) is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


class DemandaIntervaloService:
    def __init__(
        self,
        repository: DemandaStatusIntervaloRepository | None = None,
        sessao_repository: SessaoTrabalhoRepository | None = None,
    ) -> None:
        self.repository = repository or DemandaStatusIntervaloRepository()
        # AUTORIDADE da "etapa atual" (menor `ordem` não concluída) — a mesma de sessão, derivação da Demanda e progressão de workflow. Nenhuma definição nova.
        self.sessao_repository = sessao_repository or SessaoTrabalhoRepository()

    def etapa_atual_id(self, db: Session, demanda: Demanda) -> str | None:
        etapa = self.sessao_repository.get_etapa_atual(db, demanda.id)
        return etapa.id if etapa is not None else None

    def sincronizar(
        self,
        db: Session,
        demanda: Demanda,
        *,
        quando: datetime,
        origem: str,
        ator_usuario_id: str | None = None,
        evento_id: str | None = None,
        motivo_fim: str | None = None,
    ) -> ResultadoSincronizacao:
        """Alinha a linha do tempo ao estado ATUAL da Demanda (já alterado em memória pelo chamador, na mesma transação). Não faz commit.

        - `quando`: instante EFETIVO da transição (ver docstring do módulo).
        - `origem`: como o NOVO intervalo nasce (criacao/transicao/troca_etapa/restauracao/expediente).
        - `ator_usuario_id`: quem provocou (auditoria; `None` = sistema). NÃO é "quem trabalhou".
        - `evento_id`: o evento de domínio que causou a mudança (liga intervalo ↔ auditoria; o índice único em `evento_inicio_id` bloqueia o mesmo evento duas vezes).
        - `motivo_fim`: motivo do fechamento, se não for o derivado (status terminal → conclusao/cancelamento/arquivamento; mesma situação com etapa nova →
          mudanca_etapa; senão mudanca_status). A pausa automática passa `fim_expediente`.
        """
        agora = datetime.now(timezone.utc)
        quando = _utc(quando)
        # Defesa em profundidade: a Demanda já vem travada (`FOR UPDATE`) pelo fluxo que a alterou; travar de novo na mesma transação é gratuito e garante o invariante
        # "no máximo 1 aberto" mesmo para um chamador futuro que esqueça o lock. O índice único parcial é a última barreira.
        db.execute(select(Demanda.id).where(Demanda.id == demanda.id).with_for_update())
        db.flush()

        aberto = self.repository.get_aberto(db, demanda.id)
        status_desejado = demanda.status if demanda.status in STATUS_COM_INTERVALO else None
        etapa_desejada = self.etapa_atual_id(db, demanda) if status_desejado else None

        if aberto is not None and status_desejado == aberto.status and etapa_desejada == aberto.workflow_etapa_id:
            return ResultadoSincronizacao(None, None)  # mesmo estado e mesma etapa: no-op (nunca fecha/reabre nem duplica tempo)
        if aberto is None and status_desejado is None:
            return ResultadoSincronizacao(None, None)  # terminal sem nada aberto

        efetivo = quando
        fechado: DemandaStatusIntervalo | None = None
        if aberto is not None:
            inicio = _utc(aberto.inicio_em)
            if quando < inicio:
                logger.warning(
                    "demanda_intervalo_instante_anterior_ao_inicio demanda=%s intervalo=%s inicio=%s solicitado=%s",
                    demanda.id, aberto.id, inicio.isoformat(), quando.isoformat(),
                )
                efetivo = inicio
            if motivo_fim is None:
                if status_desejado is None:
                    motivo_fim = MOTIVO_POR_STATUS_TERMINAL.get(demanda.status, MOTIVO_MUDANCA_STATUS)
                elif status_desejado == aberto.status:
                    motivo_fim = MOTIVO_MUDANCA_ETAPA
                else:
                    motivo_fim = MOTIVO_MUDANCA_STATUS
            aberto.fim_em = efetivo
            aberto.duracao_segundos = max(0, int((efetivo - inicio).total_seconds()))
            aberto.motivo_fim = motivo_fim
            aberto.evento_fim_id = evento_id
            aberto.updated_at = agora
            db.flush()  # libera o índice único parcial ANTES de abrir o próximo
            fechado = aberto

        novo: DemandaStatusIntervalo | None = None
        if status_desejado is not None:
            novo = DemandaStatusIntervalo(
                id=str(uuid4()),
                empresa_id=demanda.empresa_id,
                demanda_id=demanda.id,
                status=status_desejado,
                workflow_etapa_id=etapa_desejada,
                inicio_em=efetivo,
                origem=origem,
                iniciado_por_usuario_id=ator_usuario_id,
                evento_inicio_id=evento_id,
                created_at=agora,
                updated_at=agora,
            )
            self.repository.create(db, novo)
        return ResultadoSincronizacao(fechado, novo)
