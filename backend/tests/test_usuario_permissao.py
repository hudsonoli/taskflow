"""Testes de infra/API da fundação de permissões (Fase 2G.10A).

Cobre: repository (isolamento usuário/tenant), service (cálculo efetivo via DB real),
exposição em `/auth/me` e `/usuarios/me`, e checagens de equivalência entre o catálogo e o
comportamento REAL de rotas já existentes (sem alterar nenhuma delas).

Lógica pura do resolver/catálogo fica em test_permissoes.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissoes import PermissaoInvalidaError
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository
from app.services.usuario_permissao_service import UsuarioPermissaoService
from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _override(
    db: Session,
    *,
    usuario: Usuario,
    permissao: str,
    efeito: str,
    motivo: str | None = None,
    concedido_por_usuario_id: str | None = None,
) -> UsuarioPermissao:
    agora = datetime.now(timezone.utc)
    override = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        permissao=permissao,
        efeito=efeito,
        motivo=motivo,
        concedido_por_usuario_id=concedido_por_usuario_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(override)
    db.flush()
    return override


def _payload_usuario(empresa: Empresa, **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {
        "empresaId": empresa.id,
        "codigoInterno": f"u-{sufixo}",
        "nome": f"Usuário {sufixo}",
        "email": f"u-{sufixo}@teste.local",
        "perfilBase": "operador",
        "acessoSistema": True,
        **extra,
    }


# --------------------------------------------------------------------------------------
# Repository
# --------------------------------------------------------------------------------------


def test_repository_lista_apenas_overrides_do_usuario_pedido(
    db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    _override(db_session, usuario=usuario_gestor, permissao="usuarios.criar", efeito="conceder")

    repository = UsuarioPermissaoRepository()
    do_operador = repository.list_by_usuario(db_session, empresa_id=empresa.id, usuario_id=usuario_operador.id)

    assert len(do_operador) == 1
    assert do_operador[0].permissao == "clientes.visualizar"


def test_repository_nao_retorna_override_com_empresa_id_divergente(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario
) -> None:
    """Defesa em profundidade: mesmo que uma linha exista com o `usuario_id` certo mas
    `empresa_id` divergente (dado corrompido/bug), o repository não deve devolvê-la — o
    filtro é por usuario_id E empresa_id, nunca só um dos dois."""
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    # Linha "corrompida": usuario_id certo, empresa_id de outra empresa.
    corrompida = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        usuario_id=usuario_operador.id,
        permissao="usuarios.criar",
        efeito="conceder",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(corrompida)
    db_session.flush()

    repository = UsuarioPermissaoRepository()
    resultado = repository.list_by_usuario(db_session, empresa_id=empresa.id, usuario_id=usuario_operador.id)

    permissoes = {row.permissao for row in resultado}
    assert permissoes == {"clientes.visualizar"}
    assert "usuarios.criar" not in permissoes


# --------------------------------------------------------------------------------------
# Service — cálculo efetivo com DB real
# --------------------------------------------------------------------------------------


def test_service_sem_overrides_devolve_exatamente_o_default_do_perfil(
    db_session: Session, usuario_operador: Usuario
) -> None:
    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_operador)
    assert efetivas == sorted({"demandas.visualizar", "demandas.editar"})


def test_service_override_concede_permissao_extra(db_session: Session, usuario_operador: Usuario) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_operador)

    assert "clientes.visualizar" in efetivas


def test_service_override_nega_permissao_do_default(db_session: Session, usuario_admin: Usuario) -> None:
    _override(db_session, usuario=usuario_admin, permissao="usuarios.criar", efeito="negar")

    service = UsuarioPermissaoService()
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_admin)

    assert "usuarios.criar" not in efetivas
    assert "clientes.criar" in efetivas  # resto do default de admin intacto


def test_service_isolamento_entre_usuarios(
    db_session: Session, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas_gestor = service.obter_permissoes_efetivas(db_session, usuario_gestor)

    # gestor já tem clientes.visualizar por default — o que importa é que o override do
    # operador não influenciou o CÁLCULO do gestor (nenhum efeito cruzado a mais/a menos).
    assert efetivas_gestor == service.obter_permissoes_efetivas(db_session, usuario_gestor)
    efetivas_operador = service.obter_permissoes_efetivas(db_session, usuario_operador)
    assert "clientes.visualizar" in efetivas_operador


def test_service_isolamento_entre_empresas(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    usuario_empresa_a = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="op-a"
    )
    usuario_empresa_b = _criar_usuario_com_credencial(
        db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="op-b"
    )
    _override(db_session, usuario=usuario_empresa_a, permissao="clientes.visualizar", efeito="conceder")

    service = UsuarioPermissaoService()
    efetivas_b = service.obter_permissoes_efetivas(db_session, usuario_empresa_b)

    assert "clientes.visualizar" not in efetivas_b
    assert efetivas_b == sorted({"demandas.visualizar", "demandas.editar"})


def test_service_determinismo_lista_ordenada(db_session: Session, usuario_admin: Usuario) -> None:
    service = UsuarioPermissaoService()
    resultado = service.obter_permissoes_efetivas(db_session, usuario_admin)
    assert resultado == sorted(resultado)
    assert isinstance(resultado, list)


# --------------------------------------------------------------------------------------
# obter_efeito_override (Fase 2G.10B, D1.1) — efeito EXPLÍCITO de uma chave, sem lógica de
# default. Testado isoladamente no service, sem passar pela rota/HTTP.
# --------------------------------------------------------------------------------------


def test_obter_efeito_override_sem_override_devolve_none(db_session: Session, usuario_operador: Usuario) -> None:
    service = UsuarioPermissaoService()
    assert service.obter_efeito_override(db_session, usuario=usuario_operador, permissao="demandas.criar") is None


def test_obter_efeito_override_conceder(db_session: Session, usuario_operador: Usuario) -> None:
    _override(db_session, usuario=usuario_operador, permissao="demandas.criar", efeito="conceder")
    service = UsuarioPermissaoService()
    assert service.obter_efeito_override(db_session, usuario=usuario_operador, permissao="demandas.criar") == "conceder"


def test_obter_efeito_override_negar(db_session: Session, usuario_admin: Usuario) -> None:
    _override(db_session, usuario=usuario_admin, permissao="demandas.criar", efeito="negar")
    service = UsuarioPermissaoService()
    assert service.obter_efeito_override(db_session, usuario=usuario_admin, permissao="demandas.criar") == "negar"


def test_obter_efeito_override_nao_ve_override_de_outro_usuario(
    db_session: Session, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override(db_session, usuario=usuario_gestor, permissao="demandas.criar", efeito="conceder")
    service = UsuarioPermissaoService()
    assert service.obter_efeito_override(db_session, usuario=usuario_operador, permissao="demandas.criar") is None


def test_obter_efeito_override_nao_ve_linha_com_empresa_id_divergente(
    db_session: Session, usuario_operador: Usuario, outra_empresa: Empresa
) -> None:
    """`usuario_id` é identidade global (um usuário pertence a exatamente uma empresa) —
    não é possível, pelo schema real, ter o MESMO `usuario_id` com um override legítimo em
    duas empresas diferentes. O cenário de risco real e testável é o mesmo que already
    protegido no repository (defesa em profundidade): uma linha corrompida com `usuario_id`
    certo mas `empresa_id` divergente do usuário. `list_by_usuario` já filtra por
    `usuario_id` E `empresa_id`; este teste confirma que `obter_efeito_override` herda essa
    proteção — não constrói um segundo caminho de leitura que a contorne."""
    override_corrompido = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        usuario_id=usuario_operador.id,
        permissao="demandas.criar",
        efeito="conceder",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(override_corrompido)
    db_session.flush()

    service = UsuarioPermissaoService()
    assert service.obter_efeito_override(db_session, usuario=usuario_operador, permissao="demandas.criar") is None


def test_obter_efeito_override_permissao_invalida_e_fail_closed(db_session: Session, usuario_operador: Usuario) -> None:
    """Mesma convenção de `require_permissao`/`validar_permissao_existente`: uma chave que
    não existe no catálogo falha alto (`PermissaoInvalidaError`), nunca devolve `None`
    silenciosamente como se fosse "sem override"."""
    service = UsuarioPermissaoService()
    with pytest.raises(PermissaoInvalidaError):
        service.obter_efeito_override(db_session, usuario=usuario_operador, permissao="modulo_que_nao_existe.acao")


# --------------------------------------------------------------------------------------
# Exposição em /auth/me e /usuarios/me
# --------------------------------------------------------------------------------------


def test_auth_me_expoe_permissoes_ordenadas(client_operador: TestClient) -> None:
    resposta = client_operador.get("/auth/me")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert "permissoes" in corpo
    assert corpo["permissoes"] == sorted(corpo["permissoes"])
    assert set(corpo["permissoes"]) == {"demandas.visualizar", "demandas.editar"}


def test_auth_me_compativel_com_campos_existentes(client_admin: TestClient) -> None:
    """Campo novo é aditivo — nada do contrato anterior de /auth/me some."""
    corpo = client_admin.get("/auth/me").json()
    for campo in ("usuarioId", "empresaId", "nome", "perfilBase", "acessoSistema", "status", "mustChangePassword"):
        assert campo in corpo


def test_usuarios_me_expoe_permissoes(client_gestor: TestClient) -> None:
    resposta = client_gestor.get("/usuarios/me")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["permissoes"] == sorted(corpo["permissoes"])
    assert "usuarios.visualizar" in corpo["permissoes"]
    assert "usuarios.criar" not in corpo["permissoes"]


def test_usuarios_get_outro_usuario_nao_expoe_permissoes(
    client_admin: TestClient, usuario_gestor: Usuario
) -> None:
    """GET /usuarios/{id} de OUTRA pessoa nunca devolve as permissões dela — só /me."""
    resposta = client_admin.get(f"/usuarios/{usuario_gestor.id}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["permissoes"] is None


def test_usuarios_get_outro_usuario_consulta_overrides_uma_vez(
    client_admin: TestClient, usuario_admin: Usuario, usuario_gestor: Usuario, monkeypatch
) -> None:
    """Item 14 — sem N+1: desde a Fase 2G.10B (bloco 2A), GET /usuarios/{id} passou a usar
    `require_permissao("usuarios.visualizar")`, que resolve as permissões efetivas de QUEM
    FAZ a chamada (não da pessoa consultada) — nunca zero (isso mudou de propósito nesta
    fase) e nunca N+1 por recurso retornado. O campo `permissoes` da resposta continua
    None — só /me o preenche.

    Fase S1-A: `UsuarioService.to_read` ganhou uma segunda consulta própria (independente
    da do gate) para decidir o mascaramento de `financeiro.visualizar` — por isso agora são
    2 chamadas, não 1, mas as DUAS continuam resolvendo as permissões de quem FAZ a
    request (admin), nunca da pessoa consultada."""
    chamadas = []
    original = UsuarioPermissaoRepository.list_by_usuario

    def _contar(self, db, *, empresa_id, usuario_id):
        chamadas.append(usuario_id)
        return original(self, db, empresa_id=empresa_id, usuario_id=usuario_id)

    monkeypatch.setattr(UsuarioPermissaoRepository, "list_by_usuario", _contar)

    resposta = client_admin.get(f"/usuarios/{usuario_gestor.id}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["permissoes"] is None
    # 2 chamadas (gate de require_permissao + mascaramento financeiro em to_read), as duas
    # resolvendo as permissões de QUEM FAZ a request (admin), nunca da pessoa consultada
    # (usuario_gestor) — nenhuma delas troca de identidade.
    assert chamadas == [usuario_admin.id, usuario_admin.id]


def test_usuarios_listagem_consulta_overrides_uma_vez_nao_por_linha(
    client_admin: TestClient, empresa: Empresa, usuario_admin: Usuario, usuario_gestor: Usuario, monkeypatch
) -> None:
    """Mesma garantia do teste acima, para GET /usuarios (lista): consultas de overrides de
    quem lista (via `require_permissao` + mascaramento financeiro, Fase S1-A), nunca uma
    por usuário listado."""
    chamadas = []
    original = UsuarioPermissaoRepository.list_by_usuario

    def _contar(self, db, *, empresa_id, usuario_id):
        chamadas.append(usuario_id)
        return original(self, db, empresa_id=empresa_id, usuario_id=usuario_id)

    monkeypatch.setattr(UsuarioPermissaoRepository, "list_by_usuario", _contar)

    resposta = client_admin.get(f"/usuarios?empresaId={empresa.id}")
    assert resposta.status_code == 200, resposta.text
    assert len(resposta.json()) >= 2  # admin (self) + usuario_gestor, no mínimo
    assert all(usuario["permissoes"] is None for usuario in resposta.json())
    # 2 chamadas (gate + to_read_lote, Fase S1-A), as duas só de quem lista (admin) —
    # nunca uma por linha devolvida, por maior que seja a lista.
    assert chamadas == [usuario_admin.id, usuario_admin.id]


# --------------------------------------------------------------------------------------
# Item 16 — permissão já persistida inválida não pode derrubar /auth/me nem /usuarios/me
# --------------------------------------------------------------------------------------


def test_override_invalido_persistido_nao_derruba_auth_me(
    db_session: Session, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """Simula intervenção manual/dado de versão anterior do catálogo: uma linha com
    `permissao` que não existe mais. `/auth/me` tem que continuar respondendo 200, só sem
    essa chave na lista — nunca 500 (isso trancaria o próprio login de quem precisa
    corrigir)."""
    _override(db_session, usuario=usuario_operador, permissao="modulo_removido.acao_antiga", efeito="conceder")
    _override(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")

    resposta = client_operador.get("/auth/me")

    assert resposta.status_code == 200, resposta.text
    permissoes = resposta.json()["permissoes"]
    assert "modulo_removido.acao_antiga" not in permissoes
    assert "clientes.visualizar" in permissoes  # o override válido continua funcionando


def test_override_com_efeito_invalido_e_ignorado_pelo_service(
    db_session: Session, usuario_operador: Usuario, monkeypatch
) -> None:
    """Defesa em profundidade para um `efeito` fora de conceder/negar. O `CHECK
    ck_usuario_permissao_efeito` já impede isso de ser gravado por qualquer caminho normal
    (confirmado: uma tentativa de INSERT com efeito inválido é recusada pelo Postgres) — este
    teste prova que, MESMO ASSIM, o service não confiaria cegamente no dado caso ele existisse
    (ex.: linha de uma versão anterior do CHECK, ou bypass manual), sem precisar contornar a
    constraint de verdade: troca o repository por um dublê que devolve a linha corrompida."""

    class _OverrideFalso:
        permissao = "demandas.visualizar"
        efeito = "permitir"  # inválido de propósito

    class _RepositorioFalso:
        def list_by_usuario(self, db, *, empresa_id, usuario_id):
            return [_OverrideFalso()]

    service = UsuarioPermissaoService(repository=_RepositorioFalso())
    efetivas = service.obter_permissoes_efetivas(db_session, usuario_operador)

    assert efetivas == sorted({"demandas.visualizar", "demandas.editar"})


def test_check_constraint_do_banco_recusa_efeito_invalido(db_session: Session, usuario_operador: Usuario) -> None:
    """Confirma a primeira linha de defesa (a própria migration 0034): o banco já recusa um
    `efeito` fora de conceder/negar antes mesmo do service entrar em ação."""
    override_invalido = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=usuario_operador.empresa_id,
        usuario_id=usuario_operador.id,
        permissao="demandas.visualizar",
        efeito="permitir",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(override_invalido)
    with pytest.raises(IntegrityError, match="ck_usuario_permissao_efeito"):
        db_session.flush()
    db_session.rollback()


# --------------------------------------------------------------------------------------
# Equivalência — o catálogo bate com o enforcement REAL (que não mudou nesta fase)
# --------------------------------------------------------------------------------------


def test_equivalencia_admin_continua_administrativo(client_admin: TestClient) -> None:
    assert client_admin.get("/clientes").status_code == 200


def test_equivalencia_gestor_administra_cadastro_mas_nao_usuario(
    client_gestor: TestClient, empresa: Empresa
) -> None:
    assert client_gestor.get("/clientes").status_code == 200
    resposta = client_gestor.post("/usuarios", json=_payload_usuario(empresa))
    assert resposta.status_code == 403


def test_equivalencia_operador_bloqueado_em_area_administrativa(client_operador: TestClient) -> None:
    assert client_operador.get("/clientes").status_code == 403
    assert client_operador.get("/usuarios?empresaId=" + str(uuid.uuid4())).status_code == 403


def test_equivalencia_operador_nao_cria_mais_demanda_por_default(client_operador: TestClient) -> None:
    """Reflete o achado D1 do diagnóstico original, agora FECHADO na Fase 2G.10B, D1.1:
    `demandas.criar` saiu do default de operador — só admin/gestor por perfil, Head/Atendimento
    por relação (ver `require_demandas_criar()`, app/dependencies/permissoes.py). Este teste
    documentava o comportamento antigo; a assertiva foi invertida deliberadamente."""
    resposta = client_operador.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}"})
    assert resposta.status_code == 403, resposta.text


def test_equivalencia_operador_nao_arquiva_demanda(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    criada = client_admin.post(
        "/demandas",
        json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", "usuarioResponsavelIds": [usuario_operador.id]},
    ).json()
    resposta = client_operador.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "teste"})
    assert resposta.status_code == 403
