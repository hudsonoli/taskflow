import type { TrafegoCargaAgregada } from "@/types/trafego";
import { TrafegoCargaCard } from "./TrafegoCargaCard";

export function TrafegoCargaEquipes({ cargas, erro }: { cargas: TrafegoCargaAgregada[] | null; erro?: string | null }) {
  return (
    <TrafegoCargaCard
      title="Carga por equipe"
      description="Squads com execução em andamento."
      emptyTitle="Nenhuma equipe em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por equipe."
      cargas={cargas}
      erro={erro}
      color="bg-purple-500"
      badgeTone="blue"
    />
  );
}
