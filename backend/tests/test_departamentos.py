from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from conftest import auth_headers, create_auth_context, eventos, make_empresa, persist
from app.domain.event_types import DomainEventType
from app.models.departamento import Departamento
from app.models.equipe import Equipe
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario_departamento import UsuarioDepartamento
from app.schemas.departamento import DepartamentoCreate, DepartamentoUpdate
from app.services.departamento_service import DepartamentoService


def departamento_payload(empresa_id: str, **overrides):
    data = {
        "empresaId": empresa_id,
        "codigoInterno": f" dep-{uuid4().hex[:8]} ",
        "nome": f"  Departamento   {uuid4().hex[:8]}  ",
        "descricao": "  Departamento   operacional  ",
    }
    data.update(overrides)
    return data


def make_departamento(empresa_id: str, **overrides) -> Departamento:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "codigo_interno": f"DEP-{uuid4().hex[:8]}",
        "nome": f"Departamento {uuid4().hex[:8]}",
        "descricao": "Departamento operacional",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Departamento(**data)


def persist_departamento(session_factory, empresa_id: str, **overrides) -> Departamento:
    return persist(session_factory, make_departamento(empresa_id, **overrides))


def make_usuario_departamento(empresa_id: str, usuario_id: str, departamento_id: str, **overrides) -> UsuarioDepartamento:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "usuario_id": usuario_id,
        "departamento_id": departamento_id,
        "papel": "membro",
        "principal": False,
        "status": "ativo",
        "inicio_em": now,
        "fim_em": None,
        "motivo_encerramento": None,
        "criado_por_usuario_id": None,
        "encerrado_por_usuario_id": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return UsuarioDepartamento(**data)


def make_sessao_trabalho(empresa_id: str, departamento_id: str, **overrides) -> SessaoTrabalho:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "agencia_id": None,
        "demanda_id": str(uuid4()),
        "workflow_etapa_id": None,
        "usuario_id": None,
        "departamento_id": departamento_id,
        "evento_inicio_id": str(uuid4()),
        "evento_fim_id": None,
        "status": "ativa",
        "inicio_em": now,
        "fim_em": None,
        "duracao_segundos": None,
        "motivo_encerramento": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SessaoTrabalho(**data)


def make_equipe(empresa_id: str, departamento_id: str, **overrides) -> Equipe:
    now = datetime.now(timezone.utc)
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "departamento_id": departamento_id,
        "codigo_interno": f"EQ-{uuid4().hex[:8]}",
        "nome": f"Equipe {uuid4().hex[:8]}",
        "descricao": "Equipe operacional",
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
        "inativado_at": None,
        "motivo_inativacao": None,
        "inativado_por_usuario_id": None,
    }
    data.update(overrides)
    return Equipe(**data)


