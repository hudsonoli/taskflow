import { Building2, CheckCircle2, Sparkles, Wallet } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { podeVerDadosFinanceiros, type PerfilUsuario } from "@/types/usuario";
import type { Cliente } from "@/types/cliente";

export function ClientesStats({ clientes, perfilAtual }: { clientes: Cliente[]; perfilAtual: PerfilUsuario }) {
  const ativos = clientes.filter((cliente) => cliente.status === "ativo").length;
  const referenciais = clientes.filter((cliente) => cliente.clienteReferencial).length;
  // Centavos no backend (dinheiro nunca em float); converte só na apresentação.
  const feeTotal = clientes.reduce((total, cliente) => total + (cliente.feeMensalCentavos ?? 0), 0) / 100;
  const podeVerFee = podeVerDadosFinanceiros(perfilAtual);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de clientes" value={clientes.length} description="Cadastrados na base." icon={<Building2 size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Com status ativo." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Referenciais" value={referenciais} description="Cases de portfólio." icon={<Sparkles size={16} />} tone="amber" />
      {podeVerFee ? (
        <MetricCard
          index={3}
          title="Fee mensal total"
          value={feeTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })}
          description="Soma dos contratos ativos."
          icon={<Wallet size={16} />}
          tone="neutral"
        />
      ) : (
        <MetricCard index={3} title="Fee mensal total" value="Restrito" description="Visível para Gestão e Diretoria." icon={<Wallet size={16} />} tone="neutral" />
      )}
    </div>
  );
}
