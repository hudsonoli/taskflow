import type { ReactNode } from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";

type DashboardWidgetProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

// Casca reutilizável de seção da Dashboard — mesmo raio/borda/sombra do
// padrão Clientes (rounded-2xl, não rounded-3xl). Hoje usada por
// DashboardTaskTrendChart, DashboardAgenda e DashboardRecentActivity;
// qualquer widget futuro (Financeiro, Comercial, Clientes, Equipe,
// Projetos, Tráfego) só precisa envolver seu conteúdo aqui, sem redeclarar
// a casca. Deliberadamente simples nesta fase — sem presets, variantes ou
// registro dinâmico de widgets.
export function DashboardWidget({
  title,
  description,
  action,
  children,
  className,
}: DashboardWidgetProps) {
  return (
    <section
      className={`rounded-2xl border border-zinc-100 bg-white p-4 shadow-sm ${className ?? ""}`}
    >
      <SectionHeader title={title} description={description} action={action} />
      <div className="mt-4">{children}</div>
    </section>
  );
}
