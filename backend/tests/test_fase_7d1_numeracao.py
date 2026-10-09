"""Fase 7D.1 — numeração configurável de tarefas (sem reinício anual).

- o identificador é EMITIDO uma vez (`demandas.identificador`) e nunca muda; mudar o padrão afeta só as próximas tarefas;
- o formato (prefixo, separador, ano, dígitos) e o próximo número são configuração POR EMPRESA, só admin/gestor;
- o próximo número nunca pode colidir com o histórico; emissão e PATCH serializam pelo lock da mesma linha.
"""

from __future__ import annotations

import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.numeracao_formato import (
    FormatoNumeracao,
    FormatoNumeracaoInvalidoError,
    formatar_identificador,
    validar_formato,
)
from app.models.demanda import Demanda
from tests.test_configuracao_numeracao_tarefa import _cliente_para_outra_empresa
from tests.test_demanda import _criar

URL = "/configuracoes/numeracao-tarefas"


@pytest.fixture(autouse=True)
def ano_2026(monkeypatch):
    """Ano de emissão determinístico (o service de criação e a prévia leem o mesmo relógio)."""
    anos = {"valor": 2026}
    monkeypatch.setattr("app.services.demanda_service.ano_corrente", lambda: anos["valor"])
    monkeypatch.setattr("app.services.configuracao_numeracao_tarefa_service.ano_corrente", lambda: anos["valor"])
    return anos


def _patch(client: TestClient, **corpo):
    return client.patch(URL, json=corpo)


def _identificador(db: Session, demanda: dict) -> str:
    return db.scalars(select(Demanda.identificador).where(Demanda.id == demanda["id"])).one()


# ======================================================================================
# FORMATADOR (puro)
# ======================================================================================


@pytest.mark.parametrize(
    ("formato", "numero", "ano", "esperado"),
    [
        (FormatoNumeracao(), 15, 2026, "#15"),  # padrão histórico
        (FormatoNumeracao(digitos=5), 1, 2026, "#00001"),
        (FormatoNumeracao(prefixo="TF", separador="-", digitos=5), 15, 2026, "TF-00015"),
        (FormatoNumeracao(prefixo="BOX", separador="-", incluir_ano=True, digitos=5), 15, 2026, "BOX-2026-00015"),
        (FormatoNumeracao(prefixo="BOX", separador="/", incluir_ano=True, digitos=3), 7, 2027, "BOX/2027/007"),
        (FormatoNumeracao(prefixo="", separador="-", incluir_ano=True, digitos=5), 15, 2026, "2026-00015"),  # sem prefixo
        (FormatoNumeracao(prefixo="BOX-", separador="-", incluir_ano=True, digitos=5), 15, 2026, "BOX-2026-00015"),  # sem "--"
        (FormatoNumeracao(prefixo="BOX", separador="", incluir_ano=True, digitos=5), 15, 2026, "BOX202600015"),
        (FormatoNumeracao(prefixo="#", separador="", digitos=1), 12345, 2026, "#12345"),  # número maior que os dígitos
    ],
)
def test_formatador(formato, numero, ano, esperado) -> None:
    assert formatar_identificador(formato, numero, ano) == esperado
    assert "--" not in esperado


def test_validacao_do_formato() -> None:
    validar_formato(FormatoNumeracao(prefixo="BOX", separador="-", incluir_ano=True, digitos=5))
    for ruim in (
        FormatoNumeracao(prefixo="X" * 17),
        FormatoNumeracao(separador="-----"),
        FormatoNumeracao(prefixo="B O X"),  # espaço
        FormatoNumeracao(prefixo="<b>"),  # símbolo não permitido
        FormatoNumeracao(separador="?"),
        FormatoNumeracao(digitos=0),
        FormatoNumeracao(digitos=11),
        FormatoNumeracao(prefixo="A1", separador=""),  # fronteira ambígua: `A1`+`1` == `A`+`11`
        FormatoNumeracao(prefixo="", separador="", incluir_ano=False, digitos=1),  # número puro, sem marcador
    ):
        with pytest.raises(FormatoNumeracaoInvalidoError):
            validar_formato(ruim)


# ======================================================================================
# EMISSÃO: padrão, formato, histórico imutável
# ======================================================================================


def test_default_emite_hash_numero_e_mantem_numero_operacional(client_admin, db_session) -> None:
    a, b = _criar(client_admin), _criar(client_admin)
    assert (a["identificador"], b["identificador"]) == ("#1", "#2")
    assert (a["numeroOperacional"], b["numeroOperacional"]) == (1, 2)
    assert _identificador(db_session, a) == "#1"


