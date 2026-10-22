from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field, model_validator

from app.schemas.esforco import EsforcoMinutos
from app.schemas.sla_regra import SlaUnidadePrazo

# `arquivada` no feminino acompanha o vocabulário do próprio domínio (concluida, cancelada,
# pausada). Os demais domínios usam masculino; cada service tem sua constante local, então
# não há código genérico dependendo da grafia.
DemandaStatus = Literal[
    "rascunho",
    "planejada",
    "em_execucao",
    "pausada",
    "bloqueada",
    "aguardando_cliente",
    "concluida",
    "cancelada",
    "arquivada",
]
# `arquivada` fica fora: entra pela rota de arquivamento, com motivo obrigatório.
DemandaStatusEditavel = Literal[
    "rascunho",
    "planejada",
    "em_execucao",
    "pausada",
    "bloqueada",
    "aguardando_cliente",
    "concluida",
    "cancelada",
]
DemandaPrioridade = Literal["baixa", "media", "alta"]

# Campos que a interface conhecia mas ainda não tinham tabela. A tupla existe vazia de
# propósito — não removida — para o histórico ficar rastreável: quem chegar aqui e for
# adicionar um campo novo por simetria com Demanda deve perguntar primeiro se ele tem
# persistência real, e não presumir que Demanda ainda tolera campo "de fachada".
#
# `checklist`/`arquivos` saíram na Fase 2E.3; `comentarios`/`historico` saíram na Fase 2E.4.
# Todos os quatro têm tabela própria e endpoint dedicado agora — nenhum faz parte do payload
# de Demanda nem para leitura nem para escrita (ver DemandaRead, que não declara nenhum
# deles). Enviar qualquer um dos quatro em `DemandaCreate`/`DemandaUpdate` continua sendo
# 422 por `extra="forbid"` — não porque a tupla abaixo os liste, mas porque eles nunca foram
# declarados como campo de `_DemandaCamposComuns`.
CAMPOS_SEM_PERSISTENCIA: tuple[str, ...] = ()

# `workflowEtapas`/`etapaAtualId` saíram de CAMPOS_SEM_PERSISTENCIA na Fase 2E.2: agora têm
# tabela (`demanda_workflow_etapas`) e aparecem de verdade em DemandaRead. Continuam **não
# aceitos em Create/Update** — não porque faltem persistência, mas porque não há endpoint de
# transição de etapa nesta fase (ver DemandaWorkflowEtapaWrite ausente de propósito). O único
# jeito de uma Demanda ganhar etapas é `workflowModeloId` na criação, que as materializa a
# partir do template.
WorkflowEtapaTipo = Literal["execucao", "aprovacao"]
WorkflowUnidadePrazo = Literal["dias_corridos", "dias_uteis", "horas"]
DemandaWorkflowEtapaStatus = Literal["pendente", "em_execucao", "pausada", "concluida"]


def ensure_timezone_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class _DemandaCamposComuns(BaseModel):
    pit: str | None = Field(default=None, max_length=64)
    briefing: str | None = Field(default=None, max_length=8000)
    prioridade: DemandaPrioridade = "media"
    sinalizada: bool = False
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    # Campo MANUAL e independente — não deriva de `prazoHoras` das etapas, e nunca derivou.
    # A Pauta ordena por ele.
    prazo_etapa_atual: datetime | None = Field(default=None, alias="prazoEtapaAtual")
    enviado_cliente_em: datetime | None = Field(default=None, alias="enviadoClienteEm")
    prazo_retorno_cliente: datetime | None = Field(default=None, alias="prazoRetornoCliente")
    retorno_recebido_em: datetime | None = Field(default=None, alias="retornoRecebidoEm")
    email_conclusao_enviado: bool = Field(default=False, alias="emailConclusaoEnviado")
    email_conclusao_data: datetime | None = Field(default=None, alias="emailConclusaoData")
    responsavel_ids: list[UUID] | None = Field(default=None, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] | None = Field(
        default=None, alias="departamentoResponsavelIds"
    )


