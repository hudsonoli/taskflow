"""Fase 2G.10C-B — codigoInterno de Usuario gerado pelo backend, nunca aceito do cliente.

Mesmo padrão de Cliente (ver app/services/cliente_service.py e app/schemas/cliente.py):
a API pública nunca recebe `codigoInterno` em CREATE nem em UPDATE — o backend é a única
autoridade, via `gerar_proxima_referencia` (app/core/referencias.py).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.services.usuario_service import UsuarioService, UsuarioConflictError

CODIGO_INTERNO_USUARIO_RE = re.compile(r"^U\d{2}\d{6}$")


def _payload_usuario(empresa_id: str, **overrides) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    payload = {
        "empresaId": empresa_id,
        "nome": "Usuário Teste 2G.10C-B",
        "email": f"usr-2g10cb-{sufixo}@teste.taskfloww.local",
        "perfilBase": "operador",
        "acessoSistema": True,
    }
    payload.update(overrides)
    return payload


def _criar_empresa(db: Session) -> Empresa:
    agora = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()),
        nome="Empresa Codigo Interno Usuario",
        documento=None,
        codigo_interno=f"CODIGO-USR-{uuid.uuid4().hex[:8]}".upper(),
        status="ativa",
        created_at=agora,
        updated_at=agora,
    )
    db.add(empresa)
    db.flush()
    return empresa


# --------------------------------------------------------------------------------------
# 1-2. CREATE sem codigoInterno: 201, formato correto
# --------------------------------------------------------------------------------------


def test_create_sem_codigo_interno_gera_no_backend(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.post("/usuarios", json=_payload_usuario(empresa.id))
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert CODIGO_INTERNO_USUARIO_RE.match(corpo["codigoInterno"]), corpo["codigoInterno"]


# --------------------------------------------------------------------------------------
# 3. POST com codigoInterno explícito: 422 (extra="forbid")
# --------------------------------------------------------------------------------------


def test_create_com_codigo_interno_explicito_e_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    payload = _payload_usuario(empresa.id, codigoInterno="tentativa-manual")
    resposta = client_admin.post("/usuarios", json=payload)
    assert resposta.status_code == 422, resposta.text


# --------------------------------------------------------------------------------------
# 4. PATCH com codigoInterno: 422 (campo removido de UsuarioUpdate + extra="forbid")
# --------------------------------------------------------------------------------------


def test_patch_com_codigo_interno_e_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa.id))
    assert criado.status_code == 201, criado.text
    usuario_id = criado.json()["id"]

    resposta = client_admin.patch(f"/usuarios/{usuario_id}", json={"codigoInterno": "outro-valor"})
    assert resposta.status_code == 422, resposta.text

    # O valor original não foi alterado.
    lido = client_admin.get(f"/usuarios/{usuario_id}")
    assert lido.json()["codigoInterno"] == criado.json()["codigoInterno"]


# --------------------------------------------------------------------------------------
# 5. Dois usuários na mesma empresa: códigos diferentes, sequência crescente
# --------------------------------------------------------------------------------------


def test_dois_usuarios_mesma_empresa_recebem_codigos_distintos_e_crescentes(
    client_admin: TestClient, empresa: Empresa
) -> None:
    primeiro = client_admin.post("/usuarios", json=_payload_usuario(empresa.id))
    segundo = client_admin.post("/usuarios", json=_payload_usuario(empresa.id))
    assert primeiro.status_code == 201, primeiro.text
    assert segundo.status_code == 201, segundo.text

    codigo_1 = primeiro.json()["codigoInterno"]
    codigo_2 = segundo.json()["codigoInterno"]
    assert codigo_1 != codigo_2
    sequencial_1 = int(codigo_1[-6:])
    sequencial_2 = int(codigo_2[-6:])
    assert sequencial_2 == sequencial_1 + 1


# --------------------------------------------------------------------------------------
# 6. Duas empresas: sequências independentes
# --------------------------------------------------------------------------------------


def test_duas_empresas_tem_sequencias_independentes(db_session: Session, empresa: Empresa) -> None:
    outra = _criar_empresa(db_session)
    service = UsuarioService()

    usuario_a = service.create_usuario(
        db_session,
        UsuarioCreate(**_payload_usuario(empresa.id)),
        actor_usuario_id=None,
    )
    usuario_b = service.create_usuario(
        db_session,
        UsuarioCreate(**_payload_usuario(outra.id)),
        actor_usuario_id=None,
    )

    # Cada empresa começa sua própria sequência do zero — mesmo padrão de Cliente/Departamento.
    assert usuario_a.codigo_interno[-6:] == usuario_b.codigo_interno[-6:] == "000001"


# --------------------------------------------------------------------------------------
# 7. Usuário legado (codigo_interno em formato antigo) preserva o valor no GET
# --------------------------------------------------------------------------------------


def test_usuario_legado_preserva_codigo_interno_antigo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    agora = datetime.now(timezone.utc)
    legado = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"usuario-legado-{uuid.uuid4().hex[:8]}",
        nome="Usuário Legado",
        email=f"legado-{uuid.uuid4().hex[:8]}@teste.taskfloww.local",
        perfil_base="operador",
        acesso_sistema=True,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(legado)
    db_session.flush()

    resposta = client_admin.get(f"/usuarios/{legado.id}")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["codigoInterno"] == legado.codigo_interno


# --------------------------------------------------------------------------------------
# 8. Falha no create: contador não avança (rollback é transacional)
# --------------------------------------------------------------------------------------


def test_falha_no_create_nao_avanca_o_contador(db_session: Session, empresa: Empresa) -> None:
    service = UsuarioService()
    email_duplicado = f"duplicado-{uuid.uuid4().hex[:8]}@teste.taskfloww.local"

    # Primeiro usuário ocupa o e-mail.
    service.create_usuario(
        db_session,
        UsuarioCreate(**_payload_usuario(empresa.id, email=email_duplicado)),
        actor_usuario_id=None,
    )

    # Segundo, mesmo e-mail: falha DEPOIS de reservar a referência — o rollback deve
    # desfazer o incremento junto (ver app/core/referencias.py).
    with pytest.raises(UsuarioConflictError):
        service.create_usuario(
            db_session,
            UsuarioCreate(**_payload_usuario(empresa.id, email=email_duplicado)),
            actor_usuario_id=None,
        )

    # Um terceiro usuário, com e-mail novo, prova que o número não foi queimado: continua
    # sendo o segundo da empresa (o primeiro consumiu "000001", a tentativa falha não consumiu
    # "000002", então o terceiro recebe "000002").
    terceiro = service.create_usuario(
        db_session,
        UsuarioCreate(**_payload_usuario(empresa.id)),
        actor_usuario_id=None,
    )
    assert terceiro.codigo_interno[-6:] == "000002"


# --------------------------------------------------------------------------------------
# 9. Prefixo "usuario" registrado em PREFIXOS_REFERENCIA
# --------------------------------------------------------------------------------------


def test_prefixo_usuario_esta_registrado() -> None:
    from app.core.referencias import PREFIXOS_REFERENCIA

    assert PREFIXOS_REFERENCIA["usuario"] == "U"


# --------------------------------------------------------------------------------------
# 10. Diretório continua devolvendo codigoInterno normalmente
# --------------------------------------------------------------------------------------


def test_diretorio_retorna_codigo_interno(client_admin: TestClient, empresa: Empresa) -> None:
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa.id))
    assert criado.status_code == 201, criado.text

    diretorio = client_admin.get("/usuarios/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    item = next(u for u in diretorio.json() if u["id"] == criado.json()["id"])
    assert item["codigoInterno"] == criado.json()["codigoInterno"]


# --------------------------------------------------------------------------------------
# Extra: UsuarioUpdate() em memória não aceita codigo_interno (schema, sem precisar de API)
# --------------------------------------------------------------------------------------


def test_usuario_update_schema_rejeita_codigo_interno() -> None:
    with pytest.raises(Exception):
        UsuarioUpdate(codigoInterno="qualquer-coisa")
