"use client";

import { useSyncExternalStore } from "react";
import { getEstadoExpedienteReal } from "@/lib/api-backend";
import { criarStoreEstadoExpediente, type SnapshotEstadoExpediente } from "@/lib/expediente-estado-store";

/**
 * Estado operacional de expediente (Fase 2G.3 / Fase Expediente 2), calculado no servidor — nunca no relógio do navegador (ver GET /expediente/estado).
 *
 * UM store e UM polling (~30 s) para o app inteiro, ativo só enquanto há quem use: Kanban, Meu Departamento, a tela de configuração e o guarda do AppShell (que mostra
 * "Fora do horário de expediente") assinam o MESMO dado. A lógica vive em `lib/expediente-estado-store.ts` (pura e testada).
 */

export const storeEstadoExpediente = criarStoreEstadoExpediente({ buscar: getEstadoExpedienteReal });

const SNAPSHOT_SERVIDOR: SnapshotEstadoExpediente = { estado: null, carregando: true, bloqueio: null };

export function useSnapshotExpediente(): SnapshotEstadoExpediente {
  return useSyncExternalStore(storeEstadoExpediente.subscribe, storeEstadoExpediente.getSnapshot, () => SNAPSHOT_SERVIDOR);
}

export function useEstadoExpediente() {
  const { estado, carregando } = useSnapshotExpediente();
  return { estado, carregando };
}
