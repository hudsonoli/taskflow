"""D2-D3C2 — `GET /sessoes-trabalho/trafego/carga`: "Carga por usuário / departamento /
equipe" da Central de Tráfego agregada no servidor, sem o cap de 100 da listagem.

Os valores são EXATOS: o relógio-base dos testes é o `NOW()` da própria transação
(`_agora_db`), o mesmo que o SQL usa — então "iniciada há 600s" é decorrido == 600, sem
tolerância. Além dos casos calculados à mão há um teste de PARIDADE que porta `filterSessoes` +
`buildCarga` + `buildCargaEquipe` (frontend/src/lib/trafego.ts) para Python e compara com o
servidor.
"""

from __future__ import annotations

import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.equipe import Equipe
from app.models.equipe_membro import EquipeMembro
from app.models.sessao_trabalho import SessaoTrabalho
from app.models.usuario import Usuario
from tests.helpers.api import get


def _agora_db(db: Session) -> datetime:
    """`NOW()` da transação de teste — o mesmo relógio que o SQL do agregado usa."""
    return db.execute(text("SELECT now()")).scalar_one()


def _usuario(db: Session, empresa: Empresa, nome: str | None = None, status: str = "ativo") -> Usuario:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    usuario = Usuario(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"u-{sufixo}",
        nome=nome or f"Usuário {sufixo}",
        email=f"u-{sufixo}@teste.local",
        perfil_base="operador",
        acesso_sistema=True,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _departamento(db: Session, empresa: Empresa, nome: str | None = None) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    nome = nome or f"Depto {sufixo}"
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=f"{nome.lower()}-{sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _equipe(db: Session, empresa: Empresa, nome: str, membros: list[Usuario], status: str = "ativo") -> Equipe:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    equipe = Equipe(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"eq-{sufixo}",
        codigo_referencia=f"E26{uuid.uuid4().int % 1000000:06d}",
        ano_referencia=2026,
        sequencial_referencia=uuid.uuid4().int % 1000000,
        nome=nome,
        nome_normalizado=f"{nome.lower()}-{sufixo}",
        cor_identificacao="blue",
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(equipe)
    db.flush()
    for membro in membros:
        db.add(EquipeMembro(equipe_id=equipe.id, usuario_id=membro.id, created_at=agora))
    db.flush()
    return equipe


def _sessao(
    db: Session,
    empresa: Empresa,
    *,
    decorrido: int | None = None,
    inicio_em: datetime | None = None,
    status: str = "ativa",
    usuario: Usuario | None = None,
    departamento: Departamento | None = None,
    demanda_id: str | None = None,
    created_at: datetime | None = None,
) -> SessaoTrabalho:
    """Ativa "iniciada há `decorrido` segundos" (relativo ao NOW() da transação) — ou com
    `inicio_em` explícito. `status="encerrada"`/`"cancelada"` só servem de ruído."""
    agora_db = _agora_db(db)
    inicio = inicio_em if inicio_em is not None else agora_db - timedelta(seconds=decorrido or 0)
    criada = created_at or datetime.now(timezone.utc)
    encerrada = status == "encerrada"
    sessao = SessaoTrabalho(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        demanda_id=demanda_id or str(uuid.uuid4()),
        usuario_id=usuario.id if usuario else None,
        departamento_id=departamento.id if departamento else None,
        evento_inicio_id=str(uuid.uuid4()),
        evento_fim_id=str(uuid.uuid4()) if encerrada else None,
        status="ativa" if status == "cancelada" else status,
        created_at=criada,
        updated_at=criada,
        inicio_em=inicio,
        fim_em=agora_db if encerrada else None,
        duracao_segundos=300 if encerrada else None,
    )
    db.add(sessao)
    db.flush()
    if status == "cancelada":
        sessao.status = "cancelada"
        sessao.duracao_segundos = 999
        db.flush()
    return sessao


def _url(**params: str | None) -> str:
    consulta = {chave: valor for chave, valor in params.items() if valor is not None}
    return "/sessoes-trabalho/trafego/carga" + (f"?{urlencode(consulta)}" if consulta else "")


def _carga(app, token: str, **params: str | None) -> dict:
    resposta = get(TestClient(app), _url(**params), token=token)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _resumo(itens: list[dict]) -> list[tuple]:
    return [(i["nome"], i["sessoesAtivas"], i["demandasDistintas"], i["tempoAtivoTotalSegundos"]) for i in itens]


VAZIO = {"usuarios": [], "departamentos": [], "equipes": []}


# --------------------------------------------------------------------------------------
# RBAC / tenant / validação
# --------------------------------------------------------------------------------------

def test_admin_e_gestor_acessam(app, token_admin: str, token_gestor: str) -> None:
    assert get(TestClient(app), _url(), token=token_admin).status_code == 200
    assert get(TestClient(app), _url(), token=token_gestor).status_code == 200


def test_operador_e_403(app, token_operador: str) -> None:
    assert get(TestClient(app), _url(), token=token_operador).status_code == 403


def test_sem_token_e_401(app) -> None:
    assert get(TestClient(app), _url()).status_code == 401


def test_tenant_isolado(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, token_admin: str) -> None:
    alheio = _usuario(db_session, outra_empresa)
    _sessao(db_session, outra_empresa, decorrido=500, usuario=alheio, departamento=_departamento(db_session, outra_empresa))
    _equipe(db_session, outra_empresa, "Alheia", [alheio])
    assert _carga(app, token_admin) == VAZIO


def test_ids_invalidos_sao_422(app, token_admin: str) -> None:
    assert get(TestClient(app), _url(usuarioIds="nao-uuid"), token=token_admin).status_code == 422
    assert get(TestClient(app), _url(departamentoIds=f"{uuid.uuid4()},x"), token=token_admin).status_code == 422


# --------------------------------------------------------------------------------------
# Universo
# --------------------------------------------------------------------------------------

def test_vazio(app, token_admin: str) -> None:
    assert _carga(app, token_admin) == VAZIO


def test_so_sessoes_ativas_contam(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    usuario = _usuario(db_session, empresa, "Ana")
    _sessao(db_session, empresa, decorrido=100, usuario=usuario)
    _sessao(db_session, empresa, status="encerrada", usuario=usuario)
    _sessao(db_session, empresa, status="cancelada", usuario=usuario)

    assert _resumo(_carga(app, token_admin)["usuarios"]) == [("Ana", 1, 1, 100)]


def test_ativa_antiga_conta_sem_filtro_de_periodo(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """A carga nunca olhou período: uma ativa de 3 dias conta integralmente."""
    usuario = _usuario(db_session, empresa, "Bia")
    _sessao(db_session, empresa, decorrido=3 * 24 * 3600, usuario=usuario)
    assert _resumo(_carga(app, token_admin)["usuarios"]) == [("Bia", 1, 1, 3 * 24 * 3600)]


def test_status_e_periodo_da_tela_nao_afetam_a_carga(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """No cliente as ativas eram buscadas sempre e os rankings só olhavam `ativasFiltradas`:
    `status` e `periodo` nunca mudaram a carga — e o endpoint nem os aceita (parâmetros
    desconhecidos são ignorados)."""
    usuario = _usuario(db_session, empresa, "Caio")
    _sessao(db_session, empresa, decorrido=200, usuario=usuario)
    base = _carga(app, token_admin)
    assert _carga(app, token_admin, status="encerrada", periodoInicio="2030-01-01T00:00:00Z") == base
    assert _carga(app, token_admin, status="ativa") == base


# --------------------------------------------------------------------------------------
# Usuários
# --------------------------------------------------------------------------------------

def test_carga_por_usuario_calculada_a_mao(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """u1: duas ativas (600s em A, 300s em B) → 2 sessões, 2 demandas, 900s.
    u2: uma ativa (1000s) → 1 sessão, 1 demanda, 1000s. Maior carga primeiro: u2, u1."""
    u1, u2 = _usuario(db_session, empresa, "Usuário Um"), _usuario(db_session, empresa, "Usuário Dois")
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    _sessao(db_session, empresa, decorrido=600, usuario=u1, demanda_id=a)
    _sessao(db_session, empresa, decorrido=300, usuario=u1, demanda_id=b)
    _sessao(db_session, empresa, decorrido=1000, usuario=u2)

    assert _resumo(_carga(app, token_admin)["usuarios"]) == [("Usuário Dois", 1, 1, 1000), ("Usuário Um", 2, 2, 900)]


def test_demandas_distintas_nao_duplicam(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """Duas sessões ativas do mesmo usuário na MESMA demanda (uma por etapa, por exemplo) —
    não é possível pelo índice único usuário+demanda; com departamento sem usuário é: o grupo de
    departamento deve contar 1 demanda distinta para 2 sessões."""
    dep = _departamento(db_session, empresa, "Criação")
    demanda = str(uuid.uuid4())
    u1, u2 = _usuario(db_session, empresa), _usuario(db_session, empresa)
    _sessao(db_session, empresa, decorrido=100, usuario=u1, departamento=dep, demanda_id=demanda)
    _sessao(db_session, empresa, decorrido=200, usuario=u2, departamento=dep, demanda_id=demanda)
    assert _resumo(_carga(app, token_admin)["departamentos"]) == [("Criação", 2, 1, 300)]


def test_sessao_sem_usuario_fica_fora_do_ranking_de_usuarios(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    dep = _departamento(db_session, empresa, "Só Depto")
    _sessao(db_session, empresa, decorrido=400, departamento=dep)  # sem usuário

    corpo = _carga(app, token_admin)
    assert corpo["usuarios"] == []
    assert _resumo(corpo["departamentos"]) == [("Só Depto", 1, 1, 400)]


def test_usuario_inativo_continua_aparecendo(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """Nenhum filtro de status de usuário: vínculo histórico continua no ranking (o cliente
    resolvia o nome no diretório, que inclui inativos)."""
    inativo = _usuario(db_session, empresa, "Ex Colaborador", status="inativo")
    _sessao(db_session, empresa, decorrido=50, usuario=inativo)
    assert _resumo(_carga(app, token_admin)["usuarios"]) == [("Ex Colaborador", 1, 1, 50)]


def test_item_traz_id_e_nome(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    usuario = _usuario(db_session, empresa, "Dona Maria")
    _sessao(db_session, empresa, decorrido=10, usuario=usuario)
    item = _carga(app, token_admin)["usuarios"][0]
    assert item["id"] == usuario.id and item["nome"] == "Dona Maria"
    assert set(item) == {"id", "nome", "sessoesAtivas", "demandasDistintas", "tempoAtivoTotalSegundos"}


# --------------------------------------------------------------------------------------
# Departamentos
# --------------------------------------------------------------------------------------

def test_carga_por_departamento_usa_o_departamento_da_sessao(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """O departamento é o DA SESSÃO — não o do usuário (usuário sem departamento aqui)."""
    criacao, midia = _departamento(db_session, empresa, "Criação"), _departamento(db_session, empresa, "Mídia")
    u = _usuario(db_session, empresa)
    _sessao(db_session, empresa, decorrido=700, usuario=u, departamento=criacao)
    _sessao(db_session, empresa, decorrido=100, departamento=criacao)
    _sessao(db_session, empresa, decorrido=800, departamento=midia)
    _sessao(db_session, empresa, decorrido=999, usuario=u)  # sem departamento: fora do ranking

    # Empate em 800s: vem primeiro o grupo cuja sessão mais recente começou depois (Criação: 100s).
    assert _resumo(_carga(app, token_admin)["departamentos"]) == [("Criação", 2, 2, 800), ("Mídia", 1, 1, 800)]


# --------------------------------------------------------------------------------------
# Equipes — regra: primeira equipe (por nome) que contém o usuário; sem duplicar
# --------------------------------------------------------------------------------------

def test_equipe_primeira_por_nome_sem_double_count(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """u1 está em "Alfa" E em "Beta": a sessão conta UMA vez, em "Alfa" (a primeira por nome —
    `equipes.find` sobre o diretório ordenado). u2 só em "Beta". u3 sem equipe: fora."""
    u1, u2, u3 = (_usuario(db_session, empresa) for _ in range(3))
    _equipe(db_session, empresa, "Beta", [u1, u2])
    _equipe(db_session, empresa, "Alfa", [u1])
    _sessao(db_session, empresa, decorrido=600, usuario=u1)
    _sessao(db_session, empresa, decorrido=100, usuario=u2)
    _sessao(db_session, empresa, decorrido=900, usuario=u3)

    equipes = _carga(app, token_admin)["equipes"]
    assert _resumo(equipes) == [("Alfa", 1, 1, 600), ("Beta", 1, 1, 100)]
    # prova explícita de que nada foi duplicado: 3 sessões, 2 com equipe → soma = 2, nunca 3 ou 4
    assert sum(e["sessoesAtivas"] for e in equipes) == 2


def test_equipe_com_varias_sessoes_e_membros_soma_corretamente(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    u1, u2 = _usuario(db_session, empresa), _usuario(db_session, empresa)
    _equipe(db_session, empresa, "Squad", [u1, u2])
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    _sessao(db_session, empresa, decorrido=100, usuario=u1, demanda_id=a)
    _sessao(db_session, empresa, decorrido=200, usuario=u1, demanda_id=b)
    _sessao(db_session, empresa, decorrido=300, usuario=u2, demanda_id=a)
    assert _resumo(_carga(app, token_admin)["equipes"]) == [("Squad", 3, 2, 600)]


def test_equipe_arquivada_ainda_conta_semantica_atual(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """O diretório do cliente INCLUI equipes arquivadas e `find` não filtra status: preservado."""
    u = _usuario(db_session, empresa)
    _equipe(db_session, empresa, "Antiga", [u], status="arquivado")
    _sessao(db_session, empresa, decorrido=60, usuario=u)
    assert _resumo(_carga(app, token_admin)["equipes"]) == [("Antiga", 1, 1, 60)]


def test_equipe_de_outra_empresa_nao_conta(app, db_session: Session, empresa: Empresa, outra_empresa: Empresa, token_admin: str) -> None:
    u = _usuario(db_session, empresa)
    _equipe(db_session, outra_empresa, "Alheia", [u])
    _sessao(db_session, empresa, decorrido=60, usuario=u)
    assert _carga(app, token_admin)["equipes"] == []


def test_usuario_sem_equipe_fica_fora_do_ranking_de_equipes(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    u = _usuario(db_session, empresa)
    _sessao(db_session, empresa, decorrido=60, usuario=u)
    corpo = _carga(app, token_admin)
    assert len(corpo["usuarios"]) == 1
    assert corpo["equipes"] == []


# --------------------------------------------------------------------------------------
# Filtros (mesmos de D3C1)
# --------------------------------------------------------------------------------------

def test_filtro_de_usuario_afeta_os_tres_rankings(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    u1, u2 = _usuario(db_session, empresa, "Um"), _usuario(db_session, empresa, "Dois")
    dep = _departamento(db_session, empresa, "Dep")
    _equipe(db_session, empresa, "Time", [u1, u2])
    _sessao(db_session, empresa, decorrido=100, usuario=u1, departamento=dep)
    _sessao(db_session, empresa, decorrido=500, usuario=u2, departamento=dep)

    corpo = _carga(app, token_admin, usuarioIds=u1.id)
    assert _resumo(corpo["usuarios"]) == [("Um", 1, 1, 100)]
    assert _resumo(corpo["departamentos"]) == [("Dep", 1, 1, 100)]
    assert _resumo(corpo["equipes"]) == [("Time", 1, 1, 100)]
    multi = _carga(app, token_admin, usuarioIds=f"{u1.id},{u2.id}")
    assert _resumo(multi["equipes"]) == [("Time", 2, 2, 600)]


def test_filtro_de_departamento_e_do_departamento_da_sessao(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    d1, d2 = _departamento(db_session, empresa, "D1"), _departamento(db_session, empresa, "D2")
    u = _usuario(db_session, empresa, "Pessoa")
    _sessao(db_session, empresa, decorrido=100, usuario=u, departamento=d1)
    _sessao(db_session, empresa, decorrido=700, usuario=u, departamento=d2)

    corpo = _carga(app, token_admin, departamentoIds=d1.id)
    assert _resumo(corpo["usuarios"]) == [("Pessoa", 1, 1, 100)]
    assert _resumo(corpo["departamentos"]) == [("D1", 1, 1, 100)]
    assert _resumo(_carga(app, token_admin, departamentoIds=f"{d1.id},{d2.id}")["departamentos"])[0][0] == "D2"


def test_filtro_de_demanda_com_acento_e_caixa(app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient) -> None:
    demanda = client_admin.post("/demandas", json={"nome": "Campanha Ação Social"}).json()
    u = _usuario(db_session, empresa, "Quem Casa")
    outro = _usuario(db_session, empresa, "Quem Não")
    _sessao(db_session, empresa, decorrido=100, usuario=u, demanda_id=demanda["id"])
    _sessao(db_session, empresa, decorrido=900, usuario=outro)

    assert _resumo(_carga(app, token_admin, demandaQuery="ACAO social")["usuarios"]) == [("Quem Casa", 1, 1, 100)]
    assert _carga(app, token_admin, demandaQuery="inexistente-zzz") == VAZIO
    assert len(_carga(app, token_admin, demandaQuery="   ")["usuarios"]) == 2  # só espaços = sem filtro


# --------------------------------------------------------------------------------------
# Ordenação
# --------------------------------------------------------------------------------------

def test_ordenacao_maior_carga_primeiro(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    for nome, decorrido in (("Baixa", 100), ("Alta", 3000), ("Média", 900)):
        _sessao(db_session, empresa, decorrido=decorrido, usuario=_usuario(db_session, empresa, nome))
    assert [i["nome"] for i in _carga(app, token_admin)["usuarios"]] == ["Alta", "Média", "Baixa"]


def test_empate_prefere_o_grupo_com_sessao_mais_recente(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """Totais iguais (600s). O cliente mantinha a ordem de primeira aparição na lista
    (`inicio_em DESC`): vem antes o grupo cuja sessão mais recente começou depois."""
    a, b = _usuario(db_session, empresa, "A"), _usuario(db_session, empresa, "B")
    _sessao(db_session, empresa, decorrido=600, usuario=a)                       # uma de 600s (início mais antigo)
    _sessao(db_session, empresa, decorrido=300, usuario=b)
    _sessao(db_session, empresa, decorrido=300, usuario=b)                       # duas de 300s (início mais novo)

    itens = _carga(app, token_admin)["usuarios"]
    assert [(i["nome"], i["tempoAtivoTotalSegundos"]) for i in itens] == [("B", 600), ("A", 600)]


def test_empate_total_desempata_por_created_at_e_depois_id(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    base = _agora_db(db_session) - timedelta(seconds=500)
    antigo, novo = _usuario(db_session, empresa, "Criado antes"), _usuario(db_session, empresa, "Criado depois")
    cedo = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _sessao(db_session, empresa, inicio_em=base, usuario=antigo, created_at=cedo)
    _sessao(db_session, empresa, inicio_em=base, usuario=novo, created_at=cedo + timedelta(hours=1))
    assert [i["nome"] for i in _carga(app, token_admin)["usuarios"]] == ["Criado depois", "Criado antes"]

    # tudo igual (início e criação): o id decide — determinístico entre execuções
    x, y = _usuario(db_session, empresa, "X"), _usuario(db_session, empresa, "Y")
    _sessao(db_session, empresa, inicio_em=base - timedelta(days=1), usuario=x, created_at=cedo)
    _sessao(db_session, empresa, inicio_em=base - timedelta(days=1), usuario=y, created_at=cedo)
    itens = _carga(app, token_admin)["usuarios"]
    empatados = [i for i in itens if i["nome"] in ("X", "Y")]
    assert [i["id"] for i in empatados] == sorted(i["id"] for i in empatados)
    assert _carga(app, token_admin) == _carga(app, token_admin)  # estável


# --------------------------------------------------------------------------------------
# Dataset > 100 — o que `limit=100` truncava
# --------------------------------------------------------------------------------------

def test_mais_de_100_sessoes_por_usuario(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """150 ativas em 5 usuários (30 cada, decorrido 10·(i+1) por sessão) → totais exatos
    300/600/900/1200/1500, 30 sessões e 30 demandas cada. Truncar em 100 mudaria tudo."""
    usuarios = [_usuario(db_session, empresa, f"U{i}") for i in range(5)]
    for i, usuario in enumerate(usuarios):
        for _ in range(30):
            _sessao(db_session, empresa, decorrido=10 * (i + 1), usuario=usuario)

    itens = _carga(app, token_admin)["usuarios"]
    assert _resumo(itens) == [(f"U{i}", 30, 30, 300 * (i + 1)) for i in (4, 3, 2, 1, 0)]
    assert sum(i["sessoesAtivas"] for i in itens) == 150


def test_mais_de_100_sessoes_por_departamento(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    """130 ativas em 4 departamentos (33/33/32/32), decorrido 100 cada → total = 100 × sessões."""
    deptos = [_departamento(db_session, empresa, f"Dep{i}") for i in range(4)]
    for n in range(130):
        _sessao(db_session, empresa, decorrido=100, departamento=deptos[n % 4])

    itens = _carga(app, token_admin)["departamentos"]
    assert sorted((i["nome"], i["sessoesAtivas"], i["tempoAtivoTotalSegundos"]) for i in itens) == [
        ("Dep0", 33, 3300), ("Dep1", 33, 3300), ("Dep2", 32, 3200), ("Dep3", 32, 3200),
    ]
    assert sum(i["sessoesAtivas"] for i in itens) == 130


def test_mais_de_100_sessoes_por_equipe_com_usuarios_em_varias_equipes(
    app, db_session: Session, empresa: Empresa, token_admin: str
) -> None:
    """120 ativas de 6 usuários (20 cada). u0..u2 estão em "Alfa" (e u2 também em "Zeta"),
    u3..u5 só em "Zeta". u2 conta para Alfa (primeira por nome), nunca para Zeta:
    Alfa = u0+u1+u2 = 60 sessões; Zeta = u3+u4+u5 = 60. Sem double-count: 120 no total."""
    u = [_usuario(db_session, empresa) for _ in range(6)]
    _equipe(db_session, empresa, "Zeta", [u[2], u[3], u[4], u[5]])
    _equipe(db_session, empresa, "Alfa", [u[0], u[1], u[2]])
    for usuario in u:
        for _ in range(20):
            _sessao(db_session, empresa, decorrido=10, usuario=usuario)

    equipes = _carga(app, token_admin)["equipes"]
    # empate de total (600s): a ordem é a regra de desempate já testada acima; aqui vale o conteúdo
    assert sorted(_resumo(equipes)) == [("Alfa", 60, 60, 600), ("Zeta", 60, 60, 600)]
    assert sum(e["sessoesAtivas"] for e in equipes) == 120


# --------------------------------------------------------------------------------------
# Performance — nº de consultas NÃO cresce com o nº de grupos
# --------------------------------------------------------------------------------------

def _contar_consultas_a_sessoes(app, db_session: Session, token: str) -> int:
    chamadas: list[str] = []

    def _contar(conn, cursor, statement, parameters, context, executemany):
        if "sessoes_trabalho" in statement:
            chamadas.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", _contar)
    try:
        resposta = get(TestClient(app), _url(), token=token)
    finally:
        event.remove(engine, "before_cursor_execute", _contar)
    assert resposta.status_code == 200, resposta.text
    return len(chamadas)


def test_numero_de_consultas_nao_cresce_com_o_numero_de_grupos(app, db_session: Session, empresa: Empresa, token_admin: str) -> None:
    for i in range(3):
        usuario, dep = _usuario(db_session, empresa), _departamento(db_session, empresa)
        _equipe(db_session, empresa, f"E{i}", [usuario])
        _sessao(db_session, empresa, decorrido=10, usuario=usuario, departamento=dep)
    com_poucos = _contar_consultas_a_sessoes(app, db_session, token_admin)

    for i in range(3, 30):
        usuario, dep = _usuario(db_session, empresa), _departamento(db_session, empresa)
        _equipe(db_session, empresa, f"E{i}", [usuario])
        _sessao(db_session, empresa, decorrido=10, usuario=usuario, departamento=dep)
    com_muitos = _contar_consultas_a_sessoes(app, db_session, token_admin)

    assert com_poucos == com_muitos == 3  # uma agregação por ranking, não por grupo


# --------------------------------------------------------------------------------------
# PARIDADE com o cálculo que o cliente fazia (filterSessoes + buildCarga + buildCargaEquipe)
# --------------------------------------------------------------------------------------

def _normalizar_cliente(valor: str) -> str:
    decomposto = unicodedata.normalize("NFD", valor.lower())
    return "".join(c for c in decomposto if not 0x300 <= ord(c) <= 0x36F)


def _referencia_cliente(sessoes: list[dict], equipes: list[dict], filtros: dict) -> dict:
    """Port literal de `filterSessoes` + `buildCarga` (usuário/departamento) +
    `buildCargaEquipe` (frontend/src/lib/trafego.ts), sobre o que `TrafegoView` carregava:
    as ATIVAS, na ordem da API (`inicio_em DESC, created_at DESC`). `equipes` = diretório
    (ordenado por nome, arquivadas incluídas)."""
    ativas = sorted(
        (s for s in sessoes if s["status"] == "ativa"),
        key=lambda s: (s["inicio"], s["created"]),
        reverse=True,
    )

    def passa(s: dict) -> bool:
        usuario_ok = not filtros["usuarios"] or (s["usuario"] is not None and s["usuario"] in filtros["usuarios"])
        depto_ok = not filtros["departamentos"] or (s["departamento"] is not None and s["departamento"] in filtros["departamentos"])
        consulta = filtros["demanda_query"]
        demanda_ok = True
        if consulta.strip():
            nome = f"#{s['numero']} — {s['nome']}" if s["numero"] is not None else s["demanda"]
            demanda_ok = _normalizar_cliente(consulta) in _normalizar_cliente(f"{s['demanda']} {nome}")
        return usuario_ok and depto_ok and demanda_ok

    filtradas = [s for s in ativas if passa(s)]

    def agrupar(chave) -> list[tuple]:
        grupos: dict[str, list[dict]] = {}
        for s in filtradas:
            k = chave(s)
            if k is None:
                continue
            grupos.setdefault(k, []).append(s)  # dict preserva a ordem de primeira aparição (Map do JS)
        itens = [
            (k, len(g), len({x["demanda"] for x in g}), sum(x["decorrido"] for x in g)) for k, g in grupos.items()
        ]
        return sorted(itens, key=lambda it: -it[3])  # sort estável: empate mantém a primeira aparição

    def equipe_da_sessao(s: dict):
        if s["usuario"] is None:
            return None
        return next((e["id"] for e in equipes if s["usuario"] in e["membros"]), None)

    return {
        "usuarios": agrupar(lambda s: s["usuario"]),
        "departamentos": agrupar(lambda s: s["departamento"]),
        "equipes": agrupar(equipe_da_sessao),
    }


def test_paridade_com_o_calculo_do_cliente(
    app, db_session: Session, empresa: Empresa, token_admin: str, client_admin: TestClient
) -> None:
    usuarios = [_usuario(db_session, empresa, f"Pessoa {i}") for i in range(6)]
    deptos = [_departamento(db_session, empresa, f"Setor {i}") for i in range(3)]
    demandas = [client_admin.post("/demandas", json={"nome": nome}).json() for nome in ("Banner Verão", "Relatório Ação", "Vídeo")]
    # diretório de equipes (ordem do diretório = nome ASC); u1 está em duas, u5 em nenhuma, uma arquivada
    equipes_ref = [
        {"obj": _equipe(db_session, empresa, "Alfa", [usuarios[0], usuarios[1]]), "membros": {usuarios[0].id, usuarios[1].id}},
        {"obj": _equipe(db_session, empresa, "Beta", [usuarios[1], usuarios[2], usuarios[3]]), "membros": {usuarios[1].id, usuarios[2].id, usuarios[3].id}},
        {"obj": _equipe(db_session, empresa, "Gama", [usuarios[3], usuarios[4]], status="arquivado"), "membros": {usuarios[3].id, usuarios[4].id}},
    ]
    equipes_dir = [{"id": e["obj"].id, "membros": e["membros"]} for e in sorted(equipes_ref, key=lambda e: e["obj"].nome)]
    agora_db = _agora_db(db_session)
    base_criacao = datetime(2026, 1, 1, tzinfo=timezone.utc)

    registros: list[dict] = []
    plano = [  # (decorrido, usuário, departamento, índice da demanda ou None, status)
        (900, 0, 0, 0, "ativa"), (300, 0, 1, 1, "ativa"), (1200, 1, 0, 2, "ativa"), (50, 1, None, None, "ativa"),
        (700, 2, 1, 0, "ativa"), (700, 3, 2, 1, "ativa"), (10, 4, 2, 2, "ativa"), (2000, None, 0, None, "ativa"),
        (400, 5, None, 0, "ativa"), (123, 3, 1, None, "ativa"),
        (500, 0, 0, 0, "encerrada"), (777, 2, 2, 1, "cancelada"),
    ]
    for i, (decorrido, u, d, dem, status) in enumerate(plano):
        demanda_id = demandas[dem]["id"] if dem is not None else str(uuid.uuid4())
        criada = base_criacao + timedelta(minutes=i)
        _sessao(
            db_session, empresa, status=status, decorrido=decorrido,
            usuario=usuarios[u] if u is not None else None, departamento=deptos[d] if d is not None else None,
            demanda_id=demanda_id, created_at=criada,
        )
        registros.append({
            "status": "ativa" if status == "ativa" else status, "decorrido": decorrido,
            "inicio": agora_db - timedelta(seconds=decorrido), "created": criada,
            "usuario": usuarios[u].id if u is not None else None, "departamento": deptos[d].id if d is not None else None,
            "demanda": demanda_id,
            "numero": demandas[dem]["numeroOperacional"] if dem is not None else None,
            "nome": demandas[dem]["nome"] if dem is not None else None,
        })

    casos = [
        {"usuarios": [], "departamentos": [], "demanda_query": ""},
        {"usuarios": [usuarios[0].id], "departamentos": [], "demanda_query": ""},
        {"usuarios": [usuarios[1].id, usuarios[3].id], "departamentos": [], "demanda_query": ""},
        {"usuarios": [], "departamentos": [deptos[0].id], "demanda_query": ""},
        {"usuarios": [], "departamentos": [deptos[1].id, deptos[2].id], "demanda_query": ""},
        {"usuarios": [], "departamentos": [], "demanda_query": "acao"},
        {"usuarios": [], "departamentos": [], "demanda_query": f"#{demandas[0]['numeroOperacional']}"},
        {"usuarios": [usuarios[0].id, usuarios[2].id], "departamentos": [deptos[0].id, deptos[1].id], "demanda_query": "banner"},
        {"usuarios": [], "departamentos": [], "demanda_query": "nada-casa"},
    ]
    nomes = {u.id: u.nome for u in usuarios} | {d.id: d.nome for d in deptos} | {e["obj"].id: e["obj"].nome for e in equipes_ref}
    for caso in casos:
        servidor = _carga(
            app, token_admin,
            usuarioIds=",".join(caso["usuarios"]) or None,
            departamentoIds=",".join(caso["departamentos"]) or None,
            demandaQuery=caso["demanda_query"] or None,
        )
        referencia = _referencia_cliente(registros, equipes_dir, caso)
        for ranking in ("usuarios", "departamentos", "equipes"):
            esperado = [(nomes[k], n, dem, tempo) for (k, n, dem, tempo) in referencia[ranking]]
            assert _resumo(servidor[ranking]) == esperado, f"{ranking} divergiu em {caso}"
