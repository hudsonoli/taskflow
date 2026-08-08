from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.sessao_trabalho import SessaoTrabalho
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository

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


class SessaoTrabalhoService:
    def __init__(self, repository: SessaoTrabalhoRepository | None = None) -> None:
        self.repository = repository or SessaoTrabalhoRepository()

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
