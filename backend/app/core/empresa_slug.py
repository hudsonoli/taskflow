"""Slug público da Empresa (`empresas.slug`) — identificador de URL para o futuro login multiempresa (Fase 2).

3–40 caracteres, `[a-z0-9-]`, sem hífen na ponta, único e fora de uma lista mínima de nomes reservados (rotas do
produto que um slug nunca pode "ocupar"). O mesmo formato e a mesma lista estão no CHECK do banco (migration 0041):
esta é a validação AMIGÁVEL (mensagem em português), o banco é a rede de segurança.

`codigo_interno` continua existindo por compatibilidade (é o código de login de hoje) e não é derivado nem alterado
pelo slug.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from app.core.slugify import slugify

# `gestao` (Fase 10A), `e` e `aprovacao` (rotas globais do host) juntam-se aos nomes técnicos. O CHECK do banco (migration 0041) ficou com a lista antiga — é só a
# rede de segurança; esta validação é a que vale (alinhar o CHECK é um P3 para uma futura migration).
SLUG_RESERVADOS: frozenset[str] = frozenset({"plataforma", "gestao", "api", "e", "aprovacao", "login", "logout", "admin", "suporte"})
SLUG_MIN = 3
SLUG_MAX = 40
_FORMATO = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")


def validar_slug(valor: str) -> str:
    """Devolve o slug normalizado (minúsculas, sem espaços nas pontas) ou levanta ValueError com mensagem clara."""
    slug = (valor or "").strip().lower()
    if not slug:
        raise ValueError("O slug não pode ficar vazio.")
    if len(slug) < SLUG_MIN or len(slug) > SLUG_MAX:
        raise ValueError(f"O slug deve ter entre {SLUG_MIN} e {SLUG_MAX} caracteres.")
    if not _FORMATO.fullmatch(slug):
        raise ValueError("O slug aceita só letras minúsculas, números e hífen, sem hífen no começo ou no fim.")
    if slug in SLUG_RESERVADOS:
        raise ValueError(f"'{slug}' é um nome reservado e não pode ser usado como slug.")
    return slug


def slug_a_partir_do_codigo(codigo_interno: str, *, em_uso: Callable[[str], bool]) -> str:
    """Slug válido e livre a partir do `codigo_interno` (ex.: "DEMO" → "demo"); sufixo numérico em colisão."""
    base = slugify(codigo_interno)[:SLUG_MAX].strip("-")
    if len(base) < SLUG_MIN or base in SLUG_RESERVADOS:
        base = f"{base}-empresa".strip("-")[:SLUG_MAX].strip("-") if base else "empresa"
    candidato = base
    sufixo = 2
    while em_uso(candidato) or candidato in SLUG_RESERVADOS or len(candidato) < SLUG_MIN:
        sobra = f"-{sufixo}"
        candidato = f"{base[: SLUG_MAX - len(sobra)].strip('-')}{sobra}"
        sufixo += 1
    return candidato
