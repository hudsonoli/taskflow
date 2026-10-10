from datetime import datetime, timezone
from typing import get_args
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.escopo import (
    EscopoDemanda,
    EscopoNaoAutorizadoError,
    EscopoSolicitado,
    resolver_escopo_demanda,
)
from app.core.filtros_lista import parse_csv_enum, parse_csv_uuids
from app.db.session import get_db
from app.api.escopo_leitura import EscopoLeitura, demanda_com_acesso_de_workflow
from app.dependencies.auth import get_current_user_password_ready
from app.dependencies.authorization import require_admin_or_gestor
from app.dependencies.permissoes import require_demandas_criar, require_permissao
from app.models.usuario import Usuario
from app.repositories.demanda_repository import OrigemDemanda, SortDemandas
from app.schemas.demanda import (
    DemandaAjusteRegistrar,
    DemandaArquivar,
    DemandaConclusaoEmailRegistrar,
    DemandaCreate,
    DemandaDiretorioRead,
    DemandaEstatisticasRead,
    DemandaOperacionalEmAndamentoRead,
    DemandaPrioridade,
    DemandaRead,
    DemandaResumoAtendimentoRead,
    DemandaResumoDepartamentoRead,
    DemandaResumoMinhaHomeRead,
    DemandaStatus,
    DemandaResumoOperacionalRead,
    DemandaUpdate,
)
from app.schemas.demanda_historico import DemandaHistoricoEventoRead
from app.services.demanda_historico_service import DemandaHistoricoService
from app.services.demanda_workflow_service import (
    DemandaWorkflowAcaoInvalidaError,
    DemandaWorkflowConflitoError,
    DemandaWorkflowEtapaNaoEncontradaError,
    DemandaWorkflowSemAutoridadeError,
    DemandaWorkflowService,
)
from app.services.demanda_service import (
    DemandaClienteForaDoEscopoError,
    DemandaClienteInvalidoError,
    DemandaDepartamentoForaDoEscopoError,
    DemandaDepartamentoInvalidoError,
    DemandaForaDeExpedienteError,
    DemandaInvalidTransitionError,
    DemandaMotivoBloqueioObrigatorioError,
    DemandaNotFoundError,
    DemandaProjetoClienteIncompativelError,
    DemandaProjetoInvalidoError,
    DemandaResponsavelForaDoEscopoError,
    DemandaService,
    DemandaUsuarioInvalidoError,
    DemandaWorkflowModeloInvalidoError,
)

router = APIRouter(
    prefix="/demandas",
    tags=["demandas"],
    dependencies=[Depends(get_current_user_password_ready)],
)
demanda_service = DemandaService()
workflow_service = DemandaWorkflowService(demanda_service=demanda_service)
historico_service = DemandaHistoricoService()

# Demanda é o primeiro domínio OPERACIONAL: ao contrário de Cliente, Projeto e Fornecedor,
# ler/editar é aberto a qualquer autenticado — sempre dentro do escopo resolvido. Criar
# (Fase 2G.10B, D1.1) tem regra própria — admin/gestor por perfil, Head/Atendimento por
# relação, nunca operador comum por default — ver `require_demandas_criar()`
# (app/dependencies/permissoes.py). Arquivar e restaurar seguem restritos a admin/gestor,
# como nos cadastros, via `require_permissao("demandas.arquivar")`.


