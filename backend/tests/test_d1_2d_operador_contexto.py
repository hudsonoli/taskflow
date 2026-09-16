"""D1.2D — Contexto mínimo para Operador comum em Demandas (Fase 2G.10B).

Achado central: `demandas.editar` já é default de todo `perfil_base == "operador"` desde
antes do D1.1 — só `demandas.criar` precisa de override (`demandas.criar=conceder`). Por
isso D1.2D tem dois gatilhos distintos:

- CREATE: só chega aqui quem já tem override de criação (ou é admin/gestor/Head/Atendimento,
  D1.1) — o contexto mínimo vale para o Operador comum que usou esse override.
- PATCH: vale para QUALQUER Operador comum editando dentro do próprio escopo, com ou sem
  qualquer override — porque `demandas.editar` nunca dependeu de concessão especial.

Política OPER-D refinada: `departamento_responsavel_ids ⊆ {actor.departamento_id}` e
`responsavel_ids ⊆ {actor.id} ∪ {usuários do próprio departamento}`, só quando o ator NÃO é
Head (`departamentos_como_head` vazio) — Head continua sob D1.2B para departamento e sem
restrição de responsável nesta fase. Admin/gestor sempre livres. Cliente/projeto
deliberadamente SEM nova restrição (gap registrado, não corrigido aqui).
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario

from tests.test_d1_2a_cliente_projeto import _projeto
from tests.test_d1_criacao_demandas import (
    _atendimento,
    _client_para,
    _head_por_responsavel,
    _operador_comum,
    _override,
)
from tests.test_demanda import _cliente, _departamento, _criar, _payload


def _com_departamento(db: Session, usuario: Usuario, departamento) -> Usuario:
    usuario.departamento_id = departamento.id
    db.flush()
    return usuario


# --------------------------------------------------------------------------------------
# Create — departamentos (item 19/20).
# --------------------------------------------------------------------------------------


def test_operador_grant_cria_com_proprio_departamento_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="dept-1")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-proprio")
    _com_departamento(db_session, operador, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_d1.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_cria_com_departamento_alheio_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="dept-2")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-proprio-2")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-alheio")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_d2.id])
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Departamento responsável não permitido para este usuário"


def test_operador_grant_cria_com_lista_vazia_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="dept-3")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_cria_com_proprio_e_alheio_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="dept-4")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-misto")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-misto")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas",
        json=_payload(departamentoResponsavelIds=[departamento_d1.id, departamento_d2.id]),
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Create — responsáveis (item 19/20).
# --------------------------------------------------------------------------------------


def test_operador_grant_cria_com_lista_responsaveis_vazia_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="resp-1")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_cria_com_si_proprio_como_responsavel_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="resp-2")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[operador.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_cria_com_usuario_do_proprio_departamento_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="resp-3")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-resp")
    _com_departamento(db_session, operador, departamento_d1)
    colega = _operador_comum(db_session, empresa, sufixo="resp-3-colega")
    _com_departamento(db_session, colega, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[colega.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_cria_com_usuario_de_outro_departamento_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="resp-4")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-resp-4")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-resp-4")
    outro = _operador_comum(db_session, empresa, sufixo="resp-4-outro")
    _com_departamento(db_session, outro, departamento_d2)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[outro.id])
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Responsável não permitido para este usuário"


def test_operador_grant_combinacao_departamento_e_responsavel_proprios_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="combo-1")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-combo")
    _com_departamento(db_session, operador, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas",
        json=_payload(
            departamentoResponsavelIds=[departamento_d1.id],
            usuarioResponsavelIds=[operador.id],
        ),
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Create — operador sem departamento (item 20).
# --------------------------------------------------------------------------------------


def test_operador_grant_sem_departamento_cria_com_lista_vazia_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="sem-dept-1")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_sem_departamento_cria_com_departamento_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="sem-dept-2")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-sem-dept")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_d1.id])
    )
    assert resposta.status_code == 422, resposta.text


def test_operador_grant_sem_departamento_cria_com_si_proprio_responsavel_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="sem-dept-3")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[operador.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_operador_grant_sem_departamento_cria_com_outro_responsavel_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="sem-dept-4")
    outro = _operador_comum(db_session, empresa, sufixo="sem-dept-4-outro")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[outro.id])
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Create — cliente/projeto permanecem livres (item 32, gap registrado).
# --------------------------------------------------------------------------------------


def test_operador_grant_cliente_e_projeto_continuam_livres(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Documenta conscientemente o gap: D1.2D não adiciona restrição de cliente/projeto —
    só D1.2A (Política C) continua valendo. Departamento/responsável próprios, cliente e
    projeto de terceiros, ainda assim 201."""
    operador = _operador_comum(db_session, empresa, sufixo="gap-1")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-gap")
    _com_departamento(db_session, operador, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    cliente_qualquer = _cliente(db_session, empresa)
    projeto_qualquer = _projeto(db_session, empresa, cliente_id=cliente_qualquer.id)

    resposta = _client_para(app, operador).post(
        "/demandas",
        json=_payload(
            departamentoResponsavelIds=[departamento_d1.id],
            clienteId=cliente_qualquer.id,
            projetoId=projeto_qualquer.id,
        ),
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Create — numeração/eventos (item 36).
# --------------------------------------------------------------------------------------


def test_operador_grant_rejeitado_nao_reserva_numeracao_nem_gera_evento(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="num")
    departamento_d2 = _departamento(db_session, empresa, nome="D2-num")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")

    total_antes = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_antes = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()
    eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = _client_para(app, operador).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_d2.id])
    )
    assert resposta.status_code == 422

    total_depois = db_session.execute(
        text("SELECT COUNT(*) FROM demandas WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    ultimo_depois = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one_or_none()
    eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    assert total_depois == total_antes
    assert ultimo_depois == ultimo_antes
    assert eventos_depois == eventos_antes


# --------------------------------------------------------------------------------------
# Head+grant — D1.2B decide departamento, responsáveis isentos de D1.2D (item 27).
# --------------------------------------------------------------------------------------


def test_head_com_grant_departamento_liderado_diferente_do_proprio_retorna_201(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-grant-1")
    departamento_proprio = _departamento(db_session, empresa, nome="Proprio-head")
    _com_departamento(db_session, head, departamento_proprio)
    departamento_liderado = _head_por_responsavel(db_session, empresa, head)

    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_liderado.id])
    )
    assert resposta.status_code == 201, resposta.text


