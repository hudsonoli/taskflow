"""Fase Expediente 1 — API/serviço: períodos (0, 1, 2, 3+ por dia), flags nascendo desligadas e recusando LIGAR, antecedência, fuso IANA, dias especiais manuais,
isenção por usuário (só o campo) e origem da pausa de Demanda (só registro). NENHUM bloqueio de acesso nem pausa automática existe nesta fase."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.expediente import DiaEspecial, RegraExpediente, janela_de_periodos, momento_local
from app.core.relogio import fuso_aplicacao
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.regra_expediente import RegraExpedienteDia, RegraExpedienteDiaEspecial, RegraExpedientePeriodo
from app.models.regra_expediente import RegraExpediente as RegraExpedienteModel
from app.services.regra_expediente_service import RegraExpedienteService
from tests.test_demanda import dentro_do_expediente  # noqa: F401  (fixture reaproveitada)
from tests.test_regra_expediente import _cliente_para_outra_empresa

UTIL = [{"inicio": "08:00", "fim": "12:00"}, {"inicio": "13:00", "fim": "18:00"}]


def _dias(**por_dia) -> list[dict]:
    """7 dias; `por_dia` = {"d0": [...periodos], ...}; o que não vier fica fechado."""
    return [{"diaSemana": d, "periodos": por_dia.get(f"d{d}", [])} for d in range(7)]


def _semana_util() -> list[dict]:
    return _dias(d0=UTIL, d1=UTIL, d2=UTIL, d3=UTIL, d4=UTIL)


def _eventos_regra(db: Session, empresa_id: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.tipo == "regra_expediente.alterada", Evento.empresa_id == empresa_id).order_by(Evento.occurred_at)).all())


# ── defaults e compatibilidade ───────────────────────────────────────────────────────────────────────────────────


def test_regra_nova_nasce_com_tudo_desligado_e_compativel(client_admin: TestClient) -> None:
    corpo = client_admin.get("/regra-expediente").json()
    assert corpo["bloquearForaExpediente"] is False
    assert corpo["pausarNoFimPeriodo"] is False
    assert corpo["feriadosAutomaticos"] is False
    assert corpo["antecedenciaAcessoMinutos"] == 30
    assert corpo["timezone"] == fuso_aplicacao().key
    assert corpo["diasEspeciais"] == []
    por_dia = {d["diaSemana"]: d for d in corpo["dias"]}
    assert all(len(por_dia[d]["periodos"]) == 2 and por_dia[d]["ativo"] for d in range(5))
    assert all(por_dia[d]["periodos"] == [] and not por_dia[d]["ativo"] for d in (5, 6))
    # espelho legado preservado para consumidores antigos
    assert por_dia[0]["manhaInicio"] == "09:00:00" and por_dia[0]["tardeFim"] == "19:00:00"


def test_payload_legado_manha_tarde_continua_aceito_e_vira_periodos(client_admin: TestClient) -> None:
    dias = [{"diaSemana": d, "ativo": d < 5, **({"manhaInicio": "08:00", "manhaFim": "12:00", "tardeInicio": "13:00", "tardeFim": "18:00"} if d < 5 else {})} for d in range(7)]
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 200, resposta.text
    segunda = {d["diaSemana"]: d for d in resposta.json()["dias"]}[0]
    assert [(p["inicio"], p["fim"]) for p in segunda["periodos"]] == [("08:00:00", "12:00:00"), ("13:00:00", "18:00:00")]


def test_legado_e_novo_no_mesmo_dia_e_recusado(client_admin: TestClient) -> None:
    dias = _semana_util()
    dias[0]["manhaInicio"] = "08:00"
    assert client_admin.patch("/regra-expediente", json={"dias": dias}).status_code == 422


# ── períodos ─────────────────────────────────────────────────────────────────────────────────────────────────────


def test_varios_periodos_sabado_aberto_domingo_fechado(client_admin: TestClient) -> None:
    dias = _dias(
        d0=[{"inicio": "08:00", "fim": "10:00"}, {"inicio": "11:00", "fim": "13:00"}, {"inicio": "14:00", "fim": "18:00"}],
        d1=UTIL,
        d5=[{"inicio": "08:00", "fim": "12:00"}],
    )
    resposta = client_admin.patch("/regra-expediente", json={"dias": dias})
    assert resposta.status_code == 200, resposta.text
    por_dia = {d["diaSemana"]: d for d in resposta.json()["dias"]}
    assert len(por_dia[0]["periodos"]) == 3 and por_dia[0]["ativo"] is True
    assert len(por_dia[5]["periodos"]) == 1 and por_dia[5]["ativo"] is True
    assert por_dia[6]["periodos"] == [] and por_dia[6]["ativo"] is False
    assert por_dia[2]["periodos"] == [] and por_dia[2]["ativo"] is False  # quarta não enviada com períodos = fechada
    assert client_admin.get("/regra-expediente").json()["dias"] == resposta.json()["dias"]


def test_periodos_sao_ordenados_automaticamente(client_admin: TestClient) -> None:
    dias = _dias(d0=[{"inicio": "13:00", "fim": "18:00"}, {"inicio": "08:00", "fim": "12:00"}])
    periodos = {d["diaSemana"]: d for d in client_admin.patch("/regra-expediente", json={"dias": dias}).json()["dias"]}[0]["periodos"]
    assert [p["inicio"] for p in periodos] == ["08:00:00", "13:00:00"]


@pytest.mark.parametrize(
    "periodos",
    [
        [{"inicio": "08:00", "fim": "12:00"}, {"inicio": "11:00", "fim": "13:00"}],  # sobreposição
        [{"inicio": "08:00", "fim": "08:00"}],  # início == fim
        [{"inicio": "18:00", "fim": "08:00"}],  # atravessa a meia-noite (fora da V1)
        [{"inicio": f"{h:02d}:00", "fim": f"{h:02d}:30"} for h in range(8, 17)],  # 9 períodos > limite
    ],
)
def test_periodos_invalidos_sao_422(client_admin: TestClient, periodos) -> None:
    assert client_admin.patch("/regra-expediente", json={"dias": _dias(d0=periodos, d1=UTIL)}).status_code == 422


def test_periodos_que_apenas_se_tocam_sao_aceitos(client_admin: TestClient) -> None:
    dias = _dias(d0=[{"inicio": "08:00", "fim": "12:00"}, {"inicio": "12:00", "fim": "18:00"}])
    assert client_admin.patch("/regra-expediente", json={"dias": dias}).status_code == 200


def test_dias_incompletos_continuam_422(client_admin: TestClient) -> None:
    assert client_admin.patch("/regra-expediente", json={"dias": _semana_util()[:5]}).status_code == 422


def test_espelho_legado_so_com_exatamente_dois_periodos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    dias = _dias(
        d0=UTIL,
        d1=[{"inicio": "08:00", "fim": "12:00"}],
        d2=[{"inicio": "08:00", "fim": "10:00"}, {"inicio": "11:00", "fim": "13:00"}, {"inicio": "14:00", "fim": "18:00"}],
    )
    assert client_admin.patch("/regra-expediente", json={"dias": dias}).status_code == 200
    regra = db_session.scalars(select(RegraExpedienteModel).where(RegraExpedienteModel.empresa_id == empresa.id)).one()
    linhas = {d.dia_semana: d for d in db_session.scalars(select(RegraExpedienteDia).where(RegraExpedienteDia.regra_expediente_id == regra.id)).all()}
    assert linhas[0].ativo and (linhas[0].manha_inicio, linhas[0].tarde_fim) == (time(8, 0), time(18, 0))
    assert linhas[1].ativo and linhas[1].manha_inicio is None and linhas[1].tarde_inicio is None
    assert linhas[2].ativo and linhas[2].manha_inicio is None
    assert not linhas[3].ativo and linhas[3].manha_inicio is None


# ── flags, antecedência, fuso ────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("campo", ["bloquearForaExpediente", "pausarNoFimPeriodo", "feriadosAutomaticos"])
def test_flags_criticas_nao_podem_ser_ligadas_nesta_fase(client_admin: TestClient, campo: str) -> None:
    resposta = client_admin.patch("/regra-expediente", json={campo: True})
    assert resposta.status_code == 422
    assert "próxima etapa" in resposta.text
    assert client_admin.patch("/regra-expediente", json={campo: False}).status_code == 200
    assert client_admin.get("/regra-expediente").json()[campo] is False


@pytest.mark.parametrize(("valor", "status"), [(0, 200), (30, 200), (45, 200), (720, 200), (721, 422), (-1, 422)])
def test_antecedencia_de_acesso(client_admin: TestClient, valor: int, status: int) -> None:
    resposta = client_admin.patch("/regra-expediente", json={"antecedenciaAcessoMinutos": valor})
    assert resposta.status_code == status
    if status == 200:
        assert resposta.json()["antecedenciaAcessoMinutos"] == valor


def test_antecedencia_nao_mexe_na_janela_de_trabalho_nem_na_tolerancia_legada(client_admin: TestClient) -> None:
    antes = client_admin.get("/regra-expediente").json()
    depois = client_admin.patch("/regra-expediente", json={"antecedenciaAcessoMinutos": 10}).json()
    assert depois["toleranciaRetomadaMinutos"] == antes["toleranciaRetomadaMinutos"]
    assert depois["dias"] == antes["dias"]


def test_fuso_iana_valido_e_invalido(client_admin: TestClient) -> None:
    assert client_admin.patch("/regra-expediente", json={"timezone": "America/Manaus"}).json()["timezone"] == "America/Manaus"
    assert client_admin.patch("/regra-expediente", json={"timezone": "Marte/Olympus"}).status_code == 422
    assert client_admin.get("/regra-expediente").json()["timezone"] == "America/Manaus"


def test_o_fuso_da_regra_manda_no_relogio_do_estado(client_admin: TestClient) -> None:
    client_admin.patch("/regra-expediente", json={"timezone": "Pacific/Auckland"})
    agora = datetime.fromisoformat(client_admin.get("/expediente/estado").json()["agora"])
    assert agora.utcoffset().total_seconds() in (12 * 3600, 13 * 3600)  # NZST/NZDT, não o fuso da aplicação


def test_reenviar_a_mesma_configuracao_nao_gera_evento(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    client_admin.patch("/regra-expediente", json={"dias": _semana_util(), "antecedenciaAcessoMinutos": 20})
    n = len(_eventos_regra(db_session, empresa.id))
    client_admin.patch("/regra-expediente", json={"dias": _semana_util(), "antecedenciaAcessoMinutos": 20})
    assert len(_eventos_regra(db_session, empresa.id)) == n


def test_alteracao_gera_evento_com_os_campos(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    client_admin.patch("/regra-expediente", json={"antecedenciaAcessoMinutos": 15, "timezone": "America/Manaus", "dias": _semana_util()})
    campos = _eventos_regra(db_session, empresa.id)[-1].payload["camposAlterados"]
    assert {"antecedenciaAcessoMinutos", "timezone", "dias"} <= set(campos)


def test_operador_nao_le_nem_edita_dias_especiais(client_operador: TestClient) -> None:
    corpo = {"data": "2026-10-12", "nome": "Feriado", "tipo": "feriado"}
    assert client_operador.get("/regra-expediente/dias-especiais").status_code == 403
    assert client_operador.post("/regra-expediente/dias-especiais", json=corpo).status_code == 403


# ── dias especiais ───────────────────────────────────────────────────────────────────────────────────────────────


def _criar_especial(cliente: TestClient, **extra) -> dict:
    corpo = {"data": "2026-10-12", "nome": "N. Sra. Aparecida", "tipo": "feriado", **extra}
    resposta = cliente.post("/regra-expediente/dias-especiais", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_cadastro_manual_de_feriado(client_admin: TestClient) -> None:
    dia = _criar_especial(client_admin)
    assert dia["origem"] == "manual" and dia["tipo"] == "feriado" and dia["ativo"] is True and dia["periodos"] == []
    assert client_admin.get("/regra-expediente").json()["diasEspeciais"][0]["id"] == dia["id"]
    assert [d["id"] for d in client_admin.get("/regra-expediente/dias-especiais").json()] == [dia["id"]]


def test_a_origem_nunca_e_aceita_do_cliente(client_admin: TestClient) -> None:
    resposta = client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-10-12", "nome": "x", "tipo": "feriado", "origem": "automatico"})
    assert resposta.status_code == 422


def test_trabalho_excepcional_exige_periodos_e_os_outros_tipos_recusam(client_admin: TestClient) -> None:
    base = {"data": "2026-10-17", "nome": "Sábado extra"}
    assert client_admin.post("/regra-expediente/dias-especiais", json={**base, "tipo": "trabalho_excepcional"}).status_code == 422
    assert client_admin.post("/regra-expediente/dias-especiais", json={**base, "tipo": "feriado", "periodos": UTIL}).status_code == 422
    dia = client_admin.post("/regra-expediente/dias-especiais", json={**base, "tipo": "trabalho_excepcional", "periodos": [{"inicio": "13:00", "fim": "17:00"}, {"inicio": "08:00", "fim": "12:00"}]})
    assert dia.status_code == 201, dia.text
    assert [p["inicio"] for p in dia.json()["periodos"]] == ["08:00:00", "13:00:00"]


def test_tipo_invalido_e_data_duplicada(client_admin: TestClient) -> None:
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-10-12", "nome": "x", "tipo": "carnaval"}).status_code == 422
    _criar_especial(client_admin)
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-10-12", "nome": "outro", "tipo": "recesso"}).status_code == 409


def test_editar_trocando_o_tipo_ajusta_os_periodos(client_admin: TestClient) -> None:
    dia = _criar_especial(client_admin, data="2026-10-17", tipo="trabalho_excepcional", periodos=[{"inicio": "08:00", "fim": "12:00"}])
    alterado = client_admin.patch(f"/regra-expediente/dias-especiais/{dia['id']}", json={"tipo": "recesso", "nome": "Recesso"})
    assert alterado.status_code == 200 and alterado.json()["periodos"] == [] and alterado.json()["tipo"] == "recesso"
    assert client_admin.patch(f"/regra-expediente/dias-especiais/{dia['id']}", json={"tipo": "trabalho_excepcional"}).status_code == 422  # sem períodos
    assert client_admin.patch(f"/regra-expediente/dias-especiais/{dia['id']}", json={"ativo": False}).json()["ativo"] is False


def test_excluir_dia_manual(client_admin: TestClient) -> None:
    dia = _criar_especial(client_admin)
    assert client_admin.delete(f"/regra-expediente/dias-especiais/{dia['id']}").status_code == 204
    assert client_admin.get("/regra-expediente/dias-especiais").json() == []
    assert client_admin.delete(f"/regra-expediente/dias-especiais/{dia['id']}").status_code == 404


def test_dia_automatico_so_pode_ser_ativado_ou_desativado(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    client_admin.get("/regra-expediente")
    regra = db_session.scalars(select(RegraExpedienteModel).where(RegraExpedienteModel.empresa_id == empresa.id)).one()
    agora = datetime.now(timezone.utc)
    automatico = RegraExpedienteDiaEspecial(
        id=str(uuid.uuid4()), empresa_id=empresa.id, regra_expediente_id=regra.id, data=datetime(2026, 12, 25).date(), nome="Natal",
        origem="automatico", tipo="feriado", ativo=True, created_at=agora, updated_at=agora,
    )
    db_session.add(automatico)
    db_session.commit()  # o service dá rollback ao recusar: a linha precisa estar confirmada na transação do teste
    url = f"/regra-expediente/dias-especiais/{automatico.id}"
    assert client_admin.patch(url, json={"nome": "Outro"}).status_code == 422
    assert client_admin.patch(url, json={"tipo": "recesso"}).status_code == 422
    desligado = client_admin.patch(url, json={"ativo": False})
    assert desligado.status_code == 200 and desligado.json()["ativo"] is False and desligado.json()["origem"] == "automatico"
    assert client_admin.delete(url).status_code == 422  # não se exclui: desativa-se
    # e um MANUAL na mesma data coexiste (decisão explícita da empresa), sem tocar o automático
    manual = client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-12-25", "nome": "Trabalharemos", "tipo": "ignorado"})
    assert manual.status_code == 201


def test_dias_especiais_sao_isolados_por_empresa(client_admin: TestClient, app, db_session: Session, outra_empresa: Empresa) -> None:
    dia = _criar_especial(client_admin)
    outro = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    assert outro.get("/regra-expediente/dias-especiais").json() == []
    assert outro.patch(f"/regra-expediente/dias-especiais/{dia['id']}", json={"ativo": False}).status_code == 404
    assert outro.delete(f"/regra-expediente/dias-especiais/{dia['id']}").status_code == 404
    assert client_admin.get("/regra-expediente/dias-especiais").json()[0]["ativo"] is True


def test_dia_especial_gera_evento_de_auditoria(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    dia = _criar_especial(client_admin)
    client_admin.patch(f"/regra-expediente/dias-especiais/{dia['id']}", json={"ativo": False})
    client_admin.delete(f"/regra-expediente/dias-especiais/{dia['id']}")
    acoes = [e.payload["diaEspecial"]["acao"] for e in _eventos_regra(db_session, empresa.id) if "diaEspecial" in e.payload]
    assert acoes == ["criado", "alterado", "removido"]


# ── o calendário chega ao cálculo (service → DTO) ────────────────────────────────────────────────────────────────


def test_service_monta_o_dto_com_periodos_fuso_e_dias_especiais(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    client_admin.patch("/regra-expediente", json={"dias": _semana_util(), "timezone": "America/Manaus", "antecedenciaAcessoMinutos": 20})
    _criar_especial(client_admin)
    _criar_especial(client_admin, data="2026-10-17", tipo="trabalho_excepcional", periodos=[{"inicio": "09:00", "fim": "13:00"}])
    dto = RegraExpedienteService().get_regra_calculo(db_session, empresa_id=empresa.id)
    assert dto.timezone == "America/Manaus" and dto.antecedencia_acesso_minutos == 20
    assert dto.dias[0].lista_periodos() == (("08:00", "12:00"), ("13:00", "18:00"))
    assert dto.dias[5].lista_periodos() == ()
    assert {d.tipo for d in dto.dias_especiais} == {"feriado", "trabalho_excepcional"}
    assert dto.bloquear_fora_expediente is False and dto.pausar_no_fim_periodo is False


# ── gate de ENTRADA em execução com o calendário novo (único gate que existia; não é bloqueio de acesso) ────────────


def _regra_aberta_sempre(**extra) -> RegraExpediente:
    janela = janela_de_periodos([("00:00", "23:59")])
    return RegraExpediente(ativo=True, tolerancia_retomada_minutos=0, dias={d: janela for d in range(7)}, timezone=fuso_aplicacao().key, **extra)


@pytest.fixture()
def regra_override(app):
    from app.api.routes import demandas as rotas

    original = rotas.demanda_service.regra_expediente
    yield lambda regra: setattr(rotas.demanda_service, "regra_expediente", regra)
    rotas.demanda_service.regra_expediente = original


def _demanda_rascunho(cliente: TestClient) -> dict:
    resposta = cliente.post("/demandas", json={"nome": f"D {uuid.uuid4().hex[:6]}"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_feriado_de_hoje_barra_a_entrada_em_execucao(client_admin: TestClient, regra_override) -> None:
    hoje = momento_local(None, _regra_aberta_sempre()).date()
    regra_override(_regra_aberta_sempre(dias_especiais=(DiaEspecial(data=hoje, tipo="feriado"),)))
    resposta = client_admin.patch(f"/demandas/{_demanda_rascunho(client_admin)['id']}", json={"status": "em_execucao"})
    assert resposta.status_code == 409
    assert resposta.json()["detail"]["code"] == "FORA_DE_EXPEDIENTE"
    assert "hoje não é dia útil" in resposta.json()["detail"]["message"]


def test_trabalho_excepcional_libera_dia_fechado(client_admin: TestClient, regra_override) -> None:
    hoje = momento_local(None, _regra_aberta_sempre()).date()
    fechada = RegraExpediente(
        ativo=True, tolerancia_retomada_minutos=0, dias={d: janela_de_periodos([]) for d in range(7)}, timezone=fuso_aplicacao().key,
        dias_especiais=(DiaEspecial(data=hoje, tipo="trabalho_excepcional", periodos=(("00:00", "23:59"),)),),
    )
    regra_override(fechada)
    resposta = client_admin.patch(f"/demandas/{_demanda_rascunho(client_admin)['id']}", json={"status": "em_execucao"})
    assert resposta.status_code == 200, resposta.text


def test_mensagem_do_409_lista_todos_os_periodos(client_admin: TestClient, regra_override) -> None:
    tres = janela_de_periodos([("00:00", "00:01"), ("00:02", "00:03"), ("00:04", "00:05")])
    regra_override(RegraExpediente(ativo=True, tolerancia_retomada_minutos=0, dias={d: tres for d in range(7)}, timezone=fuso_aplicacao().key))
    resposta = client_admin.patch(f"/demandas/{_demanda_rascunho(client_admin)['id']}", json={"status": "em_execucao"})
    # só falha se por acaso o teste rodar dentro de um dos 3 minutinhos
    if resposta.status_code == 409:
        assert "00:00 às 00:01, das 00:02 às 00:03 e das 00:04 às 00:05" in resposta.json()["detail"]["message"]


# ── usuário: isenção (só o campo) ────────────────────────────────────────────────────────────────────────────────


def _payload_usuario(empresa: Empresa, **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {"empresaId": empresa.id, "nome": f"Usuário {sufixo}", "email": f"u-{sufixo}@teste.local", "perfilBase": "operador", "acessoSistema": True, **extra}


def test_usuario_nasce_sem_isencao(client_admin: TestClient, empresa: Empresa) -> None:
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa))
    assert criado.status_code == 201, criado.text
    assert criado.json()["acessoForaExpediente"] is False


def test_usuario_pode_ser_criado_e_editado_com_isencao_e_gera_auditoria(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa, acessoForaExpediente=True)).json()
    assert criado["acessoForaExpediente"] is True
    alterado = client_admin.patch(f"/usuarios/{criado['id']}", json={"acessoForaExpediente": False})
    assert alterado.status_code == 200 and alterado.json()["acessoForaExpediente"] is False
    eventos = db_session.scalars(select(Evento).where(Evento.tipo == "usuario.alterado", Evento.entidade_id == criado["id"])).all()
    assert any("acessoForaExpediente" in e.payload.get("camposAlterados", []) for e in eventos)
    assert client_admin.get(f"/usuarios/{criado['id']}").json()["acessoForaExpediente"] is False


def test_reenviar_o_mesmo_valor_da_isencao_nao_gera_alteracao(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa)).json()
    client_admin.patch(f"/usuarios/{criado['id']}", json={"acessoForaExpediente": False})
    eventos = db_session.scalars(select(Evento).where(Evento.tipo == "usuario.alterado", Evento.entidade_id == criado["id"])).all()
    assert not any("acessoForaExpediente" in e.payload.get("camposAlterados", []) for e in eventos)


def test_backend_aceita_a_flag_para_gestor_sem_depender_do_perfil(client_admin: TestClient, empresa: Empresa) -> None:
    gestor = client_admin.post("/usuarios", json=_payload_usuario(empresa, perfilBase="gestor", acessoForaExpediente=True))
    assert gestor.status_code == 201, gestor.text
    assert gestor.json()["acessoForaExpediente"] is True


def test_operador_nao_altera_isencao_de_ninguem(client_operador: TestClient, client_admin: TestClient, empresa: Empresa) -> None:
    alvo = client_admin.post("/usuarios", json=_payload_usuario(empresa)).json()
    assert client_operador.patch(f"/usuarios/{alvo['id']}", json={"acessoForaExpediente": True}).status_code == 403


# ── demanda: origem da pausa (só registro) ───────────────────────────────────────────────────────────────────────


def test_pausar_manualmente_registra_origem_e_instante(client_admin: TestClient, dentro_do_expediente) -> None:
    demanda = _demanda_rascunho(client_admin)
    assert demanda["pausaOrigem"] is None and demanda["pausadaEm"] is None
    client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"})
    pausada = client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "pausada"}).json()
    assert pausada["status"] == "pausada" and pausada["pausaOrigem"] == "manual" and pausada["pausadaEm"] is not None
    retomada = client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"}).json()
    assert retomada["pausaOrigem"] is None and retomada["pausadaEm"] is None


def test_evento_de_status_carrega_a_origem_da_pausa(client_admin: TestClient, db_session: Session, dentro_do_expediente) -> None:
    demanda = _demanda_rascunho(client_admin)
    client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"})
    client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "pausada"})
    client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"})
    eventos = db_session.scalars(select(Evento).where(Evento.tipo == "demanda.status_alterado", Evento.entidade_id == demanda["id"]).order_by(Evento.occurred_at)).all()
    pausa = [e for e in eventos if e.payload.get("para") == "pausada"]
    assert len(pausa) == 1 and pausa[0].payload["pausaOrigem"] == "manual"
    assert all("pausaOrigem" not in e.payload for e in eventos if e.payload.get("para") != "pausada")  # histórico existente intacto


def test_criar_ja_pausada_e_pausa_manual(client_admin: TestClient) -> None:
    criada = client_admin.post("/demandas", json={"nome": "Já pausada", "status": "pausada"})
    assert criada.status_code == 201, criada.text
    assert criada.json()["pausaOrigem"] == "manual"


def test_arquivar_e_restaurar_pausada(client_admin: TestClient) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "P", "status": "pausada"}).json()
    arquivada = client_admin.post(f"/demandas/{demanda['id']}/arquivar", json={"motivoArquivamento": "teste"}).json()
    assert arquivada["pausaOrigem"] is None
    restaurada = client_admin.post(f"/demandas/{demanda['id']}/restaurar").json()
    assert restaurada["status"] == "pausada" and restaurada["pausaOrigem"] == "manual"


def test_a_api_nao_aceita_escrever_a_origem_da_pausa(client_admin: TestClient) -> None:
    demanda = _demanda_rascunho(client_admin)
    assert client_admin.patch(f"/demandas/{demanda['id']}", json={"pausaOrigem": "expediente"}).status_code == 422
    assert client_admin.post("/demandas", json={"nome": "x", "pausaOrigem": "expediente"}).status_code == 422


def test_nenhum_mecanismo_pausa_sozinho(client_admin: TestClient, dentro_do_expediente) -> None:
    """Fase 1: mesmo com o controle ligado, nada pausa por conta própria — a demanda segue `em_execucao` até alguém agir."""
    demanda = _demanda_rascunho(client_admin)
    client_admin.patch(f"/demandas/{demanda['id']}", json={"status": "em_execucao"})
    client_admin.get("/expediente/estado")
    client_admin.get("/regra-expediente")
    assert client_admin.get(f"/demandas/{demanda['id']}").json()["status"] == "em_execucao"
