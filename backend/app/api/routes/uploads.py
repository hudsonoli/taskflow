"""Arquivos de Demanda — autenticado e restrito ao escopo da própria Demanda.

Até esta correção o router respondia **sem token nenhum**, e a pasta era endereçada só pelo
`codigo` da tarefa (`T26000001`). Como o código é curto, sequencial e adivinhável, isso
significava ler, gravar e apagar arquivo de qualquer demanda por tentativa.

Agora o `codigo` é resolvido para uma Demanda **dentro do escopo de quem pede**. Fora do
escopo é **404**, igual ao acesso por UUID — 403 confirmaria que a demanda existe.

Nota de fase: `arquivos` não tem persistência na 2E.1 e a interface não oferece upload (ver
RecursoIndisponivel). Estes endpoints continuam existindo, então continuam precisando de
barreira — recurso sem tela é exatamente o que passa despercebido.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.escopo import resolver_escopo_demanda
from app.db.session import get_db
from app.dependencies.auth import get_current_user_password_ready
from app.models.usuario import Usuario
from app.repositories.demanda_repository import DemandaRepository

UPLOADS_ROOT = Path("uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

router = APIRouter(
    prefix="/demandas",
    tags=["uploads"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_repository = DemandaRepository()


def demanda_no_escopo(
    codigo: str,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
) -> str:
    """Resolve o código para uma Demanda que este usuário pode ver; 404 caso contrário.

    Devolve o próprio código — validado — para o restante do endpoint seguir usando o mesmo
    valor como nome de pasta.
    """
    demanda = demanda_repository.get_por_codigo_no_escopo(
        db,
        codigo_referencia=(codigo or "").strip(),
        escopo=resolver_escopo_demanda(db, current_user),
    )
    if demanda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demanda não encontrada")
    return demanda.codigo_referencia


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
async def upload_arquivo(
    codigo: str = Depends(demanda_no_escopo), file: UploadFile = File(...)
) -> ArquivoInfo:
    pasta = _codigo_dir(codigo)
    info = await _salvar(pasta, file.filename or "", file, prefixar_id=True)
    return info.model_copy(update={"url": f"/uploads/{codigo}/{info.nome}"})


@router.post("/{codigo}/uploads/final", response_model=ArquivoInfo, status_code=status.HTTP_201_CREATED)
async def upload_arquivo_final(
    codigo: str = Depends(demanda_no_escopo), file: UploadFile = File(...)
) -> ArquivoInfo:
    pasta_final = _codigo_dir(codigo) / f"{codigo}-final"
    info = await _salvar(pasta_final, file.filename or "", file, prefixar_id=False)
    return info.model_copy(update={"url": f"/uploads/{codigo}/{codigo}-final/{info.nome}", "finalDoCliente": True})


@router.get("/{codigo}/uploads", response_model=list[ArquivoInfo])
def listar_arquivos(codigo: str = Depends(demanda_no_escopo)) -> list[ArquivoInfo]:
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
def excluir_arquivo(
    nome_arquivo: str, codigo: str = Depends(demanda_no_escopo), final: bool = False
) -> None:
    pasta = _codigo_dir(codigo)
    if final:
        pasta = pasta / f"{(codigo or '').strip()}-final"
    destino = pasta / _safe_filename(nome_arquivo)
    if not destino.exists() or not destino.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")
    destino.unlink()
