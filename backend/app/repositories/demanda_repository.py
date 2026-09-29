from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import ColumnElement, and_, case, func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.core.busca import interpretar_termo_busca
from app.core.escopo import EscopoDemanda
from app.core.relogio import agora_utc
from app.models.cliente import Cliente
from app.models.demanda import Demanda
from app.models.demanda_departamento import DemandaDepartamento
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.demanda_workflow_etapa_departamento_responsavel import (
    DemandaWorkflowEtapaDepartamentoResponsavel,
)
from app.models.demanda_workflow_etapa_responsavel import DemandaWorkflowEtapaResponsavel
from app.models.departamento import Departamento
from app.models.equipe_membro import EquipeMembro
from app.models.projeto import Projeto
from app.models.usuario import Usuario

STATUS_ARQUIVADO = "arquivada"
# Dias úteis por semana usados na aproximação de capacidade — mesma constante de
# `DIAS_UTEIS_SEMANA` em MeuDepartamentoView.tsx (D2-B5). Sem calendário de dias úteis, dias
# corridos mesmo (aproximação já existente, ver lib/workflow-modelo.ts).
DIAS_UTEIS_SEMANA = 5


class SortDemandas(StrEnum):
    """Ordenação de `list()` — D2-B3. Default preserva o comportamento de todo caller
    existente (DemandasView, ProjetoDemandasSection); `PRAZO_ASC` é usado pela Pauta.
    `SINALIZADA_DESC` (D2-D2) é o Dashboard pessoal — reproduz o `.sort()` estável do
    frontend pré-migração (sinalizada primeiro, resto na ordem de chegada), agora explícito
    como desempate."""

    NUMERO_OPERACIONAL_DESC = "numero_operacional_desc"
    PRAZO_ASC = "prazo_asc"
    SINALIZADA_DESC = "sinalizada_desc"


