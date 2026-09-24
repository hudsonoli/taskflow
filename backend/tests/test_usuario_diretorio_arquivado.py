"""R1 — /usuarios/diretorio passa a incluir Usuario arquivado por padrão.

Referências históricas (responsável de cliente/departamento, membro de equipe, autor de
evento etc.) precisam continuar resolvendo nome/avatar mesmo depois do usuário ser
arquivado. Quem monta opções de NOVA seleção continua filtrando "ativo" no cliente — este
teste cobre só o contrato do endpoint, não o comportamento de picker do frontend.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario


def _usuario(
    db: Session,
    empresa: Empresa,
    *,
    status: str = "ativo",
    is_system_account: bool = False,
) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"u-{sufixo}",
        nome=f"Usuário {status} {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status=status,
        is_system_account=is_system_account,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def test_diretorio_sem_status_inclui_arquivado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    arquivado = _usuario(db_session, empresa, status="arquivado")

    resposta = client_admin.get("/usuarios/diretorio")
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert arquivado.id in ids


def test_diretorio_sem_status_inclui_todos_os_status_validos(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Confirma exatamente os 4 status definidos no model (ck_usuarios_status) — nenhum
    inventado, nenhum omitido."""
    criados = {status: _usuario(db_session, empresa, status=status) for status in ("ativo", "inativo", "bloqueado", "arquivado")}

    resposta = client_admin.get("/usuarios/diretorio")
    assert resposta.status_code == 200, resposta.text
    itens = {item["id"]: item["status"] for item in resposta.json()}

    for status, usuario in criados.items():
        assert usuario.id in itens, f"status {status!r} ausente do diretório"
        assert itens[usuario.id] == status


def test_status_explicito_ativo_filtra_somente_ativo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    ativo = _usuario(db_session, empresa, status="ativo")
    arquivado = _usuario(db_session, empresa, status="arquivado")

    resposta = client_admin.get("/usuarios/diretorio", params={"status": "ativo"})
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert ativo.id in ids
    assert arquivado.id not in ids


def test_status_explicito_arquivado_filtra_somente_arquivado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    ativo = _usuario(db_session, empresa, status="ativo")
    arquivado = _usuario(db_session, empresa, status="arquivado")

    resposta = client_admin.get("/usuarios/diretorio", params={"status": "arquivado"})
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert arquivado.id in ids
    assert ativo.id not in ids


def test_diretorio_arquivado_nao_vaza_cross_tenant(
    client_admin: TestClient, db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    arquivado_outra_empresa = _usuario(db_session, outra_empresa, status="arquivado")

    resposta = client_admin.get("/usuarios/diretorio")
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert arquivado_outra_empresa.id not in ids


def test_system_account_nunca_aparece_independente_do_status(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    sistema_arquivado = _usuario(db_session, empresa, status="arquivado", is_system_account=True)
    sistema_ativo = _usuario(db_session, empresa, status="ativo", is_system_account=True)

    sem_filtro = client_admin.get("/usuarios/diretorio")
    assert sem_filtro.status_code == 200, sem_filtro.text
    ids_sem_filtro = [u["id"] for u in sem_filtro.json()]
    assert sistema_arquivado.id not in ids_sem_filtro
    assert sistema_ativo.id not in ids_sem_filtro

    # E também não aparece nem sob filtro explícito de status igual ao seu.
    com_filtro = client_admin.get("/usuarios/diretorio", params={"status": "arquivado"})
    assert com_filtro.status_code == 200, com_filtro.text
    assert sistema_arquivado.id not in [u["id"] for u in com_filtro.json()]


def test_resolucao_historica_cliente_responsavel_comercial_arquivado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Confirma ponta a ponta que a correção do diretório é suficiente para o frontend
    resolver o nome do responsável comercial de um Cliente mesmo depois dele ser arquivado
    — sem qualquer alteração em ClientesTable/ClienteFormModal (fora do escopo do R1)."""
    responsavel = _usuario(db_session, empresa, status="ativo")

    cliente = client_admin.post(
        "/clientes",
        json={
            "nome": "Cliente com responsável arquivado",
            "tipoDocumento": "cnpj",
            "corIdentificacao": "blue",
            "responsavelComercialId": responsavel.id,
        },
    )
    assert cliente.status_code == 201, cliente.text
    assert cliente.json()["responsavelComercialId"] == responsavel.id

    # Arquiva o responsável DEPOIS de vinculado ao cliente — o vínculo em Cliente nunca é
    # tocado (SET NULL só dispara em delete físico, que nunca acontece pra Usuario).
    responsavel.status = "arquivado"
    db_session.add(responsavel)
    db_session.flush()

    diretorio = client_admin.get("/usuarios/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    item = next((u for u in diretorio.json() if u["id"] == responsavel.id), None)
    assert item is not None, "responsável arquivado precisa continuar resolvível pelo diretório"
    assert item["status"] == "arquivado"
    assert item["nome"] == responsavel.nome

    # E o Cliente continua apontando pro mesmo id — o frontend consegue casar os dois.
    assert client_admin.get(f"/clientes/{cliente.json()['id']}").json()["responsavelComercialId"] == responsavel.id


def test_usuarios_normal_continua_excluindo_arquivado_por_padrao(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """R1 altera somente /usuarios/diretorio — /usuarios (rota normal, UsuarioRepository.list)
    continua com o comportamento antigo: sem status explícito, arquivado fica oculto."""
    arquivado = _usuario(db_session, empresa, status="arquivado")

    resposta = client_admin.get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert arquivado.id not in ids
