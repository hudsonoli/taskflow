from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.routes import clientes as clientes_route
from app.models.cliente import Cliente
from app.services.cliente_service import ClienteService
from tests.conftest import auth_headers, create_auth_context, make_empresa, persist, persist_agencia


class FailingPublisher:
    def publish(self, db, **kwargs):
        raise RuntimeError("publisher indisponivel")


def now():
    return datetime.now(timezone.utc)


def make_cliente(empresa_id: str, **overrides) -> Cliente:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "agencia_id": None,
        "codigo_interno": f"CLI-{uuid4().hex[:8]}",
        "tipo_pessoa": "juridica",
        "documento": f"{uuid4().int % 10**14:014d}",
        "razao_social": "Cliente Persistido Ltda",
        "nome_fantasia": "Cliente Persistido",
        "nome": None,
        "sigla": "CP",
        "email": None,
        "telefone": None,
        "celular": None,
        "site": None,
        "codigo_externo": None,
        "observacoes": None,
        "status": "ativo",
        "status_alterado_at": None,
        "status_alterado_por_usuario_id": None,
        "motivo_status": None,
        "created_at": current_time,
        "updated_at": current_time,
    }
    data.update(overrides)
    return Cliente(**data)


def payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": "CLI-001",
        "tipoPessoa": "juridica",
        "documento": "12345678000190",
        "razaoSocial": "Cliente Modelo Ltda",
        "nomeFantasia": "Cliente Modelo",
        "sigla": "CM",
    }
    data.update(overrides)
    return data


