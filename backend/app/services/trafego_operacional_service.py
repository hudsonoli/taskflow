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
- Identidade da etapa: definição = nome normalizado + tipo (a etapa de workflow é snapshot por Demanda; ids não são estáveis). Ocorrência = (Demanda × etapa materializada): vários ciclos
  execução → pausa → execução da mesma Demanda na mesma etapa somam numa ocorrência. `n` = ocorrências com tempo medido; cada média = soma ÷ ocorrências com tempo > 0 NAQUELE estado.
- Cobertura: `medicaoDesde` = menor início de intervalo da empresa; `coberturaParcial` quando o período começa antes dele. O passado não é estimado.
- Fila/WIP: estado ATUAL (ignora o período), pela etapa do intervalo aberto (mantida em sincronia com a etapa atual do workflow pelo motor). Idade NA ETAPA = início da sequência contínua de
  intervalos da mesma etapa; devolução à etapa anterior recomeça a contagem.
- Quebra da pausa por origem (manual × expediente) NÃO é feita: `origem` do intervalo descreve como o intervalo ABRIU, e uma troca de etapa durante a pausa apaga a origem da pausa.
"""

from __future__ import annotations

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

PERIODO_PADRAO = timedelta(days=30)
PERIODO_MAXIMO = timedelta(days=90)
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200


class PeriodoInvalidoError(ValueError):
    """Período inconsistente (início ≥ fim) ou acima do máximo — 422."""


class EtapaNaoEncontradaError(LookupError):
    """`workflowEtapaId` inexistente ou de outra empresa — 404 nos dois casos."""


def _media(total: int, n: int) -> int | None:
    return total // n if n > 0 else None


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

        etapa_chave = etapa_tipo = None
        if workflow_etapa_id is not None:
            definicao = self.repository.definicao_da_etapa(db, empresa_id=empresa_id, etapa_id=workflow_etapa_id)
            if definicao is None:
                raise EtapaNaoEncontradaError("Etapa não encontrada.")
            etapa_chave, etapa_tipo = definicao
        filtros = FiltrosOperacionais(
            departamento_id=departamento_id, cliente_id=cliente_id, projeto_id=projeto_id, etapa_chave=etapa_chave, etapa_tipo=etapa_tipo
        )

        medicao = self.repository.medicao_desde(db, empresa_id=empresa_id)
        parcial = medicao is None or inicio < medicao

        linhas = self.repository.tempo_por_etapa(db, empresa_id=empresa_id, inicio=inicio, fim_efetivo=fim_efetivo, filtros=filtros) if fim_efetivo > inicio else []
        deps_por_def: dict[tuple[str, str], list[RefNomeRead]] = defaultdict(list)
        if linhas:
            for chave, tipo, departamento, nome in self.repository.departamentos_por_definicao_no_periodo(
                db, empresa_id=empresa_id, inicio=inicio, fim_efetivo=fim_efetivo, filtros=filtros
            ):
                deps_por_def[(chave, tipo)].append(RefNomeRead(id=departamento, nome=nome))

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
                    etapaId=linha["etapa_ref_id"],
                    etapaNome=linha["nome"],
                    tipo=linha["tipo"],
                    departamentos=deps_por_def.get((linha["chave"], linha["tipo"]), []),
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

        fila_linhas = self.repository.fila_atual(db, empresa_id=empresa_id, filtros=filtros)
        deps_fila: dict[tuple[str, str], list[RefNomeRead]] = defaultdict(list)
        if any(linha["categoria"] == "etapa" for linha in fila_linhas):
            for chave, tipo, departamento, nome in self.repository.departamentos_da_fila(db, empresa_id=empresa_id, filtros=filtros):
                deps_fila[(chave, tipo)].append(RefNomeRead(id=departamento, nome=nome))

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
                    etapaId=linha["etapa_ref_id"],
                    etapaNome=linha["nome"],
                    tipo=linha["tipo"],
                    departamentos=deps_fila.get((linha["chave"], linha["tipo"]), []),
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
