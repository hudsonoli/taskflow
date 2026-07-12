import { Users } from "lucide-react";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
import {
  classifyCarga,
  formatTempoOperacional,
  resolveTrafegoUsuarioNome,
} from "@/lib/trafego-mock";
import type { TrafegoCargaItem } from "@/types/trafego";

type TrafegoCargaUsuariosProps = {
  cargas: TrafegoCargaItem[];
};

export function TrafegoCargaUsuarios({ cargas }: TrafegoCargaUsuariosProps) {
  return (
    <WorkspaceSection
      title="Carga por usuário"
      description="Sessões ativas agrupadas por colaborador."
    >
      {cargas.length === 0 ? (
        <WorkspaceEmptyState
          title="Nenhum usuário em execução"
          description="Os filtros atuais não retornaram sessões ativas por usuário."
        />
      ) : (
        <div className="space-y-4">
          {cargas.map((carga) => {
            const classification = classifyCarga(
              carga.tempoAtivoTotalSegundos
            );

            return (
              <div
                key={carga.agrupamentoId}
                className="rounded-2xl border border-zinc-100 p-4 transition hover:bg-zinc-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-zinc-900 text-white">
                      <Users className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-zinc-900">
                        {resolveTrafegoUsuarioNome(carga.agrupamentoId)}
                      </p>
                      <p className="text-sm text-zinc-500">
                        {carga.sessoesAtivas} sessão(ões) ·{" "}
                        {carga.demandasDistintas} demanda(s)
                      </p>
                    </div>
                  </div>

                  <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
                    {classification.label}
                  </span>
                </div>

                <div className="mt-4 flex items-center gap-3">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
                    <div
                      className={`h-full rounded-full ${classification.color}`}
                      style={{ width: `${classification.percent}%` }}
                    />
                  </div>
                  <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-zinc-700">
                    {formatTempoOperacional(carga.tempoAtivoTotalSegundos)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </WorkspaceSection>
  );
}
