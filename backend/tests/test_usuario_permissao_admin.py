"""Fase 2G.10C-C1 — gestão administrativa de overrides de usuario_permissao.

Cobre a API nova (GET/PUT/DELETE /usuarios/{id}/permissoes): guard admin-only com piso fixo
de perfil, isolamento por tenant, bloqueio de self-escalation, grant/deny/herdar,
idempotência, eventos de domínio e integração real com os mecanismos já existentes
(require_permissao, require_demandas_criar, D1.2D) — a escrita nova alimenta esses
mecanismos, nunca os substitui.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.repositories.usuario_permissao_repository import UsuarioPermissaoRepository
from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _client_para(app, usuario: Usuario) -> TestClient:
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _override_direto(
    db: Session, *, usuario: Usuario, permissao: str, efeito: str, motivo: str | None = None
) -> UsuarioPermissao:
    """Escrita direta via ORM (bypassando a API nova) — usada só para MONTAR cenário em
    testes que não estão testando o PUT em si (ex.: guard, tenant, GET)."""
    agora = datetime.now(timezone.utc)
    override = UsuarioPermissao(
        id=str(uuid.uuid4()),
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        permissao=permissao,
        efeito=efeito,
        motivo=motivo,
        created_at=agora,
        updated_at=agora,
    )
    db.add(override)
    db.flush()
    return override


def _eventos_de(db: Session, usuario_id: str, tipo: str) -> list[Evento]:
    return list(
        db.scalars(select(Evento).where(Evento.entidade_id == usuario_id, Evento.tipo == tipo)).all()
    )


# --------------------------------------------------------------------------------------
# Guard (item 24)
# --------------------------------------------------------------------------------------


def test_admin_acessa_get(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert resposta.status_code == 200, resposta.text


def test_gestor_recebe_403(client_gestor: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_gestor.get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert resposta.status_code == 403, resposta.text


def test_operador_recebe_403(client_operador: TestClient, usuario_gestor: Usuario) -> None:
    resposta = client_operador.get(f"/usuarios/{usuario_gestor.id}/permissoes")
    assert resposta.status_code == 403, resposta.text


def test_gestor_com_grant_permissoes_gerenciar_continua_403(
    app, db_session: Session, usuario_gestor: Usuario, usuario_operador: Usuario
) -> None:
    """O piso fixo (perfil_base == admin) vence mesmo com a permissão concedida via
    override — a chave sozinha nunca é suficiente."""
    _override_direto(db_session, usuario=usuario_gestor, permissao="permissoes.gerenciar", efeito="conceder")
    resposta = _client_para(app, usuario_gestor).get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert resposta.status_code == 403, resposta.text


def test_operador_com_grant_permissoes_gerenciar_continua_403(
    app, db_session: Session, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    _override_direto(db_session, usuario=usuario_operador, permissao="permissoes.gerenciar", efeito="conceder")
    resposta = _client_para(app, usuario_operador).get(f"/usuarios/{usuario_gestor.id}/permissoes")
    assert resposta.status_code == 403, resposta.text


# --------------------------------------------------------------------------------------
# Tenant (item 25)
# --------------------------------------------------------------------------------------


def test_get_outro_tenant_e_404(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="alheio-get")
    resposta = client_admin.get(f"/usuarios/{alheio.id}/permissoes")
    assert resposta.status_code == 404, resposta.text


def test_put_outro_tenant_e_404(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="alheio-put")
    resposta = client_admin.put(f"/usuarios/{alheio.id}/permissoes/demandas.criar", json={"efeito": "conceder"})
    assert resposta.status_code == 404, resposta.text


def test_delete_outro_tenant_e_404(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa
) -> None:
    alheio = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="operador", email_prefixo="alheio-del")
    resposta = client_admin.delete(f"/usuarios/{alheio.id}/permissoes/demandas.criar")
    assert resposta.status_code == 404, resposta.text


def test_repository_nao_ve_override_de_outro_tenant(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa, usuario_operador: Usuario
) -> None:
    _override_direto(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    repository = UsuarioPermissaoRepository()
    resultado = repository.get_by_usuario_e_permissao(
        db_session, empresa_id=outra_empresa.id, usuario_id=usuario_operador.id, permissao="clientes.visualizar"
    )
    assert resultado is None


# --------------------------------------------------------------------------------------
# Self (item 26)
# --------------------------------------------------------------------------------------


def test_get_proprio_e_permitido(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.get(f"/usuarios/{usuario_admin.id}/permissoes")
    assert resposta.status_code == 200, resposta.text


def test_put_proprio_e_403(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.put(f"/usuarios/{usuario_admin.id}/permissoes/usuarios.criar", json={"efeito": "negar"})
    assert resposta.status_code == 403, resposta.text


def test_delete_proprio_e_403(client_admin: TestClient, usuario_admin: Usuario) -> None:
    resposta = client_admin.delete(f"/usuarios/{usuario_admin.id}/permissoes/usuarios.criar")
    assert resposta.status_code == 403, resposta.text


# --------------------------------------------------------------------------------------
# GET (item 27)
# --------------------------------------------------------------------------------------


def test_get_sem_override_reflete_default(client_admin: TestClient, usuario_operador: Usuario) -> None:
    itens = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes").json()
    item = next(i for i in itens if i["permissao"] == "demandas.visualizar")
    assert item["herdado"] is True
    assert item["override"] is None
    assert item["efetivo"] is True

    item_criar = next(i for i in itens if i["permissao"] == "demandas.criar")
    assert item_criar["herdado"] is False
    assert item_criar["override"] is None
    assert item_criar["efetivo"] is False


def test_get_com_conceder(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    _override_direto(db_session, usuario=usuario_operador, permissao="clientes.visualizar", efeito="conceder")
    itens = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes").json()
    item = next(i for i in itens if i["permissao"] == "clientes.visualizar")
    assert item["override"] == "conceder"
    assert item["efetivo"] is True


def test_get_com_negar(client_admin: TestClient, db_session: Session, usuario_admin: Usuario) -> None:
    _override_direto(db_session, usuario=usuario_admin, permissao="usuarios.criar", efeito="negar")
    resposta = client_admin.get(f"/usuarios/{usuario_admin.id}/permissoes")
    itens = resposta.json()
    item = next(i for i in itens if i["permissao"] == "usuarios.criar")
    assert item["herdado"] is True
    assert item["override"] == "negar"
    assert item["efetivo"] is False


def test_get_lista_contem_todas_as_permissoes(client_admin: TestClient, usuario_operador: Usuario) -> None:
    from app.core.permissoes import TODAS_AS_PERMISSOES

    itens = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes").json()
    assert {item["permissao"] for item in itens} == TODAS_AS_PERMISSOES


def test_get_labels_completas_e_modulo_derivado(client_admin: TestClient, usuario_operador: Usuario) -> None:
    itens = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes").json()
    for item in itens:
        assert item["label"], item["permissao"]
        assert item["modulo"] == item["permissao"].split(".", 1)[0]


# --------------------------------------------------------------------------------------
# PUT (item 28)
# --------------------------------------------------------------------------------------


def test_put_cria_conceder(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["override"] == "conceder"
    assert corpo["efetivo"] is True


def test_put_cria_negar(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/demandas.visualizar", json={"efeito": "negar"}
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["override"] == "negar"
    assert corpo["efetivo"] is False


def test_put_conceder_depois_negar_atualiza_a_mesma_linha(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "negar"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["override"] == "negar"

    repository = UsuarioPermissaoRepository()
    linhas = repository.list_by_usuario(db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id)
    assert len([linha for linha in linhas if linha.permissao == "clientes.visualizar"]) == 1


def test_put_negar_depois_conceder_atualiza_a_mesma_linha(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "negar"})
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["override"] == "conceder"

    repository = UsuarioPermissaoRepository()
    linhas = repository.list_by_usuario(db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id)
    assert len([linha for linha in linhas if linha.permissao == "clientes.visualizar"]) == 1


def test_put_motivo_persistido(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar",
        json={"efeito": "conceder", "motivo": "cobre férias do time comercial"},
    )
    repository = UsuarioPermissaoRepository()
    linha = repository.get_by_usuario_e_permissao(
        db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id, permissao="clientes.visualizar"
    )
    assert linha.motivo == "cobre férias do time comercial"


def test_put_muda_de_conceder_para_negar_publica_evento_do_estado_final(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    """O evento publicado numa atualização reflete o efeito NOVO, nunca o anterior."""
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "negar"})

    concedidos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_concedida")
    negados = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_negada")
    assert len(concedidos) == 1  # só o primeiro PUT
    assert len(negados) == 1  # só o segundo PUT — não duplica o de conceder


def test_put_mesmo_efeito_com_motivo_novo_atualiza_e_publica_evento_de_novo(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    """Reenviar o MESMO efeito com motivo diferente ainda conta como ação administrativa
    explícita — atualiza o motivo e publica um evento novo, não é ignorado por já existir."""
    client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar",
        json={"efeito": "conceder", "motivo": "motivo original"},
    )
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar",
        json={"efeito": "conceder", "motivo": "motivo atualizado"},
    )
    assert resposta.status_code == 200, resposta.text

    repository = UsuarioPermissaoRepository()
    linha = repository.get_by_usuario_e_permissao(
        db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id, permissao="clientes.visualizar"
    )
    assert linha.motivo == "motivo atualizado"

    eventos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_concedida")
    assert len(eventos) == 2  # os dois PUTs publicaram, mesmo com o mesmo efeito


def test_put_concedido_por_reflete_ator_mais_recente(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_admin: Usuario, usuario_operador: Usuario
) -> None:
    outro_admin = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="admin-2")
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    _client_para(app, outro_admin).put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "negar"}
    )

    repository = UsuarioPermissaoRepository()
    linha = repository.get_by_usuario_e_permissao(
        db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id, permissao="clientes.visualizar"
    )
    assert linha.concedido_por_usuario_id == outro_admin.id


def test_put_permissao_inexistente_e_422(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/modulo_que_nao_existe.acao", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 422, resposta.text


def test_put_campo_extra_no_body_e_422(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar",
        json={"efeito": "conceder", "efetivo": True},
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# DELETE (item 29)
# --------------------------------------------------------------------------------------


def test_delete_existente_e_204_e_linha_some(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})

    resposta = client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")
    assert resposta.status_code == 204, resposta.text

    repository = UsuarioPermissaoRepository()
    linha = repository.get_by_usuario_e_permissao(
        db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id, permissao="clientes.visualizar"
    )
    assert linha is None


def test_delete_faz_efetivo_voltar_ao_herdado(client_admin: TestClient, usuario_operador: Usuario) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")

    itens = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes").json()
    item = next(i for i in itens if i["permissao"] == "clientes.visualizar")
    assert item["override"] is None
    assert item["herdado"] is False
    assert item["efetivo"] is False


def test_delete_inexistente_e_204_idempotente(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")
    assert resposta.status_code == 204, resposta.text


def test_delete_permissao_invalida_e_422(client_admin: TestClient, usuario_operador: Usuario) -> None:
    resposta = client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/modulo_que_nao_existe.acao")
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Arquivado / inativo / sem acesso (item 30)
# --------------------------------------------------------------------------------------


def test_get_usuario_arquivado_e_200(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.status = "arquivado"
    db_session.flush()
    resposta = client_admin.get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert resposta.status_code == 200, resposta.text


def test_put_usuario_arquivado_e_409(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.status = "arquivado"
    db_session.flush()
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 409, resposta.text


def test_delete_usuario_arquivado_e_409(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.status = "arquivado"
    db_session.flush()
    resposta = client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")
    assert resposta.status_code == 409, resposta.text


def test_put_usuario_inativo_e_permitido(client_admin: TestClient, db_session: Session, usuario_operador: Usuario) -> None:
    usuario_operador.status = "inativo"
    db_session.flush()
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 200, resposta.text


def test_put_usuario_sem_acesso_sistema_e_permitido(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    usuario_operador.acesso_sistema = False
    db_session.flush()
    resposta = client_admin.put(
        f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"}
    )
    assert resposta.status_code == 200, resposta.text


# --------------------------------------------------------------------------------------
# Eventos (item 31)
# --------------------------------------------------------------------------------------


def test_evento_de_concessao(
    client_admin: TestClient, db_session: Session, usuario_admin: Usuario, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    eventos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_concedida")
    assert len(eventos) == 1
    assert eventos[0].usuario_id == usuario_admin.id
    assert eventos[0].payload["permissao"] == "clientes.visualizar"
    assert eventos[0].payload["efeito"] == "conceder"
    assert eventos[0].payload["concedido_por_usuario_id"] == usuario_admin.id


def test_evento_de_negacao(
    client_admin: TestClient, db_session: Session, usuario_admin: Usuario, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/demandas.visualizar", json={"efeito": "negar"})
    eventos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_negada")
    assert len(eventos) == 1
    assert eventos[0].payload["permissao"] == "demandas.visualizar"
    assert eventos[0].payload["efeito"] == "negar"


def test_evento_de_remocao(
    client_admin: TestClient, db_session: Session, usuario_admin: Usuario, usuario_operador: Usuario
) -> None:
    client_admin.put(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})
    client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")
    eventos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_removida")
    assert len(eventos) == 1
    assert eventos[0].payload["permissao"] == "clientes.visualizar"
    assert eventos[0].usuario_id == usuario_admin.id


def test_delete_idempotente_nao_publica_evento_falso(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    client_admin.delete(f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar")
    eventos = _eventos_de(db_session, usuario_operador.id, "usuario.permissao_removida")
    assert eventos == []


# --------------------------------------------------------------------------------------
# Integração D1.1 — grant real alimenta require_demandas_criar (item 32)
# --------------------------------------------------------------------------------------


def test_integracao_grant_demandas_criar_libera_criacao_real(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    operador = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="d1-int")
    client_operador = _client_para(app, operador)

    # Antes do grant: sem demandas.criar, POST /demandas é 403 (D1.1).
    bloqueado = client_operador.post("/demandas", json={"nome": "Tentativa antes do grant"})
    assert bloqueado.status_code == 403, bloqueado.text

    resposta_put = client_admin.put(
        f"/usuarios/{operador.id}/permissoes/demandas.criar", json={"efeito": "conceder"}
    )
    assert resposta_put.status_code == 200, resposta_put.text

    me = client_operador.get("/usuarios/me").json()
    assert "demandas.criar" in me["permissoes"]

    criada = client_operador.post("/demandas", json={"nome": "Demanda pós-grant"})
    assert criada.status_code == 201, criada.text


def test_integracao_grant_reflete_em_auth_me_imediatamente(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Mesma garantia do teste acima, mas para /auth/me — a outra rota que expõe permissões
    efetivas (ver test_usuario_permissao.py::test_auth_me_expoe_permissoes_ordenadas). Sem
    cache, sem token novo, sem relogin: o próximo request já vê o override."""
    operador = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="authme-int")
    client_operador = _client_para(app, operador)

    antes = client_operador.get("/auth/me").json()
    assert "clientes.visualizar" not in antes["permissoes"]

    client_admin.put(f"/usuarios/{operador.id}/permissoes/clientes.visualizar", json={"efeito": "conceder"})

    depois = client_operador.get("/auth/me").json()
    assert "clientes.visualizar" in depois["permissoes"]


