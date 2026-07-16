from fastapi import FastAPI

from app.api.routes import (
    agencias,
    auth,
    cargos,
    departamentos,
    equipes,
    empresas,
    eventos,
    health,
    root,
    sessoes_trabalho,
    status,
    usuario_cargos,
    usuario_departamentos,
    usuarios,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(root.router)
app.include_router(health.router)
app.include_router(status.router)
app.include_router(eventos.router)
app.include_router(sessoes_trabalho.router)
app.include_router(empresas.router)
app.include_router(usuarios.router)
app.include_router(agencias.router)
app.include_router(cargos.router)
app.include_router(departamentos.router)
app.include_router(equipes.router)
app.include_router(usuario_departamentos.router)
app.include_router(usuario_cargos.router)
app.include_router(auth.router)
