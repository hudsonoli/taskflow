from datetime import datetime, time
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.expediente import (
    REGRA_PADRAO,
    DiaEspecial,
    duracao_horas_dia,
    esta_dentro_expediente,
    janela_de_periodos,
    janela_do_dia,
    momento_local,
)
from app.core.expediente import RegraExpediente as RegraExpedienteCalculo
from app.core.relogio import agora_utc, fuso_aplicacao
from app.domain.event_types import DomainEventType
from app.models.regra_expediente import (
    RegraExpedienteDia,
    RegraExpedienteDiaEspecial,
    RegraExpedienteDiaEspecialPeriodo,
    RegraExpedientePeriodo,
)
from app.models.regra_expediente import RegraExpediente as RegraExpedienteModel
from app.repositories.regra_expediente_repository import RegraExpedienteRepository
from app.schemas.regra_expediente import (
    DiaEspecialRead,
    DiaEspecialUpdate,
    DiaEspecialWrite,
    EstadoExpedienteRead,
    JanelaDiaRead,
    JanelaDiaWrite,
    PeriodoRead,
    PeriodoWrite,
    RegraExpedienteRead,
    RegraExpedienteUpdate,
    normalizar_periodos,
)
from app.services.domain_event_publisher import DomainEventPublisher

TIPO_ENTIDADE = "regra_expediente"


class DiaEspecialNaoEncontradoError(LookupError):
    """Dia especial inexistente ou de outra empresa (404 nos dois casos)."""


class DiaEspecialConflitoError(ValueError):
    """Já existe um dia especial desta origem nesta data (409)."""


