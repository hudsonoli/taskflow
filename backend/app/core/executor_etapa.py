"""Quem pode COMEÇAR A TRABALHAR numa Demanda (sessão pessoal) — regra pura, sem banco.

"Responsável elegível" é quem executa: o responsável individual da ETAPA ATUAL ou um membro do departamento responsável por ela (e, sem responsáveis na etapa ou sem
workflow, os responsáveis da própria Demanda). NÃO é autoridade de gestão: admin/gestor/Head que só organizam o trabalho de outros não são executores e, por isso, mover uma
tarefa para "em execução" não abre sessão pessoal para eles. O status global da Demanda e o foco pessoal são conceitos separados."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

STATUS_SEM_TRABALHO = frozenset({"concluida", "cancelada", "arquivada"})


def eh_executor_da_demanda(
    usuario: Any,
    *,
    etapas: Sequence[Any],
    demanda_usuario_ids: Sequence[object],
    demanda_departamento_ids: Sequence[object],
) -> bool:
    """Verdadeiro se `usuario` (com `id` e `departamento_id`) pode abrir uma sessão pessoal AGORA nesta Demanda (independente do status global dela).

    `etapas`: objetos com `ordem`, `status`, `usuario_responsavel_ids` e `departamento_responsavel_ids`."""
    if etapas:
        pendentes = [etapa for etapa in etapas if etapa.status != "concluida"]
        if not pendentes:
            return False  # workflow concluído: não há etapa atual para executar
        atual = min(pendentes, key=lambda etapa: etapa.ordem)
        if atual.status == "pausada":
            return False
        usuarios, departamentos = atual.usuario_responsavel_ids, atual.departamento_responsavel_ids
        if not usuarios and not departamentos:
            usuarios, departamentos = demanda_usuario_ids, demanda_departamento_ids
    else:
        usuarios, departamentos = demanda_usuario_ids, demanda_departamento_ids
    ids_usuarios = {str(valor) for valor in usuarios}
    ids_departamentos = {str(valor) for valor in departamentos}
    return str(usuario.id) in ids_usuarios or (usuario.departamento_id is not None and str(usuario.departamento_id) in ids_departamentos)
