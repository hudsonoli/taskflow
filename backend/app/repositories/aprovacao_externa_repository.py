"""Persistência do Portal Externo de Aprovação (Fase 9B). Só consultas/escrita de linhas: as regras (estado derivado, autoridade, locks na ordem
Demanda → solicitação) ficam em `AprovacaoExternaService`."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.aprovacao_externa import AprovacaoExterna, AprovacaoExternaArquivo


class AprovacaoExternaRepository:
    def adicionar(self, db: Session, aprovacao: AprovacaoExterna, artefatos: Sequence[AprovacaoExternaArquivo]) -> AprovacaoExterna:
        db.add(aprovacao)
        db.flush()  # a solicitação existe antes dos artefatos (FK)
        for artefato in artefatos:
            db.add(artefato)
        db.flush()
        return aprovacao

    def por_token_hash(self, db: Session, token_hash: str) -> AprovacaoExterna | None:
        return db.scalar(select(AprovacaoExterna).where(AprovacaoExterna.token_hash == token_hash))

    def travar_por_id(self, db: Session, aprovacao_id: str) -> AprovacaoExterna | None:
        """`SELECT … FOR UPDATE` relendo o estado COMMITADO (chamar DEPOIS do lock da Demanda — ordem fixa Demanda → solicitação)."""
        return db.scalar(
            select(AprovacaoExterna)
            .where(AprovacaoExterna.id == aprovacao_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def por_id_da_etapa(self, db: Session, *, aprovacao_id: str, etapa_id: str, demanda_id: str) -> AprovacaoExterna | None:
        return db.scalar(
            select(AprovacaoExterna).where(
                AprovacaoExterna.id == aprovacao_id,
                AprovacaoExterna.workflow_etapa_id == etapa_id,
                AprovacaoExterna.demanda_id == demanda_id,
            )
        )

    def aberta_da_etapa(self, db: Session, etapa_id: str, *, travar: bool = False) -> AprovacaoExterna | None:
        """A solicitação NÃO decidida e NÃO revogada da etapa (no máximo uma — índice único parcial). Expirada continua "aberta" até ser revogada."""
        statement = select(AprovacaoExterna).where(
            AprovacaoExterna.workflow_etapa_id == etapa_id,
            AprovacaoExterna.decisao.is_(None),
            AprovacaoExterna.revogada_em.is_(None),
        )
        if travar:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return db.scalar(statement)

    def ultima_da_etapa(self, db: Session, etapa_id: str) -> AprovacaoExterna | None:
        """A solicitação mais recente da etapa (qualquer estado) — o que o painel interno mostra."""
        return db.scalar(
            select(AprovacaoExterna)
            .where(AprovacaoExterna.workflow_etapa_id == etapa_id)
            .order_by(AprovacaoExterna.criada_em.desc(), AprovacaoExterna.id.desc())
            .limit(1)
        )

    def artefatos(self, db: Session, aprovacao_id: str) -> list[AprovacaoExternaArquivo]:
        return list(
            db.scalars(
                select(AprovacaoExternaArquivo)
                .where(AprovacaoExternaArquivo.aprovacao_externa_id == aprovacao_id)
                .order_by(AprovacaoExternaArquivo.ordem.asc())
            ).all()
        )

    def artefato_por_ordem(self, db: Session, aprovacao_id: str, ordem: int) -> AprovacaoExternaArquivo | None:
        return db.get(AprovacaoExternaArquivo, (aprovacao_id, ordem))

    def aprovadores_externos_por_etapa(self, db: Session, etapa_ids: Sequence[str]) -> dict[str, str]:
        """Nome declarado de quem APROVOU externamente cada etapa (`decisao = 'aprovada'`), para o read model. Uma consulta, só ids pedidos."""
        if not etapa_ids:
            return {}
        linhas = db.execute(
            select(AprovacaoExterna.workflow_etapa_id, AprovacaoExterna.nome_aprovador)
            .where(AprovacaoExterna.workflow_etapa_id.in_(list(etapa_ids)), AprovacaoExterna.decisao == "aprovada")
            .order_by(AprovacaoExterna.decidida_em.asc())
        ).all()
        return {etapa_id: nome for etapa_id, nome in linhas if nome}  # a decisão mais recente prevalece (ordem asc → sobrescreve)

    # ----------------------------------------------------------------------------------
    # Proteção dos arquivos referenciados (exclusão individual e em lote)
    # ----------------------------------------------------------------------------------

    def arquivos_protegidos(self, db: Session, arquivo_ids: Sequence[str]) -> set[str]:
        """Dos arquivos pedidos, quais NÃO podem ser excluídos: referenciados por uma solicitação ABERTA (nem decidida nem revogada) ou DECIDIDA
        (evidência). Solicitação revogada sem decisão não protege. Chamar com as linhas dos arquivos já travadas (`FOR UPDATE`)."""
        if not arquivo_ids:
            return set()
        statement = (
            select(AprovacaoExternaArquivo.arquivo_id)
            .join(AprovacaoExterna, AprovacaoExterna.id == AprovacaoExternaArquivo.aprovacao_externa_id)
            .where(
                AprovacaoExternaArquivo.arquivo_id.in_(list(arquivo_ids)),
                # aberta (decisao NULL e revogada_em NULL) OU decidida (decisao NOT NULL)
                (AprovacaoExterna.decisao.is_not(None)) | (AprovacaoExterna.revogada_em.is_(None)),
            )
        )
        return {arquivo_id for (arquivo_id,) in db.execute(statement) if arquivo_id}

    def etapa_tem_solicitacao(self, db: Session, etapa_id: str) -> bool:
        return bool(db.scalar(select(exists().where(AprovacaoExterna.workflow_etapa_id == etapa_id))))
