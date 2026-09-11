"""Testes do catálogo de permissões e do resolver puro (Fase 2G.10A).

Só lógica em memória — sem banco, sem TestClient. Cobertura de infra/API fica em
test_usuario_permissao.py.
"""

from __future__ import annotations

import pytest

from app.core.permissoes import (
    CATALOGO,
    DEFAULTS_POR_PERFIL,
    PERFIL_ADMIN,
    PERFIL_GESTOR,
    PERFIL_OPERADOR,
    PermissaoInvalidaError,
    TODAS_AS_PERMISSOES,
    permissoes_efetivas,
    validar_permissao_existente,
)


def test_catalogo_usa_convencao_modulo_ponto_acao() -> None:
    for permissao in TODAS_AS_PERMISSOES:
        assert "." in permissao, f"{permissao!r} não segue <modulo>.<acao>"
        modulo, _, acao = permissao.partition(".")
        assert modulo and acao, f"{permissao!r} não segue <modulo>.<acao>"


def test_catalogo_sem_chaves_duplicadas_entre_modulos() -> None:
    todas = [permissao for permissoes in CATALOGO.values() for permissao in permissoes]
    assert len(todas) == len(set(todas))


# --------------------------------------------------------------------------------------
# Defaults — devem refletir EXATAMENTE o comportamento real hoje (ver docstring de
# app/core/permissoes.py). Cada assert aqui tem uma rota real correspondente.
# --------------------------------------------------------------------------------------


def test_default_admin_e_o_catalogo_inteiro() -> None:
    """admin passa em require_admin e em require_admin_or_gestor em toda rota — não há
    nenhuma permissão do catálogo que admin não tenha hoje."""
    assert DEFAULTS_POR_PERFIL[PERFIL_ADMIN] == TODAS_AS_PERMISSOES


def test_default_gestor_administra_cadastros_mas_nao_usuarios_nem_permissoes() -> None:
    gestor = DEFAULTS_POR_PERFIL[PERFIL_GESTOR]

    # Cadastros — require_admin_or_gestor real.
    for permissao in ("clientes.criar", "clientes.editar", "clientes.arquivar", "projetos.arquivar", "sla.criar"):
        assert permissao in gestor, permissao

    # Usuário — só visualizar; criar/editar/suspender são require_admin puro.
    assert "usuarios.visualizar" in gestor
    assert "usuarios.criar" not in gestor
    assert "usuarios.editar" not in gestor
    assert "usuarios.suspender" not in gestor

    # Permissões — nenhuma rota existe ainda; gestor não recebe.
    assert "permissoes.gerenciar" not in gestor

    # Financeiro — hoje ClienteRead/UsuarioRead com dado financeiro são require_admin_or_gestor
    # (ver Fase 2G.10, achado D4/item 18 — não é corrigido aqui).
    assert "financeiro.visualizar" in gestor


def test_default_operador_so_tem_demanda_sem_arquivar() -> None:
    """operador não tem guard de perfil em criar/editar/visualizar Demanda hoje — só
    arquivar/restaurar são require_admin_or_gestor. Nenhum cadastro, nenhuma área
    administrativa, nenhum financeiro."""
    assert DEFAULTS_POR_PERFIL[PERFIL_OPERADOR] == frozenset(
        {"demandas.visualizar", "demandas.criar", "demandas.editar"}
    )


def test_default_operador_nao_inclui_nenhum_cadastro_nem_financeiro_nem_administrativo() -> None:
    operador = DEFAULTS_POR_PERFIL[PERFIL_OPERADOR]
    bloqueadas = {
        "clientes.visualizar",
        "usuarios.visualizar",
        "financeiro.visualizar",
        "configuracoes.visualizar",
        "relatorios.visualizar",
        "trafego.visualizar",
        "permissoes.gerenciar",
        "demandas.arquivar",
    }
    assert operador.isdisjoint(bloqueadas)


# --------------------------------------------------------------------------------------
# Resolver — permissoes_efetivas(perfil_base, overrides)
# --------------------------------------------------------------------------------------


def test_override_conceder_adiciona_permissao_ausente_no_default() -> None:
    efetivas = permissoes_efetivas(PERFIL_OPERADOR, [("clientes.visualizar", "conceder")])
    assert "clientes.visualizar" in efetivas
    # o resto do default do operador continua intacto
    assert "demandas.visualizar" in efetivas


def test_override_negar_remove_permissao_existente_no_default() -> None:
    efetivas = permissoes_efetivas(PERFIL_ADMIN, [("usuarios.criar", "negar")])
    assert "usuarios.criar" not in efetivas
    # o resto do default do admin continua intacto
    assert "clientes.criar" in efetivas


def test_negacao_vence_o_default_do_perfil() -> None:
    """admin TEM demandas.arquivar por default — negar precisa vencer isso."""
    assert "demandas.arquivar" in DEFAULTS_POR_PERFIL[PERFIL_ADMIN]
    efetivas = permissoes_efetivas(PERFIL_ADMIN, [("demandas.arquivar", "negar")])
    assert "demandas.arquivar" not in efetivas


def test_sem_overrides_resultado_e_exatamente_o_default() -> None:
    for perfil in (PERFIL_ADMIN, PERFIL_GESTOR, PERFIL_OPERADOR):
        assert permissoes_efetivas(perfil, []) == DEFAULTS_POR_PERFIL[perfil]


def test_multiplos_overrides_independentes_sao_todos_aplicados() -> None:
    efetivas = permissoes_efetivas(
        PERFIL_OPERADOR,
        [("clientes.visualizar", "conceder"), ("demandas.editar", "negar")],
    )
    assert "clientes.visualizar" in efetivas
    assert "demandas.editar" not in efetivas
    assert "demandas.visualizar" in efetivas  # não tocado, continua do default


def test_permissao_invalida_em_override_e_rejeitada() -> None:
    with pytest.raises(PermissaoInvalidaError):
        permissoes_efetivas(PERFIL_OPERADOR, [("abc.qualquer_coisa", "conceder")])


def test_validar_permissao_existente_aceita_catalogo_e_rejeita_o_resto() -> None:
    for permissao in TODAS_AS_PERMISSOES:
        validar_permissao_existente(permissao)  # não levanta

    with pytest.raises(PermissaoInvalidaError):
        validar_permissao_existente("modulo_inexistente.acao_inexistente")


def test_efeito_desconhecido_levanta_erro() -> None:
    with pytest.raises(ValueError):
        permissoes_efetivas(PERFIL_OPERADOR, [("demandas.visualizar", "efeito_invalido")])


def test_perfil_desconhecido_levanta_erro() -> None:
    with pytest.raises(ValueError):
        permissoes_efetivas("superadmin", [])


def test_resultado_e_frozenset_imutavel() -> None:
    efetivas = permissoes_efetivas(PERFIL_ADMIN, [])
    assert isinstance(efetivas, frozenset)


def test_determinismo_ordenacao_estavel_apos_sorted() -> None:
    """A função pura devolve frozenset (sem ordem); quem serializa (UsuarioPermissaoService)
    é quem garante `sorted(...)`. Aqui só confirmamos que ordenar o mesmo conjunto duas
    vezes produz sempre a mesma lista — a base do determinismo exigido no item 14."""
    efetivas = permissoes_efetivas(PERFIL_ADMIN, [])
    primeira = sorted(efetivas)
    segunda = sorted(efetivas)
    assert primeira == segunda
    assert primeira == sorted(primeira)