class DiaEspecialNaoEditavelError(ValueError):
    """Tentativa de alterar/excluir o conteúdo de um dia especial AUTOMÁTICO (só `ativo` pode mudar) ou dado inválido para o tipo (422)."""


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
            # Fase Expediente 1: as flags críticas nascem desligadas; o fuso inicial é o da aplicação.
            bloquear_fora_expediente=False,
            pausar_no_fim_periodo=False,
            antecedencia_acesso_minutos=REGRA_PADRAO.antecedencia_acesso_minutos,
            timezone=fuso_aplicacao().key,
            feriados_automaticos=False,
            created_at=now,
            updated_at=now,
        )
        self.repository.create(db, regra)

        dias = []
        periodos_por_dia: dict[int, list[PeriodoWrite]] = {}
        for dia_semana, janela in REGRA_PADRAO.dias.items():
            periodos = [
                PeriodoWrite(inicio=_string_para_time(inicio), fim=_string_para_time(fim)) for inicio, fim in janela.lista_periodos()
            ]
            dia = RegraExpedienteDia(id=str(uuid4()), regra_expediente_id=regra.id, dia_semana=dia_semana, ativo=False)
            self._aplicar_periodos_ao_dia(dia, periodos)
            periodos_por_dia[dia_semana] = periodos
            dias.append(dia)
        self.repository.create_dias(db, dias)
        for dia_semana, periodos in periodos_por_dia.items():
            self.repository.replace_periodos_do_dia(db, regra.id, dia_semana, self._linhas_de_periodos(regra.id, dia_semana, periodos))
        return regra

    def get_regra_calculo(self, db: Session, *, empresa_id: str) -> RegraExpedienteCalculo:
        """Converte o model SQL pro DTO puro que `esta_dentro_expediente` consome — ver
        docstring de app/core/expediente.py sobre não misturar as duas representações."""
        regra = self.get_ou_criar(db, empresa_id=empresa_id)
        periodos = self.repository.list_periodos(db, regra.id)
        dias = {
            # `dia.ativo` (derivado dos períodos) também FECHA o dia se alguém o desligar por fora (legado/rollback): defesa barata, nunca abre um dia fechado.
            dia.dia_semana: janela_de_periodos(
                [(_time_para_string(p.inicio), _time_para_string(p.fim)) for p in periodos.get(dia.dia_semana, [])] if dia.ativo else []
            )
            for dia in self.repository.list_dias(db, regra.id)
        }
        especiais = self.repository.list_dias_especiais(db, regra.id)
        periodos_especiais = self.repository.list_periodos_especiais(db, [d.id for d in especiais])
        return RegraExpedienteCalculo(
            ativo=regra.ativo,
            tolerancia_retomada_minutos=regra.tolerancia_retomada_minutos,
            dias=dias,
            antecedencia_acesso_minutos=regra.antecedencia_acesso_minutos,
            timezone=regra.timezone,
            dias_especiais=tuple(
                DiaEspecial(
                    data=especial.data,
                    tipo=especial.tipo,
                    origem=especial.origem,
                    ativo=especial.ativo,
                    nome=especial.nome,
                    periodos=tuple(
                        (_time_para_string(p.inicio), _time_para_string(p.fim)) for p in periodos_especiais.get(especial.id, [])
                    ),
                )
                for especial in especiais
            ),
            bloquear_fora_expediente=regra.bloquear_fora_expediente,
            pausar_no_fim_periodo=regra.pausar_no_fim_periodo,
            feriados_automaticos=regra.feriados_automaticos,
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

            simples = (
                ("ativo", "ativo"),
                ("tolerancia_retomada_minutos", "toleranciaRetomadaMinutos"),
                ("bloquear_fora_expediente", "bloquearForaExpediente"),
                ("pausar_no_fim_periodo", "pausarNoFimPeriodo"),
                ("antecedencia_acesso_minutos", "antecedenciaAcessoMinutos"),
                ("timezone", "timezone"),
                ("feriados_automaticos", "feriadosAutomaticos"),
            )
            for atributo, rotulo in simples:
                if atributo in updates and updates[atributo] is not None and updates[atributo] != getattr(regra, atributo):
                    setattr(regra, atributo, updates[atributo])
                    changed_fields.append(rotulo)

            if data.dias is not None and self._substituir_dias(db, regra.id, data.dias):
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

    def _substituir_dias(self, db: Session, regra_expediente_id: str, dias_novos: list[JanelaDiaWrite]) -> bool:
        """Substitui os PERÍODOS de cada um dos 7 dias (as linhas de `regra_expediente_dias` nascem com a regra e nunca são removidas). Devolve se algo mudou de
        fato (reenviar a mesma configuração não gera evento)."""
        existentes = {dia.dia_semana: dia for dia in self.repository.list_dias(db, regra_expediente_id)}
        atuais = self.repository.list_periodos(db, regra_expediente_id)
        mudou = False
        for novo in dias_novos:
            periodos = list(novo.periodos or [])
            antes = [(p.inicio, p.fim) for p in atuais.get(novo.dia_semana, [])]
            depois = [(p.inicio, p.fim) for p in periodos]
            dia = existentes.get(novo.dia_semana)
            if dia is None:  # defensivo: a regra sempre nasce com os 7 dias
                dia = RegraExpedienteDia(id=str(uuid4()), regra_expediente_id=regra_expediente_id, dia_semana=novo.dia_semana, ativo=False)
                self.repository.create_dias(db, [dia])
            if antes != depois:
                mudou = True
                self.repository.replace_periodos_do_dia(
                    db, regra_expediente_id, novo.dia_semana, self._linhas_de_periodos(regra_expediente_id, novo.dia_semana, periodos)
                )
            self._aplicar_periodos_ao_dia(dia, periodos)
            self.repository.update_dia(db, dia)
        return mudou

    @staticmethod
    def _linhas_de_periodos(regra_expediente_id: str, dia_semana: int, periodos: list[PeriodoWrite]) -> list[RegraExpedientePeriodo]:
        return [
            RegraExpedientePeriodo(
                id=str(uuid4()), regra_expediente_id=regra_expediente_id, dia_semana=dia_semana, ordem=indice, inicio=p.inicio, fim=p.fim
            )
            for indice, p in enumerate(periodos, start=1)
        ]

    @staticmethod
    def _aplicar_periodos_ao_dia(dia: RegraExpedienteDia, periodos: list[PeriodoWrite]) -> None:
        """`ativo` derivado + ESPELHO LEGADO (manhã/tarde) quando o dia tem exatamente dois períodos — assim um rollback do código (sem downgrade do banco) continua
        lendo horários coerentes. Dia com 1, 3 ou mais períodos zera o espelho."""
        dia.ativo = bool(periodos)
        dia.manha_inicio = periodos[0].inicio if len(periodos) == 2 else None
        dia.manha_fim = periodos[0].fim if len(periodos) == 2 else None
        dia.tarde_inicio = periodos[1].inicio if len(periodos) == 2 else None
        dia.tarde_fim = periodos[1].fim if len(periodos) == 2 else None

    # ----------------------------------------------------------------------------------
    # Dias especiais (cadastro MANUAL — a importação automática é de outra fase)
    # ----------------------------------------------------------------------------------

    def listar_dias_especiais(self, db: Session, *, empresa_id: str) -> list[DiaEspecialRead]:
        regra = self.get_ou_criar(db, empresa_id=empresa_id)
        return self._dias_especiais_read(db, regra)

    def criar_dia_especial(self, db: Session, data: DiaEspecialWrite, *, empresa_id: str, actor_usuario_id: str) -> DiaEspecialRead:
        try:
            regra = self.get_ou_criar(db, empresa_id=empresa_id)
            if self.repository.find_dia_especial(db, regra.id, data.data, "manual") is not None:
                raise DiaEspecialConflitoError("Já existe um dia especial manual nesta data — edite-o em vez de criar outro")
            now = agora_utc()
            dia = RegraExpedienteDiaEspecial(
                id=str(uuid4()),
                empresa_id=empresa_id,
                regra_expediente_id=regra.id,
                data=data.data,
                nome=data.nome,
                origem="manual",
                tipo=data.tipo,
                ativo=data.ativo,
                created_at=now,
                updated_at=now,
            )
            self.repository.save_dia_especial(db, dia)
            self.repository.replace_periodos_especiais(db, dia.id, self._linhas_especiais(dia.id, data.periodos))
            self._publish_dia_especial_evento(db, regra, actor_usuario_id, "criado", dia, now)
            db.commit()
            return self._dia_especial_read(db, dia)
        except Exception:
            db.rollback()
            raise

    def atualizar_dia_especial(
        self, db: Session, dia_especial_id: str, data: DiaEspecialUpdate, *, empresa_id: str, actor_usuario_id: str
    ) -> DiaEspecialRead:
        try:
            regra = self.get_ou_criar(db, empresa_id=empresa_id)
            dia = self._dia_da_empresa(db, regra, dia_especial_id)
            updates = data.model_dump(exclude_unset=True, by_alias=False)
            if dia.origem == "automatico" and set(updates) - {"ativo"}:
                raise DiaEspecialNaoEditavelError("Um dia especial automático só pode ser ativado/desativado — para mudar o conteúdo, crie um manual na mesma data")
            now = agora_utc()
            if "nome" in updates and updates["nome"] is not None:
                dia.nome = updates["nome"]
            if "ativo" in updates and updates["ativo"] is not None:
                dia.ativo = updates["ativo"]
            tipo_final = updates.get("tipo") or dia.tipo
            periodos_atuais = self.repository.list_periodos_especiais(db, [dia.id]).get(dia.id, [])
            if "periodos" in updates and updates["periodos"] is not None:
                periodos_finais = normalizar_periodos([PeriodoWrite(**p) if isinstance(p, dict) else p for p in updates["periodos"]], "dia especial")
            else:
                periodos_finais = [PeriodoWrite(inicio=p.inicio, fim=p.fim) for p in periodos_atuais]
            if tipo_final == "trabalho_excepcional" and not periodos_finais:
                raise DiaEspecialNaoEditavelError("trabalho_excepcional precisa de pelo menos um período")
            if tipo_final != "trabalho_excepcional":
                if "periodos" in updates and updates["periodos"]:
                    raise DiaEspecialNaoEditavelError(f"o tipo {tipo_final} não usa períodos")
                periodos_finais = []
            dia.tipo = tipo_final
            dia.updated_at = now
            self.repository.save_dia_especial(db, dia)
            self.repository.replace_periodos_especiais(db, dia.id, self._linhas_especiais(dia.id, periodos_finais))
            self._publish_dia_especial_evento(db, regra, actor_usuario_id, "alterado", dia, now)
            db.commit()
            return self._dia_especial_read(db, dia)
        except Exception:
            db.rollback()
            raise

    def remover_dia_especial(self, db: Session, dia_especial_id: str, *, empresa_id: str, actor_usuario_id: str) -> None:
        try:
            regra = self.get_ou_criar(db, empresa_id=empresa_id)
            dia = self._dia_da_empresa(db, regra, dia_especial_id)
            if dia.origem == "automatico":
                raise DiaEspecialNaoEditavelError("Um dia especial automático não é excluído — desative-o")
            now = agora_utc()
            self._publish_dia_especial_evento(db, regra, actor_usuario_id, "removido", dia, now)
            self.repository.delete_dia_especial(db, dia)
            db.commit()
        except Exception:
            db.rollback()
            raise

    def _dia_da_empresa(self, db: Session, regra: RegraExpedienteModel, dia_especial_id: str) -> RegraExpedienteDiaEspecial:
        dia = self.repository.get_dia_especial(db, dia_especial_id)
        if dia is None or dia.regra_expediente_id != regra.id or dia.empresa_id != regra.empresa_id:
            raise DiaEspecialNaoEncontradoError("Dia especial não encontrado")
        return dia

    @staticmethod
    def _linhas_especiais(dia_especial_id: str, periodos: list[PeriodoWrite]) -> list[RegraExpedienteDiaEspecialPeriodo]:
        return [
            RegraExpedienteDiaEspecialPeriodo(id=str(uuid4()), dia_especial_id=dia_especial_id, ordem=indice, inicio=p.inicio, fim=p.fim)
            for indice, p in enumerate(periodos, start=1)
        ]

    def _dias_especiais_read(self, db: Session, regra: RegraExpedienteModel) -> list[DiaEspecialRead]:
        dias = self.repository.list_dias_especiais(db, regra.id)
        periodos = self.repository.list_periodos_especiais(db, [d.id for d in dias])
        return [
            DiaEspecialRead(
                id=dia.id,
                data=dia.data,
                nome=dia.nome,
                origem=dia.origem,
                tipo=dia.tipo,
                ativo=dia.ativo,
                periodos=[PeriodoRead(inicio=p.inicio, fim=p.fim) for p in periodos.get(dia.id, [])],
                createdAt=dia.created_at,
                updatedAt=dia.updated_at,
            )
            for dia in dias
        ]

    def _dia_especial_read(self, db: Session, dia: RegraExpedienteDiaEspecial) -> DiaEspecialRead:
        periodos = self.repository.list_periodos_especiais(db, [dia.id]).get(dia.id, [])
        return DiaEspecialRead(
            id=dia.id,
            data=dia.data,
            nome=dia.nome,
            origem=dia.origem,
            tipo=dia.tipo,
            ativo=dia.ativo,
            periodos=[PeriodoRead(inicio=p.inicio, fim=p.fim) for p in periodos],
            createdAt=dia.created_at,
            updatedAt=dia.updated_at,
        )

    def _publish_dia_especial_evento(
        self, db: Session, regra: RegraExpedienteModel, actor_usuario_id: str, acao: str, dia: RegraExpedienteDiaEspecial, occurred_at: datetime
    ) -> None:
        self._publish_event(
            db,
            regra,
            actor_usuario_id,
            campos_alterados=["diasEspeciais"],
            occurred_at=occurred_at,
            extra={"diaEspecial": {"acao": acao, "data": dia.data.isoformat(), "tipo": dia.tipo, "origem": dia.origem, "ativo": dia.ativo}},
        )

    # ----------------------------------------------------------------------------------
    # Apresentação
    # ----------------------------------------------------------------------------------

    def to_read(self, db: Session, regra: RegraExpedienteModel) -> RegraExpedienteRead:
        dias = self.repository.list_dias(db, regra.id)
        periodos = self.repository.list_periodos(db, regra.id)
        leitura_dias = []
        for dia in dias:
            lista = periodos.get(dia.dia_semana, [])
            primeiro = lista[0] if lista else None
            ultimo = lista[-1] if len(lista) > 1 else None
            leitura_dias.append(
                JanelaDiaRead(
                    diaSemana=dia.dia_semana,
                    ativo=bool(lista),
                    periodos=[PeriodoRead(inicio=p.inicio, fim=p.fim) for p in lista],
                    manhaInicio=primeiro.inicio if primeiro else None,
                    manhaFim=primeiro.fim if primeiro else None,
                    tardeInicio=ultimo.inicio if ultimo else None,
                    tardeFim=ultimo.fim if ultimo else None,
                )
            )
        return RegraExpedienteRead(
            id=regra.id,
            empresaId=regra.empresa_id,
            ativo=regra.ativo,
            toleranciaRetomadaMinutos=regra.tolerancia_retomada_minutos,
            bloquearForaExpediente=regra.bloquear_fora_expediente,
            pausarNoFimPeriodo=regra.pausar_no_fim_periodo,
            antecedenciaAcessoMinutos=regra.antecedencia_acesso_minutos,
            timezone=regra.timezone,
            feriadosAutomaticos=regra.feriados_automaticos,
            dias=leitura_dias,
            diasEspeciais=self._dias_especiais_read(db, regra),
            createdAt=regra.created_at,
            updatedAt=regra.updated_at,
        )

    def to_estado_read(self, db: Session, *, empresa_id: str) -> EstadoExpedienteRead:
        regra_calculo = self.get_regra_calculo(db, empresa_id=empresa_id)
        agora = momento_local(None, regra_calculo)
        return EstadoExpedienteRead(
            ativo=regra_calculo.ativo,
            dentroExpediente=esta_dentro_expediente(agora, regra=regra_calculo),
            agora=agora,
            toleranciaRetomadaMinutos=regra_calculo.tolerancia_retomada_minutos,
            horasUteisHoje=duracao_horas_dia(janela_do_dia(regra_calculo, agora.date())),
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
        extra: dict | None = None,
    ) -> None:
        payload = {
            "empresa_id": regra.empresa_id,
            "regra_expediente_id": regra.id,
            "timestamp": occurred_at.isoformat(),
            "camposAlterados": campos_alterados,
        }
        if extra:
            payload.update(extra)
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.REGRA_EXPEDIENTE_ALTERADA,
            empresa_id=regra.empresa_id,
            entidade_tipo=TIPO_ENTIDADE,
            entidade_id=regra.id,
            usuario_id=actor_usuario_id,
            payload=payload,
            occurred_at=occurred_at,
        )


def _string_para_time(valor: str | None) -> time | None:
    if valor is None:
        return None
    horas, minutos = (int(parte) for parte in valor.split(":")[:2])
    return time(hour=horas, minute=minutos)


def _time_para_string(valor: time | None) -> str | None:
    if valor is None:
        return None
    return valor.strftime("%H:%M")
