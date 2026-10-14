// Sessão tenant EXPIRADA/INVÁLIDA — lógica PURA (sem React; imports relativos para rodar em `node --test`). `npm run test:sessao-expirada`.
//
// Todas as chamadas autenticadas do tenant passam pelo proxy `/api/backend/*` (o BFF lê o cookie HttpOnly e manda o Bearer). Um 401 ali significa SESSÃO INVÁLIDA
// (token ausente, expirado, revogado, usuário/empresa inativos): a ÚNICA fonte de verdade para tratá-lo é o `envolverFetch` abaixo, instalado uma vez pelo
// `AppDataProvider` — nenhuma tela decide sozinha. O que NÃO é sessão expirada (e por isso nunca passa por aqui):
//   • login / Google / recuperação / troca de senha inicial e de senha atual → rotas `/api/auth/*` (a senha errada é um 401 de NEGÓCIO e continua sendo mensagem no formulário);
//   • Portal de Aprovação do cliente → `/api/aprovacao/*`;  • Gestão da plataforma → `/api/plataforma/*` (outro token, outro guarda);
//   • 403 (inclusive o futuro FORA_DO_EXPEDIENTE), 404, 409, 422, 5xx → seguem o tratamento normal de cada tela.
import { PAGINAS_PUBLICAS_DO_TENANT, caminhoDoTenant, normalizarSlug, rotaDoTenant } from "./tenant.ts";

export const MOTIVO_SESSAO_EXPIRADA = "session_expired";
export const MENSAGEM_SESSAO_EXPIRADA = "Sua sessão expirou. Entre novamente.";
const PREFIXO_PROXY_TENANT = "/api/backend/";
const LIMITE_NEXT = 300;

