"""Pauta operacional por ETAPA (P1_PAUTA_COLABORADOR): leituras somente leitura, poucas consultas em conjunto, sem N+1.

Universo: etapas NÃO concluídas de Demandas abertas da empresa (fora `concluida`, `cancelada` e `arquivada`; `rascunho` fica, como na Pauta anterior). `empresa_id` entra em CADA tabela com tenant.
Os filtros por colaborador/departamento aplicam a RESPONSABILIDADE EFETIVA (a mesma regra de `app.core.executor_etapa`, reproduzida em SQL e coberta por teste de equivalência): a etapa com algum vínculo
explícito (usuário OU departamento) vale só por ela; sem nenhum, valem os responsáveis/departamentos gerais da Demanda. Todo SQL usa parâmetros ligados; os fragmentos são fixos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

STATUS_FORA_DA_PAUTA = ("concluida", "cancelada", "arquivada")
_FORA_SQL = ", ".join(f"'{status}'" for status in STATUS_FORA_DA_PAUTA)

_TEM_EXPLICITO = (
    "(EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis xr WHERE xr.demanda_workflow_etapa_id = e.id)"
    " OR EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis xd WHERE xd.demanda_workflow_etapa_id = e.id))"
)
_ETAPA_ATUAL = "e.ordem = (SELECT min(x.ordem) FROM demanda_workflow_etapas x WHERE x.demanda_id = e.demanda_id AND x.status <> 'concluida')"

_PLANEJADAS = "e.planejado_inicio IS NOT NULL AND e.planejado_fim IS NOT NULL AND e.planejado_inicio <= :fim AND e.planejado_fim >= :inicio"
_INCOMPLETAS = "e.planejado_inicio IS NOT NULL AND e.planejado_fim IS NULL AND e.planejado_inicio <= :fim"
_NAO_PLANEJADAS = "e.planejado_inicio IS NULL"  # inclui o par inválido NULL/DATE (não existe no banco: CHECK), tratado como não planejado
_ANTES = "e.planejado_inicio IS NOT NULL AND e.planejado_fim IS NOT NULL AND e.planejado_fim < :inicio"
_DEPOIS = "e.planejado_inicio IS NOT NULL AND e.planejado_fim IS NOT NULL AND e.planejado_inicio > :fim"

_COLUNAS = f"""
    e.id AS etapa_id, e.demanda_id, e.nome AS etapa_nome, e.tipo AS etapa_tipo, e.ordem AS etapa_ordem, e.status AS etapa_status,
    e.planejado_inicio, e.planejado_fim, ({_ETAPA_ATUAL}) AS etapa_atual,
    d.identificador, d.nome AS demanda_nome, d.status AS demanda_status, d.prioridade, d.cliente_id, d.projeto_id, d.prazo_etapa_atual
