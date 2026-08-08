from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.models.cliente import Cliente
from app.models.cliente_grupo import ClienteGrupo

STATUS_ARQUIVADO = "arquivado"


class ClienteRepository:
    """Só persistência e consultas — regras de duplicidade, transição, arquivamento,
    vínculo com grupo e eventos ficam no service."""

    def create(self, db: Session, cliente: Cliente) -> Cliente:
        db.add(cliente)
        db.flush()
        return cliente

    def get_by_id(self, db: Session, cliente_id: str) -> Cliente | None:
        return db.get(Cliente, cliente_id)

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Cliente | None:
        statement = select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_codigo_referencia(self, db: Session, *, empresa_id: str, codigo_referencia: str) -> Cliente | None:
        statement = select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.codigo_referencia == codigo_referencia,
        )
        return db.scalars(statement).first()

    def listar_semelhantes(
        self,
        db: Session,
        *,
        empresa_id: str,
        nome_normalizado: str,
        documento_normalizado: str | None,
        excluir_id: str | None = None,
    ) -> list[Cliente]:
        """Candidatos a duplicidade — mesmo nome OU mesmo documento.

        Não existe UNIQUE de nome nem de documento (ver model): isto alimenta um AVISO,
        nunca um bloqueio. Inclui arquivados de propósito: reativar um cliente arquivado é
        exatamente o caso em que o operador precisa ser avisado.
        """
        condicoes = [Cliente.nome_normalizado == nome_normalizado]
        if documento_normalizado:
            condicoes.append(Cliente.documento_normalizado == documento_normalizado)

        statement = select(Cliente).where(Cliente.empresa_id == empresa_id, or_(*condicoes))
        if excluir_id:
            statement = statement.where(Cliente.id != excluir_id)
        return list(db.scalars(statement.order_by(Cliente.nome.asc())).all())

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        search: str | None = None,
        grupo_cliente_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Cliente]:
        statement = select(Cliente).where(Cliente.empresa_id == empresa_id)

        if status:
            statement = statement.where(Cliente.status == status)
        else:
            # Sem status explícito, arquivado fica oculto — filtro em SQL, antes da paginação.
            statement = statement.where(Cliente.status != STATUS_ARQUIVADO)

        if grupo_cliente_id:
            statement = statement.where(
                Cliente.id.in_(
                    select(ClienteGrupo.cliente_id).where(
                        ClienteGrupo.grupo_cliente_id == grupo_cliente_id
                    )
                )
            )

        termo = interpretar_termo_busca(search)
        if not termo.vazio:
            # A decisão de ativar ou não a busca por documento mora em app/core/busca.py —
            # regra única e testável. Aqui só se monta o SQL correspondente.
            like = f"%{termo.texto}%"
            # Nome, razão social e os DOIS códigos. ILIKE cobre o case-insensitive por
            # código (c26000001 = C26000001). Nome nunca é identificador — é busca textual.
            condicoes = [
                Cliente.nome.ilike(like),
                Cliente.razao_social.ilike(like),
                Cliente.codigo_referencia.ilike(like),
                Cliente.codigo_interno.ilike(like),
            ]
            if termo.documento is not None:
                # Só quando o termo é plausivelmente um documento. Busca pela forma
                # normalizada, então "39346861024508" encontra "39.346.861/0245-08".
                condicoes.append(Cliente.documento_normalizado.ilike(f"%{termo.documento}%"))
            statement = statement.where(or_(*condicoes))

        statement = statement.order_by(Cliente.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def list_diretorio(self, db: Session, *, empresa_id: str) -> list[Cliente]:
        """Inclui arquivados — referências antigas precisam continuar resolvendo o nome."""
        statement = (
            select(Cliente).where(Cliente.empresa_id == empresa_id).order_by(Cliente.nome.asc())
        )
        return list(db.scalars(statement).all())

    def update(self, db: Session, cliente: Cliente) -> Cliente:
        db.add(cliente)
        db.flush()
        return cliente

    # --- associação N:N com GrupoCliente ------------------------------------------

    def listar_grupo_ids(self, db: Session, cliente_id: str) -> list[str]:
        statement = (
            select(ClienteGrupo.grupo_cliente_id)
            .where(ClienteGrupo.cliente_id == cliente_id)
            .order_by(ClienteGrupo.grupo_cliente_id.asc())
        )
        return list(db.scalars(statement).all())

    def listar_grupo_ids_em_lote(self, db: Session, cliente_ids: list[str]) -> dict[str, list[str]]:
        """Evita N+1 ao serializar listagens: uma query para todos os clientes da página."""
        if not cliente_ids:
            return {}
        statement = select(ClienteGrupo.cliente_id, ClienteGrupo.grupo_cliente_id).where(
            ClienteGrupo.cliente_id.in_(cliente_ids)
        )
        agrupado: dict[str, list[str]] = {cliente_id: [] for cliente_id in cliente_ids}
        for cliente_id, grupo_id in db.execute(statement).all():
            agrupado[cliente_id].append(grupo_id)
        for grupos in agrupado.values():
            grupos.sort()
        return agrupado

    def adicionar_grupo(self, db: Session, vinculo: ClienteGrupo) -> None:
        db.add(vinculo)
        db.flush()

    def remover_grupo(self, db: Session, *, cliente_id: str, grupo_cliente_id: str) -> None:
        vinculo = db.get(ClienteGrupo, {"cliente_id": cliente_id, "grupo_cliente_id": grupo_cliente_id})
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()
