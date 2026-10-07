from __future__ import annotations

import unicodedata

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.usuario import Usuario

STATUS_ARQUIVADO = "arquivado"
STATUS_ATIVO = "ativo"
SITUACAO_ATIVO = "ativo"
SITUACAO_INATIVO = "inativo"
# Perfis que a tela de Usuários conta como "Gestão" (mesma lista do card do frontend).
PERFIS_GESTAO = ("gestor", "admin", "superadmin", "diretoria")

# Busca sem acento no próprio SQL (sem extensão `unaccent`, que exigiria migration): minúsculas +
# `translate` dos caracteres acentuados mais comuns. O termo é dobrado em Python do mesmo jeito.
_COM_ACENTO = "áàâãäåéèêëíìîïóòôõöúùûüýÿçñ"
_SEM_ACENTO = "aaaaaaeeeeiiiiooooouuuuyycn"


def _dobrar_coluna(coluna):
    return func.translate(func.lower(coluna), _COM_ACENTO, _SEM_ACENTO)


def _dobrar_termo(termo: str) -> str:
    decomposto = unicodedata.normalize("NFD", termo.strip().lower())
    return "".join(ch for ch in decomposto if unicodedata.category(ch) != "Mn")


def _escapar_like(termo: str) -> str:
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UsuarioRepository:
    def create(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario

    def get_by_id(self, db: Session, usuario_id: str) -> Usuario | None:
        """Busca irrestrita — usada internamente por login/`/auth/me`/`/usuarios/me`, onde a
        conta de sistema também precisa conseguir se autenticar e ver o próprio perfil."""
        return db.get(Usuario, usuario_id)

    def get_by_id_visible(self, db: Session, usuario_id: str) -> Usuario | None:
        """Busca administrativa (GET /usuarios/{id}) — nunca devolve a conta de sistema,
        mesmo que o chamador saiba o ID exatamente."""
        usuario = db.get(Usuario, usuario_id)
        if usuario is not None and usuario.is_system_account:
            return None
        return usuario

    def get_by_codigo_interno(self, db: Session, *, empresa_id: str, codigo_interno: str) -> Usuario | None:
        statement = select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.codigo_interno == codigo_interno,
        )
        return db.scalars(statement).first()

    def get_by_email(self, db: Session, *, empresa_id: str, email: str) -> Usuario | None:
        statement = select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.email == email,
        )
        return db.scalars(statement).first()

    def get_by_google_sub(self, db: Session, google_sub: str) -> Usuario | None:
        """Busca global (sem filtro de empresa) — `google_sub` é único no mundo todo, ver
        migration 0035. O chamador (AuthService.login_google) ainda confirma a empresa do
        usuário encontrado bate com a de `empresaCodigo` antes de autenticar."""
        statement = select(Usuario).where(Usuario.google_sub == google_sub)
        return db.scalars(statement).first()

    def list(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        perfil_base: str | None = None,
        search: str | None = None,
        departamento_id: str | None = None,
        situacao: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        # A conta de sistema nunca aparece aqui — incondicional, sem parâmetro pra religar.
        statement = select(Usuario).where(Usuario.empresa_id == empresa_id, Usuario.is_system_account.is_(False))

        if status:
            statement = statement.where(Usuario.status == status)
        else:
            # Sem status explícito, arquivado fica oculto por padrão — filtro SQL, antes da
            # paginação (ver docs/padrao-arquivamento.md). `status="arquivado"` explícito
            # continua consultando normalmente.
            statement = statement.where(Usuario.status != STATUS_ARQUIVADO)
        if situacao == SITUACAO_ATIVO:
            statement = statement.where(Usuario.status == STATUS_ATIVO)
        elif situacao == SITUACAO_INATIVO:
            # "Inativos" da tela de Usuários = tudo que NÃO é ativo (inativo + bloqueado; arquivado
            # já está oculto acima, salvo `status="arquivado"` explícito).
            statement = statement.where(Usuario.status != STATUS_ATIVO)
        if perfil_base:
            statement = statement.where(Usuario.perfil_base == perfil_base)
        if departamento_id:
            statement = statement.where(Usuario.departamento_id == departamento_id)
        if search and search.strip():
            padrao = f"%{_escapar_like(_dobrar_termo(search))}%"
            # Mesma busca da tela de Usuários: sem acento e sem diferenciar maiúsculas, em nome,
            # e-mail, código interno e NOME DO DEPARTAMENTO (subconsulta da mesma empresa — sem JOIN
            # que duplique linha nem N+1).
            por_departamento = Usuario.departamento_id.in_(
                select(Departamento.id).where(
                    Departamento.empresa_id == empresa_id,
                    _dobrar_coluna(Departamento.nome).like(padrao, escape="\\"),
                )
            )
            statement = statement.where(
                or_(
                    _dobrar_coluna(Usuario.nome).like(padrao, escape="\\"),
                    _dobrar_coluna(Usuario.email).like(padrao, escape="\\"),
                    _dobrar_coluna(Usuario.codigo_interno).like(padrao, escape="\\"),
                    por_departamento,
                )
            )

        # `id` no fim: desempate estável, para a paginação (offset) nunca repetir/pular linha.
        statement = statement.order_by(Usuario.created_at.desc(), Usuario.nome.asc(), Usuario.id.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def resumo(self, db: Session, *, empresa_id: str) -> dict[str, int]:
        """Agregados dos cards da tela de Usuários — UMA query, sempre sobre a empresa inteira
        (nunca sobre filtros/página): mesma base de `list()` sem `status` (sem conta de sistema,
        sem arquivado). `gestao` = perfis de gestão; `departamentos` = distintos com vínculo."""
        linha = db.execute(
            select(
                func.count(Usuario.id),
                func.count(Usuario.id).filter(Usuario.status == STATUS_ATIVO),
                func.count(Usuario.id).filter(Usuario.perfil_base.in_(PERFIS_GESTAO)),
                func.count(func.distinct(Usuario.departamento_id)),
            ).where(
                Usuario.empresa_id == empresa_id,
                Usuario.is_system_account.is_(False),
                Usuario.status != STATUS_ARQUIVADO,
            )
        ).one()
        return {"total": linha[0], "ativos": linha[1], "gestao": linha[2], "departamentos": linha[3]}

    def contar_gestores_ativos(self, db: Session, *, empresa_id: str, exceto_id: str | None = None) -> int:
        """Gestores que ainda conseguem administrar a empresa: `perfil_base="gestor"`, `ativo` e com
        `acesso_sistema`. Base da regra "a empresa nunca fica sem Gestor ativo por uma operação
        administrativa normal" (UsuarioService). Nunca conta conta de sistema; `exceto_id` tira o alvo
        da operação da conta."""
        condicoes = [
            Usuario.empresa_id == empresa_id,
            Usuario.perfil_base == "gestor",
            Usuario.status == STATUS_ATIVO,
            Usuario.acesso_sistema.is_(True),
            Usuario.is_system_account.is_(False),
        ]
        if exceto_id is not None:
            condicoes.append(Usuario.id != exceto_id)
        return int(db.scalar(select(func.count(Usuario.id)).where(*condicoes)) or 0)

    def list_diretorio(
        self,
        db: Session,
        *,
        empresa_id: str,
        status: str | None = None,
        departamento_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Usuario]:
        # Projeção mínima pra seletores de responsável/membro — mesma exclusão incondicional
        # da conta de sistema que list().
        statement = select(Usuario).where(Usuario.empresa_id == empresa_id, Usuario.is_system_account.is_(False))

        if status:
            # Sem exclusão de arquivado aqui: status explícito (inclusive "arquivado") é
            # filtro exato, igual antes.
            statement = statement.where(Usuario.status == status)
        # Sem status explícito: inclui TODOS os status (ativo/inativo/bloqueado/arquivado) —
        # referências históricas (responsável de cliente/departamento, membro de equipe,
        # autor de evento etc.) precisam continuar resolvendo nome/avatar mesmo após o
        # usuário ser arquivado (ver docs/padrao-arquivamento.md e R1). Quem monta opções de
        # NOVA seleção filtra "ativo" no cliente — mesmo padrão já usado por
        # clientes/projetos/departamentos/grupos_cliente diretorio.
        if departamento_id:
            statement = statement.where(Usuario.departamento_id == departamento_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(Usuario.nome.ilike(term))

        statement = statement.order_by(Usuario.nome.asc())
        statement = statement.limit(limit).offset(offset)

        return list(db.scalars(statement).all())

    def list_diretorio_por_ids(self, db: Session, *, empresa_id: str, ids: list[str]) -> list[Usuario]:
        # Resolução em lote id -> projeção de diretório: UMA query, escopo de empresa e exclusão
        # da conta de sistema idênticos a list_diretorio. Sem filtro de status (quem já é
        # referenciado pode estar inativo/bloqueado/arquivado). Id inexistente ou de outra
        # empresa simplesmente não volta. Ordem determinística (nome, id).
        if not ids:
            return []
        statement = (
            select(Usuario)
            .where(
                Usuario.empresa_id == empresa_id,
                Usuario.is_system_account.is_(False),
                Usuario.id.in_(ids),
            )
            .order_by(Usuario.nome.asc(), Usuario.id.asc())
        )
        return list(db.scalars(statement).all())

    def update(self, db: Session, usuario: Usuario) -> Usuario:
        db.add(usuario)
        db.flush()
        return usuario
