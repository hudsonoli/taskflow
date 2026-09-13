"""Enforcement por permissão (Fase 2G.10B) — primeira onda.

`require_permissao("<modulo>.<acao>")` é o equivalente, por permissão nomeada, de
`require_admin`/`require_admin_or_gestor` (app/dependencies/authorization.py). Uma rota
troca:

    current_user: Usuario = Depends(require_admin_or_gestor)

por:

    current_user: Usuario = Depends(require_permissao("clientes.editar"))

## Overrides: já ativos (decisão desta fase, ver kickoff item 8)

A checagem usa `UsuarioPermissaoService.obter_permissoes_efetivas` — default do perfil +
exceções individuais (`usuario_permissao`) — não só o default. Essa é a definição real de
"permissões efetivas" (app/core/permissoes.py); manter `require_permissao` restrito a
defaults exigiria um caminho de cálculo paralelo, isso sim duplicando lógica que já existe e
já é testada. Como `usuario_permissao` nasceu vazia na Fase 2G.10A e continua vazia em
produção, isso **não muda nenhum comportamento hoje** — só passa a valer no dia em que a
Fase 2G.10C criar o primeiro override de verdade.

## Fail-closed (kickoff item 5)

- Chave que não existe no catálogo: `PermissaoInvalidaError` na hora de DEFINIR a
  dependency (import time — `validar_permissao_existente` roda uma vez, quando o módulo de
  rotas é carregado), nunca em runtime. Um erro de digitação em `require_permissao("clientes.viusalizar")`
  derruba o `import`, não vira 403-sempre em produção.
- `perfil_base` inválido (nunca deveria acontecer — `ck_usuarios_perfil_base` impede na
  origem, mas o resolver trata como caso de primeira classe): `PerfilInvalidoError` vira
  **403**, nunca 500, nunca acesso liberado.
- Permissão ausente do conjunto efetivo: **403** — nunca lista vazia, nunca fallback.

## Tenant

`UsuarioPermissaoService.obter_permissoes_efetivas` já resolve os overrides usando
`current_user.empresa_id` (nunca aceito do cliente) — ver app/services/usuario_permissao_service.py
e app/repositories/usuario_permissao_repository.py, que filtram por `empresa_id` **e**
`usuario_id`.

## Performance (kickoff item 4)

Uma resolução por request (1 query de overrides, tipicamente vazia). Sem Redis, sem cache
global, sem cache por request: cada rota declara `require_permissao(...)` uma única vez,
então não há chamada duplicada dentro da mesma request para valer a pena cachear — cache
aqui seria complexidade sem benefício.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissoes import PERFIL_OPERADOR, PerfilInvalidoError, validar_permissao_existente
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.usuario import Usuario
from app.services.usuario_permissao_service import UsuarioPermissaoService

_usuario_permissao_service = UsuarioPermissaoService()

_ACESSO_NEGADO = "Acesso negado"


def require_permissao(permissao: str) -> Callable[..., Usuario]:
    """Fábrica de dependency — mesma forma de `require_profiles` (authorization.py), mas
    checando uma permissão nomeada em vez de uma lista fixa de perfis.

    Depende de `get_current_user` (não `get_current_user_password_ready`) — mesma escolha de
    `require_admin`/`require_admin_or_gestor`: o gate de senha em dia já é aplicado no nível
    do router (`dependencies=[Depends(get_current_user_password_ready)]`), então repetir aqui
    seria redundante, não mais seguro.
    """
    validar_permissao_existente(permissao)  # falha na importação, não em runtime

    def dependency(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Usuario:
        try:
            efetivas = _usuario_permissao_service.obter_permissoes_efetivas(db, current_user)
        except PerfilInvalidoError:
            # Nunca deveria acontecer (CHECK constraint garante perfil_base válido na
            # origem) — mas se acontecer, fail-closed: 403, nunca 500, nunca liberar.
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)

        if permissao not in efetivas:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)

        return current_user

    return dependency


def require_trafego_gerenciar() -> Callable[..., Usuario]:
    """Como `require_permissao("trafego.gerenciar")`, mas nunca libera para
    `perfil_base == "operador"` — mesmo com override de concessão (Fase 2G.10B, Bloco 2B.1).

    ## Por que isto existe (e por que não é lógica de `require_permissao` genérico)

    `GET /sessoes-trabalho` e `GET /sessoes-trabalho/{id}` devolvem `inicioEm`/`fimEm`/
    `duracaoSegundos` por sessão, filtráveis por `usuarioId` — dado suficiente para
    reconstruir métricas de horas/produtividade por pessoa, sem precisar de nenhum
    agregado. Isso viola a regra de domínio "operador não visualiza métricas
    temporais/horas" (a mesma razão pela qual um endpoint `/minhas/horas` autoescopado foi
    removido no passado — ver docstring de `tests/test_sessao_trabalho.py`) caso
    `trafego.gerenciar` seja concedido a alguém com `perfil_base == "operador"` via
    `usuario_permissao`.

    Esta é uma invariante de DOMÍNIO específica de Tráfego — paralela a "tenant nunca é
    ultrapassado por override" (`ensure_resource_empresa`) e "Head só vê o próprio
    departamento" (`pode_consultar_horas_departamento`) — não uma regra geral de
    permissões. Por isso vive num helper próprio, reaproveitando `require_permissao` sem
    alterá-lo: as outras ~30 permissões já migradas não têm essa propriedade e não devem
    ganhar este piso.

    ## Overrides continuam resolvidos normalmente

    O override de `trafego.gerenciar` (conceder/negar) é calculado por
    `UsuarioPermissaoService.obter_permissoes_efetivas` exatamente como qualquer outra
    permissão — este helper não intercepta nem duplica essa resolução, só aplica uma
    checagem adicional DEPOIS que `require_permissao` já decidiu. Um operador com
    `trafego.gerenciar = conceder` continua tendo a permissão no conjunto efetivo; só não
    passa neste piso adicional.

    ## `/horas` nunca passa por aqui

    `GET /sessoes-trabalho/horas` continua usando `get_current_user_password_ready` +
    `pode_consultar_horas_departamento` (escopo/relação de Head, não permissão) — esta
    dependency não é usada nessa rota e Head (mesmo com `perfil_base == "operador"`) nunca
    dependeu de `trafego.gerenciar` para acessá-la.
    """
    base = require_permissao("trafego.gerenciar")

    def dependency(current_user: Usuario = Depends(base)) -> Usuario:
        if current_user.perfil_base == PERFIL_OPERADOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)
        return current_user

    return dependency
