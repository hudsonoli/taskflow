"""Pauta operacional por ETAPA (P1_PAUTA_COLABORADOR): contrato NEUTRO e somente leitura.

A unidade é a ETAPA materializada da Demanda. O servidor devolve ITENS (nunca uma árvore por colaborador/projeto): a interface agrupa por colaborador ou por projeto sobre o MESMO
conjunto, sem regra de domínio. `responsabilidadeEfetiva` é a regra central (`app.core.executor_etapa`); `planejamento` é a janela planejada da etapa (DATE do calendário da empresa,
nunca prazo). Planejamento ≠ prazo: `prazoEtapaAtual` é só informação secundária e NUNCA é geometria.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class _Read(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class PautaMetaRead(_Read):
    agora_servidor: datetime = Field(alias="agoraServidor")
    fuso_empresa: str = Field(alias="fusoEmpresa")
    hoje: date  # no calendário da empresa
    inicio: date  # período consultado (inclusivo)
    fim: date


class PautaPlanejamentoRead(_Read):
    inicio: date | None
    fim: date | None
    # planejado | incompleto | nao_planejado (par inválido NULL/DATE é tratado como nao_planejado e marcado em `invalido`)
    estado: str
    invalido: bool = False


class PautaResponsabilidadeRead(_Read):
    origem: str  # etapa | tarefa | nenhuma
    usuario_ids: list[str] = Field(alias="usuarioIds")
    departamento_ids: list[str] = Field(alias="departamentoIds")


class PautaItemRead(_Read):
    etapa_id: str = Field(alias="etapaId")
    etapa_nome: str = Field(alias="etapaNome")
    etapa_tipo: str = Field(alias="etapaTipo")
    etapa_ordem: int = Field(alias="etapaOrdem")
    etapa_status: str = Field(alias="etapaStatus")
    etapa_atual: bool = Field(alias="etapaAtual")
    demanda_id: str = Field(alias="demandaId")
    demanda_identificador: str = Field(alias="demandaIdentificador")
    demanda_nome: str = Field(alias="demandaNome")
    demanda_status: str = Field(alias="demandaStatus")
    prioridade: str
    cliente_id: str | None = Field(alias="clienteId")
    projeto_id: str | None = Field(alias="projetoId")
    prazo_etapa_atual: datetime | None = Field(alias="prazoEtapaAtual")
    planejamento: PautaPlanejamentoRead
    responsabilidade_efetiva: PautaResponsabilidadeRead = Field(alias="responsabilidadeEfetiva")


class PautaPessoaRead(_Read):
    id: str
    nome: str


class PautaBucketRead(_Read):
    total: int  # itens que existem no filtro (não só os devolvidos)
    devolvidos: int
    truncado: bool


class PautaTotaisRead(_Read):
    planejadas: PautaBucketRead
    incompletas: PautaBucketRead
    nao_planejadas: PautaBucketRead = Field(alias="naoPlanejadas")
    # janelas completas fora do período consultado (aviso "há N etapas antes/depois")
    planejadas_antes: int = Field(alias="planejadasAntes")
    planejadas_depois: int = Field(alias="planejadasDepois")


class PautaOperacionalRead(_Read):
    meta: PautaMetaRead
    totais: PautaTotaisRead
    itens: list[PautaItemRead]
    pessoas: list[PautaPessoaRead]
