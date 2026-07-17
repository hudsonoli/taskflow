from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.services.cliente_service import (
    ClienteConflictError,
    ClienteInvalidActorError,
    ClienteInvalidAgenciaError,
    ClienteInvalidDataError,
    ClienteInvalidEmpresaError,
    ClienteInvalidTransitionError,
    ClienteNotFoundError,
    ClienteService,
)
from tests.conftest import make_empresa, make_usuario, persist, persist_agencia


class RecordingPublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.events = []

    def publish(self, db, **kwargs):
        if self.fail:
            raise RuntimeError("evento falhou")
        self.events.append(kwargs)
        return None


def now():
    return datetime.now(timezone.utc)


def make_cliente_model(empresa_id: str, **overrides) -> Cliente:
    current_time = now()
    data = {
        "id": str(uuid4()),
        "empresa_id": empresa_id,
        "agencia_id": None,
        "codigo_interno": f"CLI-{uuid4().hex[:8]}",
        "tipo_pessoa": "juridica",
        "documento": f"{uuid4().int % 10**14:014d}",
        "razao_social": "Cliente Existente Ltda",
        "nome_fantasia": "Cliente Existente",
        "nome": None,
        "sigla": "CLI",
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


def create_payload(empresa_id: str, **overrides) -> ClienteCreate:
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
    return ClienteCreate.model_validate(data)


def get_cliente(session_factory, empresa_id: str, cliente_id: str) -> Cliente | None:
    service = ClienteService(event_publisher=RecordingPublisher())
    with session_factory() as db:
        try:
            return service.obter_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
        except ClienteNotFoundError:
            return None


def test_criar_cliente_valido_forca_status_ativo_e_publica_evento(session_factory):
    emp = persist(session_factory, make_empresa())
    publisher = RecordingPublisher()
    service = ClienteService(event_publisher=publisher)

    with session_factory() as db:
        cliente = service.criar_cliente(
            db,
            create_payload(emp.id, status="ativo"),
            empresa_id=emp.id,
            actor_usuario_id="ator-1",
        )

    assert cliente.status == "ativo"
    assert cliente.codigo_interno == "CLI-001"
    assert publisher.events[0]["tipo"].value == "cliente.criado"
    assert publisher.events[0]["payload"] == {"empresa_id": emp.id, "cliente_id": cliente.id}


def test_criar_cliente_rejeita_empresa_divergente_ou_inativa(session_factory):
    emp = persist(session_factory, make_empresa())
    outra = persist(session_factory, make_empresa(status="inativa"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        with pytest.raises(ClienteInvalidEmpresaError):
            service.criar_cliente(db, create_payload(emp.id), empresa_id=outra.id)
        with pytest.raises(ClienteInvalidEmpresaError):
            service.criar_cliente(db, create_payload(outra.id, codigoInterno="CLI-002"), empresa_id=outra.id)


def test_criar_cliente_valida_unicidade_e_permite_mesmos_valores_em_empresas_diferentes(session_factory):
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        service.criar_cliente(db, create_payload(emp_a.id), empresa_id=emp_a.id)
        service.criar_cliente(db, create_payload(emp_b.id), empresa_id=emp_b.id)
        with pytest.raises(ClienteConflictError):
            service.criar_cliente(db, create_payload(emp_a.id, documento="22345678000190"), empresa_id=emp_a.id)
        with pytest.raises(ClienteConflictError):
            service.criar_cliente(db, create_payload(emp_a.id, codigoInterno="CLI-002"), empresa_id=emp_a.id)


def test_criar_cliente_valida_agencia(session_factory):
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    agencia_a = persist_agencia(session_factory, emp_a.id)
    agencia_b = persist_agencia(session_factory, emp_b.id)
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        cliente = service.criar_cliente(db, create_payload(emp_a.id, agenciaId=agencia_a.id), empresa_id=emp_a.id)
        assert cliente.agencia_id == agencia_a.id
        with pytest.raises(ClienteInvalidAgenciaError):
            service.criar_cliente(db, create_payload(emp_a.id, codigoInterno="CLI-002", documento="22345678000190", agenciaId=agencia_b.id), empresa_id=emp_a.id)
        with pytest.raises(ClienteInvalidAgenciaError):
            service.criar_cliente(db, create_payload(emp_a.id, codigoInterno="CLI-003", documento="32345678000190", agenciaId=str(uuid4())), empresa_id=emp_a.id)


def test_criar_cliente_rollback_quando_evento_falha(session_factory):
    emp = persist(session_factory, make_empresa())
    service = ClienteService(event_publisher=RecordingPublisher(fail=True))

    with session_factory() as db:
        with pytest.raises(RuntimeError):
            service.criar_cliente(db, create_payload(emp.id), empresa_id=emp.id)

    with session_factory() as db:
        assert service.listar_clientes(db, empresa_id=emp.id) == []


def test_obter_listar_e_tenant(session_factory):
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    cliente_a = persist(session_factory, make_cliente_model(emp_a.id, codigo_interno="CLI-A", documento="12345678000190"))
    persist(session_factory, make_cliente_model(emp_b.id, codigo_interno="CLI-B", documento="22345678000190"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        assert service.obter_cliente(db, empresa_id=emp_a.id, cliente_id=cliente_a.id).id == cliente_a.id
        with pytest.raises(ClienteNotFoundError):
            service.obter_cliente(db, empresa_id=emp_b.id, cliente_id=cliente_a.id)
        assert [c.codigo_interno for c in service.listar_clientes(db, empresa_id=emp_a.id)] == ["CLI-A"]


def test_to_response_usa_from_attributes_aliases_uuid_e_timezone(session_factory):
    emp = persist(session_factory, make_empresa())
    actor = persist(session_factory, make_usuario(emp.id))
    cliente = persist(
        session_factory,
        make_cliente_model(
            emp.id,
            status="suspenso",
            status_alterado_at=now(),
            status_alterado_por_usuario_id=actor.id,
        ),
    )
    service = ClienteService(event_publisher=RecordingPublisher())

    response = service.to_response(cliente)
    dumped = response.model_dump(by_alias=True)

    assert str(response.id) == cliente.id
    assert str(response.status_alterado_por_usuario_id) == actor.id
    assert dumped["statusAlteradoPorUsuarioId"] == response.status_alterado_por_usuario_id
    assert dumped["codigoInterno"] == cliente.codigo_interno
    assert dumped["createdAt"].tzinfo is not None
    assert dumped["updatedAt"].tzinfo is not None


def test_atualizar_cliente_campos_permitidos_e_evento_seguro(session_factory):
    emp = persist(session_factory, make_empresa())
    cliente = persist(session_factory, make_cliente_model(emp.id, codigo_interno="CLI-001", documento="12345678000190"))
    publisher = RecordingPublisher()
    service = ClienteService(event_publisher=publisher)

    with session_factory() as db:
        updated = service.atualizar_cliente(
            db,
            empresa_id=emp.id,
            cliente_id=cliente.id,
            data=ClienteUpdate.model_validate(
                {
                    "codigoInterno": " cli-002 ",
                    "nomeFantasia": "Novo Nome",
                    "documento": "22345678000190",
                    "email": "novo@cliente.com",
                }
            ),
            actor_usuario_id="ator-1",
        )

    assert updated.codigo_interno == "CLI-002"
    assert updated.nome_fantasia == "Novo Nome"
    payload = publisher.events[0]["payload"]
    assert payload["empresa_id"] == emp.id
    assert payload["cliente_id"] == cliente.id
    assert set(payload["campos_alterados"]) == {"codigo_interno", "nome_fantasia", "documento", "email"}
    assert "22345678000190" not in str(payload)
    assert "Novo Nome" not in str(payload)


def test_atualizar_cliente_somente_campos_enviados(session_factory):
    emp = persist(session_factory, make_empresa())
    cliente = persist(session_factory, make_cliente_model(emp.id, nome_fantasia="Original", documento="12345678000190"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        updated = service.atualizar_cliente(
            db,
            empresa_id=emp.id,
            cliente_id=cliente.id,
            data=ClienteUpdate.model_validate({"sigla": " nv "}),
        )

    assert updated.sigla == "NV"
    assert updated.nome_fantasia == "Original"
    assert updated.documento == "12345678000190"


def test_atualizar_cliente_valida_conflitos_e_agencia(session_factory):
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    agencia_b = persist_agencia(session_factory, emp_b.id)
    cliente_a = persist(session_factory, make_cliente_model(emp_a.id, codigo_interno="CLI-001", documento="12345678000190"))
    persist(session_factory, make_cliente_model(emp_a.id, codigo_interno="CLI-002", documento="22345678000190"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        with pytest.raises(ClienteConflictError):
            service.atualizar_cliente(db, empresa_id=emp_a.id, cliente_id=cliente_a.id, data=ClienteUpdate.model_validate({"codigoInterno": "CLI-002"}))
        with pytest.raises(ClienteConflictError):
            service.atualizar_cliente(db, empresa_id=emp_a.id, cliente_id=cliente_a.id, data=ClienteUpdate.model_validate({"documento": "22345678000190"}))
        with pytest.raises(ClienteInvalidAgenciaError):
            service.atualizar_cliente(db, empresa_id=emp_a.id, cliente_id=cliente_a.id, data=ClienteUpdate.model_validate({"agenciaId": agencia_b.id}))


def test_atualizar_cliente_valida_estado_final_tipo_pessoa(session_factory):
    emp = persist(session_factory, make_empresa())
    pj = persist(session_factory, make_cliente_model(emp.id, codigo_interno="PJ", documento="12345678000190", nome=None))
    pj_com_nome = persist(session_factory, make_cliente_model(emp.id, codigo_interno="PJ2", documento="32345678000190", nome="Joao"))
    pf = persist(session_factory, make_cliente_model(emp.id, codigo_interno="PF", tipo_pessoa="fisica", documento="12345678901", nome="Maria", razao_social=None, nome_fantasia=None))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        ok_pf = service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pj.id, data=ClienteUpdate.model_validate({"tipoPessoa": "fisica", "documento": "12345678902", "nome": "Joao"}))
        assert ok_pf.tipo_pessoa == "fisica"

    with session_factory() as db:
        with pytest.raises(ClienteInvalidDataError):
            service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pf.id, data=ClienteUpdate.model_validate({"tipoPessoa": "juridica"}))
        with pytest.raises(ClienteInvalidDataError):
            service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pj_com_nome.id, data=ClienteUpdate.model_validate({"tipoPessoa": "fisica"}))
        with pytest.raises(ClienteInvalidDataError):
            service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pf.id, data=ClienteUpdate.model_validate({"tipoPessoa": "juridica", "razaoSocial": "Empresa Ltda"}))
        ok_pj = service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pf.id, data=ClienteUpdate.model_validate({"tipoPessoa": "juridica", "documento": "12345678000191", "razaoSocial": "Empresa Ltda"}))
        assert ok_pj.tipo_pessoa == "juridica"


def test_atualizar_cliente_rejeita_remocao_de_nome_obrigatorio_e_status_direto(session_factory):
    emp = persist(session_factory, make_empresa())
    pf = persist(session_factory, make_cliente_model(emp.id, tipo_pessoa="fisica", documento="12345678901", nome="Maria", razao_social=None, nome_fantasia=None))
    service = ClienteService(event_publisher=RecordingPublisher())

    with pytest.raises(ValidationError):
        ClienteUpdate.model_validate({"status": "suspenso"})
    with session_factory() as db:
        with pytest.raises(ClienteInvalidDataError):
            service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=pf.id, data=ClienteUpdate.model_validate({"nome": None}))


def test_atualizar_cliente_rollback_quando_evento_falha(session_factory):
    emp = persist(session_factory, make_empresa())
    cliente = persist(session_factory, make_cliente_model(emp.id, nome_fantasia="Antes"))
    service = ClienteService(event_publisher=RecordingPublisher(fail=True))

    with session_factory() as db:
        with pytest.raises(RuntimeError):
            service.atualizar_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, data=ClienteUpdate.model_validate({"nomeFantasia": "Depois"}))

    assert get_cliente(session_factory, emp.id, cliente.id).nome_fantasia == "Antes"


def test_ciclo_de_vida_suspender_reativar_inativar_e_eventos(session_factory):
    emp = persist(session_factory, make_empresa())
    actor = persist(session_factory, make_usuario(emp.id))
    cliente = persist(session_factory, make_cliente_model(emp.id, status="ativo"))
    publisher = RecordingPublisher()
    service = ClienteService(event_publisher=publisher)

    with session_factory() as db:
        suspenso = service.suspender_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, motivo=" pausa ", actor_usuario_id=actor.id)
        assert suspenso.status == "suspenso"
        assert suspenso.motivo_status == "pausa"
        assert suspenso.status_alterado_por_usuario_id == actor.id
        assert suspenso.status_alterado_at is not None

    with session_factory() as db:
        ativo = service.reativar_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, motivo="retorno", actor_usuario_id=actor.id)
        assert ativo.status == "ativo"

    with session_factory() as db:
        inativo = service.inativar_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, motivo="encerrado", actor_usuario_id=actor.id)
        assert inativo.status == "inativo"

    assert [event["tipo"].value for event in publisher.events] == ["cliente.suspenso", "cliente.reativado", "cliente.inativado"]
    for event in publisher.events:
        payload = event["payload"]
        assert payload["cliente_id"] == cliente.id
        assert payload["empresa_id"] == emp.id
        assert payload["actor_usuario_id"] == actor.id
        assert "motivo" not in payload
        assert "documento" not in payload