# `extra="forbid"` cobre dois grupos de campos proibidos, pelo mesmo motivo — ignorar em
# silêncio faria o cliente da API acreditar que o valor foi aceito:
#
# 1. **emitidos pelo servidor**: empresaId, actorUsuarioId, codigoReferencia, anoReferencia,
#    sequencialReferencia, numeroOperacional, criadoPorUsuarioId, agenciaId, codigoInterno, e
#    (Fase 2G.6D1) todo o snapshot/deadline de SLA — slaRegraId, slaRegraNomeSnapshot, os
#    quatro campos de prazo snapshot, slaConsiderarExpedienteSnapshot, slaResolvidoAt,
#    slaPrimeiraRespostaLimiteEm, slaResolucaoLimiteEm. SLA é resolvido pelo servidor uma
#    única vez na criação (ver DemandaService.create_demanda) — nenhum desses campos é
#    declarado em `_DemandaCamposComuns`, então enviá-los é 422 pelo `extra="forbid"` abaixo,
#    não por um validador dedicado. Mesmo raciocínio para slaPrimeiraRespostaEm/
#    slaPrimeiraRespostaDentroPrazo (Fase 2G.6D2B) — fixados só pelo primeiro comentário da
#    equipe (DemandaComentarioService.criar_comentario) — e para slaResolvidoEm/
#    slaResolvidoDentroPrazo (Fase 2G.6D3B) — fixado só pela primeira transição real para
#    concluida (DemandaService.update_demanda); nenhum dos dois por Create/Update de Demanda;
# 2. **sem persistência nesta fase**: workflowEtapas, etapaAtualId, checklist, arquivos,
#    comentarios, historico — ver CAMPOS_SEM_PERSISTENCIA.
#
# O segundo grupo é o que impede a falha silenciosa que este desenho existe para evitar: o
# formulário montava etapas de workflow e elas sumiriam sem aviso.
class DemandaCreateEtapaResponsaveis(BaseModel):
    """Responsáveis EXPLÍCITOS de UMA etapa do workflow aplicado, definidos já na criação da Demanda (substituem, para essa etapa, o que o modelo trazia). A etapa é
    identificada pelo id da etapa do MODELO (`modeloEtapaId`) — inequívoco entre a tela, o modelo e a etapa materializada. Listas vazias = sem responsabilidade explícita
    (a etapa herda os responsáveis gerais da tarefa)."""

    modelo_etapa_id: UUID = Field(alias="modeloEtapaId")
    usuario_responsavel_ids: list[UUID] = Field(default_factory=list, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(default_factory=list, alias="departamentoResponsavelIds")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaWorkflowResponsaveisUpdate(BaseModel):
    """Substituição COMPLETA dos responsáveis EXPLÍCITOS de uma etapa (o editor apresenta o estado inteiro). Os dois campos são obrigatórios; `[]` + `[]` remove a
    responsabilidade explícita e a etapa volta a herdar os responsáveis gerais da tarefa (nunca "sem responsável forçado")."""

    usuario_responsavel_ids: list[UUID] = Field(alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(alias="departamentoResponsavelIds")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaCreate(_DemandaCamposComuns):
    nome: str = Field(min_length=1, max_length=255)
    status: DemandaStatusEditavel = "rascunho"
    # Obrigatório quando `status == "bloqueada"` — validado abaixo.
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio", max_length=500)
    # Aplica um WorkflowModelo no momento da criação: materializa as etapas do template como
    # `demanda_workflow_etapas` — snapshot, não referência viva (ver docstring do model). Só
    # aceito na criação; não existe endpoint pra trocar o workflow de uma Demanda já criada
    # nesta fase.
    workflow_modelo_id: UUID | None = Field(default=None, alias="workflowModeloId")
    # Opcional: responsáveis por etapa já na criação (só com `workflowModeloId`). Omitido = a criação segue idêntica à legada (responsáveis copiados do modelo).
    workflow_etapas_responsaveis: list[DemandaCreateEtapaResponsaveis] | None = Field(default=None, alias="workflowEtapasResponsaveis")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def _etapas_responsaveis_exigem_modelo(self) -> "DemandaCreate":
        if self.workflow_etapas_responsaveis:
            if self.workflow_modelo_id is None:
                raise ValueError("workflowEtapasResponsaveis exige workflowModeloId")
            ids = [item.modelo_etapa_id for item in self.workflow_etapas_responsaveis]
            if len(ids) != len(set(ids)):
                raise ValueError("workflowEtapasResponsaveis repete a mesma etapa")
        return self

    @field_validator("motivo_bloqueio")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str | None) -> str | None:
        """`min_length` contaria `"   "` como preenchido. Bloqueio sem motivo real esvazia a
        obrigatoriedade sem que ninguém perceba."""
        if value is None:
            return None
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoBloqueio não pode conter apenas espaços")
        return limpo


class DemandaUpdate(_DemandaCamposComuns):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    status: DemandaStatusEditavel | None = None
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio", max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_bloqueio")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str | None) -> str | None:
        if value is None:
            return None
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoBloqueio não pode conter apenas espaços")
        return limpo


