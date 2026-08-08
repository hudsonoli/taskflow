import type { ReactNode } from "react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { BadgeTone } from "@/components/ui/Badge";

export interface IndicadorItem {
  key: string;
  title: string;
  value: number | string;
  description: string;
  icon: ReactNode;
  tone?: BadgeTone;
}

/** Grid de indicadores reutilizável entre as visões operacionais (Meu Departamento, Minhas Demandas, Tráfego). */
export function IndicadoresGrid({ itens, colunas = 4 }: { itens: IndicadorItem[]; colunas?: 3 | 4 | 5 }) {
  const colClassName =
    colunas === 3 ? "sm:grid-cols-3" : colunas === 5 ? "sm:grid-cols-3 xl:grid-cols-5" : "sm:grid-cols-2 lg:grid-cols-4";

  return (
    <div className={`grid grid-cols-2 gap-4 ${colClassName}`}>
      {itens.map((item, index) => (
        <MetricCard
          key={item.key}
          index={index}
          title={item.title}
          value={item.value}
          description={item.description}
          icon={item.icon}
          tone={item.tone}
        />
      ))}
    </div>
  );
}
