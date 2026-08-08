"""Emissão dos códigos oficiais de referência do TaskFlowW.

Formato: [LETRA MAIÚSCULA][ANO 2 DÍGITOS][SEQUENCIAL 6 DÍGITOS] — ex.: D26000001.

O código é o identificador de negócio: humano, pesquisável e **imutável** após a emissão.
Não é chave primária e nunca é usado em FK — isso continua sendo papel do `id` (UUID).

Contrato desta função (importante, ver docs/padrao-migracao-dominio.md):
- NÃO faz commit. Executa na sessão recebida e retorna;
- o commit é do service, junto com a entidade e o evento de domínio;
- se a criação da entidade falhar, o incremento do contador sofre rollback junto e o
  número não é queimado.
"""

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc, ano_corrente

# Lista FECHADA e executável: só entra o domínio já migrado e com regras confirmadas.
#
# Prefixos reservados, ainda NÃO executáveis (entram junto da migração de cada domínio):
#   U = usuario · F = fornecedor · P = projeto
#
# `tarefa` (T) está deliberadamente fora: conflita com a numeração #AA0000 hoje em uso, que
# dá continuidade à sequência do iClips (a partir de #002062). Pendência da Fase 2E.
PREFIXOS_REFERENCIA: dict[str, str] = {
    "departamento": "D",
    "equipe": "E",
    "cliente": "C",
}

SEQUENCIAL_DIGITOS = 6


class TipoEntidadeNaoSuportadoError(ValueError):
    """tipo_entidade fora da lista fechada — nunca aceitar string arbitrária."""


@dataclass(frozen=True)
class ReferenciaGerada:
    ano_referencia: int
    sequencial_referencia: int
    codigo_referencia: str


def formatar_codigo_referencia(tipo_entidade: str, ano: int, sequencial: int) -> str:
    prefixo = _prefixo(tipo_entidade)
    return f"{prefixo}{ano % 100:02d}{sequencial:0{SEQUENCIAL_DIGITOS}d}"


def gerar_proxima_referencia(
    db: Session,
    *,
    empresa_id: str,
    tipo_entidade: str,
    ano: int | None = None,
) -> ReferenciaGerada:
    """Reserva o próximo número da sequência (empresa + tipo + ano) e devolve o código.

    `ano=None` usa o ano corrente no fuso da aplicação (ver app/core/relogio.py). Os testes
    passam `ano` explícito — é assim que a virada de ano é coberta, sem congelar o relógio.

    Atomicidade: o `ON CONFLICT ... DO UPDATE` toma lock da linha do contador, então duas
    transações concorrentes para o mesmo escopo serializam e recebem números distintos.
    """
    prefixo = _prefixo(tipo_entidade)
    ano_efetivo = ano if ano is not None else ano_corrente()
    agora = agora_utc()

    # UPSERT atômico: insere com 1 ou incrementa o existente, sempre devolvendo o número
    # efetivamente reservado. Sem SELECT prévio, sem MAX()+1.
    sequencial = db.execute(
        text(
            """
            INSERT INTO sequencias_referencia
                   (id, empresa_id, tipo_entidade, ano, ultimo_numero, created_at, updated_at)
            VALUES (:id, :empresa_id, :tipo_entidade, :ano, 1, :agora, :agora)
            ON CONFLICT (empresa_id, tipo_entidade, ano)
            DO UPDATE SET ultimo_numero = sequencias_referencia.ultimo_numero + 1,
                          updated_at    = :agora
            RETURNING ultimo_numero
            """
        ),
        {
            "id": str(uuid4()),
            "empresa_id": empresa_id,
            "tipo_entidade": tipo_entidade,
            "ano": ano_efetivo,
            "agora": agora,
        },
    ).scalar_one()

    return ReferenciaGerada(
        ano_referencia=ano_efetivo,
        sequencial_referencia=sequencial,
        codigo_referencia=f"{prefixo}{ano_efetivo % 100:02d}{sequencial:0{SEQUENCIAL_DIGITOS}d}",
    )


def _prefixo(tipo_entidade: str) -> str:
    prefixo = PREFIXOS_REFERENCIA.get(tipo_entidade)
    if prefixo is None:
        suportados = ", ".join(sorted(PREFIXOS_REFERENCIA))
        raise TipoEntidadeNaoSuportadoError(
            f"tipo_entidade {tipo_entidade!r} não é suportado nesta fase. Suportados: {suportados}."
        )
    return prefixo
