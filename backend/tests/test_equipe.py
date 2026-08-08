"""Equipe + membros — Fase 2A/Etapa C. Ver app/services/equipe_service.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from tests.helpers.assertions import assert_conflito_arquivado, assert_erro_simples


def _nome_unico(prefixo: str) -> str:
    return f"{prefixo} {uuid.uuid4().hex[:8]}"


def _payload(nome: str | None = None, cor: str = "purple", **extra) -> dict:
    return {"nome": nome or _nome_unico("Squad"), "corIdentificacao": cor, **extra}


def _criar_departamento(client: TestClient, nome: str | None = None) -> dict:
    resposta = client.post(
        "/departamentos", json={"nome": nome or _nome_unico("Depto"), "corIdentificacao": "blue"}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_usuario_na_empresa(db: Session, empresa: Empresa, status: str = "ativo") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"membro-{sufixo}",
        nome=f"Membro {sufixo}",
        email=f"membro-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


# --------------------------------------------------------------------------------------
# Criação e código de referência
# --------------------------------------------------------------------------------------

def test_criar_equipe_departamental(client_admin: TestClient) -> None:
    departamento = _criar_departamento(client_admin)
    resposta = client_admin.post("/equipes", json=_payload(departamentoId=departamento["id"]))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["departamentoId"] == departamento["id"]
    assert corpo["status"] == "ativo"


def test_criar_equipe_transversal(client_admin: TestClient) -> None:
    """Sem departamento é caso legítimo, não dado faltando."""
    resposta = client_admin.post("/equipes", json=_payload())
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["departamentoId"] is None


def test_codigo_referencia_no_formato_esperado(client_admin: TestClient) -> None:
    corpo = client_admin.post("/equipes", json=_payload()).json()
    ano = datetime.now(timezone.utc).year
    assert corpo["codigoReferencia"] == f"E{ano % 100:02d}{corpo['sequencialReferencia']:06d}"
    assert len(corpo["codigoReferencia"]) == 9


def test_sequencia_equipe_independente_de_departamento(client_admin: TestClient) -> None:
    departamento = _criar_departamento(client_admin)
    equipe = client_admin.post("/equipes", json=_payload()).json()
    assert equipe["codigoReferencia"].startswith("E")
    assert departamento["codigoReferencia"].startswith("D")


def test_editar_equipe(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    resposta = client_admin.patch(f"/equipes/{criada['id']}", json={"nome": _nome_unico("Editada")})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"].startswith("Editada")


# --------------------------------------------------------------------------------------
# Campos gerados e imutabilidade
# --------------------------------------------------------------------------------------

def test_campos_gerados_rejeitados(client_admin: TestClient, empresa: Empresa) -> None:
    for extra in [
        {"empresaId": empresa.id},
        {"actorUsuarioId": str(uuid.uuid4())},
        {"codigoInterno": "equipe-hack"},
        {"codigoReferencia": "E26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
    ]:
        resposta = client_admin.post("/equipes", json=_payload(**extra))
        assert resposta.status_code == 422, f"{extra}: {resposta.text}"


def test_codigos_imutaveis_no_patch(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    for extra in [
        {"codigoReferencia": "E26999999"},
        {"anoReferencia": 2030},
        {"sequencialReferencia": 999},
        {"codigoInterno": "equipe-outra"},
    ]:
        assert client_admin.patch(f"/equipes/{criada['id']}", json=extra).status_code == 422

    atual = client_admin.get(f"/equipes/{criada['id']}").json()
    assert atual["codigoReferencia"] == criada["codigoReferencia"]
    assert atual["codigoInterno"] == criada["codigoInterno"]


# --------------------------------------------------------------------------------------
# Duplicidade e ciclo de vida
# --------------------------------------------------------------------------------------

def test_nome_duplicado_ativo_409_simples(client_admin: TestClient) -> None:
    nome = _nome_unico("Duplicada")
    assert client_admin.post("/equipes", json=_payload(nome)).status_code == 201
    segunda = client_admin.post("/equipes", json=_payload(nome.upper()))
    assert_erro_simples(segunda, 409)
    assert isinstance(segunda.json()["detail"], str)


def test_nome_de_arquivada_409_padronizado(client_admin: TestClient) -> None:
    nome = _nome_unico("Arquivada")
    criada = client_admin.post("/equipes", json=_payload(nome)).json()
    client_admin.post(f"/equipes/{criada['id']}/arquivar", json={"motivoArquivamento": "x"})

    tentativa = client_admin.post("/equipes", json=_payload(nome))
    detail = assert_conflito_arquivado(tentativa, code="EQUIPE_ARQUIVADA_EXISTENTE")
    assert detail["equipeArquivadaId"] == criada["id"]


def test_arquivar_sem_motivo_422(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    assert client_admin.post(f"/equipes/{criada['id']}/arquivar", json={}).status_code == 422


def test_arquivar_e_restaurar(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    arquivada = client_admin.post(
        f"/equipes/{criada['id']}/arquivar", json={"motivoArquivamento": "reestruturação"}
    )
    assert arquivada.status_code == 200, arquivada.text
    assert arquivada.json()["status"] == "arquivado"

    restaurada = client_admin.post(f"/equipes/{criada['id']}/restaurar")
    assert restaurada.status_code == 200, restaurada.text
    assert restaurada.json()["status"] == "ativo"
    assert restaurada.json()["codigoReferencia"] == criada["codigoReferencia"]


def test_arquivar_equipe_preserva_membros(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    membro = _criar_usuario_na_empresa(db_session, empresa)
    criada = client_admin.post("/equipes", json=_payload(membroIds=[membro.id])).json()
    assert criada["membroIds"] == [membro.id]

    client_admin.post(f"/equipes/{criada['id']}/arquivar", json={"motivoArquivamento": "x"})

    total = db_session.execute(
        text("SELECT count(*) FROM equipe_membros WHERE equipe_id = :e"), {"e": criada["id"]}
    ).scalar_one()
    assert total == 1, "arquivar não pode apagar equipe_membros"


def test_listagem_filtro_e_diretorio(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    client_admin.post(f"/equipes/{criada['id']}/arquivar", json={"motivoArquivamento": "x"})

    assert all(e["id"] != criada["id"] for e in client_admin.get("/equipes").json())
    assert any(
        e["id"] == criada["id"] for e in client_admin.get("/equipes", params={"status": "arquivado"}).json()
    )
    diretorio = client_admin.get("/equipes/diretorio").json()
    item = next(e for e in diretorio if e["id"] == criada["id"])
    assert item["status"] == "arquivado"


def test_busca_por_codigo_case_insensitive(client_admin: TestClient) -> None:
    criada = client_admin.post("/equipes", json=_payload()).json()
    codigo = criada["codigoReferencia"]
    for termo in (codigo, codigo.lower()):
        encontrados = client_admin.get("/equipes", params={"search": termo}).json()
        assert any(e["id"] == criada["id"] for e in encontrados), f"não achou com {termo!r}"


# --------------------------------------------------------------------------------------
# Departamento
# --------------------------------------------------------------------------------------

def test_departamento_cross_tenant_422(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    from app.models.departamento import Departamento

    agora = datetime.now(timezone.utc)
    alheio = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"dep-alheio-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome="Depto de Outra Empresa",
        nome_normalizado=f"depto outra {uuid.uuid4().hex[:6]}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheio)
    db_session.flush()

    resposta = client_admin.post("/equipes", json=_payload(departamentoId=alheio.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_arquivado_recusa_novo_vinculo(client_admin: TestClient) -> None:
    departamento = _criar_departamento(client_admin)
    client_admin.post(f"/departamentos/{departamento['id']}/arquivar", json={"motivoArquivamento": "x"})

    resposta = client_admin.post("/equipes", json=_payload(departamentoId=departamento["id"]))
    assert resposta.status_code == 422, resposta.text


def test_vinculo_historico_com_departamento_arquivado_e_preservado(client_admin: TestClient) -> None:
    """Arquivar o departamento não arquiva nem desvincula a equipe já existente."""
    departamento = _criar_departamento(client_admin)
    equipe = client_admin.post("/equipes", json=_payload(departamentoId=departamento["id"])).json()

    client_admin.post(f"/departamentos/{departamento['id']}/arquivar", json={"motivoArquivamento": "x"})

    atual = client_admin.get(f"/equipes/{equipe['id']}").json()
    assert atual["status"] == "ativo", "arquivar departamento não pode arquivar a equipe"
    assert atual["departamentoId"] == departamento["id"], "vínculo histórico deve ser preservado"


def test_equipe_pode_virar_transversal_mesmo_com_departamento_arquivado(client_admin: TestClient) -> None:
    departamento = _criar_departamento(client_admin)
    equipe = client_admin.post("/equipes", json=_payload(departamentoId=departamento["id"])).json()
    client_admin.post(f"/departamentos/{departamento['id']}/arquivar", json={"motivoArquivamento": "x"})

    resposta = client_admin.patch(f"/equipes/{equipe['id']}", json={"departamentoId": None})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoId"] is None


# --------------------------------------------------------------------------------------
# Membros e líder
# --------------------------------------------------------------------------------------

def test_membro_cross_tenant_422(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    forasteiro = _criar_usuario_na_empresa(db_session, outra_empresa)
    resposta = client_admin.post("/equipes", json=_payload(membroIds=[forasteiro.id]))
    assert resposta.status_code == 422, resposta.text


def test_membros_de_departamentos_diferentes_sao_aceitos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    dep_a = _criar_departamento(client_admin)
    dep_b = _criar_departamento(client_admin)
    membro_a = _criar_usuario_na_empresa(db_session, empresa)
    membro_b = _criar_usuario_na_empresa(db_session, empresa)
    membro_a.departamento_id = dep_a["id"]
    membro_b.departamento_id = dep_b["id"]
    db_session.flush()

    resposta = client_admin.post("/equipes", json=_payload(membroIds=[membro_a.id, membro_b.id]))
    assert resposta.status_code == 201, resposta.text
    assert set(resposta.json()["membroIds"]) == {membro_a.id, membro_b.id}


def test_lider_e_incluido_automaticamente_nos_membros(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    lider = _criar_usuario_na_empresa(db_session, empresa)
    # Informado como líder, sem constar em membroIds.
    resposta = client_admin.post("/equipes", json=_payload(liderUsuarioId=lider.id))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["liderUsuarioId"] == lider.id
    assert lider.id in corpo["membroIds"], "líder tem de entrar automaticamente como membro"


def test_remover_lider_dos_membros_limpa_lider(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    lider = _criar_usuario_na_empresa(db_session, empresa)
    outro = _criar_usuario_na_empresa(db_session, empresa)
    criada = client_admin.post(
        "/equipes", json=_payload(liderUsuarioId=lider.id, membroIds=[lider.id, outro.id])
    ).json()
    assert criada["liderUsuarioId"] == lider.id

    # Lista completa SEM o líder.
    resposta = client_admin.patch(f"/equipes/{criada['id']}", json={"membroIds": [outro.id]})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["liderUsuarioId"] is None, "remover o líder dos membros deve limpar liderUsuarioId"
    assert corpo["membroIds"] == [outro.id]


def test_lider_arquivado_nao_pode_ser_definido(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    arquivado = _criar_usuario_na_empresa(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/equipes", json=_payload(liderUsuarioId=arquivado.id))
    assert resposta.status_code == 422, resposta.text


def test_membro_continua_resolvendo_apos_inativacao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Vínculo histórico: membro adicionado ativo permanece após ser inativado."""
    membro = _criar_usuario_na_empresa(db_session, empresa)
    criada = client_admin.post("/equipes", json=_payload(membroIds=[membro.id])).json()

    membro.status = "inativo"
    db_session.flush()

    atual = client_admin.get(f"/equipes/{criada['id']}").json()
    assert membro.id in atual["membroIds"]


