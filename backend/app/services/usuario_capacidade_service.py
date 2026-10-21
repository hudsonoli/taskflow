"""Capacidade individual (11B.2D-A): jornada semanal própria opcional e ausências por data de um Usuário.

## Autoridade (reaproveitada, nada novo)
- Leitura: `usuarios.visualizar`. Escrita: `usuarios.editar` (as rotas) + a regra de ALVO de `app/core/autoridade_usuarios` imposta aqui — o mesmo que o PATCH de Usuário: admin legado administra Gestor e
  Usuário; gestor (ou quem recebeu `usuarios.*` por override) só administra Usuário (`operador`). Operador comum não tem `usuarios.editar` e é recusado (403). Conta de sistema não tem jornada.
- Tenant: o usuário é sempre buscado por (id, empresa do ator) — de outra empresa é 404, igual a inexistente (nada vaza).

## Efeito
Nada aqui altera estimativa, janela planejada, divisão entre responsáveis, Demanda, workflow, sessões ou intervalos. Só muda o DENOMINADOR de capacidade da Carga, e só para essa pessoa.

## Auditoria
Toda mudança de fato publica um evento na MESMA transação (`usuario.jornada_alterada|removida`, `usuario.ausencia_criada|alterada|removida`) com o usuário afetado e antes/depois essenciais. Reenviar o
mesmo valor (no-op) não gera evento. A observação livre da ausência NÃO entra no payload.
"""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.autoridade_usuarios import ensure_pode_administrar_alvo
from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.models.usuario_capacidade import UsuarioAusencia, UsuarioJornada, UsuarioJornadaPeriodo
from app.repositories.usuario_capacidade_repository import UsuarioCapacidadeRepository
from app.schemas.regra_expediente import PeriodoRead
from app.schemas.usuario_capacidade import (
    AusenciaRead,
    AusenciaUpdate,
    AusenciaWrite,
    JornadaDiaRead,
    JornadaRead,
    JornadaWrite,
)
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.regra_expediente_service import RegraExpedienteService

TIPO_ENTIDADE_JORNADA = "usuario_jornada"
TIPO_ENTIDADE_AUSENCIA = "usuario_ausencia"


class UsuarioCapacidadeNaoEncontradoError(LookupError):
    """Usuário inexistente OU de outra empresa (404 nos dois casos), ou ausência que não é dele."""


class ContaDeSistemaSemCapacidadeError(PermissionError):
    """Conta de sistema não recebe trabalho nem tem jornada/ausência (403)."""


class CapacidadeInvalidaError(ValueError):
    """Dado inválido que só o service enxerga (ex.: edição que deixaria `fim` antes de `inicio`) — 422."""


def _texto(valor: time) -> str:
    return valor.strftime("%H:%M")


def _grade_texto(periodos_por_dia: dict[int, list[tuple[str, str]]]) -> dict[str, list[str]]:
    """Forma compacta e estável para o evento: {"0": ["09:00-12:00", ...]} só com dias que têm períodos."""
    return {str(dia): [f"{i}-{f}" for i, f in lista] for dia, lista in sorted(periodos_por_dia.items()) if lista}


