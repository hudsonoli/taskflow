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

    CARGO_CRIADO = "cargo.criado"
    CARGO_ALTERADO = "cargo.alterado"
    CARGO_INATIVADO = "cargo.inativado"
    CARGO_REATIVADO = "cargo.reativado"

    DEPARTAMENTO_CRIADO = "departamento.criado"
    DEPARTAMENTO_ALTERADO = "departamento.alterado"
    DEPARTAMENTO_INATIVADO = "departamento.inativado"
    DEPARTAMENTO_REATIVADO = "departamento.reativado"

    EQUIPE_CRIADA = "equipe.criada"
    EQUIPE_ALTERADA = "equipe.alterada"
    EQUIPE_INATIVADA = "equipe.inativada"
    EQUIPE_REATIVADA = "equipe.reativada"

    USUARIO_CRIADO = "usuario.criado"
    USUARIO_ALTERADO = "usuario.alterado"
    USUARIO_INATIVADO = "usuario.inativado"
    USUARIO_REATIVADO = "usuario.reativado"
    USUARIO_BLOQUEADO = "usuario.bloqueado"
    USUARIO_DESBLOQUEADO = "usuario.desbloqueado"

    USUARIO_DEPARTAMENTO_VINCULADO = "usuario_departamento.vinculado"
    USUARIO_DEPARTAMENTO_ALTERADO = "usuario_departamento.alterado"
    USUARIO_DEPARTAMENTO_ENCERRADO = "usuario_departamento.encerrado"

    USUARIO_CARGO_VINCULADO = "usuario_cargo.vinculado"
    USUARIO_CARGO_ALTERADO = "usuario_cargo.alterado"
    USUARIO_CARGO_ENCERRADO = "usuario_cargo.encerrado"

    USUARIO_EQUIPE_VINCULADO = "usuario_equipe.vinculado"
    USUARIO_EQUIPE_ALTERADO = "usuario_equipe.alterado"
    USUARIO_EQUIPE_ENCERRADO = "usuario_equipe.encerrado"

    AUTH_LOGIN_SUCESSO = "auth.login_sucesso"
    AUTH_LOGIN_FALHA = "auth.login_falha"
    AUTH_SENHA_DEFINIDA = "auth.senha_definida"
    AUTH_SENHA_ALTERADA = "auth.senha_alterada"

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
