export const EMPRESA_PADRAO_ID = "empresa-principal";
export const AGENCIA_PADRAO_ID = "agencia-principal";

export function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(Math.random() * 10000);
  return `#${numero.toString().padStart(4, "0")}`;
}

// Numeração de tarefas em continuidade ao iClips, separada por ano: #AA0000.
// O número inicial de cada ano é configurável em Configurações > Numeração de tarefas
// (ver AppDataContext.gerarProximoCodigoTarefa) — ajuste manual no momento da migração.
export function formatCodigoTarefa(ano: number, numero: number): string {
  const anoCurto = ((ano % 100) + 100) % 100;
  return `#${anoCurto.toString().padStart(2, "0")}${numero.toString().padStart(4, "0")}`;
}
