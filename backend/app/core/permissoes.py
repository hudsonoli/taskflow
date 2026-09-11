"""Catálogo de permissões (Fase 2G.10A) — fundação, sem enforcement.

## O que este módulo é e o que NÃO é

É o vocabulário fechado de permissões nomeadas (`<modulo>.<acao>`) e a função pura que
resolve, para um perfil + uma lista de exceções individuais, o conjunto efetivo de
permissões que uma pessoa tem.

**Não é** a autorização real ainda. Nenhuma rota consulta este módulo nesta fase — todo
endpoint continua exatamente como está, usando `app/dependencies/authorization.py`
(`require_admin`, `require_admin_or_gestor`) e `app/core/escopo.py`. Isso muda só na Fase
2G.10B, com testes de equivalência rota a rota.

## Permissão não é escopo

Uma permissão diz **se** a ação é possível em princípio (ex.: `demandas.visualizar`).
**Não** diz quais linhas de dado: isso continua sendo `app/core/escopo.py`
(`resolver_escopo_demanda`), intocado nesta fase. As duas coisas nunca se misturam neste
arquivo — quando a Fase 2G.10B ou posterior migrar enforcement de verdade, uma rota vai
checar `"demandas.visualizar" in permissoes_do_usuario` **e**, separadamente, aplicar o
escopo resolvido para filtrar a consulta. Uma delas nunca substitui a outra.

## Os defaults refletem o comportamento REAL de hoje, não o desejado

`DEFAULTS_POR_PERFIL` foi construído lendo cada rota (`app/api/routes/*.py`) e copiando
exatamente quem já passa em `require_admin`/`require_admin_or_gestor`/nenhum guard — nunca o
que "deveria" ser. Duas consequências deliberadas, ambas já mapeadas no diagnóstico da Fase
2G.10 e reservadas para subfases futuras (não corrigidas aqui):

- `demandas.criar` inclui `operador` porque `POST /demandas` hoje não tem guard de perfil
  nenhum (só `get_current_user_password_ready`) — a regra "só head/atendimento/gestão cria"
  existe somente no frontend (`podeCriarDemanda`). Ver achado D1 do diagnóstico.
- `financeiro.visualizar` inclui `gestor` porque `ClienteRead`/`UsuarioRead` (rotas
  `require_admin_or_gestor`) devolvem `feeMensalCentavos`/`valorRecebidoMensalCentavos` para
  qualquer gestor hoje — a regra "só Owner/Gestores/Financeiro" ainda não distingue Financeiro
  de Gestor porque `perfil_base` só tem 3 valores. Não é tratado como vazamento a corrigir
  nesta fase (ver Fase 2G.10, item 18) — é o retrato fiel do presente.

## Perfis

Somente os 3 valores reais de `usuarios.perfil_base` (`admin`, `gestor`, `operador`) — ver
`ck_usuarios_perfil_base`. Nenhum perfil novo (`owner`, `diretoria`, `financeiro`, `cliente`)
é criado aqui; essa decisão fica para um checkpoint separado, depois da fundação validada.
"""

from __future__ import annotations

PERFIL_ADMIN = "admin"
PERFIL_GESTOR = "gestor"
PERFIL_OPERADOR = "operador"

PERFIS_VALIDOS: frozenset[str] = frozenset({PERFIL_ADMIN, PERFIL_GESTOR, PERFIL_OPERADOR})

EFEITO_CONCEDER = "conceder"
EFEITO_NEGAR = "negar"
EFEITOS_VALIDOS: frozenset[str] = frozenset({EFEITO_CONCEDER, EFEITO_NEGAR})


# ---------------------------------------------------------------------------------------
# Catálogo — <modulo>.<acao>, só ações que existem de verdade hoje.
#
# "arquivar" cobre o par arquivar/restaurar (mesmo guard real nas duas pontas — ver
# docs/padrao-arquivamento.md; nunca há DELETE físico, então não existe permissão de exclusão
# definitiva). Sub-recursos de edição (ex.: adicionar/remover membro de Equipe, vincular
# Cliente a Grupo, gerenciar itens de Modelo de Campanha dentro de Projeto) ficam dentro da
# permissão de "editar" do recurso pai — não viram permissão própria, porque nenhuma rota
# hoje os protege com um guard diferente do recurso pai.
#
# `dashboard.*` fica de fora de propósito: não existe rota nem página de dashboard no
# TaskFloww hoje (a raiz "/" só redireciona para "/meu-dia") — ver item 20 da Fase 2G.10A.
# ---------------------------------------------------------------------------------------

