"""Identidade de CONTA DE SISTEMA nas superfícies de leitura do tenant (Fase 1A/1B).

O proprietário da plataforma é uma conta `usuarios.is_system_account` DENTRO de uma empresa. Para o usuário tenant
normal (Gestor inclusive) ela nunca é uma pessoa identificável: nome, e-mail, código e id não aparecem — o autor é
"Sistema". O registro (arquivo, comentário, evento) continua existindo; só a IDENTIDADE é mascarada, e só na
leitura. A própria conta de sistema não precisa se esconder de si (e segue podendo editar/excluir os seus).

Decisão exclusivamente por `is_system_account` — nunca por e-mail ou nome.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

AUTOR_SISTEMA = "Sistema"


def ids_de_contas_de_sistema(db: Session, ids: Iterable[str | None]) -> set[str]:
    """Dos ids dados, os que são de conta de sistema (UMA consulta para a lista inteira)."""
    candidatos = {str(valor) for valor in ids if valor}
    if not candidatos:
        return set()
    return set(
        db.scalars(select(Usuario.id).where(Usuario.id.in_(candidatos), Usuario.is_system_account.is_(True))).all()
    )
