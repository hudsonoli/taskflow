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
    PerfilInvalidoError,
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


def test_admin_default_e_enumerado_explicitamente_e_cobre_o_catalogo_atual() -> None:
    """admin passa em require_admin e em require_admin_or_gestor em toda rota — hoje não há
    nenhuma permissão do catálogo que admin não tenha. Mas o default de admin em
    app/core/permissoes.py é uma lista LITERAL, não `TODAS_AS_PERMISSOES` nem uma expressão
    derivada do catálogo (revisão pré-merge, item 8 — evita privilege creep automático).

    Este teste é o que torna essa disciplina segura: se uma permissão nova entrar em
    CATALOGO sem alguém decidir conscientemente se admin a recebe, este teste QUEBRA — a
    omissão nunca passa em silêncio."""
    assert DEFAULTS_POR_PERFIL[PERFIL_ADMIN] == TODAS_AS_PERMISSOES


def test_defaults_literais_nao_contem_permissao_fora_do_catalogo() -> None:
    """Protege contra erro de digitação nas listas literais de admin/gestor/operador — uma
    string que não bate com nenhuma chave real de CATALOGO é pega aqui, não em produção."""
    for perfil in (PERFIL_ADMIN, PERFIL_GESTOR, PERFIL_OPERADOR):
        sobra = DEFAULTS_POR_PERFIL[perfil] - TODAS_AS_PERMISSOES
        assert not sobra, f"{perfil}: permissões fora do catálogo: {sobra}"


def test_default_gestor_administra_cadastros_mas_nao_usuarios() -> None:
    gestor = DEFAULTS_POR_PERFIL[PERFIL_GESTOR]

    # Cadastros — require_admin_or_gestor real.
    for permissao in ("clientes.criar", "clientes.editar", "clientes.arquivar", "projetos.arquivar", "sla.criar"):
        assert permissao in gestor, permissao

    # Usuário — só visualizar; criar/editar/suspender são require_admin puro.
    assert "usuarios.visualizar" in gestor
    assert "usuarios.criar" not in gestor
    assert "usuarios.editar" not in gestor
    assert "usuarios.suspender" not in gestor

    # Financeiro — hoje ClienteRead/UsuarioRead com dado financeiro são require_admin_or_gestor
    # (ver Fase 2G.10, achado D4/item 18 — não é corrigido aqui).
    assert "financeiro.visualizar" in gestor

    # Tráfego (abrir/fechar sessão de trabalho) — require_admin_or_gestor real.
    assert "trafego.gerenciar" in gestor


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
        "trafego.gerenciar",
        "demandas.arquivar",
    }
    assert operador.isdisjoint(bloqueadas)


def test_permissoes_gerenciar_nao_existe_ainda() -> None:
    """Revisão pré-merge (item 3): não existe hoje nenhum endpoint de gestão de permissão —
    a chave só nasce junto da funcionalidade real, em 2G.10C/2G.10E. Não deixar uma chave
    "reservada para o futuro" sem ação real por trás."""
    assert "permissoes.gerenciar" not in TODAS_AS_PERMISSOES
    assert not any(modulo == "permissoes" for modulo in CATALOGO)


def test_trafego_e_uma_permissao_so_e_nomeada_pela_acao_mais_ampla() -> None:
    """sessoes_trabalho.py inteiro (listar, ver uma, abrir, fechar) usa o mesmo guard
    (require_admin_or_gestor) — uma permissão só, e "gerenciar" porque cobre escrita
    (abrir/fechar), não só leitura."""
    assert CATALOGO["trafego"] == ["trafego.gerenciar"]
    assert "trafego.visualizar" not in TODAS_AS_PERMISSOES


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


def test_perfil_desconhecido_e_fail_closed() -> None:
    """Perfil fora de admin/gestor/operador nunca herda default de outro perfil — levanta
    `PerfilInvalidoError` (subclasse de ValueError) em vez de devolver qualquer conjunto,
    vazio ou não. Cobre explicitamente os 4 rótulos "ricos" do frontend que nunca são
    persistidos como perfil_base real (ver types/usuario.ts): se um deles chegasse aqui por
    engano, tem que quebrar, nunca silenciosamente virar admin/gestor."""
    for perfil_invalido in ("superadmin", "diretoria", "financeiro", "cliente", "", "ADMIN"):
        with pytest.raises(PerfilInvalidoError):
            permissoes_efetivas(perfil_invalido, [])


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