MODULO_DEMANDAS = "demandas"
MODULO_PROJETOS = "projetos"
MODULO_CLIENTES = "clientes"
MODULO_GRUPOS_CLIENTE = "grupos_cliente"
MODULO_FORNECEDORES = "fornecedores"
MODULO_DEPARTAMENTOS = "departamentos"
MODULO_EQUIPES = "equipes"
MODULO_PECAS = "pecas"
MODULO_CATEGORIAS_PECA = "categorias_peca"
MODULO_WORKFLOWS = "workflows"
MODULO_TIPOS_TAREFA = "tipos_tarefa"
MODULO_SLA = "sla"
MODULO_MODELOS_CAMPANHA = "modelos_campanha"
MODULO_USUARIOS = "usuarios"
MODULO_FINANCEIRO = "financeiro"
MODULO_RELATORIOS = "relatorios"
MODULO_TRAFEGO = "trafego"
MODULO_CONFIGURACOES = "configuracoes"
MODULO_EXPEDIENTE = "expediente"
MODULO_EMAIL = "email"
MODULO_NUMERACAO = "numeracao"
MODULO_ACESSOS = "acessos"
MODULO_PERMISSOES = "permissoes"

# Cadastros administrativos: hoje todos com o mesmo formato (visualizar/criar/editar/
# arquivar), todos `require_admin_or_gestor` nas 4 ações — ver rotas em
# app/api/routes/{clientes,fornecedores,departamentos,equipes,grupos_cliente,pecas,
# categorias_peca,workflow_modelos,tipos_tarefa,sla_regras,modelos_campanha,projetos}.py.
_CADASTROS_ADMIN_OU_GESTOR: tuple[str, ...] = (
    MODULO_PROJETOS,
    MODULO_CLIENTES,
    MODULO_GRUPOS_CLIENTE,
    MODULO_FORNECEDORES,
    MODULO_DEPARTAMENTOS,
    MODULO_EQUIPES,
    MODULO_PECAS,
    MODULO_CATEGORIAS_PECA,
    MODULO_WORKFLOWS,
    MODULO_TIPOS_TAREFA,
    MODULO_SLA,
    MODULO_MODELOS_CAMPANHA,
)

_ACOES_CADASTRO = ("visualizar", "criar", "editar", "arquivar")


def _permissoes_cadastro(modulo: str) -> list[str]:
    return [f"{modulo}.{acao}" for acao in _ACOES_CADASTRO]


CATALOGO: dict[str, list[str]] = {
    # Operacional — hoje sem guard de perfil no backend (ver docstring acima, D1).
    MODULO_DEMANDAS: [
        "demandas.visualizar",
        "demandas.criar",
        "demandas.editar",
        "demandas.arquivar",
    ],
    # Cadastros administrativos — mesmo formato para todos.
    **{modulo: _permissoes_cadastro(modulo) for modulo in _CADASTROS_ADMIN_OU_GESTOR},
    # Usuários — único cadastro em que criar/editar/suspender são mais restritos que
    # visualizar (require_admin puro; ver app/api/routes/usuarios.py). "suspender" cobre
    # inativar/bloquear/desbloquear/excluir/reativar/restaurar — mesmo guard real nas seis.
    MODULO_USUARIOS: [
        "usuarios.visualizar",
        "usuarios.criar",
        "usuarios.editar",
        "usuarios.suspender",
    ],
    # Visibilidade de dado financeiro sensível (fee de Cliente, salário de Usuário) — hoje é
    # uma projeção de campos dentro de ClienteRead/UsuarioRead, não uma rota própria.
    MODULO_FINANCEIRO: ["financeiro.visualizar"],
    MODULO_RELATORIOS: ["relatorios.visualizar"],
    # Central de Tráfego / sessões de trabalho (listagem). O agregado de horas por
    # departamento (`GET /sessoes-trabalho/horas`) tem uma checagem própria em
    # `escopo.pode_consultar_horas_departamento` (admin/gestor OU head do departamento) —
    # isso é escopo, não fica representado aqui como uma segunda permissão.
    MODULO_TRAFEGO: ["trafego.visualizar"],
    # Guarda-chuva "consegue entrar na área administrativa" — espelha
    # `podeAcessarAreaAdministrativa`/o fato de toda rota sob /configuracoes/** ser
    # admin_or_gestor ou admin. Não é uma rota própria.
    MODULO_CONFIGURACOES: ["configuracoes.visualizar"],
    MODULO_EXPEDIENTE: ["expediente.visualizar", "expediente.editar"],
    MODULO_EMAIL: ["email.visualizar", "email.editar"],
    MODULO_NUMERACAO: ["numeracao.visualizar"],
    # "Acesso" no menu — trilha de auditoria de login (app/api/routes/eventos.py).
    MODULO_ACESSOS: ["acessos.visualizar"],
    # Ainda sem nenhuma rota real (não existe endpoint de gestão de permissão nesta fase) —
    # existe só para a Fase 2G.10E ter uma chave estável para proteger a futura UI
    # administrativa. Zero efeito prático hoje.
    MODULO_PERMISSOES: ["permissoes.gerenciar"],
}

