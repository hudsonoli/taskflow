"""Registro central dos models.

Importar **todos** aqui é o que garante que o registry declarativo do SQLAlchemy esteja
completo assim que qualquer model for carregado. Sem isto, um módulo que importa só
`Usuario` quebra ao resolver a ForeignKey `usuarios.departamento_id -> departamentos.id`:

    NoReferencedTableError: Foreign key associated with column 'usuarios.departamento_id'
    could not find table 'departamentos'

Esse erro apareceu de verdade ao reconstruir um banco vazio — `app.main` funcionava porque
importa todos os routers (que acabam importando todos os models por tabela), mas os seeds
importam um subconjunto e quebravam. A aplicação parecia sã e o fluxo de reconstrução não
estava.

Ao criar um model novo, acrescentar aqui **e** em `migrations/env.py`.
"""

from app.models import (  # noqa: F401
    cliente,
    cliente_grupo,
    departamento,
    empresa,
    equipe,
    equipe_membro,
    evento,
    fornecedor,
    grupo_cliente,
    projeto,
    projeto_departamento,
    projeto_equipe_membro,
    projeto_responsavel,
    sequencia_referencia,
    sessao_trabalho,
    usuario,
    usuario_credencial,
)
