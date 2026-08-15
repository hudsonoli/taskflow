"""Repository de SessaoTrabalho.

`get_active_equivalent` e `.list` filtram `usuario_id`/`departamento_id` por comparação
direta de UUID — sem `LOWER`/`TRANSLATE` nem ponte de acentuação (diferente do caso de
Departamento por nome, `0008`; aqui sempre foi id). Pós expand/contract (`0015`–`0018`, ver
`app/models/sessao_trabalho.py`): não há mais coluna textual legada para confundir com a FK.
"""

from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.sessao_trabalho import SessaoTrabalho


class SessaoTrabalhoRepository:
    def create(self, db: Session, sessao: SessaoTrabalho) -> SessaoTrabalho:
        db.add(sessao)
        db.flush()
        return sessao

    def flush(self, db: Session) -> None:
        db.flush()

    def get_by_id(self, db: Session, sessao_id: str) -> SessaoTrabalho | None:
        return db.get(SessaoTrabalho, sessao_id)

    def get_by_evento_inicio_id(self, db: Session, evento_inicio_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_inicio_id == evento_inicio_id)
        return db.scalar(statement)

    def get_by_evento_fim_id(self, db: Session, evento_fim_id: str) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(SessaoTrabalho.evento_fim_id == evento_fim_id)
        return db.scalar(statement)

    def get_active_equivalent(
        self,
        db: Session,
        *,
        demanda_id: str,
        usuario_id: str | None,
        departamento_id: str | None,
    ) -> SessaoTrabalho | None:
        statement = select(SessaoTrabalho).where(
            SessaoTrabalho.demanda_id == demanda_id,
            SessaoTrabalho.status == "ativa",
        )
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        else:
            statement = statement.where(
                SessaoTrabalho.usuario_id.is_(None),
                SessaoTrabalho.departamento_id == departamento_id,
            )
        return db.scalar(statement)

    def list(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        demanda_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        workflow_etapa_id: str | None = None,
        status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessaoTrabalho]:
        statement = select(SessaoTrabalho)

        if empresa_id:
            statement = statement.where(SessaoTrabalho.empresa_id == empresa_id)
        if demanda_id:
            statement = statement.where(SessaoTrabalho.demanda_id == demanda_id)
        if usuario_id:
            statement = statement.where(SessaoTrabalho.usuario_id == usuario_id)
        if departamento_id:
            statement = statement.where(SessaoTrabalho.departamento_id == departamento_id)
        if workflow_etapa_id:
            statement = statement.where(SessaoTrabalho.workflow_etapa_id == workflow_etapa_id)
        if status:
            statement = statement.where(SessaoTrabalho.status == status)
        if data_inicio:
            statement = statement.where(SessaoTrabalho.inicio_em >= data_inicio)
        if data_fim:
            statement = statement.where(SessaoTrabalho.inicio_em <= data_fim)

        statement = statement.order_by(SessaoTrabalho.inicio_em.desc(), SessaoTrabalho.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def horas_departamento(
        self, db: Session, *, empresa_id: str, departamento_id: str
    ) -> tuple[float, int]:
        """Agregado em SQL — nunca busca sessões individuais para o chamador somar.

        ## Pertencimento (a mesma regra OR que `horasExecutadasPorEscopo` aplicava no
        frontend antes deste endpoint existir, ver `lib/escopo-operacional.ts`)

        Uma sessão conta para o departamento quando:
        - o RESPONSÁVEL (`usuario_id`) tem `usuarios.departamento_id = departamento_id`
          (colaborador definido por vínculo organizacional — decisão aprovada: não por
          responsabilidade em Demanda); OU
        - a sessão foi aberta vinculada diretamente ao departamento (`departamento_id`),
          sem usuário — caso de trabalho não atribuído a uma pessoa específica.

        ## Duração (mesma fórmula do frontend, comparada campo a campo antes de implementar)

        Sessão ENCERRADA usa `duracao_segundos`, já calculado no fechamento — não recalcula.
        Sessão ainda ATIVA (`duracao_segundos IS NULL`) calcula ao vivo:
        `EXTRACT(EPOCH FROM (NOW() - inicio_em))`, com `GREATEST(0, ...)` (mesma defesa que o
        frontend fazia com `Math.max(0, …)` contra relógio adiantado) e `FLOOR(...)` (mesmo
        truncamento de `Math.floor`, não arredondamento). `NOW()` e `inicio_em` são os dois
        `timestamptz` — a subtração já é em UTC, sem conversão de fuso.
        """
        statement = text(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN s.duracao_segundos IS NOT NULL THEN s.duracao_segundos
                        ELSE GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (NOW() - s.inicio_em))))
                    END
                ), 0) AS segundos_totais,
                COUNT(*) AS sessoes_consideradas
            FROM sessoes_trabalho s
            WHERE s.empresa_id = :empresa_id
              AND (
                s.usuario_id IN (
                    SELECT id FROM usuarios
                    WHERE departamento_id = :departamento_id AND empresa_id = :empresa_id
                )
                OR s.departamento_id = :departamento_id
              )
            """
        )
        resultado = db.execute(
            statement, {"empresa_id": empresa_id, "departamento_id": departamento_id}
        ).one()
        horas_consumidas = float(resultado.segundos_totais) / 3600
        return horas_consumidas, int(resultado.sessoes_consideradas)
