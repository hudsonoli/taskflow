from enum import StrEnum


class DomainEventType(StrEnum):
    EMPRESA_CRIADA = "empresa.criada"
    EMPRESA_ALTERADA = "empresa.alterada"
    EMPRESA_INATIVADA = "empresa.inativada"
    EMPRESA_REATIVADA = "empresa.reativada"

    AGENCIA_CRIADA = "agencia.criada"
    AGENCIA_ALTERADA = "agencia.alterada"
    AGENCIA_INATIVADA = "agencia.inativada"
    AGENCIA_REATIVADA = "agencia.reativada"

    USUARIO_CRIADO = "usuario.criado"
    USUARIO_ALTERADO = "usuario.alterado"
    USUARIO_INATIVADO = "usuario.inativado"
    USUARIO_REATIVADO = "usuario.reativado"
    USUARIO_BLOQUEADO = "usuario.bloqueado"
    USUARIO_DESBLOQUEADO = "usuario.desbloqueado"

    PROJETO_CRIADO = "projeto.criado"
    PROJETO_ATUALIZADO = "projeto.atualizado"
    PROJETO_STATUS_ALTERADO = "projeto.status_alterado"
    PROJETO_RESPONSAVEIS_ALTERADOS = "projeto.responsaveis_alterados"

    DEMANDA_CRIADA = "demanda.criada"
    DEMANDA_ATUALIZADA = "demanda.atualizada"
    DEMANDA_STATUS_ALTERADO = "demanda.status_alterado"
    DEMANDA_PRIORIDADE_ALTERADA = "demanda.prioridade_alterada"
    DEMANDA_RESPONSAVEIS_ALTERADOS = "demanda.responsaveis_alterados"

    WORKFLOW_TEMPLATE_APLICADO = "workflow.template_aplicado"
    WORKFLOW_ETAPA_ADICIONADA = "workflow.etapa_adicionada"
    WORKFLOW_ETAPA_REMOVIDA = "workflow.etapa_removida"
    WORKFLOW_ETAPA_ATUALIZADA = "workflow.etapa_atualizada"
    WORKFLOW_ETAPA_AVANCADA = "workflow.etapa_avancada"
    WORKFLOW_ETAPA_RETROCEDIDA = "workflow.etapa_retrocedida"
    WORKFLOW_ETAPA_BLOQUEADA = "workflow.etapa_bloqueada"
    WORKFLOW_ETAPA_DESBLOQUEADA = "workflow.etapa_desbloqueada"


EVENT_TYPES = frozenset(event_type.value for event_type in DomainEventType)
