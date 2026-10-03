from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.escopo import EscopoDemanda
from app.core.relogio import agora_local, fuso_aplicacao
from app.domain.event_types import DomainEventType
from app.models.projeto import Projeto
from app.repositories.demanda_repository import DemandaRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.relatorio_repository import RelatorioRepository
from app.schemas.relatorio import (
    ColaboradorContagemRead,
    ContagemAjustesRead,
    ContagemPrioridadeRead,
    RelatorioAjustesProjetoRead,
    RelatorioAnaliseProjetoRead,
    RelatorioColaboradorOpcaoRead,
    RelatorioFatiaRead,
    RelatorioPecaRead,
    RelatorioPecasProjetoRead,
    RelatorioPerformanceColaboradorRead,
    RelatorioPontoSemanalRead,
    RelatorioSegmentoRead,
    RelatorioSerieBarraRead,
)
from app.services.cliente_service import ClienteNotFoundError, ClienteService
from app.services.projeto_service import ProjetoNotFoundError, ProjetoService

# Janela do gráfico "Volume de demandas em fluxo": a semana corrente + as 11 anteriores.
SEMANAS_DO_GRAFICO = 12


class ColaboradorNotFoundError(ValueError):
    pass

TIPO_ENTIDADE_DEMANDA = "demanda"

# Só estes três — `demanda.retorno_cliente_registrado` e qualquer outro tipo de evento (status,
# comentário, checklist, arquivo, criação) não fazem parte de Ajustes/Refações (Fase 2F.4).
_TIPO_EVENTO_PARA_CAMPO: dict[str, str] = {
    DomainEventType.DEMANDA_AJUSTE_INTERNO_REGISTRADO.value: "ajustes_internos",
    DomainEventType.DEMANDA_AJUSTE_CLIENTE_REGISTRADO.value: "ajustes_cliente",
    DomainEventType.DEMANDA_REFACAO_REGISTRADA.value: "refacoes",
}

_CONTAGEM_ZERADA = {"ajustes_internos": 0, "ajustes_cliente": 0, "refacoes": 0}


