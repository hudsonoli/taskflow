from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"app": "Taskfloww API", "status": "ok"}
