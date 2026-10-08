"""Endpoints PÚBLICOS por empresa (Fase 2) — consultados antes do login pelo slug da URL (`/e/<slug>/...`).

Só identidade visual: logo, cores, tema e nome de exibição. Nada de id, documento, usuários, configurações ou e-mail.
Slug malformado, reservado, inexistente ou de empresa inativa respondem IGUAL (identidade neutra / 404 no logo): não há
como distinguir "não existe" de "indisponível". O slug só localiza a empresa para exibir a marca — NUNCA autoriza dados.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.configuracao_personalizacao import PublicoEmpresaBrandingRead
from app.services.configuracao_personalizacao_service import (
    ConfiguracaoPersonalizacaoService,
    PersonalizacaoLogoNaoEncontradoError,
)

router = APIRouter(prefix="/publico/empresas", tags=["publico"])
personalizacao_service = ConfiguracaoPersonalizacaoService()

_SlugPath = Path(min_length=1, max_length=64)


@router.get("/{slug}/branding", response_model=PublicoEmpresaBrandingRead)
def branding_publico(slug: str = _SlugPath, db: Session = Depends(get_db)):
    return personalizacao_service.get_publico_por_slug(db, slug=slug)


@router.get("/{slug}/branding/logo")
def logo_publico(
    slug: str = _SlugPath,
    v: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db),
):
    """Mesmo contrato do logo público legado: Content-Type canônico gravado a partir dos bytes validados, `nosniff`,
    caminho interno nunca exposto. Versão correta (`v`) → imutável; sem versão → revalida."""
    try:
        caminho, mime, versao = personalizacao_service.ler_logo_publico_por_slug(db, slug=slug)
    except PersonalizacaoLogoNaoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo não encontrado") from exc
    cache = "public, max-age=31536000, immutable" if v and v == versao else "no-cache"
    return FileResponse(
        caminho,
        media_type=mime,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": cache, "Content-Disposition": "inline"},
    )