"""

_BALDES = {"planejadas": _PLANEJADAS, "incompletas": _INCOMPLETAS, "nao_planejadas": _NAO_PLANEJADAS}


def _like(termo: str) -> str:
    escapado = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


_BUSCA = (
    "(d.nome ILIKE :busca ESCAPE '\\' OR d.identificador ILIKE :busca ESCAPE '\\' OR e.nome ILIKE :busca ESCAPE '\\'"
    " OR p.nome ILIKE :busca ESCAPE '\\' OR c.nome ILIKE :busca ESCAPE '\\')"
)


class PautaOperacionalRepository:
    def _base(
        self,
        *,
        empresa_id: str,
        usuario_ids: list[str],
        departamento_ids: list[str],
        cliente_ids: list[str],
        projeto_ids: list[str],
        prioridades: list[str],
        busca: str | None,
    ) -> tuple[str, dict[str, Any]]:
        """FROM + WHERE comuns aos três baldes e aos totais (sem a janela)."""
        clausulas = ["d.empresa_id = :empresa_id", f"d.status NOT IN ({_FORA_SQL})", "e.status <> 'concluida'"]
        parametros: dict[str, Any] = {"empresa_id": empresa_id}
        if usuario_ids:
            clausulas.append(
                "(EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis fr WHERE fr.demanda_workflow_etapa_id = e.id AND fr.usuario_id = ANY(CAST(:usuario_ids AS varchar[])))"
                f" OR (NOT {_TEM_EXPLICITO} AND EXISTS (SELECT 1 FROM demanda_responsaveis gr WHERE gr.demanda_id = d.id AND gr.usuario_id = ANY(CAST(:usuario_ids AS varchar[])))))"
            )
            parametros["usuario_ids"] = usuario_ids
        if departamento_ids:
            clausulas.append(
                "(EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis fd WHERE fd.demanda_workflow_etapa_id = e.id AND fd.departamento_id = ANY(CAST(:departamento_ids AS varchar[])))"
                f" OR (NOT {_TEM_EXPLICITO} AND EXISTS (SELECT 1 FROM demanda_departamentos gd WHERE gd.demanda_id = d.id AND gd.departamento_id = ANY(CAST(:departamento_ids AS varchar[])))))"
            )
            parametros["departamento_ids"] = departamento_ids
        if cliente_ids:
            clausulas.append("d.cliente_id = ANY(CAST(:cliente_ids AS varchar[]))")
            parametros["cliente_ids"] = cliente_ids
        if projeto_ids:
            clausulas.append("d.projeto_id = ANY(CAST(:projeto_ids AS varchar[]))")
            parametros["projeto_ids"] = projeto_ids
        if prioridades:
            clausulas.append("d.prioridade = ANY(CAST(:prioridades AS varchar[]))")
            parametros["prioridades"] = prioridades
        if busca:
            clausulas.append(_BUSCA)
            parametros["busca"] = _like(busca)
        origem = (
            "FROM demanda_workflow_etapas e"
            " JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id"
            " LEFT JOIN clientes c ON c.id = d.cliente_id AND c.empresa_id = :empresa_id"
            " LEFT JOIN projetos p ON p.id = d.projeto_id AND p.empresa_id = :empresa_id"
            " WHERE " + " AND ".join(clausulas)
        )
        return origem, parametros

    def totais(self, db: Session, *, inicio: date, fim: date, **filtros: Any) -> dict[str, int]:
        origem, parametros = self._base(**filtros)
        linha = db.execute(
            text(
                f"""
                SELECT count(*) FILTER (WHERE {_PLANEJADAS}) AS planejadas,
                       count(*) FILTER (WHERE {_INCOMPLETAS}) AS incompletas,
                       count(*) FILTER (WHERE {_NAO_PLANEJADAS}) AS nao_planejadas,
                       count(*) FILTER (WHERE {_ANTES}) AS antes,
                       count(*) FILTER (WHERE {_DEPOIS}) AS depois
                {origem}
                """
            ),
            {**parametros, "inicio": inicio, "fim": fim},
        ).one()
        return dict(linha._mapping)

    def itens(self, db: Session, *, balde: str, inicio: date, fim: date, limite: int, **filtros: Any) -> list[dict[str, Any]]:
        """Itens de UM balde (`planejadas`, `incompletas` ou `nao_planejadas`), em ordem determinística, até `limite`."""
        origem, parametros = self._base(**filtros)
        linhas = db.execute(
            text(
                f"""
                SELECT {_COLUNAS}
                {origem} AND {_BALDES[balde]}
                ORDER BY e.planejado_inicio ASC NULLS LAST, e.planejado_fim ASC NULLS LAST, d.numero_operacional ASC, e.ordem ASC, e.id ASC
                LIMIT :limite
                """
            ),
            {**parametros, "inicio": inicio, "fim": fim, "limite": limite},
        ).all()
        return [dict(linha._mapping) for linha in linhas]

    def nomes_dos_usuarios(self, db: Session, *, empresa_id: str, usuario_ids: list[str]) -> list[tuple[str, str]]:
        if not usuario_ids:
            return []
        linhas = db.execute(
            text("SELECT id, nome FROM usuarios WHERE empresa_id = :empresa_id AND id = ANY(CAST(:ids AS varchar[])) ORDER BY nome, id"),
            {"empresa_id": empresa_id, "ids": usuario_ids},
        ).all()
        return [(linha.id, linha.nome) for linha in linhas]