def handle_demanda_error(exc: Exception) -> None:
    if isinstance(exc, DemandaNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, EscopoNaoAutorizadoError):
        # 403 e NÃO lista vazia: lista vazia esconderia erro de permissão atrás de um
        # resultado que parece legítimo.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, DemandaForaDeExpedienteError):
        # 409 estruturado — a interface só apresenta; a janela vem do servidor para não haver
        # duas fontes da mesma regra.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "FORA_DE_EXPEDIENTE",
                "message": str(exc),
                "expediente": {
                    # Janela de HOJE — pode vir tudo `None` quando o dia não é útil (ver
                    # docstring de DemandaForaDeExpedienteError, Fase 2G.3).
                    "manhaInicio": exc.dia_hoje.manha_inicio,
                    "manhaFim": exc.dia_hoje.manha_fim,
                    "tardeInicio": exc.dia_hoje.tarde_inicio,
                    "tardeFim": exc.dia_hoje.tarde_fim,
                    "toleranciaRetomadaMinutos": exc.tolerancia_retomada_minutos,
                },
            },
        ) from exc
    if isinstance(exc, DemandaInvalidTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    # Progressão de workflow (Fase 8A). 409 estruturado: a interface recarrega o estado e mostra a mensagem do servidor.
    if isinstance(exc, DemandaWorkflowConflitoError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": exc.codigo, "message": str(exc)}
        ) from exc
    if isinstance(exc, DemandaWorkflowEtapaNaoEncontradaError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, DemandaWorkflowSemAutoridadeError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, DemandaWorkflowAcaoInvalidaError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(
        exc,
        (
            DemandaMotivoBloqueioObrigatorioError,
            DemandaClienteInvalidoError,
            DemandaClienteForaDoEscopoError,
            DemandaProjetoInvalidoError,
            DemandaProjetoClienteIncompativelError,
            DemandaUsuarioInvalidoError,
            DemandaResponsavelForaDoEscopoError,
            DemandaDepartamentoInvalidoError,
            DemandaDepartamentoForaDoEscopoError,
            DemandaWorkflowModeloInvalidoError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _escopo(
    db: Session, current_user: Usuario, solicitado: EscopoSolicitado | None = None
) -> EscopoDemanda:
    try:
        return resolver_escopo_demanda(db, current_user, solicitado)
    except Exception as exc:
        handle_demanda_error(exc)
        raise  # inalcançável — handle_demanda_error sempre levanta


def _parse_departamento_ids(raw: str | None) -> list[str] | None:
    """`departamentoId` aceita um único UUID (compatibilidade) ou uma lista separada por
    vírgula (D2-B3: Pauta filtra por vários departamentos, semântica OR). Segmentos vazios
    (vírgula sobrando, espaços) são descartados silenciosamente — mesma tolerância já usada
    para `status` no D2-B1. O que sobra precisa ser um UUID válido; um segmento inválido é
    422, nunca ignorado silenciosamente — diferente de `status`, aqui o valor vira FK direta
    de uma consulta, então "silenciosamente ignorar o inválido" esconderia um erro de
    integração do cliente em vez de recusá-lo."""
    if raw is None:
        return None
    segmentos = [segmento.strip() for segmento in raw.split(",") if segmento.strip()]
    if not segmentos:
        return None
    for segmento in segmentos:
        try:
            UUID(segmento)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"departamentoId inválido: '{segmento}' não é um UUID",
            ) from exc
    return segmentos


MAX_IDS_LOTE = 100

PRIORIDADES_DEMANDA = ("baixa", "media", "alta")
STATUS_DEMANDA = get_args(DemandaStatus)


def _parse_ids_lote(raw: str) -> list[str]:
    """`ids` de `/demandas/por-ids` — CSV obrigatório, ao contrário de `departamentoId`
    (opcional, `None` vira "sem filtro"). Aqui não existe "sem filtro": ausência de conteúdo
    útil (vazio, só vírgulas/espaços) é 422, nunca uma lista vazia processada em silêncio —
    devolver `[]` para "ids=" pareceria sucesso e esconderia um erro de integração do
    cliente. Deduplicado (mesmo ID pode vir repetido de múltiplas sessões/eventos que
    apontam pra mesma Demanda) preservando primeira ocorrência; limite de
    `MAX_IDS_LOTE` é sobre IDs ÚNICOS, não sobre o CSV bruto."""
    segmentos = [segmento.strip() for segmento in raw.split(",") if segmento.strip()]
    if not segmentos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids não pode ser vazio",
        )
    unicos: list[str] = []
    vistos: set[str] = set()
    for segmento in segmentos:
        try:
            UUID(segmento)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ids inválido: '{segmento}' não é um UUID",
            ) from exc
        if segmento not in vistos:
            vistos.add(segmento)
            unicos.append(segmento)
    if len(unicos) > MAX_IDS_LOTE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ids aceita no máximo {MAX_IDS_LOTE} valores únicos, recebido {len(unicos)}",
        )
    return unicos


def _normalize_datetime(value: datetime | None) -> datetime | None:
    """Mesma semântica de `eventos.py`/`sessoes_trabalho.py` (não extraída para um helper
    compartilhado nesta fase — ver política D2-B3: extrair ampliaria o diff para arquivos
    fora do escopo deste bloco sem necessidade funcional). Datetime sem timezone é recusado:
    aceitar um "hoje 00:00" ambíguo aqui reintroduziria exatamente o risco de fuso que este
    parâmetro existe para eliminar — o cliente já calcula o intervalo no fuso local do
    navegador e manda o instante UTC resultante."""
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filtros de prazo devem incluir timezone",
        )
    return value.astimezone(timezone.utc)


