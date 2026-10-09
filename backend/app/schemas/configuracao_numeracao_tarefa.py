from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.numeracao_formato import NUMERO_MAX


class ConfiguracaoNumeracaoTarefaRead(BaseModel):
    """Estado da numeração operacional de Demanda/Tarefa + o FORMATO das próximas emissões (Fase 7D.1).

    Sem `empresaId`: implicitamente tenant-scoped, resolvido sempre por `current_user.empresa_id`. `preview` usa o próximo número
    e o ano de emissão atual, e NÃO consome número. Não há `reinicioAnual`: o número é contínuo (fase futura)."""

    entidade: str
    rotulo_entidade: str = Field(alias="rotuloEntidade")
    contador_atual: int = Field(alias="contadorAtual")
    proximo_numero: int = Field(alias="proximoNumero")
    proximo_numero_estimado: int = Field(alias="proximoNumeroEstimado")  # mesmo valor de `proximoNumero` (compatibilidade)
    maior_numero_emitido: int | None = Field(alias="maiorNumeroEmitido")
    consistente: bool
    motivo_inconsistencia: str | None = Field(default=None, alias="motivoInconsistencia")
    formato_exibicao: str = Field(alias="formatoExibicao")
    gerenciado_automaticamente: bool = Field(alias="gerenciadoAutomaticamente")
    prefixo: str
    separador: str
    incluir_ano: bool = Field(alias="incluirAno")
    digitos: int
    preview: str

    model_config = ConfigDict(populate_by_name=True)


class ConfiguracaoNumeracaoTarefaUpdate(BaseModel):
    """Só afeta as PRÓXIMAS emissões. Campo omitido = não muda. `extra=forbid`: qualquer campo desconhecido (inclusive
    `reinicioAnual`, que não existe nesta fase, ou `empresaId`) é 422."""

    prefixo: str | None = None
    separador: str | None = None
    incluir_ano: bool | None = Field(default=None, alias="incluirAno")
    digitos: int | None = None
    proximo_numero: int | None = Field(default=None, alias="proximoNumero", ge=1, le=NUMERO_MAX)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
