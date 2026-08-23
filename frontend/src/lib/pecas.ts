import type { Peca } from "@/types/peca";

/** Entrada de tempo: "2:30" | "2h30" | "2,5" | "150m" → minutos (inválido → null). */
export function parseHoursInput(value: string): number | null {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return null;

  const hourMinuteMatch = trimmed.match(/^(\d+)\s*[:h]\s*(\d{1,2})?$/);
  if (hourMinuteMatch) return Number(hourMinuteMatch[1]) * 60 + Number(hourMinuteMatch[2] ?? 0);

  const minuteMatch = trimmed.match(/^(\d+)\s*m(in)?$/);
  if (minuteMatch) return Number(minuteMatch[1]);

  const decimal = Number(trimmed.replace(",", "."));
  if (Number.isFinite(decimal) && decimal >= 0) return Math.round(decimal * 60);

  return null;
}

export function formatHoursMinutes(minutes: number | null): string {
  if (minutes === null || minutes <= 0) return "";
  const rounded = Math.max(0, Math.round(minutes));
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, "0")}`;
}

export function parseValorInput(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const normalized = trimmed.includes(",") ? trimmed.replace(/\./g, "").replace(",", ".") : trimmed;
  const num = Number(normalized.replace(/[R$\s]/g, ""));
  return Number.isFinite(num) ? Math.round(num * 100) : null;
}

export function formatValorInput(centavos: number | null): string {
  if (centavos === null) return "";
  return (centavos / 100).toFixed(2).replace(".", ",");
}

export function formatBRL(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** Soma dos valores de sindicato (Criação + Adaptação + Finalização) — 0 quando desativado. */
export function valorSindicatoTotalCentavos(peca: Peca): number {
  if (!peca.sindicatoAtivo) return 0;
  return (
    (peca.valorSindicatoCriacaoCentavos ?? 0) +
    (peca.valorSindicatoAdaptacaoCentavos ?? 0) +
    (peca.valorSindicatoFinalizacaoCentavos ?? 0)
  );
}