def test_head_com_grant_responsavel_de_outro_departamento_continua_livre(
    app, db_session: Session, empresa: Empresa
) -> None:
    head = _operador_comum(db_session, empresa, sufixo="head-grant-2")
    _head_por_responsavel(db_session, empresa, head)
    departamento_alheio = _departamento(db_session, empresa, nome="Alheio-head")
    outro = _operador_comum(db_session, empresa, sufixo="head-grant-2-outro")
    _com_departamento(db_session, outro, departamento_alheio)

    resposta = _client_para(app, head).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[outro.id])
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Atendimento (não-Head) + grant — departamento/responsável seguem D1.2D, cliente D1.2C
# (item 28).
# --------------------------------------------------------------------------------------


def test_atendimento_nao_head_com_grant_departamento_alheio_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-grant-1")
    departamento_atendimento = _atendimento(db_session, empresa, atendimento)
    departamento_outro = _departamento(db_session, empresa, nome="Outro-atend")

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(departamentoResponsavelIds=[departamento_outro.id])
    )
    assert resposta.status_code == 422, resposta.text


def test_atendimento_nao_head_com_grant_responsavel_alheio_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    atendimento = _operador_comum(db_session, empresa, sufixo="atend-grant-2")
    _atendimento(db_session, empresa, atendimento)
    departamento_outro = _departamento(db_session, empresa, nome="Outro-atend-2")
    outro = _operador_comum(db_session, empresa, sufixo="atend-grant-2-outro")
    _com_departamento(db_session, outro, departamento_outro)

    resposta = _client_para(app, atendimento).post(
        "/demandas", json=_payload(usuarioResponsavelIds=[outro.id])
    )
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# Head + Atendimento + grant — as três regras coexistindo (item 29).
# --------------------------------------------------------------------------------------