class OrigemDemanda(StrEnum):
    """D2-B5 — origem é sempre derivada (nunca persistida): `interna` quando não há
    cliente vinculado, `cliente` caso contrário. Mesmo par já usado em
    `escopo-operacional.ts` (`OrigemDemanda`/`classificarTarefa`)."""

    INTERNA = "interna"
    CLIENTE = "cliente"


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

    def list_por_ids(
        self, db: Session, *, ids: list[str], escopo: EscopoDemanda
    ) -> list[Demanda]:
        """D2-C — resolução histórica em lote. Mesma semântica de escopo de `get_no_escopo`
        (arquivada incluída — sem `status != STATUS_ARQUIVADO`), não a de `list()`/
        `/diretorio` (que excluem arquivada por padrão): quem já podia ver uma Demanda
        individualmente continua podendo, mesmo depois de arquivada.

        UMA consulta `IN (...)` + predicado de escopo — nunca um `get_no_escopo` por ID em
        loop. IDs inexistentes/fora do escopo simplesmente não entram no resultado; ordem não
        é garantida (quem chama indexa por `id`)."""
        if escopo.vazio or not ids:
            return []
        statement = select(Demanda).where(
            Demanda.id.in_(ids), Demanda.empresa_id == escopo.empresa_id
        )
        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)
        return list(db.scalars(statement).all())

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
        departamento_ids: list[str] | None = None,
        responsavel_id: str | None = None,
        equipe_id: str | None = None,
        prioridade: str | None = None,
        origem: OrigemDemanda | None = None,
        prazo_inicio: datetime | None = None,
        prazo_fim: datetime | None = None,
        atrasada: bool = False,
        nao_finalizada: bool = False,
        sort: SortDemandas = SortDemandas.NUMERO_OPERACIONAL_DESC,
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
            # Lista separada por vírgula (ex.: "pausada,bloqueada") — D2-B1: DemandasView tem
            # um filtro de UI que agrupa dois status reais, e aplicar isso localmente sobre uma
            # página já paginada esconderia itens de outras páginas. `.in_()` com valor único é
            # idêntico a `==`, então nenhum chamador existente muda de comportamento.
            valores_status = [valor.strip() for valor in status.split(",") if valor.strip()]
            statement = statement.where(Demanda.status.in_(valores_status))
        else:
            # Sem status explícito, arquivada fica oculta — filtro em SQL, antes da paginação.
            statement = statement.where(Demanda.status != STATUS_ARQUIVADO)

        if cliente_id:
            statement = statement.where(Demanda.cliente_id == cliente_id)

        if projeto_id:
            statement = statement.where(Demanda.projeto_id == projeto_id)

        if departamento_ids:
            # Aceita um ou vários ids (D2-B3: Pauta filtra por múltiplos departamentos, OR
            # entre eles) — mesma subquery de antes, só troca `==` por `.in_()`; um único id
            # continua idêntico ao comportamento anterior.
            statement = statement.where(
                Demanda.id.in_(
                    select(DemandaDepartamento.demanda_id).where(
                        DemandaDepartamento.departamento_id.in_(departamento_ids)
                    )
                )
            )

        if responsavel_id:
            # D2-B5 (MeuDepartamentoView: filtro "Colaborador") — mesma subquery de
            # `usuario_responsavel` em `_predicado_escopo`, só que como filtro funcional, não
            # de segurança.
            statement = statement.where(
                Demanda.id.in_(
                    select(DemandaResponsavel.demanda_id).where(
                        DemandaResponsavel.usuario_id == responsavel_id
                    )
                )
            )

        if equipe_id:
            # D2-B5 (filtro "Equipe"): demanda tem AO MENOS UM responsável que é membro da
            # equipe — join dentro da subquery, nunca na query principal (não multiplica
            # Demanda mesmo com múltiplos responsáveis/membros).
            statement = statement.where(
                Demanda.id.in_(
                    select(DemandaResponsavel.demanda_id)
                    .join(EquipeMembro, EquipeMembro.usuario_id == DemandaResponsavel.usuario_id)
                    .where(EquipeMembro.equipe_id == equipe_id)
                )
            )

        if prioridade:
            statement = statement.where(Demanda.prioridade == prioridade)

        if origem is not None:
            # Sempre derivada, nunca persistida — mesmo par de `classificarTarefa` (frontend).
            if origem == OrigemDemanda.INTERNA:
                statement = statement.where(Demanda.cliente_id.is_(None))
            else:
                statement = statement.where(Demanda.cliente_id.is_not(None))

        if prazo_inicio:
            statement = statement.where(Demanda.prazo_etapa_atual >= prazo_inicio)

        if prazo_fim:
            statement = statement.where(Demanda.prazo_etapa_atual <= prazo_fim)

        if atrasada:
            # D2-B5 (MeuDepartamentoView: período "Atrasadas") — mesma expressão do resumo
            # de Atendimento (D2-B4), agora também filtrável na lista. `status=` continua
            # independente: combinar com um status finalizado devolve vazio por construção
            # (AND), não é "corrigido" aqui — preserva a UI atual.
            finalizada, prazo_vencido = self._finalizada_e_prazo_vencido(agora_utc())
            statement = statement.where(and_(~finalizada, prazo_vencido))

        if nao_finalizada:
            # D2-D1 (NotificationBell): "aberta" para quem é responsável — reaproveita
            # `_STATUS_FINALIZADOS` (mesma constante de `atrasada`/`resumo_*`), nunca um
            # literal `("concluida", "cancelada")` novo. Independente de `status=` (AND puro):
            # `status=concluida&naoFinalizada=true` devolve vazio por construção, não é
            # "corrigido" aqui. Independente também da exclusão de arquivada acima — arquivada
            # já está fora quando `status` não é passado explicitamente; este filtro não a
            # reintroduz nem duplica essa exclusão.
            statement = statement.where(Demanda.status.not_in(self._STATUS_FINALIZADOS))

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
                # D2-B1 (revisão pré-merge): a busca por nome de cliente/projeto/responsável/
                # departamento existia no filtro local antigo de DemandasView.tsx — perdê-la ao
                # mover a busca pro servidor seria regressão real, não simplificação aceitável.
                # `.in_(select(...))` em vez de JOIN: cliente/projeto já são FK 1:1 em Demanda
                # (sem risco de duplicar linha), e responsável/departamento são N:N — um JOIN
                # duplicaria a Demanda por vínculo; a subquery evita isso sem precisar de
                # DISTINCT.
                Demanda.cliente_id.in_(select(Cliente.id).where(Cliente.nome.ilike(like))),
                Demanda.projeto_id.in_(select(Projeto.id).where(Projeto.nome.ilike(like))),
                Demanda.id.in_(
                    select(DemandaResponsavel.demanda_id)
                    .join(Usuario, Usuario.id == DemandaResponsavel.usuario_id)
                    .where(Usuario.nome.ilike(like))
                ),
                Demanda.id.in_(
                    select(DemandaDepartamento.demanda_id)
                    .join(Departamento, Departamento.id == DemandaDepartamento.departamento_id)
                    .where(Departamento.nome.ilike(like))
                ),
            ]
            # Igualdade EXATA, nunca ILIKE: "2063" localiza a demanda #2063, não toda demanda
            # cujo número contenha 2063.
            if termo.numero is not None:
                alternativas.append(Demanda.numero_operacional == termo.numero)
            statement = statement.where(or_(*alternativas))

        if sort == SortDemandas.PRAZO_ASC:
            # Tiebreaker por numero_operacional DESC: sem ele, duas demandas com o mesmo prazo
            # (ou ambas sem prazo) teriam ordem não-determinística entre requests — quebrando
            # paginação por offset (a mesma linha poderia aparecer em duas páginas, ou nenhuma).
            statement = statement.order_by(
                Demanda.prazo_etapa_atual.asc().nulls_last(), Demanda.numero_operacional.desc()
            )
        elif sort == SortDemandas.SINALIZADA_DESC:
            # D2-D2 (Dashboard pessoal): mesmo motivo de desempate do PRAZO_ASC acima.
            statement = statement.order_by(
                Demanda.sinalizada.desc(), Demanda.numero_operacional.desc()
            )
        else:
            statement = statement.order_by(Demanda.numero_operacional.desc())

        statement = statement.limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    # Únicos dois status que `classificarTarefa` (frontend) trata como "finalizada" para
    # fins de atraso — fora daqui, nada mais depende dessa noção. Compartilhado por
    # `list()` (filtro `atrasada=`), `resumo_atendimento` (D2-B4) e `resumo_departamento`
    # (D2-B5) — uma única definição, nunca reimplementada em cada método.
    _STATUS_FINALIZADOS = ("concluida", "cancelada")

    @classmethod
    def _finalizada_e_prazo_vencido(cls, agora: datetime) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
        """`(finalizada, prazo_vencido)` — mesma expressão usada em toda noção de "atrasada"
        neste repository. `prazoValido && prazo < agora` do frontend vira `IS NOT NULL` para
        `prazoValido`."""
        finalizada = Demanda.status.in_(cls._STATUS_FINALIZADOS)
        prazo_vencido = and_(Demanda.prazo_etapa_atual.is_not(None), Demanda.prazo_etapa_atual < agora)
        return finalizada, prazo_vencido

    def resumo_atendimento(self, db: Session, *, escopo: EscopoDemanda) -> dict[str, int]:
        """Indicadores agregados de "Minhas Demandas" (D2-B4) — universo INTEGRAL permitido
        pelo escopo, nunca uma página. Reproduz exatamente as nove fórmulas de
        `MinhasDemandasView.tsx`/`classificarTarefa` (frontend, pré-migração) com CASE/COUNT
        numa única query — nenhuma `DemandaRead` é carregada em Python para contar.

        Mesma exclusão default de arquivada que `list()` aplica sem `status` explícito — o
        resumo nunca teve como incluir arquivadas (o array de origem, pré-migração, também as
        excluía sempre) e isso não muda aqui, mesmo com a correção do dropdown da lista.
        """
        zero = {
            "criadas": 0,
            "nao_iniciadas": 0,
            "em_execucao": 0,
            "aguardando_cliente": 0,
            "aguardando_atendimento": 0,
            "pausadas": 0,
            "atrasadas": 0,
            "dentro_do_prazo": 0,
            "concluidas": 0,
        }
        if escopo.vazio:
            return zero

        agora = agora_utc()
        finalizada, prazo_vencido = self._finalizada_e_prazo_vencido(agora)

        statement = (
            select(
                func.count().label("criadas"),
                func.count(case((Demanda.status.in_(("rascunho", "planejada")), 1))).label(
                    "nao_iniciadas"
                ),
                func.count(case((Demanda.status == "em_execucao", 1))).label("em_execucao"),
                func.count(case((Demanda.status == "aguardando_cliente", 1))).label(
                    "aguardando_cliente"
                ),
                # `aguardandoAtendimento`/`pausadas`: MinhasDemandasView.tsx usa
                # `demanda.status` cru para estes dois indicadores — NÃO o agrupamento
                # `classificacao.pausada` (que junta pausada+bloqueada). Reproduzir a
                # distinção, não a versão "simplificada".
                func.count(case((Demanda.status == "bloqueada", 1))).label(
                    "aguardando_atendimento"
                ),
                func.count(case((Demanda.status == "pausada", 1))).label("pausadas"),
                func.count(case((and_(~finalizada, prazo_vencido), 1))).label("atrasadas"),
                # `dentroDoPrazo` = !atrasada && !finalizada (álgebra: !(!fin && venc) && !fin
                # == !fin && (!venc) — inclui itens sem prazo, igual ao frontend).
                func.count(case((and_(~finalizada, ~prazo_vencido), 1))).label("dentro_do_prazo"),
                func.count(case((Demanda.status == "concluida", 1))).label("concluidas"),
            )
            .select_from(Demanda)
            .where(Demanda.empresa_id == escopo.empresa_id)
        )

        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)
        statement = statement.where(Demanda.status != STATUS_ARQUIVADO)

        resultado = db.execute(statement).one()
        return dict(resultado._mapping)

    def resumo_minha_home(
        self,
        db: Session,
        *,
        escopo: EscopoDemanda,
        usuario_id: str,
        agora: datetime,
        hoje_inicio: datetime,
        hoje_fim: datetime,
        semana_inicio: datetime,
        semana_fim: datetime,
        ontem_inicio: datetime,
        ontem_fim: datetime,
    ) -> dict[str, int]:
        """D2-D2 — os 11 indicadores do Dashboard pessoal (`/meu-dia`), sobre o universo
        INTEGRAL permitido: escopo normal (`_predicado_escopo`, o MESMO de `list()` sem
        override) **AND** responsável N:N == `usuario_id` — nunca `empresa_id` + responsável
        isolados, o que ampliaria acesso para quem tem escopo normal mais restrito que "toda
        demanda onde é responsável". Sem restrição de perfil: qualquer usuário com
        `demandas.visualizar` chega até aqui, igual à listagem.

        Todas as fronteiras temporais vêm do cliente, calculadas a partir de UMA única
        referência (`new Date()` em DashboardView.tsx) — este método não recalcula
        "hoje"/"ontem"/"semana", mesma razão de `prazoInicio`/`prazoFim` em `list()`.
        """
        zero: dict[str, int] = {
            "ativas": 0,
            "novas": 0,
            "andamento": 0,
            "pausadas": 0,
            "aguardando": 0,
            "atrasadas": 0,
            "concluidas": 0,
            "previstas_hoje": 0,
            "previstas_semana": 0,
            "concluidas_semana": 0,
            "concluidas_ontem": 0,
        }
        if escopo.vazio:
            return zero

        finalizada, prazo_vencido = self._finalizada_e_prazo_vencido(agora)
        prazo_valido = Demanda.prazo_etapa_atual.is_not(None)

        statement = (
            select(
                # ativas = !finalizada (concluída/cancelada) — mesma expressão, sem repetir o
                # literal ("concluida", "cancelada") fora de `_STATUS_FINALIZADOS`.
                func.count(case((~finalizada, 1))).label("ativas"),
                func.count(case((Demanda.status.in_(("rascunho", "planejada")), 1))).label("novas"),
                func.count(case((Demanda.status == "em_execucao", 1))).label("andamento"),
                func.count(case((Demanda.status.in_(("pausada", "bloqueada")), 1))).label("pausadas"),
                func.count(case((Demanda.status == "aguardando_cliente", 1))).label("aguardando"),
                func.count(case((and_(~finalizada, prazo_vencido), 1))).label("atrasadas"),
                func.count(case((Demanda.status == "concluida", 1))).label("concluidas"),
                func.count(
                    case(
                        (
                            and_(
                                ~finalizada,
                                prazo_valido,
                                Demanda.prazo_etapa_atual >= hoje_inicio,
                                Demanda.prazo_etapa_atual <= hoje_fim,
                            ),
                            1,
                        )
                    )
                ).label("previstas_hoje"),
                func.count(
                    case(
                        (
                            and_(
                                ~finalizada,
                                prazo_valido,
                                Demanda.prazo_etapa_atual >= semana_inicio,
                                Demanda.prazo_etapa_atual <= semana_fim,
                            ),
                            1,
                        )
                    )
                ).label("previstas_semana"),
                # concluidasSemana: SEM limite superior — mesma fórmula do frontend
                # pré-migração (`updatedAt >= inicioDaSemana(agora)`, sem teto).
                func.count(
                    case((and_(Demanda.status == "concluida", Demanda.updated_at >= semana_inicio), 1))
                ).label("concluidas_semana"),
                func.count(
                    case(
                        (
                            and_(
                                Demanda.status == "concluida",
                                Demanda.updated_at >= ontem_inicio,
                                Demanda.updated_at <= ontem_fim,
                            ),
                            1,
                        )
                    )
                ).label("concluidas_ontem"),
            )
            .select_from(Demanda)
            .where(Demanda.empresa_id == escopo.empresa_id)
        )

        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            statement = statement.where(predicado)
        statement = statement.where(Demanda.status != STATUS_ARQUIVADO)
        statement = statement.where(
            Demanda.id.in_(
                select(DemandaResponsavel.demanda_id).where(DemandaResponsavel.usuario_id == usuario_id)
            )
        )

        resultado = db.execute(statement).one()
        return dict(resultado._mapping)

    def resumo_departamento(
        self, db: Session, *, escopo: EscopoDemanda, departamento_id: str, horas_uteis_hoje: float
    ) -> dict[str, float | int]:
        """Indicadores agregados de MeuDepartamentoView (D2-B5) — universo INTEGRAL do
        departamento dentro do escopo permitido, nunca a página filtrada da lista (os
        filtros dos 8 selects não afetam o resumo, mesma semântica de
        `classificacoesDept`/`tarefasDoDept` no frontend pré-migração).

        `horas_uteis_hoje` vem de `RegraExpedienteService.to_estado_read` — a MESMA fonte já
        usada por `GET /expediente/estado` (nenhum cálculo de horário duplicado aqui);
        `horasConsumidas` continua vindo só de `GET /sessoes-trabalho/horas`, este resumo não
        a recalcula.
        """
        zero: dict[str, float | int] = {
            "novas": 0,
            "sem_responsavel": 0,
            "em_andamento": 0,
            "pausadas": 0,
            "aguardando": 0,
            "atrasadas": 0,
            "concluidas": 0,
            "horas_estimadas_total": 0.0,
            "colaboradores_sobrecarregados": 0,
        }
        if escopo.vazio:
            return zero

        agora = agora_utc()
        finalizada, prazo_vencido = self._finalizada_e_prazo_vencido(agora)

        # Universo: empresa + escopo RBAC (Head) + departamento funcional (singular, o
        # departamentoHead.id resolvido no frontend) + exclusão de arquivada — mesma regra
        # de `list()` sem status explícito. Reaproveitado como subquery de ids pelas duas
        # agregações seguintes (contadores e horas), nunca materializado em Python.
        universo_ids = select(Demanda.id).where(Demanda.empresa_id == escopo.empresa_id)
        predicado = self._predicado_escopo(escopo)
        if predicado is not None:
            universo_ids = universo_ids.where(predicado)
        universo_ids = universo_ids.where(
            Demanda.id.in_(
                select(DemandaDepartamento.demanda_id).where(
                    DemandaDepartamento.departamento_id == departamento_id
                )
            )
        )
        universo_ids = universo_ids.where(Demanda.status != STATUS_ARQUIVADO)

        contadores_statement = (
            select(
                func.count(case((Demanda.status.in_(("rascunho", "planejada")), 1))).label("novas"),
                # semResponsavel: nenhuma linha em DemandaResponsavel para esta demanda.
                func.count(
                    case((~Demanda.id.in_(select(DemandaResponsavel.demanda_id)), 1))
                ).label("sem_responsavel"),
                func.count(case((Demanda.status == "em_execucao", 1))).label("em_andamento"),
                # `pausadas` aqui é o agrupamento (pausada OU bloqueada) — `classificacao.
                # pausada` do frontend, DIFERENTE do resumo de Atendimento (D2-B4), que usa
                # os dois status crus separadamente. Telas diferentes, semânticas diferentes;
                # não uniformizar.
                func.count(case((Demanda.status.in_(("pausada", "bloqueada")), 1))).label("pausadas"),
                func.count(case((Demanda.status == "aguardando_cliente", 1))).label("aguardando"),
                func.count(case((and_(~finalizada, prazo_vencido), 1))).label("atrasadas"),
                func.count(case((Demanda.status == "concluida", 1))).label("concluidas"),
            )
            .select_from(Demanda)
            .where(Demanda.id.in_(universo_ids))
        )
        contadores = db.execute(contadores_statement).one()

        # horasEstimadasDemanda soma TODAS as etapas de workflow da demanda, convertendo
        # unidade≠"horas" (dias_corridos/dias_uteis) para horas ×24 — mesma aproximação de
        # `converterQuantidadeEmHoras` (lib/workflow-modelo.ts). Sem filtro de status: uma
        # demanda concluída/cancelada CONTINUA contribuindo para o total (fiel ao frontend,
        # que soma sobre `tarefasDoDept` inteiro, não sobre um subconjunto ativo).
        horas_por_etapa = case(
            (DemandaWorkflowEtapa.unidade_prazo == "horas", DemandaWorkflowEtapa.quantidade_antes_deadline),
            else_=DemandaWorkflowEtapa.quantidade_antes_deadline * 24,
        )

        horas_totais_statement = (
            select(func.coalesce(func.sum(horas_por_etapa), 0))
            .select_from(DemandaWorkflowEtapa)
            .where(DemandaWorkflowEtapa.demanda_id.in_(universo_ids))
        )
        horas_estimadas_total = db.execute(horas_totais_statement).scalar_one()

        # Sobrecarga: por colaborador ELEGÍVEL (membro ativo do departamento — mesmo filtro
        # de `colaboradoresOptions` no frontend), soma INTEGRAL (não dividida) das horas
        # estimadas de toda demanda do universo onde ele é responsável — uma demanda com
        # vários responsáveis conta inteira para CADA um, mesma regra do frontend (nenhuma
        # divisão por número de responsáveis). Capacidade individual =
        # `horas_uteis_hoje × DIAS_UTEIS_SEMANA` (mesma fórmula de `capacidadeAproximada`
        # com 1 pessoa) — nunca negativa nesta rota, então `> capacidade` já cobre o caso
        # `capacidade == 0` sem precisar do ramo especial `> 0` de `detectarSobrecargaEstimada`.
        horas_por_demanda = (
            select(
                DemandaWorkflowEtapa.demanda_id.label("demanda_id"),
                func.sum(horas_por_etapa).label("horas"),
            )
            .where(DemandaWorkflowEtapa.demanda_id.in_(universo_ids))
            .group_by(DemandaWorkflowEtapa.demanda_id)
            .subquery()
        )
        colaboradores_elegiveis = select(Usuario.id).where(
            Usuario.departamento_id == departamento_id, Usuario.status == "ativo"
        )
        horas_por_colaborador = (
            select(
                DemandaResponsavel.usuario_id.label("usuario_id"),
                func.coalesce(func.sum(horas_por_demanda.c.horas), 0).label("horas"),
            )
            .select_from(DemandaResponsavel)
            .outerjoin(horas_por_demanda, horas_por_demanda.c.demanda_id == DemandaResponsavel.demanda_id)
            .where(
                DemandaResponsavel.demanda_id.in_(universo_ids),
                DemandaResponsavel.usuario_id.in_(colaboradores_elegiveis),
            )
            .group_by(DemandaResponsavel.usuario_id)
            .subquery()
        )
        capacidade_individual = horas_uteis_hoje * DIAS_UTEIS_SEMANA
        sobrecarregados_statement = select(func.count()).select_from(
            select(horas_por_colaborador.c.usuario_id)
            .where(horas_por_colaborador.c.horas > capacidade_individual)
            .subquery()
        )
        colaboradores_sobrecarregados = db.execute(sobrecarregados_statement).scalar_one()

        return {
            "novas": contadores.novas,
            "sem_responsavel": contadores.sem_responsavel,
            "em_andamento": contadores.em_andamento,
            "pausadas": contadores.pausadas,
            "aguardando": contadores.aguardando,
            "atrasadas": contadores.atrasadas,
            "concluidas": contadores.concluidas,
            "horas_estimadas_total": float(horas_estimadas_total),
            "colaboradores_sobrecarregados": colaboradores_sobrecarregados,
        }

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
