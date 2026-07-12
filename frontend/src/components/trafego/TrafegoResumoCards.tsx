import {
  Building2,
  CheckCircle2,
  CircleDot,
  Users,
  Workflow,
} from "lucide-react";
import { WorkspaceStats } from "@/components/workspace/WorkspaceStats";
import type { TrafegoResumo } from "@/types/trafego";

type TrafegoResumoCardsProps = {
  resumo: TrafegoResumo;
};

export function TrafegoResumoCards({ resumo }: TrafegoResumoCardsProps) {
  const stats = [
    {
      label: "Sessões ativas",
      value: (
        <span className="inline-flex items-center gap-2">
          <CircleDot className="h-6 w-6 text-blue-700" aria-hidden="true" />
          {resumo.sessoesAtivas}
        </span>
      ),
      description: "Em execução no momento.",
    },
    {
      label: "Sessões encerradas",
      value: (
        <span className="inline-flex items-center gap-2">
          <CheckCircle2
            className="h-6 w-6 text-emerald-600"
            aria-hidden="true"
          />
          {resumo.sessoesEncerradas}
        </span>
      ),
      description: "Finalizadas no período filtrado.",
    },
    {
      label: "Demandas distintas",
      value: (
        <span className="inline-flex items-center gap-2">
          <Workflow className="h-6 w-6 text-sky-600" aria-hidden="true" />
          {resumo.demandasDistintas}
        </span>
      ),
      description: "Demandas com movimentação.",
    },
    {
      label: "Usuários ativos",
      value: (
        <span className="inline-flex items-center gap-2">
          <Users className="h-6 w-6 text-zinc-700" aria-hidden="true" />
          {resumo.usuariosDistintos}
        </span>
      ),
      description: "Usuários nas sessões filtradas.",
    },
    {
      label: "Departamentos ativos",
      value: (
        <span className="inline-flex items-center gap-2">
          <Building2 className="h-6 w-6 text-blue-500" aria-hidden="true" />
          {resumo.departamentosDistintos}
        </span>
      ),
      description: "Setores envolvidos agora.",
    },
  ];

  return <WorkspaceStats stats={stats} />;
}
