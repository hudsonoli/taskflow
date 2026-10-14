from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.expediente import (
    AvaliacaoExpediente,
    avaliar_expediente,
    sessao_encerrada_por_logout_automatico,
    usuario_sujeito_ao_expediente,
)
from app.db.session import get_db
from app.models.usuario import Usuario
from app.repositories.usuario_credencial_repository import UsuarioCredencialRepository
from app.services.auth_service import AuthService, AuthUnauthorizedError
from app.services.regra_expediente_service import RegraExpedienteService

bearer_scheme = HTTPBearer(auto_error=False)
auth_service = AuthService()
usuario_credencial_repository = UsuarioCredencialRepository()
regra_expediente_service = RegraExpedienteService()

CODIGO_FORA_DO_EXPEDIENTE = "FORA_DO_EXPEDIENTE"
MENSAGEM_FORA_DO_EXPEDIENTE = "Fora do horário de expediente"


def usuario_esta_sujeito_ao_expediente(usuario: Usuario) -> bool:
    """Ponto ÚNICO de decisão de quem a política de expediente alcança (acesso, trabalho e logout automático): só operador comum — ver
    `usuario_sujeito_ao_expediente`. Admin, gestor, conta de sistema e `acesso_fora_expediente=true` são isentos."""
    return usuario_sujeito_ao_expediente(
        perfil_base=usuario.perfil_base,
        is_system_account=bool(usuario.is_system_account),
        acesso_fora_expediente=bool(usuario.acesso_fora_expediente),
    )


def avaliar_expediente_do_usuario(db: Session, usuario: Usuario) -> AvaliacaoExpediente | None:
    """Avaliação do gate para o usuário AGORA (relógio do servidor, fuso da empresa). `None` = empresa sem regra → sem política."""
    regra = regra_expediente_service.get_regra_calculo_para_gate(db, empresa_id=usuario.empresa_id)
    if regra is None:
        return None
    return avaliar_expediente(None, regra=regra, sujeito=usuario_esta_sujeito_ao_expediente(usuario))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    try:
        usuario, claims = auth_service.autenticar_token(db, credentials.credentials)
    except AuthUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    # LOGOUT AUTOMÁTICO (Fase Expediente 2): token emitido ANTES do último corte deixa de valer — vale para qualquer aba/navegador/dispositivo, porque a decisão é do
    # servidor (claim `iat`), nunca do navegador. É 401 de propósito: o front trata como sessão encerrada e volta ao login da empresa. Independe do bloqueio de acesso:
    # um login NOVO depois do corte gera token novo e segue valendo.
    if usuario_esta_sujeito_ao_expediente(usuario):
        regra = regra_expediente_service.get_regra_calculo_para_gate(db, empresa_id=usuario.empresa_id)
        if regra is not None and sessao_encerrada_por_logout_automatico(claims["iat"], regra=regra):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão encerrada pelo logout automático")
    return usuario


def get_current_user_password_ready_sem_expediente(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Usuario:
    """Bloqueia o restante da aplicação enquanto a troca de senha obrigatória (senha
    temporária de seed/reset) não for concluída. Só /auth/me e /auth/alterar-senha ficam
    fora desse gate — o resto de /usuarios/* passa por aqui.

    NÃO aplica o gate de expediente: existe só para `GET /expediente/estado`, que precisa responder mesmo FORA da janela de acesso (é por ele que a interface descobre,
    pelo polling, que o acesso voltou). Todo o resto usa `get_current_user_password_ready`."""
    credencial = usuario_credencial_repository.get_by_usuario_id(db, current_user.id)
    if credencial is not None and credencial.senha_deve_ser_alterada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SENHA_TROCA_OBRIGATORIA", "message": "Troca de senha obrigatória"},
        )
    return current_user


def get_current_user_password_ready(
    current_user: Usuario = Depends(get_current_user_password_ready_sem_expediente),
    db: Session = Depends(get_db),
) -> Usuario:
    """Gate central de TODA a API tenant: senha em dia + (Fase Expediente 2) ACESSO dentro do expediente.

    `403 FORA_DO_EXPEDIENTE` só quando a empresa liga `bloquearForaExpediente`, a pessoa está sujeita à política e o instante (relógio do SERVIDOR, fuso da empresa) está
    fora da janela de ACESSO. É 403 — sessão válida, política recusa — e NUNCA 401 (o front mostra a tela "Fora do horário de expediente", não o login). Login,
    logout, recuperação de senha, primeiro acesso e `/auth/me` não passam por aqui, então a pessoa sempre consegue entrar e ser identificada (sem laço login→403→login)."""
    avaliacao = avaliar_expediente_do_usuario(db, current_user)
    if avaliacao is not None and not avaliacao.acesso_permitido:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detalhe_fora_do_expediente(avaliacao))
    return current_user


def detalhe_fora_do_expediente(avaliacao: AvaliacaoExpediente) -> dict:
    def iso(valor):
        return valor.isoformat() if valor is not None else None

    return {
        "code": CODIGO_FORA_DO_EXPEDIENTE,
        "message": MENSAGEM_FORA_DO_EXPEDIENTE,
        "proximoAcesso": iso(avaliacao.proximo_acesso),
        "proximoTrabalho": iso(avaliacao.proximo_trabalho),
        "proximoTrabalhoFim": iso(avaliacao.proximo_trabalho_fim),
        "timezone": avaliacao.timezone,
    }
