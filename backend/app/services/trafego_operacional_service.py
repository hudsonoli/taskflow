"""Tráfego V2 — Fase 2: métricas OPERACIONAIS (somente leitura) sobre `demanda_status_intervalos`.

TEMPO OPERACIONAL ≠ TEMPO PESSOAL. Nada aqui lê `sessoes_trabalho`, calcula horas por pessoa ou usa "executor": "em execução há 2 h" significa que a DEMANDA está nesse estado há 2 h.

## AGORA (estado atual + triagem)
Escopo de triagem = `planejada`, `em_execucao`, `pausada`, `bloqueada`, `aguardando_cliente` (rascunho e terminais ficam de fora). KPIs:
- `atrasadas`: prazo preenchido e `prazo < agora`. O prazo da Demanda é `prazo_etapa_atual` (campo manual e independente — nunca derivado do workflow); é a MESMA noção usada por Notificações/Meu Dia/Pauta.
- `vencemHoje`: prazo dentro do dia LOCAL da empresa (fuso da `regra_expediente`; nunca o do container ou do navegador), intervalo [início do dia, início do dia seguinte). Inclui quem já passou do
  prazo hoje (aparece também em `atrasadas`; cada linha traz `atrasada`).
- `semPrazo`: prazo nulo. `semResponsavel`: com etapa atual → nenhum USUÁRIO responsável pela etapa atual; sem etapa atual (sem workflow ou workflow concluído) → nenhum responsável na Demanda.
  Um departamento responsável sozinho NÃO conta como "responsável" (é fila de departamento, não pessoa).
- `semEtapaAtual`: Demanda aberta com workflow materializado cujas etapas estão todas concluídas (pendência conhecida — conclusão automática do workflow). Contador separado, nunca erro.

## GARGALOS (histórico por período + fila atual)
- Período padrão = últimos 30 dias; máximo 90. `fimEfetivo = min(fim, agora)`.
- Recorte: cada intervalo conta só a parte que cai em [inicio, fimEfetivo] (`duracao_segundos` integral NUNCA é usado); intervalo aberto usa `fimEfetivo` (nada é gravado).
- Identidade da etapa: as métricas são "por DEFINIÇÃO de etapa", não "por etapa materializada". A etapa de workflow é snapshot por Demanda (ids diferentes em cada Demanda; a etapa do template é
  recriada a cada edição do modelo e não é copiada para o snapshot — não existe origem estável por etapa). Definição = nome normalizado + tipo + CONJUNTO CANÔNICO de departamentos responsáveis
  (ids ordenados): mesmo nome e tipo com departamentos diferentes NÃO se agrupam. O workflow de origem não entra na identidade. Ocorrência = (Demanda × etapa materializada): vários ciclos
  execução → pausa → execução da mesma Demanda na mesma etapa somam numa ocorrência. `n` = ocorrências com tempo medido; cada média = soma ÷ ocorrências com tempo > 0 NAQUELE estado.
- `workflowEtapaId` (filtro): UMA etapa materializada → métricas da MESMA definição (nome + tipo + departamentos dessa etapa) em todas as Demandas da empresa; nunca "qualquer etapa de mesmo nome".
- Cobertura: `medicaoDesde` = menor início de intervalo da empresa; `coberturaParcial` quando o período começa antes dele. O passado não é estimado.
- Fila/WIP: estado ATUAL (ignora o período), pela etapa do intervalo aberto (mantida em sincronia com a etapa atual do workflow pelo motor). Idade NA ETAPA = início da sequência contínua de
  intervalos da mesma etapa; devolução à etapa anterior recomeça a contagem.
## FLUXO (estado atual por definição de etapa)
`fluxo()` reaproveita as MESMAS consultas e a MESMA função de identidade (`_definicao`) de Gargalos: `fila_atual` (WIP por definição, universo = intervalo aberto + status de triagem), `tempo_por_etapa` (média em
execução no período) e, só para os cards, `itens_do_fluxo` (mesma CTE `abertos`: mesma etapa, mesmo universo, mesmos filtros). A etapa de cada item é a do intervalo aberto — a mesma que define o WIP em Gargalos.
Cada definição devolve `itensTotal` (contagem independente por janela SQL) que deve igualar `metricas.wip`; o limite só corta cards/colunas, nunca os totais. Ordem das colunas: neutra e determinística
(departamento(s) → nome → tipo → chave) — não existe sequência global entre workflows distintos. Demandas abertas sem etapa atual entram em `semEtapa` (contagem), nunca somem.
- Quebra da pausa por origem (manual × expediente) NÃO é feita: `origem` do intervalo descreve como o intervalo ABRIU, e uma troca de etapa durante a pausa apaga a origem da pausa.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.relogio import agora_utc
from app.repositories.trafego_operacional_repository import (
    STATUS_TRIAGEM,
    FiltrosOperacionais,
    TrafegoOperacionalRepository,
)
from app.schemas.trafego_operacional import (
    AgoraDemandaRead,
    AgoraKpisRead,
    AtualRead,
    DefinicaoEtapaRead,
    EtapaAtualRead,
    FiltrosGargalosRead,
    FilaEtapaRead,
    FilaSemEtapaRead,
    GargaloEtapaRead,
    PeriodoRead,
    RefNomeRead,
    ResponsavelRead,
    TempoSemEtapaRead,
    TrafegoOperacionalAgoraRead,
    TrafegoOperacionalGargalosRead,
)
from app.schemas.trafego_fluxo import (
    FluxoDefinicaoRead,
    FluxoFiltrosRead,
    FluxoItemRead,
    FluxoMetricasRead,
    TrafegoOperacionalFluxoRead,
)

PERIODO_PADRAO = timedelta(days=30)
PERIODO_MAXIMO = timedelta(days=90)
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200
# FLUXO: limites próprios (definições = colunas; itens = cards por coluna).
FLUXO_LIMITE_DEFINICOES_PADRAO = 100
FLUXO_LIMITE_DEFINICOES_MAXIMO = 200
FLUXO_LIMITE_ITENS_PADRAO = 20
FLUXO_LIMITE_ITENS_MAXIMO = 100
FLUXO_PERIODO_DIAS_PADRAO = 30


class PeriodoInvalidoError(ValueError):
    """Período inconsistente (início ≥ fim) ou acima do máximo — 422."""


class EtapaNaoEncontradaError(LookupError):
    """`workflowEtapaId` inexistente ou de outra empresa — 404 nos dois casos."""


def _media(total: int, n: int) -> int | None:
    return total // n if n > 0 else None


def _ids_de_departamentos(deps: str | None) -> list[str]:
    """Conjunto canônico ('id1,id2', ids ordenados) → lista de ids."""
    return [parte for parte in (deps or "").split(",") if parte]


def _definicao(linha: dict, nomes_departamento: dict[str, str]) -> DefinicaoEtapaRead:
    """Identidade da DEFINIÇÃO de etapa: nome normalizado + tipo + conjunto canônico de departamentos. `chave` é um hash determinístico dessa tripla (opaco para o cliente)."""
    ids = _ids_de_departamentos(linha["deps"])
    chave = hashlib.sha1(f"{linha['chave']}\x1f{linha['tipo']}\x1f{','.join(ids)}".encode("utf-8")).hexdigest()  # noqa: S324 — identificador, não segurança
    return DefinicaoEtapaRead(
        chave=chave,
        nome=linha["nome"],
        tipo=linha["tipo"],
        departamentos=[RefNomeRead(id=i, nome=nomes_departamento[i]) for i in ids if i in nomes_departamento],
    )


class TrafegoOperacionalService:
    def __init__(self, repository: TrafegoOperacionalRepository | None = None) -> None:
        self.repository = repository or TrafegoOperacionalRepository()

    # ----------------------------------------------------------------------------------
    # Tempo e fuso
    # ----------------------------------------------------------------------------------

    def _fuso(self, db: Session, empresa_id: str) -> tuple[str, ZoneInfo]:
        """Fuso da empresa (regra de expediente); sem regra ou fuso inválido → fuso oficial da aplicação."""
        nome = self.repository.fuso_da_empresa(db, empresa_id=empresa_id) or get_settings().app_timezone
        try:
            return nome, ZoneInfo(nome)
        except ZoneInfoNotFoundError:
            padrao = get_settings().app_timezone
            return padrao, ZoneInfo(padrao)

    @staticmethod
    def _dia_local(agora: datetime, fuso: ZoneInfo) -> tuple[date, datetime, datetime]:
        """(dia local, início do dia em UTC, início do dia seguinte em UTC) — fronteiras do dia da EMPRESA."""
        dia = agora.astimezone(fuso).date()
        inicio = datetime.combine(dia, time.min, tzinfo=fuso).astimezone(timezone.utc)
        fim = datetime.combine(dia + timedelta(days=1), time.min, tzinfo=fuso).astimezone(timezone.utc)
        return dia, inicio, fim

    # ----------------------------------------------------------------------------------
    # AGORA
    # ----------------------------------------------------------------------------------

    def agora(self, db: Session, *, empresa_id: str, limite: int = LIMITE_PADRAO) -> TrafegoOperacionalAgoraRead:
        limite = max(1, min(limite, LIMITE_MAXIMO))
        agora = agora_utc()
        fuso_nome, fuso = self._fuso(db, empresa_id)
        dia, hoje_inicio, hoje_fim = self._dia_local(agora, fuso)

        kpis = self.repository.kpis_agora(db, empresa_id=empresa_id, agora=agora, hoje_inicio=hoje_inicio, hoje_fim=hoje_fim)
        linhas = self.repository.demandas_em_execucao(db, empresa_id=empresa_id, agora=agora, limite=limite)

        etapa_ids = [linha["etapa_id"] for linha in linhas if linha["etapa_id"] is not None]
        demanda_sem_etapa = [linha["demanda_id"] for linha in linhas if linha["etapa_id"] is None]
        resp_etapa: dict[str, list[ResponsavelRead]] = defaultdict(list)
        for etapa_id, usuario_id, nome in self.repository.responsaveis_das_etapas(db, empresa_id=empresa_id, etapa_ids=etapa_ids):
            resp_etapa[etapa_id].append(ResponsavelRead(usuarioId=usuario_id, nome=nome))
        resp_demanda: dict[str, list[ResponsavelRead]] = defaultdict(list)
        for demanda_id, usuario_id, nome in self.repository.responsaveis_das_demandas(db, empresa_id=empresa_id, demanda_ids=demanda_sem_etapa):
            resp_demanda[demanda_id].append(ResponsavelRead(usuarioId=usuario_id, nome=nome))
        deps_etapa: dict[str, list[RefNomeRead]] = defaultdict(list)
        for etapa_id, departamento_id, nome in self.repository.departamentos_das_etapas(db, empresa_id=empresa_id, etapa_ids=etapa_ids):
            deps_etapa[etapa_id].append(RefNomeRead(id=departamento_id, nome=nome))

        itens: list[AgoraDemandaRead] = []
        for linha in linhas:
            etapa_id = linha["etapa_id"]
            inicio_estado = linha["inicio_estado"]
            prazo = linha["prazo"]
            itens.append(
                AgoraDemandaRead(
                    demandaId=linha["demanda_id"],
                    codigoReferencia=linha["codigo_referencia"],
                    numeroOperacional=linha["numero_operacional"],
                    identificador=linha["identificador"],
                    titulo=linha["titulo"],
                    projeto=RefNomeRead(id=linha["projeto_id"], nome=linha["projeto_nome"]) if linha["projeto_id"] else None,
                    cliente=RefNomeRead(id=linha["cliente_id"], nome=linha["cliente_nome"]) if linha["cliente_id"] else None,
                    etapaAtual=(
                        EtapaAtualRead(id=etapa_id, nome=linha["etapa_nome"], tipo=linha["etapa_tipo"], departamentos=deps_etapa.get(etapa_id, []))
                        if etapa_id is not None
                        else None
                    ),
                    responsaveis=resp_etapa.get(etapa_id, []) if etapa_id is not None else resp_demanda.get(linha["demanda_id"], []),
                    origemResponsaveis="etapa_atual" if etapa_id is not None else "demanda",
                    status=linha["status"],
                    inicioEstadoAtual=inicio_estado,
                    idadeEstadoSegundos=max(0, int((agora - inicio_estado).total_seconds())) if inicio_estado is not None else None,
                    prazo=prazo,
                    atrasada=prazo is not None and prazo < agora,
                )
            )

        total = kpis["em_execucao"]
        return TrafegoOperacionalAgoraRead(
            agoraServidor=agora,
            fusoEmpresa=fuso_nome,
            diaLocal=dia,
            hojeInicio=hoje_inicio,
            hojeFim=hoje_fim,
            escopoStatus=list(STATUS_TRIAGEM),
            kpis=AgoraKpisRead(
                emExecucao=kpis["em_execucao"],
                atrasadas=kpis["atrasadas"],
                vencemHoje=kpis["vencem_hoje"],
                semResponsavel=kpis["sem_responsavel"],
                semPrazo=kpis["sem_prazo"],
                semEtapaAtual=kpis["sem_etapa_atual"],
            ),
            emExecucao=itens,
            emExecucaoTotal=total,
            limite=limite,
            truncado=total > len(itens),
        )

    # ----------------------------------------------------------------------------------
    # GARGALOS
    # ----------------------------------------------------------------------------------

    def gargalos(
        self,
        db: Session,
        *,
        empresa_id: str,
        inicio: datetime | None = None,
        fim: datetime | None = None,
        departamento_id: str | None = None,
        cliente_id: str | None = None,
        projeto_id: str | None = None,
        workflow_etapa_id: str | None = None,
        limite: int = LIMITE_PADRAO,
    ) -> TrafegoOperacionalGargalosRead:
        limite = max(1, min(limite, LIMITE_MAXIMO))
        agora = agora_utc()
        fim = fim if fim is not None else agora
        inicio = inicio if inicio is not None else fim - PERIODO_PADRAO
        if inicio >= fim:
            raise PeriodoInvalidoError("O início do período deve ser anterior ao fim.")
        if fim - inicio > PERIODO_MAXIMO:
            raise PeriodoInvalidoError(f"O período máximo é de {PERIODO_MAXIMO.days} dias.")
        fim_efetivo = min(fim, agora)

        etapa_chave = etapa_tipo = etapa_deps = None
        if workflow_etapa_id is not None:
            definicao = self.repository.definicao_da_etapa(db, empresa_id=empresa_id, etapa_id=workflow_etapa_id)
            if definicao is None:
                raise EtapaNaoEncontradaError("Etapa não encontrada.")
            etapa_chave, etapa_tipo, etapa_deps = definicao
        filtros = FiltrosOperacionais(
            departamento_id=departamento_id,
            cliente_id=cliente_id,
            projeto_id=projeto_id,
            etapa_chave=etapa_chave,
            etapa_tipo=etapa_tipo,
            etapa_deps=etapa_deps,
        )

        medicao = self.repository.medicao_desde(db, empresa_id=empresa_id)
        parcial = medicao is None or inicio < medicao

        linhas = self.repository.tempo_por_etapa(db, empresa_id=empresa_id, inicio=inicio, fim_efetivo=fim_efetivo, filtros=filtros) if fim_efetivo > inicio else []
        fila_linhas = self.repository.fila_atual(db, empresa_id=empresa_id, filtros=filtros)
        # Nomes dos departamentos das definições devolvidas (período + fila) — UMA consulta; os ids vêm do próprio conjunto canônico da definição.
        ids_departamento = sorted({i for linha in (*linhas, *fila_linhas) if linha["chave"] is not None for i in _ids_de_departamentos(linha["deps"])})
        nomes_departamento = self.repository.departamentos_por_ids(db, empresa_id=empresa_id, departamento_ids=ids_departamento)
        etapas: list[GargaloEtapaRead] = []
        sem_etapa = TempoSemEtapaRead(
            n=0, nExecucao=0, tempoExecucaoTotalSegundos=0, tempoExecucaoMedioSegundos=None, tempoExecucaoMaiorSegundos=None, nPausado=0, tempoPausadoTotalSegundos=0,
            nBloqueado=0, tempoBloqueadoTotalSegundos=0, nAguardandoCliente=0, tempoAguardandoClienteTotalSegundos=0,
        )
        for linha in linhas:
            if linha["chave"] is None:
                sem_etapa = TempoSemEtapaRead(
                    n=linha["n"],
                    nExecucao=linha["n_exec"],
                    tempoExecucaoTotalSegundos=linha["exec_total"],
                    tempoExecucaoMedioSegundos=_media(linha["exec_total"], linha["n_exec"]),
                    tempoExecucaoMaiorSegundos=linha["exec_maior"],
                    nPausado=linha["n_pausa"],
                    tempoPausadoTotalSegundos=linha["pausa_total"],
                    nBloqueado=linha["n_bloq"],
                    tempoBloqueadoTotalSegundos=linha["bloq_total"],
                    nAguardandoCliente=linha["n_cli"],
                    tempoAguardandoClienteTotalSegundos=linha["cli_total"],
                )
                continue
            etapas.append(
                GargaloEtapaRead(
                    definicaoEtapa=_definicao(linha, nomes_departamento),
                    n=linha["n"],
                    nExecucao=linha["n_exec"],
                    tempoExecucaoTotalSegundos=linha["exec_total"],
                    tempoExecucaoMedioSegundos=_media(linha["exec_total"], linha["n_exec"]),
                    tempoExecucaoMaiorSegundos=linha["exec_maior"],
                    nPausado=linha["n_pausa"],
                    tempoPausadoTotalSegundos=linha["pausa_total"],
                    tempoPausadoMedioSegundos=_media(linha["pausa_total"], linha["n_pausa"]),
                    tempoPausadoMaiorSegundos=linha["pausa_maior"],
                    nBloqueado=linha["n_bloq"],
                    tempoBloqueadoTotalSegundos=linha["bloq_total"],
                    tempoBloqueadoMedioSegundos=_media(linha["bloq_total"], linha["n_bloq"]),
                    tempoBloqueadoMaiorSegundos=linha["bloq_maior"],
                    nAguardandoCliente=linha["n_cli"],
                    tempoAguardandoClienteTotalSegundos=linha["cli_total"],
                    tempoAguardandoClienteMedioSegundos=_media(linha["cli_total"], linha["n_cli"]),
                    tempoAguardandoClienteMaiorSegundos=linha["cli_maior"],
                )
            )

        fila: list[FilaEtapaRead] = []
        concluido = sem_workflow = 0
        wip = planejadas = em_execucao = pausadas = bloqueadas = aguardando = 0
        for linha in fila_linhas:
            wip += linha["wip"]
            planejadas += linha["planejadas"]
            em_execucao += linha["em_execucao"]
            pausadas += linha["pausadas"]
            bloqueadas += linha["bloqueadas"]
            aguardando += linha["aguardando_cliente"]
            if linha["categoria"] == "workflow_concluido":
                concluido += linha["wip"]
                continue
            if linha["categoria"] == "sem_workflow":
                sem_workflow += linha["wip"]
                continue
            fila.append(
                FilaEtapaRead(
                    definicaoEtapa=_definicao(linha, nomes_departamento),
                    wip=linha["wip"],
                    planejadas=linha["planejadas"],
                    emExecucao=linha["em_execucao"],
                    pausadas=linha["pausadas"],
                    bloqueadas=linha["bloqueadas"],
                    aguardandoCliente=linha["aguardando_cliente"],
                    maisAntigaDesde=linha["mais_antiga_desde"],
                    maisAntigaSegundos=max(0, int((agora - linha["mais_antiga_desde"]).total_seconds())),
                    maisAntigaTruncadaPelaMedicao=bool(linha["mais_antiga_truncada"]),
                    idadeEstadoMaisAntigoSegundos=max(0, int((agora - linha["estado_mais_antigo_desde"]).total_seconds())),
                )
            )

        return TrafegoOperacionalGargalosRead(
            agoraServidor=agora,
            periodo=PeriodoRead(inicio=inicio, fim=fim, fimEfetivo=fim_efetivo),
            filtros=FiltrosGargalosRead(departamentoId=departamento_id, clienteId=cliente_id, projetoId=projeto_id, workflowEtapaId=workflow_etapa_id),
            medicaoDesde=medicao,
            coberturaParcial=parcial,
            etapas=etapas[:limite],
            etapasTotal=len(etapas),
            semEtapa=sem_etapa,
            atual=AtualRead(wip=wip, planejadas=planejadas, emExecucao=em_execucao, pausadas=pausadas, bloqueadas=bloqueadas, aguardandoCliente=aguardando),
            fila=fila[:limite],
            filaTotal=len(fila),
            filaSemEtapa=FilaSemEtapaRead(workflowConcluido=concluido, semWorkflow=sem_workflow),
            limite=limite,
        )

    # ----------------------------------------------------------------------------------
    # FLUXO
    # ----------------------------------------------------------------------------------

    def fluxo(
        self,
        db: Session,
        *,
        empresa_id: str,
        periodo_dias: int = FLUXO_PERIODO_DIAS_PADRAO,
        departamento_id: str | None = None,
        limite_definicoes: int = FLUXO_LIMITE_DEFINICOES_PADRAO,
        limite_itens: int = FLUXO_LIMITE_ITENS_PADRAO,
    ) -> TrafegoOperacionalFluxoRead:
        limite_definicoes = max(1, min(limite_definicoes, FLUXO_LIMITE_DEFINICOES_MAXIMO))
        limite_itens = max(1, min(limite_itens, FLUXO_LIMITE_ITENS_MAXIMO))
        periodo = timedelta(days=max(1, min(periodo_dias, PERIODO_MAXIMO.days)))
        agora = agora_utc()
        fuso_nome, _fuso = self._fuso(db, empresa_id)
        inicio, fim_efetivo = agora - periodo, agora

        filtros = FiltrosOperacionais(departamento_id=departamento_id)
        medicao = self.repository.medicao_desde(db, empresa_id=empresa_id)
        parcial = medicao is None or inicio < medicao

        tempo_linhas = self.repository.tempo_por_etapa(db, empresa_id=empresa_id, inicio=inicio, fim_efetivo=fim_efetivo, filtros=filtros)
        fila_linhas = self.repository.fila_atual(db, empresa_id=empresa_id, filtros=filtros)
        ids_departamento = sorted({i for linha in (*tempo_linhas, *fila_linhas) if linha["chave"] is not None for i in _ids_de_departamentos(linha["deps"])})
        nomes_departamento = self.repository.departamentos_por_ids(db, empresa_id=empresa_id, departamento_ids=ids_departamento)

        # Totais ATUAIS do escopo (inclui as sem etapa) — a mesma contagem de Gargalos.
        wip = planejadas = em_execucao = pausadas = bloqueadas = aguardando = concluido = sem_workflow = 0
        fila_por_definicao: dict[tuple[str, str, str], dict] = {}
        for linha in fila_linhas:
            wip += linha["wip"]
            planejadas += linha["planejadas"]
            em_execucao += linha["em_execucao"]
            pausadas += linha["pausadas"]
            bloqueadas += linha["bloqueadas"]
            aguardando += linha["aguardando_cliente"]
            if linha["categoria"] == "workflow_concluido":
                concluido += linha["wip"]
            elif linha["categoria"] == "sem_workflow":
                sem_workflow += linha["wip"]
            else:
                fila_por_definicao[(linha["chave"], linha["tipo"], linha["deps"])] = linha
        tempo_por_definicao = {(linha["chave"], linha["tipo"], linha["deps"]): linha for linha in tempo_linhas if linha["chave"] is not None}

        # Definições = as que têm WIP agora OU tempo medido no período (estas últimas com WIP 0: coluna vazia, mas com histórico).
        # A DEFINIÇÃO é construída por `_definicao` (a MESMA função de Gargalos); o nome vem da fila quando há WIP, senão do período.
        definicoes: dict[tuple[str, str, str], DefinicaoEtapaRead] = {}
        for chave_bruta in (*fila_por_definicao, *(k for k in tempo_por_definicao if k not in fila_por_definicao)):
            origem = fila_por_definicao.get(chave_bruta) or tempo_por_definicao[chave_bruta]
            definicoes[chave_bruta] = _definicao(origem, nomes_departamento)

        def ordem(chave_bruta: tuple[str, str, str]) -> tuple:
            definicao = definicoes[chave_bruta]
            nomes = "|".join(d.nome.lower() for d in definicao.departamentos)
            return (0 if definicao.departamentos else 1, nomes, definicao.nome.lower(), definicao.tipo, definicao.chave)

        ordenadas = sorted(definicoes, key=ordem)
        selecionadas = ordenadas[:limite_definicoes]

        # Itens: só das definições devolvidas, em UMA consulta (sem N+1). As chaves vêm das linhas do servidor, nunca do cliente.
        itens_linhas = self.repository.itens_do_fluxo(
            db,
            empresa_id=empresa_id,
            filtros=filtros,
            agora=agora,
            chaves=[f"{c}\x1f{tipo}\x1f{deps}" for c, tipo, deps in selecionadas if (c, tipo, deps) in fila_por_definicao],
            limite_itens=limite_itens,
        )
        etapa_ids = [linha["etapa_id"] for linha in itens_linhas]
        responsaveis: dict[str, list[ResponsavelRead]] = defaultdict(list)
        for etapa_id, usuario_id, nome in self.repository.responsaveis_das_etapas(db, empresa_id=empresa_id, etapa_ids=etapa_ids):
            responsaveis[etapa_id].append(ResponsavelRead(usuarioId=usuario_id, nome=nome))
        itens_por_definicao: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for linha in itens_linhas:
            itens_por_definicao[(linha["chave"], linha["tipo"], linha["deps"])].append(linha)

        saida: list[FluxoDefinicaoRead] = []
        for chave_bruta in selecionadas:
            definicao = definicoes[chave_bruta]
            fila = fila_por_definicao.get(chave_bruta)
            tempo = tempo_por_definicao.get(chave_bruta)
            linhas_itens = itens_por_definicao.get(chave_bruta, [])
            itens = [
                FluxoItemRead(
                    demandaId=linha["demanda_id"],
                    codigoReferencia=linha["codigo_referencia"],
                    numeroOperacional=linha["numero_operacional"],
                    identificador=linha["identificador"],
                    titulo=linha["titulo"],
                    status=linha["status"],
                    projeto=RefNomeRead(id=linha["projeto_id"], nome=linha["projeto_nome"]) if linha["projeto_id"] else None,
                    cliente=RefNomeRead(id=linha["cliente_id"], nome=linha["cliente_nome"]) if linha["cliente_id"] else None,
                    etapaAtual=EtapaAtualRead(id=linha["etapa_id"], nome=linha["etapa_nome"], tipo=linha["tipo"], departamentos=definicao.departamentos),
                    definicaoChave=definicao.chave,
                    responsaveis=responsaveis.get(linha["etapa_id"], []),
                    inicioEstadoAtual=linha["inicio_estado"],
                    idadeEstadoSegundos=max(0, int((agora - linha["inicio_estado"]).total_seconds())) if linha["inicio_estado"] is not None else None,
                    prazo=linha["prazo"],
                    atrasada=linha["prazo"] is not None and linha["prazo"] < agora,
                )
                for linha in linhas_itens
            ]
            itens_total = linhas_itens[0]["itens_total"] if linhas_itens else 0
            saida.append(
                FluxoDefinicaoRead(
                    definicaoEtapa=definicao,
                    metricas=FluxoMetricasRead(
                        wip=fila["wip"] if fila else 0,
                        planejadas=fila["planejadas"] if fila else 0,
                        emExecucao=fila["em_execucao"] if fila else 0,
                        pausadas=fila["pausadas"] if fila else 0,
                        bloqueadas=fila["bloqueadas"] if fila else 0,
                        aguardandoCliente=fila["aguardando_cliente"] if fila else 0,
                        maisAntigaSegundos=max(0, int((agora - fila["mais_antiga_desde"]).total_seconds())) if fila else None,
                        maisAntigaTruncadaPelaMedicao=bool(fila["mais_antiga_truncada"]) if fila else None,
                        tempoExecucaoMedioSegundos=_media(tempo["exec_total"], tempo["n_exec"]) if tempo else None,
                        nExecucao=tempo["n_exec"] if tempo else 0,
                    ),
                    itensTotal=itens_total,
                    itensRetornados=len(itens),
                    truncado=itens_total > len(itens),
                    itens=itens,
                )
            )

        return TrafegoOperacionalFluxoRead(
            agoraServidor=agora,
            fusoEmpresa=fuso_nome,
            periodo=PeriodoRead(inicio=inicio, fim=agora, fimEfetivo=fim_efetivo),
            medicaoDesde=medicao,
            coberturaParcial=parcial,
            filtros=FluxoFiltrosRead(departamentoId=departamento_id),
            atual=AtualRead(wip=wip, planejadas=planejadas, emExecucao=em_execucao, pausadas=pausadas, bloqueadas=bloqueadas, aguardandoCliente=aguardando),
            semEtapa=FilaSemEtapaRead(workflowConcluido=concluido, semWorkflow=sem_workflow),
            definicoes=saida,
            definicoesTotal=len(ordenadas),
            definicoesRetornadas=len(saida),
            truncado=len(ordenadas) > len(saida),
            limiteDefinicoes=limite_definicoes,
            limiteItensPorDefinicao=limite_itens,
        )
