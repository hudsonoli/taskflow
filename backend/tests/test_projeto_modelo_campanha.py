"""Testes estruturais do snapshot de Modelo de Campanha em Projeto (Fase 2G.5C1) — só
schema/model, sem service/API ainda. Validam constraints do banco diretamente via
SQLAlchemy, mesmo padrão de fixtures de tests/test_modelo_campanha.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import categoria_peca  # noqa: F401 — registra Peca.categoria_id -> categorias_peca
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.modelo_campanha import ModeloCampanha
from app.models.peca import Peca
from app.models.projeto import Projeto
from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem
from app.models.tipo_tarefa import TipoTarefa
from app.models.usuario import Usuario
from app.models.workflow_modelo import WorkflowModelo
from tests.fixtures.usuarios import _criar_usuario_com_credencial


def _projeto(db: Session, empresa: Empresa, *, status: str = "planejamento") -> Projeto:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    projeto = Projeto(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_referencia=f"P26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Projeto {sufixo}",
        nome_normalizado=f"projeto {sufixo}",
        status=status,
        prioridade="media",
        created_at=agora,
        updated_at=agora,
    )
    db.add(projeto)
    db.flush()
    return projeto


def _modelo_campanha(db: Session, empresa: Empresa) -> ModeloCampanha:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    modelo = ModeloCampanha(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"Modelo {sufixo}",
        nome_normalizado=f"modelo {sufixo}",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(modelo)
    db.flush()
    return modelo


def _peca(db: Session, empresa: Empresa, *, status: str = "ativo") -> Peca:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    peca = Peca(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        categoria_id=None,
        nome=f"Peça {sufixo}",
        codigo_legado=None,
        briefing_padrao="",
        sindicato_ativo=False,
        status=status,
        created_at=agora,
        updated_at=agora,
    )
    db.add(peca)
    db.flush()
    return peca


def _tipo_tarefa(db: Session, empresa: Empresa) -> TipoTarefa:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    tipo = TipoTarefa(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        nome=f"Tipo {sufixo}",
        nome_normalizado=f"tipo {sufixo}",
        ordem=0,
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(tipo)
    db.flush()
    return tipo


def _workflow_modelo(db: Session, empresa: Empresa) -> WorkflowModelo:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    workflow = WorkflowModelo(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"wf-{sufixo}",
        codigo_referencia=f"W26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Workflow {sufixo}",
        nome_normalizado=f"workflow {sufixo}",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(workflow)
    db.flush()
    return workflow


def _departamento(db: Session, empresa: Empresa) -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        codigo_interno=f"dep-{sufixo}",
        codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26,
        sequencial_referencia=int(sufixo[:5], 16) % 900000,
        nome=f"Departamento {sufixo}",
        nome_normalizado=f"departamento {sufixo}",
        cor_identificacao="blue",
        status="ativo",
        created_at=agora,
        updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _usuario(db: Session, empresa: Empresa) -> Usuario:
    return _criar_usuario_com_credencial(db, empresa=empresa, perfil_base="operador", email_prefixo="pmc")


_NAO_INFORMADO = object()


def _cabecalho(
    db: Session,
    projeto: Projeto,
    *,
    modelo: ModeloCampanha | None = None,
    nome_snapshot: str | None = "Modelo aplicado",
    aplicado_at: datetime | None | object = _NAO_INFORMADO,
    aplicado_por_usuario_id: str | None = None,
) -> ProjetoModeloCampanha:
    agora = datetime.now(timezone.utc)
    # Sentinela distingue "não informado" (default = aplicação nova, agora) de
    # "explicitamente None" (cenário de legado sem data de aplicação original).
    aplicado_at_final = agora if aplicado_at is _NAO_INFORMADO else aplicado_at
    cabecalho = ProjetoModeloCampanha(
        id=str(uuid.uuid4()),
        projeto_id=projeto.id,
        modelo_campanha_origem_id=modelo.id if modelo else None,
        modelo_campanha_nome_snapshot=nome_snapshot,
        aplicado_at=aplicado_at_final,
        aplicado_por_usuario_id=aplicado_por_usuario_id,
        created_at=agora,
        updated_at=agora,
    )
    db.add(cabecalho)
    db.flush()
    return cabecalho


def _item(db: Session, cabecalho: ProjetoModeloCampanha, *, ordem: int, **overrides) -> ProjetoModeloCampanhaItem:
    agora = datetime.now(timezone.utc)
    defaults = dict(
        id=str(uuid.uuid4()),
        projeto_modelo_campanha_id=cabecalho.id,
        ordem=ordem,
        nome=f"Item {ordem}",
        briefing_padrao=None,
        prioridade_padrao="media",
        peca_id=None,
        peca_nome_snapshot=None,
        tipo_tarefa_id=None,
        tipo_tarefa_nome_snapshot=None,
        workflow_modelo_id=None,
        workflow_modelo_nome_snapshot=None,
        responsavel_usuario_id=None,
        responsavel_usuario_nome_snapshot=None,
        responsavel_departamento_id=None,
        responsavel_departamento_nome_snapshot=None,
        created_at=agora,
        updated_at=agora,
    )
    defaults.update(overrides)
    item = ProjetoModeloCampanhaItem(**defaults)
    db.add(item)
    db.flush()
    return item


# --------------------------------------------------------------------------------------
# Cardinalidade / cabeçalho
# --------------------------------------------------------------------------------------


def test_projeto_aceita_zero_snapshot(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    resultado = (
        db_session.query(ProjetoModeloCampanha).filter(ProjetoModeloCampanha.projeto_id == projeto.id).first()
    )
    assert resultado is None


def test_projeto_aceita_no_maximo_um_cabecalho(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    _cabecalho(db_session, projeto)

    with pytest.raises(IntegrityError):
        _cabecalho(db_session, projeto)
    db_session.rollback()


def test_cabecalho_aceita_multiplos_projetos_distintos(db_session: Session, empresa: Empresa) -> None:
    projeto_a = _projeto(db_session, empresa)
    projeto_b = _projeto(db_session, empresa)
    cabecalho_a = _cabecalho(db_session, projeto_a)
    cabecalho_b = _cabecalho(db_session, projeto_b)
    assert cabecalho_a.id != cabecalho_b.id


# --------------------------------------------------------------------------------------
# Itens / ordem / prioridade / responsável
# --------------------------------------------------------------------------------------


def test_cabecalho_aceita_n_itens(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    _item(db_session, cabecalho, ordem=1)
    _item(db_session, cabecalho, ordem=2)
    _item(db_session, cabecalho, ordem=3)

    itens = (
        db_session.query(ProjetoModeloCampanhaItem)
        .filter(ProjetoModeloCampanhaItem.projeto_modelo_campanha_id == cabecalho.id)
        .order_by(ProjetoModeloCampanhaItem.ordem)
        .all()
    )
    assert [item.ordem for item in itens] == [1, 2, 3]


def test_ordem_duplicada_rejeitada(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    _item(db_session, cabecalho, ordem=1)

    with pytest.raises(IntegrityError):
        _item(db_session, cabecalho, ordem=1)
    db_session.rollback()


def test_ordem_zero_rejeitada(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)

    with pytest.raises(IntegrityError):
        _item(db_session, cabecalho, ordem=0)
    db_session.rollback()


def test_prioridade_invalida_rejeitada(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)

    with pytest.raises(IntegrityError):
        _item(db_session, cabecalho, ordem=1, prioridade_padrao="urgentissima")
    db_session.rollback()


def test_usuario_e_departamento_simultaneos_rejeitados(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)

    with pytest.raises(IntegrityError):
        _item(
            db_session,
            cabecalho,
            ordem=1,
            responsavel_usuario_id=usuario.id,
            responsavel_departamento_id=departamento.id,
        )
    db_session.rollback()


def test_item_aceita_somente_usuario_ou_somente_departamento(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)

    item_usuario = _item(db_session, cabecalho, ordem=1, responsavel_usuario_id=usuario.id)
    item_departamento = _item(db_session, cabecalho, ordem=2, responsavel_departamento_id=departamento.id)
    assert item_usuario.responsavel_usuario_id == usuario.id
    assert item_departamento.responsavel_departamento_id == departamento.id


# --------------------------------------------------------------------------------------
# Snapshot de nomes / campos nullable de proveniência
# --------------------------------------------------------------------------------------


def test_nome_snapshot_persiste_mesmo_com_fk_nula(db_session: Session, empresa: Empresa) -> None:
    """Referência indisponível (FK NULL) preserva o nome histórico — nunca some
    silenciosamente. Cenário real: migração do JSONB legado com id fabricado/inválido."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    item = _item(
        db_session,
        cabecalho,
        ordem=1,
        peca_id=None,
        peca_nome_snapshot="Peça Legada Indisponível",
        tipo_tarefa_id=None,
        tipo_tarefa_nome_snapshot="Tipo de Tarefa Legado",
    )
    assert item.peca_id is None
    assert item.peca_nome_snapshot == "Peça Legada Indisponível"
    assert item.tipo_tarefa_id is None
    assert item.tipo_tarefa_nome_snapshot == "Tipo de Tarefa Legado"


