import { Building2, CheckCircle2, CircleDot, Users, Workflow } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { TrafegoResumo } from "@/types/trafego";

/**
 * D2-D3C1 — os valores vêm do servidor (`GET /sessoes-trabalho/trafego/indicadores`), nunca de
 * um array de sessões no cliente. `resumo === null` distingue "carregando" ("…") de "zero
 * confirmado" (0); `erro` cobre falha da requisição ("—", mesmo que haja um resumo anterior —
 * ele seria de outro filtro) — nenhum dos dois fabrica valor.
 */
export function TrafegoResumoCards({ resumo, erro }: { resumo: TrafegoResumo | null; erro?: string | null }) {
  const valor = (campo: number | undefined): number | string => {
    if (erro) return "—";
    if (resumo === null) return "…";
    return campo ?? "—";
  };

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
      <MetricCard index={0} title="Sessões ativas" value={valor(resumo?.sessoesAtivas)} description="Agora" tone="blue" icon={<CircleDot size={16} />} />
      <MetricCard index={1} title="Sessões encerradas" value={valor(resumo?.sessoesEncerradas)} description="Período filtrado" tone="green" icon={<CheckCircle2 size={16} />} />
      <MetricCard index={2} title="Demandas distintas" value={valor(resumo?.demandasDistintas)} description="Com movimentação" tone="blue" icon={<Workflow size={16} />} />
      <MetricCard index={3} title="Usuários ativos" value={valor(resumo?.usuariosDistintos)} description="Nas sessões filtradas" tone="neutral" icon={<Users size={16} />} />
      <MetricCard index={4} title="Departamentos" value={valor(resumo?.departamentosDistintos)} description="Setores envolvidos" tone="amber" icon={<Building2 size={16} />} />
    </div>
  );
}
