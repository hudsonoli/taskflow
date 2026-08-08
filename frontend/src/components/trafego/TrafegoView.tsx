"use client";

import { useCallback, useEffect, useState } from "react";
import { listSessoesTrabalho } from "@/lib/api";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioEquipes } from "@/lib/diretorioEquipes";
import { podeAcessarCentralTrafego } from "@/lib/escopo-operacional";
import {
  EMPRESA_TRAFEGO_PADRAO_ID,
  buildCarga,
  buildCargaEquipe,
  buildResumo,
  filterSessoes,
  periodoParaDataInicio,
} from "@/lib/trafego";
import { useNow } from "@/lib/useNow";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { TrafegoFiltersState } from "@/types/trafego";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { TempoOperacionalCard } from "./TempoOperacionalCard";
import { TrafegoAgoraTable } from "./TrafegoAgoraTable";
import { TrafegoCargaDepartamentos } from "./TrafegoCargaDepartamentos";
import { TrafegoCargaEquipes } from "./TrafegoCargaEquipes";
import { TrafegoCargaUsuarios } from "./TrafegoCargaUsuarios";
import { TrafegoFilters } from "./TrafegoFilters";
import { TrafegoHeader } from "./TrafegoHeader";
import { TrafegoIndicadoresDemandas } from "./TrafegoIndicadoresDemandas";
import { TrafegoIniciarSessao } from "./TrafegoIniciarSessao";
import { TrafegoResumoCards } from "./TrafegoResumoCards";

const initialFilters: TrafegoFiltersState = {
  usuarioIds: [],
  departamentoIds: [],
  demandaQuery: "",
  status: "todos",
  periodo: "24h",
};

export function TrafegoView() {
  const { demandas, usuarioAtual } = useAppData();
  const { equipes } = useDiretorioEquipes();
  const [filters, setFilters] = useState<TrafegoFiltersState>(initialFilters);
  const [sessoesAtivas, setSessoesAtivas] = useState<SessaoTrabalho[]>([]);
  const [sessoesEncerradas, setSessoesEncerradas] = useState<SessaoTrabalho[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const now = useNow(1000);

  const carregar = useCallback(async () => {
    setLoading(true);
    setErro(null);
    try {
      const ativasPromise = listSessoesTrabalho({ empresaId: EMPRESA_TRAFEGO_PADRAO_ID, status: "ativa" });
      const encerradasPromise =
        filters.status === "ativa"
          ? Promise.resolve([])
          : listSessoesTrabalho({
              empresaId: EMPRESA_TRAFEGO_PADRAO_ID,
              status: "encerrada",
              dataInicio: periodoParaDataInicio[filters.periodo](),
            });

      const [ativas, encerradas] = await Promise.all([ativasPromise, encerradasPromise]);
      setSessoesAtivas(ativas);
      setSessoesEncerradas(encerradas);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível conectar à API (http://localhost:8010).");
    } finally {
      setLoading(false);
    }
  }, [filters.status, filters.periodo]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  const ativasFiltradas = filterSessoes(sessoesAtivas, filters);
  const encerradasFiltradas = filterSessoes(sessoesEncerradas, filters);
  const resumo = buildResumo(ativasFiltradas, encerradasFiltradas, now);
  const cargaUsuarios = buildCarga(ativasFiltradas, "usuario", now);
  const cargaDepartamentos = buildCarga(ativasFiltradas, "departamento", now);
  const cargaEquipes = buildCargaEquipe(ativasFiltradas, equipes, now);

  if (!usuarioAtual) return null;

  if (!podeAcessarCentralTrafego(usuarioAtual)) {
    return (
      <div className="flex flex-col gap-6">
        <TrafegoHeader onRefresh={carregar} refreshing={loading} />
        <AcessoNegado
          titulo="Central de Tráfego restrita à gestão autorizada"
          descricao="Esta visão reúne carga, capacidade e demandas de toda a operação — disponível apenas para perfis de gestão autorizados nesta fase."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <TrafegoHeader onRefresh={carregar} refreshing={loading} />
      <TrafegoIniciarSessao onCreated={carregar} />
      <TrafegoFilters filters={filters} onChange={setFilters} />

      {erro ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </div>
      ) : (
        <>
          <TrafegoResumoCards resumo={resumo} />
          <TempoOperacionalCard resumo={resumo} />
          <TrafegoIndicadoresDemandas
            demandas={demandas}
            sessoes={[...ativasFiltradas, ...encerradasFiltradas]}
            periodoInicio={periodoParaDataInicio[filters.periodo]()}
          />
          <TrafegoAgoraTable sessoes={ativasFiltradas} now={now} onChanged={carregar} />

          <div className="grid gap-4 lg:grid-cols-3">
            <TrafegoCargaUsuarios cargas={cargaUsuarios} />
            <TrafegoCargaDepartamentos cargas={cargaDepartamentos} />
            <TrafegoCargaEquipes cargas={cargaEquipes} equipes={equipes} />
          </div>
        </>
      )}
    </div>
  );
}
