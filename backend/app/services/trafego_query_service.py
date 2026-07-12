from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.sessao_trabalho import SessaoTrabalho
from app.repositories.sessao_trabalho_repository import SessaoTrabalhoRepository
from app.schemas.trafego import TrafegoAgoraItem, TrafegoCargaItem, TrafegoResumo
from app.services.sessao_trabalho_service import STATUS_ATIVA, STATUS_ENCERRADA


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def elapsed_seconds(start: datetime, end: datetime) -> int:
    return max(0, int((ensure_utc(end) - ensure_utc(start)).total_seconds()))


class TrafegoQueryService:
    def __init__(self, repository: SessaoTrabalhoRepository | None = None) -> None:
        self.repository = repository or SessaoTrabalhoRepository()

    def list_agora(
        self,
        db: Session,
        *,
        empresa_id: str | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        demanda_id: str | None = None,
        workflow_etapa_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        now_utc: datetime | None = None,
    ) -> list[TrafegoAgoraItem]:
        now = ensure_utc(now_utc or utc_now())
        sessoes = self.repository.list_active(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            demanda_id=demanda_id,
            workflow_etapa_id=workflow_etapa_id,
            limit=limit,
            offset=offset,
        )
        return [self._to_agora_item(sessao, now) for sessao in sessoes]

    def get_carga(
        self,
        db: Session,
        *,
        empresa_id: str,
        agrupamento: str,
        now_utc: datetime | None = None,
    ) -> list[TrafegoCargaItem]:
        if agrupamento not in {"usuario", "departamento"}:
            raise ValueError("Agrupamento inválido")
        now = ensure_utc(now_utc or utc_now())
        sessoes = self.repository.list_active(db, empresa_id=empresa_id)
        groups: dict[str, dict] = {}

        for sessao in sessoes:
            agrupamento_id = sessao.usuario_id if agrupamento == "usuario" else sessao.departamento_id
            if not agrupamento_id:
                continue
            inicio_em = ensure_utc(sessao.inicio_em)
            updated_at = ensure_utc(sessao.updated_at)
            group = groups.setdefault(
                agrupamento_id,
                {
                    "sessoes": 0,
                    "demandas": set(),
                    "tempo": 0,
                    "inicio_mais_antigo": inicio_em,
                    "ultima_atualizacao": updated_at,
                },
            )
            group["sessoes"] += 1
            group["demandas"].add(sessao.demanda_id)
            group["tempo"] += elapsed_seconds(inicio_em, now)
            group["inicio_mais_antigo"] = min(group["inicio_mais_antigo"], inicio_em)
            group["ultima_atualizacao"] = max(group["ultima_atualizacao"], updated_at)

        return [
            TrafegoCargaItem(
                agrupamentoId=agrupamento_id,
                tipoAgrupamento=agrupamento,
                sessoesAtivas=group["sessoes"],
                demandasDistintas=len(group["demandas"]),
                tempoAtivoTotalSegundos=group["tempo"],
                inicioMaisAntigo=group["inicio_mais_antigo"],
                ultimaAtualizacao=group["ultima_atualizacao"],
            )
            for agrupamento_id, group in sorted(groups.items())
        ]

    def get_resumo(
        self,
        db: Session,
        *,
        empresa_id: str,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        usuario_id: str | None = None,
        departamento_id: str | None = None,
        demanda_id: str | None = None,
        now_utc: datetime | None = None,
    ) -> TrafegoResumo:
        now = ensure_utc(now_utc or utc_now())
        inicio_periodo, fim_periodo = self.resolve_period(data_inicio=data_inicio, data_fim=data_fim, now_utc=now)
        sessoes = self.repository.list_overlapping_period(
            db,
            empresa_id=empresa_id,
            data_inicio=inicio_periodo,
            data_fim=fim_periodo,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            demanda_id=demanda_id,
        )

        considered: list[tuple[SessaoTrabalho, int]] = []
        for sessao in sessoes:
            duration = self._clipped_duration(sessao, inicio_periodo, fim_periodo, now)
            if duration <= 0:
                continue
            considered.append((sessao, duration))

        durations = [duration for _, duration in considered]
        demandas = {sessao.demanda_id for sessao, _ in considered}
        usuarios = {sessao.usuario_id for sessao, _ in considered if sessao.usuario_id}
        departamentos = {sessao.departamento_id for sessao, _ in considered if sessao.departamento_id}
        total = sum(durations)
        count = len(durations)

        return TrafegoResumo(
            sessoesAtivas=sum(1 for sessao, _ in considered if sessao.status == STATUS_ATIVA),
            sessoesEncerradas=sum(1 for sessao, _ in considered if sessao.status == STATUS_ENCERRADA),
            demandasDistintas=len(demandas),
            usuariosDistintos=len(usuarios),
            departamentosDistintos=len(departamentos),
            tempoOperacionalEstimadoSegundos=total,
            tempoMedioSessaoSegundos=int(total / count) if count else 0,
            maiorSessaoSegundos=max(durations) if durations else 0,
            inicioPeriodo=inicio_periodo,
            fimPeriodo=fim_periodo,
        )

    def resolve_period(
        self,
        *,
        data_inicio: datetime | None,
        data_fim: datetime | None,
        now_utc: datetime,
    ) -> tuple[datetime, datetime]:
        now = ensure_utc(now_utc)
        if data_inicio is None and data_fim is None:
            inicio = now - timedelta(hours=24)
            fim = now
        elif data_inicio is not None and data_fim is None:
            inicio = ensure_utc(data_inicio)
            fim = now
        elif data_inicio is None and data_fim is not None:
            fim = ensure_utc(data_fim)
            inicio = fim - timedelta(hours=24)
        else:
            inicio = ensure_utc(data_inicio)  # type: ignore[arg-type]
            fim = ensure_utc(data_fim)  # type: ignore[arg-type]
        if fim < inicio:
            raise ValueError("dataFim deve ser maior ou igual a dataInicio")
        return inicio, fim

    def _to_agora_item(self, sessao: SessaoTrabalho, now: datetime) -> TrafegoAgoraItem:
        return TrafegoAgoraItem(
            sessaoId=sessao.id,
            empresaId=sessao.empresa_id,
            agenciaId=sessao.agencia_id,
            demandaId=sessao.demanda_id,
            workflowEtapaId=sessao.workflow_etapa_id,
            usuarioId=sessao.usuario_id,
            departamentoId=sessao.departamento_id,
            inicioEm=ensure_utc(sessao.inicio_em),
            tempoDecorridoSegundos=elapsed_seconds(sessao.inicio_em, now),
            status=sessao.status,
            eventoInicioId=sessao.evento_inicio_id,
        )

    def _clipped_duration(
        self,
        sessao: SessaoTrabalho,
        inicio_periodo: datetime,
        fim_periodo: datetime,
        now: datetime,
    ) -> int:
        inicio_sessao = ensure_utc(sessao.inicio_em)
        if sessao.status == STATUS_ATIVA:
            fim_sessao = min(now, fim_periodo)
        else:
            if sessao.fim_em is None:
                return 0
            fim_sessao = ensure_utc(sessao.fim_em)
        inicio_efetivo = max(inicio_sessao, inicio_periodo)
        fim_efetivo = min(fim_sessao, fim_periodo)
        return max(0, int((fim_efetivo - inicio_efetivo).total_seconds()))
