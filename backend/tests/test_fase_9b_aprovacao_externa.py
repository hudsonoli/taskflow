"""Fase 9B — Portal Externo de Aprovação (MVP): link-capability, sem usuário externo.

Provas: criação do link (autoridade própria, só a etapa de aprovação ATUAL, snapshot + SHA-256 dos artefatos, token só como hash); portal público
(superfície mínima, estados indistinguíveis, artefato conferido pelo hash, PDF nunca inline); decisão externa REUSANDO o workflow (aprovar avança,
ajustes devolvem), com ator externo explícito (sem `Usuario` fictício, sem e-mail em evento), notificações com o nome declarado, timeline sem duplicar;
revogação; proteção dos arquivos referenciados (individual e em lote); e concorrência REAL (sessões separadas, locks do Postgres).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.main  # noqa: F401  (registra TODOS os models: os testes de concorrência usam só `test_engine`, sem a fixture `app`)
import app.services.demanda_arquivo_service as arquivo_modulo
from app.core.security import create_platform_token
from app.models.aprovacao_externa import AprovacaoExterna, AprovacaoExternaArquivo
from app.models.demanda import Demanda
from app.models.demanda_arquivo import DemandaArquivo
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.usuario import Usuario
from tests.test_d1_criacao_demandas import _atendimento, _client_para, _operador_comum
from tests.test_demanda import _departamento
from tests.test_fase_8a_workflow_progressao import _demanda_com_workflow, _etapa, _por_ordem, _url
from tests.test_gerenciador_arquivos import PDF_VALIDO, PNG_VALIDO, _cliente, _link, _upload

PUBLICO = "/publico/aprovacoes"
APROVADA = "demanda.workflow_etapa_aprovada"
REJEITADA = "demanda.workflow_etapa_rejeitada"
ATUALIZADA = "demanda.workflow_etapa_atualizada"
EXT_CRIADA = "demanda.aprovacao_externa_criada"
EXT_APROVADA = "demanda.aprovacao_externa_aprovada"
EXT_AJUSTES = "demanda.aprovacao_externa_ajustes"
EXT_REVOGADA = "demanda.aprovacao_externa_revogada"
NOME = "Maria Cliente"
EMAIL = "Maria.Cliente@Exemplo.com"
EMAIL_NORMALIZADO = "maria.cliente@exemplo.com"
INDISPONIVEL = "Este link de aprovação não está mais disponível."


# ======================================================================================
# helpers
# ======================================================================================


def _op(db: Session, empresa: Empresa, nome: str) -> Usuario:
    return _operador_comum(db, empresa, sufixo=f"9b-{nome}-{uuid.uuid4().hex[:4]}")


def _eventos(db: Session, demanda_id: str, tipo: str | None = None) -> list[Evento]:
    db.expire_all()
    consulta = select(Evento).where(Evento.entidade_tipo == "demanda", Evento.entidade_id == demanda_id)
    if tipo:
        consulta = consulta.where(Evento.tipo == tipo)
    return list(db.scalars(consulta.order_by(Evento.occurred_at.asc(), Evento.id.asc())).all())


def _estado(client: TestClient, demanda_id: str) -> dict:
    resposta = client.get(f"/demandas/{demanda_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _por_id(demanda: dict) -> dict[str, dict]:
    return {e["id"]: e for e in demanda["workflowEtapas"]}


def _rota(demanda_id: str, etapa_id: str, sufixo: str = "") -> str:
    return f"/demandas/{demanda_id}/workflow/etapas/{etapa_id}/aprovacao-externa{sufixo}"


def _subir(client: TestClient, demanda_id: str, *, nome: str = "arte.png", tipo: str = "layout") -> str:
    if nome.endswith(".pdf"):
        resposta = _upload(client, demanda_id, nome=nome, conteudo=PDF_VALIDO + uuid.uuid4().bytes, content_type="application/pdf", tipo=tipo)
    else:
        resposta = _upload(client, demanda_id, nome=nome, conteudo=PNG_VALIDO + uuid.uuid4().bytes, content_type="image/png", tipo=tipo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


class Cenario:
    """1 Criação (a) → 2 Aprovação (b) → 3 Publicação (c), com a Criação já concluída (a Aprovação é a atual) e dois layouts (PNG + PDF)."""

    def __init__(self, app, db: Session, empresa: Empresa, client_admin: TestClient, **extra) -> None:
        self.app, self.db, self.empresa, self.admin = app, db, empresa, client_admin
        self.a, self.b, self.c = _op(db, empresa, "a"), _op(db, empresa, "b"), _op(db, empresa, "c")
        self.demanda = _demanda_com_workflow(
            client_admin,
            [_etapa("Criação", usuarios=[self.a.id]), _etapa("Aprovação", "aprovacao", usuarios=[self.b.id]), _etapa("Publicação", usuarios=[self.c.id])],
            **extra,
        )
        self.id = self.demanda["id"]
        self.e1, self.e2, self.e3 = _por_ordem(self.demanda)
        db.commit()
        self.ca, self.cb, self.cc = _client_para(app, self.a), _client_para(app, self.b), _client_para(app, self.c)
        assert self.ca.post(_url(self.id, self.e1["id"], "concluir")).status_code == 200
        self.png = _subir(client_admin, self.id, nome="arte.png")
        self.pdf = _subir(client_admin, self.id, nome="proposta.pdf")
        db.commit()
        self.pub = TestClient(app)

    def criar(self, client: TestClient | None = None, arquivos: list[str] | None = None, **extra):
        corpo = {"arquivoIds": arquivos if arquivos is not None else [self.png, self.pdf], **extra}
        return (client or self.cb).post(_rota(self.id, self.e2["id"]), json=corpo)

    def link(self, **extra) -> tuple[str, dict]:
        resposta = self.criar(**extra)
        assert resposta.status_code == 201, resposta.text
        self.db.commit()
        corpo = resposta.json()
        return corpo["token"], corpo

    def consultar(self, token: str, client: TestClient | None = None):
        return (client or self.pub).post(f"{PUBLICO}/consultar", json={"token": token})

    def decidir(self, token: str, decisao: str = "aprovar", *, nome: str = NOME, email: str | None = EMAIL, motivo: str | None = None, **extra):
        corpo = {"token": token, "decisao": decisao, "nome": nome, "email": email, "motivo": motivo, **extra}
        return self.pub.post(f"{PUBLICO}/decisao", json=corpo)

    def artefato(self, token: str, ordem: int):
        return self.pub.post(f"{PUBLICO}/artefato", json={"token": token, "ordem": ordem})

    def aprovacao(self, token: str | None = None) -> AprovacaoExterna:
        self.db.expire_all()
        consulta = select(AprovacaoExterna).where(AprovacaoExterna.demanda_id == self.id)
        if token is not None:
            consulta = consulta.where(AprovacaoExterna.token_hash == hashlib.sha256(token.encode()).hexdigest())
        return self.db.scalars(consulta.order_by(AprovacaoExterna.criada_em.desc())).first()


@pytest.fixture()
def cen(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> Cenario:
    return Cenario(app, db_session, empresa, client_admin)


# ======================================================================================
# criação do link
# ======================================================================================


def test_criar_link_gera_token_forte_guarda_so_o_hash_e_snapshot_dos_artefatos(cen: Cenario) -> None:
    resposta = cen.criar(instrucao="Aprovar a arte final", destinatarioNome="Maria", destinatarioEmail="MARIA@Cliente.com", validadeDias=5)
    assert resposta.status_code == 201, resposta.text
    assert resposta.headers["cache-control"] == "no-store"
    corpo = resposta.json()
    token = corpo["token"]
    assert len(token) == 43 and all(c.isalnum() or c in "-_" for c in token)  # token_urlsafe(32) = 256 bits
    assert corpo["estado"] == "pendente" and corpo["instrucao"] == "Aprovar a arte final"
    assert corpo["destinatarioNome"] == "Maria" and corpo["destinatarioEmail"] == "maria@cliente.com"
    assert [(a["ordem"], a["nome"], a["contentType"]) for a in corpo["artefatos"]] == [(1, "arte.png", "image/png"), (2, "proposta.pdf", "application/pdf")]
    assert corpo["criadaPorNome"] == cen.b.nome

    ap = cen.aprovacao()
    assert ap.token_hash == hashlib.sha256(token.encode()).hexdigest() and ap.criada_por_usuario_id == cen.b.id
    assert ap.empresa_id == cen.empresa.id and ap.demanda_id == cen.id and ap.workflow_etapa_id == cen.e2["id"]
    assert timedelta(days=4, hours=23) < ap.expira_em - ap.criada_em <= timedelta(days=5, seconds=5)
    # o token em claro não está em NENHUMA coluna das duas tabelas nem em nenhum payload de evento
    cen.db.expire_all()
    for linha in cen.db.execute(select(AprovacaoExterna)).scalars():
        assert token not in json.dumps({c.name: str(getattr(linha, c.name)) for c in AprovacaoExterna.__table__.columns})
    for linha in cen.db.execute(select(AprovacaoExternaArquivo)).scalars():
        assert token not in json.dumps({c.name: str(getattr(linha, c.name)) for c in AprovacaoExternaArquivo.__table__.columns})
    for evento in _eventos(cen.db, cen.id):
        assert token not in json.dumps(evento.payload) and ap.token_hash not in json.dumps(evento.payload)
    # snapshot: SHA-256 do que estava em disco
    artefatos = {a.ordem: a for a in cen.db.scalars(select(AprovacaoExternaArquivo).where(AprovacaoExternaArquivo.aprovacao_externa_id == ap.id))}
    arquivo = cen.db.get(DemandaArquivo, cen.png)
    esperado = hashlib.sha256((arquivo_modulo.UPLOADS_ROOT / "demandas" / cen.id / arquivo.nome_fisico).read_bytes()).hexdigest()
    assert artefatos[1].sha256 == esperado and artefatos[1].arquivo_id == cen.png and artefatos[1].tamanho_bytes == arquivo.tamanho_bytes
    (criada,) = _eventos(cen.db, cen.id, EXT_CRIADA)
    assert criada.usuario_id == cen.b.id and criada.payload["aprovacaoExternaId"] == ap.id and criada.payload["quantidadeArtefatos"] == 2


def test_nao_ha_ip_user_agent_nem_geolocalizacao_no_modelo(cen: Cenario) -> None:
    colunas = {c.name for c in AprovacaoExterna.__table__.columns}
    assert not {nome for nome in colunas if any(x in nome for x in ("ip", "user_agent", "agente", "geo", "dispositivo"))} - {"instrucao", "descricao"}
    assert "ip_decisao" not in colunas


def test_validade_padrao_sete_dias_e_limites(cen: Cenario) -> None:
    token, corpo = cen.link()
    ap = cen.aprovacao(token)
    assert timedelta(days=6, hours=23) < ap.expira_em - ap.criada_em <= timedelta(days=7, seconds=5)
    for invalido in (0, -1, 31, 365):
        assert cen.criar(validadeDias=invalido).status_code == 422
    assert cen.criar(validadeDias=30).status_code == 201
    assert cen.criar(validadeDias=1).status_code == 201


def test_entradas_invalidas_422(cen: Cenario) -> None:
    assert cen.criar(arquivos=[]).status_code == 422  # ao menos um
    assert cen.criar(arquivos=[cen.png, cen.png]).status_code == 422  # repetido
    assert cen.criar(arquivos=[str(uuid.uuid4())]).status_code == 422  # inexistente
    assert cen.criar(arquivos=["nao-e-uuid"]).status_code == 422
    assert cen.criar(instrucao="<script>alert(1)</script>").status_code == 422
    assert cen.criar(instrucao="x" * 1001).status_code == 422
    assert cen.criar(destinatarioEmail="sem-arroba").status_code == 422
    assert cen.criar(token="x").status_code == 422  # extra proibido
    assert cen.criar(statusLayout="aprovado").status_code == 422
    onze = [_subir(cen.admin, cen.id, nome=f"a{i}.png") for i in range(11)]
    cen.db.commit()
    assert cen.criar(arquivos=onze).status_code == 422  # > 10
    assert cen.criar(arquivos=onze[:10]).status_code == 201  # exatamente 10
    assert cen.aprovacao() is not None


def test_so_layout_ou_anexo_fisico_e_nunca_link_nem_arquivo_de_outra_demanda(cen: Cenario, db_session: Session) -> None:
    link = _link(cen.admin, cen.id)
    assert link.status_code == 201
    anexo = _subir(cen.admin, cen.id, nome="anexo.png", tipo="anexo")
    outra = _demanda_com_workflow(cen.admin, [_etapa("X")])
    alheio = _subir(cen.admin, outra["id"], nome="alheio.png")
    db_session.commit()
    assert cen.criar(arquivos=[link.json()["id"]]).status_code == 422
    assert cen.criar(arquivos=[cen.png, alheio]).status_code == 422
    assert cen.criar(arquivos=[anexo]).status_code == 201  # anexo físico é elegível
    assert db_session.scalar(select(func.count()).select_from(AprovacaoExterna).where(AprovacaoExterna.demanda_id == outra["id"])) == 0


def test_arquivo_sem_conteudo_fisico_ou_adulterado_e_recusado(cen: Cenario, db_session: Session) -> None:
    arquivo = db_session.get(DemandaArquivo, cen.png)
    caminho = arquivo_modulo.UPLOADS_ROOT / "demandas" / cen.id / arquivo.nome_fisico
    original = caminho.read_bytes()
    caminho.write_bytes(b"<html>nao sou png</html>")  # conteúdo não bate com a assinatura da extensão
    assert cen.criar(arquivos=[cen.png]).status_code == 422
    caminho.unlink()  # metadado sem arquivo físico
    assert cen.criar(arquivos=[cen.png]).status_code == 422
    caminho.write_bytes(original)
    assert cen.criar(arquivos=[cen.png]).status_code == 201


def test_total_acima_de_100_mib_e_recusado(cen: Cenario, monkeypatch) -> None:
    import app.services.aprovacao_externa_service as servico

    monkeypatch.setattr(servico, "TOTAL_MAX_BYTES", 10)
    assert cen.criar().status_code == 422


def test_so_a_etapa_de_aprovacao_atual_aceita_link(cen: Cenario, db_session: Session) -> None:
    e1_url, e3_url = _rota(cen.id, cen.e1["id"]), _rota(cen.id, cen.e3["id"])
    corpo = {"arquivoIds": [cen.png]}
    assert cen.admin.post(e1_url, json=corpo).status_code == 422  # etapa de execução
    assert cen.admin.post(e3_url, json=corpo).status_code == 422
    assert cen.admin.post(_rota(cen.id, str(uuid.uuid4())), json=corpo).status_code == 404
    # aprovação que NÃO é a atual: 409
    demanda2 = _demanda_com_workflow(cen.admin, [_etapa("A"), _etapa("Aprovar", "aprovacao"), _etapa("C")])
    e = _por_ordem(demanda2)
    arq = _subir(cen.admin, demanda2["id"])
    db_session.commit()
    resposta = cen.admin.post(_rota(demanda2["id"], e[1]["id"]), json={"arquivoIds": [arq]})
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "ETAPA_NAO_ATUAL"


def test_demanda_arquivada_409(cen: Cenario) -> None:
    assert cen.admin.post(f"/demandas/{cen.id}/arquivar", json={"motivoArquivamento": "teste"}).status_code in (200, 204)
    cen.db.commit()
    resposta = cen.criar(client=cen.admin)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "DEMANDA_ARQUIVADA"


# ======================================================================================
# autoridade de gestão (separada de podeAvancar)
# ======================================================================================


def test_autoridade_de_gestao_do_link(app, db_session: Session, empresa: Empresa, client_admin: TestClient, client_gestor: TestClient) -> None:
    ana = _op(db_session, empresa, "ana")
    atendimento = _atendimento(db_session, empresa, ana)
    resp_demanda = _op(db_session, empresa, "rd")
    head = _op(db_session, empresa, "head")
    depto = _departamento(db_session, empresa, nome="Mídia", responsavel_usuario_id=head.id)
    b = _op(db_session, empresa, "b")
    demanda = _demanda_com_workflow(
        client_admin,
        [_etapa("Aprovar", "aprovacao", usuarios=[b.id], departamentos=[depto.id]), _etapa("Fim")],
        usuarioResponsavelIds=[resp_demanda.id],
        departamentoResponsavelIds=[atendimento.id, depto.id],
    )
    e1 = _por_ordem(demanda)[0]
    arq = _subir(client_admin, demanda["id"])
    db_session.commit()
    url = _rota(demanda["id"], e1["id"])
    corpo = {"arquivoIds": [arq]}

    # Atendimento só por ser Atendimento (enxerga a demanda): sem autoridade
    r = _client_para(app, ana).post(url, json=corpo)
    assert r.status_code == 403
    estado = _client_para(app, ana).get(url)
    assert estado.status_code == 200 and estado.json()["podeGerenciar"] is False and estado.json()["contatos"] == []
    # sem acesso algum à demanda → 404 (não revela existência)
    estranho = _op(db_session, empresa, "estranho")
    assert _client_para(app, estranho).post(url, json=corpo).status_code == 404

    for quem in (b, head, resp_demanda):  # responsável da etapa, Head do departamento da etapa, responsável da Demanda
        r = _client_para(app, quem).post(url, json=corpo)
        assert r.status_code == 201, (quem.email, r.text)
        db_session.commit()
    assert client_gestor.post(url, json=corpo).status_code == 201
    db_session.commit()
    assert client_admin.post(url, json=corpo).status_code == 201


def test_token_de_plataforma_nao_gerencia_link(app, cen: Cenario, usuario_admin: Usuario) -> None:
    token = create_platform_token(sub=usuario_admin.id, administrador_id=str(uuid.uuid4()))
    plataforma = TestClient(app)
    plataforma.headers["Authorization"] = f"Bearer {token}"
    assert plataforma.post(_rota(cen.id, cen.e2["id"]), json={"arquivoIds": [cen.png]}).status_code in (401, 403)
    assert cen.aprovacao() is None


def test_cross_tenant_404_sem_efeito(app, cen: Cenario, db_session: Session, outra_empresa: Empresa) -> None:
    from tests.fixtures.usuarios import _criar_usuario_com_credencial

    intruso = _criar_usuario_com_credencial(db_session, empresa=outra_empresa, perfil_base="admin", email_prefixo="9b-intruso")
    db_session.commit()
    ci = _client_para(app, intruso)
    assert ci.post(_rota(cen.id, cen.e2["id"]), json={"arquivoIds": [cen.png]}).status_code == 404
    assert ci.get(_rota(cen.id, cen.e2["id"])).status_code == 404
    token, corpo = cen.link()
    assert ci.post(_rota(cen.id, cen.e2["id"], f"/{corpo['id']}/revogar")).status_code == 404
    assert cen.aprovacao(token).revogada_em is None


def test_painel_interno_estado_contatos_e_pode_gerenciar(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    cliente = _cliente(db_session, empresa)
    cliente.contatos = [
        {"id": "c-1", "nome": "João Financeiro", "email": "joao@cli.com", "telefone": "11999990000", "cargo": "Financeiro", "recebeEntregas": False},
        {"id": "c-2", "nome": "Maria Entregas", "email": "maria@cli.com", "telefone": "11888880000", "cargo": "Marketing", "recebeEntregas": True},
        {"id": "c-3", "nome": "   ", "email": "vazio@cli.com"},
    ]
    db_session.commit()
    cen = Cenario(app, db_session, empresa, client_admin, clienteId=cliente.id)
    estado = cen.cb.get(_rota(cen.id, cen.e2["id"])).json()
    assert estado["podeGerenciar"] is True and estado["atual"] is None
    assert [c["nome"] for c in estado["contatos"]] == ["Maria Entregas", "João Financeiro"]  # recebe entregas primeiro; contato sem nome fora
    assert all(set(c) == {"nome", "email", "cargo", "recebeEntregas"} for c in estado["contatos"])  # sem id nem telefone
    assert "11999990000" not in json.dumps(estado)
    assert (estado["validadePadraoDias"], estado["validadeMaxDias"]) == (7, 30)
    # etapa que não é de aprovação → não gerenciável
    assert cen.cb.get(_rota(cen.id, cen.e1["id"])).json()["podeGerenciar"] is False
    token, _ = cen.link(destinatarioNome="Maria Entregas", destinatarioEmail="maria@cli.com")
    atual = cen.cb.get(_rota(cen.id, cen.e2["id"])).json()["atual"]
    assert atual["estado"] == "pendente" and atual["destinatarioNome"] == "Maria Entregas" and "token" not in atual


# ======================================================================================
# portal público — superfície mínima e estados indistinguíveis
# ======================================================================================


def test_consulta_publica_so_o_necessario_e_nenhum_id_interno(cen: Cenario, db_session: Session) -> None:
    cen.cb.post(f"/demandas/{cen.id}/comentarios", json={"texto": "COMENTARIO-INTERNO-SECRETO"})
    token, criada = cen.link(instrucao="Veja a arte", destinatarioNome="Maria", destinatarioEmail="maria@cliente.com")
    resposta = cen.consultar(token)
    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store" and resposta.headers["referrer-policy"] == "no-referrer"
    corpo = resposta.json()
    assert set(corpo) == {"empresa", "demandaIdentificador", "demandaNome", "instrucao", "estado", "expiraEm", "destinatarioNome", "podeSolicitarAjustes", "artefatos", "decisao"}
    assert corpo["estado"] == "pendente" and corpo["decisao"] is None and corpo["podeSolicitarAjustes"] is True
    assert corpo["demandaIdentificador"] == cen.demanda["identificador"] and corpo["demandaNome"] == cen.demanda["nome"]
    assert corpo["instrucao"] == "Veja a arte" and corpo["destinatarioNome"] == "Maria"
    assert set(corpo["empresa"]) == {"corPrimaria", "corSecundaria", "tema", "logoDisponivel", "logoVersao", "padrao", "disponivel", "nomeExibicao"}
    assert corpo["empresa"]["disponivel"] is True
    assert [set(a) for a in corpo["artefatos"]] == [{"ordem", "nome", "tipo", "contentType", "tamanhoBytes"}] * 2
    assert [(a["ordem"], a["tipo"]) for a in corpo["artefatos"]] == [(1, "imagem"), (2, "pdf")]
    texto = resposta.text
    proibidos = [cen.id, cen.e1["id"], cen.e2["id"], cen.e3["id"], cen.empresa.id, cen.png, cen.pdf, cen.a.id, cen.b.id, cen.c.id, criada["id"],
                 "maria@cliente.com", cen.a.email, cen.b.email, "COMENTARIO-INTERNO-SECRETO", cen.demanda["codigoReferencia"], token]
    for valor in proibidos:
        assert valor not in texto, valor
    for chave in ("historico", "comentarios", "responsavel", "cliente", "prazo", "financeiro", "briefing"):
        assert chave not in texto.lower() or chave in ("cliente",)  # "cliente" aparece em texto livre da UI; nunca como campo
    assert all("cliente" not in campo.lower() for campo in corpo)


def test_estados_indisponiveis_sao_indistinguiveis(cen: Cenario, db_session: Session) -> None:
    desconhecido = "A" * 43
    revogado, c1 = cen.link()
    assert cen.cb.post(_rota(cen.id, cen.e2["id"], f"/{c1['id']}/revogar")).status_code == 200
    expirado, c2 = cen.link()
    ap = cen.aprovacao(expirado)
    ap.criada_em = datetime.now(timezone.utc) - timedelta(days=10)
    ap.expira_em = datetime.now(timezone.utc) - timedelta(days=3)
    db_session.commit()
    respostas = {
        "malformado": cen.consultar("curto"),
        "desconhecido": cen.consultar(desconhecido),
        "revogado": cen.consultar(revogado),
        "expirado": cen.consultar(expirado),
    }
    for nome, resposta in respostas.items():
        assert resposta.status_code == 404, nome
        assert resposta.json() == {"detail": INDISPONIVEL}, nome
    assert len({r.text for r in respostas.values()}) == 1  # corpo idêntico: nada distingue os motivos
    for token in (revogado, expirado, desconhecido):
        assert cen.artefato(token, 1).status_code == 404
        assert cen.decidir(token).status_code == 404


def test_link_obsoleto_quando_a_etapa_deixou_de_ser_a_atual(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    # a etapa é concluída por fora (sem passar pelo workflow): o link fica obsoleto, nunca decide
    etapa = db_session.get(DemandaWorkflowEtapa, cen.e2["id"])
    etapa.status, etapa.concluida_em = "concluida", datetime.now(timezone.utc)
    db_session.commit()
    resposta = cen.consultar(token)
    assert resposta.status_code == 404 and resposta.json() == {"detail": INDISPONIVEL}
    assert cen.decidir(token).status_code == 404


def test_empresa_inativa_torna_o_link_indisponivel(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    cen.empresa.status = "inativa"
    db_session.commit()
    assert cen.consultar(token).status_code == 404
    assert cen.decidir(token).status_code == 404
    assert cen.pub.post(f"{PUBLICO}/logo", json={"token": token}).status_code == 404


def test_sessao_do_tenant_nao_amplia_o_portal(cen: Cenario) -> None:
    token, _ = cen.link()
    anonima, autenticada = cen.consultar(token), cen.consultar(token, client=cen.admin)
    assert anonima.status_code == autenticada.status_code == 200 and anonima.json() == autenticada.json()
    # com sessão de OUTRO tenant ou de admin, nenhum dado extra e nenhuma rota de tarefas se abre
    assert cen.admin.post(f"{PUBLICO}/artefato", json={"token": token, "ordem": 99}).status_code == 422


def test_logo_so_com_link_legivel_e_da_empresa_do_token(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.pub.post(f"{PUBLICO}/logo", json={"token": "x"}).status_code == 404
    assert cen.pub.post(f"{PUBLICO}/logo", json={"token": token}).status_code == 404  # empresa sem logo personalizado: 404 neutro, sem vazamento
    outra = cen.pub.post(f"{PUBLICO}/logo", json={"token": token, "slug": "outra"})
    assert outra.status_code == 422 and token not in outra.text  # campos extras proibidos → nunca resolvem outra empresa


# ======================================================================================
# artefatos
# ======================================================================================


def test_artefato_imagem_inline_e_pdf_nunca_inline(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    imagem = cen.artefato(token, 1)
    assert imagem.status_code == 200 and imagem.headers["content-type"] == "image/png"
    assert imagem.headers["content-disposition"].startswith("inline")
    arquivo = db_session.get(DemandaArquivo, cen.png)
    assert imagem.content == (arquivo_modulo.UPLOADS_ROOT / "demandas" / cen.id / arquivo.nome_fisico).read_bytes()
    assert imagem.headers["x-content-type-options"] == "nosniff" and imagem.headers["cache-control"] == "no-store"
    assert "sandbox" in imagem.headers["content-security-policy"]
    pdf = cen.artefato(token, 2)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"].startswith("attachment")  # PDF nunca inline
    for ordem in (0, 3, 11):
        assert cen.artefato(token, ordem).status_code in (404, 422)


def test_artefato_adulterado_ausente_ou_fora_da_raiz_nao_e_servido(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    arquivo = db_session.get(DemandaArquivo, cen.png)
    caminho = arquivo_modulo.UPLOADS_ROOT / "demandas" / cen.id / arquivo.nome_fisico
    original = caminho.read_bytes()
    caminho.write_bytes(PNG_VALIDO + b"outro-conteudo-com-assinatura-valida")  # assinatura OK, hash diferente do snapshot
    assert cen.artefato(token, 1).status_code == 404
    caminho.write_bytes(original)
    assert cen.artefato(token, 1).status_code == 200
    caminho.unlink()
    assert cen.artefato(token, 1).status_code == 404
    # caminho fora da raiz de uploads (nome físico adulterado no banco) nunca é lido, mesmo com o mesmo conteúdo
    fora = arquivo_modulo.UPLOADS_ROOT.parent / "fora.png"
    fora.write_bytes(original)
    arquivo.nome_fisico = "../../../fora.png"
    db_session.commit()
    assert cen.artefato(token, 1).status_code == 404
    arquivo.nome_fisico = f"{cen.png}.png"
    caminho.write_bytes(original)
    db_session.commit()
    assert cen.artefato(token, 1).status_code == 200
    # arquivo que passou a ser de OUTRA demanda não é servido
    outra = _demanda_com_workflow(cen.admin, [_etapa("X")])
    db_session.commit()
    arquivo.demanda_id = outra["id"]
    db_session.commit()
    assert cen.artefato(token, 1).status_code == 404


def test_artefato_de_outra_aprovacao_ou_do_mesmo_arquivo_fora_da_lista_nao_e_acessivel(cen: Cenario) -> None:
    extra = _subir(cen.admin, cen.id, nome="extra.png")
    cen.db.commit()
    token, _ = cen.link(arquivos=[cen.png])
    assert cen.artefato(token, 1).status_code == 200
    assert cen.artefato(token, 2).status_code in (404, 422)  # o PDF e o "extra" não fazem parte desta aprovação
    assert extra not in cen.consultar(token).text and cen.pdf not in cen.consultar(token).text


# ======================================================================================
# decisão — contrato estrito
# ======================================================================================


@pytest.mark.parametrize(
    "extra",
    [
        {"nome": "ab"},  # < 3
        {"nome": "x" * 121},
        {"nome": "   "},
        {"nome": "<b>Maria</b>"},
        {"email": "sem-arroba"},
        {"email": "a@b"},
        {"decisao": "talvez"},
        {"decisao": "aprovar", "motivo": "não deveria vir"},
        {"decisao": "solicitar_ajustes", "motivo": None},
        {"decisao": "solicitar_ajustes", "motivo": "ab"},
        {"decisao": "solicitar_ajustes", "motivo": "<script>x</script>"},
        {"decisao": "solicitar_ajustes", "motivo": "x" * 1001},
        {"etapaId": "qualquer"},  # campos extras proibidos
        {"usuarioId": "qualquer"},
    ],
)
def test_decisao_invalida_422_sem_ecoar_o_token(cen: Cenario, extra: dict) -> None:
    token, _ = cen.link()
    corpo = {"token": token, "decisao": "aprovar", "nome": NOME, "email": None, "motivo": None, **extra}
    resposta = cen.pub.post(f"{PUBLICO}/decisao", json=corpo)
    assert resposta.status_code == 422, resposta.text
    assert token not in resposta.text  # o 422 padrão do FastAPI devolveria o input
    assert cen.aprovacao(token).decisao is None


def test_decisao_com_corpo_invalido_ou_gigante(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.pub.post(f"{PUBLICO}/decisao", content=b"nao-e-json", headers={"content-type": "application/json"}).status_code == 422
    assert cen.pub.post(f"{PUBLICO}/decisao", json=[1, 2]).status_code == 422
    assert cen.pub.post(f"{PUBLICO}/decisao", json={"token": token, "decisao": "aprovar", "nome": NOME, "motivo": None, "x": "y" * 20000}).status_code == 413


# ======================================================================================
# decisão — aprovar
# ======================================================================================


def test_aprovar_avanca_o_workflow_com_ator_externo_explicito(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    resposta = cen.decidir(token)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["estado"] == "aprovada"

    estado = _estado(cen.admin, cen.id)
    por = _por_id(estado)
    assert por[cen.e2["id"]]["status"] == "concluida" and por[cen.e2["id"]]["concluidaEm"] is not None
    assert por[cen.e2["id"]]["concluidaPorUsuarioId"] is None  # nunca um Usuario fictício
    assert por[cen.e2["id"]]["concluidaPorExternoNome"] == NOME  # derivado da decisão externa (sem coluna nova no workflow)
    assert estado["etapaAtualId"] == cen.e3["id"] and por[cen.e3["id"]]["iniciadaEm"] is not None
    assert estado["status"] == cen.demanda["status"]  # a Demanda não é concluída nem alterada

    ap = cen.aprovacao(token)
    assert (ap.decisao, ap.nome_aprovador, ap.email_aprovador, ap.motivo) == ("aprovada", NOME, EMAIL_NORMALIZADO, None) and ap.decidida_em is not None
    (aprovada,) = _eventos(db_session, cen.id, APROVADA)
    assert aprovada.usuario_id is None
    assert aprovada.payload["atorUsuarioId"] is None
    assert aprovada.payload["atorExterno"] == {"nome": NOME, "aprovacaoExternaId": ap.id}
    assert aprovada.payload["proximaEtapaId"] == cen.e3["id"]
    (externa,) = _eventos(db_session, cen.id, EXT_APROVADA)
    assert externa.usuario_id is None and externa.payload["atorExterno"]["nome"] == NOME
    for evento in _eventos(db_session, cen.id):  # e-mail do aprovador e token nunca vão para evento
        texto = json.dumps(evento.payload).lower()
        assert EMAIL_NORMALIZADO not in texto and token.lower() not in texto and "ip" not in evento.payload

    tipos = [h["tipo"] for h in cen.admin.get(f"/demandas/{cen.id}/historico").json()]
    assert APROVADA in tipos and EXT_CRIADA in tipos
    assert EXT_APROVADA not in tipos and ATUALIZADA not in tipos  # sem linha duplicada na timeline
    # layouts não mudam de status sozinhos
    assert {a["statusLayout"] for a in cen.admin.get(f"/demandas/{cen.id}/arquivos").json() if a["tipo"] == "layout"} == {"novo"}


def test_depois_de_decidido_o_link_continua_legivel_e_nao_aceita_nova_decisao(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.decidir(token).status_code == 200
    de_novo = cen.consultar(token)
    assert de_novo.status_code == 200
    corpo = de_novo.json()
    assert corpo["estado"] == "aprovada" and corpo["decisao"]["decisao"] == "aprovada" and corpo["decisao"]["decididaEm"]
    assert NOME not in de_novo.text and EMAIL_NORMALIZADO not in de_novo.text  # nem o nome nem o e-mail de quem decidiu voltam ao portador
    assert cen.artefato(token, 1).status_code == 200  # evidência continua visível, somente leitura
    segunda = cen.decidir(token)
    assert segunda.status_code == 409 and segunda.json()["detail"]["code"] == "APROVACAO_JA_DECIDIDA"
    outra = cen.decidir(token, "solicitar_ajustes", motivo="Mudei de ideia")
    assert outra.status_code == 409
    assert len(_eventos(cen.db, cen.id, APROVADA)) == 1 and len(_eventos(cen.db, cen.id, REJEITADA)) == 0
    assert cen.aprovacao(token).decisao == "aprovada"


def test_aprovar_sem_e_mail_e_nome_normalizado(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.decidir(token, nome="  Maria   da   Silva  ", email=None).status_code == 200
    ap = cen.aprovacao(token)
    assert ap.nome_aprovador == "Maria da Silva" and ap.email_aprovador is None


# ======================================================================================
# decisão — solicitar ajustes (semântica 8D)
# ======================================================================================


def test_solicitar_ajustes_devolve_para_a_etapa_anterior_com_motivo(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    motivo = "Trocar o logotipo e corrigir o telefone"
    resposta = cen.decidir(token, "solicitar_ajustes", motivo=motivo)
    assert resposta.status_code == 200 and resposta.json()["estado"] == "ajustes_solicitados"

    estado = _estado(cen.admin, cen.id)
    por = _por_id(estado)
    assert estado["etapaAtualId"] == cen.e1["id"]  # voltou para a imediatamente anterior
    assert (por[cen.e2["id"]]["status"], por[cen.e2["id"]]["concluidaPorUsuarioId"], por[cen.e2["id"]]["concluidaPorExternoNome"]) == ("pendente", None, None)
    assert por[cen.e1["id"]]["status"] == "pendente" and por[cen.e1["id"]]["concluidaEm"] is None and por[cen.e1["id"]]["iniciadaEm"] is not None
    ap = cen.aprovacao(token)
    assert (ap.decisao, ap.nome_aprovador, ap.motivo) == ("ajustes_solicitados", NOME, motivo)
    (rejeitada,) = _eventos(db_session, cen.id, REJEITADA)
    assert rejeitada.usuario_id is None and rejeitada.payload["motivo"] == motivo
    assert rejeitada.payload["atorExterno"] == {"nome": NOME, "aprovacaoExternaId": ap.id} and rejeitada.payload["etapaRetornoId"] == cen.e1["id"]
    assert len(_eventos(db_session, cen.id, EXT_AJUSTES)) == 1
    tipos = [h["tipo"] for h in cen.admin.get(f"/demandas/{cen.id}/historico").json()]
    assert REJEITADA in tipos and EXT_AJUSTES not in tipos
    # o link continua legível, somente leitura; e um novo link pode ser gerado depois da correção
    assert cen.consultar(token).json()["estado"] == "ajustes_solicitados"
    assert cen.decidir(token).status_code == 409


def test_ciclo_ajustes_corrige_e_novo_link_aprovado(cen: Cenario) -> None:
    primeiro, _ = cen.link()
    assert cen.decidir(primeiro, "solicitar_ajustes", motivo="Ajustar as cores").status_code == 200
    assert cen.ca.post(_url(cen.id, cen.e1["id"], "concluir")).status_code == 200  # Criação refeita → Aprovação volta a ser a atual
    cen.db.commit()
    segundo, _ = cen.link()
    assert segundo != primeiro
    assert cen.decidir(segundo).status_code == 200
    assert _estado(cen.admin, cen.id)["etapaAtualId"] == cen.e3["id"]
    assert cen.consultar(primeiro).json()["estado"] == "ajustes_solicitados"  # a decisão anterior continua como evidência


def test_ajustes_na_primeira_etapa_nao_tem_para_onde_devolver(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovação inicial", "aprovacao"), _etapa("Fim")])
    e1, _ = _por_ordem(demanda)
    arq = _subir(client_admin, demanda["id"])
    db_session.commit()
    criada = client_admin.post(_rota(demanda["id"], e1["id"]), json={"arquivoIds": [arq]})
    assert criada.status_code == 201
    db_session.commit()
    token, pub = criada.json()["token"], TestClient(app)
    assert pub.post(f"{PUBLICO}/consultar", json={"token": token}).json()["podeSolicitarAjustes"] is False
    corpo = {"token": token, "decisao": "solicitar_ajustes", "nome": NOME, "email": None, "motivo": "Corrigir"}
    resposta = pub.post(f"{PUBLICO}/decisao", json=corpo)
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "SEM_ETAPA_ANTERIOR"
    # nada foi gravado: o link continua pendente e a aprovação ainda é possível
    assert pub.post(f"{PUBLICO}/consultar", json={"token": token}).json()["estado"] == "pendente"
    assert pub.post(f"{PUBLICO}/decisao", json={**corpo, "decisao": "aprovar", "motivo": None}).status_code == 200


# ======================================================================================
# notificações e autor externo
# ======================================================================================


def _central(client: TestClient) -> list[dict]:
    return client.get("/notificacoes", params={"limit": 100}).json()["itens"]


def test_notificacoes_da_decisao_externa_mostram_o_nome_do_cliente_e_nao_sistema(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    dono = _op(db_session, empresa, "dono")
    cen = Cenario(app, db_session, empresa, client_admin, usuarioResponsavelIds=[dono.id])
    cdono = _client_para(app, dono)
    token, _ = cen.link()
    assert cen.decidir(token).status_code == 200
    db_session.commit()

    do_dono = {n["tipo"]: n for n in _central(cdono)}
    assert do_dono[EXT_APROVADA]["titulo"] == "Cliente aprovou a etapa de aprovação"
    assert do_dono[EXT_APROVADA]["autorNome"] == NOME and do_dono[EXT_APROVADA]["categoria"] == "minhas"
    assert do_dono[EXT_APROVADA]["detalhe"] == "Etapa 2: Aprovação"
    assert "Sistema" not in json.dumps(_central(cdono))
    # a próxima etapa (Publicação → c) avisa quem precisa agir, com o nome do cliente como autor
    de_c = [n for n in _central(cen.cc) if n["tipo"] == ATUALIZADA]
    assert de_c and de_c[0]["autorNome"] == NOME and de_c[0]["categoria"] == "minhas"
    assert cdono.get("/notificacoes/resumo").json()["naoLidas"]["sistema"] == 0  # nada vai para a categoria "Sistema"


def test_notificacoes_dos_ajustes_externos(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    dono = _op(db_session, empresa, "dono2")
    cen = Cenario(app, db_session, empresa, client_admin, usuarioResponsavelIds=[dono.id])
    token, _ = cen.link()
    assert cen.decidir(token, "solicitar_ajustes", motivo="MOTIVO-DO-CLIENTE-123").status_code == 200
    db_session.commit()
    do_dono = {n["tipo"]: n for n in _central(_client_para(app, dono))}
    assert do_dono[EXT_AJUSTES]["titulo"] == "Cliente solicitou ajustes" and do_dono[EXT_AJUSTES]["autorNome"] == NOME
    da_criacao = [n for n in _central(cen.ca) if n["tipo"] == ATUALIZADA]
    assert da_criacao and da_criacao[0]["titulo"] == "Etapa devolvida para ajustes" and da_criacao[0]["autorNome"] == NOME
    assert "MOTIVO-DO-CLIENTE-123" not in json.dumps(_central(_client_para(app, dono))) + json.dumps(_central(cen.ca))  # motivo fica no histórico


# ======================================================================================
# revogar / substituir
# ======================================================================================


def test_novo_link_revoga_o_anterior_mesmo_expirado(cen: Cenario, db_session: Session) -> None:
    antigo, c1 = cen.link()
    ap = cen.aprovacao(antigo)
    ap.criada_em, ap.expira_em = datetime.now(timezone.utc) - timedelta(days=9), datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()
    novo, c2 = cen.link()
    assert antigo != novo and c1["id"] != c2["id"]
    ap_antigo = cen.aprovacao(antigo)
    assert ap_antigo.revogada_motivo == "substituida" and ap_antigo.revogada_por_usuario_id == cen.b.id and ap_antigo.decisao is None
    assert cen.consultar(antigo).status_code == 404 and cen.consultar(novo).status_code == 200
    abertas = db_session.scalar(
        select(func.count()).select_from(AprovacaoExterna).where(
            AprovacaoExterna.workflow_etapa_id == cen.e2["id"], AprovacaoExterna.decisao.is_(None), AprovacaoExterna.revogada_em.is_(None)
        )
    )
    assert abertas == 1
    (revogada,) = _eventos(db_session, cen.id, EXT_REVOGADA)
    assert revogada.payload["motivo"] == "substituida" and revogada.payload["aprovacaoExternaId"] == c1["id"]


def test_revogar_manual_e_idempotente_e_decidida_nao_se_revoga(cen: Cenario, db_session: Session) -> None:
    token, criada = cen.link()
    url = _rota(cen.id, cen.e2["id"], f"/{criada['id']}/revogar")
    r = cen.cb.post(url)
    assert r.status_code == 200 and r.json()["estado"] == "revogada" and r.json()["revogadaMotivo"] == "manual"
    db_session.commit()
    assert cen.cb.post(url).status_code == 200  # idempotente
    assert len(_eventos(db_session, cen.id, EXT_REVOGADA)) == 1  # sem evento duplicado
    assert cen.consultar(token).status_code == 404 and cen.decidir(token).status_code == 404
    # outra etapa / solicitação inexistente
    assert cen.cb.post(_rota(cen.id, cen.e1["id"], f"/{criada['id']}/revogar")).status_code in (404, 422, 403)
    assert cen.cb.post(_rota(cen.id, cen.e2["id"], f"/{uuid.uuid4()}/revogar")).status_code == 404
    # decidida: 409
    novo, c2 = cen.link()
    assert cen.decidir(novo).status_code == 200
    db_session.commit()
    r = cen.admin.post(_rota(cen.id, cen.e2["id"], f"/{c2['id']}/revogar"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "APROVACAO_EXTERNA_JA_DECIDIDA"


def test_revogar_exige_autoridade_de_gestao(app, db_session: Session, empresa: Empresa, client_admin: TestClient) -> None:
    ana = _op(db_session, empresa, "ana2")
    atendimento = _atendimento(db_session, empresa, ana)
    b = _op(db_session, empresa, "b2")
    demanda = _demanda_com_workflow(client_admin, [_etapa("Aprovar", "aprovacao", usuarios=[b.id])], departamentoResponsavelIds=[atendimento.id])
    e = _por_ordem(demanda)[0]
    arq = _subir(client_admin, demanda["id"])
    db_session.commit()
    criada = _client_para(app, b).post(_rota(demanda["id"], e["id"]), json={"arquivoIds": [arq]}).json()
    db_session.commit()
    assert _client_para(app, ana).post(_rota(demanda["id"], e["id"], f"/{criada['id']}/revogar")).status_code == 403


# ======================================================================================
# ação interna enquanto o link está aberto
# ======================================================================================


def test_aprovacao_interna_revoga_o_link_aberto_na_mesma_transacao(cen: Cenario, db_session: Session) -> None:
    token, criada = cen.link()
    assert cen.cb.post(_url(cen.id, cen.e2["id"], "aprovar")).status_code == 200
    ap = cen.aprovacao(token)
    assert ap.revogada_motivo == "etapa_decidida_internamente" and ap.revogada_por_usuario_id == cen.b.id and ap.decisao is None
    (revogada,) = _eventos(db_session, cen.id, EXT_REVOGADA)
    assert revogada.payload["motivo"] == "etapa_decidida_internamente" and revogada.usuario_id == cen.b.id
    # o cliente que chega depois vê o link indisponível e a decisão interna segue como a única
    assert cen.consultar(token).status_code == 404 and cen.decidir(token).status_code == 404
    assert len(_eventos(db_session, cen.id, APROVADA)) == 1 and _eventos(db_session, cen.id, APROVADA)[0].usuario_id == cen.b.id


def test_rejeicao_interna_tambem_revoga_o_link_aberto(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link()
    assert cen.cb.post(_url(cen.id, cen.e2["id"], "rejeitar"), json={"motivo": "Faltou o briefing"}).status_code == 200
    assert cen.aprovacao(token).revogada_motivo == "etapa_decidida_internamente"
    assert cen.decidir(token).status_code == 404
    assert _estado(cen.admin, cen.id)["etapaAtualId"] == cen.e1["id"]


def test_decisao_externa_primeiro_e_depois_a_interna_conflita(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.decidir(token).status_code == 200
    # `b` perdeu o escopo derivado da etapa (ela deixou de ser a atual); o admin do tenant chega e recebe o 409 estruturado
    assert cen.cb.post(_url(cen.id, cen.e2["id"], "aprovar")).status_code == 404
    resposta = cen.admin.post(_url(cen.id, cen.e2["id"], "aprovar"))
    assert resposta.status_code == 409 and resposta.json()["detail"]["code"] == "ETAPA_JA_CONCLUIDA"
    assert len(_eventos(cen.db, cen.id, APROVADA)) == 1


def test_aprovar_interno_sem_link_nao_cria_evento_de_revogacao(cen: Cenario) -> None:
    assert cen.cb.post(_url(cen.id, cen.e2["id"], "aprovar")).status_code == 200
    assert _eventos(cen.db, cen.id, EXT_REVOGADA) == []


# ======================================================================================
# exclusão de arquivos (individual e em lote)
# ======================================================================================


def test_exclusao_individual_bloqueada_com_link_aberto_ou_decidido_e_liberada_se_revogado(cen: Cenario, db_session: Session) -> None:
    token, criada = cen.link(arquivos=[cen.png])
    r = cen.admin.delete(f"/demandas/{cen.id}/arquivos/{cen.png}")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ARQUIVO_VINCULADO_APROVACAO_EXTERNA"
    assert db_session.get(DemandaArquivo, cen.png) is not None
    assert cen.admin.delete(f"/demandas/{cen.id}/arquivos/{cen.pdf}").status_code in (200, 204)  # não referenciado: segue livre

    # revogada sem decisão: libera, e o snapshot sobrevive com arquivo_id NULL
    assert cen.cb.post(_rota(cen.id, cen.e2["id"], f"/{criada['id']}/revogar")).status_code == 200
    db_session.commit()
    assert cen.admin.delete(f"/demandas/{cen.id}/arquivos/{cen.png}").status_code in (200, 204)
    db_session.expire_all()
    artefato = db_session.scalars(select(AprovacaoExternaArquivo).where(AprovacaoExternaArquivo.aprovacao_externa_id == criada["id"])).one()
    assert artefato.arquivo_id is None and artefato.nome_original == "arte.png" and len(artefato.sha256) == 64


def test_exclusao_bloqueada_depois_da_decisao_evidencia_retida(cen: Cenario, db_session: Session) -> None:
    token, _ = cen.link(arquivos=[cen.png])
    assert cen.decidir(token).status_code == 200
    db_session.commit()
    r = cen.admin.delete(f"/demandas/{cen.id}/arquivos/{cen.png}")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ARQUIVO_VINCULADO_APROVACAO_EXTERNA"
    assert cen.artefato(token, 1).status_code == 200  # a evidência continua servida


def test_exclusao_em_lote_valida_todos_antes_e_nao_exclui_nada_se_um_estiver_protegido(cen: Cenario, db_session: Session) -> None:
    livre = _subir(cen.admin, cen.id, nome="livre.png")
    db_session.commit()
    cen.link(arquivos=[cen.png])
    r = cen.admin.post("/arquivos/excluir-lote", json={"mode": "ids", "ids": [livre, cen.png]})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "ARQUIVO_VINCULADO_APROVACAO_EXTERNA" and r.json()["detail"]["quantidade"] == 1
    db_session.expire_all()
    assert db_session.get(DemandaArquivo, livre) is not None and db_session.get(DemandaArquivo, cen.png) is not None  # nada parcial
    ok = cen.admin.post("/arquivos/excluir-lote", json={"mode": "ids", "ids": [livre, cen.pdf]})
    assert ok.status_code == 200 and ok.json()["excluidos"] == 2


# ======================================================================================
# segurança / logs
# ======================================================================================


def test_token_nunca_aparece_em_logs(cen: Cenario, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    token, _ = cen.link()
    cen.consultar(token)
    cen.artefato(token, 1)
    cen.consultar("B" * 43)
    cen.decidir(token, "solicitar_ajustes", motivo="ajustar")
    cen.decidir(token)
    assert token not in caplog.text and hashlib.sha256(token.encode()).hexdigest() not in caplog.text


def test_o_token_nao_trafega_em_url_nem_path(cen: Cenario) -> None:
    token, _ = cen.link()
    assert cen.pub.get(f"{PUBLICO}/consultar?token={token}").status_code == 405
    assert cen.pub.get(f"{PUBLICO}/{token}").status_code in (404, 405)
    assert cen.pub.post(f"{PUBLICO}/consultar?token={token}", json={}).status_code == 404  # só o corpo vale


# ======================================================================================
# concorrência REAL (sessões separadas, dados commitados, locks do Postgres)
# ======================================================================================


@pytest.fixture()
def commitado(test_engine):
    """Cenário com dados REAIS: empresa, gestor, Demanda com 4 etapas (2 = aprovação), 3 layouts em disco e a Criação concluída."""
    Fabrica = sessionmaker(bind=test_engine)
    sufixo = uuid.uuid4().hex[:8]
    agora = datetime.now(timezone.utc)
    with Fabrica() as db:
        empresa = Empresa(id=str(uuid.uuid4()), nome="Empresa Conc9B", codigo_interno=f"C9B-{sufixo}".upper(), status="ativa", created_at=agora, updated_at=agora)
        db.add(empresa)
        db.flush()
        usuario = Usuario(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"c9b-{sufixo}", nome="Gestor Conc", email=f"c9b-{sufixo}@teste.taskfloww.local",
            perfil_base="gestor", acesso_sistema=True, status="ativo", created_at=agora, updated_at=agora,
        )
        db.add(usuario)
        db.flush()
        demanda = Demanda(
            id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_referencia=f"T9{sufixo[:6]}", ano_referencia=26, sequencial_referencia=1,
            numero_operacional=1, identificador="#1", nome="Concorrência 9B", status="planejada", prioridade="media", sinalizada=False,
            created_at=agora, updated_at=agora,
        )
        db.add(demanda)
        db.flush()
        etapas = [
            DemandaWorkflowEtapa(
                id=str(uuid.uuid4()), demanda_id=demanda.id, ordem=i, nome=f"Etapa {i}", tipo="aprovacao" if i == 2 else "execucao",
                quantidade_antes_deadline=1, unidade_prazo="dias_corridos", status="concluida" if i == 1 else "pendente",
                iniciada_em=agora if i <= 2 else None, concluida_em=agora if i == 1 else None, created_at=agora, updated_at=agora,
            )
            for i in (1, 2, 3, 4)
        ]
        db.add_all(etapas)
        pasta = arquivo_modulo.UPLOADS_ROOT / "demandas" / demanda.id
        pasta.mkdir(parents=True, exist_ok=True)
        arquivos = []
        for i in range(3):
            arquivo_id = str(uuid.uuid4())
            conteudo = PNG_VALIDO + uuid.uuid4().bytes
            (pasta / f"{arquivo_id}.png").write_bytes(conteudo)
            arquivos.append(
                DemandaArquivo(
                    id=arquivo_id, demanda_id=demanda.id, nome_original=f"arte{i}.png", nome_fisico=f"{arquivo_id}.png", content_type="image/png",
                    tamanho_bytes=len(conteudo), tipo="layout", status_layout="novo", created_at=agora,
                )
            )
        db.add_all(arquivos)
        db.commit()
        ids = {"empresa": empresa.id, "usuario": usuario.id, "demanda": demanda.id, "etapas": [e.id for e in etapas], "arquivos": [a.id for a in arquivos]}
    try:
        yield Fabrica, ids
    finally:
        with Fabrica() as db:
            db.query(AprovacaoExterna).filter(AprovacaoExterna.demanda_id == ids["demanda"]).delete()  # artefatos caem por CASCADE
            db.query(Evento).filter(Evento.entidade_id == ids["demanda"]).delete()
            db.query(Demanda).filter(Demanda.id == ids["demanda"]).delete()  # etapas e arquivos caem por CASCADE
            db.query(Usuario).filter(Usuario.id == ids["usuario"]).delete()
            db.query(Empresa).filter(Empresa.id == ids["empresa"]).delete()
            db.commit()


def _criar_link_commitado(Fabrica, ids, arquivos: list[str] | None = None) -> tuple[str, str]:
    from app.schemas.aprovacao_externa import AprovacaoExternaCriar
    from app.services.aprovacao_externa_service import AprovacaoExternaService

    with Fabrica() as db:
        demanda, usuario = db.get(Demanda, ids["demanda"]), db.get(Usuario, ids["usuario"])
        payload = AprovacaoExternaCriar(arquivoIds=arquivos or ids["arquivos"][:1])
        criada = AprovacaoExternaService().criar(db, demanda, etapa_id=ids["etapas"][1], payload=payload, usuario=usuario)
        return criada.token, str(criada.id)


def _disputar(Fabrica, tarefas: list) -> list[str]:
    """Executa cada `tarefa(db) -> str` em sua própria sessão/thread, largando todas ao mesmo tempo."""
    barreira = threading.Barrier(len(tarefas))
    resultados: list[str] = []
    trava = threading.Lock()

    def correr(tarefa) -> None:
        with Fabrica() as db:
            barreira.wait(timeout=10)
            try:
                saida = tarefa(db)
            except Exception as exc:  # noqa: BLE001 — o nome do tipo é o resultado
                saida = type(exc).__name__ + (f":{getattr(exc, 'codigo', '')}" if getattr(exc, "codigo", None) else "")
            with trava:
                resultados.append(saida)

    threads = [threading.Thread(target=correr, args=(t,)) for t in tarefas]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(resultados) == len(tarefas), "alguma thread não terminou (possível deadlock)"
    return resultados


def _externa(token: str, decisao: str):
    from app.schemas.aprovacao_externa import AprovacaoPublicaDecisao
    from app.services.aprovacao_externa_service import AprovacaoExternaService

    corpo = AprovacaoPublicaDecisao(token=token, decisao=decisao, nome="Cliente Concorrente", motivo="Ajustar a arte" if decisao == "solicitar_ajustes" else None)

    def tarefa(db) -> str:
        AprovacaoExternaService().decidir(db, corpo)
        return f"ok:{decisao}"

    return tarefa


def _interna(ids, acao: str):
    from app.services.demanda_workflow_service import DemandaWorkflowService

    def tarefa(db) -> str:
        servico = DemandaWorkflowService()
        demanda, ator = db.get(Demanda, ids["demanda"]), db.get(Usuario, ids["usuario"])
        if acao == "aprovar":
            servico.aprovar_etapa(db, demanda, etapa_id=ids["etapas"][1], actor=ator)
        else:
            servico.rejeitar_etapa(db, demanda, etapa_id=ids["etapas"][1], motivo="Rejeição interna", actor=ator)
        return f"ok:interna-{acao}"

    return tarefa


def _contagem(Fabrica, ids, tipo: str) -> int:
    with Fabrica() as db:
        return db.scalar(select(func.count()).select_from(Evento).where(Evento.entidade_id == ids["demanda"], Evento.tipo == tipo))


def _status_etapas(Fabrica, ids) -> list[str]:
    with Fabrica() as db:
        return [e.status for e in db.scalars(select(DemandaWorkflowEtapa).where(DemandaWorkflowEtapa.demanda_id == ids["demanda"]).order_by(DemandaWorkflowEtapa.ordem))]


def test_seis_aprovacoes_externas_simultaneas_uma_vence(commitado) -> None:
    Fabrica, ids = commitado
    token, _ = _criar_link_commitado(Fabrica, ids)
    resultados = _disputar(Fabrica, [_externa(token, "aprovar") for _ in range(6)])
    assert sorted(resultados) == ["AprovacaoExternaJaDecididaError"] * 5 + ["ok:aprovar"], resultados
    assert _status_etapas(Fabrica, ids) == ["concluida", "concluida", "pendente", "pendente"]
    assert _contagem(Fabrica, ids, APROVADA) == 1 and _contagem(Fabrica, ids, EXT_APROVADA) == 1


def test_aprovar_e_pedir_ajustes_ao_mesmo_tempo_um_unico_vencedor(commitado) -> None:
    Fabrica, ids = commitado
    token, _ = _criar_link_commitado(Fabrica, ids)
    resultados = _disputar(Fabrica, [_externa(token, "aprovar"), _externa(token, "solicitar_ajustes")] * 3)
    vencedores = [r for r in resultados if r.startswith("ok:")]
    assert len(vencedores) == 1 and resultados.count("AprovacaoExternaJaDecididaError") == 5, resultados
    aprovada = vencedores[0] == "ok:aprovar"
    assert _contagem(Fabrica, ids, APROVADA) == (1 if aprovada else 0) and _contagem(Fabrica, ids, REJEITADA) == (0 if aprovada else 1)
    esperado = ["concluida", "concluida", "pendente", "pendente"] if aprovada else ["pendente", "pendente", "pendente", "pendente"]
    assert _status_etapas(Fabrica, ids) == esperado


@pytest.mark.parametrize("acao_interna", ["aprovar", "rejeitar"])
def test_decisao_interna_e_externa_simultaneas_um_vencedor(commitado, acao_interna: str) -> None:
    Fabrica, ids = commitado
    token, aprovacao_id = _criar_link_commitado(Fabrica, ids)
    resultados = _disputar(Fabrica, [_interna(ids, acao_interna), _externa(token, "aprovar")])
    assert sum(r.startswith("ok:") for r in resultados) == 1, resultados
    perdedor = next(r for r in resultados if not r.startswith("ok:"))
    interna_ganhou = f"ok:interna-{acao_interna}" in resultados
    with Fabrica() as db:
        ap = db.get(AprovacaoExterna, aprovacao_id)
        if interna_ganhou:  # o link foi revogado na MESMA transação; o cliente vê indisponível
            assert ap.revogada_motivo == "etapa_decidida_internamente" and ap.decisao is None
            assert perdedor == "AprovacaoExternaIndisponivelError"
        else:  # a decisão externa venceu; a interna encontra a etapa já resolvida (409)
            assert ap.decisao == "aprovada" and ap.revogada_em is None
            assert perdedor.startswith("DemandaWorkflowConflitoError")
    assert _contagem(Fabrica, ids, APROVADA) + _contagem(Fabrica, ids, REJEITADA) == 1


def test_criar_link_e_avancar_internamente_ao_mesmo_tempo_nao_deixa_link_em_etapa_que_nao_e_a_atual(commitado) -> None:
    Fabrica, ids = commitado
    from app.schemas.aprovacao_externa import AprovacaoExternaCriar
    from app.services.aprovacao_externa_service import AprovacaoExternaService

    def criar(db) -> str:
        demanda, usuario = db.get(Demanda, ids["demanda"]), db.get(Usuario, ids["usuario"])
        AprovacaoExternaService().criar(db, demanda, etapa_id=ids["etapas"][1], payload=AprovacaoExternaCriar(arquivoIds=ids["arquivos"][:1]), usuario=usuario)
        return "ok:criar"

    resultados = _disputar(Fabrica, [criar, _interna(ids, "aprovar")])
    assert "ok:interna-aprovar" in resultados, resultados  # a aprovação interna sempre acontece (o link nunca a bloqueia)
    with Fabrica() as db:
        abertas = db.scalar(
            select(func.count()).select_from(AprovacaoExterna).where(
                AprovacaoExterna.workflow_etapa_id == ids["etapas"][1], AprovacaoExterna.decisao.is_(None), AprovacaoExterna.revogada_em.is_(None)
            )
        )
        assert abertas == 0  # ou o link nem foi criado, ou foi criado e revogado pela ação interna
    if "ok:criar" not in resultados:
        assert any(r.startswith("DemandaWorkflowConflitoError") for r in resultados), resultados


def test_excluir_arquivo_e_criar_aprovacao_ao_mesmo_tempo_nunca_os_dois_ok(commitado) -> None:
    Fabrica, ids = commitado
    from app.schemas.aprovacao_externa import AprovacaoExternaCriar
    from app.services.aprovacao_externa_service import AprovacaoExternaService
    from app.services.demanda_arquivo_service import DemandaArquivoService

    alvo = ids["arquivos"][0]

    def criar(db) -> str:
        demanda, usuario = db.get(Demanda, ids["demanda"]), db.get(Usuario, ids["usuario"])
        AprovacaoExternaService().criar(db, demanda, etapa_id=ids["etapas"][1], payload=AprovacaoExternaCriar(arquivoIds=[alvo]), usuario=usuario)
        return "ok:criar"

    def excluir(db) -> str:
        DemandaArquivoService().excluir(db, db.get(Demanda, ids["demanda"]), alvo, actor_usuario_id=ids["usuario"])
        return "ok:excluir"

    resultados = _disputar(Fabrica, [criar, excluir])
    assert sum(r.startswith("ok:") for r in resultados) == 1, resultados  # exatamente um vence
    with Fabrica() as db:
        existe = db.get(DemandaArquivo, alvo) is not None
        referencias = db.scalar(select(func.count()).select_from(AprovacaoExternaArquivo).where(AprovacaoExternaArquivo.arquivo_id == alvo))
        if "ok:criar" in resultados:
            assert existe and referencias == 1 and "ArquivoVinculadoAprovacaoExternaError" in resultados
        else:
            assert not existe and referencias == 0 and "AprovacaoExternaEntradaInvalidaError" in resultados
