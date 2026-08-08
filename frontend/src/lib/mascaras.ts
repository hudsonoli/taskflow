// Máscaras de apresentação — formatação pura de entrada, sem dado de domínio.
// Extraído de lib/usuarios-mock.ts quando aquele mock foi removido (fechamento da Fase 2A).

export function formatCPF(rawValue: string): string {
  const digits = rawValue.replace(/\D/g, "").slice(0, 11);
  return digits
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}
