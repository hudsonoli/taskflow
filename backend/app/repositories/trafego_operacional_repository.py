"""Tráfego V2 — Fase 2: consultas AGREGADAS de métricas operacionais (somente leitura).

Fonte do tempo: `demanda_status_intervalos` (tempo OPERACIONAL). Este módulo NUNCA lê `sessoes_trabalho` (tempo pessoal). Poucas consultas, todas agregadas no PostgreSQL (nada de N+1),
todas com `empresa_id` em CADA tabela tocada (demandas, intervalos, usuários, departamentos, projetos, clientes — inclusive nas subconsultas), e SQL com parâmetros ligados: os filtros
opcionais entram como FRAGMENTOS FIXOS deste arquivo (nunca texto vindo do cliente concatenado).

Etapa de workflow é snapshot por Demanda (sem FK para a etapa do template — recriada a cada edição do modelo — e com ids diferentes em cada Demanda): a identidade agregável é a
DEFINIÇÃO = `lower(btrim(nome))` + `tipo` + CONJUNTO CANÔNICO de departamentos responsáveis (ids ordenados). Mesmo nome e tipo com departamentos diferentes NÃO são a mesma definição.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Estados do escopo de triagem (rascunho e terminais ficam fora) e estados com tempo medido nos gargalos.
STATUS_TRIAGEM = ("planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente")
STATUS_TEMPO = ("em_execucao", "pausada", "bloqueada", "aguardando_cliente")

# Definição de etapa (identidade agregável) — fragmentos SQL fixos, reusados em todas as consultas.
_CHAVE_ETAPA = "lower(btrim(e.nome))"
# Conjunto canônico de departamentos responsáveis da etapa materializada `e`: ids ordenados e unidos por vírgula ('' = nenhum). Determinístico e independente da ordem de gravação.
_DEPARTAMENTOS_DA_ETAPA = (
    "(SELECT COALESCE(string_agg(dr.departamento_id, ',' ORDER BY dr.departamento_id), '') "
    "FROM demanda_workflow_etapa_departamentos_responsaveis dr WHERE dr.demanda_workflow_etapa_id = e.id)"
)


def _deps_da_etapa(etapa_id_sql: str) -> str:
    """Conjunto canônico de departamentos responsáveis da etapa `etapa_id_sql` ('' = nenhum, ou sem etapa) — subconsulta correlacionada resolvida pela PK
    (`demanda_workflow_etapa_id`, `departamento_id`), calculada UMA vez por ocorrência de etapa (nunca por linha de intervalo)."""
    return (
        "COALESCE((SELECT string_agg(dr.departamento_id, ',' ORDER BY dr.departamento_id) "
        f"FROM demanda_workflow_etapa_departamentos_responsaveis dr WHERE dr.demanda_workflow_etapa_id = {etapa_id_sql}), '')"
    )


@dataclass(frozen=True)
class FiltrosOperacionais:
    departamento_id: str | None = None
    cliente_id: str | None = None
    projeto_id: str | None = None
    # Definição de etapa (resolvida de `workflowEtapaId` pelo service): (nome normalizado, tipo, conjunto canônico de departamentos).
    etapa_chave: str | None = None
    etapa_tipo: str | None = None
    etapa_deps: str | None = None


def _inteiro(valor: Any) -> int:
    """Segundos exatos (Decimal vindo de EXTRACT(EPOCH)) → inteiro por PISO. Nunca arredonda para cima: 59,9 s contam 59."""
    if valor is None:
        return 0
    return int(Decimal(valor).to_integral_value(rounding="ROUND_FLOOR"))


class TrafegoOperacionalRepository:
    # ----------------------------------------------------------------------------------
    # Empresa / cobertura
    # ----------------------------------------------------------------------------------

    def fuso_da_empresa(self, db: Session, *, empresa_id: str) -> str | None:
        """Fuso IANA da regra de expediente da empresa. Somente leitura (NÃO cria a regra padrão). `None` = empresa sem regra."""
        return db.execute(
            text("SELECT timezone FROM regra_expediente WHERE empresa_id = :empresa_id LIMIT 1"),
            {"empresa_id": empresa_id},
        ).scalar_one_or_none()

    def medicao_desde(self, db: Session, *, empresa_id: str) -> datetime | None:
        """Menor `inicio_em` de intervalo da empresa (a migration abre o primeiro, `origem='migracao'`). Um lookup por status no índice (empresa_id, status, inicio_em) — sem varrer a
        tabela — porque `status` só tem seis valores (CHECK)."""
        return db.execute(
            text(
                "SELECT min(m) FROM ("
                "  SELECT (SELECT min(i.inicio_em) FROM demanda_status_intervalos i WHERE i.empresa_id = :empresa_id AND i.status = s.status) AS m"
                "  FROM (VALUES ('rascunho'), ('planejada'), ('em_execucao'), ('pausada'), ('bloqueada'), ('aguardando_cliente')) AS s(status)"
                ") t"
            ),
            {"empresa_id": empresa_id},
        ).scalar_one_or_none()

    def definicao_da_etapa(self, db: Session, *, empresa_id: str, etapa_id: str) -> tuple[str, str, str] | None:
        """(nome normalizado, tipo, conjunto canônico de departamentos) da definição da etapa materializada `etapa_id` — a definição DESTA etapa, não "qualquer etapa de mesmo nome".
        Só se ela pertence a uma Demanda da empresa (outra empresa = inexistente)."""
        linha = db.execute(
            text(
                f"SELECT {_CHAVE_ETAPA} AS chave, e.tipo AS tipo, {_DEPARTAMENTOS_DA_ETAPA} AS deps FROM demanda_workflow_etapas e "
                "JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id WHERE e.id = :etapa_id"
            ),
            {"empresa_id": empresa_id, "etapa_id": etapa_id},
        ).one_or_none()
        return (linha.chave, linha.tipo, linha.deps) if linha is not None else None

    def departamentos_por_ids(self, db: Session, *, empresa_id: str, departamento_ids: list[str]) -> dict[str, str]:
        """{departamento_id: nome} (só departamentos da empresa)."""
        if not departamento_ids:
            return {}
        linhas = db.execute(
            text("SELECT id, nome FROM departamentos WHERE empresa_id = :empresa_id AND id = ANY(:ids)"),
            {"empresa_id": empresa_id, "ids": departamento_ids},
        ).all()
        return {linha[0]: linha[1] for linha in linhas}

    # ----------------------------------------------------------------------------------
    # AGORA
    # ----------------------------------------------------------------------------------

    def kpis_agora(self, db: Session, *, empresa_id: str, agora: datetime, hoje_inicio: datetime, hoje_fim: datetime) -> dict[str, int]:
        """Contadores do escopo de triagem numa única consulta.

        Responsabilidade: com etapa atual → responsáveis (usuários) DA ETAPA ATUAL; sem etapa atual (sem workflow, ou workflow concluído) → responsáveis da Demanda. Etapa atual = menor `ordem` não concluída
        (mesma derivação de `DemandaService._derivar_etapa_atual_id`)."""
        linha = db.execute(
            text(
                """
                WITH escopo AS (
                    SELECT d.id, d.status, d.prazo_etapa_atual AS prazo
                    FROM demandas d
                    WHERE d.empresa_id = :empresa_id AND d.status IN ('planejada', 'em_execucao', 'pausada', 'bloqueada', 'aguardando_cliente')
                ),
                atual AS (
                    SELECT DISTINCT ON (e.demanda_id) e.demanda_id, e.id AS etapa_id
                    FROM demanda_workflow_etapas e JOIN escopo s ON s.id = e.demanda_id
                    WHERE e.status <> 'concluida'
                    ORDER BY e.demanda_id, e.ordem
                ),
                tem_workflow AS (
                    SELECT DISTINCT e.demanda_id FROM demanda_workflow_etapas e JOIN escopo s ON s.id = e.demanda_id
                )
                SELECT
                    count(*) FILTER (WHERE s.status = 'em_execucao') AS em_execucao,
                    count(*) FILTER (WHERE s.prazo < :agora) AS atrasadas,
                    count(*) FILTER (WHERE s.prazo >= :hoje_inicio AND s.prazo < :hoje_fim) AS vencem_hoje,
                    count(*) FILTER (WHERE s.prazo IS NULL) AS sem_prazo,
                    count(*) FILTER (WHERE
                        (a.etapa_id IS NOT NULL AND NOT EXISTS (
                            SELECT 1 FROM demanda_workflow_etapa_responsaveis r WHERE r.demanda_workflow_etapa_id = a.etapa_id)
                          -- responsabilidade EFETIVA: a etapa SEM nenhum vínculo explícito herda os responsáveis gerais da Demanda
                          AND NOT (
                            NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis dd WHERE dd.demanda_workflow_etapa_id = a.etapa_id)
                            AND EXISTS (SELECT 1 FROM demanda_responsaveis gr WHERE gr.demanda_id = s.id)))
                        OR (a.etapa_id IS NULL AND NOT EXISTS (
                            SELECT 1 FROM demanda_responsaveis r WHERE r.demanda_id = s.id))
                    ) AS sem_responsavel,
                    count(*) FILTER (WHERE a.etapa_id IS NULL AND w.demanda_id IS NOT NULL) AS sem_etapa_atual
                FROM escopo s
                LEFT JOIN atual a ON a.demanda_id = s.id
                LEFT JOIN tem_workflow w ON w.demanda_id = s.id
                """
            ),
            {"empresa_id": empresa_id, "agora": agora, "hoje_inicio": hoje_inicio, "hoje_fim": hoje_fim},
        ).one()
        return {chave: int(valor) for chave, valor in linha._mapping.items()}

    def demandas_em_execucao(self, db: Session, *, empresa_id: str, agora: datetime, limite: int) -> list[dict[str, Any]]:
        """"Em execução agora": Demandas `em_execucao` da empresa, atrasadas primeiro, depois a mais antiga no estado (início do intervalo ABERTO), depois o maior número."""
        linhas = db.execute(
            text(
                """
                SELECT
                    d.id AS demanda_id, d.codigo_referencia, d.numero_operacional, d.identificador, d.nome AS titulo, d.status,
                    d.prazo_etapa_atual AS prazo,
                    p.id AS projeto_id, p.nome AS projeto_nome,
                    c.id AS cliente_id, c.nome AS cliente_nome,
                    et.id AS etapa_id, et.nome AS etapa_nome, et.tipo AS etapa_tipo,
                    i.inicio_em AS inicio_estado
                FROM demandas d
                LEFT JOIN projetos p ON p.id = d.projeto_id AND p.empresa_id = :empresa_id
                LEFT JOIN clientes c ON c.id = d.cliente_id AND c.empresa_id = :empresa_id
                LEFT JOIN LATERAL (
                    SELECT e.id, e.nome, e.tipo FROM demanda_workflow_etapas e
                    WHERE e.demanda_id = d.id AND e.status <> 'concluida' ORDER BY e.ordem LIMIT 1
                ) et ON true
                LEFT JOIN demanda_status_intervalos i ON i.demanda_id = d.id AND i.empresa_id = :empresa_id AND i.fim_em IS NULL
                WHERE d.empresa_id = :empresa_id AND d.status = 'em_execucao'
                ORDER BY COALESCE(d.prazo_etapa_atual < :agora, false) DESC, i.inicio_em ASC NULLS LAST, d.numero_operacional DESC, d.id ASC
                LIMIT :limite
                """
            ),
            {"empresa_id": empresa_id, "agora": agora, "limite": limite},
        ).all()
        return [dict(linha._mapping) for linha in linhas]

    def responsaveis_das_etapas(self, db: Session, *, empresa_id: str, etapa_ids: list[str]) -> list[tuple[str, str, str]]:
        """(etapa_id, usuario_id, nome) dos responsáveis EFETIVOS das etapas dadas (só usuários da empresa): os explícitos da etapa; e, nas etapas SEM nenhum vínculo explícito, os responsáveis gerais."""
        if not etapa_ids:
            return []
        linhas = db.execute(
            text(
                "SELECT x.etapa_id, u.id, u.nome FROM ("
                "  SELECT r.demanda_workflow_etapa_id AS etapa_id, r.usuario_id FROM demanda_workflow_etapa_responsaveis r WHERE r.demanda_workflow_etapa_id = ANY(:etapa_ids)"
                "  UNION"
                "  SELECT e.id, gr.usuario_id FROM demanda_workflow_etapas e JOIN demanda_responsaveis gr ON gr.demanda_id = e.demanda_id"
                "   WHERE e.id = ANY(:etapa_ids)"
                "     AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis a WHERE a.demanda_workflow_etapa_id = e.id)"
                "     AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis b WHERE b.demanda_workflow_etapa_id = e.id)"
                ") x JOIN usuarios u ON u.id = x.usuario_id AND u.empresa_id = :empresa_id "
                "ORDER BY u.nome, u.id"
            ),
            {"empresa_id": empresa_id, "etapa_ids": etapa_ids},
        ).all()
        return [(linha[0], linha[1], linha[2]) for linha in linhas]

    def responsaveis_das_demandas(self, db: Session, *, empresa_id: str, demanda_ids: list[str]) -> list[tuple[str, str, str]]:
        """(demanda_id, usuario_id, nome) dos responsáveis da Demanda (só usuários da empresa)."""
        if not demanda_ids:
            return []
        linhas = db.execute(
            text(
                "SELECT r.demanda_id, u.id, u.nome FROM demanda_responsaveis r "
                "JOIN demandas d ON d.id = r.demanda_id AND d.empresa_id = :empresa_id "
                "JOIN usuarios u ON u.id = r.usuario_id AND u.empresa_id = :empresa_id "
                "WHERE r.demanda_id = ANY(:demanda_ids) ORDER BY u.nome, u.id"
            ),
            {"empresa_id": empresa_id, "demanda_ids": demanda_ids},
        ).all()
        return [(linha[0], linha[1], linha[2]) for linha in linhas]

    def departamentos_das_etapas(self, db: Session, *, empresa_id: str, etapa_ids: list[str]) -> list[tuple[str, str, str]]:
        """(etapa_id, departamento_id, nome) dos departamentos responsáveis EFETIVOS das etapas dadas: os explícitos da etapa; e, nas etapas SEM nenhum vínculo explícito, os departamentos gerais."""
        if not etapa_ids:
            return []
        linhas = db.execute(
            text(
                "SELECT x.etapa_id, dep.id, dep.nome FROM ("
                "  SELECT dr.demanda_workflow_etapa_id AS etapa_id, dr.departamento_id FROM demanda_workflow_etapa_departamentos_responsaveis dr WHERE dr.demanda_workflow_etapa_id = ANY(:etapa_ids)"
                "  UNION"
                "  SELECT e.id, gd.departamento_id FROM demanda_workflow_etapas e JOIN demanda_departamentos gd ON gd.demanda_id = e.demanda_id"
                "   WHERE e.id = ANY(:etapa_ids)"
                "     AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis a WHERE a.demanda_workflow_etapa_id = e.id)"
                "     AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis b WHERE b.demanda_workflow_etapa_id = e.id)"
                ") x JOIN departamentos dep ON dep.id = x.departamento_id AND dep.empresa_id = :empresa_id "
                "ORDER BY dep.nome, dep.id"
            ),
            {"empresa_id": empresa_id, "etapa_ids": etapa_ids},
        ).all()
        return [(linha[0], linha[1], linha[2]) for linha in linhas]

    # ----------------------------------------------------------------------------------
    # GARGALOS — tempo por etapa (histórico, recortado ao período)
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _filtros_sql(filtros: FiltrosOperacionais, params: dict[str, Any], *, alias_intervalo: str = "i") -> str:
        """Fragmentos FIXOS de filtro (AND ...). Os valores vão sempre como parâmetros ligados."""
        partes: list[str] = []
        if filtros.cliente_id is not None:
            partes.append("AND d.cliente_id = :f_cliente_id")
            params["f_cliente_id"] = filtros.cliente_id
        if filtros.projeto_id is not None:
            partes.append("AND d.projeto_id = :f_projeto_id")
            params["f_projeto_id"] = filtros.projeto_id
        if filtros.departamento_id is not None:
            partes.append(
                f"AND EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis dr "
                f"WHERE dr.demanda_workflow_etapa_id = {alias_intervalo}.workflow_etapa_id AND dr.departamento_id = :f_departamento_id)"
            )
            params["f_departamento_id"] = filtros.departamento_id
        if filtros.etapa_chave is not None:
            partes.append(f"AND {_CHAVE_ETAPA} = :f_etapa_chave AND e.tipo = :f_etapa_tipo AND {_DEPARTAMENTOS_DA_ETAPA} = :f_etapa_deps")
            params["f_etapa_chave"] = filtros.etapa_chave
            params["f_etapa_tipo"] = filtros.etapa_tipo
            params["f_etapa_deps"] = filtros.etapa_deps or ""
        return " ".join(partes)

    def _base_gargalos(self, empresa_id: str, inicio: datetime, fim_efetivo: datetime, filtros: FiltrosOperacionais) -> tuple[str, dict[str, Any]]:
        """CTE `base`: UM registro por intervalo medido, com os segundos RECORTADOS ao período [inicio, fim_efetivo]. Intervalo aberto usa `fim_efetivo` (nunca grava nada).
        Só intervalos que SOBREPÕEM o período entram — `duracao_segundos` integral jamais é usado."""
        params: dict[str, Any] = {"empresa_id": empresa_id, "inicio": inicio, "fim_efetivo": fim_efetivo}
        filtro_sql = self._filtros_sql(filtros, params)
        sql = f"""
            base AS (
                SELECT i.demanda_id, i.workflow_etapa_id, i.status,
                       GREATEST(0, EXTRACT(EPOCH FROM (LEAST(COALESCE(i.fim_em, :fim_efetivo), :fim_efetivo) - GREATEST(i.inicio_em, :inicio)))) AS seg
                FROM demanda_status_intervalos i
                JOIN demandas d ON d.id = i.demanda_id AND d.empresa_id = :empresa_id
                LEFT JOIN demanda_workflow_etapas e ON e.id = i.workflow_etapa_id AND e.demanda_id = i.demanda_id
                WHERE i.empresa_id = :empresa_id
                  AND i.status IN ('em_execucao', 'pausada', 'bloqueada', 'aguardando_cliente')
                  AND i.inicio_em < :fim_efetivo
                  AND (i.fim_em IS NULL OR i.fim_em > :inicio)
                  {filtro_sql}
            )"""
        return sql, params

    def tempo_por_etapa(
        self, db: Session, *, empresa_id: str, inicio: datetime, fim_efetivo: datetime, filtros: FiltrosOperacionais
    ) -> list[dict[str, Any]]:
        """Uma linha por DEFINIÇÃO de etapa (+ uma linha com `chave IS NULL` para intervalos sem etapa).

        Denominador: primeiro soma por (Demanda × etapa materializada × estado) — vários ciclos execução→pausa→execução da mesma Demanda viram UMA ocorrência —, depois agrega por definição.
        `n` = ocorrências com algum tempo medido; `n_<estado>` = ocorrências com tempo > 0 naquele estado."""
        base, params = self._base_gargalos(empresa_id, inicio, fim_efetivo, filtros)
        sql = f"""
            WITH {base},
            ocorrencia AS (
                SELECT demanda_id, workflow_etapa_id, {_deps_da_etapa("workflow_etapa_id")} AS deps,
                       COALESCE(SUM(seg) FILTER (WHERE status = 'em_execucao'), 0) AS exec_s,
                       COALESCE(SUM(seg) FILTER (WHERE status = 'pausada'), 0) AS pausa_s,
                       COALESCE(SUM(seg) FILTER (WHERE status = 'bloqueada'), 0) AS bloq_s,
                       COALESCE(SUM(seg) FILTER (WHERE status = 'aguardando_cliente'), 0) AS cli_s
                FROM base GROUP BY demanda_id, workflow_etapa_id
            )
            SELECT {_CHAVE_ETAPA} AS chave, e.tipo AS tipo, o.deps AS deps, min(btrim(e.nome)) AS nome,
                   count(*) AS n,
                   count(*) FILTER (WHERE o.exec_s > 0) AS n_exec, COALESCE(sum(o.exec_s), 0) AS exec_total, max(o.exec_s) FILTER (WHERE o.exec_s > 0) AS exec_maior,
                   count(*) FILTER (WHERE o.pausa_s > 0) AS n_pausa, COALESCE(sum(o.pausa_s), 0) AS pausa_total, max(o.pausa_s) FILTER (WHERE o.pausa_s > 0) AS pausa_maior,
                   count(*) FILTER (WHERE o.bloq_s > 0) AS n_bloq, COALESCE(sum(o.bloq_s), 0) AS bloq_total, max(o.bloq_s) FILTER (WHERE o.bloq_s > 0) AS bloq_maior,
                   count(*) FILTER (WHERE o.cli_s > 0) AS n_cli, COALESCE(sum(o.cli_s), 0) AS cli_total, max(o.cli_s) FILTER (WHERE o.cli_s > 0) AS cli_maior
            FROM ocorrencia o
            LEFT JOIN demanda_workflow_etapas e ON e.id = o.workflow_etapa_id AND e.demanda_id = o.demanda_id
            GROUP BY {_CHAVE_ETAPA}, e.tipo, o.deps
            ORDER BY (COALESCE(sum(o.exec_s) FILTER (WHERE o.exec_s > 0), 0) / NULLIF(count(*) FILTER (WHERE o.exec_s > 0), 0)) DESC NULLS LAST,
                     count(*) DESC, {_CHAVE_ETAPA} ASC NULLS LAST, e.tipo ASC NULLS LAST, o.deps ASC
        """
        linhas = db.execute(text(sql), params).all()
        return [
            {
                "chave": linha.chave,
                "tipo": linha.tipo,
                "deps": linha.deps,
                "nome": linha.nome,
                "n": int(linha.n),
                "n_exec": int(linha.n_exec),
                "exec_total": _inteiro(linha.exec_total),
                "exec_maior": _inteiro(linha.exec_maior) if linha.exec_maior is not None else None,
                "n_pausa": int(linha.n_pausa),
                "pausa_total": _inteiro(linha.pausa_total),
                "pausa_maior": _inteiro(linha.pausa_maior) if linha.pausa_maior is not None else None,
                "n_bloq": int(linha.n_bloq),
                "bloq_total": _inteiro(linha.bloq_total),
                "bloq_maior": _inteiro(linha.bloq_maior) if linha.bloq_maior is not None else None,
                "n_cli": int(linha.n_cli),
                "cli_total": _inteiro(linha.cli_total),
                "cli_maior": _inteiro(linha.cli_maior) if linha.cli_maior is not None else None,
            }
            for linha in linhas
        ]

    # ----------------------------------------------------------------------------------
    # GARGALOS — fila / WIP atual por etapa
    # ----------------------------------------------------------------------------------

    def _abertos_sql(self, empresa_id: str, filtros: FiltrosOperacionais) -> tuple[str, dict[str, Any]]:
        params: dict[str, Any] = {"empresa_id": empresa_id}
        filtro_sql = self._filtros_sql(filtros, params)
        sql = f"""
            abertos AS (
                SELECT i.demanda_id, i.workflow_etapa_id, i.status, i.inicio_em, {_deps_da_etapa("i.workflow_etapa_id")} AS deps,
                       EXISTS (SELECT 1 FROM demanda_workflow_etapas w WHERE w.demanda_id = d.id) AS tem_workflow
                FROM demanda_status_intervalos i
                JOIN demandas d ON d.id = i.demanda_id AND d.empresa_id = :empresa_id
                LEFT JOIN demanda_workflow_etapas e ON e.id = i.workflow_etapa_id AND e.demanda_id = i.demanda_id
                WHERE i.empresa_id = :empresa_id AND i.fim_em IS NULL
                  AND i.status IN ('planejada', 'em_execucao', 'pausada', 'bloqueada', 'aguardando_cliente')
                  AND d.status IN ('planejada', 'em_execucao', 'pausada', 'bloqueada', 'aguardando_cliente')
                  {filtro_sql}
            )"""
        return sql, params

    def fila_atual(self, db: Session, *, empresa_id: str, filtros: FiltrosOperacionais) -> list[dict[str, Any]]:
        """WIP ATUAL por definição de etapa (+ linhas para Demandas sem etapa atual, `categoria` ≠ 'etapa').

        Idade NA ETAPA: para cada Demanda aberta, a "sequência" é o conjunto de intervalos CONSECUTIVOS (um começa onde o outro termina) com a MESMA `workflow_etapa_id` que termina no
        intervalo aberto; a idade conta do início da sequência. Trocar de etapa — inclusive devolver à anterior — ou um buraco (terminal/reabertura) inicia uma sequência nova.
        Ordenação do histórico: (`inicio_em`, `fim_em` com aberto por último, `created_at`) — intervalos de duração zero no mesmo instante ficam na ordem em que foram criados."""
        abertos, params = self._abertos_sql(empresa_id, filtros)
        sql = f"""
            WITH {abertos},
            historico AS (
                SELECT i.id, i.demanda_id, i.workflow_etapa_id, i.inicio_em, i.fim_em, i.origem,
                       ROW_NUMBER() OVER w AS ordem, LAG(i.id) OVER w AS id_ant, LAG(i.workflow_etapa_id) OVER w AS etapa_ant, LAG(i.fim_em) OVER w AS fim_ant
                FROM demanda_status_intervalos i
                WHERE i.empresa_id = :empresa_id AND i.demanda_id IN (SELECT demanda_id FROM abertos)
                WINDOW w AS (PARTITION BY i.demanda_id ORDER BY i.inicio_em, COALESCE(i.fim_em, 'infinity'::timestamptz), i.created_at)
            ),
            marcados AS (
                SELECT h.*, CASE WHEN id_ant IS NULL OR etapa_ant IS DISTINCT FROM workflow_etapa_id OR fim_ant IS DISTINCT FROM inicio_em THEN 1 ELSE 0 END AS nova
                FROM historico h
            ),
            sequencias AS (
                SELECT m.*, SUM(nova) OVER (PARTITION BY demanda_id ORDER BY ordem) AS seq
                FROM marcados m
            ),
            desde AS (
                SELECT s.demanda_id, s.seq, min(s.inicio_em) AS etapa_desde, bool_or(s.origem = 'migracao') AS truncada
                FROM sequencias s GROUP BY s.demanda_id, s.seq
            ),
            aberto_seq AS (
                SELECT s.demanda_id, s.seq FROM sequencias s JOIN abertos a ON a.demanda_id = s.demanda_id AND s.fim_em IS NULL
            )
            SELECT
                CASE WHEN a.workflow_etapa_id IS NOT NULL THEN 'etapa' WHEN a.tem_workflow THEN 'workflow_concluido' ELSE 'sem_workflow' END AS categoria,
                {_CHAVE_ETAPA} AS chave, e.tipo AS tipo, a.deps AS deps, min(btrim(e.nome)) AS nome,
                count(*) AS wip,
                count(*) FILTER (WHERE a.status = 'planejada') AS planejadas,
                count(*) FILTER (WHERE a.status = 'em_execucao') AS em_execucao,
                count(*) FILTER (WHERE a.status = 'pausada') AS pausadas,
                count(*) FILTER (WHERE a.status = 'bloqueada') AS bloqueadas,
                count(*) FILTER (WHERE a.status = 'aguardando_cliente') AS aguardando_cliente,
                min(ds.etapa_desde) AS mais_antiga_desde,
                (array_agg(ds.truncada ORDER BY ds.etapa_desde ASC))[1] AS mais_antiga_truncada,
                min(a.inicio_em) AS estado_mais_antigo_desde
            FROM abertos a
            JOIN aberto_seq asq ON asq.demanda_id = a.demanda_id
            JOIN desde ds ON ds.demanda_id = asq.demanda_id AND ds.seq = asq.seq
            LEFT JOIN demanda_workflow_etapas e ON e.id = a.workflow_etapa_id AND e.demanda_id = a.demanda_id
            GROUP BY 1, {_CHAVE_ETAPA}, e.tipo, a.deps
            ORDER BY count(*) DESC, min(ds.etapa_desde) ASC, {_CHAVE_ETAPA} ASC NULLS LAST, e.tipo ASC NULLS LAST, a.deps ASC
        """
        linhas = db.execute(text(sql), params).all()
        return [dict(linha._mapping) for linha in linhas]

    # ----------------------------------------------------------------------------------
    # FLUXO — itens atuais por definição de etapa
    # ----------------------------------------------------------------------------------

    def itens_do_fluxo(
        self,
        db: Session,
        *,
        empresa_id: str,
        filtros: FiltrosOperacionais,
        agora: datetime,
        chaves: list[str],
        limite_itens: int,
    ) -> list[dict[str, Any]]:
        """Demandas ABERTAS por definição de etapa — o MESMO universo e a MESMA etapa de `fila_atual` (CTE `abertos`: intervalo aberto, status de triagem na Demanda e no intervalo, mesmos filtros).

        `chaves`: definições selecionadas pelo SERVIDOR, no formato `chavetipodeps` montado a partir das linhas de `fila_atual`/`tempo_por_etapa` (nunca vindas do cliente). `itens_total` = contagem de
        TODAS as Demandas da definição (janela `count() OVER`), independente do limite; só as `limite_itens` primeiras (atrasadas, depois a mais antiga no estado) voltam. Só Demandas COM etapa
        (as sem etapa são contadas à parte)."""
        if not chaves:
            return []
        abertos, params = self._abertos_sql(empresa_id, filtros)
        params.update({"agora": agora, "chaves": chaves, "limite_itens": limite_itens})
        sql = f"""
            WITH {abertos},
            itens AS (
                SELECT a.demanda_id, a.inicio_em AS inicio_estado, a.deps,
                       {_CHAVE_ETAPA} AS chave, e.tipo AS tipo, e.id AS etapa_id, e.nome AS etapa_nome,
                       d.codigo_referencia, d.numero_operacional, d.identificador, d.nome AS titulo, d.status, d.prazo_etapa_atual AS prazo,
                       p.id AS projeto_id, p.nome AS projeto_nome, c.id AS cliente_id, c.nome AS cliente_nome
                FROM abertos a
                JOIN demandas d ON d.id = a.demanda_id AND d.empresa_id = :empresa_id
                JOIN demanda_workflow_etapas e ON e.id = a.workflow_etapa_id AND e.demanda_id = a.demanda_id
                LEFT JOIN projetos p ON p.id = d.projeto_id AND p.empresa_id = :empresa_id
                LEFT JOIN clientes c ON c.id = d.cliente_id AND c.empresa_id = :empresa_id
                WHERE ({_CHAVE_ETAPA} || chr(31) || e.tipo || chr(31) || a.deps) = ANY(:chaves)
            ),
            ranqueados AS (
                SELECT i.*,
                       count(*) OVER (PARTITION BY i.chave, i.tipo, i.deps) AS itens_total,
                       row_number() OVER (
                           PARTITION BY i.chave, i.tipo, i.deps
                           ORDER BY COALESCE(i.prazo < :agora, false) DESC, i.inicio_estado ASC NULLS LAST, i.numero_operacional DESC, i.demanda_id ASC
                       ) AS posicao
                FROM itens i
            )
            SELECT * FROM ranqueados WHERE posicao <= :limite_itens
            ORDER BY chave ASC, tipo ASC, deps ASC, posicao ASC
        """
        linhas = db.execute(text(sql), params).all()
        return [dict(linha._mapping) for linha in linhas]
