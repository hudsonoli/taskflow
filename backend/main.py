import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text
import redis

app = FastAPI(title="Taskfloww API")

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL não configurada")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
redis_client = redis.from_url(REDIS_URL)


@app.get("/")
def read_root():
    return {"message": "Bem-vindo ao Taskfloww API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def check_status():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        redis_status = redis_client.ping()

        return {
            "api": "online",
            "database": "online",
            "redis": "online" if redis_status else "offline",
        }
    except Exception as e:
        return {
            "api": "online",
            "database": "offline",
            "redis": "unknown",
            "error": str(e),
        }
