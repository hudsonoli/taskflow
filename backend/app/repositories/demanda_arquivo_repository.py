from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Row, func, or_, select
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


def _aplicar_lista(statement, coluna, incluir: Sequence[str] | None, excluir: Sequence[str] | None):
    """Filtro de um campo: `incluir` = "é um de" (OR); `excluir` = "não é um de". NULL não é igual a nenhum valor,
    então "não é" mantém as linhas em que o campo é NULL (um `NOT IN` puro as descartaria)."""
    if incluir:
        statement = statement.where(coluna.in_(list(incluir)))
    if excluir:
        statement = statement.where(or_(coluna.is_(None), coluna.not_in(list(excluir))))
    return statement


@dataclass(frozen=True)
class FiltrosCentral:
    """Filtros estruturados do Gerenciador de Arquivos — UMA definição para a listagem (`GET /arquivos`) e para as operações em lote
    (Fase 8B): o universo selecionado em lote é, por construção, o MESMO da listagem.

    `contexto_*` é o recorte FIXO da tela (aba de Cliente/Projeto/Demanda). Vai por AND, separado dos filtros: um filtro avançado
    nunca o substitui nem o amplia."""

    search: str | None = None
    cliente_ids: Sequence[str] | None = None
    projeto_ids: Sequence[str] | None = None
    demanda_ids: Sequence[str] | None = None
    tipos: Sequence[str] | None = None
    status_layouts: Sequence[str] | None = None
    usuario_ids: Sequence[str] | None = None
    cliente_ids_excluir: Sequence[str] | None = None
    projeto_ids_excluir: Sequence[str] | None = None
    demanda_ids_excluir: Sequence[str] | None = None
    tipos_excluir: Sequence[str] | None = None
    status_layouts_excluir: Sequence[str] | None = None
    usuario_ids_excluir: Sequence[str] | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    contexto_cliente_id: str | None = None
    contexto_projeto_id: str | None = None
    contexto_demanda_id: str | None = None