class RelatorioService:
    def __init__(
        self,
        projeto_service: ProjetoService | None = None,
        demanda_repository: DemandaRepository | None = None,
        evento_repository: EventoRepository | None = None,
        relatorio_repository: RelatorioRepository | None = None,
        cliente_service: ClienteService | None = None,
    ) -> None:
        self.cliente_service = cliente_service or ClienteService()
        self.projeto_service = projeto_service or ProjetoService()
        self.demanda_repository = demanda_repository or DemandaRepository()
        self.evento_repository = evento_repository or EventoRepository()
        self.relatorio_repository = relatorio_repository or RelatorioRepository()

    def _projeto_da_empresa(self, db: Session, *, empresa_id: str, projeto_id: str) -> Projeto:
        """Levanta `ProjetoNotFoundError` (mesma exceção de `ProjetoService`, não uma nova) se
        o Projeto não existir OU pertencer a outra empresa — as duas situações viram o mesmo
        404 na rota, para não confirmar a outro tenant que um UUID existe em outra empresa.
        Reaproveita `projeto_service.get_projeto`, que já é o mecanismo scoped existente; não
        há uma segunda forma de validar Projeto aqui.
        """
        projeto = self.projeto_service.get_projeto(db, projeto_id)
        if projeto.empresa_id != empresa_id:
            raise ProjetoNotFoundError("Projeto não encontrado")
        return projeto

    def analise_projeto(
        self, db: Session, *, escopo: EscopoDemanda, projeto_id: str
    ) -> RelatorioAnaliseProjetoRead:
        """D4A — "Análise de projeto" calculada no servidor (ver `RelatorioRepository`)."""
        projeto = self._projeto_da_empresa(db, empresa_id=escopo.empresa_id, projeto_id=projeto_id)
        dados = self.relatorio_repository.analise_projeto(
            db, escopo=escopo, projeto_id=projeto.id, fuso=fuso_aplicacao().key
        )
        return RelatorioAnaliseProjetoRead(
            projeto_id=projeto.id,
            projeto_nome=projeto.nome,
            total_demandas=dados["total"],
            prioridade=ContagemPrioridadeRead(baixa=dados["baixa"], media=dados["media"], alta=dados["alta"]),
            tempo_medio_abertura_ate_inicio_dias=dados["abertura"],
            tempo_medio_retorno_cliente_dias=dados["retorno"],
            colaboradores=[
                ColaboradorContagemRead(id=usuario_id, nome=nome, demandas=quantidade)
                for usuario_id, nome, quantidade in dados["colaboradores"]
            ],
        )

    def pecas_projeto(
        self, db: Session, *, escopo: EscopoDemanda, projeto_id: str, limit: int, offset: int
    ) -> RelatorioPecasProjetoRead:
        """D4A — "Análise de peças" paginada no servidor (a "peça" é a Demanda do Projeto)."""
        projeto = self._projeto_da_empresa(db, empresa_id=escopo.empresa_id, projeto_id=projeto_id)
        linhas, total = self.relatorio_repository.pecas_projeto(
            db, escopo=escopo, projeto_id=projeto.id, limit=limit, offset=offset
        )
        finalizadas = DemandaRepository._STATUS_FINALIZADOS
        return RelatorioPecasProjetoRead(
            items=[
                RelatorioPecaRead(
                    demanda_id=linha.id,
                    nome=linha.nome,
                    numero_operacional=linha.numero_operacional,
                    redator_nome=linha.redator_nome,
                    tempo_em_pauta_dias=(
                        float(linha.tempo_em_pauta_dias) if linha.tempo_em_pauta_dias is not None else None
                    ),
                    em_andamento=linha.status not in finalizadas,
                )
                for linha in linhas
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ----------------------------------------------------------------------------------
    # D4B — Performance de colaborador e gráficos
    # ----------------------------------------------------------------------------------

    def listar_colaboradores(self, db: Session, *, empresa_id: str) -> list[RelatorioColaboradorOpcaoRead]:
        linhas = self.relatorio_repository.listar_colaboradores(db, empresa_id=empresa_id)
        return [RelatorioColaboradorOpcaoRead(id=usuario_id, nome=nome) for usuario_id, nome in linhas]

    def performance_colaborador(
        self, db: Session, *, escopo: EscopoDemanda, colaborador_id: str
    ) -> RelatorioPerformanceColaboradorRead:
        """Levanta `ColaboradorNotFoundError` para usuário inexistente, de outra empresa ou conta
        de sistema (fora do diretório que alimenta o seletor) — mesmo 404 na rota."""
        colaborador = self.relatorio_repository.obter_colaborador(
            db, empresa_id=escopo.empresa_id, colaborador_id=colaborador_id
        )
        if colaborador is None:
            raise ColaboradorNotFoundError("Colaborador não encontrado")
        dados = self.relatorio_repository.performance_colaborador(
            db, escopo=escopo, colaborador_id=colaborador_id, fuso=fuso_aplicacao().key
        )
        return RelatorioPerformanceColaboradorRead(
            colaborador_id=colaborador.id,
            colaborador_nome=colaborador.nome,
            demandas_entregues=dados["entregues"],
            entregues_no_prazo=dados["no_prazo"],
            entregues_em_atraso=dados["entregues"] - dados["no_prazo"],
            participacao_por_etapa=[
                RelatorioFatiaRead(id=nome, label=nome, value=quantidade) for nome, quantidade in dados["etapas"]
            ],
        )

    def abertas_por_projeto(
        self, db: Session, *, escopo: EscopoDemanda, cliente_id: str
    ) -> list[RelatorioFatiaRead]:
        """Levanta `ClienteNotFoundError` se o Cliente não existir OU for de outra empresa."""
        cliente = self.cliente_service.get_cliente(db, cliente_id)
        if cliente.empresa_id != escopo.empresa_id:
            raise ClienteNotFoundError("Cliente não encontrado")
        linhas = self.relatorio_repository.abertas_por_projeto(db, escopo=escopo, cliente_id=cliente.id)
        return [RelatorioFatiaRead(id=projeto_id, label=nome, value=quantidade) for projeto_id, nome, quantidade in linhas]

    def volume_por_projeto_e_colaborador(
        self, db: Session, *, escopo: EscopoDemanda
    ) -> list[RelatorioSerieBarraRead]:
        projetos, pares = self.relatorio_repository.volume_por_projeto_e_colaborador(db, escopo=escopo)
        segmentos: dict[str, list[RelatorioSegmentoRead]] = {projeto_id: [] for projeto_id, _ in projetos}
        for projeto_id, usuario_id, nome, quantidade in pares:
            if projeto_id in segmentos:
                segmentos[projeto_id].append(RelatorioSegmentoRead(series_id=usuario_id, label=nome, value=quantidade))
        return [
            RelatorioSerieBarraRead(categoria=nome, categoria_id=projeto_id, segmentos=segmentos[projeto_id])
            for projeto_id, nome in projetos
        ]

    def volume_semanal(self, db: Session, *, escopo: EscopoDemanda) -> list[RelatorioPontoSemanalRead]:
        """Demandas criadas por semana, da mais antiga à corrente, com zeros nas semanas vazias.
        "Hoje" e o início da semana (segunda) são do fuso da aplicação — o que o navegador de
        quem está no Brasil sempre fez."""
        hoje = agora_local().date()
        semana_corrente = hoje - timedelta(days=hoje.weekday())
        primeira = semana_corrente - timedelta(weeks=SEMANAS_DO_GRAFICO - 1)
        contagens = self.relatorio_repository.volume_semanal(
            db,
            escopo=escopo,
            primeira_semana=primeira,
            fim_exclusivo=semana_corrente + timedelta(weeks=1),
            fuso=fuso_aplicacao().key,
        )
        pontos = []
        for indice in range(SEMANAS_DO_GRAFICO):
            inicio = primeira + timedelta(weeks=indice)
            pontos.append(RelatorioPontoSemanalRead(inicio_semana=inicio, value=contagens.get(inicio, 0)))
        return pontos

    def ajustes_por_projeto(
        self, db: Session, *, empresa_id: str, projeto_id: str
    ) -> RelatorioAjustesProjetoRead:
        """Contagem real de eventos de ajuste/refação por Projeto (Fase 2F.4); 404 como em
        `_projeto_da_empresa`."""
        self._projeto_da_empresa(db, empresa_id=empresa_id, projeto_id=projeto_id)

        demanda_ids = self.demanda_repository.listar_ids_por_projeto(
            db, empresa_id=empresa_id, projeto_id=projeto_id
        )

        linhas = self.evento_repository.contar_por_tipo_e_entidade(
            db,
            empresa_id=empresa_id,
            entidade_tipo=TIPO_ENTIDADE_DEMANDA,
            entidade_ids=demanda_ids,
            tipos=list(_TIPO_EVENTO_PARA_CAMPO.keys()),
        )

        # `total` é a soma das mesmas linhas que montam `por_demanda` — uma agregação só,
        # nunca uma segunda query para o total.
        por_demanda: dict[str, dict[str, int]] = {}
        total = dict(_CONTAGEM_ZERADA)
        for demanda_id, tipo, quantidade in linhas:
            campo = _TIPO_EVENTO_PARA_CAMPO[tipo]
            contagem = por_demanda.setdefault(demanda_id, dict(_CONTAGEM_ZERADA))
            contagem[campo] += quantidade
            total[campo] += quantidade

        return RelatorioAjustesProjetoRead(
            total=ContagemAjustesRead(**total),
            por_demanda={
                demanda_id: ContagemAjustesRead(**contagem)
                for demanda_id, contagem in por_demanda.items()
            },
        )
