from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.escopo import EscopoHorasNaoAutorizadoError, pode_consultar_horas_departamento
from app.schemas.evento import EventoCreate
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.sessao_trabalho_repository import FiltrosSessaoAvancados, SessaoTrabalhoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.evento_service import EventoService

# Mesmo conjunto usado em Projeto/Demanda: um usuário nestes estados não pode ser DEFINIDO
# como responsável novo de uma sessão. Vínculo histórico (sessão já existente) não é afetado.
STATUS_USUARIO_INVALIDO = {"arquivado", "inativo", "bloqueado"}
STATUS_DEPARTAMENTO_INVALIDO = {"arquivado"}

STATUS_ATIVA = "ativa"
STATUS_ENCERRADA = "encerrada"
STATUS_CANCELADA = "cancelada"
STATUSES_SESSAO = frozenset({STATUS_ATIVA, STATUS_ENCERRADA, STATUS_CANCELADA})

MOTIVO_PAUSA = "pausa"
MOTIVO_BLOQUEIO = "bloqueio"
MOTIVO_AGUARDANDO_CLIENTE = "aguardando_cliente"
MOTIVO_MUDANCA_ETAPA = "mudanca_etapa"
MOTIVO_CONCLUSAO = "conclusao"
MOTIVO_CANCELAMENTO = "cancelamento"
MOTIVO_TROCA_RESPONSAVEL = "troca_responsavel"
MOTIVO_SUBSTITUICAO_SESSAO_ATIVA = "substituicao_sessao_ativa"
MOTIVO_ARQUIVAMENTO = "arquivamento"
MOTIVOS_ENCERRAMENTO = frozenset(
    {
        MOTIVO_PAUSA,
        MOTIVO_BLOQUEIO,
        MOTIVO_AGUARDANDO_CLIENTE,
        MOTIVO_MUDANCA_ETAPA,
        MOTIVO_CONCLUSAO,
        MOTIVO_CANCELAMENTO,
        MOTIVO_TROCA_RESPONSAVEL,
        MOTIVO_SUBSTITUICAO_SESSAO_ATIVA,
        MOTIVO_ARQUIVAMENTO,
    }
)

# Fase 11B.2A — sessão de trabalho representa EXECUÇÃO ATIVA: só se abre com a Demanda em `em_execucao`. Qualquer outro status do CHECK real
# (rascunho, planejada, pausada, bloqueada, aguardando_cliente, concluida, cancelada, arquivada) não é executável — e nenhuma sessão ativa sobrevive a ele.
STATUS_DEMANDA_EXECUTAVEL = frozenset({"em_execucao"})
# Transição de status da Demanda -> motivo do encerramento automático (as sessões ativas acabam antes de o tempo "improdutivo" correr).
MOTIVO_POR_STATUS_DEMANDA = {
    "pausada": MOTIVO_PAUSA,
    "bloqueada": MOTIVO_BLOQUEIO,
    "aguardando_cliente": MOTIVO_AGUARDANDO_CLIENTE,
    "concluida": MOTIVO_CONCLUSAO,
    "cancelada": MOTIVO_CANCELAMENTO,
    "arquivada": MOTIVO_ARQUIVAMENTO,
    # voltar a rascunho/planejada interrompe o trabalho como uma pausa
    "rascunho": MOTIVO_PAUSA,
    "planejada": MOTIVO_PAUSA,
}

CODIGO_SESSAO_ATIVA_EXISTENTE = "SESSAO_ATIVA_EXISTENTE"
CODIGO_DEMANDA_NAO_EXECUTAVEL = "DEMANDA_NAO_EXECUTAVEL"
CODIGO_ETAPA_ATUAL_INDISPONIVEL = "ETAPA_ATUAL_INDISPONIVEL"
CODIGO_ETAPA_NAO_ATUAL = "ETAPA_NAO_ATUAL"
STATUS_ETAPA_PAUSADA = "pausada"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SessaoTrabalhoUsuarioInvalidoError(ValueError):
    """usuarioId inexistente, de outra empresa ou em status inválido para vínculo novo."""


