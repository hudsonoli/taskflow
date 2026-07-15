from fastapi import FastAPI

from app.api.routes import agencias, auth, empresas, eventos, health, root, sessoes_trabalho, status, usuarios
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
app.include_router(auth.router)
