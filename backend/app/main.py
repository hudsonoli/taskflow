from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    clientes,
    auth,
    departamentos,
    empresas,
    equipes,
    eventos,
    fornecedores,
    grupos_cliente,
    health,
    projetos,
    root,
    sessoes_trabalho,
    uploads,
    usuarios,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_ROOT = Path("uploads")
UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_ROOT), name="uploads")

app.include_router(root.router)
app.include_router(health.router)
app.include_router(eventos.router)
app.include_router(sessoes_trabalho.router)
app.include_router(empresas.router)
app.include_router(usuarios.router)
app.include_router(grupos_cliente.router)
app.include_router(clientes.router)
app.include_router(fornecedores.router)
app.include_router(projetos.router)
app.include_router(departamentos.router)
app.include_router(equipes.router)
app.include_router(auth.router)
app.include_router(uploads.router)
