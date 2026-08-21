"""Demanda — a unidade de trabalho da operação (Fase 2E.1).

Cobre CRUD, arquivamento, vínculos N:N, isolamento por empresa, busca, expediente e bloqueio.

Duas seções merecem atenção por serem exclusivas deste domínio:

**Numeração dupla** — `codigo_referencia` (T26000001, anual) e `numero_operacional` (2063,
contínuo) são emitidos na mesma transação por contadores independentes. Os testes provam a
independência, o rollback conjunto e o comportamento sob concorrência.

**Escopo** — Demanda é o primeiro domínio operacional: ao contrário dos cadastros, é lida por
qualquer autenticado, e o que cada um enxerga é decidido no servidor. Os testes cobrem a
listagem *e* o acesso direto por UUID, que é onde um escopo aplicado só na lista deixaria
passar tudo.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, time, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.expediente import JanelaDia, RegraExpediente, esta_dentro_expediente
from app.models.cliente import Cliente
from app.models.demanda import Demanda
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.usuario import Usuario


# --------------------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------------------

def _cliente(db: Session, empresa: Empresa, *, responsavel_comercial_id: str | None = None) -> Cliente:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    cliente = Cliente(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"cli-{sufixo}",
        codigo_referencia=f"C26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Cliente {sufixo}",
        nome_normalizado=f"cliente {sufixo}",
        tipo_documento="cnpj",
        status="ativo",
        cor_identificacao="blue",
        responsavel_comercial_id=responsavel_comercial_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(cliente)
    db.flush()
    return cliente


def _departamento(
    db: Session, empresa: Empresa, *, nome: str | None = None, responsavel_usuario_id: str | None = None
) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    nome_final = nome or f"Departamento {sufixo}"
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=nome_final,
        nome_normalizado=nome_final.lower(),
        cor_identificacao="blue",
        status="ativo",
        responsavel_usuario_id=responsavel_usuario_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _payload(**extra) -> dict:
    return {"nome": f"Demanda {uuid.uuid4().hex[:8]}", **extra}


def _criar(client: TestClient, **extra) -> dict:
    resposta = client.post("/demandas", json=_payload(**extra))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _regra_todos_os_dias(
    *, manha_inicio: str, manha_fim: str, tarde_inicio: str, tarde_fim: str, tolerancia_retomada_minutos: int = 0
) -> RegraExpediente:
    """Mesma janela nos 7 dias — usado pelos overrides de teste (`dentro_do_expediente`/
    `fora_do_expediente`), que precisam funcionar não importa em qual dia da semana a suíte
    rodar (ver docstring de `dentro_do_expediente`)."""
    janela = JanelaDia(
        ativo=True, manha_inicio=manha_inicio, manha_fim=manha_fim, tarde_inicio=tarde_inicio, tarde_fim=tarde_fim
    )
    return RegraExpediente(
        ativo=True,
        tolerancia_retomada_minutos=tolerancia_retomada_minutos,
        dias={dia: janela for dia in range(7)},
    )


@pytest.fixture()
def dentro_do_expediente(app):
    """Fixa uma janela 00:00–23:59 nos 7 dias para o teste não depender da hora (nem do dia
    da semana) da máquina.

    Sem isto, a suíte passaria de manhã e falharia às 20h (ou num sábado) — e o motivo da
    falha não teria relação nenhuma com o que o teste afirma.
    """
    from app.api.routes import demandas as rotas

    original = rotas.demanda_service.regra_expediente
    rotas.demanda_service.regra_expediente = _regra_todos_os_dias(
        manha_inicio="00:00", manha_fim="12:00", tarde_inicio="12:00", tarde_fim="23:59"
    )
    yield
    rotas.demanda_service.regra_expediente = original


@pytest.fixture()
def fora_do_expediente(app):
    """Janela impossível de estar dentro em nenhum dos 7 dias — qualquer hora fica fora."""
    from app.api.routes import demandas as rotas

    original = rotas.demanda_service.regra_expediente
    rotas.demanda_service.regra_expediente = _regra_todos_os_dias(
        manha_inicio="00:00", manha_fim="00:00", tarde_inicio="00:00", tarde_fim="00:00"
    )
    yield
    rotas.demanda_service.regra_expediente = original


# --------------------------------------------------------------------------------------
# Numeração dupla
# --------------------------------------------------------------------------------------

def test_primeira_demanda_recebe_os_dois_numeros(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    assert criada["codigoReferencia"].startswith("T")
    assert criada["anoReferencia"] >= 2026
    assert criada["sequencialReferencia"] == 1
    # Base sem semente começa em 1; o número de go-live entra pelo CLI.
    assert criada["numeroOperacional"] == 1


def test_os_dois_contadores_sao_independentes(client_admin: TestClient, db_session: Session, empresa) -> None:
    """O código de referência reinicia por ano; o operacional não. Provar a independência é o
    ponto: se um derivasse do outro, semear o operacional mexeria no código oficial."""
    # Semeia o contador operacional em 2062 ANTES de qualquer demanda.
    db_session.execute(
        text(
            "INSERT INTO sequencias_operacionais "
            "(id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at) "
            "VALUES (:id, :e, 'demanda', 2062, now(), now())"
        ),
        {"id": str(uuid.uuid4()), "e": empresa.id},
    )
    db_session.flush()

    criada = _criar(client_admin)
    assert criada["numeroOperacional"] == 2063, "operacional deve continuar de onde o CLI parou"
    assert criada["sequencialReferencia"] == 1, "o código oficial NÃO é afetado pela semente"
    assert criada["codigoReferencia"].endswith("000001")


def test_numeros_avancam_em_sequencia(client_admin: TestClient) -> None:
    primeira, segunda, terceira = (_criar(client_admin) for _ in range(3))
    assert [d["numeroOperacional"] for d in (primeira, segunda, terceira)] == [1, 2, 3]
    assert [d["sequencialReferencia"] for d in (primeira, segunda, terceira)] == [1, 2, 3]


def test_falha_na_criacao_nao_queima_nenhum_dos_dois_numeros(test_engine) -> None:
    """Os dois contadores são reservados na MESMA transação: se a criação falhar, AMBOS voltam.
    Um número queimado é um buraco permanente na numeração da operação.

    Usa conexão própria, fora do savepoint do `db_session`, pelo mesmo motivo de
    `test_rollback_desfaz_o_incremento_sem_queimar_numero`: só um rollback completo e real
    mostra o efeito. Pela API não daria — o rollback do service desfaria o savepoint que
    sustenta as próprias fixtures do teste.
    """
    from sqlalchemy.orm import Session as SessionRaw

    from app.core.referencias import gerar_proxima_referencia
    from app.core.sequencias_operacionais import reservar_proximo_operacional

    empresa_id = str(uuid.uuid4())
    with SessionRaw(bind=test_engine) as setup:
        setup.execute(
            text(
                "INSERT INTO empresas (id, nome, documento, codigo_interno, status, created_at, updated_at) "
                "VALUES (:id, 'Empresa Rollback', NULL, :ci, 'ativa', now(), now())"
            ),
            {"id": empresa_id, "ci": f"ROLL-{uuid.uuid4().hex[:8]}".upper()},
        )
        setup.commit()

    try:
        with SessionRaw(bind=test_engine) as sessao:
            gerar_proxima_referencia(sessao, empresa_id=empresa_id, tipo_entidade="tarefa", ano=2026)
            reservar_proximo_operacional(sessao, empresa_id=empresa_id, tipo_entidade="demanda")
            sessao.rollback()  # simula a falha depois das duas reservas

        with SessionRaw(bind=test_engine) as sessao:
            referencia = gerar_proxima_referencia(
                sessao, empresa_id=empresa_id, tipo_entidade="tarefa", ano=2026
            )
            operacional = reservar_proximo_operacional(
                sessao, empresa_id=empresa_id, tipo_entidade="demanda"
            )
            sessao.commit()

        assert referencia.sequencial_referencia == 1, "o código oficial não pode ter sido queimado"
        assert operacional == 1, "o número operacional não pode ter sido queimado"
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            for tabela in ("sequencias_referencia", "sequencias_operacionais"):
                limpeza.execute(text(f"DELETE FROM {tabela} WHERE empresa_id = :e"), {"e": empresa_id})
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()


def test_criacao_invalida_devolve_422_sem_persistir(client_admin: TestClient) -> None:
    """O outro lado do teste acima, pela API: a tentativa falha e nada é criado."""
    resposta = client_admin.post(
        "/demandas", json=_payload(usuarioResponsavelIds=[str(uuid.uuid4())])
    )
    assert resposta.status_code == 422, resposta.text


def test_concorrencia_nao_gera_numero_operacional_duplicado(test_engine, empresa) -> None:
    """Threads com conexões próprias, cada uma commitando — o ON CONFLICT serializa pelo lock
    da linha do contador."""
    from sqlalchemy.orm import Session as SessionRaw

    from app.core.sequencias_operacionais import reservar_proximo_operacional

    total = 8
    obtidos: list[int] = []
    trava = threading.Lock()
    barreira = threading.Barrier(total)
    empresa_id = empresa.id

    with SessionRaw(bind=test_engine) as setup:
        setup.execute(
            text(
                "INSERT INTO empresas (id, nome, documento, codigo_interno, status, created_at, updated_at) "
                "VALUES (:id, 'Empresa Concorrencia', NULL, :ci, 'ativa', now(), now())"
            ),
            {"id": (empresa_id := str(uuid.uuid4())), "ci": f"CONC-{uuid.uuid4().hex[:8]}".upper()},
        )
        setup.commit()

    def reservar() -> None:
        with SessionRaw(bind=test_engine) as sessao:
            barreira.wait()
            numero = reservar_proximo_operacional(
                sessao, empresa_id=empresa_id, tipo_entidade="demanda"
            )
            sessao.commit()
        with trava:
            obtidos.append(numero)

    threads = [threading.Thread(target=reservar) for _ in range(total)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(obtidos) == list(range(1, total + 1)), f"números duplicados/faltando: {obtidos}"
    finally:
        with SessionRaw(bind=test_engine) as limpeza:
            limpeza.execute(
                text("DELETE FROM sequencias_operacionais WHERE empresa_id = :e"), {"e": empresa_id}
            )
            limpeza.execute(text("DELETE FROM empresas WHERE id = :e"), {"e": empresa_id})
            limpeza.commit()


def test_uuid_nunca_aparece_como_rotulo(client_admin: TestClient) -> None:
    """O UUID existe na resposta (é a chave das rotas), mas quem identifica a demanda para a
    operação é `numeroOperacional`; `codigoReferencia` é a identidade oficial."""
    criada = _criar(client_admin)
    assert criada["id"] != criada["codigoReferencia"]
    assert isinstance(criada["numeroOperacional"], int)


# --------------------------------------------------------------------------------------
# Contrato transitório — os campos sem tabela
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "campo, valor",
    [
        ("workflowEtapas", [{"id": "x", "nome": "Etapa"}]),
        ("etapaAtualId", "alguma-etapa"),
        ("checklist", [{"id": "c1", "texto": "item"}]),
        ("arquivos", [{"id": "a1", "nome": "brief.pdf"}]),
        ("comentarios", [{"id": "m1", "texto": "oi"}]),
        ("historico", [{"id": "h1", "acao": "criou"}]),
    ],
)
def test_campo_sem_persistencia_e_recusado_na_criacao(
    client_admin: TestClient, campo: str, valor
) -> None:
    """422, nunca aceite-e-descarte.

    O formulário monta `workflowEtapas` a partir do modelo de workflow. Aceitar em silêncio
    faria a demanda ser criada e as etapas sumirem sem aviso — a falha silenciosa que este
    desenho existe para evitar.
    """
    resposta = client_admin.post("/demandas", json=_payload(**{campo: valor}))
    assert resposta.status_code == 422, resposta.text


def test_campo_sem_persistencia_e_recusado_na_edicao(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"checklist": []})
    assert resposta.status_code == 422, resposta.text


def test_leitura_devolve_colecoes_vazias_e_etapa_nula(client_admin: TestClient) -> None:
    """Vazio é a verdade: não há linha em tabela nenhuma. Devolvido só para os componentes não
    quebrarem — não para simular conteúdo.

    `checklist`/`arquivos` (2E.3) e `comentarios`/`historico` (2E.4) NÃO entram neste loop:
    saíram de `DemandaRead`, têm endpoint dedicado agora — ver test_demanda_checklist.py,
    test_demanda_arquivos.py, test_demanda_comentario.py, test_demanda_historico.py."""
    criada = _criar(client_admin)
    for campo in ("checklist", "arquivos", "comentarios", "historico"):
        assert campo not in criada
    assert criada["workflowEtapas"] == []
    assert criada["etapaAtualId"] is None


def test_campo_emitido_pelo_servidor_e_recusado(client_admin: TestClient) -> None:
    for campo, valor in (
        ("numeroOperacional", 9999),
        ("codigoReferencia", "T26000999"),
        ("empresaId", str(uuid.uuid4())),
        ("codigoInterno", "#2001"),
    ):
        resposta = client_admin.post("/demandas", json=_payload(**{campo: valor}))
        assert resposta.status_code == 422, f"{campo}: {resposta.text}"


def test_criar_com_todos_os_campos_validos_nao_perde_nada(
    client_admin: TestClient, db_session: Session, empresa, usuario_operador: Usuario
) -> None:
    cliente = _cliente(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    criada = _criar(
        client_admin,
        pit="PIT-42",
        briefing="Briefing completo",
        prioridade="alta",
        sinalizada=True,
        clienteId=str(cliente.id),
        dataInicio="2026-08-10",
        dataFimPrevista="2026-08-20",
        prazoEtapaAtual="2026-08-15T14:00:00Z",
        usuarioResponsavelIds=[str(usuario_operador.id)],
        departamentoResponsavelIds=[str(departamento.id)],
    )
    assert criada["pit"] == "PIT-42"
    assert criada["briefing"] == "Briefing completo"
    assert criada["prioridade"] == "alta"
    assert criada["sinalizada"] is True
    assert criada["clienteId"] == str(cliente.id)
    assert criada["usuarioResponsavelIds"] == [str(usuario_operador.id)]
    assert criada["departamentoResponsavelIds"] == [str(departamento.id)]
    assert criada["prazoEtapaAtual"] is not None


def test_data_fim_prevista_e_data_pura(client_admin: TestClient) -> None:
    """Documenta o contrato pós Fase 2F.1: `dataFimPrevista` é `DATE`, não timestamp —
    diferente de `prazoEtapaAtual` (datetime com fuso, ver teste acima). Hora não-zero é
    422 (`date_from_datetime_inexact`); ausência é aceita e devolvida como `None`."""
    resposta = client_admin.post("/demandas", json=_payload(dataFimPrevista="2026-08-20T14:30:00"))
    assert resposta.status_code == 422, resposta.text

    criada = _criar(client_admin)
    assert criada["dataFimPrevista"] is None


# --------------------------------------------------------------------------------------
# Escopo — listagem
# --------------------------------------------------------------------------------------

def test_admin_e_gestor_enxergam_a_empresa(
    client_admin: TestClient, client_gestor: TestClient
) -> None:
    _criar(client_admin)
    _criar(client_admin)
    assert len(client_gestor.get("/demandas").json()) == 2


def test_operador_so_enxerga_as_demandas_de_que_e_responsavel(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    _criar(client_admin)  # de outra pessoa

    achados = client_operador.get("/demandas").json()
    assert [d["id"] for d in achados] == [minha["id"]]


def test_operador_enxerga_as_do_proprio_departamento(
    client_admin: TestClient,
    client_operador: TestClient,
    db_session: Session,
    empresa,
    usuario_operador: Usuario,
) -> None:
    departamento = _departamento(db_session, empresa)
    usuario_operador.departamento_id = departamento.id
    db_session.flush()

    do_departamento = _criar(client_admin, departamentoResponsavelIds=[str(departamento.id)])
    _criar(client_admin)

    achados = client_operador.get("/demandas").json()
    assert [d["id"] for d in achados] == [do_departamento["id"]]


def test_listagem_sem_parametro_ja_vem_escopada(
    client_admin: TestClient, client_operador: TestClient
) -> None:
    """A garantia central: não existe caminho que devolva mais do que o escopo-base."""
    _criar(client_admin)
    _criar(client_admin)
    assert client_operador.get("/demandas").json() == []


def test_operador_sem_vinculo_recebe_lista_vazia_e_nao_erro(client_operador: TestClient) -> None:
    """Ausência de vínculo não é falta de permissão — 200 com lista vazia é a resposta certa."""
    resposta = client_operador.get("/demandas")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_operador_criador_sem_vinculo_perde_a_demanda_de_vista(client_operador: TestClient) -> None:
    """DESVIO CONHECIDO, fixado aqui de propósito para ficar visível.

    A tabela de escopo aprovada define `operador` como *responsável OU departamento*;
    `criado_por` entra apenas no escopo de Atendimento. A consequência é que um operador sem
    departamento que cria uma demanda **sem se atribuir** recebe 201 e, no instante seguinte,
    404 no mesmo id.

    Isto é o que a regra aprovada diz — não um bug de implementação. Está pinado para que
    qualquer mudança de comportamento seja deliberada, e para alimentar a decisão da 2E.5
    sobre incluir `criado_por` no escopo-base de todo mundo.
    """
    criada = client_operador.post("/demandas", json={"nome": "Criada pelo operador"})
    assert criada.status_code == 201

    assert client_operador.get("/demandas").json() == []
    assert client_operador.get(f"/demandas/{criada.json()['id']}").status_code == 404


def test_escopo_meus_e_sempre_permitido(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    _criar(client_admin)
    achados = client_operador.get("/demandas?escopo=meus").json()
    assert [d["id"] for d in achados] == [minha["id"]]


def test_escopo_meu_departamento_sem_ser_head_devolve_403(client_operador: TestClient) -> None:
    """403 e NÃO lista vazia: lista vazia esconderia o erro de permissão."""
    resposta = client_operador.get("/demandas?escopo=meu-departamento")
    assert resposta.status_code == 403, resposta.text


def test_head_acessa_o_escopo_do_departamento(
    client_admin: TestClient,
    client_operador: TestClient,
    db_session: Session,
    empresa,
    usuario_operador: Usuario,
) -> None:
    """Head resolvido por relação REAL (`responsavel_usuario_id`), nunca por filtro no cliente."""
    departamento = _departamento(db_session, empresa, responsavel_usuario_id=usuario_operador.id)
    db_session.flush()

    do_departamento = _criar(client_admin, departamentoResponsavelIds=[str(departamento.id)])
    _criar(client_admin)

    achados = client_operador.get("/demandas?escopo=meu-departamento").json()
    assert [d["id"] for d in achados] == [do_departamento["id"]]


def test_escopo_atendimento_sem_ser_do_atendimento_devolve_403(client_operador: TestClient) -> None:
    resposta = client_operador.get("/demandas?escopo=atendimento")
    assert resposta.status_code == 403, resposta.text


def test_atendimento_soma_criador_responsavel_e_clientes(
    client_admin: TestClient,
    client_operador: TestClient,
    db_session: Session,
    empresa,
    usuario_operador: Usuario,
) -> None:
    """Regra TRANSITÓRIA: "ser do Atendimento" é inferido pelo nome do departamento."""
    atendimento = _departamento(db_session, empresa, nome="Atendimento")
    usuario_operador.departamento_id = atendimento.id
    cliente = _cliente(db_session, empresa, responsavel_comercial_id=usuario_operador.id)
    db_session.flush()

    do_cliente = _criar(client_admin, clienteId=str(cliente.id))
    _criar(client_admin)

    achados = client_operador.get("/demandas?escopo=atendimento").json()
    assert do_cliente["id"] in [d["id"] for d in achados]


# --------------------------------------------------------------------------------------
# Escopo — acesso direto por UUID (a garantia exigida)
# --------------------------------------------------------------------------------------

def test_get_por_uuid_fora_do_escopo_devolve_404(
    client_admin: TestClient, client_operador: TestClient
) -> None:
    """Mesmo tenant + UUID conhecido NÃO é autorização.

    404 e não 403: um 403 confirmaria que o registro existe, e a quem pedisse bastaria variar
    o UUID para mapear a base.
    """
    alheia = _criar(client_admin)
    resposta = client_operador.get(f"/demandas/{alheia['id']}")
    assert resposta.status_code == 404, resposta.text


def test_patch_por_uuid_fora_do_escopo_devolve_404_e_nao_altera(
    client_admin: TestClient, client_operador: TestClient, db_session: Session
) -> None:
    """A resolução escopada acontece ANTES de qualquer escrita."""
    alheia = _criar(client_admin)
    nome_original = alheia["nome"]

    resposta = client_operador.patch(f"/demandas/{alheia['id']}", json={"nome": "Invadida"})
    assert resposta.status_code == 404, resposta.text

    persistida = db_session.get(Demanda, alheia["id"])
    db_session.refresh(persistida)
    assert persistida.nome == nome_original, "nada pode ter sido persistido"


def test_get_por_uuid_dentro_do_escopo_funciona(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    resposta = client_operador.get(f"/demandas/{minha['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["id"] == minha["id"]


def test_diretorio_tambem_e_escopado(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """Um diretório que ignorasse o escopo devolveria o nome de toda demanda da empresa —
    reabrindo por uma porta lateral o que o acesso por UUID fecha na principal."""
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    _criar(client_admin)

    achados = client_operador.get("/demandas/diretorio").json()
    assert [d["id"] for d in achados] == [minha["id"]]
    assert "numeroOperacional" in achados[0]


def test_demanda_de_outra_empresa_devolve_404(
    client_admin: TestClient, db_session: Session
) -> None:
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

    intrusa = Demanda(
        id=str(uuid.uuid4()),
        empresa_id=outra.id,
        codigo_referencia="T26000001",
        ano_referencia=26,
        sequencial_referencia=1,
        numero_operacional=1,
        nome="Demanda de outra empresa",
        status="rascunho",
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db_session.add(intrusa)
    db_session.flush()

    assert client_admin.get(f"/demandas/{intrusa.id}").status_code == 404


# --------------------------------------------------------------------------------------
# Status, bloqueio e expediente
# --------------------------------------------------------------------------------------

def test_qualquer_transicao_entre_status_validos_e_aceita(
    client_admin: TestClient, dentro_do_expediente
) -> None:
    """Não há máquina de estados nesta fase — só pertencimento ao conjunto."""
    criada = _criar(client_admin)
    for destino in ("em_execucao", "concluida", "rascunho", "cancelada", "planejada"):
        resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": destino})
        assert resposta.status_code == 200, f"{destino}: {resposta.text}"
        assert resposta.json()["status"] == destino


def test_status_invalido_e_recusado(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": "inventado"})
    assert resposta.status_code == 422


def test_status_arquivada_nao_e_editavel_por_patch(client_admin: TestClient) -> None:
    """Arquivar tem rota própria, com motivo obrigatório — não se chega lá por PATCH."""
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": "arquivada"})
    assert resposta.status_code == 422


def test_bloquear_sem_motivo_e_recusado(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": "bloqueada"})
    assert resposta.status_code == 422, resposta.text


def test_bloquear_com_motivo_so_de_espacos_e_recusado(client_admin: TestClient) -> None:
    """`min_length` contaria "   " como preenchido — bloqueio sem motivo real esvaziaria a
    obrigatoriedade sem que ninguém percebesse."""
    criada = _criar(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"status": "bloqueada", "motivoBloqueio": "   "}
    )
    assert resposta.status_code == 422, resposta.text


def test_bloquear_e_desbloquear_limpa_o_motivo(client_admin: TestClient, dentro_do_expediente) -> None:
    criada = _criar(client_admin)
    bloqueada = client_admin.patch(
        f"/demandas/{criada['id']}",
        json={"status": "bloqueada", "motivoBloqueio": "Aguardando aprovação do cliente"},
    ).json()
    assert bloqueada["motivoBloqueio"] == "Aguardando aprovação do cliente"

    desbloqueada = client_admin.patch(
        f"/demandas/{criada['id']}", json={"status": "em_execucao"}
    ).json()
    assert desbloqueada["motivoBloqueio"] is None


def test_motivo_de_bloqueio_sobrevive_no_evento(
    client_admin: TestClient, db_session: Session, dentro_do_expediente
) -> None:
    """O campo é limpo ao sair, mas o histórico NÃO se perde — vive no evento, que é o
    histórico desta fase."""
    criada = _criar(client_admin)
    client_admin.patch(
        f"/demandas/{criada['id']}", json={"status": "bloqueada", "motivoBloqueio": "Falta arte"}
    )
    client_admin.patch(f"/demandas/{criada['id']}", json={"status": "em_execucao"})

    payloads = db_session.execute(
        text(
            "SELECT payload::text FROM eventos WHERE entidade_id = :id "
            "AND tipo = 'demanda.desbloqueada'"
        ),
        {"id": criada["id"]},
    ).scalars().all()
    assert any("Falta arte" in p for p in payloads), payloads


def test_criar_ja_bloqueada_exige_motivo(client_admin: TestClient) -> None:
    resposta = client_admin.post("/demandas", json=_payload(status="bloqueada"))
    assert resposta.status_code == 422, resposta.text


def test_entrar_em_execucao_fora_do_expediente_devolve_409_estruturado(
    client_admin: TestClient, fora_do_expediente
) -> None:
    """A regra passa a valer no servidor: até aqui qualquer `curl` iniciava uma tarefa fora do
    horário, porque a verificação só existia no Kanban."""
    criada = _criar(client_admin)
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": "em_execucao"})

    assert resposta.status_code == 409, resposta.text
    detalhe = resposta.json()["detail"]
    assert detalhe["code"] == "FORA_DE_EXPEDIENTE"
    # A janela vem do servidor — a interface apenas apresenta, sem repetir a regra.
    assert "manhaInicio" in detalhe["expediente"]


def test_expediente_nao_barra_criacao_nem_outros_status(
    client_admin: TestClient, fora_do_expediente
) -> None:
    """O que a regra protege é o INÍCIO do trabalho, não o registro dele. Criar rascunho,
    planejar, concluir e cancelar seguem livres a qualquer hora."""
    criada = _criar(client_admin)
    for destino in ("planejada", "concluida", "cancelada"):
        resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"status": destino})
        assert resposta.status_code == 200, f"{destino}: {resposta.text}"


def test_regra_de_expediente_desativada_libera_qualquer_hora() -> None:
    ativa = _regra_todos_os_dias(
        manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00", tolerancia_retomada_minutos=30
    )
    desativada = RegraExpediente(ativo=False, tolerancia_retomada_minutos=30, dias=ativa.dias)
    meia_noite = datetime.combine(datetime.now().date(), time(3, 0))
    assert esta_dentro_expediente(meia_noite, regra=desativada) is True


def test_tolerancia_de_retomada_e_respeitada() -> None:
    """13h30 está fora da tarde (14h) mas dentro da tolerância de 30 minutos."""
    regra = _regra_todos_os_dias(
        manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00", tolerancia_retomada_minutos=30
    )
    hoje = datetime.now().date()
    assert esta_dentro_expediente(datetime.combine(hoje, time(13, 30)), regra=regra) is True
    assert esta_dentro_expediente(datetime.combine(hoje, time(13, 0)), regra=regra) is False


def test_dia_inativo_fica_fora_mesmo_com_hora_dentro_da_janela() -> None:
    """Prova a falha que a Fase 2G.3 corrigiu: sábado às 10h não pode contar como expediente
    só porque a hora bate com a janela da manhã de um dia útil."""
    domingo_janela_util = JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00")
    dia_inativo = JanelaDia(ativo=False)
    regra = RegraExpediente(
        ativo=True,
        tolerancia_retomada_minutos=0,
        dias={dia: domingo_janela_util for dia in range(6)} | {6: dia_inativo},  # 6 = domingo
    )
    # Um domingo qualquer, 10h — dentro da janela "da manhã", mas domingo está inativo.
    domingo = datetime(2026, 8, 23, 10, 0)  # 2026-08-23 é domingo
    assert domingo.weekday() == 6
    assert esta_dentro_expediente(domingo, regra=regra) is False


# --------------------------------------------------------------------------------------
# Busca — interpretação central, ver app/core/busca.py
# --------------------------------------------------------------------------------------

def test_busca_por_numero_operacional_e_exata(client_admin: TestClient, db_session: Session, empresa) -> None:
    """Igualdade exata, não parcial: "2063" localiza a demanda #2063, não toda demanda cujo
    número contenha 2063."""
    db_session.execute(
        text(
            "INSERT INTO sequencias_operacionais "
            "(id, empresa_id, tipo_entidade, ultimo_numero, created_at, updated_at) "
            "VALUES (:id, :e, 'demanda', 2062, now(), now())"
        ),
        {"id": str(uuid.uuid4()), "e": empresa.id},
    )
    db_session.flush()

    alvo = _criar(client_admin)  # #2063
    _criar(client_admin)  # #2064

    achados = client_admin.get("/demandas?search=2063").json()
    assert [d["id"] for d in achados] == [alvo["id"]]


def test_busca_aceita_cerquilha(client_admin: TestClient) -> None:
    """`#2063` é como a operação escreve."""
    alvo = _criar(client_admin)
    achados = client_admin.get(f"/demandas?search=%23{alvo['numeroOperacional']}").json()
    assert alvo["id"] in [d["id"] for d in achados]


def test_busca_por_codigo_de_referencia(client_admin: TestClient) -> None:
    alvo = _criar(client_admin)
    achados = client_admin.get(f"/demandas?search={alvo['codigoReferencia']}").json()
    assert [d["id"] for d in achados] == [alvo["id"]]


def test_busca_por_nome_e_por_pit(client_admin: TestClient) -> None:
    alvo = _criar(client_admin, nome="Campanha Natal Bretas", pit="PIT-777")
    _criar(client_admin, nome="Outra coisa")

    por_nome = client_admin.get("/demandas?search=Natal").json()
    assert [d["id"] for d in por_nome] == [alvo["id"]]

    por_pit = client_admin.get("/demandas?search=PIT-777").json()
    assert [d["id"] for d in por_pit] == [alvo["id"]]


def test_termo_com_letras_nao_vira_busca_numerica(client_admin: TestClient) -> None:
    """Regressão da Fase 2B, aplicada a Demanda: um termo textual não pode ser reinterpretado
    como número. `QA FASE2E` tem dígitos, mas é texto."""
    _criar(client_admin, nome="Demanda alfa")
    _criar(client_admin, nome="Demanda beta")

    achados = client_admin.get("/demandas?search=QA FASE2E").json()
    assert achados == [], "termo textual sem correspondência deve devolver vazio"


def test_toda_demanda_encontrada_justifica_o_proprio_texto(client_admin: TestClient) -> None:
    """A invariante real da busca: cada resultado tem de conter o termo em ALGUM campo
    pesquisável, ou casar o número exato."""
    _criar(client_admin, nome="Relatório mensal", pit="PIT-100")
    _criar(client_admin, nome="Ajuste de banner")
    alvo = _criar(client_admin, nome="Relatório anual")

    for demanda in client_admin.get("/demandas?search=Relatório").json():
        assert "relatório" in demanda["nome"].lower()
    assert alvo["id"] in [d["id"] for d in client_admin.get("/demandas?search=anual").json()]


# --------------------------------------------------------------------------------------
# Arquivamento
# --------------------------------------------------------------------------------------

def test_arquivar_exige_motivo_nao_branco(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    assert client_admin.post(f"/demandas/{criada['id']}/arquivar", json={}).status_code == 422
    resposta = client_admin.post(
        f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "   "}
    )
    assert resposta.status_code == 422, resposta.text


def test_arquivar_preserva_o_status_anterior(client_admin: TestClient) -> None:
    criada = _criar(client_admin, status="planejada")
    arquivada = client_admin.post(
        f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "Cancelada pelo cliente"}
    ).json()

    assert arquivada["status"] == "arquivada"
    assert arquivada["statusAnteriorArquivamento"] == "planejada"
    assert arquivada["motivoArquivamento"] == "Cancelada pelo cliente"
    assert arquivada["arquivadoAt"] is not None


def test_arquivada_sai_da_listagem_padrao_e_volta_com_filtro(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "Motivo"})

    assert client_admin.get("/demandas").json() == []
    com_filtro = client_admin.get("/demandas?status=arquivada").json()
    assert [d["id"] for d in com_filtro] == [criada["id"]]


def test_arquivada_nao_pode_ser_editada(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "Motivo"})
    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"nome": "Novo nome"})
    assert resposta.status_code == 409, resposta.text


def test_restaurar_devolve_ao_status_anterior(client_admin: TestClient) -> None:
    criada = _criar(client_admin, status="planejada")
    client_admin.post(f"/demandas/{criada['id']}/arquivar", json={"motivoArquivamento": "Motivo"})
    restaurada = client_admin.post(f"/demandas/{criada['id']}/restaurar").json()

    assert restaurada["status"] == "planejada"
    assert restaurada["arquivadoAt"] is None
    assert restaurada["restauradoAt"] is not None


def test_restaurar_demanda_ativa_e_conflito(client_admin: TestClient) -> None:
    criada = _criar(client_admin)
    resposta = client_admin.post(f"/demandas/{criada['id']}/restaurar")
    assert resposta.status_code == 409, resposta.text


def test_operador_nao_arquiva_nem_restaura(
    client_admin: TestClient, client_operador: TestClient, usuario_operador: Usuario
) -> None:
    """Arquivar/restaurar seguem restritos a admin/gestor, como nos cadastros — mesmo sobre
    demanda dentro do próprio escopo."""
    minha = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    resposta = client_operador.post(
        f"/demandas/{minha['id']}/arquivar", json={"motivoArquivamento": "Motivo"}
    )
    assert resposta.status_code == 403, resposta.text


# --------------------------------------------------------------------------------------
# Vínculos e edição
# --------------------------------------------------------------------------------------

def test_sincronizar_responsaveis_adiciona_e_remove(
    client_admin: TestClient, db_session: Session, empresa, usuario_operador: Usuario, usuario_gestor: Usuario
) -> None:
    criada = _criar(client_admin, usuarioResponsavelIds=[str(usuario_operador.id)])
    atualizada = client_admin.patch(
        f"/demandas/{criada['id']}", json={"usuarioResponsavelIds": [str(usuario_gestor.id)]}
    ).json()
    assert atualizada["usuarioResponsavelIds"] == [str(usuario_gestor.id)]


def test_sincronizar_departamentos_responsaveis_adiciona_e_remove(
    client_admin: TestClient, db_session: Session, empresa
) -> None:
    """Regressão do bug de persistência da edição inline do drawer (Fase 2E.4):
    `ResponsaveisDemandaSection` monta o payload de `departamentoResponsavelIds` a partir do
    `id` real do diretório (nunca `codigoInterno`, eliminado na 2E.2) — o teste prova que o
    valor sobrevive a uma NOVA consulta ao servidor, não só ao retorno imediato do PATCH."""
    dep_a = _departamento(db_session, empresa)
    dep_b = _departamento(db_session, empresa)
    criada = _criar(client_admin, departamentoResponsavelIds=[str(dep_a.id)])

    atualizada = client_admin.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": [str(dep_b.id)]}
    ).json()
    assert atualizada["departamentoResponsavelIds"] == [str(dep_b.id)]

    relida = client_admin.get(f"/demandas/{criada['id']}").json()
    assert relida["departamentoResponsavelIds"] == [str(dep_b.id)]


def test_departamento_responsavel_com_id_nao_uuid_e_recusado(client_admin: TestClient) -> None:
    """Trava a ponte legada (`codigoInterno` como FK, eliminada na Fase 2E.2) não voltar a
    entrar por aqui — um id no formato antigo (`dep-atendimento`) tem de falhar a validação
    de tipo antes de chegar a qualquer verificação de existência."""
    criada = _criar(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}", json={"departamentoResponsavelIds": ["dep-atendimento"]}
    )
    assert resposta.status_code == 422, resposta.text


def test_patch_persiste_campos_simples_em_nova_consulta(client_admin: TestClient) -> None:
    """Regressão do bug de persistência da edição inline do drawer (Fase 2E.4):
    `DadosDemandaSection`/`BriefingDemandaSection` só chamavam `setDemandas(...)` local — o
    valor "salvo" na tela nunca chegava ao servidor e sumia no próximo carregamento. O teste
    teria passado mesmo com o bug se só checasse a resposta do PATCH (que sempre veio do
    servidor); a prova real é uma consulta NOVA e independente."""
    criada = _criar(client_admin)
    resposta = client_admin.patch(
        f"/demandas/{criada['id']}",
        json={
            "pit": "C3A-0008/26",
            "prioridade": "alta",
            "briefing": "<p>Texto do briefing</p>",
            "prazoEtapaAtual": "2026-08-20T12:00:00+00:00",
        },
    )
    assert resposta.status_code == 200, resposta.text

    relida = client_admin.get(f"/demandas/{criada['id']}").json()
    assert relida["pit"] == "C3A-0008/26"
    assert relida["prioridade"] == "alta"
    assert relida["briefing"] == "<p>Texto do briefing</p>"
    assert relida["prazoEtapaAtual"] is not None


def test_patch_persiste_projeto_e_cliente_em_nova_consulta(
    client_admin: TestClient, db_session: Session, empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    criada = _criar(client_admin)

    resposta = client_admin.patch(f"/demandas/{criada['id']}", json={"clienteId": str(cliente.id)})
    assert resposta.status_code == 200, resposta.text

    relida = client_admin.get(f"/demandas/{criada['id']}").json()
    assert relida["clienteId"] == str(cliente.id)


def test_responsavel_de_outra_empresa_e_recusado(client_admin: TestClient) -> None:
    resposta = client_admin.post(
        "/demandas", json=_payload(usuarioResponsavelIds=[str(uuid.uuid4())])
    )
    assert resposta.status_code == 422


def test_cliente_arquivado_nao_aceita_vinculo_novo(
    client_admin: TestClient, db_session: Session, empresa
) -> None:
    cliente = _cliente(db_session, empresa)
    cliente.status = "arquivado"
    db_session.flush()
    resposta = client_admin.post("/demandas", json=_payload(clienteId=str(cliente.id)))
    assert resposta.status_code == 422, resposta.text


def test_edicao_registra_evento_de_alteracao(
    client_admin: TestClient, db_session: Session
) -> None:
    criada = _criar(client_admin)
    client_admin.patch(f"/demandas/{criada['id']}", json={"nome": "Nome novo"})

    tipos = db_session.execute(
        text("SELECT tipo FROM eventos WHERE entidade_id = :id ORDER BY occurred_at"),
        {"id": criada["id"]},
    ).scalars().all()
    assert "demanda.criada" in tipos
    assert "demanda.alterada" in tipos


def test_mudanca_de_status_gera_evento_com_de_e_para(
    client_admin: TestClient, db_session: Session, dentro_do_expediente
) -> None:
    """Toda mudança gera evento — é o que permitirá desenhar a política junto do Workflow real,
    com dado em vez de suposição."""
    criada = _criar(client_admin)
    client_admin.patch(f"/demandas/{criada['id']}", json={"status": "em_execucao"})

    payload = db_session.execute(
        text(
            "SELECT payload::text FROM eventos WHERE entidade_id = :id "
            "AND tipo = 'demanda.status_alterado'"
        ),
        {"id": criada["id"]},
    ).scalar_one()
    assert "rascunho" in payload and "em_execucao" in payload


def test_nome_duplicado_e_permitido(client_admin: TestClient) -> None:
    """Duas tarefas "Ajuste banner" no mesmo dia são rotina — não há UNIQUE de nome, e um aviso
    de duplicidade viraria ruído constante."""
    primeira = client_admin.post("/demandas", json={"nome": "Ajuste banner"})
    segunda = client_admin.post("/demandas", json={"nome": "Ajuste banner"})
    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert primeira.json()["numeroOperacional"] != segunda.json()["numeroOperacional"]


# --------------------------------------------------------------------------------------
# CLI de número operacional
# --------------------------------------------------------------------------------------

def test_cli_nao_tem_flag_forcar() -> None:
    """Sem modo de força, sem confirmação interativa, sem caminho alternativo.

    Uma operação capaz de reemitir números precisa de fricção, não de flag — e confirmação
    interativa protegeria contra engano, não contra decisão errada.
    """
    from app.cli.inicializar_numero_operacional import build_parser

    flags = {f for a in build_parser()._actions for f in a.option_strings}
    assert "--forcar" not in flags
    assert "--force" not in flags


def test_cli_grava_o_contador(db_session: Session, empresa) -> None:
    from app.cli.inicializar_numero_operacional import inicializar

    mensagem = inicializar(
        db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=2062
    )
    assert "2063" in mensagem
    gravado = db_session.execute(
        text(
            "SELECT ultimo_numero FROM sequencias_operacionais "
            "WHERE empresa_id = :e AND tipo_entidade = 'demanda'"
        ),
        {"e": empresa.id},
    ).scalar_one()
    assert gravado == 2062


def test_cli_e_idempotente_com_o_mesmo_valor(db_session: Session, empresa) -> None:
    from app.cli.inicializar_numero_operacional import inicializar

    inicializar(db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=2062)
    mensagem = inicializar(
        db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=2062
    )
    assert "Nada alterado" in mensagem


def test_cli_recusa_alterar_contador_existente(db_session: Session, empresa) -> None:
    from app.cli.inicializar_numero_operacional import InicializacaoAbortada, inicializar

    inicializar(db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=2062)
    with pytest.raises(InicializacaoAbortada) as exc:
        inicializar(db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=100)
    assert "2062" in str(exc.value) and "100" in str(exc.value)


def test_cli_recusa_valor_negativo(db_session: Session, empresa) -> None:
    from app.cli.inicializar_numero_operacional import InicializacaoAbortada, inicializar

    with pytest.raises(InicializacaoAbortada):
        inicializar(db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=-1)


def test_cli_recusa_quando_ja_existe_demanda_emitida(
    client_admin: TestClient, db_session: Session, empresa
) -> None:
    from app.cli.inicializar_numero_operacional import InicializacaoAbortada, inicializar

    _criar(client_admin)
    with pytest.raises(InicializacaoAbortada) as exc:
        inicializar(db_session, empresa_id=empresa.id, tipo_entidade="demanda", ultimo_numero=5000)
    assert "demanda(s) emitida(s)" in str(exc.value)


def test_cli_recusa_tipo_fora_da_lista(db_session: Session, empresa) -> None:
    from app.cli.inicializar_numero_operacional import InicializacaoAbortada, inicializar

    with pytest.raises(InicializacaoAbortada):
        inicializar(db_session, empresa_id=empresa.id, tipo_entidade="projeto", ultimo_numero=10)


def test_cli_nao_entra_no_seed_all() -> None:
    """Continuidade com o iClips é dado de PRODUÇÃO, não de reconstrução: semeá-la a cada
    `seed_all` faria toda base nova nascer com um contador que só faz sentido em um lugar."""
    from pathlib import Path

    fonte = Path(__file__).resolve().parents[1] / "app" / "cli" / "seed_all.py"
    assert "inicializar_numero_operacional" not in fonte.read_text(encoding="utf-8")
