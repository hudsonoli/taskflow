"""`financeiro.visualizar` protege efetivamente a LEITURA de campos financeiros de Cliente
(`feeMensalCentavos`, `horasContratadasMes`) e Usuario (`valorRecebidoMensalCentavos`,
`horasTrabalhoAproximadas`) — Fase S1-A.

Fecha o vazamento reproduzido no diagnóstico S1: `clientes.visualizar`/`usuarios.visualizar`
são concedíveis por override a um operador comum, mas isso nunca implicava
`financeiro.visualizar` — antes desta fase, o campo vinha no payload de qualquer jeito.

Regras cobertas:

- Campo nunca é OMITIDO — sai como `null` sem a permissão, presente com a permissão.
- Admin/Gestor veem por default; `financeiro.visualizar = negar` explícito tira a
  visualização de qualquer um, sem hard floor (mesmo admin/gestor).
- Escrita (`clientes.criar/editar`, `usuarios.criar/editar`) e leitura (`financeiro.visualizar`)
  são eixos independentes — a resposta de CREATE/PATCH também mascara.
- `GET /usuarios/me` é a ÚNICA exceção de autovisualização — `GET /usuarios/{proprio_id}`
  (rota normal) e a própria linha aparecendo em `GET /usuarios` continuam mascaradas sem a
  permissão, mesmo sendo o próprio ator.
- `/clientes/diretorio` e `/usuarios/diretorio` seguem sem os campos (já era assim desde
  antes desta fase — só confirmado aqui como regressão).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.usuario_permissao import UsuarioPermissao
from app.services.usuario_permissao_service import UsuarioPermissaoService

from tests.fixtures.usuarios import _criar_usuario_com_credencial
from tests.test_cliente import _criar as _criar_cliente


def _client_para(app, usuario: Usuario) -> TestClient:
    token = create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {token}"
    return cliente


def _override(db: Session, *, usuario: Usuario, permissao: str, efeito: str) -> UsuarioPermissao:
    agora = datetime.now(timezone.utc)
    override = UsuarioPermissao(
        id=str(uuid.uuid4()), empresa_id=usuario.empresa_id, usuario_id=usuario.id,
        permissao=permissao, efeito=efeito, created_at=agora, updated_at=agora,
    )
    db.add(override)
    db.flush()
    return override


def _operador(db: Session, empresa: Empresa, *, sufixo: str) -> Usuario:
    return _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="operador", email_prefixo=f"fin-{sufixo}")


# ==========================================================================================
# Cliente
# ==========================================================================================


def test_admin_ve_financeiro_do_cliente(client_admin: TestClient) -> None:
    criado = _criar_cliente(client_admin, feeMensalCentavos=150000, horasContratadasMes=40)
    resposta = client_admin.get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["feeMensalCentavos"] == 150000
    assert resposta.json()["horasContratadasMes"] == 40.0


def test_gestor_ve_financeiro_do_cliente(client_gestor: TestClient, client_admin: TestClient) -> None:
    criado = _criar_cliente(client_admin, feeMensalCentavos=200000, horasContratadasMes=60)
    resposta = client_gestor.get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["feeMensalCentavos"] == 200000


def test_operador_com_clientes_visualizar_sem_financeiro_visualizar_recebe_null(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    """Regressão do vazamento reproduzido no diagnóstico S1."""
    criado = _criar_cliente(client_admin, feeMensalCentavos=150000, horasContratadasMes=40)
    operador = _operador(db_session, empresa, sufixo="cli-1")
    _override(db_session, usuario=operador, permissao="clientes.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["feeMensalCentavos"] is None
    assert resposta.json()["horasContratadasMes"] is None


def test_operador_com_clientes_e_financeiro_visualizar_ve_valores(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    criado = _criar_cliente(client_admin, feeMensalCentavos=150000, horasContratadasMes=40)
    operador = _operador(db_session, empresa, sufixo="cli-2")
    _override(db_session, usuario=operador, permissao="clientes.visualizar", efeito="conceder")
    _override(db_session, usuario=operador, permissao="financeiro.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["feeMensalCentavos"] == 150000
    assert resposta.json()["horasContratadasMes"] == 40.0


def test_admin_com_financeiro_negar_recebe_null_no_cliente(
    app, db_session: Session, usuario_admin: Usuario, client_admin: TestClient
) -> None:
    """Sem hard floor: deny explícito tira a visualização até de admin."""
    criado = _criar_cliente(client_admin, feeMensalCentavos=150000, horasContratadasMes=40)
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")

    resposta = _client_para(app, usuario_admin).get(f"/clientes/{criado['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["feeMensalCentavos"] is None
    assert resposta.json()["horasContratadasMes"] is None


def test_clientes_diretorio_continua_sem_campos_financeiros(client_admin: TestClient) -> None:
    _criar_cliente(client_admin, feeMensalCentavos=150000, horasContratadasMes=40)
    diretorio = client_admin.get("/clientes/diretorio").json()
    assert diretorio, "diretório não pode vir vazio para este teste fazer sentido"
    for item in diretorio:
        assert "feeMensalCentavos" not in item
        assert "horasContratadasMes" not in item


def test_create_cliente_sem_financeiro_visualizar_response_mascarada(
    db_session: Session, usuario_admin: Usuario, client_admin: TestClient
) -> None:
    """Escrita e leitura são eixos independentes: admin pode SEMPRE criar (clientes.criar),
    mas a resposta do próprio POST mascara se `financeiro.visualizar` foi negado."""
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")
    resposta = client_admin.post(
        "/clientes",
        json={
            "nome": "Cliente S1-A create",
            "tipoDocumento": "cnpj",
            "corIdentificacao": "blue",
            "feeMensalCentavos": 99000,
        },
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["feeMensalCentavos"] is None


def test_patch_cliente_sem_financeiro_visualizar_response_mascarada(
    db_session: Session, usuario_admin: Usuario, client_admin: TestClient
) -> None:
    criado = _criar_cliente(client_admin, feeMensalCentavos=10000)
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")

    resposta = client_admin.patch(f"/clientes/{criado['id']}", json={"feeMensalCentavos": 55000})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["feeMensalCentavos"] is None


def test_lista_clientes_nao_calcula_permissao_efetiva_por_cliente(
    app, db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    """`obter_permissoes_efetivas` é chamado no máximo 2x por request desta rota — uma vez
    pelo gate `require_permissao("clientes.visualizar")` (autorização) e uma vez por
    `to_read_lote` (mascaramento) — nunca uma vez por Cliente da lista. Cria mais clientes do
    que esse teto pra provar que a contagem não escala com N."""
    total_clientes = 5
    for _ in range(total_clientes):
        _criar_cliente(client_admin, feeMensalCentavos=1000)
    operador = _operador(db_session, empresa, sufixo="cli-query")
    _override(db_session, usuario=operador, permissao="clientes.visualizar", efeito="conceder")
    client = _client_para(app, operador)

    original = UsuarioPermissaoService.obter_permissoes_efetivas
    with patch.object(UsuarioPermissaoService, "obter_permissoes_efetivas", autospec=True) as mock_efetivas:
        mock_efetivas.side_effect = original
        resposta = client.get("/clientes")
        assert resposta.status_code == 200
        assert len(resposta.json()) >= total_clientes
        assert mock_efetivas.call_count <= 2, "financeiro.visualizar não pode ser calculado por Cliente da lista"


# ==========================================================================================
# Usuario
# ==========================================================================================


def test_admin_ve_financeiro_do_usuario(
    db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-alvo-1")
    alvo.valor_recebido_mensal_centavos = 800000
    alvo.horas_trabalho_aproximadas = 160
    db_session.flush()

    resposta = client_admin.get(f"/usuarios/{alvo.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] == 800000
    assert resposta.json()["horasTrabalhoAproximadas"] == 160.0


def test_gestor_ve_financeiro_do_usuario(
    db_session: Session, empresa: Empresa, client_gestor: TestClient
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-alvo-2")
    alvo.valor_recebido_mensal_centavos = 700000
    db_session.flush()

    resposta = client_gestor.get(f"/usuarios/{alvo.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] == 700000


def test_operador_com_usuarios_visualizar_sem_financeiro_visualizar_recebe_null(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Regressão do vazamento reproduzido no diagnóstico S1 (Usuario)."""
    alvo = _operador(db_session, empresa, sufixo="usr-alvo-3")
    alvo.valor_recebido_mensal_centavos = 800000
    alvo.horas_trabalho_aproximadas = 160
    db_session.flush()
    operador = _operador(db_session, empresa, sufixo="usr-ator-1")
    _override(db_session, usuario=operador, permissao="usuarios.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get(f"/usuarios/{alvo.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] is None
    assert resposta.json()["horasTrabalhoAproximadas"] is None


def test_operador_com_usuarios_e_financeiro_visualizar_ve_valores(
    app, db_session: Session, empresa: Empresa
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-alvo-4")
    alvo.valor_recebido_mensal_centavos = 800000
    db_session.flush()
    operador = _operador(db_session, empresa, sufixo="usr-ator-2")
    _override(db_session, usuario=operador, permissao="usuarios.visualizar", efeito="conceder")
    _override(db_session, usuario=operador, permissao="financeiro.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get(f"/usuarios/{alvo.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] == 800000


def test_admin_com_financeiro_negar_recebe_null_no_usuario(
    app, db_session: Session, empresa: Empresa, usuario_admin: Usuario
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-alvo-5")
    alvo.valor_recebido_mensal_centavos = 800000
    db_session.flush()
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")

    resposta = _client_para(app, usuario_admin).get(f"/usuarios/{alvo.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] is None


def test_usuarios_diretorio_continua_sem_campos_financeiros(
    db_session: Session, empresa: Empresa, client_admin: TestClient
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-dir")
    alvo.valor_recebido_mensal_centavos = 800000
    db_session.flush()

    diretorio = client_admin.get("/usuarios/diretorio").json()
    achado = next((u for u in diretorio if u["id"] == alvo.id), None)
    assert achado is not None
    assert "valorRecebidoMensalCentavos" not in achado
    assert "horasTrabalhoAproximadas" not in achado


def test_usuarios_me_operador_ve_proprio_financeiro_sem_permissao(
    app, db_session: Session, empresa: Empresa
) -> None:
    """A ÚNICA exceção de autovisualização: /usuarios/me sempre mostra o próprio financeiro,
    mesmo sem financeiro.visualizar."""
    operador = _operador(db_session, empresa, sufixo="me-1")
    operador.valor_recebido_mensal_centavos = 500000
    operador.horas_trabalho_aproximadas = 150
    db_session.flush()

    resposta = _client_para(app, operador).get("/usuarios/me")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] == 500000
    assert resposta.json()["horasTrabalhoAproximadas"] == 150.0
    # Comportamento pré-existente (Fase 2G.10A) preservado — não pode se perder.
    assert "permissoes" in resposta.json() and isinstance(resposta.json()["permissoes"], list)


def test_get_usuario_proprio_id_sem_financeiro_visualizar_recebe_null(
    app, db_session: Session, empresa: Empresa
) -> None:
    """CRÍTICO: prova que a exceção é exclusiva de /usuarios/me — GET /usuarios/{proprio_id}
    (rota normal) mascara igual a qualquer outro Usuario, mesmo sendo o próprio ator."""
    operador = _operador(db_session, empresa, sufixo="me-2")
    operador.valor_recebido_mensal_centavos = 500000
    operador.horas_trabalho_aproximadas = 150
    db_session.flush()
    _override(db_session, usuario=operador, permissao="usuarios.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get(f"/usuarios/{operador.id}")
    assert resposta.status_code == 200
    assert resposta.json()["valorRecebidoMensalCentavos"] is None
    assert resposta.json()["horasTrabalhoAproximadas"] is None


def test_lista_usuarios_contendo_proprio_actor_mascara_financeiro(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Mesma regra que o teste anterior, mas via GET /usuarios (lista) — a própria linha do
    ator não ganha tratamento especial fora de /usuarios/me."""
    operador = _operador(db_session, empresa, sufixo="me-3")
    operador.valor_recebido_mensal_centavos = 500000
    db_session.flush()
    _override(db_session, usuario=operador, permissao="usuarios.visualizar", efeito="conceder")

    resposta = _client_para(app, operador).get("/usuarios", params={"empresaId": empresa.id})
    assert resposta.status_code == 200
    propria_linha = next((u for u in resposta.json() if u["id"] == operador.id), None)
    assert propria_linha is not None
    assert propria_linha["valorRecebidoMensalCentavos"] is None


def test_lista_usuarios_nao_calcula_permissao_efetiva_por_usuario(
    app, db_session: Session, empresa: Empresa
) -> None:
    """Mesmo raciocínio do teste equivalente de Cliente: no máximo 2 chamadas por request
    (gate de `require_permissao` + `to_read_lote`), nunca uma por Usuario da lista."""
    total_operadores = 5
    for i in range(total_operadores):
        _operador(db_session, empresa, sufixo=f"usr-query-{i}")
    operador = _operador(db_session, empresa, sufixo="usr-query-ator")
    _override(db_session, usuario=operador, permissao="usuarios.visualizar", efeito="conceder")
    client = _client_para(app, operador)

    original = UsuarioPermissaoService.obter_permissoes_efetivas
    with patch.object(UsuarioPermissaoService, "obter_permissoes_efetivas", autospec=True) as mock_efetivas:
        mock_efetivas.side_effect = original
        resposta = client.get("/usuarios", params={"empresaId": empresa.id})
        assert resposta.status_code == 200
        assert len(resposta.json()) >= total_operadores + 1
        assert mock_efetivas.call_count <= 2, "financeiro.visualizar não pode ser calculado por Usuario da lista"


def test_create_usuario_sem_financeiro_visualizar_response_mascarada(
    db_session: Session, usuario_admin: Usuario, client_admin: TestClient, empresa: Empresa
) -> None:
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")
    sufixo = uuid.uuid4().hex[:8]
    resposta = client_admin.post(
        "/usuarios",
        json={
            "empresaId": empresa.id,
            "nome": f"Usuário {sufixo}",
            "email": f"u-{sufixo}@teste.local",
            "perfilBase": "operador",
            "acessoSistema": True,
            "valorRecebidoMensalCentavos": 400000,
        },
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["valorRecebidoMensalCentavos"] is None


def test_patch_usuario_sem_financeiro_visualizar_response_mascarada(
    db_session: Session, usuario_admin: Usuario, client_admin: TestClient, empresa: Empresa
) -> None:
    alvo = _operador(db_session, empresa, sufixo="usr-patch")
    alvo.valor_recebido_mensal_centavos = 100000
    db_session.flush()
    _override(db_session, usuario=usuario_admin, permissao="financeiro.visualizar", efeito="negar")

    resposta = client_admin.patch(f"/usuarios/{alvo.id}", json={"valorRecebidoMensalCentavos": 250000})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["valorRecebidoMensalCentavos"] is None
