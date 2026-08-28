"""Migração do JSONB legado de Modelo de Campanha em Projeto (Fase 2G.5C4) — ver
app/cli/migrar_modelo_campanha_projetos.py.

Usa `db_session` normalmente (mesmo padrão de test_projeto_modelo_campanha_snapshot.py):
`migrar()` faz commit por Projeto, mas a fixture liga a sessão a uma SAVEPOINT
(`join_transaction_mode="create_savepoint"`) — o commit da aplicação nunca escapa da
transação externa do teste, que sempre reverte no fim. Isso permite testar idempotência
(chamar `migrar()` duas vezes na mesma sessão) sem deixar rastro no banco real.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli.migrar_modelo_campanha_projetos import migrar
from app.models.departamento import Departamento
from app.models.empresa import Empresa
from app.models.evento import Evento
from app.models.projeto import Projeto
from app.models.projeto_modelo_campanha import ProjetoModeloCampanha, ProjetoModeloCampanhaItem
from app.models.tipo_tarefa import TipoTarefa
from app.models.workflow_modelo import WorkflowModelo
from app.repositories.projeto_modelo_campanha_repository import ProjetoModeloCampanhaRepository

# --------------------------------------------------------------------------------------
# Fábricas diretas no model — mesmo padrão de test_projeto_modelo_campanha_snapshot.py
# --------------------------------------------------------------------------------------


def _projeto(db: Session, empresa: Empresa, *, modelo_campanha=None, modelo_campanha_id: str | None = None) -> Projeto:
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
        status="planejamento",
        prioridade="media",
        modelo_campanha_id=modelo_campanha_id,
        modelo_campanha=modelo_campanha,
        created_at=agora,
        updated_at=agora,
    )
    db.add(projeto)
    db.flush()
    return projeto


def _tipo_tarefa(db: Session, empresa: Empresa, *, status: str = "ativo") -> TipoTarefa:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    tipo = TipoTarefa(
        id=str(uuid.uuid4()), empresa_id=empresa.id, nome=f"Tipo {sufixo}", nome_normalizado=f"tipo {sufixo}",
        ordem=0, status=status, created_at=agora, updated_at=agora,
    )
    db.add(tipo)
    db.flush()
    return tipo


def _workflow_modelo(db: Session, empresa: Empresa, *, status: str = "ativo") -> WorkflowModelo:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    workflow = WorkflowModelo(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"wf-{sufixo}", codigo_referencia=f"W26{sufixo[:6]}",
        ano_referencia=26, sequencial_referencia=int(sufixo[:5], 16) % 900000, nome=f"Workflow {sufixo}",
        nome_normalizado=f"workflow {sufixo}", status=status, created_at=agora, updated_at=agora,
    )
    db.add(workflow)
    db.flush()
    return workflow


def _departamento(db: Session, empresa: Empresa, *, status: str = "ativo") -> Departamento:
    agora = datetime.now(timezone.utc)
    sufixo = uuid.uuid4().hex[:8]
    departamento = Departamento(
        id=str(uuid.uuid4()), empresa_id=empresa.id, codigo_interno=f"dep-{sufixo}", codigo_referencia=f"D26{sufixo[:6]}",
        ano_referencia=26, sequencial_referencia=int(sufixo[:5], 16) % 900000, nome=f"Departamento {sufixo}",
        nome_normalizado=f"departamento {sufixo}", cor_identificacao="blue", status=status,
        created_at=agora, updated_at=agora,
    )
    db.add(departamento)
    db.flush()
    return departamento


def _item_legado(
    *,
    id_="item-1",
    nome_demanda="Post de lançamento",
    tipo_tarefa_id=None,
    tipo_tarefa_nome=None,
    briefing_base="",
    prioridade_padrao="media",
    workflow_sugerido_id=None,
    workflow_sugerido_nome=None,
    responsavel_ou_setor_sugerido_id=None,
    responsavel_ou_setor_sugerido_nome=None,
) -> dict:
    return {
        "id": id_,
        "nome_demanda": nome_demanda,
        "tipo_tarefa_id": tipo_tarefa_id,
        "tipo_tarefa_nome": tipo_tarefa_nome,
        "briefing_base": briefing_base,
        "prioridade_padrao": prioridade_padrao,
        "workflow_sugerido_id": workflow_sugerido_id,
        "workflow_sugerido_nome": workflow_sugerido_nome,
        "responsavel_ou_setor_sugerido_id": responsavel_ou_setor_sugerido_id,
        "responsavel_ou_setor_sugerido_nome": responsavel_ou_setor_sugerido_nome,
    }


def _snapshot(db: Session, projeto_id: str) -> ProjetoModeloCampanha | None:
    return ProjetoModeloCampanhaRepository().get_by_projeto_id(db, projeto_id)


def _itens(db: Session, cabecalho_id: str) -> list[ProjetoModeloCampanhaItem]:
    return ProjetoModeloCampanhaRepository().list_itens(db, cabecalho_id)


# --------------------------------------------------------------------------------------
# Dry-run (item 24)
# --------------------------------------------------------------------------------------


def test_dry_run_nao_altera_banco(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    relatorio = migrar(db_session, dry_run=True)

    assert _snapshot(db_session, projeto.id) is None
    assert relatorio.migrados == 1
    assert relatorio.itens_materializados == 1


def test_dry_run_projeto_com_legado_valido_aparece_migravel(db_session: Session, empresa: Empresa) -> None:
    _projeto(db_session, empresa, modelo_campanha=[_item_legado(), _item_legado(id_="item-2")])

    relatorio = migrar(db_session, dry_run=True)

    assert relatorio.analisados == 1
    assert relatorio.migraveis == 1
    assert relatorio.migrados == 1
    assert relatorio.itens_materializados == 2


def test_dry_run_nao_publica_evento(db_session: Session, empresa: Empresa) -> None:
    contagem_antes = db_session.scalar(select(Evento).limit(1))
    total_antes = len(db_session.scalars(select(Evento)).all())
    _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    migrar(db_session, dry_run=True)

    total_depois = len(db_session.scalars(select(Evento)).all())
    assert total_depois == total_antes


def test_dry_run_nao_deixa_commit_persistente(db_session: Session, empresa: Empresa) -> None:
    """Mesma sessão, chamado duas vezes: se o primeiro dry-run tivesse commitado algo, a
    segunda chamada veria um snapshot que não deveria existir."""
    _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    migrar(db_session, dry_run=True)
    relatorio_2 = migrar(db_session, dry_run=True)

    assert relatorio_2.migrados == 1  # ainda "migrável" — nada foi persistido na primeira rodada
    assert relatorio_2.ja_migrados == 0


# --------------------------------------------------------------------------------------
# Idempotência (item 25)
# --------------------------------------------------------------------------------------


def test_primeira_execucao_cria_snapshot(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.migrados == 1
    cabecalho = _snapshot(db_session, projeto.id)
    assert cabecalho is not None
    assert len(_itens(db_session, cabecalho.id)) == 1


def test_segunda_execucao_nao_duplica(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])
    migrar(db_session, dry_run=False)
    cabecalho_1 = _snapshot(db_session, projeto.id)

    relatorio_2 = migrar(db_session, dry_run=False)

    cabecalho_2 = _snapshot(db_session, projeto.id)
    assert relatorio_2.ja_migrados == 1
    assert relatorio_2.migrados == 0
    assert cabecalho_2.id == cabecalho_1.id  # cabeçalho continua único, não recriado
    assert len(_itens(db_session, cabecalho_2.id)) == 1  # itens não duplicaram


def test_snapshot_operacional_existente_nunca_e_sobrescrito(db_session: Session, empresa: Empresa) -> None:
    """Snapshot criado pela aplicação real (POST /aplicar), não pela CLI — mesma regra de
    idempotência se aplica: JSONB legado (mesmo que presente) nunca sobrescreve."""
    projeto = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])
    agora = datetime.now(timezone.utc)
    cabecalho_real = ProjetoModeloCampanha(
        id=str(uuid.uuid4()), projeto_id=projeto.id, modelo_campanha_origem_id=None,
        modelo_campanha_nome_snapshot="Modelo Real", aplicado_at=agora, aplicado_por_usuario_id=str(uuid.uuid4()),
        created_at=agora, updated_at=agora,
    )
    db_session.add(cabecalho_real)
    db_session.flush()

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.ja_migrados == 1
    assert relatorio.migrados == 0
    cabecalho_depois = _snapshot(db_session, projeto.id)
    assert cabecalho_depois.id == cabecalho_real.id
    assert cabecalho_depois.modelo_campanha_nome_snapshot == "Modelo Real"


# --------------------------------------------------------------------------------------
# Legado vazio (item 26)
# --------------------------------------------------------------------------------------


def test_legado_null_ignorado(db_session: Session, empresa: Empresa) -> None:
    _projeto(db_session, empresa, modelo_campanha=None)

    relatorio = migrar(db_session, dry_run=True)

    assert relatorio.sem_legado == 1
    assert relatorio.migraveis == 0


def test_legado_lista_vazia_ignorado(db_session: Session, empresa: Empresa) -> None:
    _projeto(db_session, empresa, modelo_campanha=[])

    relatorio = migrar(db_session, dry_run=True)

    assert relatorio.sem_legado == 1
    assert relatorio.migraveis == 0


# --------------------------------------------------------------------------------------
# Materialização (item 27)
# --------------------------------------------------------------------------------------


def test_materializa_projeto_com_multiplos_itens(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(
        db_session,
        empresa,
        modelo_campanha=[
            _item_legado(id_="item-1", nome_demanda="Primeiro item", prioridade_padrao="alta"),
            _item_legado(id_="item-2", nome_demanda="Segundo item", prioridade_padrao="baixa", briefing_base="Briefing X"),
        ],
    )

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.migrados == 1
    cabecalho = _snapshot(db_session, projeto.id)
    assert cabecalho.modelo_campanha_origem_id is None
    assert cabecalho.modelo_campanha_nome_snapshot is None
    assert cabecalho.aplicado_at is None
    assert cabecalho.aplicado_por_usuario_id is None

    itens = _itens(db_session, cabecalho.id)
    assert len(itens) == 2
    assert [i.ordem for i in itens] == [1, 2]
    assert itens[0].nome == "Primeiro item"
    assert itens[0].prioridade_padrao == "alta"
    assert itens[1].nome == "Segundo item"
    assert itens[1].prioridade_padrao == "baixa"
    assert itens[1].briefing_padrao == "Briefing X"
    # ids sempre novos, nunca o "item-1"/"item-2" textual do legado
    assert all(len(item.id) == 36 and item.id not in {"item-1", "item-2"} for item in itens)


def test_item_sem_referencias_nasce_com_pecas_e_fks_nulas(db_session: Session, empresa: Empresa) -> None:
    """Legado nunca teve Peça — todo item nasce com peca_id/peca_nome_snapshot NULL,
    independente de referências resolvidas ou não."""
    projeto = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.peca_id is None
    assert item.peca_nome_snapshot is None


# --------------------------------------------------------------------------------------
# Referências (item 28)
# --------------------------------------------------------------------------------------


def test_referencia_uuid_valido_mesma_empresa_e_preservada(db_session: Session, empresa: Empresa) -> None:
    tipo = _tipo_tarefa(db_session, empresa)
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(tipo_tarefa_id=tipo.id, tipo_tarefa_nome=tipo.nome)],
    )

    migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id == tipo.id
    assert item.tipo_tarefa_nome_snapshot == tipo.nome


def test_referencia_uuid_invalido_vira_fk_null_e_unresolved(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(tipo_tarefa_id="nao-e-um-uuid", tipo_tarefa_nome="Tipo Legado")],
    )

    relatorio = migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id is None
    assert item.tipo_tarefa_nome_snapshot == "Tipo Legado"
    assert relatorio.referencias_nao_resolvidas == 1


def test_referencia_uuid_inexistente_vira_fk_null_e_unresolved(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(workflow_sugerido_id=str(uuid.uuid4()), workflow_sugerido_nome="Workflow Sumido")],
    )

    relatorio = migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.workflow_modelo_id is None
    assert item.workflow_modelo_nome_snapshot == "Workflow Sumido"
    assert relatorio.referencias_nao_resolvidas == 1


def test_referencia_cross_tenant_vira_fk_null_sem_vazamento(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    tipo_alheio = _tipo_tarefa(db_session, outra_empresa)
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(tipo_tarefa_id=tipo_alheio.id, tipo_tarefa_nome=tipo_alheio.nome)],
    )

    relatorio = migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id is None  # nunca vaza o id de outra Empresa pra FK
    assert item.tipo_tarefa_nome_snapshot == tipo_alheio.nome  # nome histórico preservado mesmo assim
    assert relatorio.referencias_nao_resolvidas == 1


def test_referencia_arquivada_mesma_empresa_e_preservada(db_session: Session, empresa: Empresa) -> None:
    """Migração histórica aceita lifecycle diferente de vínculo novo — arquivado/inativo não
    bloqueia a resolução (ver docstring do módulo)."""
    workflow_arquivado = _workflow_modelo(db_session, empresa, status="arquivado")
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(workflow_sugerido_id=workflow_arquivado.id, workflow_sugerido_nome=workflow_arquivado.nome)],
    )

    relatorio = migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.workflow_modelo_id == workflow_arquivado.id
    assert relatorio.referencias_nao_resolvidas == 0


# --------------------------------------------------------------------------------------
# Responsável (item 29)
# --------------------------------------------------------------------------------------


def test_responsavel_legado_resolve_como_departamento_nunca_usuario(db_session: Session, empresa: Empresa) -> None:
    departamento = _departamento(db_session, empresa)
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[
            _item_legado(
                responsavel_ou_setor_sugerido_id=departamento.id,
                responsavel_ou_setor_sugerido_nome=departamento.nome,
            )
        ],
    )

    migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.responsavel_departamento_id == departamento.id
    assert item.responsavel_usuario_id is None


# --------------------------------------------------------------------------------------
# Nomes históricos (item 30)
# --------------------------------------------------------------------------------------


def test_nome_historico_do_jsonb_prevalece_sobre_nome_atual(db_session: Session, empresa: Empresa) -> None:
    tipo = _tipo_tarefa(db_session, empresa)
    tipo.nome = "Nome B"  # nome ATUAL do cadastro, depois de "renomeado"
    db_session.flush()

    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(tipo_tarefa_id=tipo.id, tipo_tarefa_nome="Nome A")],  # nome histórico do JSONB
    )

    migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id == tipo.id
    assert item.tipo_tarefa_nome_snapshot == "Nome A"


def test_nome_ausente_no_jsonb_usa_fallback_do_cadastro_atual(db_session: Session, empresa: Empresa) -> None:
    """Quando o JSONB não trouxe nome nenhum mas a referência resolve, o nome atual do
    cadastro é usado como fallback técnico — documentado, não fingido como histórico."""
    tipo = _tipo_tarefa(db_session, empresa)
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(tipo_tarefa_id=tipo.id, tipo_tarefa_nome=None)],
    )

    migrar(db_session, dry_run=False)

    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id == tipo.id
    assert item.tipo_tarefa_nome_snapshot == tipo.nome


# --------------------------------------------------------------------------------------
# Fake refs (item 31) — ids deliberadamente inválidos, mesmo padrão do QA local
# --------------------------------------------------------------------------------------


def test_ids_fake_nao_geram_excecao_global(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[
            _item_legado(
                nome_demanda="Peça de tipo antigo",
                tipo_tarefa_id="tipo-fake-indisponivel-9999",
                tipo_tarefa_nome="Tipo de Tarefa Legado",
                workflow_sugerido_id="workflow-fake-arquivado-9999",
                workflow_sugerido_nome="Workflow Legado Arquivado",
            )
        ],
    )

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.migrados == 1
    assert relatorio.falharam == 0
    item = _itens(db_session, _snapshot(db_session, projeto.id).id)[0]
    assert item.tipo_tarefa_id is None
    assert item.tipo_tarefa_nome_snapshot == "Tipo de Tarefa Legado"
    assert item.workflow_modelo_id is None
    assert item.workflow_modelo_nome_snapshot == "Workflow Legado Arquivado"
    assert relatorio.referencias_nao_resolvidas == 2


# --------------------------------------------------------------------------------------
# Falha estrutural (item 32)
# --------------------------------------------------------------------------------------


def test_estrutura_corrompida_nao_cria_nada_mas_nao_trava_os_demais(db_session: Session, empresa: Empresa) -> None:
    projeto_corrompido = _projeto(db_session, empresa, modelo_campanha=[{"id": "x"}])  # sem nome_demanda
    projeto_valido = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.falharam == 1
    assert relatorio.migrados == 1
    assert _snapshot(db_session, projeto_corrompido.id) is None
    assert _snapshot(db_session, projeto_valido.id) is not None

    falha = next(p for p in relatorio.projetos if p.projeto_id == projeto_corrompido.id)
    assert falha.status == "falhou"
    assert falha.motivo_falha is not None


def test_modelo_campanha_nao_e_lista_e_falha_estrutural(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(db_session, empresa, modelo_campanha={"nao": "e uma lista"})

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.falharam == 1
    assert _snapshot(db_session, projeto.id) is None


def test_prioridade_invalida_e_falha_estrutural(db_session: Session, empresa: Empresa) -> None:
    projeto = _projeto(
        db_session, empresa,
        modelo_campanha=[_item_legado(prioridade_padrao="urgente")],
    )

    relatorio = migrar(db_session, dry_run=False)

    assert relatorio.falharam == 1
    assert _snapshot(db_session, projeto.id) is None


# --------------------------------------------------------------------------------------
# Legado intocado (item 33)
# --------------------------------------------------------------------------------------


def test_legado_permanece_intacto_apos_modo_real(db_session: Session, empresa: Empresa) -> None:
    itens_originais = [_item_legado()]
    projeto = _projeto(db_session, empresa, modelo_campanha=itens_originais, modelo_campanha_id="algum-valor-legado")

    migrar(db_session, dry_run=False)

    db_session.refresh(projeto)
    assert projeto.modelo_campanha == itens_originais
    assert projeto.modelo_campanha_id == "algum-valor-legado"


# --------------------------------------------------------------------------------------
# Filtros --empresa-id / --projeto-id
# --------------------------------------------------------------------------------------


def test_filtro_por_projeto_id_restringe_escopo(db_session: Session, empresa: Empresa) -> None:
    projeto_alvo = _projeto(db_session, empresa, modelo_campanha=[_item_legado()])
    _projeto(db_session, empresa, modelo_campanha=[_item_legado()])  # outro Projeto, fora do escopo

    relatorio = migrar(db_session, dry_run=True, projeto_id=projeto_alvo.id)

    assert relatorio.analisados == 1
    assert relatorio.projetos[0].projeto_id == projeto_alvo.id


def test_filtro_por_empresa_id_restringe_escopo(
    db_session: Session, empresa: Empresa, outra_empresa: Empresa
) -> None:
    _projeto(db_session, empresa, modelo_campanha=[_item_legado()])
    _projeto(db_session, outra_empresa, modelo_campanha=[_item_legado()])

    relatorio = migrar(db_session, dry_run=True, empresa_id=empresa.id)

    assert relatorio.analisados == 1
    assert relatorio.projetos[0].codigo_referencia.startswith("P26")
