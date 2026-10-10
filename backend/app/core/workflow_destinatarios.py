"""Quem precisa agir na etapa de Workflow que acabou de se tornar a atual (Fase 8C) — destinatários da notificação.

Regra (decidida UMA vez, aqui):
- responsáveis INDIVIDUAIS da etapa;
- Head de cada DEPARTAMENTO responsável pela etapa — o mesmo conceito de Head de `core/escopo.py::departamentos_como_head` visto do outro lado:
  `Departamento.responsavel_usuario_id` OU usuário marcado `lider_departamento` dentro do próprio departamento. Os demais membros do departamento
  NÃO são notificados (decisão explícita pendente do produto);
- união sem duplicados (um usuário recebe NO MÁXIMO uma notificação por ativação);
- só pessoas elegíveis: da MESMA empresa da Demanda (nunca por empresaId do cliente), `status='ativo'`, `acesso_sistema` verdadeiro e fora de
  conta de sistema (`is_system_account`). Quem concluiu a etapa anterior NÃO é excluído: se for responsável da próxima, recebe como qualquer um;
- etapa sem responsável algum → ninguém é notificado (nem admin/gestor "por padrão") e o avanço segue normalmente.
"""

from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.usuario import Usuario


def destinatarios_da_etapa(
    db: Session,
    *,
    empresa_id: str,
    usuario_responsavel_ids: Collection[str],
    departamento_responsavel_ids: Collection[str],
) -> list[str]:
    candidatos: set[str] = {str(uid) for uid in usuario_responsavel_ids}
    departamentos = [str(did) for did in departamento_responsavel_ids]
    if departamentos:
        candidatos.update(
            db.scalars(
                select(Departamento.responsavel_usuario_id).where(
                    Departamento.id.in_(departamentos),
                    Departamento.empresa_id == empresa_id,
                    Departamento.responsavel_usuario_id.is_not(None),
                )
            ).all()
        )
        candidatos.update(
            db.scalars(
                select(Usuario.id).where(
                    Usuario.empresa_id == empresa_id,
                    Usuario.lider_departamento.is_(True),
                    Usuario.departamento_id.in_(departamentos),
                )
            ).all()
        )
    if not candidatos:
        return []
    elegiveis = db.scalars(
        select(Usuario.id).where(
            Usuario.id.in_(list(candidatos)),
            Usuario.empresa_id == empresa_id,
            Usuario.status == "ativo",
            Usuario.acesso_sistema.is_(True),
            Usuario.is_system_account.is_(False),
        )
    ).all()
    return sorted(set(elegiveis))