class DemandaArquivar(BaseModel):
    motivo_arquivamento: str = Field(alias="motivoArquivamento", min_length=1, max_length=500)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo_arquivamento")
    @classmethod
    def motivo_nao_pode_ser_so_espaco(cls, value: str) -> str:
        limpo = value.strip()
        if not limpo:
            raise ValueError("motivoArquivamento não pode conter apenas espaços")
        return limpo


TipoAjuste = Literal["ajuste_interno", "ajuste_cliente", "refacao"]


class DemandaAjusteRegistrar(BaseModel):
    """Registra que um ajuste aconteceu — não muda nenhum campo da Demanda, só produz um
    evento na timeline (ver DemandaService.registrar_ajuste). Os três tipos vêm direto da UI
    existente (RegistrarAjusteCard) — mantidos diferenciados a pedido explícito."""

    tipo: TipoAjuste

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaConclusaoEmailRegistrar(BaseModel):
    """`enviado=true`: e-mail de conclusão foi enviado ao cliente. `enviado=false`: usuário
    dispensou o aviso sem enviar. As duas ações gravam os MESMOS campos reais
    (`emailConclusaoEnviado`/`emailConclusaoData`) — só o evento de domínio publicado muda,
    porque é o único jeito de diferenciar as duas intenções na timeline depois."""

    enviado: bool

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DemandaWorkflowEsforcoUpdate(BaseModel):
    esforco_estimado_minutos: EsforcoMinutos | None = Field(alias="esforcoEstimadoMinutos")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


PlanejamentoEstado = Literal["nao_planejado", "incompleto", "planejado"]


class PlanejamentoEtapaRead(BaseModel):
    """Janela PLANEJADA da etapa (11B.2B-A). Datas do calendário da empresa, fim inclusivo; planejamento ≠ prazo. `estado` é DERIVADO do par (nunca persistido):
    nao_planejado (NULL/NULL), incompleto (início sem fim — não entra na ocupação) e planejado (início + fim ≥ início). Ver `app.core.planejamento_etapa`."""

    planejado_inicio: date | None = Field(default=None, alias="planejadoInicio")
    planejado_fim: date | None = Field(default=None, alias="planejadoFim")
    estado: PlanejamentoEstado

    model_config = ConfigDict(populate_by_name=True)


def _data_planejada(valor: object) -> object:
    """`YYYY-MM-DD` ou null. Recusa números, booleanos, listas e datetimes (nada de hora num planejamento por dia)."""
    if valor is None or isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, str) and len(valor) == 10 and valor[4] == "-" and valor[7] == "-":
        return valor
    raise ValueError("Use uma data no formato AAAA-MM-DD ou null")


class DemandaWorkflowPlanejamentoUpdate(BaseModel):
    """PATCH parcial da janela planejada. Só os campos ENVIADOS mudam (`null` explícito limpa o campo); a validação vale para o PAR RESULTANTE no service, não
    para cada campo isolado. Exige ao menos um dos dois campos."""

    planejado_inicio: date | None = Field(default=None, alias="planejadoInicio")
    planejado_fim: date | None = Field(default=None, alias="planejadoFim")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("planejado_inicio", "planejado_fim", mode="before")
    @classmethod
    def _formato_da_data(cls, valor: object) -> object:
        return _data_planejada(valor)

    @model_validator(mode="after")
    def _exige_algum_campo(self) -> "DemandaWorkflowPlanejamentoUpdate":
        if not ({"planejado_inicio", "planejado_fim"} & self.model_fields_set):
            raise ValueError("Informe planejadoInicio e/ou planejadoFim")
        return self


class ResponsabilidadeEfetivaRead(BaseModel):
    """Quem é responsável pela etapa AGORA e DE ONDE vem: `etapa` (há vínculo explícito de usuário/departamento na própria etapa), `tarefa` (etapa sem vínculo explícito:
    vale o responsável geral da Demanda, resolvido em leitura — nada é copiado) ou `nenhuma`. Calculado pelo servidor; a interface não compara listas para descobrir a origem."""

    origem: Literal["etapa", "tarefa", "nenhuma"]
    usuario_ids: list[UUID] = Field(default_factory=list, alias="usuarioIds")
    departamento_ids: list[UUID] = Field(default_factory=list, alias="departamentoIds")

    model_config = ConfigDict(populate_by_name=True)