def test_patch_idempotente_nao_duplica_eventos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Reenviar a MESMA lista de membros não pode gerar novos eventos de membro."""
    membro = _criar_usuario_na_empresa(db_session, empresa)
    criada = client_admin.post("/equipes", json=_payload(membroIds=[membro.id])).json()

    def contar_eventos_membro() -> int:
        return db_session.execute(
            text(
                "SELECT count(*) FROM eventos WHERE entidade_id = :e "
                "AND tipo IN ('equipe.membro_adicionado','equipe.membro_removido')"
            ),
            {"e": criada["id"]},
        ).scalar_one()

    antes = contar_eventos_membro()
    assert antes == 1, "criação com 1 membro deve gerar 1 evento"

    client_admin.patch(f"/equipes/{criada['id']}", json={"membroIds": [membro.id]})
    assert contar_eventos_membro() == antes, "PATCH idempotente não pode duplicar eventos"

    # Mudança real gera evento.
    outro = _criar_usuario_na_empresa(db_session, empresa)
    client_admin.patch(f"/equipes/{criada['id']}", json={"membroIds": [membro.id, outro.id]})
    assert contar_eventos_membro() == antes + 1


# --------------------------------------------------------------------------------------
# Isolamento e autorização
# --------------------------------------------------------------------------------------

def _equipe_de_outra_empresa(db_session: Session, outra_empresa: Empresa) -> str:
    from app.models.equipe import Equipe

    agora = datetime.now(timezone.utc)
    alheia = Equipe(
        id=str(uuid.uuid4()),
        empresa_id=outra_empresa.id,
        codigo_interno=f"equipe-alheia-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"E26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome="Equipe de Outra Empresa",
        nome_normalizado=f"equipe outra {uuid.uuid4().hex[:6]}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(alheia)
    db_session.flush()
    return alheia.id


def test_isolamento_por_empresa_em_todas_as_rotas(
    client_admin: TestClient, outra_empresa: Empresa, db_session: Session
) -> None:
    alheia_id = _equipe_de_outra_empresa(db_session, outra_empresa)

    assert client_admin.get(f"/equipes/{alheia_id}").status_code == 404
    assert client_admin.patch(f"/equipes/{alheia_id}", json={"nome": "X"}).status_code == 404
    assert (
        client_admin.post(f"/equipes/{alheia_id}/arquivar", json={"motivoArquivamento": "x"}).status_code == 404
    )
    assert client_admin.post(f"/equipes/{alheia_id}/restaurar").status_code == 404
    assert all(e["id"] != alheia_id for e in client_admin.get("/equipes").json())
    assert all(e["id"] != alheia_id for e in client_admin.get("/equipes/diretorio").json())


def test_autorizacao_por_perfil(
    client_operador: TestClient, client_gestor: TestClient, client_admin: TestClient
) -> None:
    assert client_operador.post("/equipes", json=_payload()).status_code == 403
    assert client_gestor.post("/equipes", json=_payload()).status_code == 201

    criada = client_admin.post("/equipes", json=_payload()).json()
    assert client_operador.patch(f"/equipes/{criada['id']}", json={"nome": "X"}).status_code == 403
    assert (
        client_operador.post(
            f"/equipes/{criada['id']}/arquivar", json={"motivoArquivamento": "x"}
        ).status_code
        == 403
    )
    assert client_operador.post(f"/equipes/{criada['id']}/restaurar").status_code == 403
    # Diretório alimenta seletores operacionais.
    assert client_operador.get("/equipes/diretorio").status_code == 200


# --------------------------------------------------------------------------------------
# Seed, contador e concorrência
# --------------------------------------------------------------------------------------

def test_seed_idempotente_nao_consome_sequencia(db_session: Session, empresa: Empresa) -> None:
    from app.services.equipe_service import EquipeService

    service = EquipeService()
    codigo = f"equipe-legado-{uuid.uuid4().hex[:8]}"

    primeira = service.create_equipe_com_codigo_legado(
        db_session, nome=_nome_unico("Legada"), cor_identificacao="blue",
        empresa_id=empresa.id, codigo_interno=codigo,
    )
    contador_apos = db_session.execute(
        text("SELECT ultimo_numero FROM sequencias_referencia WHERE empresa_id = :e AND tipo_entidade = 'equipe'"),
        {"e": empresa.id},
    ).scalar_one()

    segunda = service.create_equipe_com_codigo_legado(
        db_session, nome=_nome_unico("Legada"), cor_identificacao="blue",
        empresa_id=empresa.id, codigo_interno=codigo,
    )
    contador_repetido = db_session.execute(
        text("SELECT ultimo_numero FROM sequencias_referencia WHERE empresa_id = :e AND tipo_entidade = 'equipe'"),
        {"e": empresa.id},
    ).scalar_one()

    assert primeira.id == segunda.id
    assert primeira.codigo_referencia == segunda.codigo_referencia
    assert contador_repetido == contador_apos


def test_falha_na_criacao_nao_queima_numero(db_session: Session, empresa: Empresa) -> None:
    from app.schemas.equipe import EquipeCreate
    from app.services.equipe_service import EquipeConflictError, EquipeService

    service = EquipeService()
    nome = _nome_unico("RollbackEquipe")
    service.create_equipe(
        db_session, EquipeCreate(nome=nome, corIdentificacao="blue"),
        empresa_id=empresa.id, actor_usuario_id=None,
    )
    antes = db_session.execute(
        text("SELECT ultimo_numero FROM sequencias_referencia WHERE empresa_id = :e AND tipo_entidade = 'equipe'"),
        {"e": empresa.id},
    ).scalar_one()

    try:
        service.create_equipe(
            db_session, EquipeCreate(nome=nome, corIdentificacao="blue"),
            empresa_id=empresa.id, actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except EquipeConflictError:
        pass

    depois = db_session.execute(
        text("SELECT ultimo_numero FROM sequencias_referencia WHERE empresa_id = :e AND tipo_entidade = 'equipe'"),
        {"e": empresa.id},
    ).scalar_one()
    assert depois == antes


def test_concorrencia_nome_duplicado_vira_conflito_tratado(db_session: Session, empresa: Empresa) -> None:
    from app.models.equipe import Equipe
    from app.schemas.equipe import EquipeCreate
    from app.services.equipe_service import EquipeArquivadaConflictError, EquipeConflictError, EquipeService

    nome = _nome_unico("CorridaEquipe")
    agora = datetime.now(timezone.utc)
    existente = Equipe(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"equipe-corrida-{uuid.uuid4().hex[:8]}",
        codigo_referencia=f"E26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=nome.strip().lower(),
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(existente)
    db_session.flush()

    service = EquipeService()
    try:
        service.create_equipe(
            db_session, EquipeCreate(nome=nome, corIdentificacao="green"),
            empresa_id=empresa.id, actor_usuario_id=None,
        )
        raise AssertionError("deveria ter levantado conflito")
    except (EquipeConflictError, EquipeArquivadaConflictError):
        pass
