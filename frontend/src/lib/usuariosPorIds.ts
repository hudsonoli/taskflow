import { buscarDiretorioUsuarios, type UsuarioDiretorioItem } from "@/lib/api-backend";

/**
 * Resolve usuários por id a partir do diretório (`GET /usuarios/diretorio`), que não tem filtro por
 * id e é aberto a qualquer autenticado (`GET /usuarios/{id}` exige `usuarios.visualizar`, que quem
 * edita Tarefas — Head/Atendimento — pode não ter). Por isso a resolução VARRE o diretório em
 * páginas de 200, `nome ASC`, parando assim que acha todos os ids pedidos.
 *
 * Só é usada para nomear quem JÁ está selecionado (ex.: responsáveis de uma Demanda aberta para
 * edição), nunca para montar listas de opções. Cada página varrida alimenta um cache curto, então
 * ids vizinhos e consultas repetidas não refazem a varredura. Custo no pior caso (usuário no fim de
 * um diretório grande): uma requisição por 200 usuários, uma vez por TTL — a evolução natural é um
 * filtro `ids` no backend (dívida registrada).
 */
const TAMANHO_PAGINA = 200;
const LIMITE_DE_USUARIOS_VARRIDOS = 5000;
const TTL_MS = 5 * 60 * 1000;

const cache = new Map<string, { usuario: UsuarioDiretorioItem; em: number }>();

export async function resolverUsuariosPorIds(ids: string[]): Promise<UsuarioDiretorioItem[]> {
  const agora = Date.now();
  const encontrados: UsuarioDiretorioItem[] = [];
  const procurados = new Set<string>();
  for (const id of new Set(ids)) {
    const doCache = cache.get(id);
    if (doCache && agora - doCache.em < TTL_MS) encontrados.push(doCache.usuario);
    else procurados.add(id);
  }

  for (let offset = 0; procurados.size > 0 && offset < LIMITE_DE_USUARIOS_VARRIDOS; offset += TAMANHO_PAGINA) {
    const pagina = await buscarDiretorioUsuarios({ limit: TAMANHO_PAGINA, offset });
    for (const usuario of pagina) {
      cache.set(usuario.id, { usuario, em: agora });
      if (procurados.delete(usuario.id)) encontrados.push(usuario);
    }
    if (pagina.length < TAMANHO_PAGINA) break;
  }
  return encontrados;
}
