from __future__ import annotations

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.core.escopo import EscopoDemanda
from app.models.demanda import Demanda
from app.models.demanda_departamento import DemandaDepartamento
from app.models.demanda_responsavel import DemandaResponsavel

STATUS_ARQUIVADO = "arquivada"


class DemandaRepository:
    """Só persistência e consultas. Transição, expediente, bloqueio, vínculos e eventos ficam
    no service; a **decisão** de escopo fica em `app/core/escopo.py`.

    Este repository *traduz* um `EscopoDemanda` já resolvido em SQL — não decide quem vê o
    quê, e não interpreta termo de busca. As duas regras têm dono único em outro lugar.
    """

    def create(self, db: Session, demanda: Demanda) -> Demanda:
        db.add(demanda)
        db.flush()
        return demanda

    def update(self, db: Session, demanda: Demanda) -> Demanda:
        db.add(demanda)
        db.flush()
        return demanda

    # ----------------------------------------------------------------------------------
    # Escopo — a mesma expressão para listar e para acessar por UUID
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _predicado_escopo(escopo: EscopoDemanda) -> ColumnElement[bool] | None:
        """Traduz o escopo em `WHERE`. `None` significa "sem restrição além da empresa".

        Cada ramo só entra se o campo correspondente estiver preenchido: um `IN ()` vazio é
        SQL válido que nunca casa, e somá-lo à cláusula tornaria a leitura do plano confusa
        sem mudar o resultado.
        """
        if escopo.visao_total:
            return None

        ramos: list[ColumnElement[bool]] = []

        if escopo.usuario_responsavel:
            ramos.append(
                Demanda.id.in_(
                    select(DemandaResponsavel.demanda_id).where(
                        DemandaResponsavel.usuario_id == escopo.usuario_id
                    )
                )
            )

        if escopo.departamento_ids:
            ramos.append(
                Demanda.id.in_(
                    select(DemandaDepartamento.demanda_id).where(
                        DemandaDepartamento.departamento_id.in_(escopo.departamento_ids)
                    )
                )
            )

        if escopo.cliente_ids:
            ramos.append(Demanda.cliente_id.in_(escopo.cliente_ids))

        if escopo.incluir_criadas_por_usuario:
            ramos.append(Demanda.criado_por_usuario_id == escopo.usuario_id)

        # `escopo.vazio` é tratado antes de chegar aqui; se ainda assim não houver ramo,
        # negar tudo é o único fim seguro — jamais devolver a empresa inteira por omissão.
        if not ramos:
            return Demanda.id.is_(None)

        return or_(*ramos)

    def get_by_id(self, db: Session, demanda_id: str) -> Demanda | None:
        """Sem escopo — uso interno de quem já validou o acesso (ex.: reidratar após escrita).

        **Rotas não chamam este método.** Elas usam `get_no_escopo`; ver a docstring de lá.
        """
        return db.get(Demanda, demanda_id)

    def get_no_escopo(
        self, db: Session, *, demanda_id: str, escopo: EscopoDemanda
    ) -> Demanda | None:
        """Busca por UUID **aplicando o mesmo escopo da listagem**.

        Mesmo tenant não é autorização. Sem isto, quem conhecesse o UUID leria e editaria
        qualquer demanda da empresa por acesso direto, contornando exatamente o filtro que
        `list` aplica — o escopo protegeria a lista e não o registro.

        Devolver `None` (que a rota converte em **404**) é deliberado: um 403 confirmaria que
        o registro existe e a quem pedir bastaria variar o UUID para mapear a base.
        """
        if escopo.vazio:
            return None

        statement = select(Demanda).where(
            Demanda.id == demanda_id, Demanda.empresa_id == escopo.empresa_id
        )
        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)
        return db.scalars(statement).first()

    def get_por_codigo_no_escopo(
        self, db: Session, *, codigo_referencia: str, escopo: EscopoDemanda
    ) -> Demanda | None:
        """Mesma regra de `get_no_escopo`, mas pela identidade oficial (`T26000001`).

        Existe para os uploads, que endereçam a pasta pelo código e não pelo UUID. Sem esta
        checagem, conhecer o código — que é curto, sequencial e adivinhável — daria acesso aos
        arquivos de qualquer demanda da empresa.
        """
        if escopo.vazio:
            return None

        statement = select(Demanda).where(
            Demanda.codigo_referencia == codigo_referencia,
            Demanda.empresa_id == escopo.empresa_id,
        )
        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)
        return db.scalars(statement).first()

    # ----------------------------------------------------------------------------------
    # Listagem
    # ----------------------------------------------------------------------------------

    def list(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        status: str | None = None,
        search: str | None = None,
        cliente_id: str | None = None,
        projeto_id: str | None = None,
        departamento_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Demanda]:
        # Operador sem departamento e sem demanda atribuída. Lista vazia é a resposta correta:
        # não é falta de permissão, é ausência de vínculo.
        if escopo.vazio:
            return []

        statement = select(Demanda).where(Demanda.empresa_id == escopo.empresa_id)

        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)

        if status:
            statement = statement.where(Demanda.status == status)
        else:
            # Sem status explícito, arquivada fica oculta — filtro em SQL, antes da paginação.
            statement = statement.where(Demanda.status != STATUS_ARQUIVADO)

        if cliente_id:
            statement = statement.where(Demanda.cliente_id == cliente_id)

        if projeto_id:
            statement = statement.where(Demanda.projeto_id == projeto_id)

        if departamento_id:
            statement = statement.where(
                Demanda.id.in_(
                    select(DemandaDepartamento.demanda_id).where(
                        DemandaDepartamento.departamento_id == departamento_id
                    )
                )
            )

        # A decisão "isto é texto, documento ou número?" mora INTEIRA em app/core/busca.py.
        # Este repository não extrai dígitos nem decide nada sobre o termo — reimplementar a
        # regra foi o que causou o incidente do Cliente (91 resultados em vez de 3). Demanda
        # não tem documento, então `termo.documento` é ignorado aqui.
        termo = interpretar_termo_busca(search)
        if not termo.vazio:
            like = f"%{termo.texto}%"
            alternativas: list[ColumnElement[bool]] = [
                Demanda.nome.ilike(like),
                Demanda.codigo_referencia.ilike(like),
                Demanda.pit.ilike(like),
            ]
            # Igualdade EXATA, nunca ILIKE: "2063" localiza a demanda #2063, não toda demanda
            # cujo número contenha 2063.
            if termo.numero is not None:
                alternativas.append(Demanda.numero_operacional == termo.numero)
            statement = statement.where(or_(*alternativas))

        statement = (
            statement.order_by(Demanda.numero_operacional.desc()).limit(limit).offset(offset)
        )
        return list(db.scalars(statement).all())

    # ----------------------------------------------------------------------------------
    # Vínculos N:N
    # ----------------------------------------------------------------------------------

    def listar_responsavel_ids(self, db: Session, demanda_id: str) -> list[str]:
        statement = (
            select(DemandaResponsavel.usuario_id)
            .where(DemandaResponsavel.demanda_id == demanda_id)
            .order_by(DemandaResponsavel.usuario_id.asc())
        )
        return list(db.scalars(statement).all())

    def listar_departamento_ids(self, db: Session, demanda_id: str) -> list[str]:
        statement = (
            select(DemandaDepartamento.departamento_id)
            .where(DemandaDepartamento.demanda_id == demanda_id)
            .order_by(DemandaDepartamento.departamento_id.asc())
        )
        return list(db.scalars(statement).all())

    # Versões em lote — uma query para a página inteira, em vez de N+1 ao serializar.

    def listar_responsavel_ids_em_lote(
        self, db: Session, demanda_ids: list[str]
    ) -> dict[str, list[str]]:
        return self._agrupar(
            db,
            demanda_ids,
            select(DemandaResponsavel.demanda_id, DemandaResponsavel.usuario_id).where(
                DemandaResponsavel.demanda_id.in_(demanda_ids)
            ),
        )

    def listar_departamento_ids_em_lote(
        self, db: Session, demanda_ids: list[str]
    ) -> dict[str, list[str]]:
        return self._agrupar(
            db,
            demanda_ids,
            select(DemandaDepartamento.demanda_id, DemandaDepartamento.departamento_id).where(
                DemandaDepartamento.demanda_id.in_(demanda_ids)
            ),
        )

    @staticmethod
    def _agrupar(db: Session, demanda_ids: list[str], statement) -> dict[str, list[str]]:
        if not demanda_ids:
            return {}
        agrupado: dict[str, list[str]] = {did: [] for did in demanda_ids}
        for demanda_id, valor in db.execute(statement).all():
            agrupado[demanda_id].append(valor)
        for valores in agrupado.values():
            valores.sort()
        return agrupado

    def adicionar_responsavel(self, db: Session, vinculo: DemandaResponsavel) -> None:
        db.add(vinculo)
        db.flush()

    def remover_responsavel(self, db: Session, *, demanda_id: str, usuario_id: str) -> None:
        vinculo = db.get(DemandaResponsavel, {"demanda_id": demanda_id, "usuario_id": usuario_id})
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()

    def adicionar_departamento(self, db: Session, vinculo: DemandaDepartamento) -> None:
        db.add(vinculo)
        db.flush()

    def remover_departamento(self, db: Session, *, demanda_id: str, departamento_id: str) -> None:
        vinculo = db.get(
            DemandaDepartamento, {"demanda_id": demanda_id, "departamento_id": departamento_id}
        )
        if vinculo is not None:
            db.delete(vinculo)
            db.flush()

    def contar_por_empresa(self, db: Session, empresa_id: str) -> int:
        """Usado pelo CLI de número operacional: semear um contador com demandas já emitidas
        reemitiria números, então o CLI aborta."""
        from sqlalchemy import func

        return int(
            db.scalar(
                select(func.count(Demanda.id)).where(Demanda.empresa_id == empresa_id)
            )
            or 0
        )

    def maior_numero_operacional(self, db: Session, empresa_id: str) -> int | None:
        from sqlalchemy import func

        return db.scalar(
            select(func.max(Demanda.numero_operacional)).where(Demanda.empresa_id == empresa_id)
        )
