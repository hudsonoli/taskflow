export const MAX_ESFORCO_MINUTOS = 2_147_483_647;

/** Vazio é desconhecido. Inteiro sem unidade é minutos; nunca aceita horas decimais. */
export function parseEsforco(texto: string): number | null {
  const valor = texto.trim().toLowerCase();
  if (!valor) return null;
  const minutos = /^(\d+)\s*(?:min|m)?$/.exec(valor);
  const horas = /^(\d+)\s*h(?:\s*(\d{1,2})\s*(?:min|m)?)?$/.exec(valor);
  let total: number;
  if (minutos) total = Number(minutos[1]);
  else if (horas && Number(horas[2] ?? 0) < 60) total = Number(horas[1]) * 60 + Number(horas[2] ?? 0);
  else throw new Error("Use minutos inteiros ou horas e minutos, por exemplo: 30 min, 1h ou 1h 30min.");
  if (!Number.isSafeInteger(total) || total > MAX_ESFORCO_MINUTOS) throw new Error("Esforço acima do limite permitido.");
  return total;
}

export function formatEsforco(minutos: number | null | undefined): string {
  if (minutos == null) return "Não estimado";
  const h = Math.floor(minutos / 60), m = minutos % 60;
  return h ? `${h}h${m ? ` ${m}min` : ""}` : `${m} min`;
}

export async function salvarEsforco<T>(texto: string, salvar: (minutos: number | null) => Promise<T>) {
  try {
    return { ok: true as const, valor: await salvar(parseEsforco(texto)) };
  } catch (erro) {
    return { ok: false as const, mensagem: erro instanceof Error ? erro.message : "Não foi possível salvar o esforço." };
  }
}
