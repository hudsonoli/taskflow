from datetime import datetime, time
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.expediente import REGRA_PADRAO, JanelaDia, duracao_horas_dia, esta_dentro_expediente
from app.core.expediente import RegraExpediente as RegraExpedienteCalculo
from app.core.relogio import agora_local, agora_utc
from app.domain.event_types import DomainEventType
from app.models.regra_expediente import RegraExpedienteDia
from app.models.regra_expediente import RegraExpediente as RegraExpedienteModel
from app.repositories.regra_expediente_repository import RegraExpedienteRepository
from app.schemas.regra_expediente import (
    EstadoExpedienteRead,
    JanelaDiaRead,
    JanelaDiaWrite,
    RegraExpedienteRead,
    RegraExpedienteUpdate,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "regra_expediente"


class RegraExpedienteService:
    def __init__(
        self,
        repository: RegraExpedienteRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or RegraExpedienteRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Leitura / inicialização
    # ----------------------------------------------------------------------------------

    def get_ou_criar(self, db: Session, *, empresa_id: str) -> RegraExpedienteModel:
        """Singleton por Empresa. Nenhuma Empresa fica sem regra quando consultada: se ainda
        não existir, cria a partir de `REGRA_PADRAO` — a ÚNICA finalidade que `REGRA_PADRAO`
        tem nesta fase (ver docstring de app/core/expediente.py); depois de criada, quem
        chama de novo só lê o banco.

        Concorrência: `empresa_id` é UNIQUE. Duas requisições vendo "não existe" ao mesmo
        tempo — a segunda leva IntegrityError no INSERT, dá rollback e relê: nunca duplica,
        nunca deixa a exceção vazar como 500 genérico.

        Commit próprio (só no caminho de criação — leitura pura não commita nada): é uma
        inicialização idempotente e autocontida, não uma mutação de negócio, então não
        precisa esperar a transação de quem chamou (ex.: DemandaService.update_demanda,
        que ainda não alterou a Demanda no ponto em que chama isto — ver
        DemandaService._ensure_dentro_expediente).
        """
        existente = self.repository.get_by_empresa(db, empresa_id)
        if existente is not None:
            return existente

        try:
            criada = self._criar_padrao(db, empresa_id=empresa_id)
            db.commit()
            db.refresh(criada)
            return criada
        except IntegrityError:
            db.rollback()
            existente = self.repository.get_by_empresa(db, empresa_id)
            if existente is None:
                raise
            return existente

    def _criar_padrao(self, db: Session, *, empresa_id: str) -> RegraExpedienteModel:
        now = agora_utc()
        regra = RegraExpedienteModel(
            id=str(uuid4()),
            empresa_id=empresa_id,
            ativo=REGRA_PADRAO.ativo,
            tolerancia_retomada_minutos=REGRA_PADRAO.tolerancia_retomada_minutos,
            created_at=now,
            updated_at=now,
        )
        self.repository.create(db, regra)

        dias = [
            RegraExpedienteDia(
                id=str(uuid4()),
                regra_expediente_id=regra.id,
                dia_semana=dia_semana,
                ativo=janela.ativo,
                manha_inicio=_string_para_time(janela.manha_inicio),
                manha_fim=_string_para_time(janela.manha_fim),
                tarde_inicio=_string_para_time(janela.tarde_inicio),
                tarde_fim=_string_para_time(janela.tarde_fim),
            )
            for dia_semana, janela in REGRA_PADRAO.dias.items()
        ]
        self.repository.create_dias(db, dias)
        return regra

    def get_regra_calculo(self, db: Session, *, empresa_id: str) -> RegraExpedienteCalculo:
        """Converte o model SQL pro DTO puro que `esta_dentro_expediente` consome — ver
        docstring de app/core/expediente.py sobre não misturar as duas representações."""
        regra = self.get_ou_criar(db, empresa_id=empresa_id)
        dias_model = self.repository.list_dias(db, regra.id)
        dias = {
            dia.dia_semana: JanelaDia(
                ativo=dia.ativo,
                manha_inicio=_time_para_string(dia.manha_inicio),
                manha_fim=_time_para_string(dia.manha_fim),
                tarde_inicio=_time_para_string(dia.tarde_inicio),
                tarde_fim=_time_para_string(dia.tarde_fim),
            )
            for dia in dias_model
        }
        return RegraExpedienteCalculo(
            ativo=regra.ativo, tolerancia_retomada_minutos=regra.tolerancia_retomada_minutos, dias=dias
        )

    # ----------------------------------------------------------------------------------
    # Alteração
    # ----------------------------------------------------------------------------------

    def atualizar(
        self,
        db: Session,
        data: RegraExpedienteUpdate,
        *,
        empresa_id: str,
        actor_usuario_id: str,
    ) -> RegraExpedienteModel:
        try:
            regra = self.get_ou_criar(db, empresa_id=empresa_id)
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            changed_fields: list[str] = []
            now = agora_utc()

            if "ativo" in updates and updates["ativo"] != regra.ativo:
                regra.ativo = updates["ativo"]
                changed_fields.append("ativo")

            if (
                "tolerancia_retomada_minutos" in updates
                and updates["tolerancia_retomada_minutos"] != regra.tolerancia_retomada_minutos
            ):
                regra.tolerancia_retomada_minutos = updates["tolerancia_retomada_minutos"]
                changed_fields.append("toleranciaRetomadaMinutos")

            if data.dias is not None:
                self._substituir_dias(db, regra.id, data.dias)
                changed_fields.append("dias")

            if changed_fields:
                regra.updated_at = now
                self.repository.update(db, regra)
                self._publish_event(db, regra, actor_usuario_id, campos_alterados=changed_fields, occurred_at=now)

            db.commit()
            db.refresh(regra)
            return regra
        except Exception:
            db.rollback()
            raise

    def _substituir_dias(self, db: Session, regra_expediente_id: str, dias_novos: list[JanelaDiaWrite]) -> None:
        """Update em cada uma das 7 linhas já existentes (por `dia_semana`), nunca
        DELETE+recreate — as linhas nascem junto com a regra em `_criar_padrao` e nunca são
        removidas (ver docstring de RegraExpedienteDia)."""
        existentes = {dia.dia_semana: dia for dia in self.repository.list_dias(db, regra_expediente_id)}
        for novo in dias_novos:
            atual = existentes[novo.dia_semana]
            atual.ativo = novo.ativo
            atual.manha_inicio = novo.manha_inicio if novo.ativo else None
            atual.manha_fim = novo.manha_fim if novo.ativo else None
            atual.tarde_inicio = novo.tarde_inicio if novo.ativo else None
            atual.tarde_fim = novo.tarde_fim if novo.ativo else None
            self.repository.update_dia(db, atual)

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, regra: RegraExpedienteModel) -> RegraExpedienteRead:
        dias = self.repository.list_dias(db, regra.id)
        return RegraExpedienteRead(
            id=regra.id,
            empresaId=regra.empresa_id,
            ativo=regra.ativo,
            toleranciaRetomadaMinutos=regra.tolerancia_retomada_minutos,
            dias=[
                JanelaDiaRead(
                    diaSemana=dia.dia_semana,
                    ativo=dia.ativo,
                    manhaInicio=dia.manha_inicio,
                    manhaFim=dia.manha_fim,
                    tardeInicio=dia.tarde_inicio,
                    tardeFim=dia.tarde_fim,
                )
                for dia in dias
            ],
            createdAt=regra.created_at,
            updatedAt=regra.updated_at,
        )

    def to_estado_read(self, db: Session, *, empresa_id: str) -> EstadoExpedienteRead:
        regra_calculo = self.get_regra_calculo(db, empresa_id=empresa_id)
        agora = agora_local()
        dia_hoje = regra_calculo.dias.get(agora.weekday())
        return EstadoExpedienteRead(
            ativo=regra_calculo.ativo,
            dentroExpediente=esta_dentro_expediente(agora, regra=regra_calculo),
            agora=agora,
            toleranciaRetomadaMinutos=regra_calculo.tolerancia_retomada_minutos,
            horasUteisHoje=duracao_horas_dia(dia_hoje) if dia_hoje is not None else 0.0,
        )

    # ----------------------------------------------------------------------------------
    # Regras internas
    # ----------------------------------------------------------------------------------

    def _publish_event(
        self,
        db: Session,
        regra: RegraExpedienteModel,
        actor_usuario_id: str | None,
        *,
        campos_alterados: list[str],
        occurred_at: datetime,
    ) -> None:
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.REGRA_EXPEDIENTE_ALTERADA,
            empresa_id=regra.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=regra.id,
            usuario_id=actor_usuario_id,
            payload={
                "empresa_id": regra.empresa_id,
                "regra_expediente_id": regra.id,
                "timestamp": occurred_at.isoformat(),
                "camposAlterados": campos_alterados,
            },
            occurred_at=occurred_at,
        )


def _string_para_time(valor: str | None) -> time | None:
    if valor is None:
        return None
    horas, minutos = (int(parte) for parte in valor.split(":"))
    return time(hour=horas, minute=minutos)


def _time_para_string(valor: time | None) -> str | None:
    if valor is None:
        return None
    return valor.strftime("%H:%M")
