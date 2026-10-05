import { Building2, ShieldCheck, UserCheck, Users } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { UsuarioResumo } from "@/lib/api-backend";

/**
 * Cards agregados no servidor (`GET /usuarios/resumo`) sobre a empresa inteira — nunca sobre a página
 * carregada nem sobre os filtros da tela. Sem o resumo (carregando/erro) mostra "—", não zero.
 */
export function UsuariosStats({ resumo }: { resumo: UsuarioResumo | null }) {
  const valor = (numero: number | undefined) => numero ?? "—";

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de pessoas" value={valor(resumo?.total)} description="Cadastradas na base." icon={<Users size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={valor(resumo?.ativos)} description="Podem acessar o sistema." icon={<UserCheck size={16} />} tone="green" />
      <MetricCard index={2} title="Gestão" value={valor(resumo?.gestao)} description="Gestor, Diretoria ou Admin." icon={<ShieldCheck size={16} />} tone="amber" />
      <MetricCard index={3} title="Departamentos" value={valor(resumo?.departamentos)} description="Distintos no cadastro." icon={<Building2 size={16} />} tone="neutral" />
    </div>
  );
}
