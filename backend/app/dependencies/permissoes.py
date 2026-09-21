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

from app.core.escopo import departamentos_como_head, eh_atendimento
from app.core.permissoes import PERFIL_ADMIN, PERFIL_GESTOR, PerfilInvalidoError, validar_permissao_existente
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.usuario import Usuario
from app.services.usuario_permissao_service import UsuarioPermissaoService

_usuario_permissao_service = UsuarioPermissaoService()

_ACESSO_NEGADO = "Acesso negado"

# Central de Tráfego, hoje, é admin/gestor — mesma allowlist de `require_admin_or_gestor`
# (a redefinição local que este helper substitui). Allowlist explícita, não "!= operador":
# um perfil_base futuro que não seja nenhum dos dois não deve herdar acesso a dado temporal
# só por não se chamar "operador" — ver docstring de `require_trafego_gerenciar`.
_PERFIS_TRAFEGO_AUTORIZADOS = frozenset({PERFIL_ADMIN, PERFIL_GESTOR})


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
    """Como `require_permissao("trafego.gerenciar")`, mas só libera para
    `perfil_base in {"admin", "gestor"}` — mesmo com override de concessão (Fase 2G.10B,
    Bloco 2B.1; piso reforçado na revisão pré-merge para allowlist explícita, ver seção
    abaixo).

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

    ## Allowlist explícita, não "!= operador"

    O piso é `perfil_base in _PERFIS_TRAFEGO_AUTORIZADOS` ({"admin", "gestor"}) — a mesma
    dupla que `require_admin_or_gestor` (a redefinição local que este helper substitui) já
    autorizava antes desta fase. Checar "!= operador" bloquearia hoje exatamente os mesmos
    casos (só existem 3 perfis reais), mas aceitaria implicitamente qualquer `perfil_base`
    futuro que não seja "operador" nem admin/gestor — sem uma decisão consciente de que esse
    perfil deveria ver dado temporal de Tráfego. A allowlist é fail-closed: um perfil novo só
    ganha acesso por edição explícita desta constante, nunca por omissão.

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
        if current_user.perfil_base not in _PERFIS_TRAFEGO_AUTORIZADOS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)
        return current_user

    return dependency


# admin/gestor criam Demanda por perfil, sem depender de relação nenhuma — mesma dupla de
# `_PERFIS_TRAFEGO_AUTORIZADOS`, reaproveitada aqui por ser exatamente o mesmo conceito
# ("quem administra a empresa inteira"), não uma segunda definição.
_PERFIS_DEMANDAS_CRIAR_POR_PERFIL = frozenset({PERFIL_ADMIN, PERFIL_GESTOR})


def require_demandas_criar() -> Callable[..., Usuario]:
    """Quem pode chamar `POST /demandas` (Fase 2G.10B, D1.1 — fechamento deliberado do gap
    D1 documentado em `app/core/permissoes.py`).

    ## Regra final

    1. Override explícito de `demandas.criar` sempre vence — `"negar"` bloqueia QUALQUER
       usuário (admin, gestor, Head, Atendimento, sem exceção); `"conceder"` libera QUALQUER
       usuário, inclusive operador comum sem nenhuma relação.
    2. Sem override: `perfil_base in {"admin", "gestor"}` cria.
    3. Sem override: Head de pelo menos um departamento (`departamentos_como_head`,
       app/core/escopo.py — fonte única, não duplicada) cria.
    4. Sem override: Atendimento (`eh_atendimento`, mesmo módulo — regra transitória por nome
       de departamento, já documentada como frágil ali; não corrigida nesta fase) cria.
    5. Qualquer outro caso (operador comum, sem relação, sem override): 403.

    ## Por que não é só `require_permissao("demandas.criar")`

    `demandas.criar` saiu do default de `PERFIL_OPERADOR` (ver `app/core/permissoes.py`) —
    hoje só admin/gestor têm por perfil. Head e Atendimento continuam podendo criar, mas por
    RELAÇÃO, não por perfil nem por permissão — `require_permissao` sozinho não tem acesso a
    `app/core/escopo.py` e não conseguiria expressar "permissão OU relação".

    ## Por que não usa `UsuarioPermissaoService.obter_permissoes_efetivas`

    O conjunto efetivo (`obter_permissoes_efetivas`) devolve só o resultado FINAL — uma
    permissão ausente do conjunto não distingue "nunca teve override" de "foi negada
    explicitamente". Essa distinção importa aqui porque Head/Atendimento são autorizados por
    um caminho que não passa pelo conjunto efetivo (relação, não perfil/override) — um
    `negar` explícito precisa continuar bloqueando os dois, então o helper precisa saber que o
    `negar` é EXPLÍCITO antes de cair no fallback relacional. Por isso usa
    `UsuarioPermissaoService.obter_efeito_override`, que devolve só a linha crua para esta
    chave (`"conceder"`/`"negar"`/`None`) — sem duplicar a leitura de `usuario_permissao`
    (mesma consulta de `list_by_usuario` por baixo) nem a lógica de default (que continua só
    em `permissoes_efetivas`/`DEFAULTS_POR_PERFIL`, intocada).

    ## Fail-closed

    Perfil inválido (nunca deveria acontecer): `obter_efeito_override` não levanta
    `PerfilInvalidoError` (não calcula default nenhum), então esse caso nem se aplica aqui —
    a única forma de chegar a "permitido" é override explícito, perfil admin/gestor, ou
    relação real; qualquer outra coisa cai no 403 final, nunca num acesso liberado por
    omissão.

    ## Performance

    admin/gestor sem override: 1 consulta (`obter_efeito_override`). Operador com override
    (conceder ou negar): 1 consulta. Operador comum sem override: até 3 consultas O(1) —
    override + `departamentos_como_head` + `eh_atendimento`, esta última só se a anterior não
    já tiver decidido. Nenhuma delas roda por item de listagem nem em loop; sem N+1, sem
    Redis, sem cache novo.

    ## Escopo — o que este helper NÃO decide

    Só responde "pode chamar `POST /demandas`". Não restringe `cliente_id`/`projeto_id`/
    `responsavel_ids`/`departamento_responsavel_ids` — uma vez autorizado, o ator escolhe
    qualquer recurso válido do próprio tenant, exatamente como antes desta fase (validado por
    `demanda_service.py`, não tocado aqui). Essa restrição adicional é D1.2, decisão de
    produto separada, deliberadamente fora desta fase.
    """
    validar_permissao_existente("demandas.criar")  # falha na importação, não em runtime

    def dependency(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Usuario:
        efeito = _usuario_permissao_service.obter_efeito_override(
            db, usuario=current_user, permissao="demandas.criar"
        )
        if efeito == "negar":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)
        if efeito == "conceder":
            return current_user

        if current_user.perfil_base in _PERFIS_DEMANDAS_CRIAR_POR_PERFIL:
            return current_user
        if departamentos_como_head(db, current_user):
            return current_user
        if eh_atendimento(db, current_user):
            return current_user

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)

    return dependency


# admin-only, mesma allowlist restrita de PERFIL_ADMIN sozinho (nem gestor entra aqui, ao
# contrário de _PERFIS_TRAFEGO_AUTORIZADOS) — gerenciar overrides de outras pessoas é mais
# sensível do que abrir/fechar sessão de trabalho: um override de "conceder" mal colocado
# aqui deixaria alguém administrar as próprias permissões de qualquer um, inclusive de si
# mesmo (self-escalation).
_PERFIS_PERMISSOES_GERENCIAR_AUTORIZADOS = frozenset({PERFIL_ADMIN})


def require_permissoes_gerenciar() -> Callable[..., Usuario]:
    """Como `require_trafego_gerenciar`, mas para `permissoes.gerenciar` (Fase 2G.10C-C1).

    Piso fixo: mesmo com `permissoes.gerenciar = conceder` via override, só quem já tem
    `perfil_base == "admin"` passa. Isso é o que impede um gestor/operador com grant de virar
    administrador de permissões — a permissão sozinha nunca é suficiente, só perfil real.

    Não existe "super-admin" nem hierarquia nova: um admin pode alterar overrides de outro
    admin (inclusive negar `permissoes.gerenciar` dele) — ver
    app/api/routes/usuario_permissao.py para a regra de self (bloqueada por outro motivo,
    não por este guard).
    """
    base = require_permissao("permissoes.gerenciar")

    def dependency(current_user: Usuario = Depends(base)) -> Usuario:
        if current_user.perfil_base not in _PERFIS_PERMISSOES_GERENCIAR_AUTORIZADOS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ACESSO_NEGADO)
        return current_user

    return dependency