def create_departamento(client, headers, empresa_id: str, **overrides):
    response = client.post("/departamentos", json=departamento_payload(empresa_id, **overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def departamentos(session_factory) -> list[Departamento]:
    with session_factory() as db:
        return list(db.query(Departamento).all())


class FailingPublisher:
    def publish(self, *args, **kwargs):
        raise RuntimeError("falha evento")


def test_departamentos_endpoints_require_authentication(client):
    response = client.get("/departamentos", params={"empresaId": str(uuid4())})

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get("/departamentos", params={"empresaId": str(uuid4())}, headers={"Authorization": "Bearer invalido"})

    assert response.status_code == 401


def test_admin_creates_departamento_with_normalization_and_authenticated_actor(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    departamento = create_departamento(
        client,
        headers,
        empresa.id,
        codigoInterno=" dep-001 ",
        nome="  Atendimento   Digital  ",
        descricao="   ",
    )

    assert departamento["empresaId"] == empresa.id
    assert departamento["codigoInterno"] == "DEP-001"
    assert departamento["nome"] == "Atendimento Digital"
    assert departamento["descricao"] is None
    departamento_events = [evento for evento in eventos(client.session_factory) if evento.tipo == DomainEventType.DEPARTAMENTO_CRIADO.value]
    assert len(departamento_events) == 1
    assert departamento_events[0].usuario_id == admin.id
    assert departamento_events[0].payload["actor_usuario_id"] == admin.id


def test_gestor_cannot_create_departamento(client):
    empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    headers = auth_headers(client, gestor, empresa)

    response = client.post("/departamentos", json=departamento_payload(empresa.id), headers=headers)

    assert response.status_code == 403


def test_operador_cannot_access_departamentos(client):
    empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    headers = auth_headers(client, operador, empresa)

    response = client.get("/departamentos", params={"empresaId": empresa.id}, headers=headers)

    assert response.status_code == 403


def test_admin_cannot_create_departamento_in_other_empresa(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.post("/departamentos", json=departamento_payload(other.id), headers=headers)

    assert response.status_code == 403


def test_create_departamento_missing_or_inactive_empresa_still_validates_in_service(session_factory):
    service = DepartamentoService()

    with pytest.raises(Exception, match="Empresa não encontrada"):
        with session_factory() as db:
            service.create_departamento(db, DepartamentoCreate(**departamento_payload(str(uuid4()))))

    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    with session_factory() as db:
        persisted = db.get(type(empresa), empresa.id)
        persisted.status = "inativa"
        db.commit()

    with pytest.raises(Exception, match="Empresa inativa não permite criação de Departamento"):
        with session_factory() as db:
            service.create_departamento(db, DepartamentoCreate(**departamento_payload(empresa.id)))


def test_create_departamento_rejects_empty_codigo_and_nome_after_normalization(session_factory):
    service = DepartamentoService()
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")

    with pytest.raises(Exception, match="codigoInterno é obrigatório"):
        with session_factory() as db:
            service.create_departamento(db, DepartamentoCreate(**departamento_payload(empresa.id, codigoInterno="   ")))

    with pytest.raises(Exception, match="nome é obrigatório"):
        with session_factory() as db:
            service.create_departamento(db, DepartamentoCreate(**departamento_payload(empresa.id, nome="   ")))


def test_departamento_duplicates_and_cross_empresa_rules_with_authenticated_api(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other_empresa, other_admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    other_headers = auth_headers(client, other_admin, other_empresa)

    create_departamento(client, headers, empresa.id, codigoInterno="DEP-DUP", nome="Atendimento")

    duplicate_codigo = client.post("/departamentos", json=departamento_payload(empresa.id, codigoInterno=" dep-dup ", nome="Midia"), headers=headers)
    duplicate_nome = client.post("/departamentos", json=departamento_payload(empresa.id, codigoInterno="DEP-2", nome="  Atendimento  "), headers=headers)
    same_values_other = client.post("/departamentos", json=departamento_payload(other_empresa.id, codigoInterno=" dep-dup ", nome="Atendimento"), headers=other_headers)

    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409
    assert same_values_other.status_code == 201


def test_admin_and_gestor_list_departamentos_from_own_empresa_and_filter_status(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    active = persist_departamento(client.session_factory, empresa.id, codigo_interno="DEP-A", nome="Departamento Ativo")
    inactive = persist_departamento(client.session_factory, empresa.id, codigo_interno="DEP-I", nome="Departamento Inativo", status="inativa")
    gestor_departamento = persist_departamento(client.session_factory, gestor_empresa.id, codigo_interno="DEP-G", nome="Departamento Gestor")
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    admin_response = client.get("/departamentos", params={"empresaId": empresa.id, "status": "ativa"}, headers=admin_headers)
    gestor_response = client.get("/departamentos", params={"empresaId": gestor_empresa.id}, headers=gestor_headers)

    assert admin_response.status_code == 200
    assert [item["id"] for item in admin_response.json()] == [active.id]
    assert inactive.id not in [item["id"] for item in admin_response.json()]
    assert gestor_response.status_code == 200
    assert [item["id"] for item in gestor_response.json()] == [gestor_departamento.id]


def test_list_departamentos_requires_empresa_id_for_authenticated_user(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)

    response = client.get("/departamentos", headers=headers)

    assert response.status_code == 422


def test_list_departamentos_rejects_divergent_empresa_id(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    headers = auth_headers(client, admin, empresa)

    response = client.get("/departamentos", params={"empresaId": other.id}, headers=headers)

    assert response.status_code == 403


def test_get_departamento_by_id_and_other_tenant_returns_404(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    other = persist(client.session_factory, make_empresa(codigo_interno="OUTRA"))
    own_departamento = persist_departamento(client.session_factory, empresa.id, codigo_interno="DEP-OWN", nome="Departamento Proprio")
    other_departamento = persist_departamento(client.session_factory, other.id, codigo_interno="DEP-OUT", nome="Departamento Outro")
    headers = auth_headers(client, admin, empresa)

    own_response = client.get(f"/departamentos/{own_departamento.id}", headers=headers)
    other_response = client.get(f"/departamentos/{other_departamento.id}", headers=headers)

    assert own_response.status_code == 200
    assert own_response.json()["id"] == own_departamento.id
    assert other_response.status_code == 404


def test_admin_updates_departamento_and_gestor_operador_cannot_update(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    operador_empresa, operador, _ = create_auth_context(client.session_factory, perfil_base="operador")
    departamento = persist_departamento(client.session_factory, empresa.id)
    gestor_departamento = persist_departamento(client.session_factory, gestor_empresa.id)
    operador_departamento = persist_departamento(client.session_factory, operador_empresa.id)
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)
    operador_headers = auth_headers(client, operador, operador_empresa)

    response = client.patch(
        f"/departamentos/{departamento.id}",
        json={"codigoInterno": " dep-009 ", "nome": " Atendimento   Digital ", "descricao": "  operacao  "},
        headers=admin_headers,
    )
    gestor_response = client.patch(f"/departamentos/{gestor_departamento.id}", json={"nome": "Bloqueado"}, headers=gestor_headers)
    operador_response = client.patch(f"/departamentos/{operador_departamento.id}", json={"nome": "Bloqueado"}, headers=operador_headers)

    assert response.status_code == 200
    assert response.json()["codigoInterno"] == "DEP-009"
    assert response.json()["nome"] == "Atendimento Digital"
    assert response.json()["descricao"] == "operacao"
    assert gestor_response.status_code == 403
    assert operador_response.status_code == 403


def test_departamento_patch_rejects_forbidden_fields_with_authenticated_admin(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    for field, value in [
        ("empresaId", str(uuid4())),
        ("status", "inativa"),
        ("createdAt", "2026-07-15T00:00:00Z"),
        ("updatedAt", "2026-07-15T00:00:00Z"),
        ("inativadoAt", "2026-07-15T00:00:00Z"),
        ("motivoInativacao", "teste"),
        ("inativadoPorUsuarioId", str(uuid4())),
    ]:
        response = client.patch(f"/departamentos/{departamento.id}", json={field: value}, headers=headers)
        assert response.status_code == 422
        assert field in response.json()["detail"]


def test_update_departamento_rejects_duplicates_after_normalization(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    first = persist_departamento(client.session_factory, empresa.id, codigo_interno="DEP-1", nome="Atendimento")
    second = persist_departamento(client.session_factory, empresa.id, codigo_interno="DEP-2", nome="Midia")
    headers = auth_headers(client, admin, empresa)

    duplicate_codigo = client.patch(f"/departamentos/{second.id}", json={"codigoInterno": " dep-1 "}, headers=headers)
    duplicate_nome = client.patch(f"/departamentos/{second.id}", json={"nome": "  Atendimento  "}, headers=headers)

    assert first.id
    assert duplicate_codigo.status_code == 409
    assert duplicate_nome.status_code == 409


def test_admin_status_actions_use_authenticated_actor_and_gestor_cannot_mutate(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    gestor_empresa, gestor, _ = create_auth_context(client.session_factory, perfil_base="gestor")
    departamento = persist_departamento(client.session_factory, empresa.id)
    gestor_departamento = persist_departamento(client.session_factory, gestor_empresa.id)
    fake_actor = str(uuid4())
    admin_headers = auth_headers(client, admin, empresa)
    gestor_headers = auth_headers(client, gestor, gestor_empresa)

    inactivate = client.post(
        f"/departamentos/{departamento.id}/inativar",
        json={"motivoInativacao": "encerramento", "actorUsuarioId": fake_actor},
        headers=admin_headers,
    )
    gestor_inactivate = client.post(f"/departamentos/{gestor_departamento.id}/inativar", json={"motivoInativacao": "teste"}, headers=gestor_headers)

    assert inactivate.status_code == 422
    inactivate = client.post(f"/departamentos/{departamento.id}/inativar", json={"motivoInativacao": "encerramento"}, headers=admin_headers)
    reactivate = client.post(f"/departamentos/{departamento.id}/reativar", headers=admin_headers)
    assert inactivate.status_code == 200
    assert inactivate.json()["inativadoPorUsuarioId"] == admin.id
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "ativa"
    assert gestor_inactivate.status_code == 403
    departamento_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "departamento" and evento.entidade_id == departamento.id]
    assert [evento.tipo for evento in departamento_events] == [DomainEventType.DEPARTAMENTO_INATIVADO.value, DomainEventType.DEPARTAMENTO_REATIVADO.value]
    for evento in departamento_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["actor_usuario_id"] == admin.id


@pytest.mark.parametrize("papel", ["membro", "head", "gestor"])
def test_inativar_departamento_com_vinculo_ativo_retorna_409_sem_alterar_estado(client, papel):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    persist(
        client.session_factory,
        make_usuario_departamento(empresa.id, admin.id, departamento.id, papel=papel),
    )
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/departamentos/{departamento.id}/inativar",
        json={"motivoInativacao": "teste"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Departamento possui vínculos ativos de Usuários"}
    with client.session_factory() as db:
        persisted = db.get(Departamento, departamento.id)
        assert persisted.status == "ativa"
        assert persisted.inativado_at is None
        assert persisted.motivo_inativacao is None
        assert persisted.inativado_por_usuario_id is None
    assert not [
        evento
        for evento in eventos(client.session_factory)
        if evento.entidade_id == departamento.id and evento.tipo == DomainEventType.DEPARTAMENTO_INATIVADO.value
    ]


def test_inativar_departamento_com_equipe_ativa_retorna_409_sem_alterar_estado(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    persist(
        client.session_factory,
        make_equipe(empresa.id, departamento.id),
    )
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/departamentos/{departamento.id}/inativar",
        json={"motivoInativacao": "teste"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Departamento possui Equipes ativas vinculadas"}
    with client.session_factory() as db:
        persisted = db.get(Departamento, departamento.id)
        assert persisted.status == "ativa"
        assert persisted.inativado_at is None
        assert persisted.motivo_inativacao is None
        assert persisted.inativado_por_usuario_id is None
    assert not [
        evento
        for evento in eventos(client.session_factory)
        if evento.entidade_id == departamento.id
        and evento.tipo == DomainEventType.DEPARTAMENTO_INATIVADO.value
    ]


@pytest.mark.parametrize("status_equipe", ["inativa", "arquivada"])
def test_inativar_departamento_com_equipe_nao_ativa_e_permitido(client, status_equipe):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    persist(
        client.session_factory,
        make_equipe(
            empresa.id,
            departamento.id,
            status=status_equipe,
        ),
    )
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/departamentos/{departamento.id}/inativar",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inativa"


def test_inativar_departamento_com_vinculo_inativo_e_permitido(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    now = datetime.now(timezone.utc)
    persist(
        client.session_factory,
        make_usuario_departamento(
            empresa.id,
            admin.id,
            departamento.id,
            status="inativo",
            fim_em=now + timedelta(seconds=1),
            motivo_encerramento="encerrado",
        ),
    )
    headers = auth_headers(client, admin, empresa)

    response = client.post(f"/departamentos/{departamento.id}/inativar", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "inativa"


def test_inativar_departamento_com_sessao_ativa_retorna_409_sem_alterar_estado(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    persist(client.session_factory, make_sessao_trabalho(empresa.id, departamento.id))
    headers = auth_headers(client, admin, empresa)

    response = client.post(
        f"/departamentos/{departamento.id}/inativar",
        json={"motivoInativacao": "teste"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Departamento possui sessões de trabalho ativas"}
    with client.session_factory() as db:
        persisted = db.get(Departamento, departamento.id)
        assert persisted.status == "ativa"
        assert persisted.inativado_at is None
        assert persisted.motivo_inativacao is None
        assert persisted.inativado_por_usuario_id is None
    assert not [
        evento
        for evento in eventos(client.session_factory)
        if evento.entidade_id == departamento.id and evento.tipo == DomainEventType.DEPARTAMENTO_INATIVADO.value
    ]


@pytest.mark.parametrize("status_sessao", ["encerrada", "cancelada"])
def test_inativar_departamento_com_sessao_nao_ativa_e_permitido(client, status_sessao):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    now = datetime.now(timezone.utc)
    persist(
        client.session_factory,
        make_sessao_trabalho(
            empresa.id,
            departamento.id,
            status=status_sessao,
            evento_fim_id=str(uuid4()),
            fim_em=now + timedelta(seconds=1),
            duracao_segundos=0,
            motivo_encerramento="conclusao",
        ),
    )
    headers = auth_headers(client, admin, empresa)

    response = client.post(f"/departamentos/{departamento.id}/inativar", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "inativa"


def test_inativar_departamento_sem_dependencias_ativas_e_permitido(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.post(f"/departamentos/{departamento.id}/inativar", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "inativa"


def test_invalid_status_transitions_are_rejected(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    reactivate_active = client.post(f"/departamentos/{departamento.id}/reativar", headers=headers)
    client.post(f"/departamentos/{departamento.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    inactivate_inactive = client.post(f"/departamentos/{departamento.id}/inativar", json={"motivoInativacao": "teste"}, headers=headers)

    assert reactivate_active.status_code == 409
    assert reactivate_active.json() == {"detail": "Departamento já está ativo"}
    assert inactivate_inactive.status_code == 409
    assert inactivate_inactive.json() == {"detail": "Departamento já está inativo"}


def test_archived_departamento_cannot_be_reactivated(session_factory):
    service = DepartamentoService()
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento = persist_departamento(session_factory, empresa.id, status="arquivada")

    with pytest.raises(Exception, match="Departamento arquivado não pode ser reativado"):
        with session_factory() as db:
            service.reativar_departamento(db, departamento.id, actor_usuario_id=actor.id)


def test_departamento_events_full_sequence_with_restricted_payload(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    headers = auth_headers(client, admin, empresa)
    created = create_departamento(client, headers, empresa.id, codigoInterno="DEP-EVENTOS", nome="Departamento Eventos")

    client.patch(f"/departamentos/{created['id']}", json={"nome": "Departamento Alterado", "descricao": "nova descricao"}, headers=headers)
    client.post(f"/departamentos/{created['id']}/inativar", json={"motivoInativacao": "teste"}, headers=headers)
    client.post(f"/departamentos/{created['id']}/reativar", headers=headers)

    persisted_events = [evento for evento in eventos(client.session_factory) if evento.entidade_tipo == "departamento" and evento.entidade_id == created["id"]]
    assert [evento.tipo for evento in persisted_events] == [
        DomainEventType.DEPARTAMENTO_CRIADO.value,
        DomainEventType.DEPARTAMENTO_ALTERADO.value,
        DomainEventType.DEPARTAMENTO_INATIVADO.value,
        DomainEventType.DEPARTAMENTO_REATIVADO.value,
    ]
    for evento in persisted_events:
        assert evento.usuario_id == admin.id
        assert evento.payload["empresa_id"] == empresa.id
        assert evento.payload["departamento_id"] == created["id"]
        assert evento.payload["actor_usuario_id"] == admin.id
        assert "timestamp" in evento.payload
        assert "nome" not in evento.payload
        assert "codigo_interno" not in evento.payload
        assert "codigoInterno" not in evento.payload
        assert "descricao" not in evento.payload
    alterado = [evento for evento in persisted_events if evento.tipo == DomainEventType.DEPARTAMENTO_ALTERADO.value][0]
    assert alterado.payload["campos_alterados"] == ["nome", "descricao"]


def test_service_create_departamento_rolls_back_when_event_publish_fails(session_factory):
    empresa, _, _ = create_auth_context(session_factory, perfil_base="admin")
    service = DepartamentoService(event_publisher=FailingPublisher())
    data = DepartamentoCreate(empresaId=empresa.id, codigoInterno="DEP-ROLLBACK", nome="Departamento Rollback")

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.create_departamento(db, data)

    assert [departamento for departamento in departamentos(session_factory) if departamento.codigo_interno == "DEP-ROLLBACK"] == []


def test_service_update_departamento_rolls_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    departamento = persist_departamento(session_factory, empresa.id, nome="Departamento Original")
    service = DepartamentoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.update_departamento(db, departamento.id, DepartamentoUpdate(nome="Departamento Alterado"), actor_usuario_id=actor.id)

    with session_factory() as db:
        persisted = db.get(Departamento, departamento.id)
        assert persisted.nome == "Departamento Original"


def test_service_status_actions_roll_back_when_event_publish_fails(session_factory):
    empresa, actor, _ = create_auth_context(session_factory, perfil_base="admin")
    active = persist_departamento(session_factory, empresa.id, codigo_interno="DEP-A", nome="Departamento Ativo")
    inactive = persist_departamento(session_factory, empresa.id, codigo_interno="DEP-I", nome="Departamento Inativo", status="inativa")
    service = DepartamentoService(event_publisher=FailingPublisher())

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.inativar_departamento(db, active.id, motivo_inativacao="teste", actor_usuario_id=actor.id)

    with pytest.raises(RuntimeError, match="falha evento"):
        with session_factory() as db:
            service.reativar_departamento(db, inactive.id, actor_usuario_id=actor.id)

    with session_factory() as db:
        assert db.get(Departamento, active.id).status == "ativa"
        assert db.get(Departamento, inactive.id).status == "inativa"


def test_delete_route_does_not_exist(client):
    empresa, admin, _ = create_auth_context(client.session_factory, perfil_base="admin")
    departamento = persist_departamento(client.session_factory, empresa.id)
    headers = auth_headers(client, admin, empresa)

    response = client.delete(f"/departamentos/{departamento.id}", headers=headers)

    assert response.status_code == 405
