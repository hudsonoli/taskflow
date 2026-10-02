import type { BadgeTone } from "@/components/ui/Badge";
import type { DemandaArquivoStatusLayout } from "@/types/demanda";

export const STATUS_LAYOUT_LABELS: Record<DemandaArquivoStatusLayout, string> = {
  novo: "Novo",
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  solicitar_alteracao: "Solicitar alteração",
};

export const STATUS_LAYOUT_TONE: Record<DemandaArquivoStatusLayout, BadgeTone> = {
  novo: "neutral",
  aprovado: "green",
  reprovado: "red",
  solicitar_alteracao: "amber",
};

export const STATUS_LAYOUT_OPTIONS = Object.entries(STATUS_LAYOUT_LABELS).map(([value, label]) => ({ value, label }));
