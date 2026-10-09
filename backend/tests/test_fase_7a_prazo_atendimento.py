"""Fase 7A — prazo operacional (data + horário) e distribuição transversal pelo Atendimento.

Regras provadas aqui:
- ATENDIMENTO é transversal: atribui responsável e departamento de QUALQUER lugar da empresa (POST e PATCH), sem ser membro nem
  Head do destino — mas só com usuário ELEGÍVEL (mesma empresa, ativo, não bloqueado/arquivado/inativo, não conta de sistema)
  e departamento ATIVO. Permissão de atribuir ≠ escopo de leitura: `resolver_escopo_demanda` não muda;
- operador comum e Head (que não é Atendimento) NÃO ganham autoridade transversal;
- `prazoEtapaAtual` (DateTime tz-aware, prazo operacional) e `dataFimPrevista` (Date, planejamento) coexistem sem migration, e o
  dia não muda por conversão UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.test_d1_2d_operador_contexto import _com_departamento
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _head_por_responsavel, _operador_comum, _override
from tests.test_demanda import _departamento, _payload

DEPARTAMENTOS_DESTINO = ["Criação", "Social Media", "Digital", "Redação", "Mídia/Planejamento"]


def _atendente(db: Session, empresa: Empresa, sufixo: str) -> Usuario:
    ator = _operador_comum(db, empresa, sufixo=sufixo)
    _atendimento(db, empresa, ator)
    db.commit()  # uma rejeição (422) faz rollback da sessão: o cenário precisa estar confirmado para as requisições seguintes
    return ator


def _pessoa_em(db: Session, empresa: Empresa, departamento, sufixo: str) -> Usuario:
    pessoa = _operador_comum(db, empresa, sufixo=sufixo)
    _com_departamento(db, pessoa, departamento)
    db.commit()
    return pessoa


# ======================================================================================
# ATENDIMENTO — distribuição transversal (POST e PATCH)
# ======================================================================================


@pytest.mark.parametrize("nome_destino", DEPARTAMENTOS_DESTINO)
def test_atendimento_cria_para_qualquer_departamento_com_responsavel_de_la(app, db_session, empresa, nome_destino) -> None:
    ator = _atendente(db_session, empresa, "a7-post")
    destino = _departamento(db_session, empresa, nome=nome_destino)
    joao = _pessoa_em(db_session, empresa, destino, f"a7-joao-{nome_destino[:3]}")

    resposta = _client_para(app, ator).post(
        "/demandas",
        json=_payload(departamentoResponsavelIds=[destino.id], usuarioResponsavelIds=[joao.id]),
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["departamentoResponsavelIds"] == [destino.id]
    assert corpo["usuarioResponsavelIds"] == [joao.id]


@pytest.mark.parametrize("nome_destino", DEPARTAMENTOS_DESTINO)
def test_atendimento_edita_para_qualquer_departamento_e_responsavel(app, db_session, empresa, nome_destino) -> None:
    ator = _atendente(db_session, empresa, "a7-patch")
    cliente = _client_para(app, ator)
    propria = _atendimento_do(ator, db_session)
    criada = cliente.post(
        "/demandas", json=_payload(departamentoResponsavelIds=[propria.id], usuarioResponsavelIds=[ator.id])
    ).json()
    destino = _departamento(db_session, empresa, nome=nome_destino)
    joao = _pessoa_em(db_session, empresa, destino, f"a7-joao-p-{nome_destino[:3]}")

    resposta = cliente.patch(
        f"/demandas/{criada['id']}",
        json={"departamentoResponsavelIds": [destino.id], "usuarioResponsavelIds": [joao.id]},
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoResponsavelIds"] == [destino.id]
    assert resposta.json()["usuarioResponsavelIds"] == [joao.id]


def _atendimento_do(ator: Usuario, db: Session):
    from app.models.departamento import Departamento

    return db.get(Departamento, ator.departamento_id)


def test_atendimento_que_tambem_e_head_distribui_para_fora_dos_departamentos_que_lidera(app, db_session, empresa) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="a7-head-atend")
    propria = _head_por_responsavel(db_session, empresa, ator)
    propria.nome = "Atendimento"  # o departamento que ele lidera É o Atendimento
    propria.nome_normalizado = "atendimento"
    ator.departamento_id = propria.id
    db_session.flush()
    destino = _departamento(db_session, empresa, nome="Criação")
    resposta = _client_para(app, ator).post("/demandas", json=_payload(departamentoResponsavelIds=[destino.id]))
    assert resposta.status_code == 201, resposta.text


# ======================================================================================
# NÃO GENERALIZA — operador comum e Head fora do Atendimento
# ======================================================================================


def test_operador_comum_com_grant_continua_restrito_ao_proprio_departamento(app, db_session, empresa) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="a7-op")
    proprio = _departamento(db_session, empresa, nome="Criação")
    _com_departamento(db_session, ator, proprio)
    _override(db_session, usuario=ator, permissao="demandas.criar", efeito="conceder")
    outro = _departamento(db_session, empresa, nome="Digital")
    alheio = _pessoa_em(db_session, empresa, outro, "a7-op-alheio")
    db_session.commit()
    cliente = _client_para(app, ator)

    assert cliente.post("/demandas", json=_payload(departamentoResponsavelIds=[outro.id])).status_code == 422
    assert cliente.post("/demandas", json=_payload(usuarioResponsavelIds=[alheio.id])).status_code == 422
    assert (
        cliente.post(
            "/demandas", json=_payload(departamentoResponsavelIds=[proprio.id], usuarioResponsavelIds=[ator.id])
        ).status_code
        == 201
    )


def test_head_que_nao_e_atendimento_continua_limitado_aos_departamentos_que_lidera(app, db_session, empresa) -> None:
    head = _operador_comum(db_session, empresa, sufixo="a7-head")
    liderado = _head_por_responsavel(db_session, empresa, head)
    outro = _departamento(db_session, empresa, nome="Redação")
    db_session.commit()
    cliente = _client_para(app, head)
    assert cliente.post("/demandas", json=_payload(departamentoResponsavelIds=[outro.id])).status_code == 422
    assert cliente.post("/demandas", json=_payload(departamentoResponsavelIds=[liderado.id])).status_code == 201


def test_gestor_e_admin_seguem_livres(client_gestor: TestClient, client_admin: TestClient, db_session, empresa) -> None:
    destino = _departamento(db_session, empresa, nome="Mídia")
    db_session.commit()
    for cliente in (client_gestor, client_admin):
        assert cliente.post("/demandas", json=_payload(departamentoResponsavelIds=[destino.id])).status_code == 201


# ======================================================================================
# SEGURANÇA — elegibilidade continua valendo para TODOS (inclusive Atendimento)
# ======================================================================================


@pytest.mark.parametrize("status", ["inativo", "bloqueado", "arquivado"])
def test_atendimento_nao_atribui_usuario_inativo_bloqueado_ou_arquivado(app, db_session, empresa, status) -> None:
    ator = _atendente(db_session, empresa, f"a7-st-{status}")
    destino = _departamento(db_session, empresa, nome=f"Dep {status}")
    pessoa = _pessoa_em(db_session, empresa, destino, f"a7-pessoa-{status}")
    pessoa.status = status
    db_session.commit()
    resposta = _client_para(app, ator).post("/demandas", json=_payload(usuarioResponsavelIds=[pessoa.id]))
    assert resposta.status_code == 422, resposta.text


def test_ninguem_atribui_conta_de_sistema(app, db_session, empresa, client_admin: TestClient) -> None:
    ator = _atendente(db_session, empresa, "a7-sys")
    sistema = _operador_comum(db_session, empresa, sufixo="a7-sys-conta")
    sistema.is_system_account = True
    db_session.commit()
    assert _client_para(app, ator).post("/demandas", json=_payload(usuarioResponsavelIds=[sistema.id])).status_code == 422
    assert client_admin.post("/demandas", json=_payload(usuarioResponsavelIds=[sistema.id])).status_code == 422


def test_atendimento_nao_atribui_usuario_de_outra_empresa(app, db_session, empresa, outra_empresa) -> None:
    ator = _atendente(db_session, empresa, "a7-tenant")
    alheio = _operador_comum(db_session, outra_empresa, sufixo="a7-alheio")
    resposta = _client_para(app, ator).post("/demandas", json=_payload(usuarioResponsavelIds=[alheio.id]))
    assert resposta.status_code == 422, resposta.text


def test_atendimento_nao_usa_departamento_de_outra_empresa(app, db_session, empresa, outra_empresa) -> None:
    ator = _atendente(db_session, empresa, "a7-tenant-dep")
    alheio = _departamento(db_session, outra_empresa, nome="Criação")
    resposta = _client_para(app, ator).post("/demandas", json=_payload(departamentoResponsavelIds=[alheio.id]))
    assert resposta.status_code == 422, resposta.text


@pytest.mark.parametrize("status", ["inativo", "arquivado"])
def test_departamento_inativo_ou_arquivado_nao_aceita_vinculo_novo(app, db_session, empresa, client_admin, status) -> None:
    ator = _atendente(db_session, empresa, f"a7-dep-{status}")
    destino = _departamento(db_session, empresa, nome=f"Destino {status}")
    destino.status = status
    db_session.commit()
    assert _client_para(app, ator).post("/demandas", json=_payload(departamentoResponsavelIds=[destino.id])).status_code == 422
    assert client_admin.post("/demandas", json=_payload(departamentoResponsavelIds=[destino.id])).status_code == 422


# ======================================================================================
# ESCOPO DE LEITURA — NÃO muda (atribuir ≠ ler)
# ======================================================================================


def test_leitura_nao_mudou_criador_atendimento_continua_vendo_o_que_criou_e_so_ele(app, db_session, empresa) -> None:
    """`resolver_escopo_demanda` NÃO foi tocado: Atendimento já enxergava as demandas que CRIOU (`incluir_criadas_por_usuario`),
    então continua vendo a que distribuiu para Criação — por regra existente, não por regra nova."""
    ator = _atendente(db_session, empresa, "a7-leitura")
    colega = _pessoa_em(db_session, empresa, _atendimento_do(ator, db_session), "a7-leitura-colega")  # outro do Atendimento
    cliente = _client_para(app, ator)
    destino = _departamento(db_session, empresa, nome="Criação")
    joao = _pessoa_em(db_session, empresa, destino, "a7-leitura-joao")
    criada = cliente.post(
        "/demandas", json=_payload(departamentoResponsavelIds=[destino.id], usuarioResponsavelIds=[joao.id])
    ).json()

    assert criada["id"] in {item["id"] for item in cliente.get("/demandas").json()}
    assert cliente.get(f"/demandas/{criada['id']}").status_code == 200
    # quem recebeu enxerga como responsável; outro Atendimento que não criou nem é responsável NÃO enxerga
    assert _client_para(app, joao).get(f"/demandas/{criada['id']}").status_code == 200
    assert _client_para(app, colega).get(f"/demandas/{criada['id']}").status_code == 404


# ======================================================================================
# PRAZO — data + horário
# ======================================================================================


def test_criacao_persiste_prazo_com_horario_e_data_planejada_sem_segundo_patch(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/demandas", json=_payload(prazoEtapaAtual="2026-10-15T16:30:00-03:00", dataFimPrevista="2026-10-15")
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    # instante correto (16:30 em São Paulo = 19:30Z), sem segunda chamada
    assert datetime.fromisoformat(corpo["prazoEtapaAtual"].replace("Z", "+00:00")) == datetime(2026, 10, 15, 19, 30, tzinfo=timezone.utc)
    assert corpo["dataFimPrevista"] == "2026-10-15"
    lido = client_admin.get(f"/demandas/{corpo['id']}").json()
    assert datetime.fromisoformat(lido["prazoEtapaAtual"].replace("Z", "+00:00")) == datetime(2026, 10, 15, 19, 30, tzinfo=timezone.utc)
    assert lido["dataFimPrevista"] == "2026-10-15"


def test_prazo_perto_da_meia_noite_nao_muda_o_dia_planejado(client_admin: TestClient) -> None:
    """22:30 em São Paulo já é dia 16 em UTC; a data planejada continua sendo o dia LOCAL escolhido (15)."""
    corpo = client_admin.post(
        "/demandas", json=_payload(prazoEtapaAtual="2026-10-15T22:30:00-03:00", dataFimPrevista="2026-10-15")
    ).json()
    assert datetime.fromisoformat(corpo["prazoEtapaAtual"].replace("Z", "+00:00")) == datetime(2026, 10, 16, 1, 30, tzinfo=timezone.utc)
    assert corpo["dataFimPrevista"] == "2026-10-15"


def test_campos_de_prazo_sao_independentes_e_opcionais(client_admin: TestClient) -> None:
    so_data = client_admin.post("/demandas", json=_payload(dataFimPrevista="2026-10-20")).json()
    assert so_data["dataFimPrevista"] == "2026-10-20" and so_data["prazoEtapaAtual"] is None
    so_prazo = client_admin.post("/demandas", json=_payload(prazoEtapaAtual="2026-10-20T09:00:00-03:00")).json()
    assert so_prazo["dataFimPrevista"] is None and so_prazo["prazoEtapaAtual"] is not None


def test_prazo_sem_fuso_e_tratado_como_utc_por_isso_o_cliente_envia_o_deslocamento(client_admin: TestClient) -> None:
    """Caracterização: o backend interpreta data/hora SEM deslocamento como UTC — o frontend precisa enviar o ISO com fuso."""
    corpo = client_admin.post("/demandas", json=_payload(prazoEtapaAtual="2026-10-15T16:30:00")).json()
    assert datetime.fromisoformat(corpo["prazoEtapaAtual"].replace("Z", "+00:00")) == datetime(2026, 10, 15, 16, 30, tzinfo=timezone.utc)