def test_dados_de_emissao_aparecem_em_todas_as_leituras_da_demanda(client_admin) -> None:
    a = _criar(client_admin)
    assert client_admin.get(f"/demandas/{a['id']}").json()["identificador"] == "#1"
    assert client_admin.get("/demandas", params={"limit": 10}).json()[0]["identificador"] == "#1"
    assert client_admin.get("/demandas/diretorio").json()[0]["identificador"] == "#1"


def test_padrao_com_digitos_prefixo_e_ano(client_admin) -> None:
    assert _patch(client_admin, digitos=5).status_code == 200
    assert _criar(client_admin)["identificador"] == "#00001"
    assert _patch(client_admin, prefixo="TF", separador="-", digitos=5).status_code == 200
    assert _criar(client_admin)["identificador"] == "TF-00002"
    assert _patch(client_admin, prefixo="BOX", incluirAno=True).status_code == 200
    assert _criar(client_admin)["identificador"] == "BOX-2026-00003"


def test_mudar_o_padrao_nao_toca_nas_tarefas_antigas(client_admin, db_session, ano_2026) -> None:
    antiga = _criar(client_admin)
    assert antiga["identificador"] == "#1"
    resposta = _patch(client_admin, prefixo="BOX", separador="-", incluirAno=True, digitos=5)
    assert resposta.status_code == 200 and resposta.json()["preview"] == "BOX-2026-00002"  # a prévia NÃO consome número
    assert resposta.json()["preview"] == _patch(client_admin).json()["preview"]  # idempotente: ainda 00002
    nova = _criar(client_admin)
    assert nova["identificador"] == "BOX-2026-00002"
    # a antiga continua `#1` em TODA leitura e no banco; nenhum UPDATE em massa
    assert client_admin.get(f"/demandas/{antiga['id']}").json()["identificador"] == "#1"
    assert _identificador(db_session, antiga) == "#1"
    # ano muda: sem reinício (decisão deliberada da 7D.1) — BOX-2027-00003
    ano_2026["valor"] = 2027
    assert _criar(client_admin)["identificador"] == "BOX-2027-00003"
    assert client_admin.get(f"/demandas/{nova['id']}").json()["identificador"] == "BOX-2026-00002"


def test_identificador_e_imutavel_pelo_patch_da_demanda(client_admin) -> None:
    d = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{d['id']}", json={"identificador": "HACK-1", "nome": "novo nome"})
    assert resposta.status_code == 422 or resposta.json()["identificador"] == "#1"
    assert client_admin.get(f"/demandas/{d['id']}").json()["identificador"] == "#1"


# ======================================================================================
# PRÓXIMO NÚMERO
# ======================================================================================


def test_proximo_numero_alto_e_rejeicao_de_regressao(client_admin) -> None:
    for _ in range(10):
        _criar(client_admin)
    leitura = client_admin.get(URL).json()
    assert (leitura["maiorNumeroEmitido"], leitura["proximoNumero"]) == (10, 11)
    ok = _patch(client_admin, proximoNumero=100)
    assert ok.status_code == 200 and ok.json()["proximoNumero"] == 100 and ok.json()["contadorAtual"] == 99
    assert _criar(client_admin)["numeroOperacional"] == 100
    # maior = 100: 50, 100 (já emitido) são rejeitados no BACKEND; 101 passa
    for invalido in (50, 100, 1):
        resposta = _patch(client_admin, proximoNumero=invalido)
        assert resposta.status_code == 422, invalido
        assert "101" in resposta.json()["detail"]
    assert client_admin.get(URL).json()["proximoNumero"] == 101  # nada mudou nas rejeições
    assert _patch(client_admin, proximoNumero=101).status_code == 200


def test_primeira_emissao_pode_comecar_em_numero_alto(client_admin) -> None:
    assert client_admin.get(URL).json()["proximoNumero"] == 1
    assert _patch(client_admin, proximoNumero=5001).status_code == 200
    primeira = _criar(client_admin)
    assert (primeira["numeroOperacional"], primeira["identificador"]) == (5001, "#5001")


@pytest.mark.parametrize("corpo", [{"proximoNumero": 0}, {"proximoNumero": -3}, {"proximoNumero": 2**31}, {"digitos": 0},
                                   {"digitos": 11}, {"prefixo": "X" * 17}, {"separador": "-----"}, {"prefixo": "a b"}])
def test_payload_invalido_422(client_admin, corpo) -> None:
    assert _patch(client_admin, **corpo).status_code == 422


def test_reinicio_anual_e_empresa_id_nao_existem_nesta_fase(client_admin) -> None:
    assert _patch(client_admin, reinicioAnual=True).status_code == 422
    assert _patch(client_admin, empresaId=str(uuid.uuid4())).status_code == 422
    assert "reinicioAnual" not in client_admin.get(URL).json()


# ======================================================================================
# CONSISTÊNCIA, AUTORIZAÇÃO, TENANT
# ======================================================================================


