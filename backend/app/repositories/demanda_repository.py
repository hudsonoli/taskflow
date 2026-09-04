from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.core.escopo import EscopoDemanda
from app.models.demanda import Demanda
from app.models.demanda_departamento import DemandaDepartamento
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_departamento_responsavel import (
    DemandaWorkflowEtapaDepartamentoResponsavel,
)
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel

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

    def fixar_primeira_resposta_se_vazia(
        self, db: Session, *, demanda_id: str, empresa_id: str, timestamp: datetime
    ) -> bool:
        """`UPDATE` condicional — não um `if demanda.sla_primeira_resposta_em is None` em
        memória (Fase 2G.6D2B). Duas requisições concorrentes criando comentário na mesma
        Demanda podem ambas ler `None` antes de qualquer uma escrever; só o `WHERE ... IS
        NULL` na própria instrução, avaliado pelo banco sob o lock de linha do `UPDATE`,
        decide atomicamente qual delas vence — a segunda, ao ser desbloqueada, reavalia a
        condição contra o valor já commitado pela primeira e não casa nenhuma linha.

        Devolve `True` só quando ESTA chamada foi quem fixou o campo (`rowcount == 1`);
        `False` quando outra transação já tinha fixado antes (`rowcount == 0`) — nunca
        sobrescreve. Sem `commit` aqui (fica com quem chama, na mesma transação da ação que
        disparou a marcação).
        """
        resultado = db.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_primeira_resposta_em.is_(None),
            )
            .values(sla_primeira_resposta_em=timestamp)
        )
        return resultado.rowcount == 1

    def fixar_resolucao_sla_se_vazia(
        self, db: Session, *, demanda_id: str, empresa_id: str, timestamp: datetime
    ) -> bool:
        """Mesmo mecanismo de `fixar_primeira_resposta_se_vazia` (ver docstring lá) aplicado à
        resolução do SLA (Fase 2G.6D3B): `UPDATE` condicional, garantia de atomicidade vem do
        `WHERE ... IS NULL` sob o lock de linha do banco, nunca de um `if` em memória. Devolve
        `True` só quando ESTA chamada fixou o campo; `False` quando outra transação já tinha
        fixado antes. Sem `commit` (fica com quem chama)."""
        resultado = db.execute(
            sa_update(Demanda)
            .where(
                Demanda.id == demanda_id,
                Demanda.empresa_id == empresa_id,
                Demanda.sla_resolvido_em.is_(None),
            )
            .values(sla_resolvido_em=timestamp)
        )
        return resultado.rowcount == 1

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

    def listar_ids_por_projeto(self, db: Session, *, empresa_id: str, projeto_id: str) -> list[str]:
        """Só os IDs — usado pela agregação de eventos em Relatórios (Fase 2F.4), que precisa
        da lista de Demandas de um Projeto para filtrar `eventos.entidade_id`, nunca das
        entidades completas. Sem `escopo`: quem chama (`/relatorios`) já é admin/gestor
        gated na rota, mesma fronteira de confiança de `/eventos`.
        """
        statement = select(Demanda.id).where(
            Demanda.empresa_id == empresa_id, Demanda.projeto_id == projeto_id
        )
        return list(db.scalars(statement).all())

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

    # ----------------------------------------------------------------------------------
    # Etapas de workflow materializadas — ver app/models/demanda_workflow_etapa.py
    # ----------------------------------------------------------------------------------

    def criar_etapas_workflow(self, db: Session, etapas: list[DemandaWorkflowEtapa]) -> None:
        for etapa in etapas:
            db.add(etapa)
        db.flush()

    def criar_etapa_responsaveis(self, db: Session, responsaveis: list[DemandaWorkflowEtapaResponsavel]) -> None:
        for responsavel in responsaveis:
            db.add(responsavel)
        db.flush()

    def criar_etapa_departamentos_responsaveis(
        self, db: Session, responsaveis: list[DemandaWorkflowEtapaDepartamentoResponsavel]
    ) -> None:
        for responsavel in responsaveis:
            db.add(responsavel)
        db.flush()

    def listar_etapas_workflow_em_lote(
        self, db: Session, demanda_ids: list[str]
    ) -> dict[str, list[DemandaWorkflowEtapa]]:
        """Uma query para a página inteira — mesmo motivo de `listar_responsavel_ids_em_lote`."""
        agrupado: dict[str, list[DemandaWorkflowEtapa]] = {did: [] for did in demanda_ids}
        if not demanda_ids:
            return agrupado
        statement = (
            select(DemandaWorkflowEtapa)
            .where(DemandaWorkflowEtapa.demanda_id.in_(demanda_ids))
            .order_by(DemandaWorkflowEtapa.demanda_id.asc(), DemandaWorkflowEtapa.ordem.asc())
        )
        for etapa in db.scalars(statement).all():
            agrupado[etapa.demanda_id].append(etapa)
        return agrupado

    def listar_etapa_responsavel_ids_em_lote(self, db: Session, etapa_ids: list[str]) -> dict[str, list[str]]:
        resultado: dict[str, list[str]] = {etapa_id: [] for etapa_id in etapa_ids}
        if not etapa_ids:
            return resultado
        statement = select(
            DemandaWorkflowEtapaResponsavel.demanda_workflow_etapa_id,
            DemandaWorkflowEtapaResponsavel.usuario_id,
        ).where(DemandaWorkflowEtapaResponsavel.demanda_workflow_etapa_id.in_(etapa_ids))
        for etapa_id, usuario_id in db.execute(statement):
            resultado[etapa_id].append(usuario_id)
        return resultado

    def listar_etapa_departamento_ids_em_lote(self, db: Session, etapa_ids: list[str]) -> dict[str, list[str]]:
        resultado: dict[str, list[str]] = {etapa_id: [] for etapa_id in etapa_ids}
        if not etapa_ids:
            return resultado
        statement = select(
            DemandaWorkflowEtapaDepartamentoResponsavel.demanda_workflow_etapa_id,
            DemandaWorkflowEtapaDepartamentoResponsavel.departamento_id,
        ).where(DemandaWorkflowEtapaDepartamentoResponsavel.demanda_workflow_etapa_id.in_(etapa_ids))
        for etapa_id, departamento_id in db.execute(statement):
            resultado[etapa_id].append(departamento_id)
        return resultado