TODAS_AS_PERMISSOES: frozenset[str] = frozenset(
    permissao for permissoes in CATALOGO.values() for permissao in permissoes
)


class PermissaoInvalidaError(ValueError):
    """Uma chave de permissão usada em um override não existe no catálogo."""


def validar_permissao_existente(permissao: str) -> None:
    if permissao not in TODAS_AS_PERMISSOES:
        raise PermissaoInvalidaError(f"Permissão desconhecida: {permissao!r}")


def _validar_perfil(perfil_base: str) -> None:
    if perfil_base not in PERFIS_VALIDOS:
        raise ValueError(f"Perfil desconhecido: {perfil_base!r}")


# ---------------------------------------------------------------------------------------
# Defaults por perfil — retrato EXATO do comportamento real hoje (ver docstring do módulo).
# Nunca editar para "corrigir" uma regra: isso é trabalho de fase futura, com o guard real
# migrando junto (2G.10B) ou com o dado financeiro/perfil sendo separado (2G.10D).
# ---------------------------------------------------------------------------------------

_TUDO_ADMIN_OU_GESTOR = [
    permissao
    for modulo in (
        *_CADASTROS_ADMIN_OU_GESTOR,
        MODULO_FINANCEIRO,
        MODULO_RELATORIOS,
        MODULO_TRAFEGO,
        MODULO_CONFIGURACOES,
        MODULO_EXPEDIENTE,
        MODULO_EMAIL,
        MODULO_NUMERACAO,
        MODULO_ACESSOS,
    )
    for permissao in CATALOGO[modulo]
] + ["demandas.visualizar", "demandas.criar", "demandas.editar", "demandas.arquivar", "usuarios.visualizar"]

DEFAULTS_POR_PERFIL: dict[str, frozenset[str]] = {
    # admin: tudo que existe no catálogo, incluindo o que só admin tem (usuarios.criar/
    # editar/suspender, permissoes.gerenciar).
    PERFIL_ADMIN: TODAS_AS_PERMISSOES,
    # gestor: administra os mesmos cadastros e áreas que admin, mas não gerencia Usuário
    # (só visualiza) nem Permissões — ver require_admin puro em app/api/routes/usuarios.py
    # e a ausência de qualquer rota de permissão.
    PERFIL_GESTOR: frozenset(_TUDO_ADMIN_OU_GESTOR),
    # operador: só o operacional que já é liberado sem guard de perfil hoje (Demanda —
    # visualizar/criar/editar, sempre dentro do escopo resolvido por escopo.py). Nenhum
    # cadastro, nenhuma área administrativa, nenhum dado financeiro.
    PERFIL_OPERADOR: frozenset({"demandas.visualizar", "demandas.criar", "demandas.editar"}),
}


def permissoes_efetivas(perfil_base: str, overrides: list[tuple[str, str]]) -> frozenset[str]:
    """Resolve o conjunto efetivo de permissões: `default do perfil + concessões - negações`.

    `overrides` é uma lista de `(permissao, efeito)` — normalmente vinda de
    `UsuarioPermissao` (uma linha por permissão, `UNIQUE(usuario_id, permissao)` garante que
    nunca existem duas entradas conflitantes para a mesma pessoa+permissão, então não há
    ambiguidade de precedência entre overrides — só entre override e default).

    Uma negação sempre vence o default (mesmo que o perfil normalmente tivesse a permissão).
    Uma concessão sempre soma (mesmo que o perfil normalmente não tivesse). Permissão
    desconhecida em `overrides` levanta `PermissaoInvalidaError` — nunca é ignorada em
    silêncio nem gravada.
    """
    _validar_perfil(perfil_base)
    efetivo = set(DEFAULTS_POR_PERFIL[perfil_base])

    for permissao, efeito in overrides:
        validar_permissao_existente(permissao)
        if efeito == EFEITO_CONCEDER:
            efetivo.add(permissao)
        elif efeito == EFEITO_NEGAR:
            efetivo.discard(permissao)
        else:
            raise ValueError(f"Efeito desconhecido: {efeito!r}")

    return frozenset(efetivo)
