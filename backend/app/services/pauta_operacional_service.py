"""Pauta operacional por ETAPA (P1_PAUTA_COLABORADOR): monta ITENS neutros (etapa + responsabilidade efetiva + janela planejada) para a interface agrupar por colaborador ou projeto.

- Responsabilidade: `resolver_responsabilidade_etapa` (a regra central), sobre os vínculos carregados em LOTE (4 consultas, sem N+1).
- Geometria: SÓ `planejado_inicio`/`planejado_fim` da etapa. O prazo da etapa atual vem como informação, nunca como posição.
- Período: janela de DATAS do calendário da empresa (segunda da semana atual + 4 semanas por padrão). Janela completa que cruza o período entra; incompleta (início, sem fim) entra se o início não passa
  do fim do período; não planejada entra sempre. Cada balde tem teto próprio e informa o total real (`truncado`), para a interface nunca afirmar uma contagem de recorte enganoso.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.carga_semanal import segunda_da_semana
from app.core.executor_etapa import resolver_responsabilidade_etapa
from app.core.expediente import fuso_da_regra
from app.core.planejamento_etapa import ESTADO_INCOMPLETO, ESTADO_NAO_PLANEJADO, ESTADO_PLANEJADO
from app.core.relogio import agora_utc, fuso_aplicacao
from app.repositories.demanda_repository import DemandaRepository
from app.repositories.pauta_operacional_repository import PautaOperacionalRepository
from app.schemas.pauta_operacional import (
    PautaBucketRead,
    PautaItemRead,
    PautaMetaRead,
    PautaOperacionalRead,
    PautaPessoaRead,
    PautaPlanejamentoRead,
    PautaResponsabilidadeRead,
    PautaTotaisRead,
)
from app.services.regra_expediente_service import RegraExpedienteService

PERIODO_PADRAO_DIAS = 28
PERIODO_MAXIMO_DIAS = 92
LIMITE_POR_BALDE = 1000
_BALDES = ("planejadas", "incompletas", "nao_planejadas")


class PeriodoInvalidoError(ValueError):
    """Período fora do contrato (fim antes do início ou mais de 92 dias). Vira 422."""


class PautaOperacionalService:
    def __init__(
        self,
        repository: PautaOperacionalRepository | None = None,
        demandas: DemandaRepository | None = None,
        regra_service: RegraExpedienteService | None = None,
    ) -> None:
        self.repository = repository or PautaOperacionalRepository()
        self.demandas = demandas or DemandaRepository()
        self.regra_service = regra_service or RegraExpedienteService()

    def _fuso(self, db: Session, empresa_id: str):
        """Fuso da empresa SEM criar regra numa leitura (sem regra = fuso da aplicação)."""
        existente = self.regra_service.repository.get_by_empresa(db, empresa_id)
        if existente is None:
            return fuso_aplicacao()
        return fuso_da_regra(self.regra_service.get_regra_calculo(db, empresa_id=empresa_id))

    def pauta(
        self,
        db: Session,
        *,
        empresa_id: str,
        inicio: date | None = None,
        fim: date | None = None,
        usuario_ids: list[str] | None = None,
        departamento_ids: list[str] | None = None,
        cliente_ids: list[str] | None = None,
        projeto_ids: list[str] | None = None,
        prioridades: list[str] | None = None,
        busca: str | None = None,
    ) -> PautaOperacionalRead:
        agora = agora_utc()
        fuso = self._fuso(db, empresa_id)
        hoje = agora.astimezone(fuso).date()
        if inicio is None:
            inicio = segunda_da_semana(hoje)
        if fim is None:
            fim = inicio + timedelta(days=PERIODO_PADRAO_DIAS - 1)
        if fim < inicio:
            raise PeriodoInvalidoError("fim não pode ser anterior a inicio")
        if (fim - inicio).days + 1 > PERIODO_MAXIMO_DIAS:
            raise PeriodoInvalidoError(f"O período da Pauta é de no máximo {PERIODO_MAXIMO_DIAS} dias")

        filtros = dict(
            empresa_id=empresa_id,
            usuario_ids=usuario_ids or [],
            departamento_ids=departamento_ids or [],
            cliente_ids=cliente_ids or [],
            projeto_ids=projeto_ids or [],
            prioridades=prioridades or [],
            busca=(busca or "").strip() or None,
        )
        totais = self.repository.totais(db, inicio=inicio, fim=fim, **filtros)
        linhas = {balde: self.repository.itens(db, balde=balde, inicio=inicio, fim=fim, limite=LIMITE_POR_BALDE, **filtros) for balde in _BALDES}
        todas = [linha for balde in _BALDES for linha in linhas[balde]]

        if todas:
            etapa_ids = [linha["etapa_id"] for linha in todas]
            demanda_ids = list({linha["demanda_id"] for linha in todas})
            usuarios_etapa = self.demandas.listar_etapa_responsavel_ids_em_lote(db, etapa_ids)
            departamentos_etapa = self.demandas.listar_etapa_departamento_ids_em_lote(db, etapa_ids)
            usuarios_geral = self.demandas.listar_responsavel_ids_em_lote(db, demanda_ids)
            departamentos_geral = self.demandas.listar_departamento_ids_em_lote(db, demanda_ids)
        else:
            usuarios_etapa = departamentos_etapa = usuarios_geral = departamentos_geral = {}

        itens: list[PautaItemRead] = []
        usuarios_vistos: set[str] = set()
        for linha in todas:
            origem, usuarios, departamentos = resolver_responsabilidade_etapa(
                etapa_usuario_ids=usuarios_etapa.get(linha["etapa_id"], []),
                etapa_departamento_ids=departamentos_etapa.get(linha["etapa_id"], []),
                demanda_usuario_ids=usuarios_geral.get(linha["demanda_id"], []),
                demanda_departamento_ids=departamentos_geral.get(linha["demanda_id"], []),
            )
            usuarios_vistos.update(usuarios)
            planejado_inicio, planejado_fim = linha["planejado_inicio"], linha["planejado_fim"]
            if planejado_inicio is None:
                estado, invalido = ESTADO_NAO_PLANEJADO, planejado_fim is not None  # NULL/DATE nunca existe (CHECK); se vier, não quebra a tela
            else:
                estado, invalido = (ESTADO_INCOMPLETO if planejado_fim is None else ESTADO_PLANEJADO), False
            itens.append(
                PautaItemRead(
                    etapa_id=linha["etapa_id"],
                    etapa_nome=linha["etapa_nome"],
                    etapa_tipo=linha["etapa_tipo"],
                    etapa_ordem=linha["etapa_ordem"],
                    etapa_status=linha["etapa_status"],
                    etapa_atual=bool(linha["etapa_atual"]),
                    demanda_id=linha["demanda_id"],
                    demanda_identificador=linha["identificador"],
                    demanda_nome=linha["demanda_nome"],
                    demanda_status=linha["demanda_status"],
                    prioridade=linha["prioridade"],
                    cliente_id=linha["cliente_id"],
                    projeto_id=linha["projeto_id"],
                    prazo_etapa_atual=linha["prazo_etapa_atual"] if linha["etapa_atual"] else None,
                    planejamento=PautaPlanejamentoRead(
                        inicio=None if invalido else planejado_inicio, fim=None if invalido else planejado_fim, estado=estado, invalido=invalido
                    ),
                    responsabilidade_efetiva=PautaResponsabilidadeRead(origem=origem, usuario_ids=usuarios, departamento_ids=departamentos),
                )
            )

        pessoas = [
            PautaPessoaRead(id=usuario_id, nome=nome)
            for usuario_id, nome in self.repository.nomes_dos_usuarios(db, empresa_id=empresa_id, usuario_ids=sorted(usuarios_vistos))
        ]

        def balde(total: int, balde_linhas: list[dict]) -> PautaBucketRead:
            return PautaBucketRead(total=total, devolvidos=len(balde_linhas), truncado=total > len(balde_linhas))

        return PautaOperacionalRead(
            meta=PautaMetaRead(agora_servidor=agora, fuso_empresa=str(getattr(fuso, "key", fuso)), hoje=hoje, inicio=inicio, fim=fim),
            totais=PautaTotaisRead(
                planejadas=balde(totais["planejadas"], linhas["planejadas"]),
                incompletas=balde(totais["incompletas"], linhas["incompletas"]),
                nao_planejadas=balde(totais["nao_planejadas"], linhas["nao_planejadas"]),
                planejadas_antes=totais["antes"],
                planejadas_depois=totais["depois"],
            ),
            itens=itens,
            pessoas=pessoas,
        )
