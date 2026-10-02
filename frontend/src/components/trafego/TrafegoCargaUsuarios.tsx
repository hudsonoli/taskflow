import type { TrafegoCargaAgregada } from "@/types/trafego";
import { TrafegoCargaCard } from "./TrafegoCargaCard";

export function TrafegoCargaUsuarios({ cargas, erro }: { cargas: TrafegoCargaAgregada[] | null; erro?: string | null }) {
  return (
    <TrafegoCargaCard
      title="Carga por usuário"
      description="Colaboradores com sessões ativas no momento."
      emptyTitle="Nenhum usuário em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por usuário."
      cargas={cargas}
      erro={erro}
      color="bg-indigo-500"
      badgeTone="blue"
    />
  );
}
