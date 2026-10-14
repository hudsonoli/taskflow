"""Regra de expediente — cálculo puro, independente de SQLAlchemy.

## Estado atual (Fase Expediente 1)

`RegraExpediente`/`JanelaDia`/`DiaEspecial` são DTOs puros — só dataclasses. A persistência real vive em `app/models/regra_expediente.py` (tabelas
`regra_expediente`, `regra_expediente_dias`, `regra_expediente_periodos`, `regra_expediente_dias_especiais`...) e a leitura/inicialização em
`app/services/regra_expediente_service.py`. Este módulo não importa nenhum dos dois — não faz query, não conhece `Session`, só recebe a regra já resolvida e calcula.

`REGRA_PADRAO` só inicializa o registro persistido de uma Empresa que ainda não tem regra (ver `RegraExpedienteService.get_ou_criar`). Nenhum código de produção deve
importar `REGRA_PADRAO` para USAR como regra corrente — só para SEMEAR uma.

## Dois conceitos distintos (NUNCA misturar)

- JANELA DE TRABALHO: os períodos do dia (`08:00–12:00`, `13:00–18:00`...). Início inclusivo, fim EXCLUSIVO. É onde se pode iniciar/exercer trabalho.
  `esta_dentro_janela_trabalho`, `proximo_inicio_trabalho`.
- JANELA DE ACESSO: a janela de trabalho ANTECIPADA em `antecedencia_acesso_minutos` (`07:30–12:00`, `12:30–18:00` com 30 min). É só o direito de ENTRAR no sistema; a
  antecedência NÃO conta como trabalho. `esta_dentro_janela_acesso`, `proximo_acesso`.

## Fase Expediente 2 — quatro conceitos, SEM misturar

- A. ACESSO (`esta_dentro_janela_acesso`) e B. TRABALHO (`esta_dentro_janela_trabalho`): ENFORÇADOS. O acesso é negado (403 FORA_DO_EXPEDIENTE) quando
  `bloquear_fora_expediente` está ligada; o gate de ENTRADA em execução usa SÓ a janela de trabalho NOMINAL (a tolerância legada deixou de ser autoridade).
- C. LOGOUT AUTOMÁTICO (`ultimo_corte_logout`): horário PRÓPRIO (`logout_horario`, hora local da empresa), independente de A, B e do fim do último período. Token emitido
  ANTES do último corte deixa de valer (401). Login depois do corte emite token novo e vale (o bloqueio, se ligado, é outro mecanismo).
- D. PAUSA AUTOMÁTICA: NÃO existe (Fase 3). `pausar_no_fim_periodo` segue recusada com 422.
- Quem está sujeito: SÓ `perfil_base == "operador"` que não é conta de sistema e não tem `acesso_fora_expediente` (`usuario_sujeito_ao_expediente`). Admin/gestor/
  sistema/override são isentos de A, B e C.

## `esta_dentro_expediente` (LEGADO / deprecated — não é mais autoridade de nada em produção)

Era o gate de ENTRADA em execução (2G.3) e honrava a tolerância legada (`tolerancia_retomada_minutos`: a entrada valia X min antes do início do 2º período). A partir da
Fase 2 o gate usa `esta_dentro_janela_trabalho`. A função e a coluna ficam por compatibilidade (testes, payload 409, rollback); o SLA nunca a usou.

## Precedência (dia especial × regra semanal)

1. Dia especial vence a regra semanal. Numa mesma data, a decisão MANUAL ativa vence a AUTOMÁTICA; `ativo=False` desliga a linha.
2. `feriado`/`recesso` ativos → dia FECHADO; `trabalho_excepcional` ativo → períodos próprios do dia especial; `ignorado` ativo → neutraliza a data (vale a regra
   semanal).
3. Sem dia especial aplicável → períodos do dia da semana (0 períodos = fechado).

## Fuso

Cada regra carrega um fuso IANA (`timezone`); `None` (DTO montado à mão, testes legados) cai no fuso da aplicação. `datetime` naive é interpretado como relógio LOCAL
da empresa; aware é convertido (`ZoneInfo`, seguro para horário de verão). Convenção de dia da semana: `datetime.weekday()` (0 = segunda … 6 = domingo).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.relogio import agora_utc, fuso_aplicacao

SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA, SABADO, DOMINGO = range(7)

TIPO_FERIADO = "feriado"
TIPO_RECESSO = "recesso"
TIPO_TRABALHO_EXCEPCIONAL = "trabalho_excepcional"
TIPO_IGNORADO = "ignorado"
TIPOS_DIA_ESPECIAL = (TIPO_FERIADO, TIPO_RECESSO, TIPO_TRABALHO_EXCEPCIONAL, TIPO_IGNORADO)
ORIGEM_AUTOMATICO = "automatico"
ORIGEM_MANUAL = "manual"
ORIGENS_DIA_ESPECIAL = (ORIGEM_AUTOMATICO, ORIGEM_MANUAL)

# ("HH:MM", "HH:MM") — início inclusivo, fim exclusivo.
Periodo = tuple[str, str]

# Teto de busca por "próximo" instante: um ano e um dia cobre qualquer calendário razoável (uma regra sem nenhum dia aberto devolve None, nunca laça).
_HORIZONTE_DIAS = 366


@dataclass(frozen=True)
class JanelaDia:
    """Um dia da semana. `ativo=False` → dia inteiro fora do expediente (sem períodos).

    Duas formas de construir (ambas válidas):
    - LEGADA: `manha_*`/`tarde_*` (até duas janelas) — usada por testes e pelo `REGRA_PADRAO`;
    - NOVA: `periodos` (0, 1, 2 ou mais) — o que o banco entrega desde a Fase Expediente 1. Quando presente, VENCE os campos legados (que, nesse caso, são só um
      espelho informativo para consumidores antigos, ex.: o payload do 409).
    `lista_periodos()` é a ÚNICA leitura dos horários — o resto do código não olha `manha_*`/`tarde_*` diretamente.
    """

    ativo: bool
    manha_inicio: str | None = None
    manha_fim: str | None = None
    tarde_inicio: str | None = None
    tarde_fim: str | None = None
    periodos: tuple[Periodo, ...] | None = None

    def lista_periodos(self) -> tuple[Periodo, ...]:
        if not self.ativo:
            return ()
        if self.periodos is not None:
            return tuple(sorted(self.periodos))
        encontrados: list[Periodo] = []
        if self.manha_inicio is not None and self.manha_fim is not None:
            encontrados.append((self.manha_inicio, self.manha_fim))
        if self.tarde_inicio is not None and self.tarde_fim is not None:
            encontrados.append((self.tarde_inicio, self.tarde_fim))
        return tuple(sorted(encontrados))


def janela_de_periodos(periodos: tuple[Periodo, ...] | list[Periodo]) -> JanelaDia:
    """`JanelaDia` a partir de uma lista de períodos (0 = fechado). O espelho legado recebe o primeiro e o último período (só para consumidores antigos)."""
    ordenados = tuple(sorted(periodos))
    primeiro = ordenados[0] if ordenados else None
    ultimo = ordenados[-1] if len(ordenados) > 1 else None
    return JanelaDia(
        ativo=bool(ordenados),
        manha_inicio=primeiro[0] if primeiro else None,
        manha_fim=primeiro[1] if primeiro else None,
        tarde_inicio=ultimo[0] if ultimo else None,
        tarde_fim=ultimo[1] if ultimo else None,
        periodos=ordenados,
    )


@dataclass(frozen=True)
class DiaEspecial:
    data: date
    tipo: str
    origem: str = ORIGEM_MANUAL
    ativo: bool = True
    nome: str = ""
    periodos: tuple[Periodo, ...] = ()  # só para `trabalho_excepcional`


@dataclass(frozen=True)
class RegraExpediente:
    ativo: bool
    # LEGADO (semântica antiga, preservada): minutos antes do início do 2º período em que a ENTRADA em execução já é aceita. Ver docstring do módulo.
    tolerancia_retomada_minutos: int
    dias: dict[int, JanelaDia]  # chave: 0 (segunda) .. 6 (domingo)
    antecedencia_acesso_minutos: int = 30
    timezone: str | None = None
    dias_especiais: tuple[DiaEspecial, ...] = field(default_factory=tuple)
    # Fase Expediente 2: `bloquear_fora_expediente` é ENFORÇADA (gate de acesso). `pausar_no_fim_periodo` e `feriados_automaticos` seguem sem efeito (Fase 3+).
    bloquear_fora_expediente: bool = False
    pausar_no_fim_periodo: bool = False
    feriados_automaticos: bool = False
    # Logout automático (Fase 2): horário local "HH:MM" PRÓPRIO; só vale com `ativo` e `logout_automatico_ativo`.
    logout_automatico_ativo: bool = False
    logout_horario: str | None = None


def _dia_util_padrao() -> JanelaDia:
    return JanelaDia(ativo=True, manha_inicio="09:00", manha_fim="12:00", tarde_inicio="14:00", tarde_fim="19:00")


def _dia_folga_padrao() -> JanelaDia:
    return JanelaDia(ativo=False)


# Usado SÓ para inicializar o registro persistido de uma Empresa sem regra ainda — ver docstring do módulo.
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


# ── utilidades ───────────────────────────────────────────────────────────────────────────────────────────────────


def _para_minutos(hora_minuto: str) -> int:
    horas, minutos = (int(parte) for parte in hora_minuto.split(":")[:2])
    return horas * 60 + minutos


def fuso_da_regra(regra: RegraExpediente) -> ZoneInfo:
    """Fuso da empresa (IANA); sem fuso na regra (DTO legado/de teste), o fuso da aplicação."""
    return ZoneInfo(regra.timezone) if regra.timezone else fuso_aplicacao()


def momento_local(agora: datetime | None, regra: RegraExpediente) -> datetime:
    """`agora` no relógio da EMPRESA. Sem valor: o instante atual. Naive = já é relógio local da empresa; aware é convertido."""
    fuso = fuso_da_regra(regra)
    if agora is None:
        return agora_utc().astimezone(fuso)
    if agora.tzinfo is None or agora.utcoffset() is None:
        return agora.replace(tzinfo=fuso)
    return agora.astimezone(fuso)


def _segundos_do_dia(momento: datetime) -> int:
    return momento.hour * 3600 + momento.minute * 60 + momento.second


def _combinar(dia: date, hora_minuto: str, fuso: ZoneInfo) -> datetime:
    minutos = _para_minutos(hora_minuto)
    return datetime.combine(dia, time(minutos // 60, minutos % 60), tzinfo=fuso)


# ── dia especial e períodos do dia ───────────────────────────────────────────────────────────────────────────────


def resolver_dia_especial(regra: RegraExpediente, data: date) -> DiaEspecial | None:
    """O dia especial que MANDA nesta data, ou `None` (vale a regra semanal). Mesma data: a decisão MANUAL ativa vence a AUTOMÁTICA; `ativo=False` não conta;
    `ignorado` ativo neutraliza (devolve `None`). Nunca ambíguo: há no máximo uma linha ativa por (data, origem)."""
    ativos = [dia for dia in regra.dias_especiais if dia.data == data and dia.ativo]
    if not ativos:
        return None
    manuais = [dia for dia in ativos if dia.origem == ORIGEM_MANUAL]
    escolhido = manuais[0] if manuais else ativos[0]
    return None if escolhido.tipo == TIPO_IGNORADO else escolhido


def periodos_do_dia(regra: RegraExpediente, data: date) -> tuple[Periodo, ...]:
    """Períodos NOMINAIS de trabalho da data (0 = fechado), já aplicada a precedência de dia especial."""
    especial = resolver_dia_especial(regra, data)
    if especial is not None:
        if especial.tipo == TIPO_TRABALHO_EXCEPCIONAL:
            return tuple(sorted(especial.periodos))
        return ()  # feriado / recesso
    dia = regra.dias.get(data.weekday())
    return dia.lista_periodos() if dia is not None else ()


def dia_aberto(regra: RegraExpediente, data: date) -> bool:
    return bool(periodos_do_dia(regra, data))


def janela_do_dia(regra: RegraExpediente, data: date) -> JanelaDia:
    """O dia efetivo da data como `JanelaDia` (para mensagens/estado)."""
    return janela_de_periodos(periodos_do_dia(regra, data))


# ── janela de TRABALHO ───────────────────────────────────────────────────────────────────────────────────────────


def esta_dentro_janela_trabalho(agora: datetime | None = None, *, regra: RegraExpediente) -> bool:
    """Está dentro de algum período de trabalho (início inclusivo, fim exclusivo)? Regra desligada (`ativo=False`) libera qualquer hora. NÃO considera a
    antecedência de acesso nem a tolerância legada."""
    if not regra.ativo:
        return True
    momento = momento_local(agora, regra)
    segundos = _segundos_do_dia(momento)
    return any(
        _para_minutos(inicio) * 60 <= segundos < _para_minutos(fim) * 60 for inicio, fim in periodos_do_dia(regra, momento.date())
    )


def esta_dentro_expediente(agora: datetime | None = None, *, regra: RegraExpediente) -> bool:
    """Gate de ENTRADA em execução (2G.3), preservado. Igual a `esta_dentro_janela_trabalho`, MAS honrando a tolerância LEGADA: a entrada já vale
    `tolerancia_retomada_minutos` antes do início do 2º período do dia (como sempre foi). Regra com `ativo=False` libera qualquer hora; dia fechado é sempre fora."""
    if not regra.ativo:
        return True
    momento = momento_local(agora, regra)
    segundos = _segundos_do_dia(momento)
    for indice, (inicio, fim) in enumerate(periodos_do_dia(regra, momento.date())):
        tolerancia = regra.tolerancia_retomada_minutos if indice == 1 else 0
        if (_para_minutos(inicio) - tolerancia) * 60 <= segundos < _para_minutos(fim) * 60:
            return True
    return False


def proximo_inicio_trabalho(agora: datetime | None = None, *, regra: RegraExpediente) -> datetime | None:
    """Primeiro instante, a partir de `agora`, em que se PODE trabalhar: o próprio `agora` se já está na janela de trabalho; senão o início do próximo período
    (pode ser em outro dia). `None` se não houver nenhum nos próximos ~366 dias (ex.: nenhum dia aberto)."""
    return _proximo_instante(agora, regra, antecedencia_minutos=0)


# ── janela de ACESSO ─────────────────────────────────────────────────────────────────────────────────────────────


def esta_dentro_janela_acesso(agora: datetime | None = None, *, regra: RegraExpediente) -> bool:
    """O acesso (entrar/usar o sistema) está dentro da janela de trabalho ANTECIPADA em `antecedencia_acesso_minutos`? A antecedência vale só para ACESSO — ela não
    é trabalho (`esta_dentro_janela_trabalho` continua falso nela). Regra desligada libera tudo."""
    if not regra.ativo:
        return True
    momento = momento_local(agora, regra)
    return _em_algum(momento, _intervalos(regra, momento.date(), regra.antecedencia_acesso_minutos))


def proximo_acesso(agora: datetime | None = None, *, regra: RegraExpediente) -> datetime | None:
    """Primeiro instante, a partir de `agora`, em que o ACESSO é permitido: o próprio `agora` se já é, senão o início antecipado do próximo período. `None` se
    não houver nenhum nos próximos ~366 dias."""
    return _proximo_instante(agora, regra, antecedencia_minutos=regra.antecedencia_acesso_minutos)


def proximo_periodo_trabalho(agora: datetime | None = None, *, regra: RegraExpediente) -> tuple[datetime, datetime] | None:
    """(início, fim) do período de trabalho EM CURSO ou, se não houver, do PRÓXIMO (pode ser em outro dia). Só para mensagem ("Próximo período de trabalho:
    13:00–18:00"); nunca decide acesso. `None` com a regra desligada ou sem nenhum período nos próximos ~366 dias."""
    if not regra.ativo:
        return None
    momento = momento_local(agora, regra)
    fuso = fuso_da_regra(regra)
    melhor: tuple[datetime, datetime] | None = None
    for deslocamento in range(-1, _HORIZONTE_DIAS + 1):
        dia = momento.date() + timedelta(days=deslocamento)
        for inicio, fim in periodos_do_dia(regra, dia):
            inicio_dt, fim_dt = _combinar(dia, inicio, fuso), _combinar(dia, fim, fuso)
            if fim_dt.timestamp() > momento.timestamp() and (melhor is None or inicio_dt.timestamp() < melhor[0].timestamp()):
                melhor = (inicio_dt, fim_dt)
        if melhor is not None and dia > melhor[0].date():
            break
    return melhor


# ── quem está sujeito + avaliação do gate (Fase Expediente 2) ────────────────────────────────────────────────────


def usuario_sujeito_ao_expediente(*, perfil_base: str, is_system_account: bool, acesso_fora_expediente: bool) -> bool:
    """SÓ o operador "comum" está sujeito (acesso, trabalho e logout automático). A autoridade é o `perfil_base` — nunca um rótulo de tela, nem relações como
    Head/Atendimento. Isentos: admin, gestor, conta de sistema e quem tem `acesso_fora_expediente`."""
    return perfil_base == "operador" and not is_system_account and not acesso_fora_expediente


@dataclass(frozen=True)
class AvaliacaoExpediente:
    """Resultado do gate para UM usuário num instante, tudo no fuso da empresa. `acesso_permitido=False` ⇒ 403 FORA_DO_EXPEDIENTE; `trabalho_permitido=False` ⇒
    não pode ENTRAR em execução. Sem efeitos colaterais: quem chama decide o que fazer."""

    agora: datetime
    timezone: str
    sujeito: bool
    controle_ativo: bool
    bloqueio_ativo: bool
    acesso_permitido: bool
    trabalho_permitido: bool
    proximo_acesso: datetime | None
    proximo_trabalho: datetime | None
    proximo_trabalho_fim: datetime | None


def avaliar_expediente(agora: datetime | None, *, regra: RegraExpediente, sujeito: bool) -> AvaliacaoExpediente:
    momento = momento_local(agora, regra)
    bloqueio = regra.ativo and regra.bloquear_fora_expediente
    dentro_acesso = esta_dentro_janela_acesso(momento, regra=regra)
    dentro_trabalho = esta_dentro_janela_trabalho(momento, regra=regra)
    acesso_permitido = (not sujeito) or (not bloqueio) or dentro_acesso
    trabalho_permitido = (not sujeito) or dentro_trabalho
    periodo = None if dentro_trabalho else proximo_periodo_trabalho(momento, regra=regra)
    return AvaliacaoExpediente(
        agora=momento,
        timezone=regra.timezone or fuso_aplicacao().key,
        sujeito=sujeito,
        controle_ativo=regra.ativo,
        bloqueio_ativo=bloqueio,
        acesso_permitido=acesso_permitido,
        trabalho_permitido=trabalho_permitido,
        proximo_acesso=None if acesso_permitido else proximo_acesso(momento, regra=regra),
        proximo_trabalho=None if trabalho_permitido else (periodo[0] if periodo else None),
        proximo_trabalho_fim=None if trabalho_permitido else (periodo[1] if periodo else None),
    )


# ── LOGOUT AUTOMÁTICO ────────────────────────────────────────────────────────────────────────────────────────────


def logout_automatico_vigente(regra: RegraExpediente) -> bool:
    return bool(regra.ativo and regra.logout_automatico_ativo and regra.logout_horario)


def ultimo_corte_logout(agora: datetime | None = None, *, regra: RegraExpediente) -> datetime | None:
    """O corte de logout MAIS RECENTE que já passou (`≤ agora`): o de hoje se `logout_horario` já chegou, senão o de ontem. `None` com o logout desligado.
    Horário PRÓPRIO — não deriva do fim do último período — e sempre no fuso da empresa."""
    if not logout_automatico_vigente(regra):
        return None
    momento = momento_local(agora, regra)
    fuso = fuso_da_regra(regra)
    assert regra.logout_horario is not None
    hoje = _combinar(momento.date(), regra.logout_horario, fuso)
    if hoje.timestamp() <= momento.timestamp():
        return hoje
    return _combinar(momento.date() - timedelta(days=1), regra.logout_horario, fuso)


def sessao_encerrada_por_logout_automatico(emitido_em: datetime | float | int, agora: datetime | None = None, *, regra: RegraExpediente) -> bool:
    """O token emitido em `emitido_em` (claim `iat`) já foi alcançado por algum corte? Verdadeiro quando foi emitido ANTES do último corte. Token emitido no próprio
    corte ou depois (novo login) segue valendo. `iat` do JWT tem resolução de segundos; datetime aware ou epoch."""
    corte = ultimo_corte_logout(agora, regra=regra)
    if corte is None:
        return False
    epoca = emitido_em.timestamp() if isinstance(emitido_em, datetime) else float(emitido_em)
    return epoca < corte.timestamp()


def _intervalos(regra: RegraExpediente, data_base: date, antecedencia_minutos: int) -> list[tuple[datetime, datetime]]:
    """Intervalos [início − antecedência, fim) dos períodos de ontem, hoje e amanhã (a antecedência pode cruzar a meia-noite). Aware, no fuso da empresa."""
    fuso = fuso_da_regra(regra)
    intervalos: list[tuple[datetime, datetime]] = []
    for deslocamento in (-1, 0, 1):
        dia = data_base + timedelta(days=deslocamento)
        for inicio, fim in periodos_do_dia(regra, dia):
            intervalos.append((_combinar(dia, inicio, fuso) - timedelta(minutes=antecedencia_minutos), _combinar(dia, fim, fuso)))
    return intervalos


def _em_algum(momento: datetime, intervalos: list[tuple[datetime, datetime]]) -> bool:
    """Comparação por INSTANTE (timestamp), nunca pelo relógio de parede: seguro na virada de horário de verão mesmo com o mesmo `ZoneInfo` nos dois lados."""
    instante = momento.timestamp()
    return any(inicio.timestamp() <= instante < fim.timestamp() for inicio, fim in intervalos)


def _proximo_instante(agora: datetime | None, regra: RegraExpediente, *, antecedencia_minutos: int) -> datetime | None:
    momento = momento_local(agora, regra)
    if not regra.ativo:
        return momento
    if _em_algum(momento, _intervalos(regra, momento.date(), antecedencia_minutos)):
        return momento
    fuso = fuso_da_regra(regra)
    melhor: datetime | None = None
    for deslocamento in range(_HORIZONTE_DIAS + 1):
        dia = momento.date() + timedelta(days=deslocamento)
        for inicio, _fim in periodos_do_dia(regra, dia):
            candidato = _combinar(dia, inicio, fuso) - timedelta(minutes=antecedencia_minutos)
            if candidato.timestamp() > momento.timestamp() and (melhor is None or candidato.timestamp() < melhor.timestamp()):
                melhor = candidato
        # a antecedência (≤ 12 h) só alcança o dia anterior: dois dias além do primeiro achado já não podem ser menores
        if melhor is not None and dia > melhor.date() + timedelta(days=1):
            break
    return melhor


def duracao_horas_dia(dia: JanelaDia) -> float:
    """Duração total (soma dos períodos) em horas de um dia — `0.0` se ele for inativo. Existe só para a estimativa de capacidade operacional (campo
    `horasUteisHoje` de `GET /expediente/estado`) — nunca para decidir dentro/fora de expediente.

    Forma LEGADA (`periodos is None`) exige as quatro janelas (`0.0` se incompleta, comportamento anterior); a forma nova soma os períodos que houver."""
    if not dia.ativo:
        return 0.0
    if dia.periodos is None and None in (dia.manha_inicio, dia.manha_fim, dia.tarde_inicio, dia.tarde_fim):
        return 0.0
    minutos = sum(_para_minutos(fim) - _para_minutos(inicio) for inicio, fim in dia.lista_periodos())
    return minutos / 60