def test_head_e_atendimento_com_grant_departamento_liderado_e_responsavel_alheio_ambos_livres(
    app, db_session: Session, empresa: Empresa
) -> None:
    ator = _operador_comum(db_session, empresa, sufixo="hae-1")
    departamento_liderado = _head_por_responsavel(db_session, empresa, ator)
    _atendimento(db_session, empresa, ator)
    departamento_outro = _departamento(db_session, empresa, nome="Outro-hae")
    outro = _operador_comum(db_session, empresa, sufixo="hae-1-outro")
    _com_departamento(db_session, outro, departamento_outro)

    resposta = _client_para(app, ator).post(
        "/demandas",
        json=_payload(
            departamentoResponsavelIds=[departamento_liderado.id],
            usuarioResponsavelIds=[outro.id],
        ),
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Override negar — regressão (item 31).
# --------------------------------------------------------------------------------------


def test_operador_com_override_negar_criar_recebe_403(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="negar-criar")
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="negar")

    resposta = _client_para(app, operador).post("/demandas", json=_payload())
    assert resposta.status_code == 403


def test_operador_com_override_negar_editar_recebe_403(
    app, db_session: Session, empresa: Empresa
) -> None:
    admin_client_indireto = _operador_comum(db_session, empresa, sufixo="negar-editar-alvo")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-negar")
    _com_departamento(db_session, admin_client_indireto, departamento_d1)
    _override(db_session, usuario=admin_client_indireto, permissao="demandas.criar", efeito="conceder")
    client = _client_para(app, admin_client_indireto)
    criada = _criar(client, departamentoResponsavelIds=[departamento_d1.id])

    _override(db_session, usuario=admin_client_indireto, permissao="demandas.editar", efeito="negar")
    resposta = client.patch(f"/demandas/{criada['id']}", json={"nome": "Novo nome"})
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Patch — operador comum SEM nenhum override especial (item 22-26).
# --------------------------------------------------------------------------------------


def test_patch_operador_comum_departamento_proprio_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-dept-1")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-patch")
    _com_departamento(db_session, operador, departamento_d1)
    admin = _operador_comum(db_session, empresa, sufixo="patch-dept-1-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [departamento_d1.id]}
    )
    assert resposta.status_code == 200, resposta.text


