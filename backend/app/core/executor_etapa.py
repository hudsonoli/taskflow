"""Responsabilidade EFETIVA de uma etapa e quem pode COMEÇAR A TRABALHAR nela (sessão pessoal) — regra pura, sem banco.

## Resolução (única fonte; leitura, Pauta/Carga futuras e "iniciar trabalho" consomem daqui)
1. a etapa tem responsabilidade EXPLÍCITA se possuir ao menos 1 usuário OU 1 departamento → vale SÓ a da etapa (origem `etapa`);
2. senão, os responsáveis GERAIS da Demanda são o fallback (origem `tarefa`) — resolvido em tempo de leitura, NUNCA copiado para a etapa;
3. senão, não há responsável (origem `nenhuma`).
"Só departamento" já é responsabilidade explícita: não cai no fallback geral.

"Executor" é quem executa: o responsável efetivo da ETAPA ATUAL ou membro do departamento efetivo. NÃO é autoridade de gestão: admin/gestor/Head que só organizam o trabalho de outros
não são executores e, por isso, mover uma tarefa para "em execução" não abre sessão pessoal para eles. O status global da Demanda e o foco pessoal são conceitos separados."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

STATUS_SEM_TRABALHO = frozenset({"concluida", "cancelada", "arquivada"})

ORIGEM_ETAPA = "etapa"
ORIGEM_TAREFA = "tarefa"
ORIGEM_NENHUMA = "nenhuma"


def resolver_responsabilidade_etapa(
    *,
    etapa_usuario_ids: Sequence[object],
    etapa_departamento_ids: Sequence[object],
    demanda_usuario_ids: Sequence[object],
    demanda_departamento_ids: Sequence[object],
) -> tuple[str, list[str], list[str]]:
    """`(origem, usuario_ids, departamento_ids)` efetivos da etapa. Ver a regra no topo do módulo."""
    if etapa_usuario_ids or etapa_departamento_ids:
        return ORIGEM_ETAPA, [str(valor) for valor in etapa_usuario_ids], [str(valor) for valor in etapa_departamento_ids]
    if demanda_usuario_ids or demanda_departamento_ids:
        return ORIGEM_TAREFA, [str(valor) for valor in demanda_usuario_ids], [str(valor) for valor in demanda_departamento_ids]
    return ORIGEM_NENHUMA, [], []


def etapa_atual(etapas: Sequence[Any]) -> Any | None:
    """Menor `ordem` com status ≠ concluída (a mesma derivação do servidor); `None` se o workflow está concluído ou não há etapas."""
    pendentes = [etapa for etapa in etapas if etapa.status != "concluida"]
    return min(pendentes, key=lambda etapa: etapa.ordem) if pendentes else None


def eh_executor_da_demanda(
    usuario: Any,
    *,
    etapas: Sequence[Any],
    demanda_usuario_ids: Sequence[object],
    demanda_departamento_ids: Sequence[object],
) -> bool:
    """Verdadeiro se `usuario` (com `id` e `departamento_id`) pode abrir uma sessão pessoal AGORA nesta Demanda (independente do status global dela).

    `etapas`: objetos com `ordem`, `status`, `usuario_responsavel_ids` e `departamento_responsavel_ids` (os vínculos EXPLÍCITOS da etapa)."""
    if etapas:
        atual = etapa_atual(etapas)
        if atual is None:
            return False  # workflow concluído: não há etapa atual para executar
        if atual.status == "pausada":
            return False
        _, usuarios, departamentos = resolver_responsabilidade_etapa(
            etapa_usuario_ids=atual.usuario_responsavel_ids,
            etapa_departamento_ids=atual.departamento_responsavel_ids,
            demanda_usuario_ids=demanda_usuario_ids,
            demanda_departamento_ids=demanda_departamento_ids,
        )
    else:
        usuarios, departamentos = [str(v) for v in demanda_usuario_ids], [str(v) for v in demanda_departamento_ids]
    return str(usuario.id) in set(usuarios) or (usuario.departamento_id is not None and str(usuario.departamento_id) in set(departamentos))
