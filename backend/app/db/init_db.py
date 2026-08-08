"""Descontinuado: o schema agora é criado/evoluído exclusivamente via Alembic.

Rode `alembic upgrade head` (a partir de backend/) em vez de importar este módulo.
"""

raise RuntimeError("app.db.init_db foi descontinuado — use `alembic upgrade head` para criar/evoluir o schema.")
