"""Primeiro acesso de usuários criados DENTRO da empresa (hotfix de onboarding).

O produto não tem convite nem envio de e-mail no onboarding (ver docs/administracao-plataforma.md): o primeiro acesso é por SENHA TEMPORÁRIA, igual ao Gestor
inicial criado pela Gestão. Antes deste serviço, `POST /usuarios` criava só a linha em `usuarios` — sem credencial, sem senha e sem convite — e o usuário
nunca conseguia entrar nem recuperar a conta (a recuperação só atende quem já tem credencial).

Regras: a senha é gerada no servidor (CSPRNG), só o HASH é persistido, `senha_deve_ser_alterada=True` (o servidor impõe a troca) e a senha em claro existe
apenas na resposta que a emitiu. Nada vai para log, evento ou campo do banco. Nenhuma operação aqui faz commit: a transação é de quem chama.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.autoridade_usuarios import ensure_nao_e_auto_administracao, ensure_pode_administrar_alvo
from app.core.security import gerar_senha_temporaria
from app.domain.event_types import DomainEventType
from app.models.usuario import Usuario
from app.services.auth_service import AuthService
from app.services.domain_event_publisher import DomainEventPublisher
from app.services.usuario_service import (
    STATUS_ATIVO,
    UsuarioInvalidTransitionError,
    UsuarioNotFoundError,
    UsuarioService,
    UsuarioSystemAccountProtegidoError,
)

MENSAGEM_NAO_ELEGIVEL = "Só um usuário ativo, com acesso ao sistema, pode receber uma senha temporária."
MENSAGEM_PRIMEIRO_ACESSO_CONCLUIDO = (
    'Este usuário já definiu a própria senha: use "Esqueci minha senha" na tela de login para recuperar a conta.'
)


class UsuarioAcessoService:
    def __init__(
        self,
        usuario_service: UsuarioService | None = None,
        auth_service: AuthService | None = None,
        event_publisher: DomainEventPublisher | None = None,
    ) -> None:
        self.usuario_service = usuario_service or UsuarioService()
        self.auth_service = auth_service or AuthService()
        self.event_publisher = event_publisher or DomainEventPublisher()

    def emitir_para_usuario_novo(self, db: Session, usuario: Usuario, *, actor_usuario_id: str | None) -> str | None:
        """Credencial inicial do usuário recém-criado (SEM commit; mesma transação da criação). Sem acesso ao sistema não há o que entregar: devolve `None`."""
        if not usuario.acesso_sistema:
            return None
        return self._emitir(db, usuario, actor_usuario_id=actor_usuario_id)

    def gerar_para_usuario_existente(self, db: Session, usuario_id: str, *, actor: Usuario) -> tuple[Usuario, str]:
        """Saída operacional para quem ficou SEM credencial (criado antes deste hotfix) ou perdeu a senha antes do primeiro acesso. SEM commit.

        Só enquanto o primeiro acesso está pendente (sem credencial, ou troca obrigatória ainda ligada): quem já definiu a própria senha usa "Esqueci minha senha".
        Hierarquia do RBAC (perfil do alvo) e nunca sobre si mesmo; outra empresa e inexistente respondem igual."""
        alvo = self.usuario_service.get_usuario(db, usuario_id)
        if alvo.empresa_id != actor.empresa_id:
            raise UsuarioNotFoundError("Usuário não encontrado")
        if alvo.is_system_account:
            raise UsuarioSystemAccountProtegidoError("Conta de sistema não recebe senha temporária")
        ensure_pode_administrar_alvo(actor.perfil_base, alvo.perfil_base)
        ensure_nao_e_auto_administracao(actor.id, alvo.id)
        if alvo.status != STATUS_ATIVO or not alvo.acesso_sistema:
            raise UsuarioInvalidTransitionError(MENSAGEM_NAO_ELEGIVEL)
        credencial = self.auth_service.credencial_repository.get_by_usuario_id(db, alvo.id)
        if credencial is not None and not credencial.senha_deve_ser_alterada:
            raise UsuarioInvalidTransitionError(MENSAGEM_PRIMEIRO_ACESSO_CONCLUIDO)
        return alvo, self._emitir(db, alvo, actor_usuario_id=actor.id)

    def _emitir(self, db: Session, usuario: Usuario, *, actor_usuario_id: str | None) -> str:
        senha = gerar_senha_temporaria()
        self.auth_service.aplicar_senha_temporaria(db, usuario, senha)
        self.event_publisher.publish(
            db,
            tipo=DomainEventType.USUARIO_SENHA_TEMPORARIA_GERADA,
            empresa_id=usuario.empresa_id,
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            usuario_id=actor_usuario_id,
            payload={"usuarioId": usuario.id},
        )
        return senha
