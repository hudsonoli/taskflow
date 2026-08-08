export const coresIdentificacaoDisponiveis: { id: string; hex: string }[] = [
  { id: "zinc", hex: "#a1a1aa" },
  { id: "blue", hex: "#3b82f6" },
  { id: "green", hex: "#22c55e" },
  { id: "orange", hex: "#f97316" },
  { id: "red", hex: "#ef4444" },
  { id: "purple", hex: "#a855f7" },
  { id: "pink", hex: "#ec4899" },
  { id: "cyan", hex: "#06b6d4" },
  { id: "yellow", hex: "#eab308" },
  { id: "brown", hex: "#a8785a" },
];

export function resolveCorIdentificacaoHex(corId: string): string {
  return coresIdentificacaoDisponiveis.find((cor) => cor.id === corId)?.hex ?? coresIdentificacaoDisponiveis[0].hex;
}
