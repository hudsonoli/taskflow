"""11B.2D-A — capacidade individual pela API real: jornada própria, ausências, autoridade, tenant, eventos e a integração com `GET /trafego/operacional/carga`.

Prova: fallback para o expediente da empresa; jornada substitui a semana (dia vazio = 0); ausência por data (dia inteiro, deduplicada); RBAC (admin/gestor sobre o alvo permitido, operador recusado, 401, outra
empresa = 404); evento na mesma transação e nenhum em no-op; a Carga muda SÓ o denominador de capacidade; planejamento/estimativa/status intocados; expediente desligado ignora jornada; consultas constantes.
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

from sqlalchemy import event, func, select

from app.models.demanda import Demanda
from app.models.demanda_workflow_etapa import DemandaWorkflowEtapa
from app.models.evento import Evento
from app.models.usuario import Usuario
from app.models.usuario_capacidade import UsuarioAusencia, UsuarioJornada
from tests.test_carga_semanal_api import SEG, SEG2, SEG3, carga, etapa_carga, por_id, regra, relogio  # noqa: F401  (regra/relogio são fixtures)
from tests.test_carga_semanal_api import pessoa as _pessoa
from tests.test_sessao_trabalho import _departamento

SEMANA2 = SEG2.isoformat()  # semana futura inteira (26/10): 5 dias úteis × 480 = 2400 nominais


def pessoa(db, empresa, **campos):
    """Cria o usuário e CONFIRMA: o service faz `rollback()` nos caminhos de erro (403/404/422) e, no banco de teste, isso desfaria tudo o que só foi dado `flush`."""
    criado = _pessoa(db, empresa, **campos)
    db.commit()
    return criado


def dia(d: int, *periodos: tuple[str, str]) -> dict:
    return {"diaSemana": d, "periodos": [{"inicio": i, "fim": f} for i, f in periodos]}


def seg_a_sex(inicio: str, fim: str) -> list[dict]:
    return [dia(d, (inicio, fim)) for d in range(5)]


def put_jornada(cliente, usuario_id: str, dias: list[dict]):
    return cliente.put(f"/usuarios/{usuario_id}/jornada", json={"dias": dias})


def ausencia(cliente, usuario_id: str, inicio, fim, tipo: str = "ferias", **extra):
    return cliente.post(f"/usuarios/{usuario_id}/ausencias", json={"tipo": tipo, "inicio": inicio.isoformat(), "fim": fim.isoformat(), **extra})


def eventos(db, tipo: str) -> list[Evento]:
    return list(db.scalars(select(Evento).where(Evento.tipo == tipo).order_by(Evento.occurred_at)).all())


def capacidade_de(cliente, usuario_id: str, semana: str = SEMANA2) -> dict:
    return por_id(carga(cliente, semana=semana).json()["pessoas"], "usuarioId", usuario_id)


# ── jornada: leitura, criação, substituição e volta ao padrão ───────────────────────────────────────────────────────


def test_sem_jornada_get_devolve_o_fallback_da_empresa_e_nada_e_copiado(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    corpo = client_admin.get(f"/usuarios/{a.id}/jornada").json()
    assert corpo["personalizada"] is False and corpo["usuarioId"] == a.id
    por_dia = {d["diaSemana"]: d["periodos"] for d in corpo["dias"]}
    assert len(corpo["dias"]) == 7 and len(por_dia[0]) >= 1 and por_dia[5] == [] and por_dia[6] == []  # seg–sex abertos, fim de semana fechado (expediente padrão)
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 0


def test_criar_substituir_e_remover_a_jornada_volta_exatamente_ao_fallback(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    antes = capacidade_de(client_admin, a.id)
    assert (antes["capacidadeNominalMin"], antes["capacidadeOrigem"], antes["diasAusentes"]) == (2400, "empresa", 0)

    criada = put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))
    assert criada.status_code == 200 and criada.json()["personalizada"] is True
    assert capacidade_de(client_admin, a.id)["capacidadeNominalMin"] == 1800  # 6h × 5
    assert capacidade_de(client_admin, a.id)["capacidadeOrigem"] == "individual"

    substituida = put_jornada(client_admin, a.id, [dia(0, ("09:00", "13:00")), dia(2, ("09:00", "13:00")), dia(4, ("09:00", "13:00"))])
    assert substituida.status_code == 200
    assert capacidade_de(client_admin, a.id)["capacidadeNominalMin"] == 720  # terça e quinta SEM período = 0 (sem fallback dia a dia)

    removida = client_admin.delete(f"/usuarios/{a.id}/jornada")
    assert removida.status_code == 200 and removida.json()["personalizada"] is False
    volta = capacidade_de(client_admin, a.id)
    assert {k: volta[k] for k in ("capacidadeNominalMin", "capacidadeAlocavelMin", "capacidadeOrigem")} == {k: antes[k] for k in ("capacidadeNominalMin", "capacidadeAlocavelMin", "capacidadeOrigem")}
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 0  # nada ficou para trás


def test_multiplos_periodos_no_dia_e_dia_de_fim_de_semana(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    resposta = put_jornada(client_admin, a.id, [dia(0, ("09:00", "12:00"), ("13:00", "17:00")), dia(5, ("08:00", "12:00"))])
    assert resposta.status_code == 200
    lida = {d["diaSemana"]: d["periodos"] for d in client_admin.get(f"/usuarios/{a.id}/jornada").json()["dias"]}
    assert len(lida[0]) == 2 and len(lida[5]) == 1 and lida[1] == []
    assert capacidade_de(client_admin, a.id)["capacidadeNominalMin"] == 7 * 60 + 240  # segunda 7h + sábado 4h


def test_validacao_da_grade(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    assert put_jornada(client_admin, a.id, [dia(0, ("09:00", "12:00"), ("11:00", "14:00"))]).status_code == 422  # sobreposição
    assert put_jornada(client_admin, a.id, [dia(0, ("12:00", "09:00"))]).status_code == 422  # fim antes do início
    assert put_jornada(client_admin, a.id, [dia(0, ("09:00", "09:00"))]).status_code == 422
    assert put_jornada(client_admin, a.id, [dia(7, ("09:00", "12:00"))]).status_code == 422  # dia da semana fora de 0..6
    assert put_jornada(client_admin, a.id, [dia(1, ("09:00", "12:00")), dia(1, ("13:00", "17:00"))]).status_code == 422  # dia repetido
    assert put_jornada(client_admin, a.id, [dia(0, ("09:00", "12:00"), ("12:00", "14:00"))]).status_code == 200  # só se tocam: válido
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 1  # as recusas não criaram nada


def test_jornada_sem_nenhum_periodo_e_valida_e_zera_a_capacidade(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    assert put_jornada(client_admin, a.id, []).status_code == 200
    cap = capacidade_de(client_admin, a.id)
    assert (cap["capacidadeNominalMin"], cap["capacidadeOrigem"]) == (0, "individual")


# ── auditoria da jornada ─────────────────────────────────────────────────────────────────────────────────────────


def test_eventos_da_jornada_mesma_transacao_e_sem_duplicar_no_op(client_admin, db_session, empresa, regra, usuario_admin) -> None:
    a = pessoa(db_session, empresa)
    grade = seg_a_sex("09:00", "15:00")
    put_jornada(client_admin, a.id, grade)
    [criada] = eventos(db_session, "usuario.jornada_alterada")
    assert criada.usuario_id == usuario_admin.id and criada.payload["usuarioAfetadoId"] == a.id
    assert criada.payload["acao"] == "criada" and criada.payload["antes"] is None and criada.payload["depois"]["0"] == ["09:00-15:00"]

    put_jornada(client_admin, a.id, grade)  # no-op: mesma grade
    assert len(eventos(db_session, "usuario.jornada_alterada")) == 1

    put_jornada(client_admin, a.id, seg_a_sex("09:00", "16:00"))
    alterada = eventos(db_session, "usuario.jornada_alterada")[-1]
    assert alterada.payload["acao"] == "substituida" and alterada.payload["antes"]["0"] == ["09:00-15:00"] and alterada.payload["depois"]["0"] == ["09:00-16:00"]

    client_admin.delete(f"/usuarios/{a.id}/jornada")
    [removida] = eventos(db_session, "usuario.jornada_removida")
    assert removida.payload["antes"]["0"] == ["09:00-16:00"] and removida.payload["depois"] is None
    client_admin.delete(f"/usuarios/{a.id}/jornada")  # já sem jornada: no-op
    assert len(eventos(db_session, "usuario.jornada_removida")) == 1


def test_falha_na_validacao_nao_deixa_jornada_nem_evento(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    assert put_jornada(client_admin, a.id, [dia(0, ("09:00", "12:00"), ("11:00", "14:00"))]).status_code == 422
    assert eventos(db_session, "usuario.jornada_alterada") == []
    assert client_admin.get(f"/usuarios/{a.id}/jornada").json()["personalizada"] is False


# ── ausências: CRUD ──────────────────────────────────────────────────────────────────────────────────────────────


def test_crud_de_ausencias_com_eventos_sem_observacao_no_payload(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    criada = ausencia(client_admin, a.id, SEG2, SEG2 + timedelta(days=4), observacao="Atestado — CID sigiloso")
    assert criada.status_code == 201
    corpo = criada.json()
    assert (corpo["tipo"], corpo["inicio"], corpo["fim"], corpo["observacao"]) == ("ferias", "2026-10-26", "2026-10-30", "Atestado — CID sigiloso")
    [evento_criado] = eventos(db_session, "usuario.ausencia_criada")
    assert evento_criado.payload["depois"] == {"tipo": "ferias", "inicio": "2026-10-26", "fim": "2026-10-30"}
    assert "sigiloso" not in str(evento_criado.payload)  # a observação livre nunca vai para a auditoria

    assert [x["id"] for x in client_admin.get(f"/usuarios/{a.id}/ausencias").json()] == [corpo["id"]]

    editada = client_admin.patch(f"/usuarios/{a.id}/ausencias/{corpo['id']}", json={"fim": "2026-10-28", "tipo": "folga"})
    assert editada.status_code == 200 and (editada.json()["fim"], editada.json()["tipo"], editada.json()["observacao"]) == ("2026-10-28", "folga", "Atestado — CID sigiloso")
    [evento_alterado] = eventos(db_session, "usuario.ausencia_alterada")
    assert evento_alterado.payload["antes"]["fim"] == "2026-10-30" and evento_alterado.payload["depois"]["fim"] == "2026-10-28"

    client_admin.patch(f"/usuarios/{a.id}/ausencias/{corpo['id']}", json={"fim": "2026-10-28"})  # no-op
    assert len(eventos(db_session, "usuario.ausencia_alterada")) == 1
    limpar = client_admin.patch(f"/usuarios/{a.id}/ausencias/{corpo['id']}", json={"observacao": None})
    assert limpar.json()["observacao"] is None  # só a observação mudou: gera evento, sem vazar texto
    ultimo = eventos(db_session, "usuario.ausencia_alterada")[-1]
    assert ultimo.payload["observacaoAlterada"] is True and "sigiloso" not in str(ultimo.payload)

    assert client_admin.delete(f"/usuarios/{a.id}/ausencias/{corpo['id']}").status_code == 204
    [removida] = eventos(db_session, "usuario.ausencia_removida")
    assert removida.payload["antes"]["tipo"] == "folga" and removida.payload["depois"] is None
    assert client_admin.get(f"/usuarios/{a.id}/ausencias").json() == []
    assert client_admin.delete(f"/usuarios/{a.id}/ausencias/{corpo['id']}").status_code == 404


def test_validacao_de_ausencia(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    assert ausencia(client_admin, a.id, SEG2 + timedelta(days=2), SEG2).status_code == 422  # fim antes do início
    assert ausencia(client_admin, a.id, SEG2, SEG2, tipo="licenca_premio").status_code == 422  # tipo fora do catálogo
    assert client_admin.post(f"/usuarios/{a.id}/ausencias", json={"tipo": "ferias", "inicio": "2026-10-26"}).status_code == 422
    assert client_admin.post(f"/usuarios/{a.id}/ausencias", json={"tipo": "ferias", "inicio": SEG2.isoformat(), "fim": SEG2.isoformat(), "valor": 100}).status_code == 422  # campo estranho
    um_dia = ausencia(client_admin, a.id, SEG2, SEG2, tipo="folga")
    assert um_dia.status_code == 201  # início = fim é válido (inclusive)
    assert client_admin.patch(f"/usuarios/{a.id}/ausencias/{um_dia.json()['id']}", json={"fim": "2026-10-20"}).status_code == 422  # edição deixaria fim < início
    assert db_session.scalar(select(func.count()).select_from(UsuarioAusencia)) == 1


def test_listagem_filtra_por_intervalo(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    ausencia(client_admin, a.id, SEG, SEG + timedelta(days=1), tipo="folga")
    ausencia(client_admin, a.id, SEG3, SEG3 + timedelta(days=4))
    todas = client_admin.get(f"/usuarios/{a.id}/ausencias").json()
    assert [x["inicio"] for x in todas] == [SEG3.isoformat(), SEG.isoformat()]
    so_segunda = client_admin.get(f"/usuarios/{a.id}/ausencias", params={"desde": SEG.isoformat(), "ate": (SEG + timedelta(days=6)).isoformat()}).json()
    assert [x["inicio"] for x in so_segunda] == [SEG.isoformat()]


# ── autoridade, tenant, sistema ──────────────────────────────────────────────────────────────────────────────────


def test_operador_comum_e_recusado_e_sem_token_401(client_operador, client, db_session, empresa, regra) -> None:
    alvo = pessoa(db_session, empresa)
    assert put_jornada(client_operador, alvo.id, seg_a_sex("09:00", "15:00")).status_code == 403
    assert client_operador.delete(f"/usuarios/{alvo.id}/jornada").status_code == 403
    assert ausencia(client_operador, alvo.id, SEG2, SEG2).status_code == 403
    assert client_operador.get(f"/usuarios/{alvo.id}/jornada").status_code == 403
    assert client_operador.get(f"/usuarios/{alvo.id}/ausencias").status_code == 403
    assert put_jornada(client, alvo.id, seg_a_sex("09:00", "15:00")).status_code == 401
    assert client.get(f"/usuarios/{alvo.id}/ausencias").status_code == 401
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 0


def test_gestor_administra_so_usuario_e_admin_administra_gestor(client_admin, client_gestor, db_session, empresa, regra, usuario_admin) -> None:
    operador = pessoa(db_session, empresa)
    outro_gestor = pessoa(db_session, empresa, perfil_base="gestor")
    assert put_jornada(client_gestor, operador.id, seg_a_sex("09:00", "15:00")).status_code == 200  # gestor → operador
    assert ausencia(client_gestor, operador.id, SEG2, SEG2).status_code == 201
    assert put_jornada(client_gestor, outro_gestor.id, seg_a_sex("09:00", "15:00")).status_code == 403  # gestor → gestor
    assert put_jornada(client_gestor, usuario_admin.id, seg_a_sex("09:00", "15:00")).status_code == 403  # gestor → admin
    assert ausencia(client_gestor, outro_gestor.id, SEG2, SEG2).status_code == 403
    assert put_jornada(client_admin, outro_gestor.id, seg_a_sex("09:00", "15:00")).status_code == 200  # admin → gestor
    assert client_gestor.get(f"/usuarios/{outro_gestor.id}/jornada").status_code == 200  # leitura segue `usuarios.visualizar`


def test_outra_empresa_e_404_em_tudo_e_nada_vaza(client_admin, db_session, empresa, outra_empresa, regra) -> None:
    alheio = pessoa(db_session, outra_empresa)
    assert client_admin.get(f"/usuarios/{alheio.id}/jornada").status_code == 404
    assert put_jornada(client_admin, alheio.id, seg_a_sex("09:00", "15:00")).status_code == 404
    assert client_admin.delete(f"/usuarios/{alheio.id}/jornada").status_code == 404
    assert ausencia(client_admin, alheio.id, SEG2, SEG2).status_code == 404
    assert client_admin.get(f"/usuarios/{alheio.id}/ausencias").status_code == 404
    inexistente = str(uuid.uuid4())
    assert client_admin.get(f"/usuarios/{inexistente}/jornada").status_code == 404  # igual a inexistente: não distingue
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 0


def test_ausencia_de_outro_usuario_nao_e_acessivel_pelo_caminho_errado(client_admin, db_session, empresa, regra) -> None:
    a, b = pessoa(db_session, empresa), pessoa(db_session, empresa)
    do_a = ausencia(client_admin, a.id, SEG2, SEG2).json()["id"]
    assert client_admin.patch(f"/usuarios/{b.id}/ausencias/{do_a}", json={"tipo": "folga"}).status_code == 404
    assert client_admin.delete(f"/usuarios/{b.id}/ausencias/{do_a}").status_code == 404
    assert client_admin.get(f"/usuarios/{a.id}/ausencias").json()[0]["tipo"] == "ferias"


def test_conta_de_sistema_nao_tem_jornada_nem_ausencia(client_admin, db_session, empresa, regra) -> None:
    sistema = pessoa(db_session, empresa, is_system_account=True)
    assert put_jornada(client_admin, sistema.id, seg_a_sex("09:00", "15:00")).status_code == 403
    assert ausencia(client_admin, sistema.id, SEG2, SEG2).status_code == 403


# ── integração com a Carga ───────────────────────────────────────────────────────────────────────────────────────


def test_carga_com_capacidades_diferentes_departamento_soma_real_e_planejamento_intacto(client_admin, db_session, empresa, regra) -> None:
    dep = _departamento(db_session, empresa)
    a, b, c = (pessoa(db_session, empresa, dep=dep, nome=n) for n in ("Ana", "Bia", "Caio"))
    _d, etapa = etapa_carga(db_session, empresa, est=1200, ini=SEG2, fim=SEG2 + timedelta(days=4), users=[a, b, c], status="planejada")
    base = carga(client_admin, semana=SEMANA2).json()
    assert [p["capacidadeNominalMin"] for p in base["pessoas"] if p["nome"] in ("Ana", "Bia", "Caio")] == [2400, 2400, 2400]  # (o admin autenticado também é elegível)

    put_jornada(client_admin, b.id, seg_a_sex("09:00", "15:00"))  # B = 30h
    ausencia(client_admin, c.id, SEG2, SEG2 + timedelta(days=4))  # C = 40h com 5 dias de férias
    depois = carga(client_admin, semana=SEMANA2).json()
    pessoas = {p["nome"]: p for p in depois["pessoas"]}
    assert (pessoas["Ana"]["capacidadeNominalMin"], pessoas["Bia"]["capacidadeNominalMin"], pessoas["Caio"]["capacidadeNominalMin"]) == (2400, 1800, 0)
    assert (pessoas["Ana"]["capacidadeOrigem"], pessoas["Bia"]["capacidadeOrigem"], pessoas["Caio"]["capacidadeOrigem"]) == ("empresa", "individual", "empresa")
    assert (pessoas["Ana"]["diasAusentes"], pessoas["Caio"]["diasAusentes"]) == (0, 5)
    assert pessoas["Caio"]["ocupacaoPercentual"] is None  # capacidade 0 → sem denominador (e a carga dele continua visível)
    [departamento] = depois["departamentos"]
    assert departamento["capacidadeNominalMin"] == 2400 + 1800 + 0 and departamento["capacidadeAlocavelMin"] == 4200  # soma real, não 3 × padrão

    # planejamento IDÊNTICO: cada pessoa mantém o mesmo planejado; só saldo/ocupação (denominador) mudam
    for antes, agora in zip(base["pessoas"], depois["pessoas"]):
        assert antes["usuarioId"] == agora["usuarioId"] and antes["planejadoMin"] == agora["planejadoMin"]
        assert antes["planejadoMin"] == (400 if antes["nome"] in ("Ana", "Bia", "Caio") else 0)
    assert pessoas["Ana"]["saldoMin"] == 2400 - 400 and pessoas["Bia"]["saldoMin"] == 1800 - 400 and pessoas["Caio"]["saldoMin"] == -400
    assert depois["semana"]["dias"] == base["semana"]["dias"]  # o calendário da empresa por dia não muda
    assert depois["naoPlanejado"] == base["naoPlanejado"] and depois["pendenciasPlanejamento"] == base["pendenciasPlanejamento"]


def test_percentual_alocavel_da_empresa_aplica_sobre_a_jornada_individual(client_admin, db_session, empresa, regra) -> None:
    regra.percentual_capacidade_alocavel = 75
    db_session.flush()
    a = pessoa(db_session, empresa)
    put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))  # 30h nominais
    cap = capacidade_de(client_admin, a.id)
    assert (cap["capacidadeNominalMin"], cap["capacidadeAlocavelMin"]) == (1800, 1350)  # 22h30


def test_semana_atual_ausencia_antes_de_hoje_nao_conta_e_hoje_em_diante_conta(client_admin, db_session, empresa, regra, relogio) -> None:
    from datetime import datetime, timezone

    relogio(datetime(2026, 10, 21, 13, 0, tzinfo=timezone.utc))  # quarta 10:00 em São Paulo
    a = pessoa(db_session, empresa)
    ausencia(client_admin, a.id, SEG, SEG + timedelta(days=1))  # seg–ter: já passou
    cap = por_id(carga(client_admin).json()["pessoas"], "usuarioId", a.id)
    assert (cap["capacidadeNominalMin"], cap["diasAusentes"]) == (3 * 480, 0)
    ausencia(client_admin, a.id, SEG + timedelta(days=3), SEG + timedelta(days=3), tipo="folga")  # quinta
    cap = por_id(carga(client_admin).json()["pessoas"], "usuarioId", a.id)
    assert (cap["capacidadeNominalMin"], cap["diasAusentes"]) == (2 * 480, 1)


def test_ausencias_sobrepostas_e_em_dia_fechado_nunca_descontam_duas_vezes(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    ausencia(client_admin, a.id, SEG2, SEG2 + timedelta(days=2))
    ausencia(client_admin, a.id, SEG2 + timedelta(days=1), SEG2 + timedelta(days=3), tipo="outro")
    ausencia(client_admin, a.id, SEG2 + timedelta(days=5), SEG2 + timedelta(days=6), tipo="folga")  # sáb–dom: já fechados
    cap = capacidade_de(client_admin, a.id)
    assert (cap["capacidadeNominalMin"], cap["diasAusentes"]) == (480, 6)  # só sexta sobra; 6 datas distintas cobertas


def test_expediente_da_empresa_desligado_vence_a_jornada_individual(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))
    ausencia(client_admin, a.id, SEG2, SEG2)
    regra.ativo = False
    db_session.flush()
    corpo = carga(client_admin, semana=SEMANA2).json()
    assert corpo["capacidade"]["capacidadeIndisponivel"] == "expediente_desligado"
    p = por_id(corpo["pessoas"], "usuarioId", a.id)
    assert (p["capacidadeNominalMin"], p["capacidadeAlocavelMin"], p["saldoMin"], p["ocupacaoPercentual"], p["capacidadeOrigem"], p["diasAusentes"]) == (None, None, None, None, None, None)


def test_feriado_e_trabalho_excepcional_pela_api(client_admin, db_session, empresa, regra) -> None:
    from datetime import time

    from app.models.regra_expediente import RegraExpedienteDiaEspecial, RegraExpedienteDiaEspecialPeriodo
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    feriado = RegraExpedienteDiaEspecial(id=str(uuid.uuid4()), empresa_id=empresa.id, regra_expediente_id=regra.id, data=SEG2, nome="Feriado", origem="manual", tipo="feriado", ativo=True, created_at=agora, updated_at=agora)
    extra = RegraExpedienteDiaEspecial(id=str(uuid.uuid4()), empresa_id=empresa.id, regra_expediente_id=regra.id, data=SEG2 + timedelta(days=1), nome="Extra", origem="manual", tipo="trabalho_excepcional", ativo=True, created_at=agora, updated_at=agora)
    db_session.add_all([feriado, extra])
    db_session.flush()
    db_session.add(RegraExpedienteDiaEspecialPeriodo(id=str(uuid.uuid4()), dia_especial_id=extra.id, ordem=1, inicio=time(9, 0), fim=time(18, 0)))
    db_session.flush()
    sem_jornada, com_jornada = pessoa(db_session, empresa), pessoa(db_session, empresa)
    put_jornada(client_admin, com_jornada.id, seg_a_sex("09:00", "15:00"))
    ausente_no_extra = pessoa(db_session, empresa)
    ausencia(client_admin, ausente_no_extra.id, SEG2 + timedelta(days=1), SEG2 + timedelta(days=1), tipo="folga")

    # sem jornada: feriado fecha segunda (0), terça usa o especial 9h, qua–sex 8h → 9h + 24h = 33h
    assert capacidade_de(client_admin, sem_jornada.id)["capacidadeNominalMin"] == 9 * 60 + 3 * 480
    # com jornada 09–15: feriado fecha; terça é a INTERSEÇÃO (09–15 = 6h, não 9h); qua–sex 6h → 24h
    assert capacidade_de(client_admin, com_jornada.id)["capacidadeNominalMin"] == 4 * 360
    # ausência vence o trabalho excepcional: terça = 0, qua–sex 8h
    assert capacidade_de(client_admin, ausente_no_extra.id)["capacidadeNominalMin"] == 3 * 480


def test_ausencia_nao_inativa_o_usuario_nem_altera_planejamento(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    d, etapa = etapa_carga(db_session, empresa, est=300, ini=SEG2, fim=SEG2 + timedelta(days=4), users=[a], status="em_execucao")
    antes = (d.status, etapa.esforco_estimado_minutos, etapa.planejado_inicio, etapa.planejado_fim, db_session.get(DemandaWorkflowEtapa, etapa.id).status)
    contagem = db_session.scalar(select(func.count()).select_from(Evento).where(~Evento.tipo.like("usuario.%")))
    ausencia(client_admin, a.id, SEG2, SEG2 + timedelta(days=4))
    put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))
    db_session.expire_all()
    assert db_session.get(Usuario, a.id).status == "ativo"  # férias não é inativação
    d2, e2 = db_session.get(Demanda, d.id), db_session.get(DemandaWorkflowEtapa, etapa.id)
    assert (d2.status, e2.esforco_estimado_minutos, e2.planejado_inicio, e2.planejado_fim, e2.status) == antes
    assert db_session.scalar(select(func.count()).select_from(Evento).where(~Evento.tipo.like("usuario.%"))) == contagem  # nenhum evento de Demanda/workflow/sessão
    p = capacidade_de(client_admin, a.id)
    assert p["planejadoMin"] == 300 and p["capacidadeNominalMin"] == 0  # a carga continua; só a capacidade da semana zerou


# ── leitura da Carga continua somente leitura; consultas constantes ──────────────────────────────────────────────────


def test_consultar_a_carga_com_capacidade_individual_nao_escreve_nem_gera_evento(client_admin, db_session, empresa, regra) -> None:
    a = pessoa(db_session, empresa)
    put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))
    ausencia(client_admin, a.id, SEG2, SEG2)
    antes = (db_session.scalar(select(func.count()).select_from(Evento)), db_session.scalar(select(func.count()).select_from(UsuarioJornada)), db_session.scalar(select(func.count()).select_from(UsuarioAusencia)))
    declaracoes: list[str] = []

    def captura(conn, cursor, statement, parameters, context, executemany):
        declaracoes.append(statement)

    motor = db_session.get_bind()
    event.listen(motor, "before_cursor_execute", captura)
    try:
        assert carga(client_admin, semana=SEMANA2).status_code == 200
    finally:
        event.remove(motor, "before_cursor_execute", captura)
    assert not [s for s in declaracoes if s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
    assert not [s for s in declaracoes if "sessoes_trabalho" in s or "demanda_status_intervalos" in s]
    assert antes == (db_session.scalar(select(func.count()).select_from(Evento)), db_session.scalar(select(func.count()).select_from(UsuarioJornada)), db_session.scalar(select(func.count()).select_from(UsuarioAusencia)))


def _consultas(db, chamada) -> int:
    declaracoes: list[str] = []

    def captura(conn, cursor, statement, parameters, context, executemany):
        declaracoes.append(statement)

    motor = db.get_bind()
    event.listen(motor, "before_cursor_execute", captura)
    try:
        chamada()
    finally:
        event.remove(motor, "before_cursor_execute", captura)
    return len(declaracoes)


def test_quantidade_de_consultas_nao_cresce_com_usuarios_jornadas_e_ausencias(client_admin, db_session, empresa, regra) -> None:
    deps = [_departamento(db_session, empresa) for _ in range(2)]
    pequenas = [pessoa(db_session, empresa, dep=deps[i % 2]) for i in range(3)]
    for p in pequenas:
        etapa_carga(db_session, empresa, est=120, ini=SEG, fim=SEG2, users=[p])
    put_jornada(client_admin, pequenas[0].id, seg_a_sex("09:00", "15:00"))
    ausencia(client_admin, pequenas[1].id, SEG2, SEG2)
    carga(client_admin, semana=SEMANA2)  # aquecimento (autenticação/permissões)
    pequeno = _consultas(db_session, lambda: carga(client_admin, semana=SEMANA2))

    muitas = [pessoa(db_session, empresa, dep=deps[i % 2]) for i in range(60)]
    for i, p in enumerate(muitas):
        put_jornada(client_admin, p.id, seg_a_sex("09:00", "13:00" if i % 2 else "15:00"))
        ausencia(client_admin, p.id, SEG2 + timedelta(days=i % 5), SEG2 + timedelta(days=i % 5 + 1), tipo="folga")
        etapa_carga(db_session, empresa, est=60 + i, ini=SEG, fim=SEG3, users=[p, muitas[(i + 1) % 60]], deps=[deps[i % 2]])
    carga(client_admin, semana=SEMANA2)  # novo aquecimento: os `commit()` dos service expiram o usuário autenticado, e recarregá-lo não é custo da Carga
    grande = _consultas(db_session, lambda: carga(client_admin, semana=SEMANA2))
    assert pequeno == grande, (pequeno, grande)
    print(f"LOAD_QUERY_COUNT_SMALL={pequeno} LOAD_QUERY_COUNT_LARGE={grande}")


def test_diagnostico_de_desempenho_com_200_usuarios(client_admin, db_session, empresa, regra) -> None:
    deps = [_departamento(db_session, empresa) for _ in range(5)]
    pessoas = [pessoa(db_session, empresa, dep=deps[i % 5]) for i in range(210)]
    for i, p in enumerate(pessoas):
        if i % 3 == 0:
            put_jornada(client_admin, p.id, seg_a_sex("09:00", "15:00"))
        if i % 4 == 0:
            ausencia(client_admin, p.id, SEG2 + timedelta(days=i % 5), SEG2 + timedelta(days=i % 5 + 2))
    for i in range(320):
        etapa_carga(db_session, empresa, est=30 + i, ini=SEG + timedelta(days=i % 4), fim=SEG3 + timedelta(days=i % 5), users=[pessoas[i % 210], pessoas[(i * 7 + 1) % 210]], deps=[deps[i % 5]])
    carga(client_admin, semana=SEMANA2)  # aquecimento (os `commit()` do service expiram o usuário autenticado)
    inicio = time.perf_counter()
    consultas = _consultas(db_session, lambda: carga(client_admin, semana=SEMANA2))
    decorrido_ms = (time.perf_counter() - inicio) * 1000
    corpo = carga(client_admin, semana=SEMANA2).json()
    assert len(corpo["pessoas"]) == 211  # 210 + o admin autenticado (elegível como qualquer pessoa ativa)
    print(f"PERF_200_USERS_QUERIES={consultas} PERF_200_USERS_MS={decorrido_ms:.0f} (diagnóstico, sem cache e sem índice novo)")


# ── elegibilidade e atomicidade ──────────────────────────────────────────────────────────────────────────────────


def test_usuario_inativo_continua_fora_da_capacidade_mesmo_com_jornada_e_ausencia(client_admin, db_session, empresa, regra) -> None:
    ativo, inativo = pessoa(db_session, empresa, nome="Ativa"), pessoa(db_session, empresa, nome="Inativa")
    put_jornada(client_admin, inativo.id, seg_a_sex("09:00", "15:00"))
    ausencia(client_admin, inativo.id, SEG2, SEG2)
    inativo.status = "inativo"
    db_session.commit()
    ids = [p["usuarioId"] for p in carga(client_admin, semana=SEMANA2).json()["pessoas"]]
    assert ativo.id in ids and inativo.id not in ids


def test_evento_e_mudanca_na_mesma_transacao_falha_do_evento_desfaz_tudo(client_admin, db_session, empresa, regra, monkeypatch) -> None:
    from app.api.routes import usuario_capacidade as rotas

    a = pessoa(db_session, empresa)

    def falha(*_args, **_kwargs):
        raise RuntimeError("evento indisponível")

    monkeypatch.setattr(rotas.service.event_publisher, "publish", falha)
    try:
        put_jornada(client_admin, a.id, seg_a_sex("09:00", "15:00"))
    except RuntimeError:
        pass  # o TestClient repropaga a exceção do servidor: o que importa é o estado do banco
    assert db_session.scalar(select(func.count()).select_from(UsuarioJornada)) == 0
    try:
        ausencia(client_admin, a.id, SEG2, SEG2)
    except RuntimeError:
        pass
    assert db_session.scalar(select(func.count()).select_from(UsuarioAusencia)) == 0