def test_consistencia_detecta_contador_atras_do_maior_emitido(client_admin, db_session, empresa) -> None:
    _criar(client_admin), _criar(client_admin)
    assert client_admin.get(URL).json()["consistente"] is True
    db_session.execute(text("UPDATE sequencias_operacionais SET ultimo_numero = 1 WHERE empresa_id = :e"), {"e": empresa.id})
    db_session.commit()
    corpo = client_admin.get(URL).json()
    assert corpo["consistente"] is False and corpo["motivoInconsistencia"]


def test_so_admin_e_gestor_configuram(client_admin, client_gestor, client_operador) -> None:
    assert _patch(client_operador, prefixo="X").status_code == 403
    assert client_operador.get(URL).status_code == 403
    assert _patch(client_gestor, prefixo="GST", separador="-").status_code == 200
    assert _patch(client_admin, prefixo="ADM", separador="-").status_code == 200
    assert client_gestor.get(URL).json()["prefixo"] == "ADM"  # mesma empresa, mesma configuração


def test_head_e_atendimento_sem_perfil_administrativo_nao_configuram(app, db_session, empresa, client_admin) -> None:
    from tests.test_d1_criacao_demandas import _client_para, _head_por_responsavel, _operador_comum
    from tests.test_fase_7c_visoes_lideranca import _atendimento

    head = _operador_comum(db_session, empresa, sufixo="n-head")
    _head_por_responsavel(db_session, empresa, head)
    ana = _operador_comum(db_session, empresa, sufixo="n-ana")
    _atendimento(db_session, empresa, ana)
    db_session.commit()
    for usuario in (head, ana):
        cliente = _client_para(app, usuario)
        assert cliente.get(URL).status_code == 403
        assert cliente.patch(URL, json={"prefixo": "X"}).status_code == 403


def test_tenants_independentes(app, db_session, empresa, outra_empresa, client_admin) -> None:
    client_b = _cliente_para_outra_empresa(app, db_session, outra_empresa)
    assert _patch(client_admin, prefixo="BOX", separador="-", digitos=5, proximoNumero=700).status_code == 200
    assert _patch(client_b, prefixo="AG", separador="-", digitos=3).status_code == 200
    a, b = _criar(client_admin), _criar(client_b)
    assert (a["identificador"], b["identificador"]) == ("BOX-00700", "AG-001")
    assert (client_admin.get(URL).json()["prefixo"], client_b.get(URL).json()["prefixo"]) == ("BOX", "AG")
    assert client_b.get(URL).json()["maiorNumeroEmitido"] == 1  # a sequência da empresa A nunca é lida/consumida por B
    # mesmo identificador em empresas diferentes é permitido (unicidade é por empresa)
    assert _patch(client_b, prefixo="BOX", separador="-", digitos=5, proximoNumero=700).status_code == 200
    assert _criar(client_b)["identificador"] == "BOX-00700"


def test_unicidade_do_identificador_por_empresa_no_banco(client_admin, db_session, empresa) -> None:
    from sqlalchemy.exc import IntegrityError

    a, b = _criar(client_admin), _criar(client_admin)
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE demandas SET identificador = :i WHERE id = :d"), {"i": a["identificador"], "d": b["id"]})
        db_session.flush()
    db_session.rollback()


# ======================================================================================
# BUSCA
# ======================================================================================


def test_busca_por_numero_hash_numero_e_identificador_completo(client_admin) -> None:
    antiga = _criar(client_admin)
    _patch(client_admin, prefixo="BOX", separador="-", incluirAno=True, digitos=5)
    nova = _criar(client_admin)

    def achados(termo: str) -> set[str]:
        resposta = client_admin.get("/demandas", params={"search": termo, "limit": 50})
        assert resposta.status_code == 200
        return {d["id"] for d in resposta.json()}

    assert antiga["id"] in achados("1")  # número puro: igualdade exata (+ texto, como sempre)
    assert achados("#1") == {antiga["id"]}
    assert nova["id"] in achados("2")  # número operacional continua funcionando
    assert achados("BOX-2026-00002") == {nova["id"]}
    assert achados("box-2026-00002") == {nova["id"]}  # sem diferenciar caixa
    assert achados("BOX-2026-0000") == set()  # identificador é igualdade exata, nunca parcial


# ======================================================================================
# ATOMICIDADE E CONCORRÊNCIA
# ======================================================================================


def test_criacao_que_falha_nao_queima_numero_nem_deixa_demanda(client_admin, db_session) -> None:
    primeira = _criar(client_admin)
    falha = client_admin.post("/demandas", json={"nome": "x", "clienteId": str(uuid.uuid4())})
    assert falha.status_code in (404, 422)
    segunda = _criar(client_admin)
    assert (primeira["numeroOperacional"], segunda["numeroOperacional"]) == (1, 2)  # sem buraco
    assert db_session.scalar(text("SELECT count(*) FROM demandas")) == 2


