"""@menções de usuários em comentários de Demanda + notificação interna (P1_AGORA_MENTIONS).

Cobre: autocomplete elegível, menção estruturada (id + rótulo no texto), "@" manual não notifica, tenant, status, acesso, autoria (self), 1/3/repetido,
edição (só os novos), remoção sem apagar histórico, re-adição, atomicidade, retry/dedupe, sino/não lidas/marcar lida e timeline limpa."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.demanda_comentario import DemandaComentario
from app.models.demanda_comentario_mencao import DemandaComentarioMencao
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario

TIPO = "demanda.usuarios_mencionados"


def _client_de(app, usuario: Usuario) -> TestClient:
    cliente = TestClient(app)
    cliente.headers["Authorization"] = f"Bearer {create_access_token(sub=usuario.id, empresa_id=usuario.empresa_id, perfil_base=usuario.perfil_base)}"
    return cliente


def _usuario(db: Session, empresa: Empresa, nome: str, *, perfil: str = "operador", status: str = "ativo", acesso: bool = True, sistema: bool = False) -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"m-{sufixo}", nome=nome, email=f"m-{sufixo}@teste.local",
        perfil_base=perfil, acesso_sistema=acesso, status=status, is_system_account=sistema, created_at=agora, updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _demanda(client: TestClient, responsaveis: list[str] | None = None) -> dict:
    resposta = client.post("/demandas", json={"nome": f"Tarefa {uuid.uuid4().hex[:6]}", "usuarioResponsavelIds": responsaveis or []})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _comentar(client: TestClient, demanda_id: str, texto: str, ids: list[str] | None = None):
    corpo: dict = {"texto": texto}
    if ids is not None:
        corpo["mencoesUsuarioIds"] = ids
    return client.post(f"/demandas/{demanda_id}/comentarios", json=corpo)


def _editar(client: TestClient, demanda_id: str, comentario_id: str, texto: str, ids: list[str] | None = None):
    corpo: dict = {"texto": texto}
    if ids is not None:
        corpo["mencoesUsuarioIds"] = ids
    return client.patch(f"/demandas/{demanda_id}/comentarios/{comentario_id}", json=corpo)


def _eventos(db: Session, demanda_id: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.tipo == TIPO, Evento.entidade_id == demanda_id).order_by(Evento.occurred_at, Evento.id)).all())


def _notificacoes(cliente: TestClient) -> list[dict]:
    resposta = cliente.get("/notificacoes?categoria=minhas&limit=100")
    assert resposta.status_code == 200, resposta.text
    return [item for item in resposta.json()["itens"] if item["tipo"] == TIPO]


def _nao_lidas(cliente: TestClient) -> int:
    return cliente.get("/notificacoes/resumo").json()["naoLidas"]["total"]


# ------------------------------------------------------------------ autocomplete


def test_autocomplete_so_traz_elegiveis_da_empresa_com_acesso(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    com_acesso = _usuario(db_session, empresa, "Raquel Elegível")
    _usuario(db_session, empresa, "Raquel Sem Acesso")  # operador que não é responsável: não lê a tarefa
    _usuario(db_session, empresa, "Raquel Suspensa", status="inativo")
    _usuario(db_session, empresa, "Raquel Bloqueada", status="bloqueado")
    _usuario(db_session, empresa, "Raquel Sem Login", acesso=False)
    _usuario(db_session, empresa, "Raquel Sistema", sistema=True)
    _usuario(db_session, outra_empresa, "Raquel De Outro Tenant", perfil="admin")
    demanda = _demanda(client_admin, [com_acesso.id])

    resposta = client_admin.get(f"/demandas/{demanda['id']}/mencionaveis?q=raq")
    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()
    assert [item["nome"] for item in itens if item["nome"].startswith("Raquel")] == ["Raquel Elegível"]
    assert set(itens[0]) <= {"id", "nome", "cargo"}  # sem e-mail/telefone/documento


def test_autocomplete_nao_inclui_o_proprio_usuario_e_filtra_por_nome(app, db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_admin: Usuario) -> None:
    pedro = _usuario(db_session, empresa, "Pedro Alvo", perfil="gestor")
    demanda = _demanda(client_admin)
    todos = client_admin.get(f"/demandas/{demanda['id']}/mencionaveis").json()
    assert usuario_admin.id not in [item["id"] for item in todos]
    assert [item["id"] for item in client_admin.get(f"/demandas/{demanda['id']}/mencionaveis?q=ped").json()] == [pedro.id]
    assert client_admin.get(f"/demandas/{demanda['id']}/mencionaveis?q=zzzz").json() == []


def test_autocomplete_exige_poder_comentar_na_tarefa(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    estranho = _usuario(db_session, empresa, "Estranho Operador")
    demanda = _demanda(client_admin)
    assert _client_de(app, estranho).get(f"/demandas/{demanda['id']}/mencionaveis").status_code == 404


def test_autocomplete_de_outro_tenant_nao_enxerga_a_tarefa(app, db_session: Session, outra_empresa: Empresa, client_admin: TestClient) -> None:
    demanda = _demanda(client_admin)
    forasteiro = _usuario(db_session, outra_empresa, "Forasteiro", perfil="admin")
    assert _client_de(app, forasteiro).get(f"/demandas/{demanda['id']}/mencionaveis").status_code == 404


# ------------------------------------------------------------------ criar


def test_mencao_selecionada_notifica_uma_vez_e_texto_manual_nao(app, db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_admin: Usuario) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    cliente_raquel = _client_de(app, raquel)

    # "@Raquel" digitado à mão (sem id estruturado) NÃO é menção
    assert _comentar(client_admin, demanda["id"], "@Raquel Oliveira olha isso").status_code == 201
    assert _eventos(db_session, demanda["id"]) == []
    assert _notificacoes(cliente_raquel) == []

    antes = _nao_lidas(cliente_raquel)  # já inclui a notificação de atribuição da tarefa
    resposta = _comentar(client_admin, demanda["id"], "@Raquel Oliveira revisar arte", [raquel.id])
    assert resposta.status_code == 201, resposta.text
    assert [m["usuarioId"] for m in resposta.json()["mencoes"]] == [raquel.id]
    assert [m["nome"] for m in resposta.json()["mencoes"]] == ["Raquel Oliveira"]

    notificacoes = _notificacoes(cliente_raquel)
    assert len(notificacoes) == 1
    item = notificacoes[0]
    assert item["titulo"] == "Você foi mencionado em um comentário"
    assert item["detalhe"] == "@Raquel Oliveira revisar arte"
    assert item["demandaId"] == demanda["id"]
    assert item["lida"] is False
    assert item["autorNome"] == usuario_admin.nome
    assert _nao_lidas(cliente_raquel) == antes + 1
    assert _notificacoes(client_admin) == []  # quem mencionou não é notificado


def test_tres_usuarios_tres_notificacoes_e_repetido_vale_um(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro, ana = (_usuario(db_session, empresa, nome) for nome in ("Raquel Oliveira", "Pedro Silva", "Ana Costa"))
    demanda = _demanda(client_admin, [raquel.id, pedro.id, ana.id])
    texto = "@Raquel Oliveira @Pedro Silva @Ana Costa e de novo @Raquel Oliveira"
    assert _comentar(client_admin, demanda["id"], texto, [raquel.id, pedro.id, ana.id, raquel.id]).status_code == 201

    assert len(_eventos(db_session, demanda["id"])) == 1  # UM evento por ação, não um por pessoa
    for pessoa in (raquel, pedro, ana):
        assert len(_notificacoes(_client_de(app, pessoa))) == 1
    linhas = db_session.scalar(select(func.count()).select_from(DemandaComentarioMencao)) or 0
    assert linhas == 3


def test_auto_mencao_fica_no_texto_e_nao_notifica(app, db_session: Session, empresa: Empresa, client_admin: TestClient, usuario_admin: Usuario) -> None:
    demanda = _demanda(client_admin)
    resposta = _comentar(client_admin, demanda["id"], f"Lembrete para @{usuario_admin.nome}", [usuario_admin.id])
    assert resposta.status_code == 201, resposta.text
    assert [m["usuarioId"] for m in resposta.json()["mencoes"]] == [usuario_admin.id]
    assert _eventos(db_session, demanda["id"]) == []
    assert _notificacoes(client_admin) == []


def test_mencao_invalida_recusa_o_comentario_inteiro_sem_notificar(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    valido = _usuario(db_session, empresa, "Valida Pessoa")
    outro_tenant = _usuario(db_session, outra_empresa, "Intruso Tenant", perfil="admin")
    inativo = _usuario(db_session, empresa, "Inativo Pessoa", status="inativo")
    sem_acesso = _usuario(db_session, empresa, "Sem Acesso Pessoa")  # operador que não é responsável
    sistema = _usuario(db_session, empresa, "Conta Sistema", sistema=True)
    demanda = _demanda(client_admin, [valido.id])

    for alvo in (outro_tenant, inativo, sem_acesso, sistema):
        resposta = _comentar(client_admin, demanda["id"], f"@Valida Pessoa e @{alvo.nome}", [valido.id, alvo.id])
        assert resposta.status_code == 422, (alvo.nome, resposta.text)
    # atomicidade: nada foi gravado — nem comentário, nem menção, nem evento, nem notificação
    assert client_admin.get(f"/demandas/{demanda['id']}/comentarios").json() == []
    assert _eventos(db_session, demanda["id"]) == []
    assert _notificacoes(_client_de(app, valido)) == []
    assert (db_session.scalar(select(func.count()).select_from(DemandaComentarioMencao)) or 0) == 0


def test_id_sem_o_rotulo_no_texto_e_recusado(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    assert _comentar(client_admin, demanda["id"], "Texto sem menção nenhuma", [raquel.id]).status_code == 422
    assert _notificacoes(_client_de(app, raquel)) == []


def test_ids_inexistentes_e_excesso_sao_recusados(client_admin: TestClient) -> None:
    demanda = _demanda(client_admin)
    assert _comentar(client_admin, demanda["id"], "@Fantasma", [str(uuid.uuid4())]).status_code == 422
    assert _comentar(client_admin, demanda["id"], "@x", [str(uuid.uuid4()) for _ in range(51)]).status_code == 422


def test_responsavel_nao_mencionado_nao_recebe_a_notificacao_de_mencao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro = _usuario(db_session, empresa, "Raquel Oliveira"), _usuario(db_session, empresa, "Pedro Silva")
    demanda = _demanda(client_admin, [raquel.id, pedro.id])
    _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id])
    assert len(_notificacoes(_client_de(app, raquel))) == 1
    assert _notificacoes(_client_de(app, pedro)) == []  # responsável pela tarefa, mas não mencionado


def test_previa_na_notificacao_e_curta(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    _comentar(client_admin, demanda["id"], "@Raquel Oliveira " + "texto longo " * 100, [raquel.id])
    detalhe = _notificacoes(_client_de(app, raquel))[0]["detalhe"]
    assert len(detalhe) <= 140 and detalhe.endswith("…")


# ------------------------------------------------------------------ editar


def test_edicao_notifica_so_quem_e_novo(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro = _usuario(db_session, empresa, "Raquel Oliveira"), _usuario(db_session, empresa, "Pedro Silva")
    demanda = _demanda(client_admin, [raquel.id, pedro.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira revisar arte", [raquel.id]).json()
    cliente_raquel, cliente_pedro = _client_de(app, raquel), _client_de(app, pedro)
    assert len(_notificacoes(cliente_raquel)) == 1

    # mesma pessoa, texto novo → 0 notificações novas
    assert _editar(client_admin, demanda["id"], comentario["id"], "@Raquel Oliveira revisar arte hoje", [raquel.id]).status_code == 200
    assert len(_notificacoes(cliente_raquel)) == 1 and len(_eventos(db_session, demanda["id"])) == 1

    # pessoa nova → só ela recebe
    resposta = _editar(client_admin, demanda["id"], comentario["id"], "@Raquel Oliveira @Pedro Silva revisar arte hoje", [raquel.id, pedro.id])
    assert resposta.status_code == 200, resposta.text
    assert {m["usuarioId"] for m in resposta.json()["mencoes"]} == {raquel.id, pedro.id}
    assert len(_notificacoes(cliente_raquel)) == 1
    assert len(_notificacoes(cliente_pedro)) == 1
    assert len(_eventos(db_session, demanda["id"])) == 2


def test_reenvio_identico_da_edicao_nao_duplica(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro = _usuario(db_session, empresa, "Raquel Oliveira"), _usuario(db_session, empresa, "Pedro Silva")
    demanda = _demanda(client_admin, [raquel.id, pedro.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira ok", [raquel.id]).json()
    corpo = ("@Raquel Oliveira @Pedro Silva ok", [raquel.id, pedro.id])
    for _ in range(3):  # retry HTTP / duplo envio
        assert _editar(client_admin, demanda["id"], comentario["id"], *corpo).status_code == 200
    assert len(_notificacoes(_client_de(app, pedro))) == 1
    assert len(_eventos(db_session, demanda["id"])) == 2


def test_remover_mencao_apaga_o_estado_mas_preserva_a_notificacao_e_readicionar_notifica_de_novo(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id]).json()
    cliente_raquel = _client_de(app, raquel)

    resposta = _editar(client_admin, demanda["id"], comentario["id"], "ver sem ninguém", [])
    assert resposta.status_code == 200 and resposta.json()["mencoes"] == []
    assert (db_session.scalar(select(func.count()).select_from(DemandaComentarioMencao)) or 0) == 0
    assert len(_notificacoes(cliente_raquel)) == 1  # a notificação já entregue é histórico

    assert _editar(client_admin, demanda["id"], comentario["id"], "@Raquel Oliveira de volta", [raquel.id]).status_code == 200
    assert len(_notificacoes(cliente_raquel)) == 2  # menção NOVA e explícita → nova notificação


def test_rotulo_removido_do_texto_com_id_remanescente_apaga_a_mencao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id]).json()
    resposta = _editar(client_admin, demanda["id"], comentario["id"], "ver", [raquel.id])
    assert resposta.status_code == 200 and resposta.json()["mencoes"] == []


def test_edicao_sem_o_campo_nao_mexe_nas_mencoes(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id]).json()
    resposta = _editar(client_admin, demanda["id"], comentario["id"], "@Raquel Oliveira ver melhor")
    assert resposta.status_code == 200
    assert [m["usuarioId"] for m in resposta.json()["mencoes"]] == [raquel.id]
    assert len(_eventos(db_session, demanda["id"])) == 1


def test_mencao_antiga_nao_e_revalidada_se_a_pessoa_foi_inativada(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro = _usuario(db_session, empresa, "Raquel Oliveira"), _usuario(db_session, empresa, "Pedro Silva")
    demanda = _demanda(client_admin, [raquel.id, pedro.id])
    comentario = _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id]).json()
    raquel.status = "inativo"
    db_session.flush()
    resposta = _editar(client_admin, demanda["id"], comentario["id"], "@Raquel Oliveira @Pedro Silva ver", [raquel.id, pedro.id])
    assert resposta.status_code == 200, resposta.text  # só os NOVOS são validados
    assert len(_notificacoes(_client_de(app, pedro))) == 1


def test_edicao_com_pessoa_nova_invalida_e_recusada_sem_efeitos(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    intruso = _usuario(db_session, outra_empresa, "Intruso Tenant", perfil="admin")
    demanda = _demanda(client_admin, [raquel.id])
    comentario = _comentar(client_admin, demanda["id"], "oi", []).json()
    resposta = _editar(client_admin, demanda["id"], comentario["id"], "oi @Intruso Tenant", [intruso.id])
    assert resposta.status_code == 422
    atual = client_admin.get(f"/demandas/{demanda['id']}/comentarios").json()[0]
    assert atual["texto"] == "oi" and atual["mencoes"] == []  # o texto novo também não persistiu
    assert _eventos(db_session, demanda["id"]) == []


# ------------------------------------------------------------------ sino / leitura / timeline / exclusão


def test_marcar_lida_e_nao_lidas_funcionam_com_a_infra_existente(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id])
    cliente_raquel = _client_de(app, raquel)
    antes = _nao_lidas(cliente_raquel)
    notificacao = _notificacoes(cliente_raquel)[0]
    assert cliente_raquel.post(f"/notificacoes/{notificacao['id']}/lida").status_code in (200, 204)
    assert _nao_lidas(cliente_raquel) == antes - 1
    assert _notificacoes(cliente_raquel)[0]["lida"] is True


def test_notificacao_de_mencao_nao_e_de_outro_usuario_nem_de_outro_tenant(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, client_admin: TestClient) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id])
    notificacao = _notificacoes(_client_de(app, raquel))[0]
    forasteiro = _client_de(app, _usuario(db_session, outra_empresa, "Forasteiro", perfil="admin"))
    assert forasteiro.post(f"/notificacoes/{notificacao['id']}/lida").status_code == 404
    assert _notificacoes(forasteiro) == []


def test_evento_de_mencao_nao_aparece_na_timeline(client_admin: TestClient, app, db_session: Session, empresa: Empresa) -> None:
    raquel = _usuario(db_session, empresa, "Raquel Oliveira")
    demanda = _demanda(client_admin, [raquel.id])
    _comentar(client_admin, demanda["id"], "@Raquel Oliveira ver", [raquel.id])
    historico = client_admin.get(f"/demandas/{demanda['id']}/historico")
    assert historico.status_code == 200, historico.text
    tipos = [evento["tipo"] for evento in historico.json()]
    assert "demanda.comentario_criado" in tipos and TIPO not in tipos


def test_listagem_traz_as_mencoes_e_excluir_comentario_limpa_as_linhas(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    raquel, pedro = _usuario(db_session, empresa, "Raquel Oliveira"), _usuario(db_session, empresa, "Pedro Silva")
    demanda = _demanda(client_admin, [raquel.id, pedro.id])
    primeiro = _comentar(client_admin, demanda["id"], "@Raquel Oliveira @Pedro Silva ver", [raquel.id, pedro.id]).json()
    _comentar(client_admin, demanda["id"], "sem menção")
    lista = client_admin.get(f"/demandas/{demanda['id']}/comentarios").json()
    por_id = {item["id"]: item for item in lista}
    assert {m["nome"] for m in por_id[primeiro["id"]]["mencoes"]} == {"Raquel Oliveira", "Pedro Silva"}
    assert [item["mencoes"] for item in lista if item["id"] != primeiro["id"]] == [[]]

    assert client_admin.delete(f"/demandas/{demanda['id']}/comentarios/{primeiro['id']}").status_code == 204
    db_session.expire_all()
    assert db_session.get(DemandaComentario, primeiro["id"]) is None
    assert (db_session.scalar(select(func.count()).select_from(DemandaComentarioMencao)) or 0) == 0


def test_comentario_sem_mencoes_continua_igual(client_admin: TestClient) -> None:
    demanda = _demanda(client_admin)
    resposta = _comentar(client_admin, demanda["id"], "comentário comum")
    assert resposta.status_code == 201 and resposta.json()["mencoes"] == []
