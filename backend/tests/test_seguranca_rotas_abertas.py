"""Regressão de autenticação — os três routers que respondiam sem token.

## O incidente

Durante a validação visual da Fase 2E.1, um `curl` sem `Authorization` recebeu **HTTP 200**
em três routers:

- `GET /eventos` — a trilha de auditoria inteira, incluindo `auth.login_sucesso` com nome,
  UUID e horário de cada pessoa;
- `GET /sessoes-trabalho` — quem está trabalhando em quê, agora;
- `GET|POST|DELETE /demandas/{codigo}/uploads` — ler, gravar e apagar arquivos de qualquer
  demanda, endereçados por um código curto e sequencial.

A causa não foi um `Depends` esquecido em um endpoint: os três routers nasceram sem
dependência nenhuma, e o controle vivia só no componente React que os consumia
(`AcessosView`, `TrafegoView`). Gate de frontend é UX; a porta 8010 continua aberta.

## O que estes testes travam

Um teste por método, sem token, exigindo 401 — porque o buraco era por ROUTER, não por rota.
Mais os recortes de perfil e de empresa, que impedem a correção de virar "autenticado é
suficiente".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.demanda import Demanda
from app.models.demanda_responsavel import DemandaResponsavel
from app.models.empresa import Empresa
from app.models.usuario import Usuario


# --------------------------------------------------------------------------------------
# Sem token: TODO método dos três routers precisa recusar
# --------------------------------------------------------------------------------------

# (método, caminho, corpo) — a lista cobre o router inteiro, não uma amostra.
ROTAS_PROTEGIDAS = [
    ("get", "/eventos", None),
    ("get", f"/eventos/{uuid.uuid4()}", None),
    ("post", "/eventos", {"empresaId": "x", "tipo": "t", "entidadeTipo": "e", "entidadeId": "1"}),
    ("get", "/sessoes-trabalho", None),
    ("get", f"/sessoes-trabalho/{uuid.uuid4()}", None),
    ("post", "/sessoes-trabalho/abrir", {"empresaId": "x", "demandaId": "1"}),
    ("post", f"/sessoes-trabalho/{uuid.uuid4()}/fechar", {"motivoEncerramento": "conclusao"}),
    ("get", "/demandas/T26000001/uploads", None),
    ("delete", "/demandas/T26000001/uploads/arquivo.pdf", None),
]


@pytest.mark.parametrize("metodo, caminho, corpo", ROTAS_PROTEGIDAS)
def test_sem_token_recusa(client: TestClient, metodo: str, caminho: str, corpo) -> None:
    """401 — nunca 200, nunca 404 "por acaso".

    404 aqui seria tão ruim quanto 200: significaria que a rota processou o pedido antes de
    checar a identidade de quem pediu.
    """
    resposta = getattr(client, metodo)(caminho, **({"json": corpo} if corpo else {}))
    assert resposta.status_code == 401, f"{metodo.upper()} {caminho} devolveu {resposta.status_code}"


# --------------------------------------------------------------------------------------
# /eventos — administrativo
# --------------------------------------------------------------------------------------

def test_operador_nao_le_auditoria(client_operador: TestClient) -> None:
    """A trilha de auditoria é administrativa: expõe o comportamento de todo mundo."""
    assert client_operador.get("/eventos").status_code == 403


def test_admin_e_gestor_leem_auditoria(client_admin: TestClient, client_gestor: TestClient) -> None:
    assert client_admin.get("/eventos").status_code == 200
    assert client_gestor.get("/eventos").status_code == 200


def test_empresa_vem_do_token_e_nao_do_parametro(client_admin: TestClient) -> None:
    """Pedir a auditoria de outra empresa é 403, não uma lista silenciosamente trocada.

    Sobrescrever o parâmetro sem avisar faria o chamador crer que recebeu o que pediu.
    """
    resposta = client_admin.get(f"/eventos?empresaId={uuid.uuid4()}")
    assert resposta.status_code == 403


def test_empresa_do_proprio_token_e_aceita(client_admin: TestClient, empresa) -> None:
    assert client_admin.get(f"/eventos?empresaId={empresa.id}").status_code == 200


def test_evento_de_outra_empresa_devolve_404(
    client_admin: TestClient, db_session: Session
) -> None:
    from app.models.evento import Evento

    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa",
        documento=None,
        codigo_interno=f"OUT-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    evento = Evento(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        tipo="cliente.criado",
        entidade_tipo="cliente",
        entidade_id=str(uuid.uuid4()),
        payload={},
        occurred_at=agora,
        created_at=agora,
    )
    db_session.add(evento)
    db_session.flush()

    # 404 e não 403: 403 confirmaria que o evento existe.
    assert client_admin.get(f"/eventos/{evento.id}").status_code == 404


def test_criar_evento_em_outra_empresa_e_recusado(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/eventos",
        json={
            "empresaId": str(uuid.uuid4()),
            "tipo": "cliente.criado",
            "entidadeTipo": "cliente",
            "entidadeId": str(uuid.uuid4()),
            "payload": {},
        },
    )
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# /sessoes-trabalho — Central de Tráfego
# --------------------------------------------------------------------------------------

def test_operador_nao_le_sessoes(client_operador: TestClient) -> None:
    assert client_operador.get("/sessoes-trabalho").status_code == 403


def test_admin_e_gestor_leem_sessoes(client_admin: TestClient, client_gestor: TestClient) -> None:
    assert client_admin.get("/sessoes-trabalho").status_code == 200
    assert client_gestor.get("/sessoes-trabalho").status_code == 200


def test_operador_nao_abre_sessao_em_nome_de_terceiro(
    client_operador: TestClient, empresa, usuario_gestor: Usuario
) -> None:
    resposta = client_operador.post(
        "/sessoes-trabalho/abrir",
        json={"empresaId": empresa.id, "demandaId": str(uuid.uuid4()), "usuarioId": usuario_gestor.id},
    )
    assert resposta.status_code == 403


def test_sessoes_de_outra_empresa_recusadas_no_parametro(client_admin: TestClient) -> None:
    resposta = client_admin.get(f"/sessoes-trabalho?empresaId={uuid.uuid4()}")
    assert resposta.status_code == 403


# --------------------------------------------------------------------------------------
# uploads — escopo da própria Demanda
# --------------------------------------------------------------------------------------

def _criar_demanda(client: TestClient) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Demanda {uuid.uuid4().hex[:8]}"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_upload_de_demanda_fora_do_escopo_devolve_404(
    client_admin: TestClient, client_operador: TestClient
) -> None:
    """O código (`T26000001`) é curto, sequencial e adivinhável — não pode ser a única chave.

    404 e não 403, igual ao acesso por UUID: 403 confirmaria que a demanda existe.
    """
    alheia = _criar_demanda(client_admin)
    codigo = alheia["codigoReferencia"]

    assert client_operador.get(f"/demandas/{codigo}/uploads").status_code == 404
    assert client_operador.delete(f"/demandas/{codigo}/uploads/x.pdf").status_code == 404


def test_upload_de_demanda_no_escopo_e_permitido(
    client_admin: TestClient, client_operador: TestClient, db_session: Session, usuario_operador: Usuario
) -> None:
    minha = _criar_demanda(client_admin)
    db_session.add(
        DemandaResponsavel(
            demanda_id=minha["id"],
            usuario_id=usuario_operador.id,
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()

    resposta = client_operador.get(f"/demandas/{minha['codigoReferencia']}/uploads")
    assert resposta.status_code == 200
    # Sem tabela de arquivos nesta fase — lista vazia é a verdade.
    assert resposta.json() == []


def test_codigo_inexistente_devolve_404(client_admin: TestClient) -> None:
    assert client_admin.get("/demandas/T99999999/uploads").status_code == 404


def test_codigo_com_travessia_de_caminho_devolve_404(client_admin: TestClient) -> None:
    """`..%2F..` não resolve para demanda nenhuma, então morre na checagem de escopo — antes
    de chegar ao sistema de arquivos."""
    assert client_admin.get("/demandas/..%2F..%2Fetc/uploads").status_code == 404


def test_demanda_de_outra_empresa_nao_da_acesso_aos_arquivos(
    client_admin: TestClient, db_session: Session
) -> None:
    agora = datetime.now(timezone.utc)
    outra = Empresa(
        id=str(uuid.uuid4()),
        nome="Outra Empresa Uploads",
        documento=None,
        codigo_interno=f"OUP-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(outra)
    db_session.flush()

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26009999",
        ano_referencia=26,
        sequencial_referencia=9999,
        numero_operacional=9999,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.codigo_referencia}/uploads").status_code == 404
