from enum import StrEnum


class DomainEventType(StrEnum):
    EMPRESA_CRIADA = "empresa.criada"
    EMPRESA_ALTERADA = "empresa.alterada"
    EMPRESA_INATIVADA = "empresa.inativada"
    EMPRESA_REATIVADA = "empresa.reativada"

    USUARIO_CRIADO = "usuario.criado"
    USUARIO_ALTERADO = "usuario.alterado"
    USUARIO_INATIVADO = "usuario.inativado"
    USUARIO_REATIVADO = "usuario.reativado"
    USUARIO_BLOQUEADO = "usuario.bloqueado"
    USUARIO_DESBLOQUEADO = "usuario.desbloqueado"
    USUARIO_ARQUIVADO = "usuario.arquivado"
    USUARIO_RESTAURADO = "usuario.restaurado"

    GRUPO_CLIENTE_CRIADO = "grupo_cliente.criado"
    GRUPO_CLIENTE_ALTERADO = "grupo_cliente.alterado"
    GRUPO_CLIENTE_ARQUIVADO = "grupo_cliente.arquivado"
    GRUPO_CLIENTE_RESTAURADO = "grupo_cliente.restaurado"

    DEPARTAMENTO_CRIADO = "departamento.criado"
    DEPARTAMENTO_ALTERADO = "departamento.alterado"
    DEPARTAMENTO_ARQUIVADO = "departamento.arquivado"
    DEPARTAMENTO_RESTAURADO = "departamento.restaurado"

    EQUIPE_CRIADA = "equipe.criada"
    EQUIPE_ALTERADA = "equipe.alterada"
    EQUIPE_ARQUIVADA = "equipe.arquivada"
    EQUIPE_RESTAURADA = "equipe.restaurada"
    EQUIPE_MEMBRO_ADICIONADO = "equipe.membro_adicionado"
    EQUIPE_MEMBRO_REMOVIDO = "equipe.membro_removido"

    # Cliente não tem tabela de histórico: estes eventos SÃO o histórico.
    CLIENTE_CRIADO = "cliente.criado"
    CLIENTE_ALTERADO = "cliente.alterado"
    CLIENTE_ARQUIVADO = "cliente.arquivado"
    CLIENTE_RESTAURADO = "cliente.restaurado"
    CLIENTE_GRUPO_ADICIONADO = "cliente.grupo_adicionado"
    CLIENTE_GRUPO_REMOVIDO = "cliente.grupo_removido"

    # Fornecedor, como Cliente, não tem tabela de histórico: estes eventos SÃO o histórico.
    FORNECEDOR_CRIADO = "fornecedor.criado"
    FORNECEDOR_ALTERADO = "fornecedor.alterado"
    FORNECEDOR_ARQUIVADO = "fornecedor.arquivado"
    FORNECEDOR_RESTAURADO = "fornecedor.restaurado"

    # Projeto, como Cliente e Fornecedor, não tem tabela de histórico: estes eventos SÃO o
    # histórico (o mock tinha `historico[]` com usuário, ip e dispositivo — virou evento).
    PROJETO_CRIADO = "projeto.criado"
    PROJETO_ALTERADO = "projeto.alterado"
    PROJETO_ARQUIVADO = "projeto.arquivado"
    PROJETO_RESTAURADO = "projeto.restaurado"
    PROJETO_RESPONSAVEL_ADICIONADO = "projeto.responsavel_adicionado"
    PROJETO_RESPONSAVEL_REMOVIDO = "projeto.responsavel_removido"
    PROJETO_DEPARTAMENTO_ADICIONADO = "projeto.departamento_adicionado"
    PROJETO_DEPARTAMENTO_REMOVIDO = "projeto.departamento_removido"
    PROJETO_MEMBRO_ADICIONADO = "projeto.membro_adicionado"
    PROJETO_MEMBRO_REMOVIDO = "projeto.membro_removido"

    # Demanda não tem tabela de histórico: estes eventos SÃO o histórico. O campo
    # `historico[]` do mock, com ip e dispositivo, vira payload de evento.
    DEMANDA_CRIADA = "demanda.criada"
    DEMANDA_ALTERADA = "demanda.alterada"
    DEMANDA_STATUS_ALTERADO = "demanda.status_alterado"
    DEMANDA_BLOQUEADA = "demanda.bloqueada"
    DEMANDA_DESBLOQUEADA = "demanda.desbloqueada"
    DEMANDA_RESPONSAVEL_ADICIONADO = "demanda.responsavel_adicionado"
    DEMANDA_RESPONSAVEL_REMOVIDO = "demanda.responsavel_removido"
    DEMANDA_DEPARTAMENTO_ADICIONADO = "demanda.departamento_adicionado"
    DEMANDA_DEPARTAMENTO_REMOVIDO = "demanda.departamento_removido"
    DEMANDA_ARQUIVADA = "demanda.arquivada"
    DEMANDA_RESTAURADA = "demanda.restaurada"

    # Checklist e arquivos (Fase 2E.3) — mesma entidade_tipo/entidade_id da Demanda-mãe, para
    # que a futura tela de Histórico (2E.4) leia tudo com uma única consulta por Demanda.
    DEMANDA_CHECKLIST_ITEM_CRIADO = "demanda.checklist_item_criado"
    DEMANDA_CHECKLIST_ITEM_ALTERADO = "demanda.checklist_item_alterado"
    DEMANDA_CHECKLIST_ITEM_CONCLUIDO = "demanda.checklist_item_concluido"
    DEMANDA_CHECKLIST_ITEM_REABERTO = "demanda.checklist_item_reaberto"
    DEMANDA_CHECKLIST_ITEM_EXCLUIDO = "demanda.checklist_item_excluido"
    DEMANDA_ARQUIVO_ENVIADO = "demanda.arquivo_enviado"
    DEMANDA_ARQUIVO_REMOVIDO = "demanda.arquivo_removido"

    # Comentários (Fase 2E.4) — mesma entidade_tipo/entidade_id da Demanda-mãe.
    DEMANDA_COMENTARIO_CRIADO = "demanda.comentario_criado"
    DEMANDA_COMENTARIO_EDITADO = "demanda.comentario_editado"
    DEMANDA_COMENTARIO_REMOVIDO = "demanda.comentario_removido"

    # Completa a timeline com marcos que já existiam como campo/ação mas nunca viravam
    # evento (Fase 2E.4).
    DEMANDA_WORKFLOW_APLICADO = "demanda.workflow_aplicado"
    DEMANDA_AJUSTE_INTERNO_REGISTRADO = "demanda.ajuste_interno_registrado"
    DEMANDA_AJUSTE_CLIENTE_REGISTRADO = "demanda.ajuste_cliente_registrado"
    DEMANDA_REFACAO_REGISTRADA = "demanda.refacao_registrada"
    DEMANDA_EMAIL_CONCLUSAO_ENVIADO = "demanda.email_conclusao_enviado"
    DEMANDA_EMAIL_CONCLUSAO_DISPENSADO = "demanda.email_conclusao_dispensado"
    DEMANDA_RETORNO_CLIENTE_REGISTRADO = "demanda.retorno_cliente_registrado"

    # WorkflowModelo não tem tabela de histórico: estes eventos SÃO o histórico.
    WORKFLOW_MODELO_CRIADO = "workflow_modelo.criado"
    WORKFLOW_MODELO_ALTERADO = "workflow_modelo.alterado"
    WORKFLOW_MODELO_ARQUIVADO = "workflow_modelo.arquivado"
    WORKFLOW_MODELO_RESTAURADO = "workflow_modelo.restaurado"

    AUTH_LOGIN_SUCESSO = "auth.login_sucesso"
    AUTH_LOGIN_FALHA = "auth.login_falha"
    AUTH_SENHA_DEFINIDA = "auth.senha_definida"
    AUTH_SENHA_ALTERADA = "auth.senha_alterada"


EVENT_TYPES = frozenset(event_type.value for event_type in DomainEventType)
