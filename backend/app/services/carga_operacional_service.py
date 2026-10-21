"""Tráfego V2 — 11B.2B-B: serviço da CARGA semanal (`GET /trafego/operacional/carga`, somente leitura). Autoridade das regras: docs/carga-semanal.md.

Fluxo: (1) carrega regra de expediente/fator, pessoas elegíveis, etapas abertas e responsáveis em POUCAS consultas em conjunto; (2) `calcular_carga` (puro) faz a alocação COMPLETA da semana; (3) só então os filtros
`usuarioId`/`departamentoId` recortam o resultado — filtrar NUNCA recalcula a divisão. Nenhuma escrita, nenhum evento, nada de `sessoes_trabalho` nem `demanda_status_intervalos`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.carga_calculo import (
    Agregado,
    EtapaCalculada,
    EtapaEntrada,
    PessoaElegivel,
    Ref,
    ResultadoCarga,
    calcular_carga,
)
from app.core.capacidade_individual import ConfiguracaoCapacidade, JornadaIndividual, dias_ausentes_da_semana
from app.core.carga_semanal import ALOCACAO_JANELA_VENCIDA, ALOCACAO_SEM_DIA_UTIL, dias_da_semana, segunda_da_semana
from app.core.expediente import RegraExpediente, fuso_da_regra
from app.core.relogio import agora_utc, fuso_aplicacao
from app.repositories.carga_operacional_repository import CargaOperacionalRepository
from app.schemas.trafego_carga import (
    BucketRead,
    CapacidadeRead,
    DepartamentoCargaRead,
    DetalheRead,
    DiaSemanaRead,
    ItemEtapaRead,
    JanelaRead,
    MetaRead,
    NaoPlanejadoRead,
    PendenciaRead,
    PendenciasPlanejamentoRead,
    PessoaCargaRead,
    PoolSemDepartamentoRead,
    RefRead,
    SemanaRead,
    TrafegoCargaRead,
)
from app.services.regra_expediente_service import RegraExpedienteService

LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200

DETALHE_USUARIO = "usuario"
DETALHE_DEPARTAMENTO = "departamento"


class SemanaPassadaNaoSuportadaError(ValueError):
    """Semana anterior à semana atual: a v1 só calcula a semana atual e as futuras (sem relatório histórico de capacidade) — 422 `SEMANA_PASSADA_NAO_SUPORTADA`."""

    codigo = "SEMANA_PASSADA_NAO_SUPORTADA"


class FiltroInvalidoError(ValueError):
    """Combinação de parâmetros inválida (ex.: `detalhe=usuario` sem `usuarioId`) — 422."""

    codigo = "FILTRO_INVALIDO"


class AlvoNaoEncontradoError(LookupError):
    """`usuarioId`/`departamentoId` inexistente OU de outra empresa — 404 nos dois casos (não vaza existência entre tenants)."""


def _ocupacao(planejado: int | None, alocavel: int | None) -> float | None:
    if planejado is None or not alocavel:
        return None
    return round(planejado * 100 / alocavel, 1)


class CargaOperacionalService:
    def __init__(self, repository: CargaOperacionalRepository | None = None, regra_service: RegraExpedienteService | None = None) -> None:
        self.repository = repository or CargaOperacionalRepository()
        self.regra_service = regra_service or RegraExpedienteService()

    # ------------------------------------------------------------------------------------------------------------------
    # Leituras
    # ------------------------------------------------------------------------------------------------------------------

    def _regra(self, db: Session, empresa_id: str) -> tuple[RegraExpediente | None, int]:
        """Regra (DTO de cálculo) e fator alocável, SEM criar nada: empresa sem regra = sem política = expediente desligado (nenhuma regra padrão é inventada numa leitura)."""
        existente = self.regra_service.repository.get_by_empresa(db, empresa_id)
        if existente is None:
            return None, 100
        return self.regra_service.get_regra_calculo(db, empresa_id=empresa_id), int(existente.percentual_capacidade_alocavel)

    def _entradas(self, db: Session, empresa_id: str) -> list[EtapaEntrada]:
        etapas = self.repository.etapas_abertas(db, empresa_id=empresa_id)
        usuarios: dict[str, list[str]] = defaultdict(list)
        for etapa_id, usuario_id in self.repository.usuarios_das_etapas(db, empresa_id=empresa_id):
            usuarios[etapa_id].append(usuario_id)
        departamentos: dict[str, list[str]] = defaultdict(list)
        for etapa_id, departamento_id in self.repository.departamentos_das_etapas(db, empresa_id=empresa_id):
            departamentos[etapa_id].append(departamento_id)
        return [
            EtapaEntrada(
                etapa_id=linha["etapa_id"],
                demanda_id=linha["demanda_id"],
                etapa_nome=linha["etapa_nome"],
                etapa_tipo=linha["etapa_tipo"],
                ordem=linha["ordem"],
                estimativa_min=linha["estimativa"],
                planejado_inicio=linha["planejado_inicio"],
                planejado_fim=linha["planejado_fim"],
                usuario_ids=tuple(usuarios.get(linha["etapa_id"], ())),
                departamento_ids=tuple(departamentos.get(linha["etapa_id"], ())),
                demanda_identificador=linha["identificador"],
                demanda_nome=linha["demanda_nome"],
                demanda_status=linha["demanda_status"],
                cliente=Ref(linha["cliente_id"], linha["cliente_nome"]) if linha["cliente_id"] else None,
                projeto=Ref(linha["projeto_id"], linha["projeto_nome"]) if linha["projeto_id"] else None,
            )
            for linha in etapas
        ]

    def _configuracoes(self, db: Session, empresa_id: str, segunda: date) -> dict[str, ConfiguracaoCapacidade]:
        """Jornada própria + ausências da semana de TODOS os elegíveis, em duas consultas fixas (sem N+1). Quem não aparece não tem configuração: usa o expediente da empresa."""
        dias_jornada: dict[str, dict[int, list[tuple[str, str]]]] = {}
        for usuario_id, dia, inicio, fim in self.repository.jornadas_dos_elegiveis(db, empresa_id=empresa_id):
            dias = dias_jornada.setdefault(usuario_id, {})
            if dia is not None and inicio is not None and fim is not None:
                dias.setdefault(dia, []).append((inicio, fim))
        domingo = segunda + timedelta(days=6)
        intervalos: dict[str, list[tuple[date, date]]] = defaultdict(list)
        for usuario_id, inicio, fim in self.repository.ausencias_dos_elegiveis(db, empresa_id=empresa_id, inicio=segunda, fim=domingo):
            intervalos[usuario_id].append((inicio, fim))
        semana = dias_da_semana(segunda)
        return {
            usuario_id: ConfiguracaoCapacidade(
                jornada=JornadaIndividual({dia: tuple(periodos) for dia, periodos in dias_jornada[usuario_id].items()}) if usuario_id in dias_jornada else None,
                dias_ausentes=dias_ausentes_da_semana(intervalos.get(usuario_id, ()), semana),
            )
            for usuario_id in set(dias_jornada) | set(intervalos)
        }

    # ------------------------------------------------------------------------------------------------------------------
    # Entrada pública
    # ------------------------------------------------------------------------------------------------------------------

    def carga(
        self,
        db: Session,
        *,
        empresa_id: str,
        semana: date | None = None,
        departamento_id: str | None = None,
        usuario_id: str | None = None,
        detalhe: str | None = None,
        limite: int = LIMITE_PADRAO,
    ) -> TrafegoCargaRead:
        if detalhe is not None and detalhe not in (DETALHE_USUARIO, DETALHE_DEPARTAMENTO):
            raise FiltroInvalidoError("detalhe deve ser 'usuario' ou 'departamento'")
        if detalhe == DETALHE_USUARIO and not usuario_id:
            raise FiltroInvalidoError("detalhe=usuario exige usuarioId")
        if detalhe == DETALHE_DEPARTAMENTO and not departamento_id:
            raise FiltroInvalidoError("detalhe=departamento exige departamentoId")

        regra, percentual = self._regra(db, empresa_id)
        fuso = fuso_da_regra(regra) if regra is not None else fuso_aplicacao()
        agora = agora_utc()
        hoje = agora.astimezone(fuso).date()
        segunda = segunda_da_semana(semana or hoje)
        if segunda < segunda_da_semana(hoje):
            raise SemanaPassadaNaoSuportadaError("A Carga calcula a semana atual e as futuras; semanas passadas não são suportadas")

        if usuario_id and not self.repository.usuario_existe(db, empresa_id=empresa_id, usuario_id=usuario_id):
            raise AlvoNaoEncontradoError("Usuário não encontrado")
        if departamento_id and not self.repository.departamento_existe(db, empresa_id=empresa_id, departamento_id=departamento_id):
            raise AlvoNaoEncontradoError("Departamento não encontrado")

        pessoas = [PessoaElegivel(p["id"], p["nome"], p["departamento_id"]) for p in self.repository.pessoas_elegiveis(db, empresa_id=empresa_id)]
        nomes_departamento = self.repository.departamentos(db, empresa_id=empresa_id)
        # Capacidade individual só existe com o expediente da empresa LIGADO: desligado, nenhuma jornada própria reativa capacidade (nem se consulta).
        configuracoes = self._configuracoes(db, empresa_id, segunda) if regra is not None and regra.ativo else {}
        resultado = calcular_carga(
            etapas=self._entradas(db, empresa_id),
            pessoas=pessoas,
            regra=regra,
            percentual_alocavel=percentual,
            hoje=hoje,
            semana_inicio=segunda,
            configuracoes=configuracoes,
        )
        return self._montar(
            resultado,
            agora=agora,
            fuso_nome=getattr(fuso, "key", str(fuso)),
            nomes_departamento=nomes_departamento,
            departamento_id=departamento_id,
            usuario_id=usuario_id,
            detalhe=detalhe,
            limite=limite,
        )

    # ------------------------------------------------------------------------------------------------------------------
    # Montagem da resposta (filtros DEPOIS do cálculo)
    # ------------------------------------------------------------------------------------------------------------------

    def _montar(
        self,
        r: ResultadoCarga,
        *,
        agora,
        fuso_nome: str,
        nomes_departamento: dict[str, str],
        departamento_id: str | None,
        usuario_id: str | None,
        detalhe: str | None,
        limite: int,
    ) -> TrafegoCargaRead:
        disponivel = r.capacidade_indisponivel is None

        def nominal_de(usuario_id: str) -> int | None:
            return r.capacidades[usuario_id].nominal_min if disponivel else None

        def alocavel_de(usuario_id: str) -> int | None:
            return r.capacidades[usuario_id].alocavel_min if disponivel else None

        def planejado_de(agregado_min: int) -> int | None:
            return agregado_min if disponivel else None

        def saldo_de(alocavel_total: int | None, planejado: int | None) -> int | None:
            return None if alocavel_total is None or planejado is None else alocavel_total - planejado

        # ---- pessoas
        ids_pessoas = sorted(r.pessoas_info, key=lambda i: (r.pessoas_info[i].nome.lower(), i))
        if usuario_id:
            ids_pessoas = [i for i in ids_pessoas if i == usuario_id]
        elif departamento_id:
            ids_pessoas = [i for i in ids_pessoas if r.pessoas_info[i].departamento_id == departamento_id]
        pessoas_read = []
        for i in ids_pessoas:
            info, agg = r.pessoas_info[i], r.pessoas[i]
            planejado = planejado_de(agg.planejado_min)
            nominal, alocavel = nominal_de(i), alocavel_de(i)
            capacidade_pessoa = r.capacidades.get(i)
            pessoas_read.append(
                PessoaCargaRead(
                    usuarioId=i,
                    nome=info.nome,
                    departamentoId=info.departamento_id,
                    capacidadeNominalMin=nominal,
                    capacidadeAlocavelMin=alocavel,
                    planejadoMin=planejado,
                    saldoMin=saldo_de(alocavel, planejado),
                    ocupacaoPercentual=_ocupacao(planejado, alocavel),
                    capacidadeOrigem=capacidade_pessoa.origem if capacidade_pessoa else None,
                    diasAusentes=capacidade_pessoa.dias_ausentes if capacidade_pessoa else None,
                    naoPlanejadoMin=agg.nao_planejado_min,
                    pendenciasPlanejamentoMin=agg.pendencia_min,
                    semEstimativaCount=len(agg.sem_estimativa),
                )
            )

        # ---- departamentos
        membros: dict[str, list[str]] = defaultdict(list)
        for i, info in r.pessoas_info.items():
            if info.departamento_id:
                membros[info.departamento_id].append(i)
        ids_departamentos = sorted(set(membros) | set(r.pools_departamento), key=lambda d: (nomes_departamento.get(d, "").lower(), d))
        if usuario_id:
            ids_departamentos = []
        elif departamento_id:
            ids_departamentos = [departamento_id]
        departamentos_read = []
        for d in ids_departamentos:
            pessoas_do_dep = membros.get(d, [])
            pool = r.pools_departamento.get(d, Agregado())
            planejado_total = sum(r.pessoas[i].planejado_min for i in pessoas_do_dep) + pool.planejado_min
            planejado = planejado_de(planejado_total)
            # A capacidade do departamento é a SOMA das capacidades reais das pessoas (podem diferir: jornadas próprias, ausências) — nunca "n × capacidade padrão".
            nominal_dep = sum(nominal_de(i) or 0 for i in pessoas_do_dep) if disponivel else None
            alocavel_dep = sum(alocavel_de(i) or 0 for i in pessoas_do_dep) if disponivel else None
            sem_estimativa = set(pool.sem_estimativa)
            for i in pessoas_do_dep:
                sem_estimativa |= r.pessoas[i].sem_estimativa
            departamentos_read.append(
                DepartamentoCargaRead(
                    departamentoId=d,
                    nome=nomes_departamento.get(d, ""),
                    pessoasCount=len(pessoas_do_dep),
                    capacidadeNominalMin=nominal_dep,
                    capacidadeAlocavelMin=alocavel_dep,
                    planejadoMin=planejado,
                    planejadoPoolMin=planejado_de(pool.planejado_min),
                    saldoMin=saldo_de(alocavel_dep, planejado),
                    ocupacaoPercentual=_ocupacao(planejado, alocavel_dep),
                    naoPlanejadoMin=sum(r.pessoas[i].nao_planejado_min for i in pessoas_do_dep) + pool.nao_planejado_min,
                    pendenciasPlanejamentoMin=sum(r.pessoas[i].pendencia_min for i in pessoas_do_dep) + pool.pendencia_min,
                    semEstimativaCount=len(sem_estimativa),
                )
            )

        # ---- pool sem departamento (só na visão sem filtro)
        pool_sem = r.pool_sem_departamento
        pool_sem_read = None
        if not usuario_id and not departamento_id:
            pool_sem_read = PoolSemDepartamentoRead(
                etapasCount=len(pool_sem.etapas),
                planejadoMin=planejado_de(pool_sem.planejado_min),
                naoPlanejadoMin=pool_sem.nao_planejado_min,
                pendenciasPlanejamentoMin=pool_sem.pendencia_min,
                semEstimativaCount=len(pool_sem.sem_estimativa),
            )

        # ---- etapas dentro do filtro (a divisão já foi feita sobre o total: só se escolhe QUAIS etapas entram nos baldes)
        def alvo_no_filtro(tipo: str, chave: str) -> bool:
            if usuario_id:
                return tipo == "usuario" and chave == usuario_id
            if departamento_id:
                if tipo == "usuario":
                    return r.pessoas_info[chave].departamento_id == departamento_id
                return tipo == "pool_departamento" and chave == departamento_id
            return True

        etapas_no_filtro = [e for e in r.etapas if any(alvo_no_filtro(*alvo) for alvo in e.alvos)]
        limite_itens = min(limite, LIMITE_MAXIMO)

        def item(e: EtapaCalculada, parte: int | None) -> ItemEtapaRead:
            ent = e.entrada
            return ItemEtapaRead(
                demandaId=ent.demanda_id,
                identificador=ent.demanda_identificador,
                titulo=ent.demanda_nome,
                statusDemanda=ent.demanda_status,
                cliente=RefRead(id=ent.cliente.id, nome=ent.cliente.nome) if ent.cliente else None,
                projeto=RefRead(id=ent.projeto.id, nome=ent.projeto.nome) if ent.projeto else None,
                etapaId=ent.etapa_id,
                etapaNome=ent.etapa_nome,
                etapaTipo=ent.etapa_tipo,
                estimativaMin=ent.estimativa_min,
                restanteMin=e.restante_min,
                planejadoNaSemanaMin=e.planejado_semana_min,
                parteMin=parte,
                janela=JanelaRead(planejadoInicio=ent.planejado_inicio, planejadoFim=ent.planejado_fim, estado=e.estado_planejamento),
                alocacaoEstado=e.alocacao_estado,
                motivoNaoPlanejado=e.motivo_nao_planejado,
                origem=e.origem,
                divididoEntre=len(e.alvos),
            )

        def bucket(lista: list[EtapaCalculada]) -> BucketRead:
            return BucketRead(
                etapasCount=len(lista),
                minutosConhecidos=sum(e.restante_min or 0 for e in lista),
                semEstimativaCount=sum(1 for e in lista if e.sem_estimativa),
            )

        def pendencia(lista: list[EtapaCalculada]) -> PendenciaRead:
            base = bucket(lista)
            return PendenciaRead(
                etapasCount=base.etapas_count,
                minutosConhecidos=base.minutos_conhecidos,
                semEstimativaCount=base.sem_estimativa_count,
                itens=[item(e, None) for e in lista[:limite_itens]],
                truncado=len(lista) > limite_itens,
            )

        nao_planejado = NaoPlanejadoRead(
            semJanela=bucket([e for e in etapas_no_filtro if e.motivo_nao_planejado == "sem_janela"]),
            janelaIncompleta=bucket([e for e in etapas_no_filtro if e.motivo_nao_planejado == "janela_incompleta"]),
        )
        pendencias = PendenciasPlanejamentoRead(
            janelaVencida=pendencia([e for e in etapas_no_filtro if e.alocacao_estado == ALOCACAO_JANELA_VENCIDA]),
            semDiaUtil=pendencia([e for e in etapas_no_filtro if e.alocacao_estado == ALOCACAO_SEM_DIA_UTIL]),
        )

        # ---- detalhe (drill-down) — só com filtro e `detalhe`
        detalhe_read = None
        if detalhe:
            predicado = (lambda tipo, chave: tipo == "usuario" and chave == usuario_id) if detalhe == DETALHE_USUARIO else (
                lambda tipo, chave: (tipo == "usuario" and r.pessoas_info[chave].departamento_id == departamento_id)
                or (tipo == "pool_departamento" and chave == departamento_id)
            )
            linhas: list[tuple[int, EtapaCalculada, int | None]] = []
            for e in r.etapas:
                indices = [i for i, alvo in enumerate(e.alvos) if predicado(*alvo)]
                if not indices:
                    continue
                parte = sum(e.divisao_semana[i] for i in indices) if e.divisao_semana else None
                linhas.append((parte or 0, e, parte))
            linhas.sort(key=lambda t: (-t[0], t[1].entrada.demanda_identificador, t[1].entrada.ordem, t[1].entrada.etapa_id))
            detalhe_read = DetalheRead(
                tipo=detalhe,
                id=(usuario_id if detalhe == DETALHE_USUARIO else departamento_id) or "",
                etapas=[item(e, parte) for _ordem, e, parte in linhas[:limite_itens]],
                etapasTotal=len(linhas),
                truncado=len(linhas) > limite_itens,
            )

        return TrafegoCargaRead(
            meta=MetaRead(agoraServidor=agora, fusoEmpresa=fuso_nome),
            semana=SemanaRead(
                inicio=r.semana_inicio,
                fim=r.semana_fim,
                recorteHoje=r.recorte_hoje,
                dias=[DiaSemanaRead(data=d, minutosNominais=m, considerado=ok) for d, m, ok in r.dias],
            ),
            capacidade=CapacidadeRead(capacidadeIndisponivel=r.capacidade_indisponivel, fatorAlocavelPercentual=r.percentual),
            pessoas=pessoas_read,
            departamentos=departamentos_read,
            poolSemDepartamento=pool_sem_read,
            naoPlanejado=nao_planejado,
            pendenciasPlanejamento=pendencias,
            detalhe=detalhe_read,
        )
