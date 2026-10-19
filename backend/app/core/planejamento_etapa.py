"""Janela planejada de uma etapa de workflow (11B.2B-A) — regras PURAS, sem SQLAlchemy.

`planejado_inicio`/`planejado_fim` são DATAS do calendário da empresa (fim inclusivo): PLANEJAMENTO contextual à Demanda, independente de prazo
(`demandas.prazo_etapa_atual`), de período da Demanda (`data_inicio`/`data_fim_prevista`), de sessões de trabalho e do tempo operacional.

Estados da JANELA (derivados do par, nunca persistidos):

| início | fim    | estado           | pode participar da ocupação (Fase B) |
|--------|--------|------------------|--------------------------------------|
| NULL   | NULL   | `nao_planejado`  | não                                  |
| data   | NULL   | `incompleto`     | NÃO — não aloca carga em semana alguma |
| data   | ≥ início | `planejado`    | sim                                  |
| NULL   | data   | INVÁLIDO         | nunca existe (CHECK + 422)           |

`sem_dia_util` (janela completa sem nenhum dia de capacidade nominal) e `janela_vencida` (janela completa no passado com a etapa ainda aberta) NÃO são estados da
janela nem colunas: serão estados DERIVADOS DE ALOCAÇÃO, calculados pelo endpoint de Carga (Fase B) a partir do calendário e da data de hoje.
"""
from datetime import date

ESTADO_NAO_PLANEJADO = "nao_planejado"
ESTADO_INCOMPLETO = "incompleto"
ESTADO_PLANEJADO = "planejado"


class JanelaPlanejadaInvalidaError(ValueError):
    """O par resultante (início, fim) não é um estado válido da janela. Vira 422."""


def validar_janela(inicio: date | None, fim: date | None) -> None:
    """Valida o PAR RESULTANTE — nunca um campo isolado. Levanta `JanelaPlanejadaInvalidaError` para fim sem início e para fim anterior ao início."""
    if fim is None:
        return
    if inicio is None:
        raise JanelaPlanejadaInvalidaError("Informe o início do planejamento antes do fim (ou limpe os dois campos)")
    if fim < inicio:
        raise JanelaPlanejadaInvalidaError("O fim do planejamento não pode ser anterior ao início")


def estado_da_janela(inicio: date | None, fim: date | None) -> str:
    """Estado derivado do par. Um par inválido (fim sem início) não existe no banco; se chegar aqui por erro de programação, falha alto em vez de classificar."""
    validar_janela(inicio, fim)
    if inicio is None:
        return ESTADO_NAO_PLANEJADO
    return ESTADO_INCOMPLETO if fim is None else ESTADO_PLANEJADO