def test_patch_operador_comum_departamento_alheio_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-dept-2")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-patch-2")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-patch-2")
    admin = _operador_comum(db_session, empresa, sufixo="patch-dept-2-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [departamento_d2.id]}
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Departamento responsável não permitido para este usuário"


def test_patch_operador_comum_responsaveis_proprio_e_mesmo_departamento_retorna_200(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-resp-1")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-patch-resp")
    _com_departamento(db_session, operador, departamento_d1)
    colega = _operador_comum(db_session, empresa, sufixo="patch-resp-1-colega")
    _com_departamento(db_session, colega, departamento_d1)
    admin = _operador_comum(db_session, empresa, sufixo="patch-resp-1-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}",
        json={"usuarioResponsavelIds": [operador.id, colega.id]},
    )
    assert resposta.status_code == 200, resposta.text


def test_patch_operador_comum_responsavel_de_outro_departamento_e_rejeitado(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-resp-2")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-patch-resp-2")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-patch-resp-2")
    outro = _operador_comum(db_session, empresa, sufixo="patch-resp-2-outro")
    _com_departamento(db_session, outro, departamento_d2)
    admin = _operador_comum(db_session, empresa, sufixo="patch-resp-2-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}", json={"usuarioResponsavelIds": [outro.id]}
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["detail"] == "Responsável não permitido para este usuário"


def test_patch_campo_omitido_nao_aciona_d1_2d(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-omitido")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-omitido")
    _com_departamento(db_session, operador, departamento_d1)
    admin = _operador_comum(db_session, empresa, sufixo="patch-omitido-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}", json={"nome": "Só o nome"}
    )
    assert resposta.status_code == 200, resposta.text


def test_patch_demanda_fora_do_escopo_continua_404(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="patch-fora")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-fora")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-fora")
    admin = _operador_comum(db_session, empresa, sufixo="patch-fora-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    de_outro_departamento = _criar(
        _client_para(app, admin), departamentoResponsavelIds=[departamento_d2.id]
    )

    resposta = _client_para(app, operador).patch(
        f"/demandas/{de_outro_departamento['id']}", json={"nome": "Tentativa"}
    )
    assert resposta.status_code == 404, resposta.text


def test_patch_escalada_departamento_e_responsavel_e_rejeitada(
    app, db_session: Session, empresa: Empresa
) -> None:
    """O risco central do diagnóstico: Operador vê demanda do próprio departamento e tenta
    escalar para departamento/responsável alheios via PATCH — sem nenhum grant especial,
    só o `demandas.editar` default. D1.2D bloqueia antes de qualquer mutação."""
    operador = _operador_comum(db_session, empresa, sufixo="escalada")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-escalada")
    _com_departamento(db_session, operador, departamento_d1)
    departamento_d2 = _departamento(db_session, empresa, nome="D2-escalada")
    outro = _operador_comum(db_session, empresa, sufixo="escalada-outro")
    _com_departamento(db_session, outro, departamento_d2)
    admin = _operador_comum(db_session, empresa, sufixo="escalada-admin")
    admin.perfil_base = "admin"
    db_session.flush()
    criada = _criar(_client_para(app, admin), departamentoResponsavelIds=[departamento_d1.id])

    eventos_antes = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()

    resposta = _client_para(app, operador).patch(
        f"/demandas/{criada['id']}",
        json={
            "departamentoResponsavelIds": [departamento_d2.id],
            "usuarioResponsavelIds": [outro.id],
        },
    )
    assert resposta.status_code == 422, resposta.text

    eventos_depois = db_session.execute(
        text("SELECT COUNT(*) FROM eventos WHERE empresa_id = :e"), {"e": empresa.id}
    ).scalar_one()
    assert eventos_depois == eventos_antes, "escalada rejeitada não pode ter publicado evento"

    linha = db_session.execute(
        text(
            "SELECT COUNT(*) FROM demanda_departamentos WHERE demanda_id = :id AND departamento_id = :d"
        ),
        {"id": criada["id"], "d": departamento_d2.id},
    ).scalar_one()
    assert linha == 0, "departamento alheio não pode ter sido adicionado"


# --------------------------------------------------------------------------------------
# Admin/Gestor — sempre livres (item 30).
# --------------------------------------------------------------------------------------


def test_admin_nao_e_restringido_por_d1_2d(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento_qualquer = _departamento(db_session, empresa, nome="Admin-d1-2d")
    outro = _operador_comum(db_session, empresa, sufixo="admin-d1-2d-outro")
    resposta = client_admin.post(
        "/demandas",
        json=_payload(
            departamentoResponsavelIds=[departamento_qualquer.id],
            usuarioResponsavelIds=[outro.id],
        ),
    )
    assert resposta.status_code == 201, resposta.text


# --------------------------------------------------------------------------------------
# Query/performance (item 33).
# --------------------------------------------------------------------------------------


def test_create_admin_nao_chama_usuarios_do_departamento(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    outro = _operador_comum(db_session, empresa, sufixo="perf-admin")
    resultado = {}

    def _acao():
        resultado["resposta"] = client_admin.post(
            "/demandas", json=_payload(usuarioResponsavelIds=[outro.id])
        )

    with patch(
        "app.services.demanda_service.DemandaService._usuarios_do_departamento"
    ) as mock_usuarios:
        _acao()
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    mock_usuarios.assert_not_called()


def test_create_campos_ausentes_nao_chama_usuarios_do_departamento(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="perf-ausente")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-perf-ausente")
    _com_departamento(db_session, operador, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    client = _client_para(app, operador)
    resultado = {}

    def _acao():
        resultado["resposta"] = client.post("/demandas", json=_payload())

    with patch(
        "app.services.demanda_service.DemandaService._usuarios_do_departamento"
    ) as mock_usuarios:
        _acao()
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    mock_usuarios.assert_not_called()


def test_create_operador_comum_responsaveis_faz_no_maximo_uma_chamada(
    app, db_session: Session, empresa: Empresa
) -> None:
    operador = _operador_comum(db_session, empresa, sufixo="perf-op")
    departamento_d1 = _departamento(db_session, empresa, nome="D1-perf-op")
    _com_departamento(db_session, operador, departamento_d1)
    colega = _operador_comum(db_session, empresa, sufixo="perf-op-colega")
    _com_departamento(db_session, colega, departamento_d1)
    _override(db_session, usuario=operador, permissao="demandas.criar", efeito="conceder")
    client = _client_para(app, operador)
    resultado = {}

    def _acao():
        resultado["resposta"] = client.post(
            "/demandas", json=_payload(usuarioResponsavelIds=[colega.id])
        )

    from app.services.demanda_service import DemandaService

    with patch.object(
        DemandaService, "_usuarios_do_departamento", autospec=True, wraps=DemandaService._usuarios_do_departamento
    ) as mock_usuarios:
        _acao()
    assert resultado["resposta"].status_code == 201, resultado["resposta"].text
    assert mock_usuarios.call_count <= 1
