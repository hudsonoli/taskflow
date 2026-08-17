"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { ChartCard } from "@/components/ui/ChartCard";
import { Select } from "@/components/ui/Select";
import { Tabs } from "@/components/ui/Tabs";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { demandasAbertasPorProjeto, resolveClientesComProjeto, volumePorProjetoEColaborador, volumeSemanal } from "@/lib/relatorios";
import { AnalisePecasReport } from "./AnalisePecasReport";
import { AnaliseProjetoReport } from "./AnaliseProjetoReport";
import { DemandasPorProjetoDonut, DemandasPorProjetoTable } from "./DemandasPorProjetoDonut";
import { PerformanceColaboradorReport } from "./PerformanceColaboradorReport";
import { VolumeColaboradorBars, VolumeColaboradorTable } from "./VolumeColaboradorBars";
import { VolumeSemanalLine, VolumeSemanalTable } from "./VolumeSemanalLine";

const SECOES = [
  { id: "graficos", label: "Gráficos" },
  { id: "relatorios", label: "Relatórios" },
];

export function RelatoriosView() {
  const { demandas } = useAppData();
  const { projetos } = useDiretorioProjetos();
  const { clientes } = useDiretorioClientes();
  const { usuarios } = useDiretorioUsuarios();
  const clientesComProjeto = useMemo(() => resolveClientesComProjeto(projetos, clientes), [projetos, clientes]);
  const [secao, setSecao] = useState("graficos");
  const [clienteIdSelecionado, setClienteIdSelecionado] = useState("");
  // Mesmo padrão de PerformanceColaboradorReport: o diretório carrega assíncrono, então
  // `useState(clientesComProjeto[0]?.id)` capturaria sempre "" no mount. Deriva o efetivo a
  // cada render em vez de sincronizar com `useEffect` + `setState`.
  const clienteId = clienteIdSelecionado || clientesComProjeto[0]?.id || "";

  const fatiasPizza = useMemo(() => demandasAbertasPorProjeto(clienteId, demandas, projetos), [clienteId, demandas, projetos]);
  const seriesColaborador = useMemo(
    () => volumePorProjetoEColaborador(demandas, projetos, usuarios),
    [demandas, projetos, usuarios],
  );
  const pontosSemanais = useMemo(() => volumeSemanal(new Date("2026-08-01"), demandas), [demandas]);

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Relatórios e indicadores</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Visão geral de demandas por cliente, projeto, colaborador e período.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <Tabs tabs={SECOES} activeTab={secao} onChange={setSecao} />

      {secao === "graficos" && (
        <div className="flex flex-col gap-6">
          <ChartCard
            title="Demandas em aberto por projeto"
            description="Distribuição percentual das demandas em aberto entre os projetos de um cliente."
            chart={
              <div className="flex flex-col gap-4">
                <div className="max-w-xs">
                  <Select
                    label="Cliente"
                    value={clienteId}
                    onChange={(event) => setClienteIdSelecionado(event.target.value)}
                    options={clientesComProjeto.map((cliente) => ({
                      value: cliente.id,
                      label: cliente.status === "arquivado" ? `${cliente.nome} (arquivado)` : cliente.nome,
                    }))}
                  />
                </div>
                <DemandasPorProjetoDonut fatias={fatiasPizza} />
              </div>
            }
            table={
              <div className="flex flex-col gap-4">
                <div className="max-w-xs">
                  <Select
                    label="Cliente"
                    value={clienteId}
                    onChange={(event) => setClienteIdSelecionado(event.target.value)}
                    options={clientesComProjeto.map((cliente) => ({
                      value: cliente.id,
                      label: cliente.status === "arquivado" ? `${cliente.nome} (arquivado)` : cliente.nome,
                    }))}
                  />
                </div>
                <DemandasPorProjetoTable fatias={fatiasPizza} />
              </div>
            }
          />

          <ChartCard
            title="Volume de demandas por projeto e colaborador"
            description="Quantas demandas cada colaborador toca em cada projeto."
            chart={<VolumeColaboradorBars series={seriesColaborador} />}
            table={<VolumeColaboradorTable series={seriesColaborador} />}
          />

          <ChartCard
            title="Volume de demandas em fluxo"
            description="Demandas criadas por semana, últimas 12 semanas."
            chart={<VolumeSemanalLine pontos={pontosSemanais} />}
            table={<VolumeSemanalTable pontos={pontosSemanais} />}
          />
        </div>
      )}

      {secao === "relatorios" && (
        <div className="flex flex-col gap-6">
          <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-1 text-base font-semibold text-zinc-950 dark:text-zinc-50">Análise de projeto</h2>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              Volume, prazos, ajustes e colaboradores envolvidos em um projeto.
            </p>
            <AnaliseProjetoReport />
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-1 text-base font-semibold text-zinc-950 dark:text-zinc-50">Análise de peças por projeto</h2>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              Tempo em pauta, ajustes e refações de cada peça do projeto.
            </p>
            <AnalisePecasReport />
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-1 text-base font-semibold text-zinc-950 dark:text-zinc-50">Performance de colaborador</h2>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              Entregas, prazos e em qual etapa do workflow o colaborador mais atua.
            </p>
            <PerformanceColaboradorReport />
          </section>
        </div>
      )}
    </div>
  );
}
