from __future__ import annotations

from datetime import datetime

from sqlalchemy import Row, or_, select
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.core.escopo import EscopoDemanda
from app.models.cliente import Cliente
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.models.projeto import Projeto
from app.models.usuario import Usuario
# Reaproveita o MESMO predicado de segurança da listagem de Demanda — zero duplicação da
# regra de escopo (ver diagnóstico do Gerenciador de Arquivos). É um @staticmethod, chamável
# sem instanciar DemandaRepository; não há acoplamento de estado, só da regra.
from app.repositories.demanda_repository import DemandaRepository


class DemandaArquivoRepository:
    """Só persistência e consultas de metadado. O conteúdo físico é responsabilidade do
    service (`DemandaArquivoService`), que é quem decide o caminho em disco."""

    def create(self, db: Session, arquivo: DemandaArquivo) -> DemandaArquivo:
        db.add(arquivo)
        db.flush()
        return arquivo

    def delete(self, db: Session, arquivo: DemandaArquivo) -> None:
        db.delete(arquivo)
        db.flush()

    def update(self, db: Session, arquivo: DemandaArquivo) -> DemandaArquivo:
        db.add(arquivo)
        db.flush()
        return arquivo

    def get_by_id(self, db: Session, arquivo_id: str) -> DemandaArquivo | None:
        return db.get(DemandaArquivo, arquivo_id)

    def list_by_demanda(self, db: Session, demanda_id: str) -> list[DemandaArquivo]:
        statement = (
            select(DemandaArquivo)
            .where(DemandaArquivo.demanda_id == demanda_id)
            .order_by(DemandaArquivo.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def list_central(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        search: str | None = None,
        cliente_id: str | None = None,
        projeto_id: str | None = None,
        demanda_id: str | None = None,
        tipo: str | None = None,
        status_layout: str | None = None,
        usuario_id: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Row]:
        """`GET /arquivos` — UMA query, com todos os JOINs necessários pra resposta ser
        autossuficiente (ver `ArquivoCentralRead`): nunca materializa tudo em memória (sempre
        `limit`/`offset`), nunca N+1 (cliente/projeto/usuário vêm da MESMA query via
        `outerjoin`, não de uma consulta por item).

        Devolve `Row` (tuplas nomeadas), não `DemandaArquivo` — quem monta `ArquivoCentralRead`
        é `DemandaArquivoService.to_central_read`, não este repository (mesma divisão de
        responsabilidade do resto do projeto: repository traduz escopo em SQL, service decide
        formato de saída).
        """
        if escopo.vazio:
            return []

        statement = (
            select(
                DemandaArquivo,
                Demanda.numero_operacional,
                Demanda.codigo_referencia.label("demanda_codigo_referencia"),
                Demanda.nome.label("demanda_nome"),
                Demanda.cliente_id,
                Demanda.projeto_id,
                Cliente.nome.label("cliente_nome"),
                Projeto.nome.label("projeto_nome"),
                Usuario.nome.label("usuario_nome"),
                Usuario.is_system_account.label("usuario_sistema"),
            )
            .join(Demanda, DemandaArquivo.demanda_id == Demanda.id)
            .outerjoin(Cliente, Demanda.cliente_id == Cliente.id)
            .outerjoin(Projeto, Demanda.projeto_id == Projeto.id)
            .outerjoin(Usuario, DemandaArquivo.enviado_por_usuario_id == Usuario.id)
            .where(Demanda.empresa_id == escopo.empresa_id)
        )

        predicado = DemandaRepository._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)

        if cliente_id:
            statement = statement.where(Demanda.cliente_id == cliente_id)
        if projeto_id:
            statement = statement.where(Demanda.projeto_id == projeto_id)
        if demanda_id:
            statement = statement.where(DemandaArquivo.demanda_id == demanda_id)
        if tipo:
            statement = statement.where(DemandaArquivo.tipo == tipo)
        if status_layout:
            statement = statement.where(DemandaArquivo.status_layout == status_layout)
        if usuario_id:
            statement = statement.where(DemandaArquivo.enviado_por_usuario_id == usuario_id)
        if data_inicio:
            statement = statement.where(DemandaArquivo.created_at >= data_inicio)
        if data_fim:
            statement = statement.where(DemandaArquivo.created_at <= data_fim)

        # Mesma regra de app/core/busca.py do resto do projeto — nenhuma reimplementação
        # local. `termo.numero`/`termo.documento` não se aplicam a Arquivo, só `texto`.
        termo = interpretar_termo_busca(search)
        if not termo.vazio:
            like = f"%{termo.texto}%"
            statement = statement.where(
                or_(
                    DemandaArquivo.nome_original.ilike(like),
                    DemandaArquivo.titulo.ilike(like),
                    Demanda.nome.ilike(like),
                    Demanda.codigo_referencia.ilike(like),
                    Cliente.nome.ilike(like),
                    Projeto.nome.ilike(like),
                )
            )

        # `id` como desempate determinístico — mesmo motivo do tiebreaker em
        # DemandaRepository.list (sem ele, duas linhas com o mesmo created_at teriam ordem
        # não-determinística entre requests, quebrando paginação por offset).
        statement = statement.order_by(DemandaArquivo.created_at.desc(), DemandaArquivo.id.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.execute(statement).all())
