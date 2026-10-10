"""Central de Notificações.

PRINCÍPIO: não existe uma segunda tabela de notificações. Uma notificação é uma VISÃO TIPADA dos eventos de
domínio já gravados (`eventos`) que dizem respeito às demandas de que o usuário é responsável. O único dado
novo é o estado "lida" por usuário (`notificacao_leituras`) — sem linha = não lida. Nada aqui duplica evento.

Categorias (derivadas do evento, nunca de texto):
  - minhas  : atividade de OUTRA pessoa nas demandas em que sou responsável (atribuição a mim, mudança de
              status, bloqueio, ajuste/refação, anexo, arquivamento) — nunca a minha própria ação;
  - sistema : o mesmo catálogo, mas gerado sem ator humano (`eventos.usuario_id` nulo — automação) OU por uma
              conta de sistema (`usuarios.is_system_account`): para o tenant, a conta de sistema é "Sistema", nunca
              uma pessoa — a notificação continua existindo, mas sem nome/identidade da conta (Fase 1A).

"Prazos da equipe" NÃO é persistido: é derivado de Demandas, no MESMO escopo de `GET /demandas`
(`core/escopo.py`), em `DemandaRepository.contar_prazos` / `list`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import DateTime, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from app.core.relogio import agora_local, agora_utc
from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.evento import Evento
from app.models.notificacao_leitura import NotificacaoLeitura
from app.models.usuario import Usuario
from app.schemas.notificacao import (
    NaoLidasRead,
    NotificacaoRead,
    NotificacoesPaginaRead,
    NotificacoesResumoRead,
    PrazosResumoRead,
)

AUTOR_SISTEMA = "Sistema"  # autor exibido quando o ator é conta de sistema (nunca o nome real)

JANELA_DIAS = 30  # histórico exibido: últimos 30 dias (a central não é um arquivo morto)

TIPO_ATRIBUICAO = "demanda.responsavel_adicionado"
# Fase 8C: avisa quem precisa agir na etapa que acabou de virar a atual. Os destinatários vêm EXPLÍCITOS no payload (`destinatarioUsuarioIds`,
# calculados na progressão — `core/workflow_destinatarios.py`): quem é responsável pela ETAPA nem sempre é responsável pela DEMANDA.
TIPO_ETAPA_ATUALIZADA = "demanda.workflow_etapa_atualizada"

# tipo do evento → título. Só entra na central o que está aqui; evento novo não "vaza" sozinho.
TITULOS: dict[str, str] = {
    TIPO_ATRIBUICAO: "Você foi atribuído a uma tarefa",
    "demanda.status_alterado": "Status da tarefa alterado",
    "demanda.bloqueada": "Tarefa bloqueada",
    "demanda.desbloqueada": "Tarefa desbloqueada",
    "demanda.ajuste_interno_registrado": "Ajuste interno registrado",
    "demanda.ajuste_cliente_registrado": "Ajuste do cliente registrado",
    "demanda.refacao_registrada": "Refação registrada",
    "demanda.arquivo_enviado": "Novo arquivo na tarefa",
    "demanda.arquivada": "Tarefa arquivada",
    "demanda.restaurada": "Tarefa restaurada",
    TIPO_ETAPA_ATUALIZADA: "Nova etapa de Workflow disponível",  # título por tipo de etapa: ver `_titulo`
    # Fase 9B — decisão do cliente no Portal de Aprovação (autor = nome declarado do cliente; o motivo dos ajustes fica no histórico)
    "demanda.aprovacao_externa_aprovada": "Cliente aprovou a etapa de aprovação",
    "demanda.aprovacao_externa_ajustes": "Cliente solicitou ajustes",
}

TIPOS_APROVACAO_EXTERNA = ("demanda.aprovacao_externa_aprovada", "demanda.aprovacao_externa_ajustes")

TITULO_ETAPA_APROVACAO = "Uma etapa de aprovação está aguardando você"
TITULO_ETAPA_DEVOLVIDA = "Etapa devolvida para ajustes"  # Fase 8D: a aprovação rejeitada reabriu a etapa anterior (o motivo fica no histórico)


def _titulo(tipo: str, payload: dict | None) -> str:
    if tipo == TIPO_ETAPA_ATUALIZADA and (payload or {}).get("devolvida") is True:
        return TITULO_ETAPA_DEVOLVIDA
    if tipo == TIPO_ETAPA_ATUALIZADA and (payload or {}).get("etapaTipo") == "aprovacao":
        return TITULO_ETAPA_APROVACAO
    return TITULOS[tipo]


# mesmos rótulos de `statusDemandaLabels` (frontend/src/lib/demandas.ts)
_ROTULOS_STATUS = {
    "rascunho": "Rascunho",
    "planejada": "Planejada",
    "em_execucao": "Em execução",
    "pausada": "Pausada",
    "bloqueada": "Bloqueada",
    "aguardando_cliente": "Aguardando cliente",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
    "arquivada": "Arquivada",
}


def _rotulo_status(valor: object) -> str:
    if not valor:
        return ""
    return _ROTULOS_STATUS.get(str(valor), str(valor).replace("_", " ").capitalize())


def _detalhe(tipo: str, payload: dict | None) -> str | None:
    dados = payload or {}
    if tipo == "demanda.status_alterado":
        de, para = _rotulo_status(dados.get("de")), _rotulo_status(dados.get("para"))
        return f"{de} → {para}" if de and para else (para or None)
    if tipo == "demanda.bloqueada":
        return dados.get("motivoBloqueio") or None
    if tipo == "demanda.arquivo_enviado":
        return dados.get("nomeOriginal") or None
    if tipo == TIPO_ETAPA_ATUALIZADA or tipo in TIPOS_APROVACAO_EXTERNA:
        nome = dados.get("etapaNome")
        return f"Etapa {dados.get('etapaOrdem')}: {nome}" if nome and dados.get("etapaOrdem") else (nome or None)
    return None


def janelas_prazo() -> tuple[datetime, datetime, datetime]:
    """(agora, fim do dia, fim do 7º dia) no fuso da aplicação, devolvidos em UTC — mesmo padrão
    temporal já adotado (`core/relogio.py`)."""
    agora = agora_utc()
    local = agora_local()
    fim_hoje_local = local.replace(hour=23, minute=59, second=59, microsecond=999999)
    return agora, fim_hoje_local.astimezone(agora.tzinfo), (fim_hoje_local + timedelta(days=7)).astimezone(agora.tzinfo)


class NotificacaoNaoEncontradaError(LookupError):
    """Evento inexistente ou que não é uma notificação DESTE usuário (outro usuário/empresa) — vira 404."""


class NotificacaoService:
    # ----------------------------------------------------------------------------------
    # Predicado único: o que é uma notificação deste usuário
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _predicado(usuario: Usuario) -> list:
        desde = agora_utc() - timedelta(days=JANELA_DIAS)
        # (a) eventos das demandas em que eu sou RESPONSÁVEL (regra de sempre)
        das_minhas_demandas = and_(
            Evento.tipo.in_([t for t in TITULOS if t != TIPO_ETAPA_ATUALIZADA]),
            # só das demandas em que eu sou responsável (hoje)
            Evento.entidade_id.in_(select(DemandaResponsavel.demanda_id).where(DemandaResponsavel.usuario_id == usuario.id)),
            # nunca a minha própria ação
            or_(Evento.usuario_id.is_(None), Evento.usuario_id != usuario.id),
            # atribuição só é notificação para QUEM foi atribuído
            or_(Evento.tipo != TIPO_ATRIBUICAO, Evento.payload["usuarioId"].as_string() == usuario.id),
        )
        # (b) Fase 8C: a etapa que acabou de virar a atual é minha (destinatário EXPLÍCITO). Vale mesmo sem eu ser responsável pela demanda e
        # mesmo que eu tenha sido quem concluiu a etapa anterior (sem exceção especial); a notificação não concede visibilidade da demanda.
        etapa_para_mim = and_(
            Evento.tipo == TIPO_ETAPA_ATUALIZADA,
            cast(Evento.payload, JSONB).contains({"destinatarioUsuarioIds": [usuario.id]}),
        )
        return [
            Evento.empresa_id == usuario.empresa_id,
            Evento.entidade_tipo == "demanda",
            Evento.occurred_at >= desde,
            or_(das_minhas_demandas, etapa_para_mim),
        ]

    @staticmethod
    def _ator_e_conta_de_sistema():
        """O ator do evento é uma conta `is_system_account`. ÚNICO ponto que decide isso nas notificações — vale
        para a categoria, para a contagem e para o autor exibido. Alias: o JOIN da listagem já usa `Usuario`."""
        ator = aliased(Usuario)
        return exists(
            select(1).select_from(ator).where(ator.id == Evento.usuario_id, ator.is_system_account.is_(True)).correlate(Evento)
        )

    @staticmethod
    def _nome_ator_externo():
        """Fase 9B: nome declarado do cliente que decidiu pelo Portal de Aprovação (`payload.atorExterno.nome`), ou NULL se o evento não é externo."""
        return Evento.payload["atorExterno"]["nome"].as_string()

    @classmethod
    def _eh_sistema(cls):
        """Sem ator humano: automação (`usuario_id` nulo SEM ator externo) ou conta de sistema. Quem decidiu pelo Portal de Aprovação é uma pessoa
        (externa): `usuario_id` nulo, mas nunca "Sistema"."""
        return or_(
            and_(Evento.usuario_id.is_(None), cls._nome_ator_externo().is_(None)),
            cls._ator_e_conta_de_sistema(),
        )

    @classmethod
    def _filtro_categoria(cls, categoria: str | None) -> list:
        if categoria == "sistema":
            return [cls._eh_sistema()]
        if categoria == "minhas":
            return [~cls._eh_sistema()]
        return []

    @staticmethod
    def _nao_lida(usuario: Usuario):
        lida = aliased(NotificacaoLeitura)  # alias: não colide com o OUTER JOIN da listagem
        return ~exists(select(1).select_from(lida).where(lida.usuario_id == usuario.id, lida.evento_id == Evento.id)).correlate(Evento)

    # ----------------------------------------------------------------------------------
    # Leitura
    # ----------------------------------------------------------------------------------

    def listar(
        self,
        db: Session,
        usuario: Usuario,
        *,
        categoria: str | None,
        apenas_nao_lidas: bool,
        limit: int,
        offset: int,
    ) -> NotificacoesPaginaRead:
        condicoes = [*self._predicado(usuario), *self._filtro_categoria(categoria)]
        if apenas_nao_lidas:
            condicoes.append(self._nao_lida(usuario))

        total = db.scalar(select(func.count()).select_from(Evento).where(*condicoes)) or 0
        eh_sistema = self._eh_sistema()
        # O nome real só sai do banco quando o ator é uma pessoa: para conta de sistema o CASE já devolve "Sistema".
        autor = case(
            (self._ator_e_conta_de_sistema(), literal(AUTOR_SISTEMA)),
            (self._nome_ator_externo().is_not(None), self._nome_ator_externo()),
            else_=Usuario.nome,
        )
        linhas = db.execute(
            select(Evento, Demanda.codigo_referencia, Demanda.nome, autor, NotificacaoLeitura.lida_em, eh_sistema, Demanda.identificador)
            .select_from(Evento)
            .join(Demanda, and_(Demanda.id == Evento.entidade_id, Demanda.empresa_id == usuario.empresa_id))
            .outerjoin(Usuario, Usuario.id == Evento.usuario_id)
            .outerjoin(
                NotificacaoLeitura,
                and_(NotificacaoLeitura.evento_id == Evento.id, NotificacaoLeitura.usuario_id == usuario.id),
            )
            .where(*condicoes)
            .order_by(Evento.occurred_at.desc(), Evento.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()  # UMA consulta para a página inteira (sem N+1)
        itens = [
            NotificacaoRead(
                id=evento.id,
                categoria="sistema" if sistema else "minhas",
                tipo=evento.tipo,
                titulo=_titulo(evento.tipo, evento.payload),
                detalhe=_detalhe(evento.tipo, evento.payload),
                ocorridaEm=evento.occurred_at,
                lida=lida_em is not None,
                demandaId=evento.entidade_id,
                demandaReferencia=referencia,
                demandaIdentificador=identificador,
                demandaNome=nome_demanda,
                autorNome=autor,
            )
            for evento, referencia, nome_demanda, autor, lida_em, sistema, identificador in linhas
        ]
        return NotificacoesPaginaRead(itens=itens, total=total, limit=limit, offset=offset)

    def nao_lidas(self, db: Session, usuario: Usuario) -> NaoLidasRead:
        sistema, minhas = db.execute(
            select(
                func.count(case((self._eh_sistema(), 1))),
                func.count(case((~self._eh_sistema(), 1))),
            )
            .select_from(Evento)
            .where(*self._predicado(usuario), self._nao_lida(usuario))
        ).one()
        return NaoLidasRead(sistema=int(sistema), minhas=int(minhas), total=int(sistema) + int(minhas))

    def resumo(self, db: Session, usuario: Usuario, *, prazos: dict[str, int]) -> NotificacoesResumoRead:
        return NotificacoesResumoRead(naoLidas=self.nao_lidas(db, usuario), prazos=PrazosResumoRead(**prazos))

    # ----------------------------------------------------------------------------------
    # Escrita (só o estado "lida" DO PRÓPRIO usuário)
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _linha_leitura(usuario: Usuario, agora: datetime) -> dict:
        return {
            "usuario_id": usuario.id,
            "empresa_id": usuario.empresa_id,
            "lida_em": agora,
            "created_at": agora,
            "updated_at": agora,
        }

    def marcar_lida(self, db: Session, usuario: Usuario, evento_id: str) -> None:
        visivel = db.scalar(select(Evento.id).where(*self._predicado(usuario), Evento.id == evento_id))
        if visivel is None:
            raise NotificacaoNaoEncontradaError("Notificação não encontrada.")
        agora = agora_utc()
        db.execute(
            pg_insert(NotificacaoLeitura)
            .values(evento_id=evento_id, **self._linha_leitura(usuario, agora))
            .on_conflict_do_nothing(index_elements=["usuario_id", "evento_id"])  # idempotente
        )
        db.commit()

    def marcar_todas_lidas(self, db: Session, usuario: Usuario, *, categoria: str | None) -> None:
        agora = agora_utc()
        origem = select(
            literal(usuario.id).label("usuario_id"),
            Evento.id.label("evento_id"),
            literal(usuario.empresa_id).label("empresa_id"),
            literal(agora, DateTime(timezone=True)).label("lida_em"),
            literal(agora, DateTime(timezone=True)).label("created_at"),
            literal(agora, DateTime(timezone=True)).label("updated_at"),
        ).where(*self._predicado(usuario), *self._filtro_categoria(categoria), self._nao_lida(usuario))
        db.execute(
            pg_insert(NotificacaoLeitura)
            .from_select(["usuario_id", "evento_id", "empresa_id", "lida_em", "created_at", "updated_at"], origem)
            .on_conflict_do_nothing(index_elements=["usuario_id", "evento_id"])
        )  # um único INSERT … SELECT, não um laço
        db.commit()
