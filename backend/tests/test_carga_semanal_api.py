"""11B.2B-B — `GET /trafego/operacional/carga`: carga SEMANAL planejada × capacidade. Dados sintéticos (ORM direto); o "agora" do serviço é injetado.

Prova, pela API real: RBAC/tenant, semana (segunda no fuso da empresa, atual recortada em hoje, futura inteira, passada recusada), fator alocável, expediente desligado, distribuição por semana que
conserva os minutos, divisão entre responsáveis, pools, filtros que NÃO recalculam, estados da janela, status das Demandas, sem estimativa, detalhe, somente leitura e — principalmente — que nada de
tempo pessoal (`sessoes_trabalho`) nem de tempo operacional (`demanda_status_intervalos`) entra na consulta.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_status_intervalo import DemandaStatusIntervalo
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.evento import Evento
from app.models.regra_expediente import RegraExpediente as RegraModel
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from app.services.regra_expediente_service import RegraExpedienteService
from tests.test_demanda import _cliente
from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_sessao_trabalho import _departamento, _usuario
from tests.test_trafego_v2_metricas import _demanda, _dep_etapa, _etapa, _intervalo, _resp_etapa

# Segunda 2026-10-19 10:00 em São Paulo (13:00 UTC). Expediente padrão: seg–sex, 480 min nominais por dia.
AGORA = datetime(2026, 10, 19, 13, 0, tzinfo=timezone.utc)
SEG = date(2026, 10, 19)
SEG2, SEG3 = SEG + timedelta(days=7), SEG + timedelta(days=14)
_SEQ = itertools.count(1)


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    def fixar(instante: datetime) -> None:
        monkeypatch.setattr("app.services.carga_operacional_service.agora_utc", lambda instante=instante: instante)

    fixar(AGORA)
    return fixar


@pytest.fixture()
def regra(db_session: Session, empresa) -> RegraModel:
    modelo = RegraExpedienteService().get_ou_criar(db_session, empresa_id=empresa.id)
    modelo.timezone = "America/Sao_Paulo"
    modelo.ativo = True
    modelo.percentual_capacidade_alocavel = 100
    db_session.flush()
    return modelo


def pessoa(db: Session, empresa, *, dep=None, nome: str | None = None, **campos) -> Usuario:
    usuario = _usuario(db, empresa)
    if nome:
        usuario.nome = nome
    usuario.departamento_id = dep.id if dep is not None else None
    for campo, valor in campos.items():
        setattr(usuario, campo, valor)
    db.flush()
    return usuario


def etapa_carga(db: Session, empresa, *, est=None, ini=None, fim=None, users=(), deps=(), status="planejada", concluida=False, nome="Etapa", **demanda):
    d = _demanda(db, empresa, status=status, nome=f"Demanda {next(_SEQ)}", **demanda)
    e = _etapa(db, d, 1, nome, concluida=concluida)
    e.esforco_estimado_minutos = est
    e.planejado_inicio, e.planejado_fim = ini, fim
    db.flush()
    for u in users:
        _resp_etapa(db, e, u)
    for dep in deps:
        _dep_etapa(db, e, dep)
    return d, e


def carga(cliente: TestClient, **params):
    return cliente.get("/trafego/operacional/carga", params={k: v for k, v in params.items() if v is not None})


def por_id(lista: list[dict], chave: str, valor: str) -> dict:
    [achada] = [x for x in lista if x[chave] == valor]
    return achada


# ── RBAC / tenant ──────────────────────────────────────────────────────────────────────────────────────────────────


def test_admin_e_gestor_acessam_operador_403_e_sem_token_401(client_admin, client_gestor, client_operador, client, regra) -> None:
    assert carga(client_admin).status_code == 200
    assert carga(client_gestor).status_code == 200
    assert carga(client_operador).status_code == 403
    assert carga(client).status_code == 401


def test_empresa_vem_do_token_e_dados_de_outra_empresa_nunca_aparecem(client_admin, db_session, empresa, outra_empresa, regra) -> None:
    alheio = pessoa(db_session, outra_empresa, nome="Pessoa de outra empresa")
    etapa_carga(db_session, outra_empresa, est=300, ini=SEG, fim=SEG, users=[alheio])
    dep_alheio = _departamento(db_session, outra_empresa)
    corpo = carga(client_admin, empresaId=str(outra_empresa.id)).json()  # parâmetro desconhecido é ignorado: o tenant é o do token
    assert alheio.id not in [p["usuarioId"] for p in corpo["pessoas"]]
    assert corpo["naoPlanejado"]["semJanela"]["etapasCount"] == 0
    assert carga(client_admin, usuarioId=alheio.id).status_code == 404
    assert carga(client_admin, departamentoId=dep_alheio.id).status_code == 404
    assert carga(client_admin, usuarioId=str(uuid.uuid4())).status_code == 404
    assert carga(client_admin, usuarioId="nao-e-uuid").status_code == 422


# ── semana e fuso ──────────────────────────────────────────────────────────────────────────────────────────────────


def test_semana_normaliza_para_segunda_e_omitida_e_a_atual(client_admin, regra) -> None:
    assert carga(client_admin).json()["semana"]["inicio"] == "2026-10-19"
    for dia in ("2026-10-19", "2026-10-22", "2026-10-25"):
        assert carga(client_admin, semana=dia).json()["semana"]["inicio"] == "2026-10-19"
    corpo = carga(client_admin, semana="2026-11-04").json()["semana"]
    assert (corpo["inicio"], corpo["fim"], corpo["recorteHoje"]) == ("2026-11-02", "2026-11-08", False)


def test_a_semana_usa_o_fuso_da_empresa_e_nao_o_utc(client_admin, relogio, regra) -> None:
    relogio(datetime(2026, 10, 19, 2, 30, tzinfo=timezone.utc))  # domingo 23:30 em São Paulo, mas segunda em UTC
    corpo = carga(client_admin).json()
    assert corpo["semana"]["inicio"] == "2026-10-12" and corpo["meta"]["fusoEmpresa"] == "America/Sao_Paulo"
    regra.timezone = "UTC"
    regra_service_cache_off = carga(client_admin).json()
    assert regra_service_cache_off["semana"]["inicio"] == "2026-10-19"


def test_semana_passada_e_recusada_com_codigo_de_dominio(client_admin, regra) -> None:
    resposta = carga(client_admin, semana="2026-10-18")
    assert resposta.status_code == 422 and resposta.json()["detail"]["code"] == "SEMANA_PASSADA_NAO_SUPORTADA"
    assert carga(client_admin, semana="2026-10-19").status_code == 200  # a semana atual é suportada


def test_semana_atual_recorta_em_hoje_e_a_futura_e_completa(client_admin, relogio, db_session, empresa, regra) -> None:
    pessoa(db_session, empresa)
    relogio(datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc))  # quarta 17:00 em SP: hoje conta como dia COMPLETO
    atual = carga(client_admin).json()
    assert atual["semana"]["recorteHoje"] is True
    assert [d["considerado"] for d in atual["semana"]["dias"]] == [False, False, True, True, True, True, True]
    assert [d["minutosNominais"] for d in atual["semana"]["dias"]] == [480, 480, 480, 480, 480, 0, 0]
    assert atual["pessoas"][0]["capacidadeNominalMin"] == 3 * 480
    futura = carga(client_admin, semana="2026-10-26").json()
    assert futura["semana"]["recorteHoje"] is False and all(d["considerado"] for d in futura["semana"]["dias"])
    assert futura["pessoas"][0]["capacidadeNominalMin"] == 2400


def test_fator_alocavel_100_e_75(client_admin, db_session, empresa, regra) -> None:
    pessoa(db_session, empresa)
    p = carga(client_admin).json()["pessoas"][0]
    assert (p["capacidadeNominalMin"], p["capacidadeAlocavelMin"]) == (2400, 2400)
    regra.percentual_capacidade_alocavel = 75
    db_session.flush()
    corpo = carga(client_admin).json()
    assert (corpo["pessoas"][0]["capacidadeAlocavelMin"], corpo["capacidade"]["fatorAlocavelPercentual"]) == (1800, 75)


def test_dia_especial_fechado_zera_a_capacidade_do_dia(client_admin, db_session, empresa, regra) -> None:
    pessoa(db_session, empresa)
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-10-21", "nome": "Feriado de teste", "tipo": "feriado"}).status_code == 201
    corpo = carga(client_admin).json()
    assert [d["minutosNominais"] for d in corpo["semana"]["dias"]][:5] == [480, 480, 0, 480, 480]
    assert corpo["pessoas"][0]["capacidadeNominalMin"] == 1920


def test_trabalho_excepcional_usa_os_periodos_do_dia_especial(client_admin, db_session, empresa, regra) -> None:
    pessoa(db_session, empresa)
    resposta = client_admin.post(
        "/regra-expediente/dias-especiais",
        json={"data": "2026-10-24", "nome": "Plantão", "tipo": "trabalho_excepcional", "periodos": [{"inicio": "08:00", "fim": "12:00"}]},
    )
    assert resposta.status_code == 201, resposta.text
    corpo = carga(client_admin, semana="2026-10-24").json()
    assert [d["minutosNominais"] for d in corpo["semana"]["dias"]][5] == 240
    assert corpo["pessoas"][0]["capacidadeNominalMin"] == 2400 + 240


def test_expediente_desligado_nao_inventa_capacidade_e_ocupacao_e_nula(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=300, ini=SEG, fim=SEG + timedelta(days=2), users=[a])
    etapa_carga(db_session, empresa, est=90, users=[a])  # sem janela: independe do calendário
    regra.ativo = False
    db_session.flush()
    corpo = carga(client_admin).json()
    p = por_id(corpo["pessoas"], "usuarioId", a.id)
    assert corpo["capacidade"]["capacidadeIndisponivel"] == "expediente_desligado"
    assert (p["capacidadeNominalMin"], p["capacidadeAlocavelMin"], p["planejadoMin"], p["saldoMin"], p["ocupacaoPercentual"]) == (None, None, None, None, None)
    assert p["naoPlanejadoMin"] == 90 and all(d["minutosNominais"] is None for d in corpo["semana"]["dias"])


def test_empresa_sem_regra_de_expediente_nao_cria_regra_e_e_tratada_como_desligada(client_admin, db_session, empresa) -> None:
    antes = db_session.scalar(select(func.count()).select_from(RegraModel).where(RegraModel.empresa_id == empresa.id))
    corpo = carga(client_admin).json()
    assert antes == 0 and corpo["capacidade"]["capacidadeIndisponivel"] == "expediente_desligado"
    assert db_session.scalar(select(func.count()).select_from(RegraModel).where(RegraModel.empresa_id == empresa.id)) == 0  # leitura não escreve


# ── janela e distribuição ──────────────────────────────────────────────────────────────────────────────────────────


def test_janela_atravessando_tres_semanas_distribui_e_conserva(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=600, ini=SEG, fim=date(2026, 11, 6), users=[a])
    partes = [por_id(carga(client_admin, semana=s.isoformat()).json()["pessoas"], "usuarioId", a.id)["planejadoMin"] for s in (SEG, SEG2, SEG3)]
    assert partes == [200, 200, 200] and sum(partes) == 600
    assert por_id(carga(client_admin, semana="2026-11-09").json()["pessoas"], "usuarioId", a.id)["planejadoMin"] == 0


def test_janela_com_semanas_de_pesos_diferentes_e_resto_conservam(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    db_session.flush()
    assert client_admin.post("/regra-expediente/dias-especiais", json={"data": "2026-10-28", "nome": "Folga", "tipo": "feriado"}).status_code == 201
    etapa_carga(db_session, empresa, est=1001, ini=date(2026, 10, 22), fim=date(2026, 11, 3), users=[a])  # qui, sex | seg, ter, (qua feriado), qui, sex | seg, ter
    partes = [por_id(carga(client_admin, semana=s).json()["pessoas"], "usuarioId", a.id)["planejadoMin"] for s in ("2026-10-19", "2026-10-26", "2026-11-02")]
    assert sum(partes) == 1001 and all(parte > 0 for parte in partes)


def test_janela_iniciada_no_passado_distribui_so_de_hoje_em_diante(client_admin, relogio, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    relogio(datetime(2026, 10, 21, 13, 0, tzinfo=timezone.utc))  # quarta
    etapa_carga(db_session, empresa, est=900, ini=date(2026, 10, 12), fim=date(2026, 10, 30), users=[a])
    atual = por_id(carga(client_admin).json()["pessoas"], "usuarioId", a.id)["planejadoMin"]
    seguinte = por_id(carga(client_admin, semana="2026-10-26").json()["pessoas"], "usuarioId", a.id)["planejadoMin"]
    assert atual + seguinte == 900 and (atual, seguinte) == (338, 562)  # 3 dias restantes (qua–sex) de 8


def test_janela_vencida_e_pendencia_e_nao_move_para_a_semana_atual(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    d, e = etapa_carga(db_session, empresa, est=240, ini=date(2026, 10, 1), fim=date(2026, 10, 16), users=[a])
    corpo = carga(client_admin).json()
    p = por_id(corpo["pessoas"], "usuarioId", a.id)
    assert p["planejadoMin"] == 0 and p["pendenciasPlanejamentoMin"] == 240
    venc = corpo["pendenciasPlanejamento"]["janelaVencida"]
    assert (venc["etapasCount"], venc["minutosConhecidos"]) == (1, 240) and venc["itens"][0]["etapaId"] == e.id
    assert venc["itens"][0]["janela"]["estado"] == "planejado" and venc["itens"][0]["alocacaoEstado"] == "janela_vencida"


def test_janela_so_em_dias_fechados_e_sem_dia_util(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    d, e = etapa_carga(db_session, empresa, est=120, ini=date(2026, 10, 24), fim=date(2026, 10, 25), users=[a])  # sábado → domingo
    for semana in ("2026-10-19", "2026-10-26"):
        corpo = carga(client_admin, semana=semana).json()
        assert por_id(corpo["pessoas"], "usuarioId", a.id)["planejadoMin"] == 0
        [item] = corpo["pendenciasPlanejamento"]["semDiaUtil"]["itens"]
        assert item["etapaId"] == e.id and item["janela"]["estado"] == "planejado" and item["alocacaoEstado"] == "sem_dia_util"
        assert corpo["naoPlanejado"]["semJanela"]["etapasCount"] == corpo["naoPlanejado"]["janelaIncompleta"]["etapasCount"] == 0


def test_sem_janela_e_janela_incompleta_aparecem_separados_e_fora_da_ocupacao(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=90, users=[a])
    etapa_carga(db_session, empresa, est=60, ini=date(2026, 10, 20), users=[a])
    etapa_carga(db_session, empresa, est=None, users=[a])
    corpo = carga(client_admin).json()
    p = por_id(corpo["pessoas"], "usuarioId", a.id)
    assert (p["planejadoMin"], p["ocupacaoPercentual"], p["naoPlanejadoMin"], p["semEstimativaCount"]) == (0, 0.0, 150, 1)
    assert corpo["naoPlanejado"]["semJanela"] == {"etapasCount": 2, "minutosConhecidos": 90, "semEstimativaCount": 1}
    assert corpo["naoPlanejado"]["janelaIncompleta"] == {"etapasCount": 1, "minutosConhecidos": 60, "semEstimativaCount": 0}


def test_sem_estimativa_nao_vira_zero_mesmo_com_janela_completa(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=None, ini=SEG, fim=SEG + timedelta(days=4), users=[a])
    etapa_carga(db_session, empresa, est=0, ini=SEG, fim=SEG + timedelta(days=4), users=[a])  # zero explícito é estimativa
    p = por_id(carga(client_admin).json()["pessoas"], "usuarioId", a.id)
    assert p["planejadoMin"] == 0 and p["semEstimativaCount"] == 1


# ── responsabilidade ───────────────────────────────────────────────────────────────────────────────────────────────


def test_dois_responsaveis_dividem_241_em_121_e_120(client_admin, db_session, empresa, regra) -> None:
    a, b = pessoa(db_session, empresa), pessoa(db_session, empresa)
    d, e = etapa_carga(db_session, empresa, est=241, ini=SEG, fim=SEG + timedelta(days=4), users=[a, b])
    corpo = carga(client_admin).json()
    partes = sorted([por_id(corpo["pessoas"], "usuarioId", u.id)["planejadoMin"] for u in (a, b)], reverse=True)
    assert partes == [121, 120]
    menor_id = min(a.id, b.id)
    assert por_id(corpo["pessoas"], "usuarioId", menor_id)["planejadoMin"] == 121  # resto sempre para o menor id: determinístico


def test_filtros_nao_recalculam_a_divisao(client_admin, db_session, empresa, regra) -> None:
    dep1, dep2 = _departamento(db_session, empresa), _departamento(db_session, empresa)
    a, b = pessoa(db_session, empresa, dep=dep1), pessoa(db_session, empresa, dep=dep2)
    etapa_carga(db_session, empresa, est=240, ini=SEG, fim=SEG + timedelta(days=4), users=[a, b])
    completo = carga(client_admin).json()
    pa, pb = (por_id(completo["pessoas"], "usuarioId", u.id)["planejadoMin"] for u in (a, b))
    assert (pa, pb) == (120, 120)
    so_a = carga(client_admin, usuarioId=a.id).json()
    assert [p["usuarioId"] for p in so_a["pessoas"]] == [a.id] and so_a["pessoas"][0]["planejadoMin"] == 120  # NÃO virou 240
    so_dep2 = carga(client_admin, departamentoId=dep2.id).json()
    assert [d["departamentoId"] for d in so_dep2["departamentos"]] == [dep2.id]
    assert so_dep2["departamentos"][0]["planejadoMin"] == 120 and [p["usuarioId"] for p in so_dep2["pessoas"]] == [b.id]
    assert por_id(completo["departamentos"], "departamentoId", dep2.id)["planejadoMin"] == 120  # mesmo valor com e sem filtro


def test_usuario_mais_departamento_a_carga_vai_so_para_o_usuario(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    a = pessoa(db_session, empresa, dep=dep)
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[a], deps=[dep])
    corpo = carga(client_admin).json()
    d = por_id(corpo["departamentos"], "departamentoId", dep.id)
    assert por_id(corpo["pessoas"], "usuarioId", a.id)["planejadoMin"] == 100
    assert (d["planejadoMin"], d["planejadoPoolMin"]) == (100, 0)  # o departamento NÃO recebe pool adicional


def test_sem_usuario_o_departamento_recebe_o_pool_que_e_subconjunto_do_planejado(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    a = pessoa(db_session, empresa, dep=dep)
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[a])
    etapa_carga(db_session, empresa, est=60, ini=SEG, fim=SEG, deps=[dep])
    d = por_id(carga(client_admin).json()["departamentos"], "departamentoId", dep.id)
    assert (d["planejadoMin"], d["planejadoPoolMin"], d["pessoasCount"]) == (160, 60, 1)  # 100 da pessoa + 60 do pool: sem contar duas vezes
    assert (d["capacidadeNominalMin"], d["capacidadeAlocavelMin"], d["saldoMin"]) == (2400, 2400, 2240)
    assert d["ocupacaoPercentual"] == round(160 * 100 / 2400, 1)


def test_dois_departamentos_sem_usuario_dividem_o_pool(client_admin, db_session, empresa, regra) -> None:
    dep1, dep2 = _departamento(db_session, empresa), _departamento(db_session, empresa)
    pessoa(db_session, empresa, dep=dep1)
    etapa_carga(db_session, empresa, est=241, ini=SEG, fim=SEG, deps=[dep1, dep2])
    corpo = carga(client_admin).json()
    pools = sorted(por_id(corpo["departamentos"], "departamentoId", d.id)["planejadoPoolMin"] for d in (dep1, dep2))
    assert pools == [120, 121]


def test_sem_usuario_e_sem_departamento_vai_para_o_pool_sem_departamento(client_admin, db_session, empresa, regra) -> None:
    etapa_carga(db_session, empresa, est=90, ini=SEG, fim=SEG)
    etapa_carga(db_session, empresa, est=40)
    etapa_carga(db_session, empresa, est=None)
    pool = carga(client_admin).json()["poolSemDepartamento"]
    assert pool == {"etapasCount": 3, "planejadoMin": 90, "naoPlanejadoMin": 40, "pendenciasPlanejamentoMin": 0, "semEstimativaCount": 1}


def test_pessoa_sem_departamento_conta_na_lista_de_pessoas_mas_em_nenhum_departamento(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=60, ini=SEG, fim=SEG, users=[a])
    corpo = carga(client_admin).json()
    assert por_id(corpo["pessoas"], "usuarioId", a.id)["departamentoId"] is None and por_id(corpo["pessoas"], "usuarioId", a.id)["planejadoMin"] == 60
    assert corpo["departamentos"] == []


def test_usuarios_inelegiveis_ficam_fora_e_a_carga_deles_cai_no_pool(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    ativo = pessoa(db_session, empresa, dep=dep, nome="Ativo")
    inativo = pessoa(db_session, empresa, dep=dep, status="inativo")
    bloqueado = pessoa(db_session, empresa, dep=dep, status="bloqueado")
    arquivado = pessoa(db_session, empresa, dep=dep, status="arquivado")
    sistema = pessoa(db_session, empresa, dep=dep, is_system_account=True)
    sem_acesso = pessoa(db_session, empresa, dep=dep, acesso_sistema=False)
    gestor = pessoa(db_session, empresa, dep=dep, perfil_base="gestor")  # perfil NÃO decide: gestor ativo recebe trabalho como qualquer um
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[inativo], deps=[dep])
    corpo = carga(client_admin).json()
    ids = {p["usuarioId"] for p in corpo["pessoas"]}
    assert {ativo.id, gestor.id} <= ids
    assert not ids & {inativo.id, bloqueado.id, arquivado.id, sistema.id, sem_acesso.id}
    assert por_id(corpo["departamentos"], "departamentoId", dep.id)["planejadoPoolMin"] == 100  # nunca desaparece


def test_sem_estimativa_conta_por_pessoa_departamento_e_pool(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    a = pessoa(db_session, empresa, dep=dep)
    etapa_carga(db_session, empresa, est=None, ini=SEG, fim=SEG, users=[a])
    etapa_carga(db_session, empresa, est=None, ini=SEG, fim=SEG, deps=[dep])
    etapa_carga(db_session, empresa, est=None, ini=SEG, fim=SEG)
    corpo = carga(client_admin).json()
    assert por_id(corpo["pessoas"], "usuarioId", a.id)["semEstimativaCount"] == 1
    assert por_id(corpo["departamentos"], "departamentoId", dep.id)["semEstimativaCount"] == 2  # a da pessoa + a do pool, sem duplicar
    assert corpo["poolSemDepartamento"]["semEstimativaCount"] == 1
    assert corpo["naoPlanejado"]["semJanela"]["semEstimativaCount"] == 0  # todas têm janela completa: não entram no balde "sem janela"


# ── status das Demandas ────────────────────────────────────────────────────────────────────────────────────────────


def test_status_que_participam_e_os_que_ficam_de_fora(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    for status in ("planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"):
        etapa_carga(db_session, empresa, est=10, ini=SEG, fim=SEG, users=[a], status=status)
    for status in ("rascunho", "concluida", "cancelada", "arquivada"):
        etapa_carga(db_session, empresa, est=1000, ini=SEG, fim=SEG, users=[a], status=status)
    etapa_carga(db_session, empresa, est=1000, ini=SEG, fim=SEG, users=[a], concluida=True)  # etapa concluída: 0
    assert por_id(carga(client_admin).json()["pessoas"], "usuarioId", a.id)["planejadoMin"] == 50


def test_etapa_futura_ainda_nao_iniciada_com_janela_valida_participa(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    d = _demanda(db_session, empresa, status="planejada")
    atual = _etapa(db_session, d, 1, "Atual")
    futura = _etapa(db_session, d, 2, "Futura")
    futura.esforco_estimado_minutos, futura.planejado_inicio, futura.planejado_fim = 180, SEG2, SEG2 + timedelta(days=1)
    db_session.flush()
    _resp_etapa(db_session, futura, a)
    assert por_id(carga(client_admin, semana="2026-10-26").json()["pessoas"], "usuarioId", a.id)["planejadoMin"] == 180


# ── detalhe ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_detalhe_do_usuario_explica_o_numero(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    c = _cliente(db_session, empresa)
    pj = _projeto(db_session, empresa, cliente_id=c.id)
    a, b = pessoa(db_session, empresa, dep=dep), pessoa(db_session, empresa, dep=dep)
    d1, e1 = etapa_carga(db_session, empresa, est=241, ini=SEG, fim=SEG + timedelta(days=4), users=[a, b], cliente_id=c.id, projeto_id=pj.id, nome="Criação")
    etapa_carga(db_session, empresa, est=60, users=[a])
    corpo = carga(client_admin, usuarioId=a.id, detalhe="usuario").json()
    det = corpo["detalhe"]
    assert (det["tipo"], det["id"], det["etapasTotal"], det["truncado"]) == ("usuario", a.id, 2, False)
    primeiro = det["etapas"][0]
    assert primeiro["etapaId"] == e1.id and primeiro["demandaId"] == d1.id and primeiro["etapaNome"] == "Criação"
    assert (primeiro["estimativaMin"], primeiro["restanteMin"], primeiro["planejadoNaSemanaMin"], primeiro["divididoEntre"], primeiro["origem"]) == (241, 241, 241, 2, "responsavel")
    assert primeiro["parteMin"] == por_id(corpo["pessoas"], "usuarioId", a.id)["planejadoMin"]
    assert primeiro["cliente"]["id"] == c.id and primeiro["projeto"]["id"] == pj.id
    assert primeiro["janela"] == {"planejadoInicio": "2026-10-19", "planejadoFim": "2026-10-23", "estado": "planejado"}
    assert det["etapas"][1]["motivoNaoPlanejado"] == "sem_janela" and det["etapas"][1]["parteMin"] is None


def test_detalhe_do_departamento_soma_pessoas_e_pool(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    a = pessoa(db_session, empresa, dep=dep)
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[a])
    etapa_carga(db_session, empresa, est=60, ini=SEG, fim=SEG, deps=[dep])
    corpo = carga(client_admin, departamentoId=dep.id, detalhe="departamento").json()
    assert sorted(i["parteMin"] for i in corpo["detalhe"]["etapas"]) == [60, 100]
    assert sorted(i["origem"] for i in corpo["detalhe"]["etapas"]) == ["pool_departamento", "responsavel"]
    assert sum(i["parteMin"] for i in corpo["detalhe"]["etapas"]) == corpo["departamentos"][0]["planejadoMin"]


def test_detalhe_exige_o_id_correspondente_e_respeita_o_limite(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    for _ in range(5):
        etapa_carga(db_session, empresa, est=10, ini=SEG, fim=SEG, users=[a])
    assert carga(client_admin, detalhe="usuario").status_code == 422
    assert carga(client_admin, detalhe="departamento").status_code == 422
    assert carga(client_admin, detalhe="outro", usuarioId=a.id).status_code == 422
    corpo = carga(client_admin, usuarioId=a.id, detalhe="usuario", limite=2).json()["detalhe"]
    assert (len(corpo["etapas"]), corpo["etapasTotal"], corpo["truncado"]) == (2, 5, True)
    assert carga(client_admin, limite=0).status_code == 422


# ── somente leitura e tempo pessoal/operacional fora ───────────────────────────────────────────────────────────────


def _contagens(db: Session) -> dict:
    return {
        "eventos": db.scalar(select(func.count()).select_from(Evento)),
        "demandas": db.scalar(select(func.count()).select_from(Demanda)),
        "etapas": db.scalar(select(func.count()).select_from(DemandaWorkflowEtapa)),
        "sessoes": db.scalar(select(func.count()).select_from(SessaoTrabalho)),
        "intervalos": db.scalar(select(func.count()).select_from(DemandaStatusIntervalo)),
        "etapas_dump": [(e.id, e.status, e.esforco_estimado_minutos, e.planejado_inicio, e.planejado_fim, e.updated_at) for e in db.scalars(select(DemandaWorkflowEtapa).order_by(DemandaWorkflowEtapa.id))],
        "regra": [(r.id, r.updated_at, r.percentual_capacidade_alocavel, r.pausa_automatica_ativada_em, r.timezone) for r in db.scalars(select(RegraModel))],
    }


def test_chamar_o_endpoint_nao_escreve_nada(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[a])
    db_session.expire_all()
    antes = _contagens(db_session)
    for params in ({}, {"semana": "2026-10-26"}, {"usuarioId": a.id, "detalhe": "usuario"}):
        assert carga(client_admin, **params).status_code == 200
    db_session.expire_all()
    assert _contagens(db_session) == antes


def test_a_consulta_nao_toca_sessoes_nem_intervalos_e_o_resultado_nao_depende_deles(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    d, e = etapa_carga(db_session, empresa, est=300, ini=SEG, fim=SEG + timedelta(days=4), users=[a], status="em_execucao")
    sem = carga(client_admin).json()
    # Com sessão pessoal longa e intervalo operacional longo: NADA muda (não reduzem o restante nem a capacidade).
    agora = datetime.now(timezone.utc)
    db_session.add(SessaoTrabalho(id=str(uuid.uuid4()), empresa_id=empresa.id, demanda_id=d.id, workflow_etapa_id=e.id, usuario_id=a.id, evento_inicio_id=str(uuid.uuid4()), evento_fim_id=str(uuid.uuid4()), status="encerrada", inicio_em=agora - timedelta(hours=9), fim_em=agora, duracao_segundos=9 * 3600, motivo_encerramento="pausa", created_at=agora, updated_at=agora))
    _intervalo(db_session, d, "em_execucao", agora - timedelta(days=3), agora - timedelta(days=1), etapa=e)
    db_session.flush()
    com = carga(client_admin).json()
    assert {k: v for k, v in com.items() if k != "meta"} == {k: v for k, v in sem.items() if k != "meta"}

    declaracoes: list[str] = []

    def captura(conn, cursor, statement, parameters, context, executemany):
        declaracoes.append(statement)

    motor = db_session.get_bind()
    event.listen(motor, "before_cursor_execute", captura)
    try:
        assert carga(client_admin, usuarioId=a.id, detalhe="usuario").status_code == 200
    finally:
        event.remove(motor, "before_cursor_execute", captura)
    assert declaracoes
    assert not [s for s in declaracoes if "sessoes_trabalho" in s or "demanda_status_intervalos" in s]
    assert not [s for s in declaracoes if s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]


def test_a_resposta_nao_tem_campos_de_tempo_pessoal_nem_ranking(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    etapa_carga(db_session, empresa, est=100, ini=SEG, fim=SEG, users=[a])
    texto = carga(client_admin, usuarioId=a.id, detalhe="usuario").text.lower()
    for proibido in ("horastrabalhadas", "produtividade", "ranking", "eficiencia", "custo", "valor", "salario"):
        assert proibido not in texto


# ── consultas em conjunto (sem N+1) ────────────────────────────────────────────────────────────────────────────────


def _consultas(db: Session, chamada) -> int:
    declaracoes: list[str] = []

    def captura(conn, cursor, statement, parameters, context, executemany):
        declaracoes.append(statement)

    motor = db.get_bind()
    event.listen(motor, "before_cursor_execute", captura)
    try:
        chamada()
    finally:
        event.remove(motor, "before_cursor_execute", captura)
    return len(declaracoes)


def test_quantidade_de_consultas_nao_cresce_com_etapas_usuarios_e_departamentos(client_admin, db_session, empresa, regra) -> None:
    deps = [_departamento(db_session, empresa) for _ in range(2)]
    pessoas = [pessoa(db_session, empresa, dep=deps[i % 2]) for i in range(3)]
    for i in range(3):
        etapa_carga(db_session, empresa, est=60 + i, ini=SEG, fim=SEG2, users=[pessoas[i % 3]], deps=[deps[0]])
    carga(client_admin, semana="2026-10-26")  # aquecimento: a PRIMEIRA chamada paga a autenticação/permissões do usuário, que não é custo da Carga
    pequeno = _consultas(db_session, lambda: carga(client_admin, semana="2026-10-26"))

    mais_pessoas = [pessoa(db_session, empresa, dep=deps[i % 2]) for i in range(25)]
    for i in range(120):
        etapa_carga(
            db_session, empresa, est=30 + i, ini=SEG + timedelta(days=i % 4), fim=SEG3 + timedelta(days=i % 5),
            users=[mais_pessoas[i % 25], mais_pessoas[(i + 1) % 25]], deps=[deps[i % 2]],
        )
    grande = _consultas(db_session, lambda: carga(client_admin, semana="2026-10-26"))
    assert pequeno == grande, (pequeno, grande)
    assert grande <= 20  # constante e pequeno: regra + dias + períodos + especiais + pessoas + departamentos + etapas + responsáveis
    print(f"LOAD_QUERY_COUNT_SMALL={pequeno} LOAD_QUERY_COUNT_LARGE={grande}")