class UsuarioCapacidadeService:
    def __init__(
        self,
        repository: UsuarioCapacidadeRepository | None = None,
        regra_service: RegraExpedienteService | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.repository = repository or UsuarioCapacidadeRepository()
        self.regra_service = regra_service or RegraExpedienteService()
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ------------------------------------------------------------------------------------------------------------------
    # Alvo e autoridade
    # ------------------------------------------------------------------------------------------------------------------

    def _alvo(self, db: Session, actor: Usuario, usuario_id: str, *, escrita: bool) -> Usuario:
        alvo = db.scalars(select(Usuario).where(Usuario.id == usuario_id, Usuario.empresa_id == actor.empresa_id)).first()
        if alvo is None:
            raise UsuarioCapacidadeNaoEncontradoError("Usuário não encontrado")
        if escrita:
            if alvo.is_system_account:
                raise ContaDeSistemaSemCapacidadeError("Conta de sistema não tem jornada nem ausências")
            ensure_pode_administrar_alvo(actor.perfil_base, alvo.perfil_base)  # AutoridadeUsuarioError → 403
        return alvo

    # ------------------------------------------------------------------------------------------------------------------
    # Jornada
    # ------------------------------------------------------------------------------------------------------------------

    def _periodos_atuais(self, db: Session, jornada: UsuarioJornada) -> dict[int, list[tuple[str, str]]]:
        return {dia: [(_texto(p.inicio), _texto(p.fim)) for p in lista] for dia, lista in self.repository.list_periodos(db, jornada.id).items()}

    def _jornada_read(self, db: Session, alvo: Usuario, jornada: UsuarioJornada | None) -> JornadaRead:
        if jornada is not None:
            por_dia = self.repository.list_periodos(db, jornada.id)
            dias = [JornadaDiaRead(diaSemana=d, periodos=[PeriodoRead(inicio=p.inicio, fim=p.fim) for p in por_dia.get(d, [])]) for d in range(7)]
            return JornadaRead(usuarioId=alvo.id, personalizada=True, dias=dias, updatedAt=jornada.updated_at)
        # Fallback: a semana recorrente da EMPRESA (só consulta; nada é copiado para o usuário).
        existente = self.regra_service.repository.get_by_empresa(db, alvo.empresa_id)
        dias_empresa = self.regra_service.get_regra_calculo(db, empresa_id=alvo.empresa_id).dias if existente is not None else {}
        dias = []
        for d in range(7):
            janela = dias_empresa.get(d)
            periodos = janela.lista_periodos() if janela is not None else ()
            dias.append(
                JornadaDiaRead(
                    diaSemana=d,
                    periodos=[PeriodoRead(inicio=time(int(i[:2]), int(i[3:5])), fim=time(int(f[:2]), int(f[3:5]))) for i, f in periodos],
                )
            )
        return JornadaRead(usuarioId=alvo.id, personalizada=False, dias=dias, updatedAt=None)

    def obter_jornada(self, db: Session, actor: Usuario, usuario_id: str) -> JornadaRead:
        alvo = self._alvo(db, actor, usuario_id, escrita=False)
        return self._jornada_read(db, alvo, self.repository.get_jornada(db, alvo.id))

    def substituir_jornada(self, db: Session, actor: Usuario, usuario_id: str, data: JornadaWrite) -> JornadaRead:
        """Cria a jornada personalizada ou SUBSTITUI a grade inteira. Dia não enviado = fechado. Mesma grade = no-op (sem evento)."""
        try:
            alvo = self._alvo(db, actor, usuario_id, escrita=True)
            novos = {dia.dia_semana: [(_texto(p.inicio), _texto(p.fim)) for p in dia.periodos] for dia in data.dias}
            novos = {dia: lista for dia, lista in novos.items() if lista}
            agora = agora_utc()
            jornada = self.repository.get_jornada(db, alvo.id)
            if jornada is None:
                jornada = self.repository.add_jornada(
                    db, UsuarioJornada(id=str(uuid4()), empresa_id=alvo.empresa_id, usuario_id=alvo.id, created_at=agora, updated_at=agora)
                )
                antes: dict[int, list[tuple[str, str]]] | None = None
                acao = "criada"
            else:
                antes = self._periodos_atuais(db, jornada)
                acao = "substituida"
            if antes is not None and {d: v for d, v in antes.items() if v} == novos:
                db.rollback()  # nada mudou: nenhuma escrita, nenhum evento
                return self._jornada_read(db, alvo, self.repository.get_jornada(db, alvo.id))
            linhas = [
                UsuarioJornadaPeriodo(
                    id=str(uuid4()),
                    jornada_id=jornada.id,
                    dia_semana=dia,
                    ordem=ordem,
                    inicio=time(int(inicio[:2]), int(inicio[3:5])),
                    fim=time(int(fim[:2]), int(fim[3:5])),
                )
                for dia, lista in sorted(novos.items())
                for ordem, (inicio, fim) in enumerate(lista, start=1)
            ]
            self.repository.replace_periodos(db, jornada.id, linhas)
            jornada.updated_at = agora
            db.add(jornada)
            self._publicar(
                db,
                DomainEventType.USUARIO_JORNADA_ALTERADA,
                actor,
                alvo,
                TIPO_ENTIDADE_JORNADA,
                jornada.id,
                {"acao": acao, "antes": None if antes is None else _grade_texto(antes), "depois": _grade_texto(novos)},
                agora,
            )
            db.commit()
            db.refresh(jornada)
            return self._jornada_read(db, alvo, jornada)
        except Exception:
            db.rollback()
            raise

    def remover_jornada(self, db: Session, actor: Usuario, usuario_id: str) -> JornadaRead:
        """"Usar expediente da empresa": remove a jornada personalizada (nada era copiado). Sem jornada = no-op idempotente (sem evento)."""
        try:
            alvo = self._alvo(db, actor, usuario_id, escrita=True)
            jornada = self.repository.get_jornada(db, alvo.id)
            if jornada is not None:
                antes = self._periodos_atuais(db, jornada)
                jornada_id = jornada.id
                self.repository.delete_jornada(db, jornada)
                self._publicar(
                    db, DomainEventType.USUARIO_JORNADA_REMOVIDA, actor, alvo, TIPO_ENTIDADE_JORNADA, jornada_id, {"antes": _grade_texto(antes), "depois": None}, agora_utc()
                )
            db.commit()
            return self._jornada_read(db, alvo, None)
        except Exception:
            db.rollback()
            raise

    # ------------------------------------------------------------------------------------------------------------------
    # Ausências
    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _ausencia_read(ausencia: UsuarioAusencia) -> AusenciaRead:
        return AusenciaRead(
            id=ausencia.id,
            usuarioId=ausencia.usuario_id,
            tipo=ausencia.tipo,
            inicio=ausencia.inicio,
            fim=ausencia.fim,
            observacao=ausencia.observacao,
            createdAt=ausencia.created_at,
            updatedAt=ausencia.updated_at,
        )

    @staticmethod
    def _resumo(ausencia: UsuarioAusencia) -> dict:
        """Essencial para auditoria — SEM a observação livre."""
        return {"tipo": ausencia.tipo, "inicio": ausencia.inicio.isoformat(), "fim": ausencia.fim.isoformat()}

    def listar_ausencias(self, db: Session, actor: Usuario, usuario_id: str, *, desde: date | None = None, ate: date | None = None) -> list[AusenciaRead]:
        alvo = self._alvo(db, actor, usuario_id, escrita=False)
        return [self._ausencia_read(a) for a in self.repository.list_ausencias(db, empresa_id=alvo.empresa_id, usuario_id=alvo.id, desde=desde, ate=ate)]

    def criar_ausencia(self, db: Session, actor: Usuario, usuario_id: str, data: AusenciaWrite) -> AusenciaRead:
        try:
            alvo = self._alvo(db, actor, usuario_id, escrita=True)
            agora = agora_utc()
            ausencia = self.repository.add_ausencia(
                db,
                UsuarioAusencia(
                    id=str(uuid4()),
                    empresa_id=alvo.empresa_id,
                    usuario_id=alvo.id,
                    tipo=data.tipo,
                    inicio=data.inicio,
                    fim=data.fim,
                    observacao=data.observacao,
                    created_at=agora,
                    updated_at=agora,
                ),
            )
            self._publicar(db, DomainEventType.USUARIO_AUSENCIA_CRIADA, actor, alvo, TIPO_ENTIDADE_AUSENCIA, ausencia.id, {"depois": self._resumo(ausencia)}, agora)
            db.commit()
            db.refresh(ausencia)
            return self._ausencia_read(ausencia)
        except Exception:
            db.rollback()
            raise

    def _ausencia_do_usuario(self, db: Session, alvo: Usuario, ausencia_id: str) -> UsuarioAusencia:
        ausencia = self.repository.get_ausencia(db, empresa_id=alvo.empresa_id, usuario_id=alvo.id, ausencia_id=ausencia_id)
        if ausencia is None:
            raise UsuarioCapacidadeNaoEncontradoError("Ausência não encontrada")
        return ausencia

    def editar_ausencia(self, db: Session, actor: Usuario, usuario_id: str, ausencia_id: str, data: AusenciaUpdate) -> AusenciaRead:
        try:
            alvo = self._alvo(db, actor, usuario_id, escrita=True)
            ausencia = self._ausencia_do_usuario(db, alvo, ausencia_id)
            antes = self._resumo(ausencia)
            enviados = data.model_fields_set
            novo_tipo = data.tipo if "tipo" in enviados and data.tipo is not None else ausencia.tipo
            novo_inicio = data.inicio if "inicio" in enviados and data.inicio is not None else ausencia.inicio
            novo_fim = data.fim if "fim" in enviados and data.fim is not None else ausencia.fim
            nova_observacao = data.observacao if "observacao" in enviados else ausencia.observacao
            if novo_fim < novo_inicio:
                raise CapacidadeInvalidaError("fim não pode ser anterior ao início")
            observacao_mudou = nova_observacao != ausencia.observacao
            if (novo_tipo, novo_inicio, novo_fim) == (ausencia.tipo, ausencia.inicio, ausencia.fim) and not observacao_mudou:
                db.rollback()
                return self._ausencia_read(ausencia)  # no-op: sem escrita nem evento
            ausencia.tipo, ausencia.inicio, ausencia.fim, ausencia.observacao = novo_tipo, novo_inicio, novo_fim, nova_observacao
            agora = agora_utc()
            ausencia.updated_at = agora
            db.add(ausencia)
            db.flush()
            self._publicar(
                db,
                DomainEventType.USUARIO_AUSENCIA_ALTERADA,
                actor,
                alvo,
                TIPO_ENTIDADE_AUSENCIA,
                ausencia.id,
                {"antes": antes, "depois": self._resumo(ausencia), "observacaoAlterada": observacao_mudou},
                agora,
            )
            db.commit()
            db.refresh(ausencia)
            return self._ausencia_read(ausencia)
        except Exception:
            db.rollback()
            raise

    def remover_ausencia(self, db: Session, actor: Usuario, usuario_id: str, ausencia_id: str) -> None:
        try:
            alvo = self._alvo(db, actor, usuario_id, escrita=True)
            ausencia = self._ausencia_do_usuario(db, alvo, ausencia_id)
            antes, ausencia_pk = self._resumo(ausencia), ausencia.id
            self.repository.delete_ausencia(db, ausencia)
            self._publicar(db, DomainEventType.USUARIO_AUSENCIA_REMOVIDA, actor, alvo, TIPO_ENTIDADE_AUSENCIA, ausencia_pk, {"antes": antes, "depois": None}, agora_utc())
            db.commit()
        except Exception:
            db.rollback()
            raise

    # ------------------------------------------------------------------------------------------------------------------
    # Evento (mesma transação)
    # ------------------------------------------------------------------------------------------------------------------

    def _publicar(
        self, db: Session, tipo: DomainEventType, actor: Usuario, alvo: Usuario, entidade_tipo: str, entidade_id: str, detalhe: dict, occurred_at: datetime
    ) -> None:
        self.event_publisher.publish(
            db,
            tipo=tipo,
            empresa_id=alvo.empresa_id,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            usuario_id=actor.id,
            payload={"empresa_id": alvo.empresa_id, "usuarioAfetadoId": alvo.id, "timestamp": occurred_at.isoformat(), **detalhe},
            occurred_at=occurred_at,
        )
