"use client";

import { useMemo, useState } from "react";
import { Select } from "@/components/ui/Select";
import { MetricCard } from "@/components/ui/MetricCard";
import { ClipboardList, RotateCcw, Timer, UserCog, Users } from "lucide-react";
import { analisarProjeto } from "@/lib/relatorios";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";

function formatDias(dias: number): string {
  if (dias < 1) return `${Math.round(dias * 24)}h`;
  return `${dias.toFixed(1)}d`;
}

export function AnaliseProjetoReport() {
  const { demandas } = useAppData();
  const { projetos } = useDiretorioProjetos();
  const { usuarios } = useDiretorioUsuarios();
  const [projetoIdSelecionado, setProjetoIdSelecionado] = useState("");
  // Diretório carrega assíncrono: `useState(projetos[0]?.id)` capturaria sempre "" no mount.
  // Mesmo padrão derivado de RelatoriosView/PerformanceColaboradorReport.
  const projetoId = projetoIdSelecionado || projetos[0]?.id || "";
  const analise = useMemo(
    () => analisarProjeto(projetoId, demandas, projetos, usuarios),
    [projetoId, demandas, projetos, usuarios],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Projeto"
          value={projetoId}
          onChange={(event) => setProjetoIdSelecionado(event.target.value)}
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <MetricCard index={0} title="Demandas abertas" value={analise.totalDemandas} description="Total no projeto" tone="blue" icon={<ClipboardList size={16} />} />
        <MetricCard
          index={1}
          title="Criação → início"
          value={formatDias(analise.tempoMedioAberturaAteInicioDias)}
          description="Tempo médio até cair no atendimento"
          tone="neutral"
          icon={<Timer size={16} />}
        />
        <MetricCard
          index={2}
          title="Retorno do cliente"
          value={analise.tempoMedioRetornoClienteDias !== null ? formatDias(analise.tempoMedioRetornoClienteDias) : "—"}
          description="Tempo médio de resposta"
          tone="amber"
          icon={<Timer size={16} />}
        />
        <MetricCard index={3} title="Colaboradores" value={analise.colaboradores.length} description="Envolvidos no projeto" tone="green" icon={<Users size={16} />} />
        <MetricCard index={4} title="Ajustes internos" value={analise.ajustesInternos} description="Movimentações internas" tone="blue" icon={<UserCog size={16} />} />
        <MetricCard index={5} title="Ajustes de cliente" value={analise.ajustesCliente} description="Solicitados pelo cliente" tone="amber" icon={<Users size={16} />} />
        <MetricCard index={6} title="Refações" value={analise.refacoes} description="Registradas no período" tone="red" icon={<RotateCcw size={16} />} />
        <MetricCard
          index={7}
          title="Prioridade alta"
          value={analise.prioridade.alta}
          description={`Média ${analise.prioridade.media} · Baixa ${analise.prioridade.baixa}`}
          tone="neutral"
          icon={<ClipboardList size={16} />}
        />
      </div>

      <div className="rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Demandas por colaborador</p>
        {analise.colaboradores.length === 0 ? (
          <p className="text-sm text-zinc-400">Nenhum colaborador com demandas neste projeto.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {analise.colaboradores.map((colaborador) => (
              <li key={colaborador.id} className="flex items-center justify-between text-sm">
                <span className="text-zinc-700 dark:text-zinc-300">{colaborador.nome}</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">{colaborador.demandas} demanda(s)</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
