"""Portal Externo de Aprovação — lado PÚBLICO (Fase 9B). SEM autenticação, SEM sessão, SEM tenant do cliente: a ÚNICA credencial é o token (capability).

Regras de superfície:
- TUDO é POST com o token no CORPO JSON — nunca em path/query (não vai para log de acesso, proxy, histórico nem `Referer`). O corpo é lido à mão e validado
  aqui: o tratamento padrão de erro de validação do FastAPI devolveria o `input` (o token) na resposta de 422;
- link inexistente, malformado, revogado, expirado ou obsoleto — ou com o `slug` da URL (`/e/<slug>/aprovacao`) diferente da empresa dona do token — → o
  MESMO 404 neutro (nada de dado interno, nem o motivo). O slug é só CONFERIDO contra a empresa do token: quem manda é o token;
- resposta sempre `no-store`, `no-referrer`, `nosniff`; artefato com `sandbox` e PDF NUNCA inline;
- throttling é do edge (Cloudflare — requisito de Go-Live, ver docs/aprovacao-externa.md): a aplicação não persiste IP nem faz rate-limit próprio.
"""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.aprovacao_externa import (
    AprovacaoPublicaArtefatoPedido,
    AprovacaoPublicaConsultar,
    AprovacaoPublicaDecisao,
    AprovacaoPublicaDecisaoResultadoRead,
    AprovacaoPublicaRead,
)
from app.services.aprovacao_externa_service import (
    AprovacaoExternaConflitoError,
    AprovacaoExternaIndisponivelError,
    AprovacaoExternaJaDecididaError,
    AprovacaoExternaService,
)

router = APIRouter(prefix="/publico/aprovacoes", tags=["publico-aprovacao"])
aprovacao_service = AprovacaoExternaService()

MENSAGEM_INDISPONIVEL = "Este link de aprovação não está mais disponível."
CORPO_MAX_BYTES = 16 * 1024
_CABECALHOS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}


def _indisponivel() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MENSAGEM_INDISPONIVEL, headers=_CABECALHOS)


async def _corpo(request: Request, modelo: type[BaseModel]):
    bruto = await request.body()
    if len(bruto) > CORPO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Requisição inválida", headers=_CABECALHOS)
    try:
        dados = json.loads(bruto)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Requisição inválida", headers=_CABECALHOS) from None
    if not isinstance(dados, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Requisição inválida", headers=_CABECALHOS)
    try:
        return modelo.model_validate(dados)
    except ValidationError as exc:
        erros = exc.errors(include_input=False, include_url=False, include_context=False)
        if any(erro["loc"] and erro["loc"][0] in ("token", "slug") for erro in erros):
            raise _indisponivel() from None  # token ou slug malformado/ausente = link inexistente
        detalhe = [
            {"campo": ".".join(str(parte) for parte in erro["loc"]) or "corpo", "mensagem": str(erro["msg"]).removeprefix("Value error, ")}
            for erro in erros
        ]
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detalhe, headers=_CABECALHOS) from None


@router.post("/consultar", response_model=AprovacaoPublicaRead)
async def consultar(request: Request, response: Response, db: Session = Depends(get_db)):
    corpo = await _corpo(request, AprovacaoPublicaConsultar)
    try:
        resultado = aprovacao_service.consultar_publico(db, corpo.token, corpo.slug)
    except AprovacaoExternaIndisponivelError:
        raise _indisponivel() from None
    response.headers.update(_CABECALHOS)
    return resultado


@router.post("/decisao", response_model=AprovacaoPublicaDecisaoResultadoRead)
async def decidir(request: Request, response: Response, db: Session = Depends(get_db)):
    corpo = await _corpo(request, AprovacaoPublicaDecisao)
    try:
        resultado = aprovacao_service.decidir(db, corpo)
    except AprovacaoExternaIndisponivelError:
        raise _indisponivel() from None
    except AprovacaoExternaJaDecididaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "APROVACAO_JA_DECIDIDA", "message": str(exc)}, headers=_CABECALHOS
        ) from None
    except AprovacaoExternaConflitoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": exc.codigo, "message": str(exc)}, headers=_CABECALHOS
        ) from None
    response.headers.update(_CABECALHOS)
    return resultado


@router.post("/artefato")
async def artefato(request: Request, db: Session = Depends(get_db)):
    """Bytes do artefato `ordem`. Imagem → `inline`; PDF → `attachment` (o navegador nunca interpreta um PDF do cliente na nossa origem)."""
    corpo = await _corpo(request, AprovacaoPublicaArtefatoPedido)
    try:
        servido = aprovacao_service.obter_artefato(db, corpo.token, corpo.slug, corpo.ordem)
    except AprovacaoExternaIndisponivelError:
        raise _indisponivel() from None
    disposicao = "inline" if servido.inline else "attachment"
    return Response(
        content=servido.conteudo,
        media_type=servido.media_type,
        headers={
            **_CABECALHOS,
            "Content-Disposition": f"{disposicao}; filename*=UTF-8''{quote(servido.nome, safe='')}",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.post("/logo")
async def logo(request: Request, db: Session = Depends(get_db)):
    """Logo da empresa DONA do link (derivada do token). Sem token legível → 404 neutro."""
    corpo = await _corpo(request, AprovacaoPublicaConsultar)
    try:
        caminho, mime, _versao = aprovacao_service.logo_publico(db, corpo.token, corpo.slug)
    except AprovacaoExternaIndisponivelError:
        raise _indisponivel() from None
    return FileResponse(caminho, media_type=mime, headers={**_CABECALHOS, "Content-Disposition": "inline"})
