"""Reserva do próximo número operacional — contador contínuo, sem ano.

Complementa `app/core/referencias.py`, que emite o código oficial (`T26000001`) e **reinicia
por ano**. Aqui o número não reinicia: `#2063` em 2026 continua `#15843` em 2027.

Contrato idêntico ao de `gerar_proxima_referencia`, e pelos mesmos motivos:

- **NÃO faz commit.** Executa na sessão recebida e retorna;
- o commit é do service, junto com a entidade e o evento de domínio;
- se a criação da entidade falhar, o incremento sofre rollback junto e o número não é
  queimado.

Atomicidade: o `INSERT ... ON CONFLICT DO UPDATE` toma lock da linha do contador, então duas
transações concorrentes para a mesma empresa serializam e recebem números distintos.

Diferente de `gerar_proxima_referencia`, devolve **inteiro cru** — o número operacional não
tem prefixo nem formatação: `2063` é exibido como `#2063` pela interface, e isso é decisão de
apresentação, não de domínio.
"""

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc

# Lista FECHADA, como em PREFIXOS_REFERENCIA: só entra domínio com número operacional
# aprovado. Hoje apenas Demanda tem — os demais usam somente `codigo_referencia`.
TIPOS_COM_NUMERO_OPERACIONAL: frozenset[str] = frozenset({"demanda"})


class TipoSemNumeroOperacionalError(ValueError):
    """tipo_entidade fora da lista fechada — nunca aceitar string arbitrária."""


def reservar_proximo_operacional(db: Session, *, empresa_id: str, tipo_entidade: str) -> int:
    """Reserva e devolve o próximo número operacional da empresa.

    Base sem semente começa em **1**. O número de go-live (continuidade com o iClips) é
    gravado antes por `app/cli/inicializar_numero_operacional.py`.
    """
    if tipo_entidade not in TIPOS_COM_NUMERO_OPERACIONAL:
        suportados = ", ".join(sorted(TIPOS_COM_NUMERO_OPERACIONAL))
        raise TipoSemNumeroOperacionalError(
            f"tipo_entidade {tipo_entidade!r} não usa número operacional. Suportados: {suportados}."
        )

    agora = agora_utc()
    resultado = db.execute(
        text(
            """
            INSERT INTO sequencias_operacionais
                (id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at)
            VALUES (:id, :empresa_id, :tipo_entidade, 1, :agora, :agora)
            ON CONFLICT (empresa_id, tipo_entidade)
            DO UPDATE SET ultimo_numero = sequencias_operacionais.ultimo_numero + 1,
                          updated_at = :agora
            RETURNING ultimo_numero
            """
        ),
        {"id": str(uuid4()), "empresa_id": empresa_id, "tipo_entidade": tipo_entidade, "agora": agora},
    )
    return int(resultado.scalar_one())