@router.post("", response_model=DemandaRead, status_code=status.HTTP_201_CREATED)
def create_demanda(
    payload: DemandaCreate,
    current_user: Usuario = Depends(require_demandas_criar()),
    db: Session = Depends(get_db),
):
    try:
        criada = demanda_service.create_demanda(
            db, payload, empresa_id=current_user.empresa_id, actor=current_user
        )
        return demanda_service.to_read(db, criada, usuario=current_user)
    except Exception as exc:
        handle_demanda_error(exc)


@router.get("", response_model=list[DemandaRead])
def list_demandas(
    status_demanda: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, alias="search"),
    cliente_id: str | None = Query(default=None, alias="clienteId"),
    projeto_id: str | None = Query(default=None, alias="projetoId"),
    departamento_id: str | None = Query(default=None, alias="departamentoId"),
    responsavel_id: str | None = Query(default=None, alias="responsavelId"),
    equipe_id: str | None = Query(default=None, alias="equipeId"),
    prioridade: str | None = Query(default=None),
    origem: OrigemDemanda | None = Query(default=None),
    prazo_inicio: datetime | None = Query(default=None, alias="prazoInicio"),
    prazo_fim: datetime | None = Query(default=None, alias="prazoFim"),
    atrasada: bool = Query(default=False),
    nao_finalizada: bool = Query(default=False, alias="naoFinalizada"),
    status_excluir: str | None = Query(default=None, alias="statusExcluir"),
    cliente_id_excluir: str | None = Query(default=None, alias="clienteIdExcluir"),
    projeto_id_excluir: str | None = Query(default=None, alias="projetoIdExcluir"),
    responsavel_id_excluir: str | None = Query(default=None, alias="responsavelIdExcluir"),
    equipe_id_excluir: str | None = Query(default=None, alias="equipeIdExcluir"),
    prioridade_excluir: str | None = Query(default=None, alias="prioridadeExcluir"),
    # Só para `sort=fila_pessoal` (Meu Dia): "agora" e as fronteiras de "hoje" vêm do cliente (fuso local), como no resumo pessoal.
    agora: datetime | None = Query(default=None),
    hoje_inicio: datetime | None = Query(default=None, alias="hojeInicio"),
    hoje_fim: datetime | None = Query(default=None, alias="hojeFim"),
    sort: SortDemandas = Query(default=SortDemandas.NUMERO_OPERACIONAL_DESC),
    escopo_solicitado: EscopoSolicitado | None = Query(default=None, alias="escopo"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """**Sem parâmetro nenhum já vem escopado.** `escopo=` só estreita, nunca amplia."""
    escopo = _escopo(db, current_user, escopo_solicitado)
    if sort == SortDemandas.FILA_PESSOAL and (agora is None or hoje_inicio is None or hoje_fim is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort=fila_pessoal exige agora, hojeInicio e hojeFim",
        )
    demandas = demanda_service.list_demandas(
        db,
        escopo=escopo,
        status=status_demanda,
        search=search,
        cliente_ids=parse_csv_uuids(cliente_id, "clienteId"),
        projeto_ids=parse_csv_uuids(projeto_id, "projetoId"),
        departamento_ids=_parse_departamento_ids(departamento_id),
        responsavel_ids=parse_csv_uuids(responsavel_id, "responsavelId"),
        equipe_ids=parse_csv_uuids(equipe_id, "equipeId"),
        prioridades=parse_csv_enum(prioridade, "prioridade", PRIORIDADES_DEMANDA),
        status_excluir=parse_csv_enum(status_excluir, "statusExcluir", STATUS_DEMANDA),
        cliente_ids_excluir=parse_csv_uuids(cliente_id_excluir, "clienteIdExcluir"),
        projeto_ids_excluir=parse_csv_uuids(projeto_id_excluir, "projetoIdExcluir"),
        responsavel_ids_excluir=parse_csv_uuids(responsavel_id_excluir, "responsavelIdExcluir"),
        equipe_ids_excluir=parse_csv_uuids(equipe_id_excluir, "equipeIdExcluir"),
        prioridades_excluir=parse_csv_enum(prioridade_excluir, "prioridadeExcluir", PRIORIDADES_DEMANDA),
        origem=origem,
        prazo_inicio=_normalize_datetime(prazo_inicio),
        prazo_fim=_normalize_datetime(prazo_fim),
        atrasada=atrasada,
        # A Pauta global é a operação em ABERTO: concluída/cancelada nunca entram (arquivada já fica fora por padrão).
        # Meu Departamento (Fase 7C.2) também abre na operação em ABERTO — mas só POR PADRÃO: com `status` explícito (ex.: Concluída),
        # respeita o pedido, para o Head continuar consultando o que já terminou. Decidido aqui, antes de limit/offset.
        nao_finalizada=(
            nao_finalizada
            or escopo_solicitado is EscopoSolicitado.PAUTA
            or (escopo_solicitado is EscopoSolicitado.MEU_DEPARTAMENTO and not status_demanda)
        ),
        agora=_normalize_datetime(agora),
        hoje_inicio=_normalize_datetime(hoje_inicio),
        hoje_fim=_normalize_datetime(hoje_fim),
        sort=sort,
        limit=limit,
        offset=offset,
    )
    # `podeAvancar` (Fase 8A) é por usuário; a Pauta global é leitura — ver a Demanda ali não concede ação.
    return demanda_service.to_read_lote(
        db, demandas, usuario=current_user, somente_leitura=escopo_solicitado is EscopoSolicitado.PAUTA
    )


@router.get("/diretorio", response_model=list[DemandaDiretorioRead])
def list_diretorio(
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """Escopado como a listagem, e sem as arquivadas — arquivada não é opção de vínculo novo."""
    escopo = _escopo(db, current_user)
    demandas = demanda_service.list_demandas(db, escopo=escopo, limit=200)
    return [DemandaDiretorioRead.model_validate(demanda) for demanda in demandas]


@router.get("/estatisticas", response_model=DemandaEstatisticasRead)
def estatisticas_demandas(
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """Cards de `DemandasStats` (tela Tarefas), sobre o universo INTEGRAL do escopo de quem
    pede — nunca as 200 Demandas de `AppDataContext`. Mesma autoridade e mesmo escopo da
    listagem (`require_permissao("demandas.visualizar")` + `_escopo(db, current_user)` default,
    sem override): cada usuário vê os números do que a tela dele lista. Sem filtros: a tela
    nunca amarrou os cards à busca nem ao filtro de status."""
    escopo = _escopo(db, current_user)
    return DemandaEstatisticasRead.model_validate(demanda_service.estatisticas(db, escopo=escopo))


@router.get("/minhas/resumo", response_model=DemandaResumoAtendimentoRead)
def resumo_minhas_demandas(
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """D2-B4 — os nove indicadores de MinhasDemandasView, sobre o universo INTEGRAL do
    escopo Atendimento (nunca uma página). Mesma autoridade da listagem: recorte fixo em
    `EscopoSolicitado.ATENDIMENTO` — quem não é Atendimento recebe 403, nunca zeros."""
    escopo = _escopo(db, current_user, EscopoSolicitado.ATENDIMENTO)
    resumo = demanda_service.resumo_atendimento(db, escopo=escopo)
    return DemandaResumoAtendimentoRead.model_validate(resumo)


@router.get("/meu-departamento/resumo", response_model=DemandaResumoDepartamentoRead)
def resumo_meu_departamento(
    departamento_id: UUID = Query(alias="departamentoId"),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """D2-B5 — indicadores de MeuDepartamentoView, sobre o universo INTEGRAL do
    departamento (nunca uma página, nunca os 8 filtros de UI — mesma semântica de
    `tarefasDoDept`/`classificacoesDept` pré-migração). `departamentoId` é o departamento
    ÚNICO já resolvido pelo frontend (`resolverHeadDepartamento`, `.find()` — o primeiro
    departamento formal do usuário, não "todos os que ele lidera"); este endpoint não decide
    qual é, só recebe. Autoridade: `EscopoSolicitado.MEU_DEPARTAMENTO` — quem não é head de
    nenhum departamento recebe 403. Um `departamentoId` fora do(s) departamento(s) que o
    usuário lidera não é 403 — o predicado de escopo e o filtro funcional apenas não se
    intersectam, resultando em zeros (mesma regra de list() com departamento fora do
    escopo)."""
    escopo = _escopo(db, current_user, EscopoSolicitado.MEU_DEPARTAMENTO)
    resumo = demanda_service.resumo_departamento(
        db, escopo=escopo, departamento_id=str(departamento_id), empresa_id=current_user.empresa_id
    )
    return DemandaResumoDepartamentoRead.model_validate(resumo)


@router.get("/minha-home/resumo", response_model=DemandaResumoMinhaHomeRead)
def resumo_minha_home(
    agora: datetime = Query(...),
    hoje_inicio: datetime = Query(..., alias="hojeInicio"),
    hoje_fim: datetime = Query(..., alias="hojeFim"),
    semana_inicio: datetime = Query(..., alias="semanaInicio"),
    semana_fim: datetime = Query(..., alias="semanaFim"),
    ontem_inicio: datetime = Query(..., alias="ontemInicio"),
    ontem_fim: datetime = Query(..., alias="ontemFim"),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """D2-D2 — os 11 indicadores do Dashboard pessoal (`/meu-dia`), sobre o universo INTEGRAL
    permitido do usuário (escopo normal AND responsável N:N == `current_user.id`) — nunca as
    200 demandas globais de `AppDataContext`. Sem restrição de perfil: qualquer usuário com
    `demandas.visualizar` recebe o PRÓPRIO resumo, nunca 403 (diferente de
    `/minhas/resumo`/`/meu-departamento/resumo`, que exigem Atendimento/Head — aqui não há
    recorte de papel, só "sou responsável").

    Todas as fronteiras temporais são obrigatórias e vêm do cliente (mesma fotografia de
    `new Date()`, ver DashboardView.tsx) — esta rota não calcula "hoje"/"ontem"/"semana"."""
    escopo = _escopo(db, current_user)
    resumo = demanda_service.resumo_minha_home(
        db,
        escopo=escopo,
        usuario_id=current_user.id,
        agora=_normalize_datetime(agora),
        hoje_inicio=_normalize_datetime(hoje_inicio),
        hoje_fim=_normalize_datetime(hoje_fim),
        semana_inicio=_normalize_datetime(semana_inicio),
        semana_fim=_normalize_datetime(semana_fim),
        ontem_inicio=_normalize_datetime(ontem_inicio),
        ontem_fim=_normalize_datetime(ontem_fim),
    )
    return DemandaResumoMinhaHomeRead.model_validate(resumo)


@router.get("/operacional/resumo", response_model=DemandaResumoOperacionalRead)
def resumo_operacional(
    periodo_inicio: datetime = Query(..., alias="periodoInicio"),
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    """D2-D3A — Central de Tráfego (`TrafegoIndicadoresDemandas`). Autorização própria,
    real no backend — `require_admin_or_gestor` (`perfil_base in {"admin","gestor"}`),
    **não** apenas `require_permissao("demandas.visualizar")`: operador autenticado recebe
    403, nunca um resumo escopado parcial (política congelada do diagnóstico D2-D3 —
    Tráfego já exige exatamente este mesmo conjunto de perfis para `GET
    /sessoes-trabalho`, via `require_trafego_gerenciar`).

    Escopo: `_escopo(db, current_user)` default, sem override — para quem passa no gate
    acima (sempre admin/gestor), isso resolve `visao_total=True` pelo mecanismo normal, não
    por hardcode aqui. `periodoInicio` é "desde quando", sem teto — mesma semântica de
    `periodoParaDataInicio` no frontend (hoje/24h/7d/30d)."""
    escopo = _escopo(db, current_user)
    resumo = demanda_service.resumo_operacional(
        db, escopo=escopo, periodo_inicio=_normalize_datetime(periodo_inicio)
    )
    return DemandaResumoOperacionalRead.model_validate(resumo)


@router.get("/operacional/em-andamento", response_model=DemandaOperacionalEmAndamentoRead)
def em_andamento_operacional(
    current_user: Usuario = Depends(require_admin_or_gestor),
    db: Session = Depends(get_db),
):
    """D2-D3A — RegraExpedienteView. Mesma autorização/escopo de `resumo_operacional`
    acima, endpoint dedicado porque `emAndamento` não depende de período — ver
    `DemandaRepository.count_em_andamento_operacional`."""
    escopo = _escopo(db, current_user)
    total = demanda_service.count_em_andamento_operacional(db, escopo=escopo)
    return DemandaOperacionalEmAndamentoRead(em_andamento=total)


@router.get("/por-ids", response_model=list[DemandaDiretorioRead])
def list_demandas_por_ids(
    ids: str = Query(...),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """D2-C — resolução histórica em lote. Registrada ANTES de `/{demanda_id}` (mesmo motivo
    de `/diretorio`, `/minhas/resumo`, `/meu-departamento/resumo`): sem isso, `por-ids`
    casaria com o path param UUID e nunca seria alcançada.

    Semântica de `GET /{demanda_id}` (arquivada incluída, escopo idêntico), NÃO de
    `GET /demandas`/`/diretorio` (que excluem arquivada) — histórico precisa continuar
    resolvendo uma Demanda mesmo depois de arquivada, se o usuário ainda tem escopo pra ela.

    ID inexistente, de outra empresa ou fora do escopo simplesmente não aparece na resposta —
    nunca 404/null por item: um sinal diferenciado por item permitiria mapear a base variando
    o UUID, exatamente o que `get_no_escopo` já evita no acesso individual."""
    ids_unicos = _parse_ids_lote(ids)
    escopo = _escopo(db, current_user)
    demandas = demanda_service.list_por_ids(db, escopo=escopo, ids=ids_unicos)
    return [DemandaDiretorioRead.model_validate(demanda) for demanda in demandas]


@router.get("/{demanda_id}", response_model=DemandaRead)
def get_demanda(
    demanda_id: UUID,
    escopo_leitura: EscopoLeitura | None = Query(default=None, alias="escopo"),
    current_user: Usuario = Depends(require_permissao("demandas.visualizar")),
    db: Session = Depends(get_db),
):
    """Fora da empresa **ou fora do escopo** → 404. Conhecer o UUID não autoriza nada.

    `?escopo=pauta` (Fase 7C.1): LEITURA do detalhe de uma demanda exibida na Pauta global — só para quem tem a Pauta global (403 para
    os demais) e sempre dentro da empresa do token. Não dá poder de escrita: PATCH/arquivar/etc. seguem no escopo-base."""
    try:
        # Escopo-base (ou Pauta) e, se a demanda não estiver nele, o escopo DERIVADO da etapa atual do Workflow (Fase 8C.1): quem é responsável
        # pela etapa atual (ou Head do departamento dela) abre a demanda para ler e agir no Workflow — sem virar `DemandaResponsavel`.
        demanda, via_workflow = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service, escopo_leitura)
        leitura = demanda_service.to_read(db, demanda, usuario=current_user, somente_leitura=escopo_leitura == "pauta")
        leitura.acesso_apenas_workflow = via_workflow
        return leitura
    except Exception as exc:
        handle_demanda_error(exc)


@router.patch("/{demanda_id}", response_model=DemandaRead)
def update_demanda(
    demanda_id: UUID,
    payload: DemandaUpdate,
    current_user: Usuario = Depends(require_permissao("demandas.editar")),
    db: Session = Depends(get_db),
):
    """A resolução escopada acontece ANTES de qualquer escrita — fora do escopo é 404 e nada
    é persistido."""
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        atualizada = demanda_service.update_demanda(
            db, demanda, payload, actor=current_user
        )
        return demanda_service.to_read(db, atualizada, usuario=current_user)
    except Exception as exc:
        handle_demanda_error(exc)


# "Excluir" = arquivar (soft-delete permanente). Nunca há delete físico de demanda.
@router.post("/{demanda_id}/arquivar", response_model=DemandaRead)
def arquivar_demanda(
    demanda_id: UUID,
    payload: DemandaArquivar,
    current_user: Usuario = Depends(require_permissao("demandas.arquivar")),
    db: Session = Depends(get_db),
):
    try:
        # O escopo se SOMA à permissão: admin/gestor têm visão total, então na prática só a
        # empresa filtra — mas a checagem fica aqui para a regra nunca depender só de
        # `require_permissao`.
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        arquivada = demanda_service.arquivar_demanda(
            db,
            demanda,
            motivo_arquivamento=payload.motivo_arquivamento,
            actor_usuario_id=current_user.id,
        )
        return demanda_service.to_read(db, arquivada, usuario=current_user)
    except Exception as exc:
        handle_demanda_error(exc)


@router.post("/{demanda_id}/restaurar", response_model=DemandaRead)
def restaurar_demanda(
    demanda_id: UUID,
    current_user: Usuario = Depends(require_permissao("demandas.arquivar")),
    db: Session = Depends(get_db),
):
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        restaurada = demanda_service.restaurar_demanda(
            db, demanda, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, restaurada, usuario=current_user)
    except Exception as exc:
        handle_demanda_error(exc)


# Ajuste e conclusão-por-e-mail (Fase 2E.4) são operacionais como checklist/arquivos/
# comentários (ver instrução da fase, item 13 da 2E.3, reaplicado aqui): qualquer
# autenticado com escopo sobre a Demanda aciona, sem gate de perfil — ao contrário de
# arquivar/restaurar, que seguem admin/gestor.


@router.post(
    "/{demanda_id}/ajustes", response_model=DemandaHistoricoEventoRead, status_code=status.HTTP_201_CREATED
)
def registrar_ajuste(
    demanda_id: UUID,
    payload: DemandaAjusteRegistrar,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Não muda nenhum campo da Demanda — só produz uma entrada na timeline (ver
    DemandaService.registrar_ajuste)."""
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        evento = demanda_service.registrar_ajuste(
            db, demanda, payload.tipo, actor_usuario_id=current_user.id
        )
        return historico_service.to_read(evento)
    except Exception as exc:
        handle_demanda_error(exc)


@router.post("/{demanda_id}/conclusao-email", response_model=DemandaRead)
def registrar_conclusao_email(
    demanda_id: UUID,
    payload: DemandaConclusaoEmailRegistrar,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    try:
        escopo = _escopo(db, current_user)
        demanda = demanda_service.get_demanda(db, str(demanda_id), escopo=escopo)
        atualizada = demanda_service.registrar_conclusao_email(
            db, demanda, enviado=payload.enviado, actor_usuario_id=current_user.id
        )
        return demanda_service.to_read(db, atualizada, usuario=current_user)
    except Exception as exc:
        handle_demanda_error(exc)


# Progressão do snapshot de Workflow (Fase 8A). Escopo-BASE (nunca o da Pauta global: leitura não concede ação) + autoridade da etapa
# (responsável, admin/gestor do tenant ou Head do departamento da etapa — `core/workflow_autoridade.py`). O cliente indica QUAL etapa
# quer avançar; o servidor decide a próxima. Sem payload: não existe `nextStepId`.


@router.post("/{demanda_id}/workflow/etapas/{etapa_id}/concluir", response_model=DemandaRead)
def concluir_etapa_workflow(
    demanda_id: UUID,
    etapa_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Conclui a etapa ATUAL de tipo `execucao` e ativa a próxima. Etapa de aprovação → 422; sem autoridade → 403; etapa que não é
    (mais) a atual, workflow concluído/sem etapas → 409."""
    try:
        # Escopo-base OU escopo derivado da etapa atual (Fase 8C.1); a autoridade final (responsável/Head/admin-gestor) é do serviço.
        demanda, via_workflow = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service)
        atualizada = workflow_service.concluir_etapa(db, demanda, etapa_id=str(etapa_id), actor=current_user)
        resposta = demanda_service.to_read(db, atualizada, usuario=current_user)
        resposta.acesso_apenas_workflow = via_workflow
        return resposta
    except Exception as exc:
        handle_demanda_error(exc)


@router.post("/{demanda_id}/workflow/etapas/{etapa_id}/aprovar", response_model=DemandaRead)
def aprovar_etapa_workflow(
    demanda_id: UUID,
    etapa_id: UUID,
    current_user: Usuario = Depends(get_current_user_password_ready),
    db: Session = Depends(get_db),
):
    """Aprova a etapa ATUAL de tipo `aprovacao` e ativa a próxima. Mesmas regras de `concluir` (etapa de execução → 422)."""
    try:
        # Escopo-base OU escopo derivado da etapa atual (Fase 8C.1); a autoridade final (responsável/Head/admin-gestor) é do serviço.
        demanda, via_workflow = demanda_com_acesso_de_workflow(db, current_user, str(demanda_id), demanda_service)
        atualizada = workflow_service.aprovar_etapa(db, demanda, etapa_id=str(etapa_id), actor=current_user)
        resposta = demanda_service.to_read(db, atualizada, usuario=current_user)
        resposta.acesso_apenas_workflow = via_workflow
        return resposta
    except Exception as exc:
        handle_demanda_error(exc)
