"use client";

import { CalendarDays } from "lucide-react";
import clsx from "clsx";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { formatPrazo, normalizarUsuarioId, prioridadeDemandaLabels, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverProjetoNome, resolverUsuarioPorReferencia, rotuloDemanda } from "@/lib/referencias";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import type { Demanda } from "@/types/demanda";
import type { GrupoPrazo } from "@/types/notificacoes";

// "Prazos da equipe": lista de demandas abertas com prazo, já filtrada e paginada NO SERVIDOR no escopo real do
// usuário. Aqui só se apresenta — nomes de responsáveis/projeto vêm dos diretórios já existentes (em lote).
export function PrazosEquipeLista({
  demandas,
  grupo,
  onAbrir,
}: {
  demandas: Demanda[];
  grupo: GrupoPrazo;
  onAbrir: (demandaId: string) => void;
}) {
  const { usuarios } = useUsuariosComIds(demandas.flatMap((demanda) => demanda.usuarioResponsavelIds));
  const { projetos } = useDiretorioProjetos();

  return (
    <ul className="divide-y divide-line">
      {demandas.map((demanda) => {
        const responsaveis = demanda.usuarioResponsavelIds
          .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
          .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));
        return (
          <li key={demanda.id}>
            <button
              type="button"
              onClick={() => onAbrir(demanda.id)}
              className="flex w-full flex-col gap-2 px-4 py-3 text-left transition hover:bg-surface-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus sm:flex-row sm:items-center sm:gap-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-fg">
                  <span className="mr-1.5 font-mono text-xs font-semibold text-fg-muted">{rotuloDemanda(demanda)}</span>
                  {demanda.nome}
                </p>
                <p className="mt-0.5 truncate text-xs text-fg-muted">{resolverProjetoNome(demanda.projetoId, projetos)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                <span className="rounded-full border border-line px-2 py-0.5 text-[11px] font-semibold text-fg-muted">
                  {prioridadeDemandaLabels[demanda.prioridade]}
                </span>
                <span
                  className={clsx(
                    "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold",
                    grupo === "atrasadas"
                      ? "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
                      : grupo === "hoje"
                        ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                        : "bg-surface-2 text-fg-muted",
                  )}
                >
                  <CalendarDays className="h-3.5 w-3.5" />
                  {formatPrazo(demanda.prazoEtapaAtual)}
                </span>
                <AvatarStack
                  pessoas={responsaveis.map((usuario) => ({
                    id: usuario.id,
                    nome: usuario.nome,
                    corIdentificacao: usuario.corIdentificacao,
                    fotoUrl: usuario.fotoUrl,
                  }))}
                  max={3}
                  size="h-7 w-7"
                />
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
