"""Autoridade para concluir/aprovar a etapa ATUAL do snapshot de Workflow de uma Demanda (Fase 8A).

Fonte ÚNICA desta decisão — o endpoint e o `podeAvancar` do read model chamam a mesma função. Autoridade é ADITIVA: basta
satisfazer UMA fonte (nunca exige responsável individual E departamento ao mesmo tempo):

  A. responsável individual da etapa (`demanda_workflow_etapa_responsaveis`);
  B. perfil do TENANT admin/gestor (`PERFIS_VISAO_TOTAL`, a regra legada existente);
  C. Head real de um departamento responsável pela etapa (`departamentos_como_head` ∩ departamentos da etapa).

Etapa sem responsável algum só é avançada por B. Atendimento NÃO ganha autoridade por ser Atendimento, e visibilidade da Demanda
(Meu Dia, Meu Departamento, Pauta) também não concede nada. `perfil_base == "admin"` é o perfil do usuário DO TENANT: o
administrador da plataforma usa outro token (`tipo="plataforma"`), recusado por `get_current_user`, e nunca chega aqui.
"""

from __future__ import annotations

from collections.abc import Collection

from sqlalchemy.orm import Session

from app.core.escopo import PERFIS_VISAO_TOTAL, departamentos_como_head
from app.models.usuario import Usuario


def tem_autoridade_total_tenant(usuario: Usuario) -> bool:
    return usuario.perfil_base in PERFIS_VISAO_TOTAL


def departamentos_head_para_workflow(db: Session, usuario: Usuario) -> frozenset[str]:
    """Departamentos de que o usuário é Head (relação real). Vazio para admin/gestor: já têm autoridade total."""
    if tem_autoridade_total_tenant(usuario):
        return frozenset()
    return frozenset(departamentos_como_head(db, usuario))


def pode_avancar_etapa(
    usuario: Usuario,
    *,
    usuario_responsavel_ids: Collection[str],
    departamento_responsavel_ids: Collection[str],
    departamentos_head: Collection[str],
) -> bool:
    if tem_autoridade_total_tenant(usuario):
        return True
    if usuario.id in {str(item) for item in usuario_responsavel_ids}:
        return True
    return bool({str(item) for item in departamento_responsavel_ids} & {str(item) for item in departamentos_head})


def pode_gerenciar_aprovacao_externa(
    usuario: Usuario,
    *,
    usuario_responsavel_ids: Collection[str],
    departamento_responsavel_ids: Collection[str],
    departamentos_head: Collection[str],
    demanda_responsavel_ids: Collection[str],
) -> bool:
    """Fase 9B — quem pode CRIAR/REVOGAR o link de aprovação externa da etapa de aprovação ATUAL. Autoridade separada de `podeAvancar`/`podeRejeitar`
    (gerar link não aprova nada), mas com as mesmas fontes da etapa (responsável, Head do departamento, admin/gestor do tenant) MAIS o responsável
    da Demanda (quem conduz o cliente). Atendimento NÃO ganha autoridade por ser Atendimento; o Administrador da Plataforma nunca chega aqui."""
    if pode_avancar_etapa(
        usuario,
        usuario_responsavel_ids=usuario_responsavel_ids,
        departamento_responsavel_ids=departamento_responsavel_ids,
        departamentos_head=departamentos_head,
    ):
        return True
    return usuario.id in {str(item) for item in demanda_responsavel_ids}
