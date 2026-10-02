import type { TrafegoCargaAgregada } from "@/types/trafego";
import { TrafegoCargaCard } from "./TrafegoCargaCard";

export function TrafegoCargaDepartamentos({ cargas, erro }: { cargas: TrafegoCargaAgregada[] | null; erro?: string | null }) {
  return (
    <TrafegoCargaCard
      title="Carga por departamento"
      description="Setores com execução em andamento."
      emptyTitle="Nenhum departamento em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por departamento."
      cargas={cargas}
      erro={erro}
      color="bg-emerald-500"
      badgeTone="green"
    />
  );
}
