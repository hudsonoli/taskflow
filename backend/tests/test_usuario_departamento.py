"""D3-A — Usuário passa a usar Departamento por UUID.

O contrato público mantém o nome `departamentoId`, mas ele agora significa o id técnico de
Departamento, não mais o nome em texto livre.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa


def _departamento(db: Session, empresa: Empresa, nome: str | None = None, status: str = "ativo") -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome or f"Depto {sufixo}",
        nome_normalizado=f"depto-{sufixo}",
        cor_identificacao="blue",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _payload_usuario(empresa: Empresa, **extra) -> dict:
    sufixo = uuid.uuid4().hex[:8]
    return {
        "empresaId": empresa.id,
        "codigoInterno": f"u-{sufixo}",
        "nome": f"Usuário {sufixo}",
        "email": f"u-{sufixo}@teste.local",
        "perfilBase": "operador",
        "acessoSistema": True,
        **extra,
    }


# --------------------------------------------------------------------------------------

def test_criar_usuario_com_departamento_uuid(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    resposta = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id)
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["departamentoId"] == departamento.id


def test_usuario_read_devolve_uuid_ou_null(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    departamento = _departamento(db_session, empresa)
    com = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id)).json()
    sem = client_admin.post("/usuarios", json=_payload_usuario(empresa)).json()

    assert com["departamentoId"] == departamento.id
    uuid.UUID(com["departamentoId"])  # é UUID válido
    assert sem["departamentoId"] is None


def test_nome_textual_e_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    """O que antes era aceito (nome livre) agora é 422 — não há fallback silencioso."""
    resposta = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId="Criação"))
    assert resposta.status_code == 422, resposta.text


def test_nome_textual_e_rejeitado_no_patch(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O PATCH recebe dict cru e só depois valida — precisa recusar o nome do mesmo jeito."""
    departamento = _departamento(db_session, empresa)
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id)
    ).json()

    resposta = client_admin.patch(f"/usuarios/{criado['id']}", json={"departamentoId": "Criação"})
    assert resposta.status_code == 422, resposta.text

    # E o vínculo anterior permanece intacto — recusa não pode corromper o que já existia.
    assert client_admin.get(f"/usuarios/{criado['id']}").json()["departamentoId"] == departamento.id


def test_patch_com_payload_invalido_nunca_devolve_500(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Correção incidental achada pela D3-A.

    O PATCH recebe `dict` cru e valida à mão, então o ValidationError do Pydantic não passa
    pelo tratamento automático do FastAPI — escapava como 500. Qualquer entrada inválida
    tem de virar 422, o status que o projeto já usa para falha de schema. O contrato de
    sucesso não muda: só o caminho de erro foi corrigido.
    """
    departamento = _departamento(db_session, empresa)
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id)
    ).json()

    payloads_invalidos = [
        {"departamentoId": "Criação"},          # nome textual
        {"departamentoId": "nao-e-uuid"},       # string qualquer
        {"departamentoId": 123},                # tipo errado
        {"perfilBase": "inexistente"},          # enum inválido (fora de Departamento)
        {"liderDepartamento": "talvez"},        # bool inválido
    ]
    for payload in payloads_invalidos:
        resposta = client_admin.patch(f"/usuarios/{criado['id']}", json=payload)
        assert resposta.status_code == 422, f"{payload} -> {resposta.status_code}: {resposta.text}"

    # Nenhuma das recusas pode ter alterado o registro.
    atual = client_admin.get(f"/usuarios/{criado['id']}").json()
    assert atual["departamentoId"] == departamento.id
    assert atual["perfilBase"] == "operador"


def test_patch_valido_continua_200(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Contra-prova da correção acima: o caminho de sucesso segue idêntico."""
    departamento = _departamento(db_session, empresa)
    criado = client_admin.post("/usuarios", json=_payload_usuario(empresa)).json()

    resposta = client_admin.patch(
        f"/usuarios/{criado['id']}", json={"nome": "Nome Novo", "departamentoId": departamento.id}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"] == "Nome Novo"
    assert resposta.json()["departamentoId"] == departamento.id


def test_departamento_inexistente_rejeitado(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=str(uuid.uuid4()))
    )
    assert resposta.status_code == 422, resposta.text


def test_departamento_de_outra_empresa_rejeitado(
    client_admin: TestClient, db_session: Session, outra_empresa: Empresa, empresa: Empresa
) -> None:
    alheio = _departamento(db_session, outra_empresa)
    resposta = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=alheio.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_arquivado_rejeitado_em_novo_vinculo(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    arquivado = _departamento(db_session, empresa, status="arquivado")
    resposta = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=arquivado.id))
    assert resposta.status_code == 422, resposta.text


