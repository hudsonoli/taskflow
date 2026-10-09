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

from app.core.escopo import EscopoDemanda, EscopoNaoAutorizadoError, EscopoSolicitado, resolver_escopo_demanda
from app.models.usuario import Usuario

# Único valor aceito além de "sem parâmetro": outros recortes (meus, atendimento…) não fazem sentido para ler UMA demanda.
EscopoLeitura = Literal["pauta"]


def escopo_para_leitura(db: Session, usuario: Usuario, escopo_leitura: EscopoLeitura | None) -> EscopoDemanda:
    if escopo_leitura is None:
        return resolver_escopo_demanda(db, usuario)
    try:
        return resolver_escopo_demanda(db, usuario, EscopoSolicitado.PAUTA)
    except EscopoNaoAutorizadoError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
