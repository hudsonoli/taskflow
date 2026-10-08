"""Administração da PLATAFORMA (Fase 1B): empresas, branding por empresa e provisionamento de Gestor.

Nada aqui duplica regra de negócio: empresa → `EmpresaService`; branding → `ConfiguracaoPersonalizacaoService` (a mesma
validação de cores/tema/logo do tenant, só que com `empresa_id` explícito); usuário → `UsuarioService`; senha →
`AuthService.definir_senha_usuario`. A autoridade vem de `administradores_plataforma` (nunca de e-mail ou de
`perfil_base`) e é reconferida a cada requisição por `require_platform_admin`.

SEGUNDO_TENANT_GO_LIVE_BLOQUEADO: criar uma empresa e o Gestor dela já funciona por esta API, mas o login do produto
ainda resolve a empresa por `EMPRESA_CODIGO` (variável do servidor Next), então os usuários de uma segunda empresa NÃO
conseguem entrar. A resolução multiempresa (slug/branding no login, reset, Google) é a Fase 2 — nada de atalho aqui.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import create_platform_token
from app.domain.event_types import DomainEventType
from app.models.administrador_plataforma import AdministradorPlataforma
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.repositories.administrador_plataforma_repository import AdministradorPlataformaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.configuracao_personalizacao import PersonalizacaoRead, PersonalizacaoUpdate
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate
from app.schemas.plataforma import (
    PlataformaEmpresaRead,
    PlataformaGestorCreate,
    PlataformaGestorCriadoRead,
    PlataformaMeRead,
    PlataformaSessaoRead,
    PlataformaUsuarioRead,
)
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.services.auth_service import AuthService
from app.services.configuracao_personalizacao_service import ConfiguracaoPersonalizacaoService
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.empresa_service import EmpresaService
from app.services.usuario_service import UsuarioService

# Sem caracteres ambíguos (0/O, 1/l/I): a senha temporária é lida e digitada por uma pessoa.
_ALFABETO_SENHA = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_TAMANHO_SENHA = 14


class PlataformaAcessoNegadoError(PermissionError):
    pass


class PlataformaUsuarioNaoEncontradoError(LookupError):
    """Usuário inexistente NESTA empresa (outra empresa, conta de sistema e arquivado respondem igual: não revela nada)."""


class PlataformaUsuarioNaoElegivelError(ValueError):
    """O usuário existe nesta empresa, mas não pode ser promovido a Gestor (já é Gestor, é admin legado, está
    inativo/bloqueado ou sem acesso ao sistema)."""


class PlataformaGestorSenhaError(RuntimeError):
    """O Gestor foi criado, mas a senha temporária não pôde ser definida (a transação de usuário já tinha commitado)."""


def gerar_senha_temporaria() -> str:
    """CSPRNG (`secrets`), 14 caracteres de um alfabeto legível. Nunca é registrada em log nem em evento."""
    return "".join(secrets.choice(_ALFABETO_SENHA) for _ in range(_TAMANHO_SENHA))


class PlataformaService:
    def __init__(
        self,
        empresa_service: EmpresaService | None = None,
        usuario_service: UsuarioService | None = None,
        auth_service: AuthService | None = None,
        personalizacao_service: ConfiguracaoPersonalizacaoService | None = None,
        administrador_repository: AdministradorPlataformaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        event_publisher: DomainEventPublisher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.empresa_service = empresa_service or EmpresaService()
        self.usuario_service = usuario_service or UsuarioService()
        self.auth_service = auth_service or AuthService()
        self.personalizacao_service = personalizacao_service or ConfiguracaoPersonalizacaoService()
        self.administrador_repository = administrador_repository or AdministradorPlataformaRepository()
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.event_publisher = event_publisher or DomainEventPublisher()
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------------------------
    # Autoridade / sessão
    # ------------------------------------------------------------------------------------

    def administrador_ativo_de(self, db: Session, usuario: Usuario) -> AdministradorPlataforma | None:
        administrador = self.administrador_repository.get_by_usuario_id(db, usuario.id)
        return administrador if administrador is not None and administrador.ativo else None

    def emitir_sessao(self, db: Session, usuario: Usuario) -> PlataformaSessaoRead:
        """O usuário TENANT logado (token `access` válido) troca por um token de plataforma — só se a linha ativa existir."""
        administrador = self.administrador_ativo_de(db, usuario)
        if administrador is None:
            raise PlataformaAcessoNegadoError("Acesso negado")
        token = create_platform_token(sub=usuario.id, administrador_id=administrador.id, settings=self.settings)
        return PlataformaSessaoRead(accessToken=token, expiresIn=self.settings.platform_token_expire_minutes * 60)

    @staticmethod
    def me(administrador: AdministradorPlataforma, usuario: Usuario) -> PlataformaMeRead:
        return PlataformaMeRead(
            administradorId=administrador.id,
            usuarioId=usuario.id,
            nome=usuario.nome,
            ativo=administrador.ativo,
            criadoEm=administrador.criado_em,
        )

    # ------------------------------------------------------------------------------------
    # Empresas
    # ------------------------------------------------------------------------------------

    def _read(self, db: Session, empresas: list[Empresa]) -> list[PlataformaEmpresaRead]:
        ids = [empresa.id for empresa in empresas]
        gestores = self.administrador_repository.gestores_ativos_por_empresa(db, ids)
        hospedam = self.administrador_repository.empresas_que_hospedam_administrador_ativo(db, ids)
        resultado: list[PlataformaEmpresaRead] = []
        for empresa in empresas:
            base = self.empresa_service.to_read(empresa).model_dump(by_alias=True)
            resultado.append(
                PlataformaEmpresaRead(
                    **base,
                    gestoresAtivos=gestores.get(empresa.id, 0),
                    hospedaAdministradorPlataforma=empresa.id in hospedam,
                )
            )
        return resultado

    def listar_empresas(
        self, db: Session, *, status: str | None, search: str | None, limit: int, offset: int
    ) -> list[PlataformaEmpresaRead]:
        statement = select(Empresa)
        if status:
            statement = statement.where(Empresa.status == status)
        if search and search.strip():
            termo = f"%{search.strip().lower()}%"
            statement = statement.where(
                or_(
                    Empresa.nome.ilike(termo),
                    Empresa.nome_fantasia.ilike(termo),
                    Empresa.slug.ilike(termo),
                    Empresa.codigo_interno.ilike(termo),
                )
            )
        statement = statement.order_by(Empresa.created_at.desc(), Empresa.nome.asc()).limit(limit).offset(offset)
        return self._read(db, list(db.scalars(statement).all()))

    def obter_empresa(self, db: Session, empresa_id: str) -> PlataformaEmpresaRead:
        return self._read(db, [self.empresa_service.get_empresa(db, empresa_id)])[0]

    def criar_empresa(self, db: Session, data: EmpresaCreate, *, ator: Usuario) -> PlataformaEmpresaRead:
        empresa = self.empresa_service.create_empresa(db, data, actor_usuario_id=ator.id)
        return self._read(db, [empresa])[0]

    def atualizar_empresa(self, db: Session, empresa_id: str, data: EmpresaUpdate, *, ator: Usuario) -> PlataformaEmpresaRead:
        empresa = self.empresa_service.update_empresa(db, empresa_id, data, actor_usuario_id=ator.id)
        return self._read(db, [empresa])[0]

    def inativar_empresa(self, db: Session, empresa_id: str, *, motivo: str | None, ator: Usuario) -> PlataformaEmpresaRead:
        empresa = self.empresa_service.inativar_empresa(
            db, empresa_id, motivo_inativacao=motivo, actor_usuario_id=ator.id
        )
        return self._read(db, [empresa])[0]

    def reativar_empresa(self, db: Session, empresa_id: str, *, ator: Usuario) -> PlataformaEmpresaRead:
        empresa = self.empresa_service.reativar_empresa(db, empresa_id, actor_usuario_id=ator.id)
        return self._read(db, [empresa])[0]

    # ------------------------------------------------------------------------------------
    # Branding por empresa (mesmo serviço, mesma validação, `empresa_id` explícito)
    # ------------------------------------------------------------------------------------

    def obter_personalizacao(self, db: Session, empresa_id: str) -> PersonalizacaoRead:
        self.empresa_service.get_empresa(db, empresa_id)
        return self.personalizacao_service.get_ou_default(db, empresa_id=empresa_id)

    def atualizar_personalizacao(self, db: Session, empresa_id: str, payload: PersonalizacaoUpdate, *, ator: Usuario) -> PersonalizacaoRead:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        resultado = self.personalizacao_service.atualizar(db, empresa_id=empresa.id, payload=payload)
        self._auditar_personalizacao(db, empresa, ator, "cores_tema", sorted(payload.model_dump(exclude_unset=True, by_alias=True)))
        return resultado

    def restaurar_personalizacao(self, db: Session, empresa_id: str, *, ator: Usuario) -> PersonalizacaoRead:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        resultado = self.personalizacao_service.restaurar_padrao(db, empresa_id=empresa.id)
        self._auditar_personalizacao(db, empresa, ator, "restaurar_padrao", [])
        return resultado

    def ler_logo(self, db: Session, empresa_id: str) -> tuple[str, str, str]:
        """(caminho, mime, versão) do logo da empresa — mesma leitura/validação do endpoint público do tenant."""
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        return self.personalizacao_service.ler_logo_publico(db, empresa_codigo=empresa.codigo_interno)

    def enviar_logo(
        self, db: Session, empresa_id: str, *, conteudo: bytes, nome_arquivo: str | None, content_type: str | None, ator: Usuario
    ) -> PersonalizacaoRead:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        resultado = self.personalizacao_service.salvar_logo(
            db, empresa_id=empresa.id, conteudo=conteudo, nome_arquivo=nome_arquivo, content_type=content_type
        )
        self._auditar_personalizacao(db, empresa, ator, "logo_enviado", [])
        return resultado

    def remover_logo(self, db: Session, empresa_id: str, *, ator: Usuario) -> PersonalizacaoRead:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        resultado = self.personalizacao_service.remover_logo(db, empresa_id=empresa.id)
        self._auditar_personalizacao(db, empresa, ator, "logo_removido", [])
        return resultado

    def _auditar_personalizacao(self, db: Session, empresa: Empresa, ator: Usuario, acao: str, campos: list[str]) -> None:
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.EMPRESA_PERSONALIZACAO_ALTERADA,
            empresa_id=empresa.id,
            entidade_tipo="empresa",
            entidade_id=empresa.id,
            usuario_id=ator.id,
            payload={"acao": acao, "campos": campos, "nome": empresa.nome},
        )
        db.commit()

    # ------------------------------------------------------------------------------------
    # Usuários da empresa (só metadados) e primeiro Gestor
    # ------------------------------------------------------------------------------------

    @staticmethod
    def _usuario_read(usuario: Usuario) -> PlataformaUsuarioRead:
        return PlataformaUsuarioRead(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            perfilBase=usuario.perfil_base,
            status=usuario.status,
            acessoSistema=usuario.acesso_sistema,
            createdAt=usuario.created_at,
        )

    def listar_usuarios(
        self, db: Session, empresa_id: str, *, search: str | None, limit: int, offset: int
    ) -> list[PlataformaUsuarioRead]:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        # `UsuarioRepository.list` já exclui a conta de sistema (incondicional) e arquivados.
        usuarios = self.usuario_repository.list(db, empresa_id=empresa.id, search=search, limit=limit, offset=offset)
        return [self._usuario_read(usuario) for usuario in usuarios]

    # ------------------------------------------------------------------------------------
    # Gestor a partir de um Usuário EXISTENTE da própria empresa
    # ------------------------------------------------------------------------------------

    @staticmethod
    def _elegivel_para_gestor(usuario: Usuario) -> bool:
        """Candidato = Usuário (`operador`) ATIVO e com acesso ao sistema, que não é conta de sistema. Inativo,
        bloqueado ou sem acesso NÃO é oferecido: promover não reativa ninguém (a reativação é uma ação explícita à parte)."""
        return (
            usuario.perfil_base == "operador"
            and usuario.status == "ativo"
            and bool(usuario.acesso_sistema)
            and not usuario.is_system_account
        )

    def listar_candidatos_gestor(self, db: Session, empresa_id: str) -> list[PlataformaUsuarioRead]:
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        usuarios = self.usuario_repository.list(
            db, empresa_id=empresa.id, status="ativo", perfil_base="operador", search=None, limit=200, offset=0
        )
        return [self._usuario_read(u) for u in usuarios if self._elegivel_para_gestor(u)]

    def promover_gestor(self, db: Session, empresa_id: str, usuario_id: str, *, ator: Usuario) -> PlataformaUsuarioRead:
        """Promove um Usuário JÁ existente da empresa a Gestor. Mesmo registro (id, credencial, histórico e exceções
        individuais de permissão intactos); nenhuma senha é gerada ou alterada. Reaproveita `UsuarioService.update_usuario`
        (mesmas validações do projeto) e registra um evento de plataforma próprio."""
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        usuario = self.usuario_repository.get_by_id(db, usuario_id)
        # outra empresa, inexistente, conta de sistema ou arquivado: a MESMA resposta (nunca promove cross-tenant)
        if usuario is None or usuario.empresa_id != empresa.id or usuario.is_system_account or usuario.status == "arquivado":
            raise PlataformaUsuarioNaoEncontradoError("Usuário não encontrado nesta empresa")
        if usuario.perfil_base == "gestor":
            raise PlataformaUsuarioNaoElegivelError("Este usuário já é Gestor.")
        if not self._elegivel_para_gestor(usuario):
            raise PlataformaUsuarioNaoElegivelError(
                "Só um Usuário ativo, com acesso ao sistema, pode ser promovido a Gestor."
            )

        atualizado = self.usuario_service.update_usuario(
            db, usuario.id, UsuarioUpdate(perfilBase="gestor"), actor_usuario_id=ator.id
        )
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.EMPRESA_GESTOR_PROMOVIDO,
            empresa_id=empresa.id,
            entidade_tipo="empresa",
            entidade_id=empresa.id,
            usuario_id=ator.id,
            payload={"usuarioId": atualizado.id, "perfilAnterior": "operador", "nome": empresa.nome},
        )
        db.commit()
        return self._usuario_read(atualizado)

    def criar_gestor(
        self, db: Session, empresa_id: str, data: PlataformaGestorCreate, *, ator: Usuario
    ) -> PlataformaGestorCriadoRead:
        """Cria um Gestor para a empresa — SEMPRE `gestor` (nunca `admin`), só nesta empresa, com troca de senha
        obrigatória. A senha temporária sai só na resposta."""
        empresa = self.empresa_service.get_empresa(db, empresa_id)
        gestores_antes = self.administrador_repository.gestores_ativos_por_empresa(db, [empresa.id]).get(empresa.id, 0)

        usuario = self.usuario_service.create_usuario(
            db,
            UsuarioCreate(
                empresaId=empresa.id, nome=data.nome, email=data.email, perfilBase="gestor", acessoSistema=True
            ),
            actor_usuario_id=ator.id,
        )

        senha = gerar_senha_temporaria()
        try:
            self.auth_service.definir_senha_usuario(
                db,
                empresa_codigo=empresa.codigo_interno,
                email=usuario.email,
                senha=senha,
                actor_usuario_id=ator.id,
                deve_alterar_senha=True,
            )
        except Exception as exc:  # o Gestor existe; a senha não — nunca devolve uma senha que não foi gravada
            raise PlataformaGestorSenhaError(
                "O Gestor foi criado, mas não foi possível definir a senha temporária. "
                "Defina a senha pelo CLI de administração (definir_senha_usuario)."
            ) from exc

        self.event_publisher.publish(
            db,
            tipo=DomainEventType.EMPRESA_GESTOR_CRIADO,
            empresa_id=empresa.id,
            entidade_tipo="empresa",
            entidade_id=empresa.id,
            usuario_id=ator.id,
            payload={"usuarioId": usuario.id, "primeiroGestor": gestores_antes == 0, "nome": empresa.nome},
        )
        db.commit()
        return PlataformaGestorCriadoRead(usuario=self._usuario_read(usuario), senhaTemporaria=senha)

    # ------------------------------------------------------------------------------------
    # Bootstrap (CLI) — o ÚNICO lugar onde um e-mail localiza a autoridade
    # ------------------------------------------------------------------------------------

    def conceder_autoridade(self, db: Session, usuario: Usuario, *, criado_por_usuario_id: str | None = None) -> tuple[AdministradorPlataforma, str]:
        """Cria ou reativa a linha. Idempotente. Devolve (linha, resultado) com resultado em {criada, reativada, ja_ativa}."""
        agora = datetime.now(timezone.utc)
        existente = self.administrador_repository.get_by_usuario_id(db, usuario.id)
        if existente is None:
            linha = AdministradorPlataforma(
                id=str(uuid4()), usuario_id=usuario.id, ativo=True, criado_em=agora, criado_por_usuario_id=criado_por_usuario_id
            )
            self.administrador_repository.create(db, linha)
            db.commit()
            return linha, "criada"
        if existente.ativo:
            return existente, "ja_ativa"
        existente.ativo = True
        existente.revogado_em = None
        existente.revogado_por_usuario_id = None
        self.administrador_repository.update(db, existente)
        db.commit()
        return existente, "reativada"

    def revogar_autoridade(self, db: Session, administrador: AdministradorPlataforma, *, revogado_por_usuario_id: str | None = None) -> None:
        administrador.ativo = False
        administrador.revogado_em = datetime.now(timezone.utc)
        administrador.revogado_por_usuario_id = revogado_por_usuario_id
        self.administrador_repository.update(db, administrador)
        db.commit()
