import { Building2, CheckCircle2, UserCheck, Users } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import { correspondeDepartamento } from "@/lib/referencias";
import type { Departamento } from "@/types/departamento";

export function DepartamentosStats({ departamentos, usuarios }: { departamentos: Departamento[]; usuarios: UsuarioDiretorioItem[] }) {
  const ativos = departamentos.filter((departamento) => departamento.status === "ativo").length;
  const comResponsavel = departamentos.filter((departamento) => departamento.responsavelId).length;
  // A comparação passa pela camada central (id OU codigoInterno) — nunca por igualdade direta.
  const totalPessoas = usuarios.filter(
    (usuario) =>
      !!usuario.departamentoId &&
      departamentos.some((departamento) => correspondeDepartamento(usuario.departamentoId!, departamento)),
  ).length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de departamentos" value={departamentos.length} description="Cadastrados na base." icon={<Building2 size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Em operação." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Com responsável" value={comResponsavel} description="Com pessoa designada." icon={<UserCheck size={16} />} tone="amber" />
      <MetricCard index={3} title="Pessoas alocadas" value={totalPessoas} description="Vinculadas a um departamento." icon={<Users size={16} />} tone="neutral" />
    </div>
  );
}