/** Só o proxy autenticado do tenant (`/api/backend/...`), relativo ou absoluto da MESMA origem. Nada de `/api/auth`, `/api/aprovacao`, `/api/plataforma`. */
export function ehChamadaTenantAutenticada(url: string, origem?: string): boolean {
  let caminho = url;
  if (/^https?:\/\//i.test(url)) {
    try {
      const alvo = new URL(url);
      if (origem && alvo.origin !== origem) return false;
      caminho = alvo.pathname;
    } catch {
      return false;
    }
  }
  const semQuery = caminho.split(/[?#]/)[0];
  return semQuery.startsWith(PREFIXO_PROXY_TENANT);
}

/** A tela atual é uma área AUTENTICADA de uma empresa (`/e/<slug>/<página>` que não seja login, recuperação ou Portal de Aprovação). Fora disso (ex.: `/gestao`) não há sessão tenant a encerrar. */
export function ehAreaAutenticadaDoTenant(pathname: string): boolean {
  const rota = rotaDoTenant(pathname);
  if (!rota) return false;
  return !(PAGINAS_PUBLICAS_DO_TENANT as readonly string[]).includes(rota.pagina);
}

export function deveEncerrarPorSessaoExpirada(entrada: { url: string; status: number; pathname: string; origem?: string }): boolean {
  return entrada.status === 401 && ehChamadaTenantAutenticada(entrada.url, entrada.origem) && ehAreaAutenticadaDoTenant(entrada.pathname);
}

/**
 * `next` do login: SÓ um caminho interno do tenant ATUAL. Recusa esquema, `//host`, `\`, `..`, controle, outro tenant, as próprias telas públicas e excesso de tamanho.
 * Devolve o caminho (com query) ou `null`.
 */
export function proximoSeguro(bruto: string | null | undefined, slug: string | null | undefined): string | null {
  const alvo = normalizarSlug(slug);
  if (!alvo || typeof bruto !== "string" || bruto.length === 0 || bruto.length > LIMITE_NEXT) return null;
  if (!bruto.startsWith(`/e/${alvo}/`)) return null; // também barra `//externo`, `https:`, `javascript:` e outro tenant
  let decodificado = bruto;
  try {
    decodificado = decodeURIComponent(bruto);
  } catch {
    return null;
  }
  for (const texto of [bruto, decodificado]) {
    if (/[\\\u0000-\u001f\u007f]/.test(texto) || texto.includes("//") || texto.split(/[/?#]/).includes("..")) return null;
  }
  const rota = rotaDoTenant(bruto.split(/[?#]/)[0]);
  if (!rota || rota.slug !== alvo) return null;
  if ((PAGINAS_PUBLICAS_DO_TENANT as readonly string[]).includes(rota.pagina) || rota.pagina === "trocar-senha-inicial") return null;
  return bruto;
}

/** Destino do redirecionamento por sessão expirada: `/e/<slug>/login?reason=session_expired[&next=<caminho seguro>]`. `null` fora de uma área autenticada do tenant. */
export function hrefLoginPorExpiracao(pathname: string, search = ""): string | null {
  if (!ehAreaAutenticadaDoTenant(pathname)) return null;
  const rota = rotaDoTenant(pathname);
  if (!rota) return null;
  const parametros = new URLSearchParams({ reason: MOTIVO_SESSAO_EXPIRADA });
  const proximo = proximoSeguro(`${pathname}${search}`, rota.slug);
  if (proximo) parametros.set("next", proximo);
  return `${caminhoDoTenant(rota.slug, "login")}?${parametros.toString()}`;
}

/** `?reason=` do login → mensagem discreta; qualquer outro valor é ignorado (nunca ecoa texto da URL). */
export function motivoDoLogin(valor: string | string[] | null | undefined): typeof MOTIVO_SESSAO_EXPIRADA | null {
  const unico = Array.isArray(valor) ? valor[0] : valor;
  return unico === MOTIVO_SESSAO_EXPIRADA ? MOTIVO_SESSAO_EXPIRADA : null;
}

/** Destino pós-login: `next` seguro (quando houver) ou o padrão. */
export function destinoAposLogin(slug: string, proximo: string | null | undefined, padrao: string): string {
  return proximoSeguro(proximo, slug) ?? padrao;
}

/** Singleton idempotente: a ação roda UMA vez até `resetar()` (chamado quando uma nova sessão é estabelecida). */
export function criarCoordenadorDeSessaoExpirada() {
  let disparado = false;
  let disparos = 0;
  return {
    disparar(acao: () => void): boolean {
      if (disparado) return false;
      disparado = true;
      disparos += 1;
      acao();
      return true;
    },
    resetar() {
      disparado = false;
    },
    jaDisparado: () => disparado,
    totalDisparos: () => disparos,
  };
}

const MARCA = Symbol.for("taskflow.fetch.sessao-expirada");
type FetchComMarca = typeof fetch & { [MARCA]?: true };

/**
 * Envolve um `fetch`: depois de cada resposta, se for um 401 do proxy tenant numa área autenticada, chama `aoExpirar` (o coordenador garante uma só execução).
 * A resposta é devolvida INTACTA — quem chamou ainda a recebe, mas a tela já está sendo trocada. Idempotente (não envolve duas vezes).
 *
 * `aoRecusar` (opcional) recebe QUALQUER resposta não-ok do proxy tenant numa área autenticada, para outros tratamentos centrais que não são sessão expirada (ex.:
 * o 403 de política da Fase Expediente 2, decodificado por quem instala). Só observa: nunca altera a resposta e nunca redireciona por conta própria.
 */
export function envolverFetch(
  original: typeof fetch,
  opcoes: {
    aoExpirar: () => void;
    pathname: () => string;
    origem?: () => string | undefined;
    aoRecusar?: (info: { url: string; status: number; resposta: Response }) => void;
  },
): typeof fetch {
  if ((original as FetchComMarca)[MARCA]) return original;
  const envolvido: FetchComMarca = async (entrada, init) => {
    const resposta = await original(entrada, init);
    if (!resposta.ok) {
      const url = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
      if (resposta.status === 401) {
        if (deveEncerrarPorSessaoExpirada({ url, status: resposta.status, pathname: opcoes.pathname(), origem: opcoes.origem?.() })) opcoes.aoExpirar();
      } else if (opcoes.aoRecusar && ehChamadaTenantAutenticada(url, opcoes.origem?.()) && ehAreaAutenticadaDoTenant(opcoes.pathname())) {
        opcoes.aoRecusar({ url, status: resposta.status, resposta });
      }
    }
    return resposta;
  };
  envolvido[MARCA] = true;
  return envolvido;
}