class SessaoTrabalhoDepartamentoInvalidoError(ValueError):
    """departamentoId inexistente, de outra empresa ou arquivado (vínculo novo)."""


class SessaoTrabalhoDepartamentoNaoEncontradoError(ValueError):
    """departamentoId inexistente ou de outra empresa, na CONSULTA do agregado de horas — 404,
    nunca 403 (existência cross-tenant não se confirma). Distinta da 422 de
    SessaoTrabalhoDepartamentoInvalidoError, que é sobre abrir sessão nova, não consultar."""


class SessaoTrabalhoDemandaNaoEncontradaError(LookupError):
    """demandaId inexistente OU de outra empresa — 404 nos dois casos (existência cross-tenant não se confirma)."""


class SessaoTrabalhoEtapaInvalidaError(ValueError):
    """workflowEtapaId inexistente, de outra demanda ou de outra empresa (422, mensagem única: não revela qual)."""


class SessaoTrabalhoConflitoError(RuntimeError):
    """Conflito de domínio previsível (409): `codigo` estável para a UI, `str(exc)` legível."""

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class SessaoTrabalhoService:
    def __init__(
        self,
        repository: SessaoTrabalhoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
        evento_service: EventoService | None = None,
    ) -> None:
        self.evento_service = evento_service or EventoService()
        self.repository = repository or SessaoTrabalhoRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()

    def abrir(
        self,
        db: Session,
        *,
        empresa_id: str,
        demanda_id: str,
        evento_inicio_id: str,
        inicio_em: datetime,
        agencia_id: str | None = None,
        workflow_etapa_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
    ) -> SessaoTrabalho:
        """Abertura PELO SERVIDOR (Fase 11B.2A): nada que o cliente mandou é confiável. Valida, nesta ordem: responsável (usuário OU departamento) →
        demanda (existe, é desta empresa, está em execução) → etapa → depois `open_session` (usuário/departamento da empresa, uma sessão ativa por pessoa).

        ## Etapa (decisão de produto)
        Demanda COM workflow: a sessão fica SEMPRE ligada à ETAPA ATUAL, resolvida aqui pela semântica oficial (menor `ordem` não concluída). O cliente pode omitir
        `workflowEtapaId` (o servidor usa a atual) ou enviá-lo — e então ele precisa SER a atual: etapa inexistente/de outra demanda/de outra empresa = 422 (uma
        mensagem só); etapa da demanda que já passou ou ainda não chegou = 409 `ETAPA_NAO_ATUAL`. Sem etapa atual inequívoca para executar (workflow concluído, etapa
        atual pausada, workflow sem etapas materializadas) = 409 `ETAPA_ATUAL_INDISPONIVEL` — nunca uma sessão sem etapa, nunca "primeira/última/por responsável".
        Demanda SEM workflow: `workflow_etapa_id` fica NULL (nada é fabricado). A Demanda é travada (`FOR UPDATE`) durante a resolução, serializando com o avanço
        de etapa e com a mudança de status."""
        self._validate_responsavel(usuario_id=usuario_id, departamento_id=departamento_id, allow_usuario_and_departamento=False)
        demanda = self._ensure_demanda_executavel(db, empresa_id, demanda_id)
        workflow_etapa_id = self._resolver_etapa_da_sessao(db, demanda, workflow_etapa_id)
        return self.open_session(
            db,
            empresa_id=empresa_id,
            demanda_id=demanda.id,
            evento_inicio_id=evento_inicio_id,
            inicio_em=inicio_em,
            agencia_id=agencia_id,
            workflow_etapa_id=workflow_etapa_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
        )

    def _ensure_demanda_executavel(self, db: Session, empresa_id: str, demanda_id: str):
        demanda = self.repository.get_demanda_travada(db, demanda_id)
        if demanda is None or demanda.empresa_id != empresa_id:
            raise SessaoTrabalhoDemandaNaoEncontradaError("Demanda não encontrada")
        if demanda.status not in STATUS_DEMANDA_EXECUTAVEL:
            raise SessaoTrabalhoConflitoError(
                CODIGO_DEMANDA_NAO_EXECUTAVEL,
                f"A demanda está '{demanda.status}': só é possível iniciar uma sessão de trabalho em demanda em execução",
            )
        return demanda

    def _resolver_etapa_da_sessao(self, db: Session, demanda, workflow_etapa_id: str | None) -> str | None:
        """A etapa a gravar na sessão (ver `abrir`): NULL só em demanda sem workflow; senão, a etapa ATUAL resolvida no servidor."""
        if workflow_etapa_id:
            etapa = self.repository.get_etapa(db, workflow_etapa_id)
            # a etapa pertence a UMA demanda (FK) e a demanda já foi validada na empresa: comparar com a demanda cobre etapa inexistente, de outra demanda
            # e de outra empresa, com a mesma mensagem (nunca confirma que existe em outro tenant).
            if etapa is None or etapa.demanda_id != demanda.id:
                raise SessaoTrabalhoEtapaInvalidaError("Etapa não encontrada nesta demanda")
        atual = self.repository.get_etapa_atual(db, demanda.id)
        tem_workflow = (
            atual is not None or demanda.workflow_modelo_id is not None or self.repository.demanda_tem_etapas(db, demanda.id)
        )
        if not tem_workflow:
            return None  # sem workflow: NULL é o valor correto (e uma etapa enviada já foi recusada acima)
        if atual is None or atual.status == STATUS_ETAPA_PAUSADA:
            raise SessaoTrabalhoConflitoError(
                CODIGO_ETAPA_ATUAL_INDISPONIVEL, "Esta demanda não tem uma etapa atual disponível para execução"
            )
        if workflow_etapa_id and workflow_etapa_id != atual.id:
            raise SessaoTrabalhoConflitoError(
                CODIGO_ETAPA_NAO_ATUAL, "A sessão só pode ser iniciada na etapa atual do workflow"
            )
        return atual.id

    def open_session(
        self,
        db: Session,
        *,
        empresa_id: str,
        demanda_id: str,
        evento_inicio_id: str,
        inicio_em: datetime,
        agencia_id: str | None = None,
        workflow_etapa_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        allow_usuario_and_departamento: bool = False,
    ) -> SessaoTrabalho:
        self._validate_responsavel(
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            allow_usuario_and_departamento=allow_usuario_and_departamento,
        )
        # `usuarioId`/`departamentoId` do payload são UUID real — validados aqui, não
        # normalizados. Ver docstring do modelo: nenhuma ponte tipo "user-1 -> usuario-1"
        # entra em código de aplicação nenhum.
        if usuario_id:
            self._ensure_usuario_valido(db, empresa_id, usuario_id)
        if departamento_id:
            self._ensure_departamento_valido(db, empresa_id, departamento_id)

        existing = self.repository.get_by_evento_inicio_id(db, evento_inicio_id)
        if existing:
            return existing

        inicio_em = ensure_utc(inicio_em)

        # Fase 11B.2A — UMA sessão ativa por pessoa, em qualquer demanda. Segunda abertura = 409 SESSAO_ATIVA_EXISTENTE; a anterior NUNCA é encerrada em
        # silêncio (antes, abrir de novo na MESMA demanda substituía a sessão). Só vale para sessão de PESSOA: a puramente departamental (sem usuário) mantém
        # a semântica anterior (reabrir o mesmo departamento na mesma demanda substitui) e nunca é multiplicada pelos membros.
        if usuario_id:
            self._ensure_sem_sessao_ativa(db, empresa_id, usuario_id)

        # Corrida (duas aberturas concorrentes): o índice parcial único (empresa_id, usuario_id) WHERE status='ativa' (e os de demanda) é a barreira real; o par
        # SELECT + INSERT não é atômico. A tentativa roda num SAVEPOINT (nunca um rollback da Session inteira: a rota já adicionou o Evento da abertura, não
        # commitado). Sessão de pessoa que perde a corrida vira o MESMO 409 de uma segunda abertura sequencial; a departamental converge pela substituição.
        for tentativa in (1, 2):
            try:
                with db.begin_nested():
                    if not usuario_id:
                        active = self.repository.get_active_equivalent(
                            db,
                            demanda_id=demanda_id,
                            usuario_id=None,
                            departamento_id=departamento_id,
                        )
                        if active:
                            self.close_session(
                                db,
                                active,
                                evento_fim_id=evento_inicio_id,
                                fim_em=inicio_em,
                                motivo_encerramento=MOTIVO_SUBSTITUICAO_SESSAO_ATIVA,
                            )

                    now = utc_now()
                    sessao = SessaoTrabalho(
                        id=str(uuid4()),
                        empresa_id=empresa_id,
                        agencia_id=agencia_id,
                        demanda_id=demanda_id,
                        workflow_etapa_id=workflow_etapa_id,
                        usuario_id=usuario_id,
                        departamento_id=departamento_id,
                        evento_inicio_id=evento_inicio_id,
                        evento_fim_id=None,
                        status=STATUS_ATIVA,
                        inicio_em=inicio_em,
                        fim_em=None,
                        duracao_segundos=None,
                        motivo_encerramento=None,
                        created_at=now,
                        updated_at=now,
                    )
                    self.repository.create(db, sessao)
                return sessao
            except IntegrityError:
                if usuario_id:
                    ja = self.repository.get_by_evento_inicio_id(db, evento_inicio_id)
                    if ja:
                        return ja
                    self._ensure_sem_sessao_ativa(db, empresa_id, usuario_id)
                if tentativa == 2:
                    raise
        raise AssertionError("inalcançável — o loop sempre retorna ou levanta antes daqui")

    def _ensure_sem_sessao_ativa(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        if self.repository.get_active_by_usuario(db, empresa_id=empresa_id, usuario_id=usuario_id) is not None:
            raise SessaoTrabalhoConflitoError(CODIGO_SESSAO_ATIVA_EXISTENTE, "Você já possui uma atividade em execução.")

    def _ensure_usuario_valido(self, db: Session, empresa_id: str, usuario_id: str) -> None:
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        if usuario is None or usuario.empresa_id != empresa_id:
            raise SessaoTrabalhoUsuarioInvalidoError("Usuário não encontrado nesta empresa")
        if usuario.status in STATUS_USUARIO_INVALIDO:
            raise SessaoTrabalhoUsuarioInvalidoError(
                f"Usuário com status '{usuario.status}' não pode iniciar sessão de trabalho"
            )

    def _ensure_departamento_valido(self, db: Session, empresa_id: str, departamento_id: str) -> None:
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise SessaoTrabalhoDepartamentoInvalidoError("Departamento não encontrado nesta empresa")
        if departamento.status in STATUS_DEPARTAMENTO_INVALIDO:
            raise SessaoTrabalhoDepartamentoInvalidoError(
                "Departamento arquivado não aceita novas sessões de trabalho"
            )

    def close_session(
        self,
        db: Session,
        sessao: SessaoTrabalho,
        *,
        evento_fim_id: str,
        fim_em: datetime,
        motivo_encerramento: str,
    ) -> SessaoTrabalho:
        self._validate_motivo(motivo_encerramento)
        already_closed_by_event = self.repository.get_by_evento_fim_id(db, evento_fim_id)
        if already_closed_by_event:
            return already_closed_by_event
        if sessao.status != STATUS_ATIVA:
            return sessao

        fim_em = ensure_utc(fim_em)
        inicio_em = ensure_utc(sessao.inicio_em)
        duracao = max(0, int((fim_em - inicio_em).total_seconds()))
        sessao.status = STATUS_ENCERRADA
        sessao.fim_em = fim_em
        sessao.evento_fim_id = evento_fim_id
        sessao.duracao_segundos = duracao
        sessao.motivo_encerramento = motivo_encerramento
        sessao.updated_at = utc_now()
        self.repository.flush(db)
        return sessao

    def close_active_equivalent(
        self,
        db: Session,
        *,
        demanda_id: str,
        evento_fim_id: str,
        fim_em: datetime,
        motivo_encerramento: str,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
    ) -> SessaoTrabalho | None:
        already_closed_by_event = self.repository.get_by_evento_fim_id(db, evento_fim_id)
        if already_closed_by_event:
            return already_closed_by_event
        if not usuario_id and not departamento_id:
            return None
        active = self.repository.get_active_equivalent(
            db,
            demanda_id=demanda_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
        )
        if active is None:
            return None
        return self.close_session(
            db,
            active,
            evento_fim_id=evento_fim_id,
            fim_em=fim_em,
            motivo_encerramento=motivo_encerramento,
        )

    def encerrar_ativas_da_demanda(
        self,
        db: Session,
        *,
        empresa_id: str,
        demanda_id: str,
        motivo_encerramento: str,
        fim_em: datetime,
        usuario_ids: list[str] | None = None,
        departamento_ids: list[str] | None = None,
        workflow_etapa_id: str | None = None,
    ) -> list[SessaoTrabalho]:
        """Encerramento AUTOMÁTICO por transição de domínio (Fase 11B.2A). Chamado DENTRO da transação da transição (não faz commit): o Evento de fim e o
        fechamento entram junto com a mudança que os causou, ou nenhum entra.

        - Escopo: SÓ sessões ATIVAS DESTA demanda (outra demanda nunca é tocada). Sem filtro = todas; `usuario_ids`/`departamento_ids` = só as dessas pessoas /
          dessos departamentos (sessão puramente departamental); `workflow_etapa_id` = só as ligadas à etapa.
        - Idempotente: sessão já encerrada/cancelada nem é selecionada (nada de segundo evento, duração ou carimbo alterado); a seleção trava as linhas
          (`FOR UPDATE`), então transições concorrentes não fecham duas vezes.
        - Duração = `fim_em - inicio_em` pela MESMA regra de `close_session` (nunca negativa). Um Evento `sessao_trabalho_encerrada` por sessão, com o
          motivo e a marca `automatico` — a mesma forma do encerramento manual.
        """
        self._validate_motivo(motivo_encerramento)
        ativas = self.repository.listar_ativas_para_encerramento(
            db,
            empresa_id=empresa_id,
            demanda_id=demanda_id,
            usuario_ids=usuario_ids,
            departamento_ids=departamento_ids,
            workflow_etapa_id=workflow_etapa_id,
        )
        fechadas: list[SessaoTrabalho] = []
        for sessao in ativas:
            evento = self.evento_service.create_evento(
                db,
                EventoCreate(
                    empresaId=sessao.empresa_id,
                    agenciaId=sessao.agencia_id,
                    tipo="sessao_trabalho_encerrada",
                    entidadeTipo="demanda",
                    entidadeId=sessao.demanda_id,
                    usuarioId=sessao.usuario_id,
                    payload={
                        "demandaId": sessao.demanda_id,
                        "motivoEncerramento": motivo_encerramento,
                        "automatico": True,
                    },
                    occurredAt=fim_em,
                ),
                commit=False,
            )
            fechadas.append(
                self.close_session(
                    db, sessao, evento_fim_id=evento.id, fim_em=fim_em, motivo_encerramento=motivo_encerramento
                )
            )
        return fechadas

    def horas_departamento(
        self, db: Session, *, empresa_id: str, departamento_id: str, usuario: Usuario
    ) -> tuple[float, int]:
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise SessaoTrabalhoDepartamentoNaoEncontradoError("Departamento não encontrado nesta empresa")
        if not pode_consultar_horas_departamento(db, usuario, departamento_id):
            raise EscopoHorasNaoAutorizadoError("Sem direito ao agregado de horas deste departamento")
        # UM instante só por resposta: as sessões ativas são todas medidas até o mesmo `as_of`.
        return self.repository.horas_departamento(
            db, empresa_id=empresa_id, departamento_id=departamento_id, as_of=utc_now()
        )

    def resumo_trafego(self, db: Session, *, empresa_id: str, periodo_inicio: datetime) -> float:
        return self.repository.resumo_trafego(db, empresa_id=empresa_id, periodo_inicio=periodo_inicio)

    def indicadores_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        periodo_inicio: datetime,
        status: str = "todos",
        usuario_ids: list[str] | None = None,
        departamento_ids: list[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
    ) -> dict[str, int]:
        return self.repository.indicadores_trafego(
            db,
            empresa_id=empresa_id,
            periodo_inicio=periodo_inicio,
            status=status,
            usuario_ids=usuario_ids,
            departamento_ids=departamento_ids,
            demanda_query=demanda_query,
            avancados=avancados,
        )

    def carga_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_ids: list[str] | None = None,
        departamento_ids: list[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
    ) -> dict[str, list[dict]]:
        return self.repository.carga_trafego(
            db,
            empresa_id=empresa_id,
            usuario_ids=usuario_ids,
            departamento_ids=departamento_ids,
            demanda_query=demanda_query,
            avancados=avancados,
        )

    def agora_trafego(
        self,
        db: Session,
        *,
        empresa_id: str,
        usuario_ids: list[str] | None = None,
        departamento_ids: list[str] | None = None,
        demanda_query: str | None = None,
        avancados: FiltrosSessaoAvancados | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        return self.repository.agora_trafego(
            db,
            empresa_id=empresa_id,
            usuario_ids=usuario_ids,
            departamento_ids=departamento_ids,
            demanda_query=demanda_query,
            avancados=avancados,
            limit=limit,
            offset=offset,
        )

    def demanda_ids_ativas_da_empresa(self, db: Session, *, empresa_id: str) -> list[str]:
        return self.repository.demanda_ids_ativas_da_empresa(db, empresa_id=empresa_id)

    def equipe_do_departamento_agora(self, db: Session, *, empresa_id: str, departamento_id: str) -> list[dict]:
        return self.repository.equipe_do_departamento_agora(db, empresa_id=empresa_id, departamento_id=departamento_id)

    def demanda_ids_ativas_do_usuario(self, db: Session, *, empresa_id: str, usuario_id: str) -> list[str]:
        return self.repository.demanda_ids_ativas_do_usuario(db, empresa_id=empresa_id, usuario_id=usuario_id)

    def get_session(self, db: Session, sessao_id: str) -> SessaoTrabalho | None:
        return self.repository.get_by_id(db, sessao_id)

    def list_sessions(self, db: Session, **filters) -> list[SessaoTrabalho]:
        status = filters.get("status")
        if status and status not in STATUSES_SESSAO:
            raise ValueError(f"Status de sessão inválido: {status}")
        return self.repository.list(db, **filters)

    def _validate_responsavel(
        self,
        *,
        usuario_id: str | None,
        departamento_id: str | None,
        allow_usuario_and_departamento: bool,
    ) -> None:
        if not usuario_id and not departamento_id:
            raise ValueError("Sessão exige usuarioId ou departamentoId")
        if usuario_id and departamento_id and not allow_usuario_and_departamento:
            raise ValueError("Sessão com usuarioId e departamentoId exige justificativa explícita")

    def _validate_motivo(self, motivo_encerramento: str) -> None:
        if motivo_encerramento not in MOTIVOS_ENCERRAMENTO:
            raise ValueError(f"Motivo de encerramento inválido: {motivo_encerramento}")