# --------------------------------------------------------------------------------------
# D1.2D preservado — grant não vira bypass de escopo (item 33)
# --------------------------------------------------------------------------------------


def test_integracao_grant_nao_ignora_restricao_d1_2d(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    from tests.test_demanda import _departamento

    operador = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="d1-2d-int")
    departamento_proprio = _departamento(db_session, empresa, nome="Próprio D1.2D")
    departamento_alheio = _departamento(db_session, empresa, nome="Alheio D1.2D")
    operador.departamento_id = departamento_proprio.id
    db_session.flush()

    client_admin.put(f"/usuarios/{operador.id}/permissoes/demandas.criar", json={"efeito": "conceder"})
    client_operador = _client_para(app, operador)

    # Próprio departamento: passa (D1.2D permite).
    ok = client_operador.post(
        "/demandas", json={"nome": "Com departamento próprio", "departamentoResponsavelIds": [departamento_proprio.id]}
    )
    assert ok.status_code == 201, ok.text

    # Departamento alheio: D1.2D continua rejeitando, mesmo com o grant novo.
    rejeitado = client_operador.post(
        "/demandas", json={"nome": "Com departamento alheio", "departamentoResponsavelIds": [departamento_alheio.id]}
    )
    assert rejeitado.status_code == 422, rejeitado.text


