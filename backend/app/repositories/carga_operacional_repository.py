"""Tráfego V2 — 11B.2B-B: leituras da CARGA semanal (somente leitura, poucas consultas em conjunto, sem N+1).

NÃO lê `sessoes_trabalho` (tempo pessoal) nem `demanda_status_intervalos` (tempo operacional): carga = estimativa + janela planejada da etapa; capacidade = expediente. `empresa_id` entra em CADA tabela
com tenant (demandas, usuarios, departamentos, clientes, projetos), inclusive nos joins. Todo SQL usa parâmetros ligados; os filtros são fragmentos fixos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Demandas que participam do planejamento de capacidade. `rascunho` e os estados terminais (`concluida`, `cancelada`, `arquivada`) ficam FORA; pausada/bloqueada/aguardando_cliente continuam com carga futura.
STATUS_CARGA = ("planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente")
_STATUS_SQL = ", ".join(f"'{status}'" for status in STATUS_CARGA)

# Elegibilidade para receber trabalho = a MESMA regra de `DemandaService._ensure_usuario_valido` (não é conta de sistema e o status não está em {arquivado, inativo, bloqueado}, ou seja, está ativo)
# + acesso ao sistema. Perfil (admin/gestor/operador) NÃO decide isso sozinho.
_USUARIO_ELEGIVEL = "u.status = 'ativo' AND u.acesso_sistema AND NOT u.is_system_account"


class CargaOperacionalRepository:
    def etapas_abertas(self, db: Session, *, empresa_id: str) -> list[dict[str, Any]]:
        """Etapas NÃO concluídas das Demandas operacionais da empresa (inclusive etapas futuras: a capacidade não se limita à etapa atual)."""
        linhas = db.execute(
            text(
                f"""
                SELECT e.id AS etapa_id, e.demanda_id, e.nome AS etapa_nome, e.tipo AS etapa_tipo, e.ordem,
                       e.esforco_estimado_minutos AS estimativa, e.planejado_inicio, e.planejado_fim,
                       d.identificador, d.nome AS demanda_nome, d.status AS demanda_status,
                       c.id AS cliente_id, c.nome AS cliente_nome, p.id AS projeto_id, p.nome AS projeto_nome
                FROM demanda_workflow_etapas e
                JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id
                LEFT JOIN clientes c ON c.id = d.cliente_id AND c.empresa_id = :empresa_id
                LEFT JOIN projetos p ON p.id = d.projeto_id AND p.empresa_id = :empresa_id
                WHERE d.status IN ({_STATUS_SQL}) AND e.status <> 'concluida'
                ORDER BY d.numero_operacional, e.ordem, e.id
                """
            ),
            {"empresa_id": empresa_id},
        ).all()
        return [dict(linha._mapping) for linha in linhas]

    def usuarios_das_etapas(self, db: Session, *, empresa_id: str) -> list[tuple[str, str]]:
        """(etapa_id, usuario_id) das etapas abertas elegíveis, pela responsabilidade EFETIVA: os usuários explícitos da etapa; e, SÓ nas etapas sem NENHUM vínculo explícito (nem usuário nem
        departamento), os responsáveis gerais da Demanda (fallback em leitura, nunca copiado). A elegibilidade do usuário é decidida depois, contra a lista de pessoas."""
        linhas = db.execute(
            text(
                f"""
                SELECT r.demanda_workflow_etapa_id, r.usuario_id
                FROM demanda_workflow_etapa_responsaveis r
                JOIN demanda_workflow_etapas e ON e.id = r.demanda_workflow_etapa_id AND e.status <> 'concluida'
                JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id AND d.status IN ({_STATUS_SQL})
                UNION
                SELECT e.id, gr.usuario_id
                FROM demanda_workflow_etapas e
                JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id AND d.status IN ({_STATUS_SQL})
                JOIN demanda_responsaveis gr ON gr.demanda_id = d.id
                WHERE e.status <> 'concluida'
                  AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis x WHERE x.demanda_workflow_etapa_id = e.id)
                  AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis y WHERE y.demanda_workflow_etapa_id = e.id)
                """
            ),
            {"empresa_id": empresa_id},
        ).all()
        return [(linha[0], linha[1]) for linha in linhas]

    def departamentos_das_etapas(self, db: Session, *, empresa_id: str) -> list[tuple[str, str]]:
        """(etapa_id, departamento_id) pela responsabilidade EFETIVA: departamentos explícitos da etapa; e, só nas etapas SEM nenhum vínculo explícito, os departamentos gerais da Demanda."""
        linhas = db.execute(
            text(
                f"""
                SELECT r.demanda_workflow_etapa_id, r.departamento_id
                FROM demanda_workflow_etapa_departamentos_responsaveis r
                JOIN demanda_workflow_etapas e ON e.id = r.demanda_workflow_etapa_id AND e.status <> 'concluida'
                JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id AND d.status IN ({_STATUS_SQL})
                JOIN departamentos dep ON dep.id = r.departamento_id AND dep.empresa_id = :empresa_id
                UNION
                SELECT e.id, gd.departamento_id
                FROM demanda_workflow_etapas e
                JOIN demandas d ON d.id = e.demanda_id AND d.empresa_id = :empresa_id AND d.status IN ({_STATUS_SQL})
                JOIN demanda_departamentos gd ON gd.demanda_id = d.id
                JOIN departamentos dep ON dep.id = gd.departamento_id AND dep.empresa_id = :empresa_id
                WHERE e.status <> 'concluida'
                  AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_responsaveis x WHERE x.demanda_workflow_etapa_id = e.id)
                  AND NOT EXISTS (SELECT 1 FROM demanda_workflow_etapa_departamentos_responsaveis y WHERE y.demanda_workflow_etapa_id = e.id)
                """
            ),
            {"empresa_id": empresa_id},
        ).all()
        return [(linha[0], linha[1]) for linha in linhas]

    def pessoas_elegiveis(self, db: Session, *, empresa_id: str) -> list[dict[str, Any]]:
        linhas = db.execute(
            text(
                f"SELECT u.id, u.nome, u.departamento_id FROM usuarios u WHERE u.empresa_id = :empresa_id AND {_USUARIO_ELEGIVEL} ORDER BY u.id"
            ),
            {"empresa_id": empresa_id},
        ).all()
        return [dict(linha._mapping) for linha in linhas]

    def departamentos(self, db: Session, *, empresa_id: str) -> dict[str, str]:
        """id → nome de TODOS os departamentos da empresa (nome só para exibição; a identidade é sempre o id)."""
        linhas = db.execute(text("SELECT id, nome FROM departamentos WHERE empresa_id = :empresa_id"), {"empresa_id": empresa_id}).all()
        return {linha[0]: linha[1] for linha in linhas}

    def usuario_existe(self, db: Session, *, empresa_id: str, usuario_id: str) -> bool:
        return db.execute(text("SELECT 1 FROM usuarios WHERE id = :id AND empresa_id = :empresa_id"), {"id": usuario_id, "empresa_id": empresa_id}).first() is not None

    def departamento_existe(self, db: Session, *, empresa_id: str, departamento_id: str) -> bool:
        return db.execute(text("SELECT 1 FROM departamentos WHERE id = :id AND empresa_id = :empresa_id"), {"id": departamento_id, "empresa_id": empresa_id}).first() is not None

    # ── capacidade individual (11B.2D-A) — UMA consulta cada, para TODAS as pessoas elegíveis (sem N+1) ─────────────────────────────────────────────

    def jornadas_dos_elegiveis(self, db: Session, *, empresa_id: str) -> list[tuple[str, int | None, str | None, str | None]]:
        """(usuario_id, dia_semana, "HH:MM", "HH:MM") das jornadas PRÓPRIAS dos elegíveis. Jornada sem nenhum período (todos os dias fechados) volta como uma linha com dia/horários nulos."""
        linhas = db.execute(
            text(
                f"""
                SELECT j.usuario_id, p.dia_semana, p.inicio, p.fim
                FROM usuario_jornadas j
                JOIN usuarios u ON u.id = j.usuario_id AND u.empresa_id = :empresa_id AND {_USUARIO_ELEGIVEL}
                LEFT JOIN usuario_jornada_periodos p ON p.jornada_id = j.id
                WHERE j.empresa_id = :empresa_id
                ORDER BY j.usuario_id, p.dia_semana, p.ordem
                """
            ),
            {"empresa_id": empresa_id},
        ).all()
        return [(l[0], l[1], l[2].strftime("%H:%M") if l[2] is not None else None, l[3].strftime("%H:%M") if l[3] is not None else None) for l in linhas]

    def ausencias_dos_elegiveis(self, db: Session, *, empresa_id: str, inicio: date, fim: date) -> list[tuple[str, date, date]]:
        """(usuario_id, inicio, fim) das ausências dos elegíveis que TOCAM [inicio, fim] (a semana consultada)."""
        linhas = db.execute(
            text(
                f"""
                SELECT a.usuario_id, a.inicio, a.fim
                FROM usuario_ausencias a
                JOIN usuarios u ON u.id = a.usuario_id AND u.empresa_id = :empresa_id AND {_USUARIO_ELEGIVEL}
                WHERE a.empresa_id = :empresa_id AND a.fim >= :inicio AND a.inicio <= :fim
                """
            ),
            {"empresa_id": empresa_id, "inicio": inicio, "fim": fim},
        ).all()
        return [(l[0], l[1], l[2]) for l in linhas]