def test_ciclo_de_vida_suspenso_para_inativo_e_inativo_para_ativo(session_factory):
    emp = persist(session_factory, make_empresa())
    actor = persist(session_factory, make_usuario(emp.id))
    cliente = persist(session_factory, make_cliente_model(emp.id, status="suspenso"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        inativo = service.inativar_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, motivo="fim", actor_usuario_id=actor.id)
        assert inativo.status == "inativo"
    with session_factory() as db:
        ativo = service.reativar_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, actor_usuario_id=actor.id)
        assert ativo.status == "ativo"


def test_ciclo_de_vida_transicoes_invalidas_e_motivo_obrigatorio(session_factory):
    emp = persist(session_factory, make_empresa())
    actor = persist(session_factory, make_usuario(emp.id))
    ativo = persist(session_factory, make_cliente_model(emp.id, codigo_interno="A", status="ativo"))
    suspenso = persist(session_factory, make_cliente_model(emp.id, codigo_interno="S", documento="12345678000191", status="suspenso"))
    inativo = persist(session_factory, make_cliente_model(emp.id, codigo_interno="I", documento="12345678000192", status="inativo"))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        with pytest.raises(ClienteInvalidDataError):
            service.suspender_cliente(db, empresa_id=emp.id, cliente_id=ativo.id, motivo=" ", actor_usuario_id=actor.id)
        with pytest.raises(ClienteInvalidTransitionError):
            service.reativar_cliente(db, empresa_id=emp.id, cliente_id=ativo.id, actor_usuario_id=actor.id)
        with pytest.raises(ClienteInvalidTransitionError):
            service.suspender_cliente(db, empresa_id=emp.id, cliente_id=suspenso.id, motivo="pausa", actor_usuario_id=actor.id)
        with pytest.raises(ClienteInvalidTransitionError):
            service.inativar_cliente(db, empresa_id=emp.id, cliente_id=inativo.id, motivo="fim", actor_usuario_id=actor.id)
        with pytest.raises(ClienteInvalidTransitionError):
            service.suspender_cliente(db, empresa_id=emp.id, cliente_id=inativo.id, motivo="pausa", actor_usuario_id=actor.id)


