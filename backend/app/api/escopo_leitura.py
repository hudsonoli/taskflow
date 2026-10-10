"""Escopo de LEITURA do detalhe de uma Demanda (Fase 7C.1).

Quem tem a Pauta global (Atendimento, Heads e Gestão — `pode_visualizar_pauta_global`) enxerga na Pauta demandas de toda a empresa,
fora do seu escopo-base. Para abrir o detalhe dessas demandas, as rotas de LEITURA aceitam `?escopo=pauta`: o servidor valida a
autorização (403 para quem não tem Pauta global) e resolve a demanda com visão da EMPRESA do token — nunca de outro tenant.

É SOMENTE LEITURA: só os GET declaram o parâmetro. Toda rota de escrita (PATCH/POST/DELETE) continua resolvendo o escopo-base
(`resolver_escopo_demanda` sem argumento) e ignora `?escopo=pauta`. Ler pela Pauta global NÃO é poder escrever.
"""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.escopo import (
    EscopoDemanda,
    EscopoNaoAutorizadoError,
    EscopoSolicitado,
    resolver_escopo_demanda,
    resolver_escopo_workflow_atual,
)
from app.models.demanda import Demanda
from app.models.usuario import Usuario
from app.services.demanda_service import DemandaNotFoundError, DemandaService

# Único valor aceito além de "sem parâmetro": outros recortes (meus, atendimento…) não fazem sentido para ler UMA demanda.
EscopoLeitura = Literal["pauta"]


def escopo_para_leitura(db: Session, usuario: Usuario, escopo_leitura: EscopoLeitura | None) -> EscopoDemanda:
    if escopo_leitura is None:
        return resolver_escopo_demanda(db, usuario)
    try:
        return resolver_escopo_demanda(db, usuario, EscopoSolicitado.PAUTA)
    except EscopoNaoAutorizadoError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def demanda_com_acesso_de_workflow(
    db: Session, usuario: Usuario, demanda_id: str, demanda_service: DemandaService, escopo_leitura: EscopoLeitura | None = None
) -> tuple[Demanda, bool]:
    """Resolve a Demanda para LEITURA do detalhe/subrecursos ou para a AÇÃO do Workflow (Fase 8C.1): escopo-base (ou Pauta, se pedida) e, se a
    Demanda não estiver nele, o escopo DERIVADO da etapa atual (`resolver_escopo_workflow_atual`). Devolve `(demanda, via_workflow)`; `via_workflow`
    é verdadeiro quando SÓ o escopo de Workflow deu acesso — a interface então trata o acesso como "ler e agir no Workflow", sem edição geral.

    Fora de ambos → `DemandaNotFoundError` (404, sem confirmar existência). Escritas gerais NÃO usam esta função. A Pauta global não tem fallback:
    ler pela Pauta é uma autorização própria e não se mistura com a de Workflow."""
    escopo = escopo_para_leitura(db, usuario, escopo_leitura)
    try:
        return demanda_service.get_demanda(db, demanda_id, escopo=escopo), False
    except DemandaNotFoundError:
        if escopo_leitura is not None:
            raise
    return demanda_service.get_demanda(db, demanda_id, escopo=resolver_escopo_workflow_atual(db, usuario)), True
