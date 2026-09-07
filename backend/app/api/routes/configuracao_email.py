"""Configuração administrativa de disparo SMTP — singleton por Empresa (Fase 2G.7B1).

Sem POST/DELETE/list/{id}: é singleton, não coleção — mesmo padrão de
app/api/routes/regra_expediente.py. `GET` é estritamente read-only (nunca cria a linha —
diferença deliberada em relação a RegraExpediente, ver ConfiguracaoEmailService.get_ou_default);
`PATCH` cria na primeira chamada e atualiza nas seguintes. `POST /testar` usa só a configuração
já salva — nunca aceita host/porta/usuário/senha no corpo (ver Fase 2G.7A, item 18).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.configuracao_email import (
    ConfiguracaoEmailRead,
    ConfiguracaoEmailTesteResultado,
    ConfiguracaoEmailUpdate,
)
from app.services.configuracao_email_crypto_service import (
    ChaveCriptografiaAusenteError,
    ChaveCriptografiaInvalidaError,
)
from app.services.configuracao_email_service import ConfiguracaoEmailService, ConfiguracaoEmailValidationError

router = APIRouter(
    prefix="/configuracoes/email",
    tags=["configuracoes-email"],
    dependencies=[Depends(get_current_user_password_ready)],
)
configuracao_email_service = ConfiguracaoEmailService()


def handle_configuracao_email_error(exc: Exception) -> None:
    if isinstance(exc, ConfiguracaoEmailValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, ChaveCriptografiaAusenteError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não é possível salvar a senha SMTP: chave de criptografia não configurada no servidor.",
        ) from exc
    if isinstance(exc, ChaveCriptografiaInvalidaError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não é possível salvar a senha SMTP: chave de criptografia configurada no servidor é inválida.",
        ) from exc
    raise exc


@router.get("", response_model=ConfiguracaoEmailRead)
def get_configuracao_email(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return configuracao_email_service.get_ou_default(db, empresa_id=current_user.empresa_id)


@router.patch("", response_model=ConfiguracaoEmailRead)
def update_configuracao_email(
    payload: ConfiguracaoEmailUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return configuracao_email_service.atualizar(
            db, payload, empresa_id=current_user.empresa_id, actor_usuario_id=current_user.id
        )
    except Exception as exc:
        handle_configuracao_email_error(exc)


@router.post("/testar", response_model=ConfiguracaoEmailTesteResultado)
def testar_configuracao_email(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    # Sempre 200: falha de SMTP é resultado esperado do teste, não um erro de API — ver Fase
    # 2G.7A, item 24. Sem body: usa SOMENTE a configuração já salva (item 18/19 do kickoff).
    return configuracao_email_service.testar_conexao(db, empresa_id=current_user.empresa_id)
