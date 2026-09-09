from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConfiguracaoNumeracaoTarefaRead(BaseModel):
    """Somente leitura (Fase 2G.8B) — sem schema de escrita: esta tela não oferece nenhum
    ajuste, só informa o estado atual do contador operacional (`numero_operacional`) de
    Demanda. Sem `empresaId`: implicitamente tenant-scoped, resolvido sempre por
    `current_user.empresa_id` (mesmo padrão de ConfiguracaoEmailRead)."""

    entidade: str
    rotulo_entidade: str = Field(alias="rotuloEntidade")
    contador_atual: int = Field(alias="contadorAtual")
    proximo_numero_estimado: int = Field(alias="proximoNumeroEstimado")
    maior_numero_emitido: int | None = Field(alias="maiorNumeroEmitido")
    consistente: bool
    formato_exibicao: str = Field(alias="formatoExibicao")
    gerenciado_automaticamente: bool = Field(alias="gerenciadoAutomaticamente")

    model_config = ConfigDict(populate_by_name=True)
