"""Configuração de Numeração de tarefas — leitura administrativa (Fase 2G.8B).

Só `GET`, sem query params: não existe forma de escolher outra Empresa, outro `tipo_entidade`
nem consultar/ajustar o contador. `empresa_id` vem exclusivamente de `current_user`. Não é
singleton editável (como `ConfiguracaoEmail`/`RegraExpediente`) — é um retrato somente-leitura
do estado real de `sequencias_operacionais`/`demandas`. Nenhuma escrita, nenhum Evento.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.models.usuario import Usuario
from app.schemas.configuracao_numeracao_tarefa import ConfiguracaoNumeracaoTarefaRead
from app.services.configuracao_numeracao_tarefa_service import ConfiguracaoNumeracaoTarefaService

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