def restringir_central(statement, escopo: EscopoDemanda, f: FiltrosCentral):
    """Tenant + escopo da Demanda + filtros, tudo no SQL. `statement` já tem `Demanda` (inner) e `Cliente`/`Projeto` (outer) em JOIN."""
    statement = statement.where(Demanda.empresa_id == escopo.empresa_id)

    predicado = DemandaRepository._predicado_escopo(escopo)
    if predicado is not None:
        statement = statement.where(predicado)

    if f.contexto_cliente_id:
        statement = statement.where(Demanda.cliente_id == f.contexto_cliente_id)
    if f.contexto_projeto_id:
        statement = statement.where(Demanda.projeto_id == f.contexto_projeto_id)
    if f.contexto_demanda_id:
        statement = statement.where(DemandaArquivo.demanda_id == f.contexto_demanda_id)

    statement = _aplicar_lista(statement, Demanda.cliente_id, f.cliente_ids, f.cliente_ids_excluir)
    statement = _aplicar_lista(statement, Demanda.projeto_id, f.projeto_ids, f.projeto_ids_excluir)
    statement = _aplicar_lista(statement, DemandaArquivo.demanda_id, f.demanda_ids, f.demanda_ids_excluir)
    statement = _aplicar_lista(statement, DemandaArquivo.tipo, f.tipos, f.tipos_excluir)
    statement = _aplicar_lista(statement, DemandaArquivo.status_layout, f.status_layouts, f.status_layouts_excluir)
    statement = _aplicar_lista(statement, DemandaArquivo.enviado_por_usuario_id, f.usuario_ids, f.usuario_ids_excluir)
    if f.data_inicio:
        statement = statement.where(DemandaArquivo.created_at >= f.data_inicio)
    if f.data_fim:
        statement = statement.where(DemandaArquivo.created_at <= f.data_fim)

    # Mesma regra de app/core/busca.py do resto do projeto — nenhuma reimplementação local.
    # `termo.numero`/`termo.documento` não se aplicam a Arquivo, só `texto`.
    termo = interpretar_termo_busca(f.search)
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
    return statement


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
        cliente_ids: Sequence[str] | None = None,
        projeto_ids: Sequence[str] | None = None,
        demanda_ids: Sequence[str] | None = None,
        tipos: Sequence[str] | None = None,
        status_layouts: Sequence[str] | None = None,
        usuario_ids: Sequence[str] | None = None,
        cliente_ids_excluir: Sequence[str] | None = None,
        projeto_ids_excluir: Sequence[str] | None = None,
        demanda_ids_excluir: Sequence[str] | None = None,
        tipos_excluir: Sequence[str] | None = None,
        status_layouts_excluir: Sequence[str] | None = None,
        usuario_ids_excluir: Sequence[str] | None = None,
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

        Filtros estruturados (filtros avançados): entre campos diferentes vale AND; dentro de um campo,
        `*_ids`/`tipos`/... é OR ("é um de") e `*_excluir` é "não é um de" (ver `_aplicar_lista`). Tudo dentro
        do SQL, antes do `limit`/`offset`.
        """
        if escopo.vazio:
            return []

        statement = (
            select(
                DemandaArquivo,
                Demanda.numero_operacional,
                Demanda.identificador.label("demanda_identificador"),
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
        )
        statement = restringir_central(
            statement,
            escopo,
            FiltrosCentral(
                search=search,
                cliente_ids=cliente_ids,
                projeto_ids=projeto_ids,
                demanda_ids=demanda_ids,
                tipos=tipos,
                status_layouts=status_layouts,
                usuario_ids=usuario_ids,
                cliente_ids_excluir=cliente_ids_excluir,
                projeto_ids_excluir=projeto_ids_excluir,
                demanda_ids_excluir=demanda_ids_excluir,
                tipos_excluir=tipos_excluir,
                status_layouts_excluir=status_layouts_excluir,
                usuario_ids_excluir=usuario_ids_excluir,
                data_inicio=data_inicio,
                data_fim=data_fim,
            ),
        )

        # `id` como desempate determinístico — mesmo motivo do tiebreaker em
        # DemandaRepository.list (sem ele, duas linhas com o mesmo created_at teriam ordem
        # não-determinística entre requests, quebrando paginação por offset).
        statement = statement.order_by(DemandaArquivo.created_at.desc(), DemandaArquivo.id.desc())
        statement = statement.limit(limit).offset(offset)

        return list(db.execute(statement).all())

    def selecionar_lote(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        ids: Sequence[str] | None = None,
        excluir_ids: Sequence[str] | None = None,
        limite: int | None = None,
        somente_fisicos: bool = False,
        travar: bool = False,
    ) -> list[Row]:
        """Operações em lote (Fase 8B): as linhas AUTORIZADAS da seleção — mesmo tenant, mesmo escopo e mesmos filtros da listagem
        (`restringir_central`), em UMA query sem N+1. `ids` restringe a IDs explícitos (modo "ids"); `excluir_ids` tira exceções do
        modo "todos do filtro". `limite` busca no máximo `limite` linhas (quem chama passa teto+1 para detectar excesso). `travar` faz
        `SELECT … FOR UPDATE OF demanda_arquivos` — a exclusão usa para serializar com outra exclusão simultânea."""
        if escopo.vazio:
            return []
        statement = (
            select(
                DemandaArquivo.id,
                DemandaArquivo.demanda_id,
                DemandaArquivo.tipo,
                DemandaArquivo.nome_original,
                DemandaArquivo.nome_fisico,
                DemandaArquivo.titulo,
                DemandaArquivo.tamanho_bytes,
            )
            .join(Demanda, DemandaArquivo.demanda_id == Demanda.id)
            .outerjoin(Cliente, Demanda.cliente_id == Cliente.id)
            .outerjoin(Projeto, Demanda.projeto_id == Projeto.id)
        )
        statement = restringir_central(statement, escopo, filtros)
        if ids is not None:
            statement = statement.where(DemandaArquivo.id.in_(list(ids)))
        if excluir_ids:
            statement = statement.where(DemandaArquivo.id.not_in(list(excluir_ids)))
        if somente_fisicos:
            statement = statement.where(DemandaArquivo.tipo != "link")
        statement = statement.order_by(DemandaArquivo.created_at.desc(), DemandaArquivo.id.desc())
        if limite is not None:
            statement = statement.limit(limite)
        if travar:
            statement = statement.with_for_update(of=DemandaArquivo)
        return list(db.execute(statement).all())

    def contar_lote(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        filtros: FiltrosCentral,
        excluir_ids: Sequence[str] | None = None,
    ) -> tuple[int, int, int]:
        """Total, links e bytes do universo autorizado (agregado no SQL — nunca traz as linhas)."""
        if escopo.vazio:
            return (0, 0, 0)
        statement = (
            select(
                func.count(DemandaArquivo.id),
                func.count(DemandaArquivo.id).filter(DemandaArquivo.tipo == "link"),
                func.coalesce(func.sum(DemandaArquivo.tamanho_bytes), 0),
            )
            .select_from(DemandaArquivo)
            .join(Demanda, DemandaArquivo.demanda_id == Demanda.id)
            .outerjoin(Cliente, Demanda.cliente_id == Cliente.id)
            .outerjoin(Projeto, Demanda.projeto_id == Projeto.id)
        )
        statement = restringir_central(statement, escopo, filtros)
        if excluir_ids:
            statement = statement.where(DemandaArquivo.id.not_in(list(excluir_ids)))
        return db.execute(statement).one()
