"""D4A — consultas agregadas dos Relatórios de Projeto ("Análise de projeto" e "Análise de
peças"), sobre o universo INTEGRAL do Projeto.

Antes, as duas telas calculavam no navegador sobre `AppDataContext.demandas`, que é
`GET /demandas?limit=200` — as 200 Demandas mais recentes da EMPRESA INTEIRA (sem arquivadas).
Um Projeto com Demandas fora dessa janela aparecia com totais, médias e rankings truncados em
silêncio. Aqui tudo é SQL sobre o Projeto, sem cap.

Universo (idêntico ao que as telas enxergavam, menos o cap): empresa + escopo normal de quem
pede (`DemandaRepository._predicado_escopo`, a mesma regra de `list()`) + Projeto + exclusão de
arquivada (default de `list()` sem `status`). Quem chega aqui é admin/gestor (gate na rota), logo
`visao_total` — mas isso vem do escopo resolvido, não é fixado aqui.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, DateTime, String, and_, case, cast, extract, func, literal, select
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.usuario import Usuario
from app.repositories.demanda_repository import STATUS_ARQUIVADO, DemandaRepository

_SEGUNDOS_POR_DIA = 86400.0


def _dias(valor: Any) -> float | None:
    return None if valor is None else float(valor)


class RelatorioRepository:
    @staticmethod
    def _universo_projeto(escopo: EscopoDemanda, projeto_id: str) -> list[ColumnElement[bool]]:
        condicoes: list[ColumnElement[bool]] = [
            Demanda.empresa_id == escopo.empresa_id,
            Demanda.projeto_id == projeto_id,
            Demanda.status != STATUS_ARQUIVADO,
        ]
        # Reuso deliberado da regra única de escopo de Demanda — nenhuma segunda definição.
        predicado = DemandaRepository._predicado_escopo(escopo)
        if predicado is not None:
            condicoes.append(predicado)
        return condicoes

    def analise_projeto(
        self, db: Session, *, escopo: EscopoDemanda, projeto_id: str, fuso: str
    ) -> dict[str, Any]:
        """Totais, prioridade, tempos médios e colaboradores — 2 queries, constantes.

        `Criação → início`: `data_inicio` é DATE (sem hora); entra como 00:00 do dia no fuso da
        aplicação (era 00:00 do fuso do navegador). Demanda sem `data_inicio` fica fora da
        média (AVG ignora NULL). `Retorno do cliente`: só quem tem `enviado_cliente_em` E
        `retorno_recebido_em`. Valores negativos entram como sempre entraram.
        """
        vazio: dict[str, Any] = {
            "total": 0,
            "baixa": 0,
            "media": 0,
            "alta": 0,
            "abertura": None,
            "retorno": None,
            "colaboradores": [],
        }
        if escopo.vazio:
            return vazio

        condicoes = self._universo_projeto(escopo, projeto_id)

        inicio_local = func.timezone(literal(fuso, String), cast(Demanda.data_inicio, DateTime))
        abertura = extract("epoch", inicio_local - Demanda.created_at) / _SEGUNDOS_POR_DIA
        retorno = extract("epoch", Demanda.retorno_recebido_em - Demanda.enviado_cliente_em) / _SEGUNDOS_POR_DIA

        agregados = db.execute(
            select(
                func.count().label("total"),
                func.count(case((Demanda.prioridade == "baixa", 1))).label("baixa"),
                func.count(case((Demanda.prioridade == "media", 1))).label("media"),
                func.count(case((Demanda.prioridade == "alta", 1))).label("alta"),
                func.avg(abertura).label("abertura"),
                func.avg(retorno).label("retorno"),
            )
            .select_from(Demanda)
            .where(and_(*condicoes))
        ).one()

        # Ordem = a do diretório de usuários que a tela usava (`nome ASC`), com `id` só para
        # desempatar de forma estável. Conta de sistema nunca esteve no diretório.
        colaboradores = db.execute(
            select(Usuario.id, Usuario.nome, func.count(DemandaResponsavel.demanda_id))
            .select_from(DemandaResponsavel)
            .join(Demanda, Demanda.id == DemandaResponsavel.demanda_id)
            .join(Usuario, Usuario.id == DemandaResponsavel.usuario_id)
            .where(and_(*condicoes), Usuario.empresa_id == escopo.empresa_id, Usuario.is_system_account.is_(False))
            .group_by(Usuario.id, Usuario.nome)
            .order_by(Usuario.nome.asc(), Usuario.id.asc())
        ).all()

        return {
            "total": agregados.total,
            "baixa": agregados.baixa,
            "media": agregados.media,
            "alta": agregados.alta,
            "abertura": _dias(agregados.abertura),
            "retorno": _dias(agregados.retorno),
            "colaboradores": [(usuario_id, nome, quantidade) for usuario_id, nome, quantidade in colaboradores],
        }

    def pecas_projeto(
        self, db: Session, *, escopo: EscopoDemanda, projeto_id: str, limit: int, offset: int
    ) -> tuple[Sequence[Any], int]:
        """Página das Demandas do Projeto (`numero_operacional DESC`, a ordem da listagem que a
        tela consumia) + total do universo. 2 queries, constantes.

        Redator = o PRIMEIRO responsável pela ordem de id (`DemandaRepository` ordena os
        responsáveis por `usuario_id`), resolvido por nome; sem responsável, ou responsável fora
        do diretório (conta de sistema), fica `NULL` — a tela mostra "Sem responsável".
        "Tempo em pauta" só existe para concluída/cancelada: `updated_at - created_at`.
        """
        if escopo.vazio:
            return [], 0

        condicoes = self._universo_projeto(escopo, projeto_id)

        total = db.execute(select(func.count()).select_from(Demanda).where(and_(*condicoes))).scalar_one()

        primeiro_responsavel = (
            select(func.min(DemandaResponsavel.usuario_id))
            .where(DemandaResponsavel.demanda_id == Demanda.id)
            .correlate(Demanda)
            .scalar_subquery()
        )
        tempo_em_pauta = case(
            (
                Demanda.status.in_(DemandaRepository._STATUS_FINALIZADOS),
                extract("epoch", Demanda.updated_at - Demanda.created_at) / _SEGUNDOS_POR_DIA,
            )
        )
        linhas = db.execute(
            select(
                Demanda.id,
                Demanda.nome,
                Demanda.numero_operacional,
                Demanda.status,
                Usuario.nome.label("redator_nome"),
                tempo_em_pauta.label("tempo_em_pauta_dias"),
            )
            .select_from(Demanda)
            .outerjoin(
                Usuario,
                and_(
                    Usuario.id == primeiro_responsavel,
                    Usuario.empresa_id == escopo.empresa_id,
                    Usuario.is_system_account.is_(False),
                ),
            )
            .where(and_(*condicoes))
            .order_by(Demanda.numero_operacional.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return linhas, total
