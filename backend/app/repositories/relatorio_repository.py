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
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Date, DateTime, String, and_, case, cast, extract, func, literal, select
from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.projeto import Projeto
from app.models.usuario import Usuario
from app.repositories.demanda_repository import STATUS_ARQUIVADO, DemandaRepository

_SEGUNDOS_POR_DIA = 86400.0

# "Aberta" nos gráficos de Relatórios = os seis status que `isDemandaAberta` (frontend,
# lib/relatorios.ts) sempre considerou — não é "diferente de concluída": cancelada e arquivada
# também ficam de fora. Cópia literal da regra antiga, não uma definição nova.
_STATUS_ABERTOS = ("rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente")


def _dias(valor: Any) -> float | None:
    return None if valor is None else float(valor)


class RelatorioRepository:
    @staticmethod
    def _universo(escopo: EscopoDemanda) -> list[ColumnElement[bool]]:
        """Empresa + escopo normal + sem arquivada: o que `AppDataContext.demandas` enxergava,
        menos o cap de 200."""
        condicoes: list[ColumnElement[bool]] = [
            Demanda.empresa_id == escopo.empresa_id,
            Demanda.status != STATUS_ARQUIVADO,
        ]
        # Reuso deliberado da regra única de escopo de Demanda — nenhuma segunda definição.
        predicado = DemandaRepository._predicado_escopo(escopo)
        if predicado is not None:
            condicoes.append(predicado)
        return condicoes

    def _universo_projeto(self, escopo: EscopoDemanda, projeto_id: str) -> list[ColumnElement[bool]]:
        return [*self._universo(escopo), Demanda.projeto_id == projeto_id]

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
                Demanda.identificador,
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

    # ----------------------------------------------------------------------------------
    # D4B — Performance de colaborador e gráficos
    # ----------------------------------------------------------------------------------

    def listar_colaboradores(self, db: Session, *, empresa_id: str) -> Sequence[Any]:
        """Opções do seletor de "Performance de colaborador": o MESMO conjunto do diretório de
        usuários que a tela usava (todos os status — inclusive inativo/bloqueado/arquivado, que
        têm Demandas históricas —, sem conta de sistema, `nome ASC`), mas sem o `limit=200`."""
        return db.execute(
            select(Usuario.id, Usuario.nome)
            .where(Usuario.empresa_id == empresa_id, Usuario.is_system_account.is_(False))
            .order_by(Usuario.nome.asc(), Usuario.id.asc())
        ).all()

    def obter_colaborador(self, db: Session, *, empresa_id: str, colaborador_id: str) -> Any | None:
        return db.execute(
            select(Usuario.id, Usuario.nome).where(
                Usuario.id == colaborador_id,
                Usuario.empresa_id == empresa_id,
                Usuario.is_system_account.is_(False),
            )
        ).first()

    def performance_colaborador(
        self, db: Session, *, escopo: EscopoDemanda, colaborador_id: str, fuso: str
    ) -> dict[str, Any]:
        """Entregas e participação por etapa de UM colaborador — 2 queries, constantes.

        Regras portadas de `analisarPerformanceColaborador` (frontend):
        - a Demanda conta para CADA responsável (N:N) — não só o primeiro, sem divisão;
        - "entregue" = status `concluida`; "no prazo" = `data_fim_prevista` existe E `updated_at`
          cai até o fim desse dia no fuso da aplicação (`< 00:00 do dia seguinte`); sem
          `data_fim_prevista` não há prazo: a entrega cai em atraso;
        - participação por etapa: dentro das Demandas em que ele é responsável, cada ETAPA em que
          ele também é responsável conta 1 para o `nome` da etapa; a ordem é a de primeira
          aparição (Demandas `numero_operacional DESC`, etapas por `ordem`), como o `Map` antigo.
        """
        zero: dict[str, Any] = {"entregues": 0, "no_prazo": 0, "etapas": []}
        if escopo.vazio:
            return zero

        condicoes = self._universo(escopo)
        do_colaborador = Demanda.id.in_(
            select(DemandaResponsavel.demanda_id).where(DemandaResponsavel.usuario_id == colaborador_id)
        )

        fim_do_prazo = func.timezone(
            literal(fuso, String), cast(Demanda.data_fim_prevista, DateTime) + timedelta(days=1)
        )
        entregue = Demanda.status == "concluida"
        no_prazo = and_(entregue, Demanda.data_fim_prevista.is_not(None), Demanda.updated_at < fim_do_prazo)
        entregas = db.execute(
            select(func.count(case((entregue, 1))), func.count(case((no_prazo, 1))))
            .select_from(Demanda)
            .where(and_(*condicoes), do_colaborador)
        ).one()

        posicao = func.row_number().over(
            order_by=(Demanda.numero_operacional.desc(), DemandaWorkflowEtapa.ordem.asc(), DemandaWorkflowEtapa.id.asc())
        )
        participacoes = (
            select(DemandaWorkflowEtapa.nome.label("nome"), posicao.label("posicao"))
            .select_from(DemandaWorkflowEtapa)
            .join(Demanda, Demanda.id == DemandaWorkflowEtapa.demanda_id)
            .join(
                DemandaWorkflowEtapaResponsavel,
                and_(
                    DemandaWorkflowEtapaResponsavel.demanda_workflow_etapa_id == DemandaWorkflowEtapa.id,
                    DemandaWorkflowEtapaResponsavel.usuario_id == colaborador_id,
                ),
            )
            .where(and_(*condicoes), do_colaborador)
            .subquery()
        )
        etapas = db.execute(
            select(participacoes.c.nome, func.count())
            .group_by(participacoes.c.nome)
            .order_by(func.min(participacoes.c.posicao))
        ).all()

        return {"entregues": entregas[0], "no_prazo": entregas[1], "etapas": [(nome, qtd) for nome, qtd in etapas]}

    def abertas_por_projeto(self, db: Session, *, escopo: EscopoDemanda, cliente_id: str) -> Sequence[Any]:
        """Pizza "Demandas em aberto por projeto": projetos do Cliente com ao menos 1 Demanda
        aberta (`nome ASC`, como o diretório), contagem sobre TODAS as Demandas. Demanda sem
        Projeto não entra em nenhuma fatia; Projeto sem Demanda aberta é omitido."""
        if escopo.vazio:
            return []
        return db.execute(
            select(Projeto.id, Projeto.nome, func.count(Demanda.id))
            .select_from(Projeto)
            .join(Demanda, Demanda.projeto_id == Projeto.id)
            .where(
                Projeto.empresa_id == escopo.empresa_id,
                Projeto.cliente_id == cliente_id,
                Demanda.status.in_(_STATUS_ABERTOS),
                *self._universo(escopo),
            )
            .group_by(Projeto.id, Projeto.nome)
            .order_by(Projeto.nome.asc(), Projeto.id.asc())
        ).all()

    def volume_por_projeto_e_colaborador(
        self, db: Session, *, escopo: EscopoDemanda
    ) -> tuple[Sequence[Any], Sequence[Any]]:
        """Barras empilhadas "Volume por projeto e colaborador": TODOS os projetos da empresa
        (`nome ASC`, mesmo os sem Demanda ou arquivados — o diretório os incluía) e, por projeto,
        quantas Demandas (qualquer status, sem arquivada) cada colaborador tem como responsável.
        Mesma regra de responsável do relatório antigo: a Demanda conta para CADA responsável.
        2 queries, constantes (projetos + pares projeto×colaborador já agregados)."""
        projetos = db.execute(
            select(Projeto.id, Projeto.nome)
            .where(Projeto.empresa_id == escopo.empresa_id)
            .order_by(Projeto.nome.asc(), Projeto.id.asc())
        ).all()
        if escopo.vazio:
            return projetos, []
        pares = db.execute(
            select(Demanda.projeto_id, Usuario.id, Usuario.nome, func.count(DemandaResponsavel.demanda_id))
            .select_from(DemandaResponsavel)
            .join(Demanda, Demanda.id == DemandaResponsavel.demanda_id)
            .join(Usuario, Usuario.id == DemandaResponsavel.usuario_id)
            .where(
                Demanda.projeto_id.is_not(None),
                Usuario.empresa_id == escopo.empresa_id,
                Usuario.is_system_account.is_(False),
                *self._universo(escopo),
            )
            .group_by(Demanda.projeto_id, Usuario.id, Usuario.nome)
            .order_by(Usuario.nome.asc(), Usuario.id.asc())
        ).all()
        return projetos, pares

    def volume_semanal(
        self, db: Session, *, escopo: EscopoDemanda, primeira_semana: date, fim_exclusivo: date, fuso: str
    ) -> dict[date, int]:
        """Demandas CRIADAS por semana (segunda 00:00 → segunda seguinte, no fuso da aplicação),
        qualquer status/projeto/responsável, sem arquivada. `primeira_semana`/`fim_exclusivo` são
        segundas-feiras locais; o preenchimento das semanas vazias é de quem chama."""
        if escopo.vazio:
            return {}
        zona = literal(fuso, String)
        semana = cast(func.date_trunc("week", func.timezone(zona, Demanda.created_at)), Date)
        limite_inferior = func.timezone(zona, datetime(primeira_semana.year, primeira_semana.month, primeira_semana.day))
        limite_superior = func.timezone(zona, datetime(fim_exclusivo.year, fim_exclusivo.month, fim_exclusivo.day))
        linhas = db.execute(
            select(semana, func.count())
            .select_from(Demanda)
            .where(and_(*self._universo(escopo)), Demanda.created_at >= limite_inferior, Demanda.created_at < limite_superior)
            .group_by(semana)
        ).all()
        return {dia: quantidade for dia, quantidade in linhas}
