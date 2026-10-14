"""Tick de backend da pausa automática por expediente (Fase Expediente 3).

Uma `asyncio.Task` no lifespan da aplicação — SEM APScheduler, SEM Redis, SEM container novo. A lógica (e toda a segurança: advisory lock por empresa+corte,
idempotência por `correlation_id`, regra de catch-up) vive em `ExpedientePausaService`; aqui só existe o relógio de ~60 s. Várias instâncias/processos podem rodar este
loop ao mesmo tempo: o advisory lock e o registro de conclusão do corte garantem que um corte é processado uma única vez.

O trabalho de banco é síncrono e roda em `asyncio.to_thread` (não trava o event loop). O loop dorme até o próximo segundo `:01` de cada intervalo — o corte efetivo é o
horário configurado (12:00), então 1–2 s de atraso do tick não mudam nenhum dado gravado.
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import get_settings
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

ATRASO_INICIAL_SEGUNDOS = 5  # catch-up logo depois de subir (restart no meio de um intervalo)


def segundos_ate_o_proximo_tick(intervalo: int, agora: float | None = None) -> float:
    """Segundos até o próximo múltiplo do intervalo + 1 s (ex.: 60 s → próximo `HH:MM:01`). Sempre positivo."""
    atual = time.time() if agora is None else agora
    espera = intervalo - (atual % intervalo) + 1
    return espera if espera > 0.5 else espera + intervalo


def executar_uma_rodada() -> int:
    """Uma rodada síncrona do tick (usada pelo loop e testável sem asyncio). Devolve quantos cortes foram executados."""
    from app.services.expediente_pausa_service import ExpedientePausaService

    resultados = ExpedientePausaService().executar_tick(get_session_factory())
    return sum(1 for r in resultados if r.status in ("executado", "parcial"))


async def loop_pausa_expediente(intervalo: int) -> None:
    await asyncio.sleep(ATRASO_INICIAL_SEGUNDOS)
    while True:
        try:
            await asyncio.to_thread(executar_uma_rodada)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — o tick nunca morre por um erro de uma rodada
            logger.exception("expediente_tick_falhou")
        await asyncio.sleep(segundos_ate_o_proximo_tick(intervalo))


def tick_habilitado() -> bool:
    return get_settings().expediente_tick_habilitado
