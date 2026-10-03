"use client";

import { useState } from "react";
import { Select } from "@/components/ui/Select";
import { MetricCard } from "@/components/ui/MetricCard";
import { ClipboardList, RotateCcw, Timer, UserCog, Users } from "lucide-react";
import type { ContagemAjustes } from "@/lib/api-backend";
import { useAjustesProjeto } from "@/lib/useAjustesProjeto";
import { useAnaliseProjeto } from "@/lib/useAnaliseProjeto";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import type { RelatorioAnaliseProjeto } from "@/types/relatorios";

function formatDias(dias: number): string {
  if (dias < 1) return `${Math.round(dias * 24)}h`;
  return `${dias.toFixed(1)}d`;
}

// Sem Projeto resolvido (diretório vazio) não há consulta: a tela mostra o estado zerado de sempre.
const ANALISE_ZERADA: RelatorioAnaliseProjeto = {
  projetoId: "",
  projetoNome: "",
  totalDemandas: 0,
  prioridade: { baixa: 0, media: 0, alta: 0 },
  tempoMedioAberturaAteInicioDias: null,
  tempoMedioRetornoClienteDias: null,
  colaboradores: [],
};

export function AnaliseProjetoReport() {
  const { projetos } = useDiretorioProjetos();
  const [projetoIdSelecionado, setProjetoIdSelecionado] = useState("");
  // Diretório carrega assíncrono: `useState(projetos[0]?.id)` capturaria sempre "" no mount.
  // Mesmo padrão derivado de RelatoriosView/PerformanceColaboradorReport.
  const projetoId = projetoIdSelecionado || projetos[0]?.id || "";

  // D4A — totais, prioridades, tempos médios e colaboradores vêm do servidor, calculados sobre
  // TODAS as Demandas do Projeto (antes: `analisarProjeto` sobre `AppDataContext.demandas`, só as
  // 200 mais recentes da empresa). `carregando` => "…"; `erro` => "—" (nunca um número parcial).
  const { resultado, carregando, erro } = useAnaliseProjeto(projetoId || null);
  const analise = projetoId ? resultado : ANALISE_ZERADA;
  const valor = (extrair: (dados: RelatorioAnaliseProjeto) => number | string): number | string => {
    if (carregando) return "…";
    if (!analise) return "—";
    return extrair(analise);
  };
  const dias = (valorDias: number | null | undefined): string => (valorDias != null ? formatDias(valorDias) : "—");
  const prioridadeAlta = valor((dados) => dados.prioridade.alta);
  const prioridadeOutras = carregando
    ? "Média … · Baixa …"
    : analise
      ? `Média ${analise.prioridade.media} · Baixa ${analise.prioridade.baixa}`
      : "Média — · Baixa —";

  // Ajustes internos/Ajustes cliente/Refações (Fase 2F.4) vêm de agregação real no backend —
  // requisição própria por Projeto selecionado, separada da análise acima.
  const { resultado: ajustes, carregando: carregandoAjustes, erro: erroAjustes } = useAjustesProjeto(
    projetoId || null,
  );
  const valorAjuste = (campo: keyof ContagemAjustes): number | string => {
    if (carregandoAjustes) return "…";
    if (erroAjustes || !ajustes) return "—";
    return ajustes.total[campo];
  };

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
        <MetricCard index={0} title="Demandas abertas" value={valor((dados) => dados.totalDemandas)} description="Total no projeto" tone="blue" icon={<ClipboardList size={16} />} />
        <MetricCard
          index={1}
          title="Criação → início"
          value={valor((dados) => dias(dados.tempoMedioAberturaAteInicioDias))}
          description="Tempo médio até cair no atendimento"
          tone="neutral"
          icon={<Timer size={16} />}
        />
        <MetricCard
          index={2}
          title="Retorno do cliente"
          value={valor((dados) => dias(dados.tempoMedioRetornoClienteDias))}
          description="Tempo médio de resposta"
          tone="amber"
          icon={<Timer size={16} />}
        />
        <MetricCard index={3} title="Colaboradores" value={valor((dados) => dados.colaboradores.length)} description="Envolvidos no projeto" tone="green" icon={<Users size={16} />} />
        <MetricCard index={4} title="Ajustes internos" value={valorAjuste("ajustesInternos")} description="Movimentações internas" tone="blue" icon={<UserCog size={16} />} />
        <MetricCard index={5} title="Ajustes de cliente" value={valorAjuste("ajustesCliente")} description="Solicitados pelo cliente" tone="amber" icon={<Users size={16} />} />
        <MetricCard index={6} title="Refações" value={valorAjuste("refacoes")} description="Registradas no período" tone="red" icon={<RotateCcw size={16} />} />
        <MetricCard
          index={7}
          title="Prioridade alta"
          value={prioridadeAlta}
          description={prioridadeOutras}
          tone="neutral"
          icon={<ClipboardList size={16} />}
        />
      </div>

      {erro && (
        <p className="text-xs text-red-600 dark:text-red-400">Não foi possível carregar a análise do projeto: {erro}</p>
      )}
      {erroAjustes && (
        <p className="text-xs text-red-600 dark:text-red-400">
          Não foi possível carregar Ajustes internos/Ajustes de cliente/Refações: {erroAjustes}
        </p>
      )}

      <div className="rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Demandas por colaborador</p>
        {carregando ? (
          <p className="text-sm text-zinc-400">Carregando…</p>
        ) : !analise ? (
          <p className="text-sm text-zinc-400">—</p>
        ) : analise.colaboradores.length === 0 ? (
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
