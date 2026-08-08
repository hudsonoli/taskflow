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

    AUTH_LOGIN_SUCESSO = "auth.login_sucesso"
    AUTH_LOGIN_FALHA = "auth.login_falha"
    AUTH_SENHA_DEFINIDA = "auth.senha_definida"
    AUTH_SENHA_ALTERADA = "auth.senha_alterada"


EVENT_TYPES = frozenset(event_type.value for event_type in DomainEventType)
