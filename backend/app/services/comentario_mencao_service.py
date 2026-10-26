"""@menções de usuários em comentários de Demanda (V1: só comentários; só @usuário; só notificação interna).

Identidade é o `usuario_id` enviado pelo cliente — mas NUNCA confiado: o servidor revalida tudo antes de gravar e antes de notificar.

  - mesma empresa do ator (outro tenant é recusado com a mesma mensagem genérica de "inválido", sem confirmar que o usuário existe);
  - usuário `ativo`, com acesso ao sistema e que não seja conta de sistema (suspenso/inativo/arquivado não recebem nem aparecem no autocomplete);
  - o usuário PODE LER a Demanda (`pode_ler`, decidido pela rota com as mesmas regras de leitura do detalhe): a menção não fura o RBAC nem entrega uma tarefa que a pessoa não veria;
  - o rótulo `@Nome` está no texto: o id não é aceito "solto", então ninguém consegue notificar alguém sem que a menção apareça no comentário.

Notificação: UM evento `demanda.usuarios_mencionados` por ação (criar/editar), com os destinatários NOVOS em `destinatarioUsuarioIds` — o mesmo desenho da Fase 8C (etapa atual).
Os eventos já são a única fonte da central de notificações (sem tabela/sino/unread paralelos).

Deduplicação (`new_mentions = current − previous`): a linha (comentário, usuário) é única e só a inserção EFETIVA (`ON CONFLICT DO NOTHING … RETURNING`) notifica — editar sem pessoa nova não notifica,
adicionar uma pessoa notifica só a nova, e duas requisições idênticas concorrentes notificam uma vez. Mencionar a si mesmo é permitido (fica no texto) e nunca notifica. Remover a menção do texto
apaga a linha e preserva a notificação já entregue; mencionar de novo depois é uma menção nova e notifica de novo.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.relogio import agora_utc
from app.domain.event_types import DomainEventType
from app.models.demanda import Demanda
from app.models.demanda_comentario import DemandaComentario
from app.models.demanda_comentario_mencao import DemandaComentarioMencao
from app.models.usuario import Usuario
from app.services.domain_event_publisher import DomainEventPublisher

MAX_MENCOES_POR_COMENTARIO = 20
TAMANHO_PREVIA = 140
LIMITE_CANDIDATOS_AUTOCOMPLETE = 60  # quantos candidatos por nome o servidor examina (cada um passa pela checagem de leitura) até achar `limit` elegíveis

PodeLer = Callable[[Usuario], bool]


class MencaoInvalidaError(ValueError):
    """Usuário mencionado inexistente/de outra empresa/inativo/sem acesso à tarefa/sem o `@Nome` no texto — vira 422."""


def previa_do_texto(texto: str) -> str:
    limpo = " ".join(texto.split())
    return limpo if len(limpo) <= TAMANHO_PREVIA else limpo[: TAMANHO_PREVIA - 1].rstrip() + "…"


def rotulo_da_mencao(usuario: Usuario) -> str:
    """O texto que o autocomplete insere e que o servidor procura no comentário."""
    return f"@{usuario.nome}"


class ComentarioMencaoService:
    def __init__(self, event_publisher: DomainEventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or DomainEventPublisher()

    # ----------------------------------------------------------------------------------
    # Leitura
    # ----------------------------------------------------------------------------------

    def listar_por_comentarios(self, db: Session, comentario_ids: Sequence[str]) -> dict[str, list[tuple[str, str]]]:
        """`{comentario_id: [(usuario_id, nome)]}` numa única consulta (sem N+1)."""
        if not comentario_ids:
            return {}
        linhas = db.execute(
            select(DemandaComentarioMencao.comentario_id, Usuario.id, Usuario.nome)
            .join(Usuario, Usuario.id == DemandaComentarioMencao.usuario_id)
            .where(DemandaComentarioMencao.comentario_id.in_(list(comentario_ids)))
            .order_by(Usuario.nome)
        ).all()
        resultado: dict[str, list[tuple[str, str]]] = {}
        for comentario_id, usuario_id, nome in linhas:
            resultado.setdefault(comentario_id, []).append((usuario_id, nome))
        return resultado

    def buscar_mencionaveis(
        self, db: Session, *, empresa_id: str, autor_id: str, consulta: str, limite: int, pode_ler: PodeLer
    ) -> list[Usuario]:
        """Autocomplete: só usuários elegíveis (mesma empresa, ativos, com acesso, não-sistema, que PODEM ler a tarefa). Quem digita não aparece (menção a si mesmo não notifica)."""
        termo = consulta.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.status == "ativo",
            Usuario.acesso_sistema.is_(True),
            Usuario.is_system_account.is_(False),
            Usuario.id != autor_id,
        )
        if termo:
            statement = statement.where(Usuario.nome.ilike(f"%{termo}%", escape="\\"))
        candidatos = db.scalars(statement.order_by(Usuario.nome).limit(LIMITE_CANDIDATOS_AUTOCOMPLETE)).all()
        elegiveis: list[Usuario] = []
        for candidato in candidatos:
            if pode_ler(candidato):
                elegiveis.append(candidato)
                if len(elegiveis) >= limite:
                    break
        return elegiveis

    # ----------------------------------------------------------------------------------
    # Escrita (na MESMA transação do comentário; quem chama faz o commit)
    # ----------------------------------------------------------------------------------

    def sincronizar(
        self,
        db: Session,
        *,
        demanda: Demanda,
        comentario: DemandaComentario,
        autor: Usuario,
        usuario_ids: Sequence[str] | None,
        pode_ler: PodeLer | None,
    ) -> list[str]:
        """Alinha as menções do comentário com `usuario_ids` e devolve os destinatários NOVOS notificados. `None` = não mexer nas menções (cliente antigo / edição sem o campo)."""
        if usuario_ids is None:
            return []
        ids = list(dict.fromkeys(str(valor) for valor in usuario_ids))
        if len(ids) > MAX_MENCOES_POR_COMENTARIO:
            raise MencaoInvalidaError(f"No máximo {MAX_MENCOES_POR_COMENTARIO} pessoas por comentário.")

        anteriores = set(db.scalars(select(DemandaComentarioMencao.usuario_id).where(DemandaComentarioMencao.comentario_id == comentario.id)).all())
        novos = [valor for valor in ids if valor not in anteriores]
        texto_normalizado = comentario.texto.casefold()

        validos_novos: list[Usuario] = []
        if novos:
            if pode_ler is None:
                raise MencaoInvalidaError("Não foi possível validar as menções.")
            encontrados = {u.id: u for u in db.scalars(select(Usuario).where(Usuario.id.in_(novos), Usuario.empresa_id == demanda.empresa_id)).all()}
            for valor in novos:
                alvo = encontrados.get(valor)
                if alvo is None or alvo.status != "ativo" or not alvo.acesso_sistema or alvo.is_system_account:
                    raise MencaoInvalidaError("Usuário mencionado inválido ou sem acesso a esta tarefa.")
                if rotulo_da_mencao(alvo).casefold() not in texto_normalizado:
                    raise MencaoInvalidaError("A menção precisa aparecer no texto do comentário.")
                if alvo.id != autor.id and not pode_ler(alvo):
                    raise MencaoInvalidaError("Usuário mencionado inválido ou sem acesso a esta tarefa.")
                validos_novos.append(alvo)

        # Menções já gravadas cujo "@Nome" saiu do texto são removidas (o estado persistido segue o texto); as que continuam não são revalidadas (o usuário pode ter sido inativado depois).
        permanecem = {valor for valor in ids if valor in anteriores}
        if permanecem:
            nomes = {u.id: u for u in db.scalars(select(Usuario).where(Usuario.id.in_(permanecem))).all()}
            permanecem = {valor for valor in permanecem if valor in nomes and rotulo_da_mencao(nomes[valor]).casefold() in texto_normalizado}
        a_remover = anteriores - permanecem
        if a_remover:
            db.execute(delete(DemandaComentarioMencao).where(DemandaComentarioMencao.comentario_id == comentario.id, DemandaComentarioMencao.usuario_id.in_(a_remover)))

        inseridos: list[str] = []
        if validos_novos:
            agora = agora_utc()
            resultado = db.execute(
                pg_insert(DemandaComentarioMencao)
                .values([{"comentario_id": comentario.id, "usuario_id": alvo.id, "empresa_id": demanda.empresa_id, "created_at": agora} for alvo in validos_novos])
                .on_conflict_do_nothing(index_elements=["comentario_id", "usuario_id"])
                .returning(DemandaComentarioMencao.usuario_id)
            )
            inseridos = [linha[0] for linha in resultado.all()]

        destinatarios = [valor for valor in inseridos if valor != autor.id]
        if destinatarios:
            agora = agora_utc()
            self.event_publisher.publish(
                db,
                tipo=DomainEventType.DEMANDA_USUARIOS_MENCIONADOS,
                empresa_id=demanda.empresa_id,
                entidade_tipo="demanda",
                entidade_id=demanda.id,
                usuario_id=autor.id,
                payload={
                    "empresa_id": demanda.empresa_id,
                    "demanda_id": demanda.id,
                    "codigo_referencia": demanda.codigo_referencia,
                    "timestamp": agora.isoformat(),
                    "comentarioId": comentario.id,
                    "origem": "comentario",
                    "destinatarioUsuarioIds": destinatarios,
                    "previa": previa_do_texto(comentario.texto),
                },
                occurred_at=agora,
            )
        return destinatarios
