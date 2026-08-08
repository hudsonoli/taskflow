from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

UPLOADS_ROOT = Path("uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

router = APIRouter(prefix="/demandas", tags=["uploads"])


class ArquivoInfo(BaseModel):
    nome: str
    url: str
    tamanhoBytes: int
    finalDoCliente: bool


def _safe_filename(filename: str) -> str:
    nome = Path(filename or "").name.strip()
    if not nome:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome de arquivo inválido")
    return nome


def _validate_extension(filename: str) -> None:
    extensao = Path(filename or "").suffix.lower()
    if extensao not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de arquivo não permitido. Use PNG, JPG, JPEG ou PDF.",
        )


def _codigo_dir(codigo: str) -> Path:
    codigo_seguro = (codigo or "").strip()
    if not codigo_seguro or "/" in codigo_seguro or "\\" in codigo_seguro or ".." in codigo_seguro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Código da tarefa inválido")
    return UPLOADS_ROOT / codigo_seguro


async def _salvar(pasta: Path, filename: str, file: UploadFile, prefixar_id: bool) -> ArquivoInfo:
    _validate_extension(filename)
    pasta.mkdir(parents=True, exist_ok=True)
    nome_seguro = _safe_filename(filename)
    if prefixar_id:
        nome_seguro = f"{uuid4().hex[:8]}_{nome_seguro}"
    destino = pasta / nome_seguro
    conteudo = await file.read()
    destino.write_bytes(conteudo)
    return ArquivoInfo(nome=nome_seguro, url="", tamanhoBytes=len(conteudo), finalDoCliente=False)


@router.post("/{codigo}/uploads", response_model=ArquivoInfo, status_code=status.HTTP_201_CREATED)
async def upload_arquivo(codigo: str, file: UploadFile = File(...)) -> ArquivoInfo:
    pasta = _codigo_dir(codigo)
    info = await _salvar(pasta, file.filename or "", file, prefixar_id=True)
    return info.model_copy(update={"url": f"/uploads/{codigo}/{info.nome}"})


@router.post("/{codigo}/uploads/final", response_model=ArquivoInfo, status_code=status.HTTP_201_CREATED)
async def upload_arquivo_final(codigo: str, file: UploadFile = File(...)) -> ArquivoInfo:
    pasta_final = _codigo_dir(codigo) / f"{codigo}-final"
    info = await _salvar(pasta_final, file.filename or "", file, prefixar_id=False)
    return info.model_copy(update={"url": f"/uploads/{codigo}/{codigo}-final/{info.nome}", "finalDoCliente": True})


@router.get("/{codigo}/uploads", response_model=list[ArquivoInfo])
def listar_arquivos(codigo: str) -> list[ArquivoInfo]:
    pasta = _codigo_dir(codigo)
    if not pasta.exists():
        return []

    final_dir_name = f"{(codigo or '').strip()}-final"
    resultado: list[ArquivoInfo] = []
    for item in sorted(pasta.iterdir()):
        if item.is_file():
            resultado.append(
                ArquivoInfo(nome=item.name, url=f"/uploads/{codigo}/{item.name}", tamanhoBytes=item.stat().st_size, finalDoCliente=False)
            )
        elif item.is_dir() and item.name == final_dir_name:
            for sub in sorted(item.iterdir()):
                if sub.is_file():
                    resultado.append(
                        ArquivoInfo(
                            nome=sub.name,
                            url=f"/uploads/{codigo}/{final_dir_name}/{sub.name}",
                            tamanhoBytes=sub.stat().st_size,
                            finalDoCliente=True,
                        )
                    )
    return resultado


@router.delete("/{codigo}/uploads/{nome_arquivo}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_arquivo(codigo: str, nome_arquivo: str, final: bool = False) -> None:
    pasta = _codigo_dir(codigo)
    if final:
        pasta = pasta / f"{(codigo or '').strip()}-final"
    destino = pasta / _safe_filename(nome_arquivo)
    if not destino.exists() or not destino.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")
    destino.unlink()
