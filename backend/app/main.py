from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    clientes,
    auth,
    demanda_arquivos,
    demanda_checklist,
    demandas,
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
    usuarios,
    workflow_modelos,
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

# Não há mais mount estático de /uploads (ver docs/pendencias-arquiteturais.md, item 9,
# resolvido na Fase 2E.3): conteúdo de arquivo de Demanda só é servido por
# demanda_arquivos.router, autenticado e escopado por Demanda.

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
app.include_router(demandas.router)
app.include_router(demanda_checklist.router)
app.include_router(demanda_arquivos.router)
app.include_router(departamentos.router)
app.include_router(equipes.router)
app.include_router(workflow_modelos.router)
app.include_router(auth.router)
