import { Building2, ShieldCheck, UserCheck, Users } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Usuario } from "@/types/usuario";

export function UsuariosStats({ usuarios }: { usuarios: Usuario[] }) {
  const ativos = usuarios.filter((usuario) => usuario.ativo).length;
  const gestores = usuarios.filter((usuario) => usuario.perfil === "gestor" || usuario.perfil === "admin" || usuario.perfil === "superadmin" || usuario.perfil === "diretoria").length;
  const departamentos = new Set(usuarios.map((usuario) => usuario.departamentoId).filter(Boolean)).size;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de pessoas" value={usuarios.length} description="Cadastradas na base." icon={<Users size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Podem acessar o sistema." icon={<UserCheck size={16} />} tone="green" />
      <MetricCard index={2} title="Gestão" value={gestores} description="Gestor, Diretoria ou Admin." icon={<ShieldCheck size={16} />} tone="amber" />
      <MetricCard index={3} title="Departamentos" value={departamentos} description="Distintos no cadastro." icon={<Building2 size={16} />} tone="neutral" />
    </div>
  );
}
