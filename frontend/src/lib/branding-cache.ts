// Cache em memória POR CHAVE (uma chave por empresa) — lógica pura, sem `server-only` nem fetch, para poder ser provada
// com `node --test`. Quem usa (lib/server/branding.ts) escolhe a chave: sempre distinta por tenant, nunca um valor global
// compartilhado. TTL por entrada e teto de entradas (despeja a mais antiga): slugs arbitrários vindos da URL não fazem o
// cache crescer sem limite.

export type EntradaCache<T> = { valor: T; expiraEm: number };

export type CachePorChave<T> = {
  obter: (chave: string, agora: number) => T | undefined;
  guardar: (chave: string, valor: T, expiraEm: number) => void;
  limpar: () => void;
  tamanho: () => number;
  chaves: () => string[];
};

export function criarCachePorChave<T>(maxEntradas: number): CachePorChave<T> {
  const mapa = new Map<string, EntradaCache<T>>();
  return {
    obter(chave, agora) {
      const entrada = mapa.get(chave);
      return entrada && entrada.expiraEm > agora ? entrada.valor : undefined;
    },
    guardar(chave, valor, expiraEm) {
      mapa.delete(chave); // reinserir move para o fim (mais recente)
      mapa.set(chave, { valor, expiraEm });
      while (mapa.size > maxEntradas) {
        const maisAntiga = mapa.keys().next().value;
        if (maisAntiga === undefined) break;
        mapa.delete(maisAntiga);
      }
    },
    limpar: () => mapa.clear(),
    tamanho: () => mapa.size,
    chaves: () => [...mapa.keys()],
  };
}

/** Devolve o valor em cache da CHAVE ou busca, guarda (com o TTL que a busca indicar) e devolve. */
export async function resolverComCache<T>(
  cache: CachePorChave<T>,
  chave: string,
  agora: () => number,
  buscar: () => Promise<{ valor: T; ttlMs: number }>,
): Promise<T> {
  const existente = cache.obter(chave, agora());
  if (existente !== undefined) return existente;
  const { valor, ttlMs } = await buscar();
  cache.guardar(chave, valor, agora() + ttlMs);
  return valor;
}
