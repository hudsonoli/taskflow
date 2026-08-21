"""Regra de expediente — cálculo puro, independente de SQLAlchemy.

## Estado atual (Fase 2G.3)

`RegraExpediente`/`JanelaDia` são DTOs puros — só dataclasses. A persistência real vive em
`app/models/regra_expediente.py` (`RegraExpediente`/`RegraExpedienteDia`, tabelas
`regra_expediente`/`regra_expediente_dias`) e a leitura/inicialização em
`app/services/regra_expediente_service.py`. Este módulo não importa nenhum dos dois — não faz
query, não conhece `Session`, só recebe a regra já resolvida e calcula.

`REGRA_PADRAO` deixou de ser a fonte executada em paralelo ao banco: agora só inicializa o
registro persistido de uma Empresa que ainda não tem regra (ver
`RegraExpedienteService.get_ou_criar`). Nenhum código de produção deve importar
`REGRA_PADRAO` para USAR como regra corrente — só para SEMEAR uma.

## Por que dias da semana

Até esta fase, `esta_dentro_expediente` considerava só o horário: sábado às 10h caía dentro da
janela da manhã só porque a hora batia, mesmo sem nenhum dia da semana marcado como útil. Cada
dia agora tem seu próprio `ativo`/janelas — dia inativo é sempre fora, independente da hora.

Convenção de dia da semana: `datetime.weekday()` nativo do Python — `0` = segunda,
`6` = domingo. Sem tradução própria, para não haver um segundo mapeamento a manter igual ao
do banco (`regra_expediente_dias.dia_semana` usa a mesma convenção).
"""

from dataclasses import dataclass
from datetime import datetime

from app.core.relogio import agora_local

SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA, SABADO, DOMINGO = range(7)


@dataclass(frozen=True)
class JanelaDia:
    """Um dia da semana. `ativo=False` → dia inteiro fora do expediente, independente dos
    horários (que ficam `None` nesse caso — dia inativo não carrega janela)."""

    ativo: bool
    manha_inicio: str | None = None
    manha_fim: str | None = None
    tarde_inicio: str | None = None
    tarde_fim: str | None = None


@dataclass(frozen=True)
class RegraExpediente:
    ativo: bool
    # Minutos antes de `tarde_inicio` (do dia em questão) em que a retomada já é permitida.
    tolerancia_retomada_minutos: int
    dias: dict[int, JanelaDia]  # chave: 0 (segunda) .. 6 (domingo)


def _dia_util_padrao() -> JanelaDia:
    return JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00")


def _dia_folga_padrao() -> JanelaDia:
    return JanelaDia(ativo=False)


# Usado SÓ para inicializar o registro persistido de uma Empresa sem regra ainda — ver
# docstring do módulo. Espelha o padrão que `regraExpedienteMock` usava no frontend antes da
# migração (mesmos horários), agora com segunda–sexta explicitamente úteis e fim de semana
# explicitamente de folga.
REGRA_PADRAO = RegraExpediente(
    ativo=True,
    tolerancia_retomada_minutos=30,
    dias={
        SEGUNDA: _dia_util_padrao(),
        TERCA: _dia_util_padrao(),
        QUARTA: _dia_util_padrao(),
        QUINTA: _dia_util_padrao(),
        SEXTA: _dia_util_padrao(),
        SABADO: _dia_folga_padrao(),
        DOMINGO: _dia_folga_padrao(),
    },
)


def _para_minutos(hora_minuto: str) -> int:
    horas, minutos = (int(parte) for parte in hora_minuto.split(":"))
    return horas * 60 + minutos


def esta_dentro_expediente(agora: datetime | None = None, *, regra: RegraExpediente) -> bool:
    """`agora` sem valor usa o **fuso da aplicação**, não UTC: expediente é decisão de
    calendário local, e às 22h em São Paulo já é o dia seguinte em UTC — inclusive pra decidir
    QUAL dia da semana está em curso.

    `regra` é **obrigatório e sem default** de propósito: antes desta fase o default era
    `REGRA_PADRAO`, o que deixava aberto um caminho de um caller esquecer de passar a regra
    real e cair silenciosamente no template em vez de errar alto. `REGRA_PADRAO` só serve para
    semear o registro persistido de uma Empresa nova (`RegraExpedienteService._criar_padrao`)
    — nunca para ser usado como regra corrente de cálculo.

    Regra com `ativo=False` libera qualquer hora (mesmo comportamento de antes desta fase).
    Dia da semana com `ativo=False` (ex.: fim de semana no padrão inicial) é sempre fora,
    mesmo que a hora coincida com alguma janela de outro dia.
    """
    if not regra.ativo:
        return True

    momento = agora or agora_local()
    dia = regra.dias.get(momento.weekday())
    if dia is None or not dia.ativo:
        return False

    minutos = momento.hour * 60 + momento.minute

    dentro_manha = (
        dia.manha_inicio is not None
        and dia.manha_fim is not None
        and _para_minutos(dia.manha_inicio) <= minutos < _para_minutos(dia.manha_fim)
    )

    inicio_tarde_tolerado = (
        _para_minutos(dia.tarde_inicio) - regra.tolerancia_retomada_minutos
        if dia.tarde_inicio is not None
        else None
    )
    dentro_tarde = (
        inicio_tarde_tolerado is not None
        and dia.tarde_fim is not None
        and inicio_tarde_tolerado <= minutos < _para_minutos(dia.tarde_fim)
    )

    return dentro_manha or dentro_tarde


def duracao_horas_dia(dia: JanelaDia) -> float:
    """Duração total (manhã + tarde) em horas de um dia — `0.0` se ele for inativo ou tiver
    janela incompleta. Existe só para a estimativa de capacidade operacional (campo
    `horasUteisHoje` de `GET /expediente/estado`) — nunca para decidir dentro/fora de
    expediente, que é sempre `esta_dentro_expediente`."""
    if not dia.ativo or None in (dia.manha_inicio, dia.manha_fim, dia.tarde_inicio, dia.tarde_fim):
        return 0.0
    minutos_manha = _para_minutos(dia.manha_fim) - _para_minutos(dia.manha_inicio)
    minutos_tarde = _para_minutos(dia.tarde_fim) - _para_minutos(dia.tarde_inicio)
    return (minutos_manha + minutos_tarde) / 60
