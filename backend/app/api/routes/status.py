import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

router = APIRouter()


def get_redis_client():
    redis_url = get_settings().redis_url
    if not redis_url:
        raise RuntimeError("REDIS_URL não configurada")

    return redis.from_url(redis_url)


@router.get("/status")
def check_status():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))

        redis_status = get_redis_client().ping()

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