# --------------------------------------------------------------------------------------
# Integração negar demandas.editar (item 34)
# --------------------------------------------------------------------------------------


def test_integracao_negar_demandas_editar_bloqueia_patch_real(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    operador = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="operador", email_prefixo="deny-int")
    client_operador = _client_para(app, operador)

    resposta_criacao = client_admin.post("/demandas", json={"nome": "Demanda para negar edição"})
    assert resposta_criacao.status_code == 201, resposta_criacao.text
    criada = resposta_criacao.json()

    client_admin.put(f"/usuarios/{operador.id}/permissoes/demandas.editar", json={"efeito": "negar"})

    me = client_operador.get("/usuarios/me").json()
    assert "demandas.editar" not in me["permissoes"]

    resposta = client_operador.patch(f"/demandas/{criada['id']}", json={"nome": "Tentativa de editar"})
    assert resposta.status_code == 403, resposta.text


# --------------------------------------------------------------------------------------
# permissoes.gerenciar entre dois admins (item 35)
# --------------------------------------------------------------------------------------


def test_admin_a_nega_permissoes_gerenciar_de_admin_b_e_depois_restaura(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    admin_b = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="admin-b")
    client_b = _client_para(app, admin_b)

    # Antes: Admin B administra normalmente (mesmo tenant, não-self).
    assert client_b.get(f"/usuarios/{usuario_operador.id}/permissoes").status_code == 200

    resposta_negar = client_admin.put(
        f"/usuarios/{admin_b.id}/permissoes/permissoes.gerenciar", json={"efeito": "negar"}
    )
    assert resposta_negar.status_code == 200, resposta_negar.text

    # Depois do deny: Admin B continua perfil_base == admin, mas 403 nos endpoints de
    # permissões — o floor NÃO ignora um deny explícito, e não existe "super-admin" imune.
    bloqueado = client_b.get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert bloqueado.status_code == 403, bloqueado.text

    # Admin A remove o override (herdar) — Admin B volta a acessar.
    resposta_remover = client_admin.delete(f"/usuarios/{admin_b.id}/permissoes/permissoes.gerenciar")
    assert resposta_remover.status_code == 204, resposta_remover.text

    restaurado = client_b.get(f"/usuarios/{usuario_operador.id}/permissoes")
    assert restaurado.status_code == 200, restaurado.text