def test_departamento_nulo_continua_permitido(client_admin: TestClient, empresa: Empresa) -> None:
    resposta = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=None))
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["departamentoId"] is None


def test_editar_departamento_do_usuario(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    inicial = _departamento(db_session, empresa)
    novo = _departamento(db_session, empresa)
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=inicial.id)
    ).json()

    resposta = client_admin.patch(f"/usuarios/{criado['id']}", json={"departamentoId": novo.id})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["departamentoId"] == novo.id


def test_editar_para_departamento_arquivado_rejeitado(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    inicial = _departamento(db_session, empresa)
    arquivado = _departamento(db_session, empresa, status="arquivado")
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=inicial.id)
    ).json()

    resposta = client_admin.patch(f"/usuarios/{criado['id']}", json={"departamentoId": arquivado.id})
    assert resposta.status_code == 422, resposta.text


def test_diretorio_devolve_uuid(client_admin: TestClient, db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id)
    ).json()

    diretorio = client_admin.get("/usuarios/diretorio")
    assert diretorio.status_code == 200, diretorio.text
    item = next(u for u in diretorio.json() if u["id"] == criado["id"])
    assert item["departamentoId"] == departamento.id
    uuid.UUID(item["departamentoId"])


def test_filtro_por_departamento_usa_uuid(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """O filtro `departamentoId` vive em /usuarios/diretorio e agora casa por UUID."""
    alvo = _departamento(db_session, empresa)
    outro = _departamento(db_session, empresa)
    dentro = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=alvo.id)).json()
    fora = client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=outro.id)).json()

    resposta = client_admin.get("/usuarios/diretorio", params={"departamentoId": alvo.id})
    assert resposta.status_code == 200, resposta.text
    ids = [u["id"] for u in resposta.json()]
    assert dentro["id"] in ids
    assert fora["id"] not in ids