def test_ciclo_de_vida_valida_ator_e_tenant(session_factory):
    emp_a, emp_b = persist(session_factory, make_empresa(), make_empresa())
    actor_b = persist(session_factory, make_usuario(emp_b.id))
    cliente = persist(session_factory, make_cliente_model(emp_a.id))
    service = ClienteService(event_publisher=RecordingPublisher())

    with session_factory() as db:
        with pytest.raises(ClienteInvalidActorError):
            service.suspender_cliente(db, empresa_id=emp_a.id, cliente_id=cliente.id, motivo="pausa", actor_usuario_id=actor_b.id)
        with pytest.raises(ClienteInvalidActorError):
            service.suspender_cliente(db, empresa_id=emp_a.id, cliente_id=cliente.id, motivo="pausa", actor_usuario_id=str(uuid4()))
        with pytest.raises(ClienteNotFoundError):
            service.suspender_cliente(db, empresa_id=emp_b.id, cliente_id=cliente.id, motivo="pausa", actor_usuario_id=actor_b.id)


def test_ciclo_de_vida_rollback_quando_evento_falha(session_factory):
    emp = persist(session_factory, make_empresa())
    actor = persist(session_factory, make_usuario(emp.id))
    cliente = persist(session_factory, make_cliente_model(emp.id, status="ativo"))
    service = ClienteService(event_publisher=RecordingPublisher(fail=True))

    with session_factory() as db:
        with pytest.raises(RuntimeError):
            service.suspender_cliente(db, empresa_id=emp.id, cliente_id=cliente.id, motivo="pausa", actor_usuario_id=actor.id)

    assert get_cliente(session_factory, emp.id, cliente.id).status == "ativo"
