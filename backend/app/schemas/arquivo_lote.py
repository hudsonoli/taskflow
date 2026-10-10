"""Operações em lote sobre Arquivos (Fase 8B): contrato de SELEÇÃO compartilhado por resumo, download ZIP e exclusão.

Duas formas, nunca misturadas:
- `mode="ids"`: IDs explícitos (até `LIMITE_IDS`) — a seleção manual de cards;
- `mode="all_filtered"`: "todos os resultados do filtro" — o navegador NÃO carrega os IDs; manda os filtros atuais e o servidor reexecuta a consulta
  autorizada (tenant + escopo + filtros), menos as exceções `excludedIds` (itens desmarcados depois de "selecionar todos").

`filtros` usa os MESMOS nomes e o MESMO formato (CSV) da query de `GET /arquivos`, e é interpretado pelos mesmos parsers: o universo selecionado
é o da listagem. `contexto` é o recorte fixo da tela (aba de Cliente/Projeto/Demanda); vai por AND e nunca é ampliado por `filtros`.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

LIMITE_IDS = 500
LIMITE_EXCLUIDOS = 1000
_CSV = Field(default=None, max_length=4000)


class ArquivosLoteFiltros(BaseModel):
    search: str | None = Field(default=None, max_length=200)
    cliente_id: str | None = Field(default=None, alias="clienteId", max_length=4000)
    projeto_id: str | None = Field(default=None, alias="projetoId", max_length=4000)
    demanda_id: str | None = Field(default=None, alias="demandaId", max_length=4000)
    tipo: str | None = _CSV
    status: str | None = _CSV
    usuario_id: str | None = Field(default=None, alias="usuarioId", max_length=4000)
    cliente_id_excluir: str | None = Field(default=None, alias="clienteIdExcluir", max_length=4000)
    projeto_id_excluir: str | None = Field(default=None, alias="projetoIdExcluir", max_length=4000)
    demanda_id_excluir: str | None = Field(default=None, alias="demandaIdExcluir", max_length=4000)
    tipo_excluir: str | None = Field(default=None, alias="tipoExcluir", max_length=4000)
    status_excluir: str | None = Field(default=None, alias="statusExcluir", max_length=4000)
    usuario_id_excluir: str | None = Field(default=None, alias="usuarioIdExcluir", max_length=4000)
    data_inicio: datetime | None = Field(default=None, alias="dataInicio")
    data_fim: datetime | None = Field(default=None, alias="dataFim")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def vazio(self) -> bool:
        return not any(valor not in (None, "") for valor in self.model_dump().values())


class ArquivosLoteContexto(BaseModel):
    cliente_id: UUID | None = Field(default=None, alias="clienteId")
    projeto_id: UUID | None = Field(default=None, alias="projetoId")
    demanda_id: UUID | None = Field(default=None, alias="demandaId")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ArquivosLoteSelecao(BaseModel):
    mode: Literal["ids", "all_filtered"]
    ids: list[UUID] = Field(default_factory=list)
    excluded_ids: list[UUID] = Field(default_factory=list, alias="excludedIds")
    filtros: ArquivosLoteFiltros | None = None
    contexto: ArquivosLoteContexto | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validar_combinacao(self) -> "ArquivosLoteSelecao":
        if self.mode == "ids":
            if not self.ids:
                raise ValueError("ids: informe ao menos um arquivo")
            if len(self.ids) > LIMITE_IDS:
                raise ValueError(f"ids: no máximo {LIMITE_IDS} arquivos explícitos — para mais, use all_filtered")
            if len(set(self.ids)) != len(self.ids):
                raise ValueError("ids: contém identificadores repetidos")
            if self.excluded_ids:
                raise ValueError("excludedIds só é aceito com mode=all_filtered")
            if self.filtros is not None and not self.filtros.vazio():
                raise ValueError("filtros só são aceitos com mode=all_filtered")
        else:
            if self.ids:
                raise ValueError("ids não é aceito com mode=all_filtered")
            if len(self.excluded_ids) > LIMITE_EXCLUIDOS:
                raise ValueError(f"excludedIds: no máximo {LIMITE_EXCLUIDOS} exceções")
            if len(set(self.excluded_ids)) != len(self.excluded_ids):
                raise ValueError("excludedIds: contém identificadores repetidos")
        return self


class ArquivosLoteResumoRead(BaseModel):
    """O que a seleção cobre e os tetos operacionais — a interface mostra "N arquivos", avisa dos links (não entram no ZIP) e bloqueia o
    que o servidor recusaria."""

    total: int
    links: int
    arquivos_fisicos: int = Field(alias="arquivosFisicos")
    tamanho_total_bytes: int = Field(alias="tamanhoTotalBytes")
    limite_zip_arquivos: int = Field(alias="limiteZipArquivos")
    limite_zip_bytes: int = Field(alias="limiteZipBytes")
    limite_exclusao: int = Field(alias="limiteExclusao")

    model_config = ConfigDict(populate_by_name=True)


class ArquivosLoteExclusaoRead(BaseModel):
    excluidos: int
    # Registro e eventos já foram removidos em UMA transação; isto conta só os arquivos físicos que o disco não deixou apagar depois
    # (órfãos inacessíveis, nunca visíveis na interface).
    arquivos_fisicos_nao_removidos: int = Field(alias="arquivosFisicosNaoRemovidos")

    model_config = ConfigDict(populate_by_name=True)
