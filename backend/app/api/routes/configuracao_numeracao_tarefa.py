"""Configuração de Numeração de tarefas (Fase 2G.8B leitura → Fase 7D.1 configuração do formato futuro).

`GET` devolve o estado do contador + o formato das próximas emissões + a prévia (sem consumir número). `PATCH` altera SÓ o formato
das próximas emissões e/ou o próximo número; tarefas já emitidas mantêm o identificador gravado. `empresa_id` vem exclusivamente de
`current_user` (nunca de payload/query); autorização `require_admin_or_gestor` (a mesma do GET desde a 2G.8B).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.configuracao_numeracao_tarefa import ConfiguracaoNumeracaoTarefaRead, ConfiguracaoNumeracaoTarefaUpdate
from app.services.configuracao_numeracao_tarefa_service import (
    ConfiguracaoNumeracaoTarefaService,
    FormatoNumeracaoInvalidoError,
    ProximoNumeroInvalidoError,
)

router = APIRouter(
    prefix="/configuracoes/numeracao-tarefas",
    tags=["configuracoes-numeracao-tarefas"],
    dependencies=[Depends(get_current_user_password_ready)],
)
configuracao_numeracao_tarefa_service = ConfiguracaoNumeracaoTarefaService()


@router.get("", response_model=ConfiguracaoNumeracaoTarefaRead)
def get_configuracao_numeracao_tarefa(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    return configuracao_numeracao_tarefa_service.obter(db, empresa_id=current_user.empresa_id)


@router.patch("", response_model=ConfiguracaoNumeracaoTarefaRead)
def patch_configuracao_numeracao_tarefa(
    payload: ConfiguracaoNumeracaoTarefaUpdate,
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    try:
        return configuracao_numeracao_tarefa_service.atualizar(db, empresa_id=current_user.empresa_id, data=payload)
    except (FormatoNumeracaoInvalidoError, ProximoNumeroInvalidoError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