def test_admin_a_concede_permissao_qualquer_a_admin_b(
    app, client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Admin A pode alterar overrides de Admin B (mesmo tenant, não-self) — sem criar
    hierarquia nova entre admins."""
    admin_b = _criar_usuario_com_credencial(db_session, empresa=empresa, perfil_base="admin", email_prefixo="admin-b-2")
    resposta = client_admin.put(f"/usuarios/{admin_b.id}/permissoes/usuarios.criar", json={"efeito": "negar"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["efetivo"] is False


# --------------------------------------------------------------------------------------
# Concorrência mínima (item 36) — upsert repetido não cria duas linhas
# --------------------------------------------------------------------------------------


def test_upsert_repetido_nao_cria_linha_duplicada(
    client_admin: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    for efeito in ("conceder", "negar", "conceder"):
        resposta = client_admin.put(
            f"/usuarios/{usuario_operador.id}/permissoes/clientes.visualizar", json={"efeito": efeito}
        )
        assert resposta.status_code == 200, resposta.text

    repository = UsuarioPermissaoRepository()
    linhas = repository.list_by_usuario(db_session, empresa_id=usuario_operador.empresa_id, usuario_id=usuario_operador.id)
    assert len([linha for linha in linhas if linha.permissao == "clientes.visualizar"]) == 1
