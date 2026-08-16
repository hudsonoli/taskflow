"""Comentários de Demanda (Fase 2E.4) — primeira versão: texto, autoria, moderação.

Sem anexo, @mention, reação, thread ou interno/externo — fora do escopo desta fase por
decisão explícita (ver instrução da Fase 2E.4).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.demanda import Demanda
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _criar_demanda(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_comentario(client: TestClient, demanda_id: str, texto: str = "Primeiro comentário") -> dict:
    resposta = client.post(f"/demandas/{demanda_id}/comentarios", json={"texto": texto})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _client_para(app, usuario: Usuario) -> TestClient:
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


# --------------------------------------------------------------------------------------
# CRUD básico
# --------------------------------------------------------------------------------------

def test_criar_comentario(client_admin: TestClient, usuario_admin: Usuario) -> None:
    demanda = _criar_demanda(client_admin)
    comentario = _criar_comentario(client_admin, demanda["id"], "Olá, tudo certo com o briefing?")

    assert comentario["texto"] == "Olá, tudo certo com o briefing?"
    assert comentario["demandaId"] == demanda["id"]
    assert comentario["autorUsuarioId"] == usuario_admin.id
    assert comentario["editadoEm"] is None


def test_texto_so_espaco_e_recusado(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.post(f"/demandas/{demanda['id']}/comentarios", json={"texto": "   "})
    assert resposta.status_code == 422, resposta.text


def test_listar_comentarios_mais_recente_primeiro(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    _criar_comentario(client_admin, demanda["id"], "Primeiro")
    _criar_comentario(client_admin, demanda["id"], "Segundo")
    _criar_comentario(client_admin, demanda["id"], "Terceiro")

    resposta = client_admin.get(f"/demandas/{demanda['id']}/comentarios")
    assert resposta.status_code == 200
    textos = [item["texto"] for item in resposta.json()]
    assert textos == ["Terceiro", "Segundo", "Primeiro"]


def test_demanda_recem_criada_tem_comentarios_vazio(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    assert client_admin.get(f"/demandas/{demanda['id']}/comentarios").json() == []


# --------------------------------------------------------------------------------------
# Autoria — editar
# --------------------------------------------------------------------------------------

def test_autor_edita_o_proprio_comentario(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    comentario = _criar_comentario(client_admin, demanda["id"])

    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/comentarios/{comentario['id']}", json={"texto": "Texto revisado"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["texto"] == "Texto revisado"
    assert corpo["editadoEm"] is not None


def test_editado_em_so_aparece_apos_edicao(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    comentario = _criar_comentario(client_admin, demanda["id"])
    assert comentario["editadoEm"] is None

    lido = client_admin.get(f"/demandas/{demanda['id']}/comentarios").json()[0]
    assert lido["editadoEm"] is None


def test_outro_operador_nao_edita_comentario_alheio(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    """O outro operador PRECISA ter escopo sobre a Demanda (senão o 404 de acesso nega
    primeiro, corretamente — ver doutrina 404-antes-de-403). O 403 é especificamente sobre
    não ser o autor, não sobre não enxergar a Demanda."""
    outro_operador = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="operador-outro"
    )
    client_autor = _client_para(app, usuario_operador)
    demanda = _criar_demanda(
        client_autor, usuarioResponsavelIds=[usuario_operador.id, outro_operador.id]
    )
    comentario = _criar_comentario(client_autor, demanda["id"])

    client_outro = _client_para(app, outro_operador)
    resposta = client_outro.patch(
        f"/demandas/{demanda['id']}/comentarios/{comentario['id']}", json={"texto": "invasão"}
    )
    assert resposta.status_code == 403


def test_admin_gestor_nao_edita_comentario_alheio(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_admin: Usuario
) -> None:
    """Moderação cobre exclusão, não edição — reescrever o texto de outra pessoa
    corromperia a autoria do que foi dito (ver instrução da Fase 2E.4, item 2)."""
    client_autor = _client_para(app, usuario_operador)
    demanda = _criar_demanda(client_autor, usuarioResponsavelIds=[usuario_operador.id])
    comentario = _criar_comentario(client_autor, demanda["id"])

    client_admin_direto = _client_para(app, usuario_admin)
    resposta = client_admin_direto.patch(
        f"/demandas/{demanda['id']}/comentarios/{comentario['id']}", json={"texto": "moderado"}
    )
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Autoria — excluir (moderação)
# --------------------------------------------------------------------------------------

def test_autor_exclui_o_proprio_comentario(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    comentario = _criar_comentario(client_admin, demanda["id"])

    resposta = client_admin.delete(f"/demandas/{demanda['id']}/comentarios/{comentario['id']}")
    assert resposta.status_code == 204
    assert client_admin.get(f"/demandas/{demanda['id']}/comentarios").json() == []


def test_admin_exclui_comentario_alheio_para_moderar(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_admin: Usuario
) -> None:
    client_autor = _client_para(app, usuario_operador)
    demanda = _criar_demanda(client_autor, usuarioResponsavelIds=[usuario_operador.id])
    comentario = _criar_comentario(client_autor, demanda["id"])

    client_admin_direto = _client_para(app, usuario_admin)
    resposta = client_admin_direto.delete(f"/demandas/{demanda['id']}/comentarios/{comentario['id']}")
    assert resposta.status_code == 204


def test_gestor_exclui_comentario_alheio_para_moderar(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    client_autor = _client_para(app, usuario_operador)
    demanda = _criar_demanda(client_autor, usuarioResponsavelIds=[usuario_operador.id])
    comentario = _criar_comentario(client_autor, demanda["id"])

    client_gestor_direto = _client_para(app, usuario_gestor)
    resposta = client_gestor_direto.delete(f"/demandas/{demanda['id']}/comentarios/{comentario['id']}")
    assert resposta.status_code == 204


def test_outro_operador_nao_exclui_comentario_alheio(
    app, db_session: Session, empresa: Empresa, usuario_operador: Usuario
) -> None:
    outro_operador = _criar_usuario_com_credencial(
        db_session, empresa=empresa, perfil_base="operador", email_prefixo="operador-outro2"
    )
    client_autor = _client_para(app, usuario_operador)
    demanda = _criar_demanda(
        client_autor, usuarioResponsavelIds=[usuario_operador.id, outro_operador.id]
    )
    comentario = _criar_comentario(client_autor, demanda["id"])

    client_outro = _client_para(app, outro_operador)
    resposta = client_outro.delete(f"/demandas/{demanda['id']}/comentarios/{comentario['id']}")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# Escopo e isolamento
# --------------------------------------------------------------------------------------

def test_demanda_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get(f"/demandas/{uuid.uuid4()}/comentarios").status_code == 404
    assert (
        client_admin.post(f"/demandas/{uuid.uuid4()}/comentarios", json={"texto": "x"}).status_code == 404
    )


def test_comentario_inexistente_devolve_404(client_admin: TestClient) -> None:
    demanda = _criar_demanda(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{demanda['id']}/comentarios/{uuid.uuid4()}", json={"texto": "x"}
    )
    assert resposta.status_code == 404


def test_comentario_de_outra_demanda_nao_e_alcancavel(client_admin: TestClient) -> None:
    demanda_a = _criar_demanda(client_admin)
    demanda_b = _criar_demanda(client_admin)
    comentario_de_a = _criar_comentario(client_admin, demanda_a["id"])

    resposta = client_admin.patch(
        f"/demandas/{demanda_b['id']}/comentarios/{comentario_de_a['id']}", json={"texto": "invasão"}
    )
    assert resposta.status_code == 404


def test_operador_sem_escopo_recebe_404(client_admin: TestClient, client_operador: TestClient) -> None:
    alheia = _criar_demanda(client_admin)
    assert client_operador.get(f"/demandas/{alheia['id']}/comentarios").status_code == 404


def test_operador_com_escopo_comenta_normalmente(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar_demanda(client_admin, usuarioResponsavelIds=[usuario_operador.id])
    comentario = _criar_comentario(client_operador, minha["id"], "Comentário do operador")
    assert comentario["autorUsuarioId"] == usuario_operador.id


def test_demanda_de_outra_empresa_devolve_404(client_admin: TestClient, db_session: Session) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Comentario",
        documento=None,
        codigo_interno=f"COM-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26006666",
        ano_referencia=26,
        sequencial_referencia=6666,
        numero_operacional=6666,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.id}/comentarios").status_code == 404


# --------------------------------------------------------------------------------------
# Eventos — sem texto completo
# --------------------------------------------------------------------------------------

def test_eventos_de_comentario_nao_carregam_texto_completo(
    client_admin: TestClient, db_session: Session
) -> None:
    demanda = _criar_demanda(client_admin)
    comentario = _criar_comentario(client_admin, demanda["id"], "Texto que não pode vazar no evento")

    client_admin.patch(
        f"/demandas/{demanda['id']}/comentarios/{comentario['id']}", json={"texto": "Texto editado, também não pode vazar"}
    )
    client_admin.delete(f"/demandas/{demanda['id']}/comentarios/{comentario['id']}")

    eventos = db_session.scalars(
        select(Evento).where(
            Evento.entidade_id == demanda["id"],
            Evento.tipo.in_(
                ["demanda.comentario_criado", "demanda.comentario_editado", "demanda.comentario_removido"]
            ),
        )
    ).all()
    assert len(eventos) == 3
    for evento in eventos:
        assert "texto" not in evento.payload
        assert comentario["id"] == evento.payload["comentarioId"]

    removido = next(e for e in eventos if e.tipo == "demanda.comentario_removido")
    assert removido.payload["autorUsuarioId"] == comentario["autorUsuarioId"]