def test_admin_cria_obtem_atualiza_e_lista_clientes(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    create_response = client.post("/clientes", json=payload(empresa.id), headers=headers)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["empresaId"] == empresa.id
    assert created["status"] == "ativo"

    get_response = client.get(f"/clientes/{created['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["codigoInterno"] == "CLI-001"

    patch_response = client.patch(
        f"/clientes/{created['id']}",
        json={"nomeFantasia": "Cliente Atualizado", "sigla": "CA"},
        headers=headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["nomeFantasia"] == "Cliente Atualizado"

    list_response = client.get("/clientes", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]


def test_listagem_filtros_e_paginacao(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    agencia = persist_agencia(client.session_factory, empresa.id)
    persist(
        client.session_factory,
        make_cliente(empresa.id, agencia_id=agencia.id, codigo_interno="CLI-A", documento="12345678000190", nome_fantasia="Alfa", status="ativo"),
        make_cliente(empresa.id, codigo_interno="CLI-B", documento="22345678000190", nome_fantasia="Beta", status="suspenso"),
        make_cliente(empresa.id, codigo_interno="CLI-C", documento="32345678000190", tipo_pessoa="fisica", nome="Carlos", razao_social=None, nome_fantasia=None, status="ativo"),
    )

    assert len(client.get("/clientes", params={"status": "ativo"}, headers=headers).json()) == 2
    assert len(client.get("/clientes", params={"tipoPessoa": "fisica"}, headers=headers).json()) == 1
    assert len(client.get("/clientes", params={"agenciaId": agencia.id}, headers=headers).json()) == 1
    assert [c["codigoInterno"] for c in client.get("/clientes", params={"busca": "Beta"}, headers=headers).json()] == ["CLI-B"]
    assert len(client.get("/clientes", params={"limit": 1, "offset": 1}, headers=headers).json()) == 1


def test_gestor_tem_acesso_completo(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    create_response = client.post("/clientes", json=payload(empresa.id), headers=headers)
    assert create_response.status_code == 201
    created = create_response.json()

    assert client.get("/clientes", headers=headers).status_code == 200
    assert client.get(f"/clientes/{created['id']}", headers=headers).status_code == 200
    assert client.patch(f"/clientes/{created['id']}", json={"sigla": "CG"}, headers=headers).status_code == 200
    assert client.post(f"/clientes/{created['id']}/suspender", json={"motivo": "pausa"}, headers=headers).status_code == 200
    assert client.post(f"/clientes/{created['id']}/reativar", json={"motivo": "retorno"}, headers=headers).status_code == 200
    assert client.post(f"/clientes/{created['id']}/inativar", json={"motivo": "fim"}, headers=headers).status_code == 200


def test_operador_nao_acessa_endpoints_de_clientes(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    _, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    operador.empresa_id = empresa.id
    persist(client.session_factory, operador)
    admin_headers = auth_headers(client, admin, empresa)
    operador_headers = auth_headers(client, operador, empresa)
    created = client.post("/clientes", json=payload(empresa.id), headers=admin_headers).json()

    assert client.get("/clientes", headers=operador_headers).status_code == 403
    assert client.get(f"/clientes/{created['id']}", headers=operador_headers).status_code == 403
    assert client.post("/clientes", json=payload(empresa.id), headers=operador_headers).status_code == 403
    assert client.patch(f"/clientes/{created['id']}", json={"sigla": "OP"}, headers=operador_headers).status_code == 403
    assert client.post(f"/clientes/{created['id']}/suspender", json={"motivo": "pausa"}, headers=operador_headers).status_code == 403
    assert client.post(f"/clientes/{created['id']}/reativar", json={"motivo": "retorno"}, headers=operador_headers).status_code == 403
    assert client.post(f"/clientes/{created['id']}/inativar", json={"motivo": "fim"}, headers=operador_headers).status_code == 403


def test_usuario_nao_autenticado_recebe_401_em_todos_endpoints(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    admin_headers = auth_headers(client, admin, empresa)
    created = client.post("/clientes", json=payload(empresa.id), headers=admin_headers).json()

    assert client.get("/clientes").status_code == 401
    assert client.get(f"/clientes/{created['id']}").status_code == 401
    assert client.post("/clientes", json=payload(empresa.id)).status_code == 401
    assert client.patch(f"/clientes/{created['id']}", json={"sigla": "NA"}).status_code == 401
    assert client.post(f"/clientes/{created['id']}/suspender", json={"motivo": "pausa"}).status_code == 401
    assert client.post(f"/clientes/{created['id']}/reativar", json={"motivo": "retorno"}).status_code == 401
    assert client.post(f"/clientes/{created['id']}/inativar", json={"motivo": "fim"}).status_code == 401


def test_tenant_isolation_e_404(client):
    empresa_a, admin_a, _ = create_auth_context(client.session_factory, perfil_base="admin")
    empresa_b, _, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin_a, empresa_a)
    cliente_b = persist(client.session_factory, make_cliente(empresa_b.id, codigo_interno="CLI-B", documento="12345678000190"))

    assert client.get(f"/clientes/{cliente_b.id}", headers=headers).status_code == 404
    assert client.patch(f"/clientes/{cliente_b.id}", json={"sigla": "X"}, headers=headers).status_code == 404
    assert client.post(f"/clientes/{cliente_b.id}/suspender", json={"motivo": "pausa"}, headers=headers).status_code == 404
    assert client.get("/clientes", headers=headers).json() == []
    assert client.get(f"/clientes/{uuid4()}", headers=headers).status_code == 404


def test_conflitos_409_e_validacoes_422_400_403(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    outra = persist(client.session_factory, make_empresa())
    agencia_outra = persist_agencia(client.session_factory, outra.id)
    headers = auth_headers(client, admin, empresa)

    created = client.post("/clientes", json=payload(empresa.id), headers=headers).json()
    assert client.post("/clientes", json=payload(empresa.id, documento="22345678000190"), headers=headers).status_code == 409
    assert client.post("/clientes", json=payload(empresa.id, codigoInterno="CLI-002"), headers=headers).status_code == 409
    assert client.post("/clientes", json=payload(str(uuid4()), codigoInterno="CLI-003", documento="32345678000190"), headers=headers).status_code == 403
    assert client.post("/clientes", json=payload(empresa.id, codigoInterno="CLI-004", documento="42345678000190", agenciaId=agencia_outra.id), headers=headers).status_code == 400
    assert client.post("/clientes", json={"empresaId": empresa.id, "codigoInterno": "CLI-X", "tipoPessoa": "fisica"}, headers=headers).status_code == 422
    assert client.patch(f"/clientes/{created['id']}", json={"status": "suspenso"}, headers=headers).status_code == 422


def test_ciclo_de_vida(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = client.post("/clientes", json=payload(empresa.id), headers=headers).json()

    suspenso = client.post(f"/clientes/{created['id']}/suspender", json={"motivo": "pausa"}, headers=headers)
    assert suspenso.status_code == 200
    assert suspenso.json()["status"] == "suspenso"
    assert suspenso.json()["motivoStatus"] == "pausa"
    assert suspenso.json()["statusAlteradoPorUsuarioId"] == admin.id

    assert client.post(f"/clientes/{created['id']}/suspender", json={"motivo": "nova pausa"}, headers=headers).status_code == 409
    ativo = client.post(f"/clientes/{created['id']}/reativar", json={"motivo": "retorno"}, headers=headers)
    assert ativo.status_code == 200
    assert ativo.json()["status"] == "ativo"
    inativo = client.post(f"/clientes/{created['id']}/inativar", json={"motivo": "fim"}, headers=headers)
    assert inativo.status_code == 200
    assert inativo.json()["status"] == "inativo"
    assert client.post(f"/clientes/{created['id']}/inativar", json={"motivo": "fim"}, headers=headers).status_code == 409
    assert client.post(f"/clientes/{created['id']}/suspender", json={}, headers=headers).status_code == 422


def test_rollback_quando_publisher_falha(client, monkeypatch):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    monkeypatch.setattr(clientes_route, "cliente_service", ClienteService(event_publisher=FailingPublisher()))

    with pytest.raises(RuntimeError):
        client.post("/clientes", json=payload(empresa.id), headers=headers)

    with client.session_factory() as db:
        assert db.query(Cliente).filter(Cliente.empresa_id == empresa.id).count() == 0
