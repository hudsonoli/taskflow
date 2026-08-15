from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.escopo import EscopoHorasNaoAutorizadoError, pode_consultar_horas_departamento
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.repositories.departamento_repository import DepartamentoRepository
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.repositories.usuario_repository import UsuarioRepository

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
    }
)


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


class SessaoTrabalhoService:
    def __init__(
        self,
        repository: SessaoTrabalhoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        departamento_repository: DepartamentoRepository | None = None,
    ) -> None:
        self.repository = repository or SessaoTrabalhoRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.departamento_repository = departamento_repository or DepartamentoRepository()

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
        active = self.repository.get_active_equivalent(
            db,
            demanda_id=demanda_id,
            usuario_id=usuario_id,
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
        return self.repository.create(db, sessao)

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

    def horas_departamento(
        self, db: Session, *, empresa_id: str, departamento_id: str, usuario: Usuario
    ) -> tuple[float, int]:
        departamento = self.departamento_repository.get_by_id(db, departamento_id)
        if departamento is None or departamento.empresa_id != empresa_id:
            raise SessaoTrabalhoDepartamentoNaoEncontradoError("Departamento não encontrado nesta empresa")
        if not pode_consultar_horas_departamento(db, usuario, departamento_id):
            raise EscopoHorasNaoAutorizadoError("Sem direito ao agregado de horas deste departamento")
        return self.repository.horas_departamento(db, empresa_id=empresa_id, departamento_id=departamento_id)

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
