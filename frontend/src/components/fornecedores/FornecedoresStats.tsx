import { CheckCircle2, Tag, Truck, XCircle } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Fornecedor } from "@/types/fornecedor";

export function FornecedoresStats({ fornecedores }: { fornecedores: Fornecedor[] }) {
  // Contagem explícita por status: com o arquivamento, "inativos" deixou de ser
  // "total menos ativos" — arquivado é um terceiro estado, não uma variação de inativo.
  const ativos = fornecedores.filter((fornecedor) => fornecedor.status === "ativo").length;
  const inativos = fornecedores.filter((fornecedor) => fornecedor.status === "inativo").length;
  const categorias = new Set(fornecedores.map((fornecedor) => fornecedor.categoria).filter(Boolean)).size;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de fornecedores" value={fornecedores.length} description="Cadastrados na base." icon={<Truck size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Com status ativo." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Inativos" value={inativos} description="Fora de operação." icon={<XCircle size={16} />} tone="neutral" />
      <MetricCard index={3} title="Categorias" value={categorias} description="Distintas no cadastro." icon={<Tag size={16} />} tone="amber" />
    </div>
  );
}