def _empresa_commitada(test_engine) -> str:
    from sqlalchemy.orm import Session as SessionRaw

    empresa_id = str(uuid.uuid4())
    with SessionRaw(bind=test_engine) as setup:
        setup.execute(
            text(
                "INSERT INTO empresas (id, nome, documento, codigo_interno, slug, status, created_at, updated_at) "
                "VALUES (:id, 'Empresa Concorrencia 7D', NULL, :ci, lower(CAST(:ci AS varchar)), 'ativa', now(), now())"
            ),
            {"id": empresa_id, "ci": f"CONC7D-{uuid.uuid4().hex[:8]}".upper()},
        )
        setup.commit()
    return empresa_id


def _limpar(test_engine, empresa_id: str) -> None:
    from sqlalchemy.orm import Session as SessionRaw

    with SessionRaw(bind=test_engine) as limpeza:
        limpeza.execute(text("DELETE FROM sequencias_operacionais WHERE empresa_id = :e"), {"e": empresa_id})
        limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
        limpeza.commit()


def test_concorrencia_emissoes_paralelas_nao_duplicam_numero_nem_identificador(test_engine) -> None:
    from sqlalchemy.orm import Session as SessionRaw

    from app.core.sequencias_operacionais import reservar_proximo_identificado

    empresa_id = _empresa_commitada(test_engine)
    total = 8
    barreira = threading.Barrier(total)
    obtidos: list[tuple[int, str]] = []
    trava = threading.Lock()

    def emitir() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()
            reserva = reservar_proximo_identificado(sessao, empresa_id=empresa_id, tipo_entidade="demanda", ano=2026)
            sessao.commit()
        with trava:
            obtidos.append((reserva.numero, reserva.identificador))

    threads = [threading.Thread(target=emitir) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(n for n, _ in obtidos) == list(range(1, total + 1))
        assert len({i for _, i in obtidos}) == total  # identificadores distintos
        assert sorted(i for _, i in obtidos) == sorted(f"#{n}" for n in range(1, total + 1))
    finally:
        _limpar(test_engine, empresa_id)


def test_patch_espera_a_emissao_em_curso_e_o_estado_final_e_coerente(test_engine) -> None:
    """A emissão (transação A) tem o lock da linha do contador; o PATCH (transação B) NÃO passa por cima: espera o commit de A,
    lê o estado já definitivo e aplica. Resultado: ou tarefa `#1` ou formato novo — nunca meio a meio nem número repetido."""
    from sqlalchemy.orm import Session as SessionRaw

    from app.core.sequencias_operacionais import reservar_proximo_identificado
    from app.schemas.configuracao_numeracao_tarefa import ConfiguracaoNumeracaoTarefaUpdate
    from app.services.configuracao_numeracao_tarefa_service import ConfiguracaoNumeracaoTarefaService

    empresa_id = _empresa_commitada(test_engine)
    resultado: dict = {}

    def aplicar_patch() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            resultado["inicio"] = time.monotonic()
            ConfiguracaoNumeracaoTarefaService().atualizar(
                sessao, empresa_id=empresa_id, data=ConfiguracaoNumeracaoTarefaUpdate(prefixo="BOX", separador="-", digitos=5)
            )
            resultado["fim"] = time.monotonic()

    try:
        with SessionRaw(bind=test_engine) as emissao:
            reserva = reservar_proximo_identificado(emissao, empresa_id=empresa_id, tipo_entidade="demanda", ano=2026)
            assert reserva.identificador == "#1"  # A emitiu com o formato ANTIGO, sob o lock
            patch = threading.Thread(target=aplicar_patch)
            patch.start()
            time.sleep(0.6)
            assert patch.is_alive(), "o PATCH deveria estar esperando o lock da emissão em curso"
            emissao.commit()
        patch.join(timeout=20)
        assert not patch.is_alive()
        with SessionRaw(bind=test_engine) as leitura:
            linha = leitura.execute(
                text("SELECT ultimo_numero, prefixo, separador, digitos FROM sequencias_operacionais WHERE empresa_id = :e"),
                {"e": empresa_id},
            ).one()
            assert tuple(linha) == (1, "BOX", "-", 5)  # contador preservado + formato novo inteiro
            # e a PRÓXIMA emissão já sai no formato novo, sem repetir o número
            proxima = reservar_proximo_identificado(leitura, empresa_id=empresa_id, tipo_entidade="demanda", ano=2026)
            leitura.commit()
            assert (proxima.numero, proxima.identificador) == (2, "BOX-00002")
    finally:
        _limpar(test_engine, empresa_id)
