"use client";

import type { ReactNode } from "react";
import { useSnapshotExpediente } from "@/lib/estadoExpediente";
import { ForaDoExpedienteView } from "./ForaDoExpedienteView";
import { PausaAutomaticaAviso } from "./PausaAutomaticaAviso";

/**
 * Guarda de ACESSO por expediente (Fase Expediente 2) — só dentro da área autenticada do tenant. Lê o store ÚNICO de `/expediente/estado` (o mesmo polling de ~30 s que
 * Kanban e capacidade já usavam; este componente não cria outro). Fora da janela: troca o app pela tela "Fora do horário de expediente" (e desmonta as telas, que não
 * disparam mais chamadas bloqueadas). Quando o servidor devolve o acesso, o app volta sozinho — sem novo login.
 */
export function ExpedienteGuard({ children, onSair, saindo }: { children: ReactNode; onSair: () => void; saindo: boolean }) {
  const { bloqueio } = useSnapshotExpediente();
  if (bloqueio) return <ForaDoExpedienteView bloqueio={bloqueio} onSair={onSair} saindo={saindo} />;
  return (
    <>
      {children}
      <PausaAutomaticaAviso />
    </>
  );
}
