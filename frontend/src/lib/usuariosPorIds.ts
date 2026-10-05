import { buscarDiretorioUsuariosPorIds, type UsuarioDiretorioItem } from "@/lib/api-backend";

/**
 * Resolução de usuários por id (`GET /usuarios/diretorio/por-ids`) com cache por id e agrupamento.
 *
 * Existe porque o diretório global (`useDiretorioUsuarios`) termina no usuário nº 200: um responsável
 * ou autor além dessa janela ficava sem nome (avatar sumindo, "Usuário removido" ou UUID cru). Aqui
 * só se pergunta pelos ids que o chamador não achou no diretório.
 *
 * - Agrupamento: ids pedidos dentro de uma janela curta (vários cards/linhas montando juntos) saem
 *   numa única requisição, em lotes de até 100 (limite do endpoint), nunca uma por usuário.
 * - Cache por id, 5 min, inclusive "não existe" (null) — não reperguntar a cada render.
 * - Falha não é cacheada como "não existe": fica marcada por 30 s (sem laço de retentativas) e
 *   depois pode ser tentada de novo.
 * - Só ids em formato UUID são enviados (um id fora do formato derrubaria o lote inteiro com 422).
 */
const TAMANHO_LOTE = 100;
const JANELA_AGRUPAMENTO_MS = 10;
const TTL_MS = 5 * 60 * 1000;
const TTL_FALHA_MS = 30 * 1000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Entrada = { usuario: UsuarioDiretorioItem | null; expiraEm: number };
type Pendente = { promise: Promise<void>; resolve: () => void; reject: (erro: unknown) => void };

const cache = new Map<string, Entrada>();
const falhas = new Map<string, number>();
const emAndamento = new Map<string, Pendente>();
let fila = new Set<string>();
let agendado = false;

let versao = 0;
const assinantes = new Set<() => void>();

function notificar(): void {
  versao += 1;
  assinantes.forEach((assinante) => assinante());
}

/** Para `useSyncExternalStore`: muda sempre que o cache ou o conjunto de falhas muda. */
export function assinarUsuariosPorIds(assinante: () => void): () => void {
  assinantes.add(assinante);
  return () => {
    assinantes.delete(assinante);
  };
}

export function versaoUsuariosPorIds(): number {
  return versao;
}

export function ehIdDeUsuario(id: string): boolean {
  return UUID.test(id);
}

/**
 * `undefined` = ainda não se sabe; `null` = o servidor confirmou que não existe (ou não é desta
 * empresa); objeto = resolvido.
 */
export function usuarioEmCache(id: string): UsuarioDiretorioItem | null | undefined {
  const entrada = cache.get(id.toLowerCase());
  if (!entrada || entrada.expiraEm <= Date.now()) return undefined;
  return entrada.usuario;
}

/** A última tentativa de resolver este id falhou há pouco — não insistir agora. */
export function falhouRecentemente(id: string): boolean {
  const expiraEm = falhas.get(id.toLowerCase());
  return expiraEm !== undefined && expiraEm > Date.now();
}

/** Zera tudo (usado quando o cadastro de usuários muda, junto de `invalidarDiretorioUsuarios`). */
export function limparUsuariosPorIds(): void {
  cache.clear();
  falhas.clear();
  notificar();
}

function criarPendente(): Pendente {
  let resolve!: () => void;
  let reject!: (erro: unknown) => void;
  const promise = new Promise<void>((ok, erro) => {
    resolve = ok;
    reject = erro;
  });
  // Quem enfileirou trata o erro; isto só evita "unhandled rejection" se ninguém mais aguarda.
  promise.catch(() => undefined);
  return { promise, resolve, reject };
}

async function descarregarLote(ids: string[]): Promise<void> {
  try {
    const usuarios = await buscarDiretorioUsuariosPorIds(ids);
    const achados = new Map(usuarios.map((usuario) => [usuario.id.toLowerCase(), usuario]));
    const expiraEm = Date.now() + TTL_MS;
    for (const id of ids) {
      cache.set(id, { usuario: achados.get(id) ?? null, expiraEm });
      falhas.delete(id);
      emAndamento.get(id)?.resolve();
      emAndamento.delete(id);
    }
  } catch (erro) {
    const expiraEm = Date.now() + TTL_FALHA_MS;
    for (const id of ids) {
      falhas.set(id, expiraEm);
      emAndamento.get(id)?.reject(erro);
      emAndamento.delete(id);
    }
  }
}

async function descarregarFila(): Promise<void> {
  agendado = false;
  const ids = [...fila];
  fila = new Set();
  const lotes: string[][] = [];
  for (let indice = 0; indice < ids.length; indice += TAMANHO_LOTE) lotes.push(ids.slice(indice, indice + TAMANHO_LOTE));
  await Promise.all(lotes.map(descarregarLote));
  notificar();
}

function enfileirar(id: string): Promise<void> {
  const existente = emAndamento.get(id);
  if (existente) return existente.promise;
  const pendente = criarPendente();
  emAndamento.set(id, pendente);
  fila.add(id);
  if (!agendado) {
    agendado = true;
    setTimeout(() => void descarregarFila(), JANELA_AGRUPAMENTO_MS);
  }
  return pendente.promise;
}

/**
 * Resolve os ids dados (qualquer status, sem conta de sistema; inexistente/de outra empresa fica de
 * fora do resultado). Rejeita se a consulta falhar — o chamador decide o fallback.
 */
export async function resolverUsuariosPorIds(ids: string[]): Promise<UsuarioDiretorioItem[]> {
  const unicos = [...new Set(ids.filter(ehIdDeUsuario).map((id) => id.toLowerCase()))];
  await Promise.all(unicos.filter((id) => usuarioEmCache(id) === undefined).map(enfileirar));
  return unicos.flatMap((id) => {
    const usuario = usuarioEmCache(id);
    return usuario ? [usuario] : [];
  });
}