def test_filtro_por_nome_textual_nao_retorna_ninguem(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Sem fallback: filtrar pelo NOME do departamento não pode mais casar com ninguém."""
    departamento = _departamento(db_session, empresa, nome="Criação")
    client_admin.post("/usuarios", json=_payload_usuario(empresa, departamentoId=departamento.id))

    resposta = client_admin.get("/usuarios/diretorio", params={"departamentoId": "Criação"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == []


def test_schema_final_tem_uma_unica_coluna(db_session: Session) -> None:
    """D3-B: sobrou UMA representação. `departamento_uuid` e a coluna textual não existem."""
    colunas = {
        linha[0]: (linha[1], linha[2])
        for linha in db_session.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'usuarios' AND column_name LIKE 'departamento%'"
            )
        ).all()
    }
    assert set(colunas) == {"departamento_id"}, f"colunas inesperadas: {sorted(colunas)}"
    assert colunas["departamento_id"] == ("character varying", 36)


def test_fk_e_indice_finais(db_session: Session) -> None:
    """Renomear coluna no Postgres não renomeia FK nem índice — a migration fez isso à mão."""
    fk = db_session.execute(
        text(
            "SELECT con.conname, pg_get_constraintdef(con.oid) FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "WHERE rel.relname = 'usuarios' AND con.contype = 'f' "
            "AND pg_get_constraintdef(con.oid) ILIKE '%departamentos(id)%'"
        )
    ).one()
    assert fk[0] == "fk_usuarios_departamento_id"
    assert "departamento_id" in fk[1]
    assert "ON DELETE SET NULL" in fk[1]

    indices = [
        linha[0]
        for linha in db_session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename='usuarios' AND indexdef ILIKE '%departamento%'")
        ).all()
    ]
    assert indices == ["ix_usuarios_departamento_id"], indices

    nullable = db_session.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='usuarios' AND column_name='departamento_id'"
        )
    ).scalar_one()
    assert nullable == "YES", "usuário sem departamento continua legítimo"


def test_ciclo_completo_de_escrita(
    client_admin: TestClient, db_session: Session, empresa: Empresa
) -> None:
    """Criar -> ler -> editar -> ler -> anular -> ler, conferindo o banco em cada estágio."""
    primeiro = _departamento(db_session, empresa)
    segundo = _departamento(db_session, empresa)

    def estado_no_banco(usuario_id: str) -> tuple[None, str | None]:
        db_session.expire_all()
        atual = db_session.execute(
            text("SELECT departamento_id FROM usuarios WHERE id = :i"), {"i": usuario_id}
        ).scalar_one()
        return None, atual

    # 1. criar com UUID
    criado = client_admin.post(
        "/usuarios", json=_payload_usuario(empresa, departamentoId=primeiro.id)
    )
    assert criado.status_code == 201, criado.text
    usuario_id = criado.json()["id"]
    assert criado.json()["departamentoId"] == primeiro.id
    assert estado_no_banco(usuario_id)[1] == primeiro.id

    # 2. consultar e confirmar o mesmo UUID
    lido = client_admin.get(f"/usuarios/{usuario_id}")
    assert lido.status_code == 200, lido.text
    assert lido.json()["departamentoId"] == primeiro.id

    # 3. editar para outro UUID
    editado = client_admin.patch(f"/usuarios/{usuario_id}", json={"departamentoId": segundo.id})
    assert editado.status_code == 200, editado.text
    assert editado.json()["departamentoId"] == segundo.id
    assert estado_no_banco(usuario_id)[1] == segundo.id

    # 4. consultar e confirmar
    assert client_admin.get(f"/usuarios/{usuario_id}").json()["departamentoId"] == segundo.id

    # 5. anular
    anulado = client_admin.patch(f"/usuarios/{usuario_id}", json={"departamentoId": None})
    assert anulado.status_code == 200, anulado.text
    assert anulado.json()["departamentoId"] is None
    assert estado_no_banco(usuario_id)[1] is None

    # 6. consultar e confirmar null
    assert client_admin.get(f"/usuarios/{usuario_id}").json()["departamentoId"] is None


def test_seed_resolve_nome_legado_para_uuid(db_session: Session, empresa: Empresa) -> None:
    """O seed resolve o nome do JSON para UUID ANTES de persistir — nunca grava texto.

    Também confere que a normalização em Python é a mesma da migration D2 em SQL: se as
    duas divergirem, o seed passaria a criar vínculos diferentes do backfill.
    """
    from app.cli.seed_usuarios import _normalizar_nome_departamento

    nomes = ["Criação", "Conteúdo", "Diretoria", "Atendimento", "Mídia", "Orçamento/Produção"]
    criados = {nome: _departamento(db_session, empresa, nome).id for nome in nomes}

    # Mesmo índice que o seed monta a partir dos departamentos existentes.
    indice = {_normalizar_nome_departamento(nome): departamento_id for nome, departamento_id in criados.items()}

    for nome, esperado in criados.items():
        # O JSON de seed traz o nome com acento e capitalização originais.
        assert indice[_normalizar_nome_departamento(nome)] == esperado
        uuid.UUID(esperado)

        # E a normalização SQL da migration D2 produz exatamente a mesma chave.
        em_sql = db_session.execute(
            text(
                "SELECT lower(translate(btrim(:n), "
                "'áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ', "
                "'aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN'))"
            ),
            {"n": nome},
        ).scalar_one()
        assert em_sql == _normalizar_nome_departamento(nome), f"divergência de normalização em {nome!r}"