def test_item_com_referencias_reais_grava_fk_e_nome_snapshot(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    peca = _peca(db_session, empresa)
    tipo = _tipo_tarefa(db_session, empresa)
    workflow = _workflow_modelo(db_session, empresa)

    item = _item(
        db_session,
        cabecalho,
        ordem=1,
        peca_id=peca.id,
        peca_nome_snapshot=peca.nome,
        tipo_tarefa_id=tipo.id,
        tipo_tarefa_nome_snapshot=tipo.nome,
        workflow_modelo_id=workflow.id,
        workflow_modelo_nome_snapshot=workflow.nome,
    )
    assert item.peca_id == peca.id
    assert item.tipo_tarefa_id == tipo.id
    assert item.workflow_modelo_id == workflow.id


def test_campos_de_provenance_e_aplicacao_podem_ser_nulos_para_legado(
    db_session: Session, empresa: Empresa
) -> None:
    """A migração futura do JSONB legado (Fase 2G.5C4) materializa snapshots que não têm de
    qual Modelo vieram, nem quando, nem quem aplicou — esses dados nunca existiram no JSONB.
    O schema precisa aceitar isso sem exigir um valor inventado."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(
        db_session,
        projeto,
        modelo=None,
        nome_snapshot=None,
        aplicado_at=None,
        aplicado_por_usuario_id=None,
    )
    assert cabecalho.modelo_campanha_origem_id is None
    assert cabecalho.modelo_campanha_nome_snapshot is None
    assert cabecalho.aplicado_at is None
    assert cabecalho.aplicado_por_usuario_id is None


def test_cabecalho_com_aplicacao_nova_preenche_os_quatro_campos(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    usuario = _usuario(db_session, empresa)
    agora = datetime.now(timezone.utc)

    cabecalho = _cabecalho(
        db_session,
        projeto,
        modelo=modelo,
        nome_snapshot=modelo.nome,
        aplicado_at=agora,
        aplicado_por_usuario_id=usuario.id,
    )
    assert cabecalho.modelo_campanha_origem_id == modelo.id
    assert cabecalho.modelo_campanha_nome_snapshot == modelo.nome
    assert cabecalho.aplicado_at is not None
    assert cabecalho.aplicado_por_usuario_id == usuario.id


# --------------------------------------------------------------------------------------
# FKs cross-tabela — cascade / preservação
# --------------------------------------------------------------------------------------


def test_referencias_sem_cascade_nao_sao_afetadas_por_arquivamento(db_session: Session, empresa: Empresa) -> None:
    """Simula o "arquivamento" real (nunca DELETE) de uma Peça depois que o item já a
    referencia — o item continua íntegro (comportamento real é responsabilidade do service
    futuro, aqui só confirmamos que a FK sem CASCADE não interfere na alteração de status)."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    peca = _peca(db_session, empresa)
    item = _item(db_session, cabecalho, ordem=1, peca_id=peca.id, peca_nome_snapshot=peca.nome)

    peca.status = "arquivado"
    db_session.flush()

    db_session.refresh(item)
    assert item.peca_id == peca.id
    assert item.peca_nome_snapshot == peca.nome


def test_deletar_peca_referenciada_e_bloqueado_pela_fk(db_session: Session, empresa: Empresa) -> None:
    """FK sem CASCADE nas referências (Peça/TipoTarefa/Workflow/Usuário/Departamento) é
    RESTRICT por padrão do Postgres — confirma que nenhuma entidade externa desapareceria
    "de graça" nem um item ficaria orfão por uma exclusão física indevida. Delete físico é
    só um instrumento estrutural deste teste (transação isolada, revertida ao final) — nunca
    o fluxo real do domínio, que é soft-delete."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    peca = _peca(db_session, empresa)
    _item(db_session, cabecalho, ordem=1, peca_id=peca.id, peca_nome_snapshot=peca.nome)

    with pytest.raises(IntegrityError):
        db_session.delete(peca)
        db_session.flush()
    db_session.rollback()


def test_cascade_projeto_cabecalho_itens(db_session: Session, empresa: Empresa) -> None:
    """Deletar o Projeto (só neste teste estrutural, transação isolada e revertida — nunca o
    fluxo real do domínio) cascateia para o cabeçalho e para os itens, sem deixar órfão."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    item = _item(db_session, cabecalho, ordem=1)
    cabecalho_id, item_id = cabecalho.id, item.id

    db_session.delete(projeto)
    db_session.flush()
    # A cascata é do banco (ON DELETE CASCADE), não do ORM — cabeçalho/item nunca foram
    # marcados para exclusão no unit-of-work, então o identity map ficaria com o objeto
    # "vivo" em cache se não expirarmos antes de reconsultar.
    db_session.expire_all()

    assert db_session.get(ProjetoModeloCampanha, cabecalho_id) is None
    assert db_session.get(ProjetoModeloCampanhaItem, item_id) is None


def test_cascade_nao_apaga_entidades_externas_referenciadas(db_session: Session, empresa: Empresa) -> None:
    """Deletar Projeto → cabeçalho → itens nunca deve arrastar Peça/TipoTarefa/Workflow/
    Usuário/Departamento — a cascata só flui na direção Projeto → snapshot, nunca do
    snapshot para as entidades que ele referencia."""
    projeto = _projeto(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto)
    peca = _peca(db_session, empresa)
    tipo = _tipo_tarefa(db_session, empresa)
    workflow = _workflow_modelo(db_session, empresa)
    usuario = _usuario(db_session, empresa)
    departamento = _departamento(db_session, empresa)
    _item(
        db_session,
        cabecalho,
        ordem=1,
        peca_id=peca.id,
        tipo_tarefa_id=tipo.id,
        workflow_modelo_id=workflow.id,
        responsavel_departamento_id=departamento.id,
    )
    peca_id, tipo_id, workflow_id, usuario_id, departamento_id = (
        peca.id,
        tipo.id,
        workflow.id,
        usuario.id,
        departamento.id,
    )

    db_session.delete(projeto)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(Peca, peca_id) is not None
    assert db_session.get(TipoTarefa, tipo_id) is not None
    assert db_session.get(WorkflowModelo, workflow_id) is not None
    assert db_session.get(Usuario, usuario_id) is not None
    assert db_session.get(Departamento, departamento_id) is not None


def test_arquivar_modelo_origem_nao_afeta_cabecalho(db_session: Session, empresa: Empresa) -> None:
    """Arquivar (nunca deletar) o Modelo de origem preserva o cabeçalho e o nome snapshot
    intactos — só um DELETE físico do Modelo (que o domínio não faz) acionaria o SET NULL."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto, modelo=modelo, nome_snapshot=modelo.nome)

    modelo.status = "arquivado"
    db_session.flush()

    db_session.refresh(cabecalho)
    assert cabecalho.modelo_campanha_origem_id == modelo.id
    assert cabecalho.modelo_campanha_nome_snapshot == modelo.nome


def test_deletar_modelo_origem_seta_null_no_cabecalho(db_session: Session, empresa: Empresa) -> None:
    """ON DELETE SET NULL na FK de proveniência — confirma o comportamento defensivo mesmo
    que o domínio nunca dispare isto na prática (Modelo só é arquivado, nunca apagado)."""
    projeto = _projeto(db_session, empresa)
    modelo = _modelo_campanha(db_session, empresa)
    cabecalho = _cabecalho(db_session, projeto, modelo=modelo, nome_snapshot=modelo.nome)

    db_session.delete(modelo)
    db_session.flush()

    db_session.refresh(cabecalho)
    assert cabecalho.modelo_campanha_origem_id is None
    # Nome snapshot não é recalculado nem apagado — só a FK vira NULL.
    assert cabecalho.modelo_campanha_nome_snapshot == modelo.nome


# --------------------------------------------------------------------------------------
# Projeto legado (JSONB) intocado
# --------------------------------------------------------------------------------------


def test_projeto_jsonb_legado_continua_funcionando_sem_relacao_com_snapshot(
    db_session: Session, empresa: Empresa
) -> None:
    """O snapshot novo é aditivo — projetos.modelo_campanha (JSONB) continua gravável e
    legível normalmente, sem nenhuma interferência da tabela nova."""
    projeto = _projeto(db_session, empresa)
    projeto.modelo_campanha = [{"id": "item-1", "nome_demanda": "Post legado"}]
    db_session.flush()
    db_session.refresh(projeto)

    assert projeto.modelo_campanha == [{"id": "item-1", "nome_demanda": "Post legado"}]
    assert projeto.modelo_campanha_id is None

    cabecalho = (
        db_session.query(ProjetoModeloCampanha).filter(ProjetoModeloCampanha.projeto_id == projeto.id).first()
    )
    assert cabecalho is None
