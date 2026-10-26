// @menções de usuários em comentários — funções PURAS (sem React): rodam no `node --test`.
//
// Modelo: o TEXTO guarda o rótulo legível ("@Raquel Oliveira") e a identidade vai à parte, como `usuarioId` (escolhido no autocomplete). Digitar "@Raquel" à mão NÃO é menção:
// só vira menção quem foi selecionado na lista. O servidor revalida tudo (empresa, status, acesso à tarefa e a presença do rótulo no texto).

export type Mencionavel = { id: string; nome: string; cargo?: string | null };
export type MencaoSalva = { usuarioId: string; nome: string };
export type SegmentoTexto = { tipo: "texto" | "mencao"; valor: string };

/** A consulta do autocomplete em andamento: onde o "@" começa e o que foi digitado depois dele (até o cursor). */
export type MencaoAtiva = { inicio: number; consulta: string };

const MAX_CONSULTA = 30; // nomes têm espaços ("Raquel Oliveira"): a consulta pode continuar depois de um espaço, mas não indefinidamente
const MAX_ESPACOS = 2;

export const rotuloDaMencao = (nome: string): string => `@${nome}`;

const ehEspacoOuInicio = (caractere: string | undefined): boolean => caractere === undefined || /\s/.test(caractere);

/** Há um "@" de menção imediatamente antes do cursor? O "@" precisa abrir uma palavra (início do texto ou depois de espaço/quebra), nunca no meio de um e-mail. */
export function detectarMencaoAtiva(texto: string, cursor: number): MencaoAtiva | null {
  const ate = texto.slice(0, Math.max(0, Math.min(cursor, texto.length)));
  const arroba = ate.lastIndexOf("@");
  if (arroba < 0) return null;
  if (!ehEspacoOuInicio(ate[arroba - 1])) return null;
  const consulta = ate.slice(arroba + 1);
  if (consulta.length > MAX_CONSULTA || /[\n\r@]/.test(consulta)) return null;
  if (consulta.length > 0 && /^\s/.test(consulta)) return null; // "@ " não é menção
  if ((consulta.match(/\s/g) ?? []).length > MAX_ESPACOS) return null;
  return { inicio: arroba, consulta };
}

/** Troca "@consulta" (do "@" ao cursor) pelo rótulo escolhido + um espaço, e devolve o novo cursor (logo depois do espaço). */
export function inserirMencao(texto: string, ativa: MencaoAtiva, cursor: number, usuario: Pick<Mencionavel, "nome">): { texto: string; cursor: number } {
  const antes = texto.slice(0, ativa.inicio);
  const depois = texto.slice(cursor);
  const token = `${rotuloDaMencao(usuario.nome)} `;
  const semEspacoDuplo = depois.startsWith(" ") ? depois.slice(1) : depois;
  return { texto: `${antes}${token}${semEspacoDuplo}`, cursor: antes.length + token.length };
}

const contemRotulo = (texto: string, nome: string): boolean => texto.toLocaleLowerCase("pt-BR").includes(rotuloDaMencao(nome).toLocaleLowerCase("pt-BR"));

/** Mantém só as seleções cujo "@Nome" ainda está no texto (apagar o rótulo desfaz a menção) e sem repetir pessoa. */
export function reconciliarSelecionadas<T extends Pick<Mencionavel, "id" | "nome">>(texto: string, selecionadas: readonly T[]): T[] {
  const vistos = new Set<string>();
  return selecionadas.filter((pessoa) => {
    if (vistos.has(pessoa.id) || !contemRotulo(texto, pessoa.nome)) return false;
    vistos.add(pessoa.id);
    return true;
  });
}

/** Os ids a enviar ao servidor (únicos, na ordem em que foram escolhidos). */
export const idsDasMencoes = (selecionadas: readonly Pick<Mencionavel, "id">[]): string[] => [...new Set(selecionadas.map((pessoa) => pessoa.id))];

const ESCAPAR = /[.*+?^${}()|[\]\\]/g;

/** Divide o texto em trechos comuns e menções reais (as que o servidor guardou), para destacar só elas. O rótulo precisa terminar numa fronteira (não no meio de outra palavra). */
export function segmentarComMencoes(texto: string, mencoes: readonly MencaoSalva[]): SegmentoTexto[] {
  const nomes = [...new Set(mencoes.map((m) => m.nome).filter(Boolean))].sort((a, b) => b.length - a.length);
  if (nomes.length === 0 || !texto) return texto ? [{ tipo: "texto", valor: texto }] : [];
  const padrao = new RegExp(`@(?:${nomes.map((nome) => nome.replace(ESCAPAR, "\\$&")).join("|")})(?![\\p{L}\\p{N}])`, "giu");
  const segmentos: SegmentoTexto[] = [];
  let ultimo = 0;
  for (const achado of texto.matchAll(padrao)) {
    const inicio = achado.index ?? 0;
    if (inicio > 0 && !ehEspacoOuInicio(texto[inicio - 1]) && !/[([{"'“]/.test(texto[inicio - 1])) continue; // "@" no meio de uma palavra não é menção
    if (inicio > ultimo) segmentos.push({ tipo: "texto", valor: texto.slice(ultimo, inicio) });
    segmentos.push({ tipo: "mencao", valor: achado[0] });
    ultimo = inicio + achado[0].length;
  }
  if (ultimo < texto.length) segmentos.push({ tipo: "texto", valor: texto.slice(ultimo) });
  return segmentos;
}
