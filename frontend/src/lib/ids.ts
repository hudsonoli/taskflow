export const EMPRESA_PADRAO_ID = "empresa-principal";
export const AGENCIA_PADRAO_ID = "agencia-principal";

export function generateId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(Math.random() * 10000);
  return `#${numero.toString().padStart(4, "0")}`;
}