class DemandaWorkflowEtapaRead(BaseModel):
    """Etapa de workflow materializada — snapshot, não referência ao WorkflowModelo (ver
    docstring de app/models/demanda_workflow_etapa.py)."""

    id: UUID
    ordem: int
    nome: str
    tipo: WorkflowEtapaTipo
    esforco_estimado_minutos: EsforcoMinutos | None = Field(default=None, alias="esforcoEstimadoMinutos")
    pode_editar_esforco: bool = Field(default=False, alias="podeEditarEsforco")
    # 11B.2B-A — janela planejada (independente de prazo) e a mesma autoridade de `podeEditarEsforco`, calculada pelo SERVIDOR.
    planejamento: PlanejamentoEtapaRead = Field(
        default_factory=lambda: PlanejamentoEtapaRead(planejadoInicio=None, planejadoFim=None, estado="nao_planejado")
    )
    pode_editar_planejamento: bool = Field(default=False, alias="podeEditarPlanejamento")
    quantidade_antes_deadline: int = Field(alias="quantidadeAntesDeadline")
    unidade_prazo: WorkflowUnidadePrazo = Field(alias="unidadePrazo")
    status: DemandaWorkflowEtapaStatus
    # Vínculos EXPLÍCITOS da etapa ("responsáveis configurados"): o que está gravado nas relações da própria etapa. A responsabilidade EFETIVA (com a herança da tarefa)
    # está em `responsabilidadeEfetiva`.
    usuario_responsavel_ids: list[UUID] = Field(alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(alias="departamentoResponsavelIds")
    responsabilidade_efetiva: ResponsabilidadeEfetivaRead | None = Field(default=None, alias="responsabilidadeEfetiva")
    # Fase 8A — progressão. `iniciadaEm` NULL = início histórico desconhecido (snapshot anterior à 8A).
    iniciada_em: datetime | None = Field(default=None, alias="iniciadaEm")
    concluida_em: datetime | None = Field(default=None, alias="concluidaEm")
    # Quem concluiu (tipo execucao) ou aprovou (tipo aprovacao) — um conceito só; NULL no histórico/usuário removido.
    concluida_por_usuario_id: UUID | None = Field(default=None, alias="concluidaPorUsuarioId")
    # Fase 9B — aprovada pelo CLIENTE no Portal de Aprovação: nome DECLARADO (não verificado), derivado da decisão externa. `concluidaPorUsuarioId`
    # fica NULL nesse caso (o cliente nunca vira Usuario). Sem e-mail.
    concluida_por_externo_nome: str | None = Field(default=None, alias="concluidaPorExternoNome")
    # Calculado pelo SERVIDOR para o usuário da requisição: verdadeiro só na etapa ATUAL, para quem tem autoridade real
    # (responsável da etapa, admin/gestor do tenant ou Head de departamento da etapa), fora de leitura global (Pauta) e com a
    # Demanda não arquivada. O frontend não reconstrói RBAC; o endpoint reavalia tudo.
    pode_avancar: bool = Field(default=False, alias="podeAvancar")
    # Fase 8D — calculado pelo SERVIDOR: etapa ATUAL de APROVAÇÃO, com etapa anterior, autoridade real, não pausada, demanda não arquivada e fora de
    # leitura global (Pauta). O frontend não reconstrói RBAC nem decide a etapa de retorno (o servidor decide: a imediatamente anterior).
    pode_rejeitar: bool = Field(default=False, alias="podeRejeitar")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DemandaProgressoRead(BaseModel):
    """Progresso AUTORITATIVO da Demanda (acompanhamento), derivado SÓ do workflow materializado: etapas concluídas ÷ etapas do fluxo. A etapa em andamento NÃO ganha
    fração (2 de 5 concluídas = 40% mesmo com a 3ª em execução). Não usa tempo, sessão, estimativa, prazo nem intervalo. O frontend só exibe — nunca recalcula."""

    etapas_total: int = Field(alias="etapasTotal")
    etapas_concluidas: int = Field(alias="etapasConcluidas")
    # `None` = sem fluxo (a Demanda não tem etapas): a interface mostra "Sem fluxo", nunca 0%.
    percentual: int | None = None
    sem_fluxo: bool = Field(alias="semFluxo")
    etapa_atual_id: UUID | None = Field(default=None, alias="etapaAtualId")
    etapa_atual_nome: str | None = Field(default=None, alias="etapaAtualNome")

    model_config = ConfigDict(populate_by_name=True)


class DemandaDiretorioRead(BaseModel):
    """Forma enxuta para seletores — `TrafegoIniciarSessao` escolhe uma demanda, e as telas de
    sessão resolvem `demandaId` → nome.

    **Também é escopado.** Um diretório que ignorasse o escopo devolveria o nome de toda
    demanda da empresa a qualquer autenticado — reabrindo por uma porta lateral exatamente o
    que `get_no_escopo` fecha na porta principal.
    """

    id: UUID
    numero_operacional: int = Field(alias="numeroOperacional")
    # Identificador EMITIDO (`#845`, `BOX-2026-00846`) — é o que a interface mostra; o inteiro segue para ordenação/compatibilidade.
    identificador: str
    codigo_referencia: str = Field(alias="codigoReferencia")
    nome: str
    status: DemandaStatus
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DemandaRead(BaseModel):
    id: UUID
    empresa_id: UUID = Field(alias="empresaId")
    codigo_referencia: str = Field(alias="codigoReferencia")
    ano_referencia: int = Field(alias="anoReferencia")
    sequencial_referencia: int = Field(alias="sequencialReferencia")
    # Rótulo principal da operação — exibido como `#2063`.
    numero_operacional: int = Field(alias="numeroOperacional")
    # Fase 7D.1 — identificador EMITIDO (imutável): o que a interface exibe (`#2063` histórico ou `BOX-2026-02064`).
    identificador: str
    nome: str
    pit: str | None = None
    briefing: str | None = None
    status: DemandaStatus
    prioridade: DemandaPrioridade
    sinalizada: bool
    motivo_bloqueio: str | None = Field(default=None, alias="motivoBloqueio")
    # Fase Expediente 1 — origem da pausa (manual | expediente | null) e quando entrou em pausada. Só leitura: a API de escrita não aceita estes campos.
    pausa_origem: Literal["manual", "expediente"] | None = Field(default=None, alias="pausaOrigem")
    pausada_em: datetime | None = Field(default=None, alias="pausadaEm")
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    criado_por_usuario_id: UUID | None = Field(default=None, alias="criadoPorUsuarioId")
    # Qual WorkflowModelo originou as etapas abaixo — só informativo (ver docstring do
    # model). Editar/arquivar o modelo depois não muda nada aqui.
    workflow_modelo_id: UUID | None = Field(default=None, alias="workflowModeloId")
    data_inicio: date | None = Field(default=None, alias="dataInicio")
    data_fim_prevista: date | None = Field(default=None, alias="dataFimPrevista")
    prazo_etapa_atual: datetime | None = Field(default=None, alias="prazoEtapaAtual")
    enviado_cliente_em: datetime | None = Field(default=None, alias="enviadoClienteEm")
    prazo_retorno_cliente: datetime | None = Field(default=None, alias="prazoRetornoCliente")
    retorno_recebido_em: datetime | None = Field(default=None, alias="retornoRecebidoEm")
    email_conclusao_enviado: bool = Field(alias="emailConclusaoEnviado")
    email_conclusao_data: datetime | None = Field(default=None, alias="emailConclusaoData")
    usuario_responsavel_ids: list[UUID] = Field(default_factory=list, alias="usuarioResponsavelIds")
    departamento_responsavel_ids: list[UUID] = Field(
        default_factory=list, alias="departamentoResponsavelIds"
    )
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    arquivado_at: datetime | None = Field(default=None, alias="arquivadoAt")
    arquivado_por_usuario_id: UUID | None = Field(default=None, alias="arquivadoPorUsuarioId")
    motivo_arquivamento: str | None = Field(default=None, alias="motivoArquivamento")
    restaurado_at: datetime | None = Field(default=None, alias="restauradoAt")
    restaurado_por_usuario_id: UUID | None = Field(default=None, alias="restauradoPorUsuarioId")
    status_anterior_arquivamento: DemandaStatus | None = Field(
        default=None, alias="statusAnteriorArquivamento"
    )

    # --- SLA (snapshot, Fase 2G.6D1) — ver docstring de app/models/demanda.py. Resolvido uma
    # única vez na criação; `NULL` em tudo quando nenhuma SlaRegra ativa combinou (não é
    # erro). `sla_regra_id` é só proveniência técnica (pode virar `None` se a regra for
    # removida fisicamente) — o snapshot abaixo é a fonte histórica real, nunca um JOIN vivo.
    sla_regra_id: UUID | None = Field(default=None, alias="slaRegraId")
    sla_regra_nome_snapshot: str | None = Field(default=None, alias="slaRegraNomeSnapshot")
    sla_prazo_primeira_resposta_quantidade_snapshot: int | None = Field(
        default=None, alias="slaPrazoPrimeiraRespostaQuantidadeSnapshot"
    )
    sla_prazo_primeira_resposta_unidade_snapshot: SlaUnidadePrazo | None = Field(
        default=None, alias="slaPrazoPrimeiraRespostaUnidadeSnapshot"
    )
    sla_prazo_resolucao_quantidade_snapshot: int | None = Field(
        default=None, alias="slaPrazoResolucaoQuantidadeSnapshot"
    )
    sla_prazo_resolucao_unidade_snapshot: SlaUnidadePrazo | None = Field(
        default=None, alias="slaPrazoResolucaoUnidadeSnapshot"
    )
    sla_considerar_expediente_snapshot: bool | None = Field(
        default=None, alias="slaConsiderarExpedienteSnapshot"
    )
    sla_resolvido_at: datetime | None = Field(default=None, alias="slaResolvidoAt")
    sla_primeira_resposta_limite_em: datetime | None = Field(
        default=None, alias="slaPrimeiraRespostaLimiteEm"
    )
    sla_resolucao_limite_em: datetime | None = Field(default=None, alias="slaResolucaoLimiteEm")
    # --- Primeira resposta (Fase 2G.6D2B) — ver docstring de app/models/demanda.py.
    sla_primeira_resposta_em: datetime | None = Field(default=None, alias="slaPrimeiraRespostaEm")
    # DERIVADO em runtime pelo service (mesmo padrão de `etapa_atual_id`) — nunca uma coluna.
    # `None` quando falta qualquer um dos dois lados da comparação (sem primeira resposta
    # ainda, ou sem limite por ausência de SLA); nunca `False` só por indisponibilidade de dado.
    sla_primeira_resposta_dentro_prazo: bool | None = Field(
        default=None, alias="slaPrimeiraRespostaDentroPrazo"
    )
    # --- Resolução (Fase 2G.6D3B) — ver docstring de app/models/demanda.py. Fixada na
    # primeira transição REAL para `concluida`; `cancelada`/`arquivada` nunca preenchem.
    sla_resolvido_em: datetime | None = Field(default=None, alias="slaResolvidoEm")
    # DERIVADO em runtime (mesmo padrão de `slaPrimeiraRespostaDentroPrazo`) — nunca coluna.
    sla_resolvido_dentro_prazo: bool | None = Field(default=None, alias="slaResolvidoDentroPrazo")

    # Etapas de workflow materializadas (Fase 2E.2) — lista real, ordenada por `ordem`.
    # `etapa_atual_id` é DERIVADO em runtime (menor `ordem` com `status != 'concluida'`),
    # nunca uma coluna: evita ciclo de FK com `demanda_workflow_etapas` e uma segunda fonte
    # de verdade. Sem etapas, ou todas concluídas, é `None`.
    workflow_etapas: list[DemandaWorkflowEtapaRead] = Field(default_factory=list, alias="workflowEtapas")
    @computed_field(alias="estimadoConhecidoMinutos")
    @property
    def estimado_conhecido_minutos(self) -> int | None:
        valores = [e.esforco_estimado_minutos for e in self.workflow_etapas if e.esforco_estimado_minutos is not None]
        return sum(valores) if valores else None

    @computed_field(alias="etapasEstimadas")
    @property
    def etapas_estimadas(self) -> int:
        return sum(e.esforco_estimado_minutos is not None for e in self.workflow_etapas)

    @computed_field(alias="etapasSemEstimativa")
    @property
    def etapas_sem_estimativa(self) -> int:
        return len(self.workflow_etapas) - self.etapas_estimadas

    @computed_field(alias="estimativaCompleta")
    @property
    def estimativa_completa(self) -> bool:
        return bool(self.workflow_etapas) and self.etapas_sem_estimativa == 0

    etapa_atual_id: UUID | None = Field(default=None, alias="etapaAtualId")

    @computed_field(alias="progresso")
    @property
    def progresso(self) -> DemandaProgressoRead:
        """Regras: Concluída = 100%; sem etapas (e não concluída) = sem fluxo (percentual nulo); caso contrário concluídas/total×100 arredondado. Cancelada/bloqueada/pausada/
        aguardando cliente preservam o percentual histórico — o rótulo do estado é da interface. Etapa reaberta/rejeitada deixa de estar `concluida` no workflow e, portanto, de contar."""
        total = len(self.workflow_etapas)
        concluidas = sum(etapa.status == "concluida" for etapa in self.workflow_etapas)
        atual = next((etapa for etapa in self.workflow_etapas if self.etapa_atual_id is not None and etapa.id == self.etapa_atual_id), None)
        if self.status == "concluida":
            percentual: int | None = 100
        elif total == 0:
            percentual = None
        else:
            percentual = (concluidas * 200 + total) // (2 * total)  # arredonda metade para cima (round() do Python arredonda 12,5 para 12)
        return DemandaProgressoRead(
            etapasTotal=total,
            etapasConcluidas=concluidas,
            percentual=percentual,
            semFluxo=total == 0 and self.status != "concluida",
            etapaAtualId=atual.id if atual else None,
            etapaAtualNome=atual.nome if atual else None,
        )

    # Fase 8C.1 — o acesso a esta demanda veio SÓ do escopo derivado da etapa atual do Workflow (não é do escopo-base): a interface lê tudo e age no
    # Workflow, mas não oferece edição geral (o servidor também recusa). Só o detalhe e as ações do Workflow preenchem; nas listagens é sempre falso.
    acesso_apenas_workflow: bool = Field(default=False, alias="acessoApenasWorkflow")
    # O acesso a esta demanda veio SÓ da autoria (o usuário a solicitou, mas não é mais responsável nem atua nela): acompanhamento — a interface lê tudo e não
    # oferece edição nem ação de Workflow. Só o detalhe preenche; nas listagens é sempre falso.
    acesso_somente_acompanhamento: bool = Field(default=False, alias="acessoSomenteAcompanhamento")
    # Calculados pelo SERVIDOR para o usuário da requisição (listagens e detalhe; falsos em leitura global/acompanhamento): `podeIniciarTrabalho` = é executor da etapa
    # atual (ou da Demanda, sem fluxo) e a Demanda admite trabalho; `trabalhandoAgora` = tem sessão pessoal ATIVA nesta Demanda. A interface só exibe "Iniciar trabalho".
    pode_iniciar_trabalho: bool = Field(default=False, alias="podeIniciarTrabalho")
    trabalhando_agora: bool = Field(default=False, alias="trabalhandoAgora")
    # `checklist`/`arquivos` (2E.3) e `comentarios`/`historico` (2E.4) NÃO aparecem mais
    # aqui — todos têm tabela e endpoint dedicado agora (`/demandas/{id}/checklist`,
    # `/arquivos`, `/comentarios`, `/historico`). Embuti-los de novo infligiria em toda
    # listagem de Demandas um dado que só é necessário ao abrir uma Demanda específica —
    # evita N+1/payload pesado na listagem.

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator(
        "created_at",
        "updated_at",
        "arquivado_at",
        "restaurado_at",
        "prazo_etapa_atual",
        "enviado_cliente_em",
        "prazo_retorno_cliente",
        "retorno_recebido_em",
        "email_conclusao_data",
        "sla_resolvido_at",
        "sla_primeira_resposta_limite_em",
        "sla_resolucao_limite_em",
        "sla_primeira_resposta_em",
        "sla_resolvido_em",
    )
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


class DemandaResumoAtendimentoRead(BaseModel):
    """D2-B4 — os nove indicadores de MinhasDemandasView, agregados no servidor sobre o
    universo INTEGRAL do escopo Atendimento (nunca uma página). Ver
    DemandaRepository.resumo_atendimento — reproduz `classificarTarefa`/
    `MinhasDemandasView.tsx` (frontend, pré-migração), não uma aproximação nova."""

    criadas: int
    nao_iniciadas: int = Field(alias="naoIniciadas")
    em_execucao: int = Field(alias="emExecucao")
    aguardando_cliente: int = Field(alias="aguardandoCliente")
    aguardando_atendimento: int = Field(alias="aguardandoAtendimento")
    pausadas: int
    atrasadas: int
    dentro_do_prazo: int = Field(alias="dentroDoPrazo")
    concluidas: int

    model_config = ConfigDict(populate_by_name=True)


class DemandaResumoMinhaHomeRead(BaseModel):
    """D2-D2 — os 11 indicadores do Dashboard pessoal (`/meu-dia`), agregados no servidor
    sobre o universo INTEGRAL permitido do usuário (escopo normal AND responsável N:N),
    nunca as 200 demandas globais de `AppDataContext`. Reproduz `classificarTarefa` +
    os dois números do resumo textual de `DashboardView.tsx` (frontend, pré-migração), não
    uma aproximação nova. Sem `horas`/percentuais/dados de lista — só o que este endpoint é
    responsável por fornecer."""

    ativas: int
    novas: int
    andamento: int
    pausadas: int
    aguardando: int
    atrasadas: int
    concluidas: int
    previstas_hoje: int = Field(alias="previstasHoje")
    previstas_semana: int = Field(alias="previstasSemana")
    concluidas_semana: int = Field(alias="concluidasSemana")
    concluidas_ontem: int = Field(alias="concluidasOntem")

    model_config = ConfigDict(populate_by_name=True)


class DemandaEstatisticasRead(BaseModel):
    """Cards de `DemandasStats` (tela Tarefas), agregados no servidor sobre o universo INTEGRAL
    do escopo de quem pede — nunca as 200 Demandas de `AppDataContext`. Ver
    `DemandaRepository.estatisticas`."""

    total: int
    em_execucao: int = Field(alias="emExecucao")
    pausadas_ou_bloqueadas: int = Field(alias="pausadasOuBloqueadas")
    aguardando_cliente: int = Field(alias="aguardandoCliente")
    concluidas: int

    model_config = ConfigDict(populate_by_name=True)


class DemandaResumoOperacionalRead(BaseModel):
    """D2-D3A — os 7 indicadores baseados em Demanda de `TrafegoIndicadoresDemandas`,
    agregados no servidor sobre o universo INTEGRAL permitido (escopo normal, default) —
    nunca as 200 demandas globais de `AppDataContext`. Sem `horasExecutadas` (fonte separada,
    `SessaoTrabalho` — D2-D3B trata o cap de sessões, não este schema)."""

    internas: int
    clientes: int
    recebidas: int
    concluidas_no_periodo: int = Field(alias="concluidasNoPeriodo")
    horas_estimadas: float = Field(alias="horasEstimadas")
    total_na_base: int = Field(alias="totalNaBase")
    em_andamento: int = Field(alias="emAndamento")

    model_config = ConfigDict(populate_by_name=True)


class DemandaOperacionalEmAndamentoRead(BaseModel):
    """D2-D3A — RegraExpedienteView. Endpoint dedicado, não o resumo acima: `emAndamento`
    não depende de período, e essa tela nunca teve conceito de período — ver
    `DemandaRepository.count_em_andamento_operacional`."""

    em_andamento: int = Field(alias="emAndamento")

    model_config = ConfigDict(populate_by_name=True)


class DemandaResumoDepartamentoRead(BaseModel):
    """D2-B5 — indicadores de MeuDepartamentoView, agregados no servidor sobre o universo
    INTEGRAL do departamento (nunca a página filtrada). Não inclui `horasConsumidas`
    (continua vindo de `GET /sessoes-trabalho/horas`) nem `capacidadeDisponivel`
    (calculável no cliente a partir de `horasUteisHoje` + headcount, sem depender de
    Demanda) — só as métricas que este endpoint é responsável por fornecer."""

    novas: int
    sem_responsavel: int = Field(alias="semResponsavel")
    em_andamento: int = Field(alias="emAndamento")
    pausadas: int
    aguardando: int
    atrasadas: int
    concluidas: int
    horas_estimadas_total: float = Field(alias="horasEstimadasTotal")
    colaboradores_sobrecarregados: int = Field(alias="colaboradoresSobrecarregados")

    model_config = ConfigDict(populate_by_name=True)


class DemandaWorkflowRejeicao(BaseModel):
    """`POST /demandas/{id}/workflow/etapas/{etapa_id}/rejeitar` — SÓ o motivo. Não existe `targetStepId`/`previousStepId`/status: o servidor devolve
    para a etapa imediatamente anterior."""

    motivo: str = Field(min_length=3, max_length=1000)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, value: str) -> str:
        texto = " ".join(value.split())  # trim + colapsa espaços/quebras
        if len(texto) < 3:
            raise ValueError("Informe o motivo da rejeição (mínimo de 3 caracteres)")
        if "<" in texto and ">" in texto:
            raise ValueError("O motivo não pode conter HTML")
        return texto
