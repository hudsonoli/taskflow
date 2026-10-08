// Fase 2 — acesso multiempresa por slug. `npm run test:multitenant` (node --test, sem dependências).
// Lógica pura (tenant.ts, branding-cache.ts) é exercitada de verdade; as rotas/telas (.tsx/.ts com alias `@/`, que o
// node --test não resolve) são lidas como texto para provar as garantias de segurança que não aparecem em tipos:
// o slug chega ao BFF, EMPRESA_CODIGO só existe como fallback LEGADO, o cache é por tenant, o console da plataforma é
// neutro e nenhum cookie/header visual autoriza dado de empresa.
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { criarCachePorChave, resolverComCache } from "./branding-cache.ts";
import {
  COOKIE_TENANT_SLUG,
  HEADER_CONTEXTO,
  HEADER_TENANT_SLUG,
  ehRotaDaPlataforma,
  ehRotaDeLogin,
  ehRotaDeRecuperacaoDeSenha,
  hrefDoTenant,
  hrefLogin,
  normalizarSlug,
  rotaDoTenant,
  slugDaRota,
  slugVisual,
  usaTemaDaEmpresa,
} from "./tenant.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const ESTE_TESTE = "lib/multitenant.test.ts";
const caminhoRelativo = (absoluto: string) => absoluto.replace(/\\/g, "/").split("/src/")[1];

function arquivos(dir: URL, acumulado: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = new URL(nome + (statSync(new URL(nome, dir)).isDirectory() ? "/" : ""), dir);
    if (statSync(caminho).isDirectory()) arquivos(caminho, acumulado);
    else if (/\.(ts|tsx)$/.test(nome)) acumulado.push(caminho.pathname.replace(/^\/([A-Za-z]:)/, "$1"));
  }
  return acumulado;
}

// ── slug e rotas: lógica pura ────────────────────────────────────────────────────────────────────────
test("normalizarSlug: válido vira minúsculo; malformado/reservado/ataque vira null (nunca lança)", () => {
  assert.equal(normalizarSlug("  ACME-Dev "), "acme-dev");
  assert.equal(normalizarSlug("demo"), "demo");
  for (const ruim of ["", "ab", "x".repeat(41), "-acme", "acme-", "com espaço", "a_b", "..%2f..%2fetc", "%E0%A4%A", "plataforma", "login", "api", "admin", "suporte", "logout", null, undefined, 42, {}]) {
    assert.equal(normalizarSlug(ruim as unknown), null, String(ruim));
  }
});

test("rotas por slug: só /e/<slug>/<pagina> com slug válido", () => {
  assert.deepEqual(rotaDoTenant("/e/acme/login"), { slug: "acme", pagina: "login" });
  assert.deepEqual(rotaDoTenant("/e/Acme/esqueci-senha"), { slug: "acme", pagina: "esqueci-senha" });
  assert.equal(slugDaRota("/e/acme/redefinir-senha"), "acme");
  for (const nao of ["/login", "/e", "/e/", "/e/login/login", "/e/ab/login", "/x/acme/login", "/meu-dia", "/plataforma/empresas"]) {
    assert.equal(rotaDoTenant(nao), null, nao);
  }
});

test("hrefs: com slug vai para /e/<slug>/..., sem slug (ou inválido) cai no legado", () => {
  assert.equal(hrefLogin("acme"), "/e/acme/login");
  assert.equal(hrefDoTenant("acme", "esqueci-senha"), "/e/acme/esqueci-senha");
  assert.equal(hrefLogin(null), "/login");
  assert.equal(hrefLogin(undefined), "/login");
  assert.equal(hrefLogin("plataforma"), "/login");
  assert.equal(hrefDoTenant(null, "redefinir-senha"), "/redefinir-senha");
});

test("telas públicas: legado e por slug são tratados igual", () => {
  for (const p of ["/login", "/e/acme/login"]) assert.ok(ehRotaDeLogin(p), p);
  for (const p of ["/esqueci-senha", "/redefinir-senha", "/e/acme/esqueci-senha", "/e/acme/redefinir-senha"]) {
    assert.ok(ehRotaDeRecuperacaoDeSenha(p), p);
    assert.ok(usaTemaDaEmpresa(p), p); // antes do login nunca vale preferência de usuário
  }
  assert.ok(usaTemaDaEmpresa("/trocar-senha-inicial") && usaTemaDaEmpresa("/login"));
  assert.ok(!usaTemaDaEmpresa("/meu-dia") && !ehRotaDeLogin("/meu-dia"));
  assert.ok(ehRotaDaPlataforma("/plataforma") && ehRotaDaPlataforma("/plataforma/empresas/x") && !ehRotaDaPlataforma("/plataformax"));
});

test("slugVisual: a rota manda; o cookie só vale COM sessão (a tela pública de outra pessoa nunca herda marca)", () => {
  assert.equal(slugVisual({ slugDaRota: "acme", slugDoCookie: "demo", autenticado: true }), "acme");
  assert.equal(slugVisual({ slugDaRota: null, slugDoCookie: "acme", autenticado: true }), "acme");
  assert.equal(slugVisual({ slugDaRota: null, slugDoCookie: "acme", autenticado: false }), null); // legado
  assert.equal(slugVisual({ slugDaRota: null, slugDoCookie: null, autenticado: true }), null);
});

// ── cache por tenant: a sequência A → B → A não contamina ───────────────────────────────────────────
type Marca = { logo: string; primaria: string; secundaria: string; tema: string };
const MARCAS: Record<string, Marca> = {
  demo: { logo: "sha-demo", primaria: "#ff9500", secundaria: "#7c3aed", tema: "claro" },
  acme: { logo: "sha-acme", primaria: "#ff7a00", secundaria: "#0891b2", tema: "escuro" },
};

function ambiente() {
  const cache = criarCachePorChave<Marca>(100);
  let agora = 1_000;
  const buscas: string[] = [];
  const obter = (slug: string) =>
    resolverComCache(cache, `slug:${slug}`, () => agora, async () => {
      buscas.push(slug);
      return { valor: MARCAS[slug], ttlMs: 30_000 };
    });
  return { cache, obter, buscas, avancar: (ms: number) => (agora += ms) };
}

test("cache: DEMO → ACME → DEMO → ACME devolve sempre a marca da própria empresa", async () => {
  const { obter } = ambiente();
  for (const slug of ["demo", "acme", "demo", "acme", "acme", "demo"]) assert.deepEqual(await obter(slug), MARCAS[slug], slug);
});

test("cache: ACME → DEMO → ACME (ordem inversa) e em paralelo, sem contaminação", async () => {
  const { obter } = ambiente();
  const resultados = await Promise.all(["acme", "demo", "acme", "demo", "demo", "acme"].map((s) => obter(s)));
  assert.deepEqual(resultados, ["acme", "demo", "acme", "demo", "demo", "acme"].map((s) => MARCAS[s]));
  for (const slug of ["acme", "demo", "acme"]) assert.deepEqual(await obter(slug), MARCAS[slug]);
});

test("cache: cada empresa tem a SUA chave e a segunda leitura não vai ao backend", async () => {
  const { cache, obter, buscas } = ambiente();
  await obter("demo");
  await obter("acme");
  await obter("demo");
  await obter("acme");
  assert.deepEqual(buscas, ["demo", "acme"]);
  assert.deepEqual(cache.chaves().sort(), ["slug:acme", "slug:demo"]);
});

test("cache: TTL expira, limpar() (invalidação após salvar branding) e teto de entradas", async () => {
  const { cache, obter, buscas, avancar } = ambiente();
  await obter("acme");
  avancar(29_999);
  await obter("acme");
  assert.equal(buscas.length, 1);
  avancar(2);
  await obter("acme"); // TTL vencido
  assert.equal(buscas.length, 2);
  cache.limpar();
  await obter("acme");
  assert.equal(buscas.length, 3);

  const pequeno = criarCachePorChave<number>(3);
  for (const [i, chave] of ["a", "b", "c", "d"].entries()) pequeno.guardar(chave, i, 10_000);
  assert.equal(pequeno.tamanho(), 3); // slugs arbitrários não fazem o cache crescer sem limite
  assert.equal(pequeno.obter("a", 0), undefined); // a mais antiga foi despejada
  assert.equal(pequeno.obter("d", 0), 3);
});

// ── servidor: o cache real é por tenant e o logo/branding resolve por alvo ──────────────────────────
test("server/branding: chave por empresa, cache em globalThis, sem 'obterBranding' global", () => {
  const branding = ler("lib/server/branding.ts");
  assert.match(branding, /slug:\$\{alvo\.slug\}/);
  assert.match(branding, /legado:\$\{EMPRESA_CODIGO\}/);
  assert.match(branding, /globalThis/);
  assert.match(branding, /\/publico\/empresas\/\$\{encodeURIComponent\(alvo\.slug\)\}\/branding/);
  assert.doesNotMatch(branding, /export (async )?function obterBranding\b/); // a antiga função global saiu
  for (const arquivo of arquivos(new URL("./", SRC))) {
    assert.doesNotMatch(semComentarios(readFileSync(arquivo, "utf8")), /\bobterBranding\(/, arquivo);
  }
});

test("logo: ?slug= vai ao endpoint público do slug; sem slug, legado; nunca arquivo arbitrário nem EMPRESA_CODIGO direto", () => {
  const logo = semComentarios(ler("app/api/branding/logo/route.ts"));
  assert.match(logo, /normalizarSlug\(parametroSlug\)/);
  assert.match(logo, /tipo: "slug", slug/);
  assert.doesNotMatch(logo, /EMPRESA_CODIGO/);
  assert.match(logo, /image\/png/);
  assert.match(logo, /nosniff/);
  assert.doesNotMatch(logo, /readFile|createReadStream|path\.join|storage/i);
  assert.match(ler("lib/branding.ts"), /slug=\$\{encodeURIComponent\(branding\.slug\)\}/);
});

// ── rotas novas ──────────────────────────────────────────────────────────────────────────────────────
test("rotas /e/[slug]/{login,esqueci-senha,redefinir-senha} existem, resolvem a empresa e passam o slug às views", () => {
  const paginas: [string, RegExp][] = [
    ["app/e/[slug]/login/page.tsx", /<LoginView[^>]*slug=\{empresa\.slug\}/],
    ["app/e/[slug]/esqueci-senha/page.tsx", /<EsqueciSenhaView slug=\{empresa\.slug\}/],
    ["app/e/[slug]/redefinir-senha/page.tsx", /<RedefinirSenhaView slug=\{empresa\.slug\}/],
  ];
  for (const [caminho, padrao] of paginas) {
    const pagina = ler(caminho);
    assert.match(pagina, padrao, caminho);
    assert.match(pagina, /empresaDisponivelDaRota/);
    assert.match(pagina, /EmpresaIndisponivelView/);
    assert.doesNotMatch(semComentarios(pagina), /EMPRESA_CODIGO/);
  }
  assert.match(ler("lib/server/tenant-pagina.ts"), /disponivel \? \{ slug, nome/);
});

test("slug inexistente/inativo: uma mensagem só, sem detalhe interno", () => {
  const vista = ler("components/auth/EmpresaIndisponivelView.tsx");
  assert.match(vista, /Empresa não encontrada ou indisponível/);
  assert.doesNotMatch(semComentarios(vista), /inativ|status|slug|404|stack/i);
});

test("as views mantêm o slug nos links e na chamada ao BFF", () => {
  const login = ler("components/auth/LoginView.tsx");
  assert.match(login, /await login\(email, senha, slug\)/);
  assert.match(login, /await loginGoogle\(email, idToken, slug\)/);
  assert.match(login, /hrefDoTenant\(slug, "esqueci-senha"\)/);
  assert.match(ler("components/auth/EsqueciSenhaView.tsx"), /solicitarRedefinicaoSenha\(email\.trim\(\), slug\)/);
  const redefinir = ler("components/auth/RedefinirSenhaView.tsx");
  assert.match(redefinir, /confirmarRedefinicaoSenha\(token, novaSenha, confirmacao, slug\)/);
  for (const v of ["EsqueciSenhaView", "RedefinirSenhaView"]) {
    assert.doesNotMatch(ler(`components/auth/${v}.tsx`), /href="\/login"/); // voltar ao login = login DA empresa
  }
});

// ── BFF: o slug chega ao backend; EMPRESA_CODIGO só no fallback LEGADO ──────────────────────────────
const ROTAS_BFF_PUBLICAS = [
  "app/api/auth/login/route.ts",
  "app/api/auth/google/route.ts",
  "app/api/auth/password-reset/request/route.ts",
  "app/api/auth/password-reset/confirm/route.ts",
];

test("BFF: login, Google e reset recebem empresaSlug e só caem em EMPRESA_CODIGO quando NÃO há slug", () => {
  for (const caminho of ROTAS_BFF_PUBLICAS) {
    const rota = semComentarios(ler(caminho));
    assert.match(rota, /body\?\.empresaSlug/, caminho);
    assert.match(rota, /normalizarSlug\(slugInformado\)/, caminho);
    assert.match(rota, /const empresa = slug \? \{ empresaSlug: slug \} : \{ empresaCodigo: EMPRESA_CODIGO \};/, caminho);
    // o único uso de EMPRESA_CODIGO além do import é o fallback legado acima
    assert.equal((rota.match(/EMPRESA_CODIGO/g) ?? []).length, 2, caminho);
    // slug presente porém inválido NÃO cai no legado
    assert.match(rota, /slugInformado !== undefined && slugInformado !== null && !slug/, caminho);
    // o navegador nunca escolhe empresaCodigo
    assert.doesNotMatch(rota, /body\?\.empresaCodigo|body\.empresaCodigo/, caminho);
  }
});

test("EMPRESA_CODIGO: mapa de usos restantes = só legado intencional (nenhum fluxo por slug depende dele)", () => {
  const usos = arquivos(SRC)
    .map(caminhoRelativo)
    .filter((a) => a !== ESTE_TESTE && /EMPRESA_CODIGO/.test(semComentarios(ler(a))))
    .sort();
  assert.deepEqual(usos, [
    "app/api/auth/google/route.ts", // fallback legado (/login sem slug)
    "app/api/auth/login/route.ts", // fallback legado (/login sem slug)
    "app/api/auth/password-reset/confirm/route.ts", // fallback legado
    "app/api/auth/password-reset/request/route.ts", // fallback legado
    "lib/server/backend.ts", // definição da empresa padrão do servidor
    "lib/server/branding.ts", // alvo "legado" (empresa padrão) do branding
  ]);
});

test("login/Google/reset por slug usam a empresa do slug nas chamadas do cliente (empresaSlug no corpo)", () => {
  const auth = ler("lib/auth.ts");
  assert.equal((auth.match(/\.\.\.\(slug \? \{ empresaSlug: slug \} : \{\}\)/g) ?? []).length, 4);
});

// ── cookies e headers visuais nunca autorizam ────────────────────────────────────────────────────────
test("cookie visual do tenant: não sensível, só no SSR/BFF de sessão — nunca em proxy de dados nem em rota autenticada", () => {
  assert.equal(COOKIE_TENANT_SLUG, "tf_tenant_slug");
  const backend = ler("lib/server/backend.ts");
  const opcoes = backend.slice(backend.indexOf("export function tenantSlugCookieOptions"), backend.indexOf("export const PLATFORM_COOKIE_NAME"));
  assert.match(opcoes, /httpOnly: true/);
  assert.match(opcoes, /path: "\/"/);
  const consumidores = arquivos(SRC)
    .map(caminhoRelativo)
    .filter((a) => a !== ESTE_TESTE && /COOKIE_TENANT_SLUG|HEADER_TENANT_SLUG/.test(semComentarios(ler(a))))
    .sort();
  assert.deepEqual(consumidores, [
    "app/api/auth/logout/route.ts",
    "app/api/auth/session/route.ts",
    "app/layout.tsx",
    "lib/server/tema.ts",
    "lib/tenant.ts",
    "proxy.ts",
  ]);
  // nenhum proxy/BFF de DADOS lê o cookie ou o header visual
  for (const dados of ["app/api/backend/[...path]/route.ts", "app/api/plataforma/[...path]/route.ts"]) {
    assert.doesNotMatch(ler(dados), /tf_tenant_slug|COOKIE_TENANT_SLUG|HEADER_TENANT_SLUG|x-tf-/);
  }
  // o proxy de dados continua autorizando só pelo token da sessão
  assert.match(ler("app/api/backend/[...path]/route.ts"), /SESSION_COOKIE_NAME/);
});

test("proxy.ts apaga os headers internos do navegador e só define o slug a partir do caminho", () => {
  const proxy = ler("proxy.ts");
  assert.match(proxy, /headers\.delete\(HEADER_TENANT_SLUG\)/);
  assert.match(proxy, /headers\.delete\(HEADER_CONTEXTO\)/);
  assert.ok(proxy.indexOf("headers.delete(HEADER_TENANT_SLUG)") < proxy.indexOf("headers.set(HEADER_TENANT_SLUG"));
  assert.match(proxy, /slugDaRota\(pathname\)/);
  assert.equal(HEADER_TENANT_SLUG, "x-tf-tenant-slug");
  assert.equal(HEADER_CONTEXTO, "x-tf-contexto");
});

test("sessão: o cookie visual é reconciliado com a empresa da SESSÃO e some no logout", () => {
  const sessao = ler("app/api/auth/session/route.ts");
  assert.match(sessao, /normalizarSlug\(data\?\.empresaSlug\)/);
  assert.match(sessao, /sincronizarCookieTenant/);
  const login = ler("app/api/auth/login/route.ts");
  assert.match(login, /sincronizarCookieTenant\(cookieStore, visual\.empresaSlug\)/); // da sessão emitida, não do slug digitado
  assert.match(ler("app/api/auth/logout/route.ts"), /cookieStore\.delete\(COOKIE_TENANT_SLUG\)/);
});

test("logout tenant encerra a sessão derivada da plataforma e não mistura cookies", () => {
  const logout = ler("app/api/auth/logout/route.ts");
  assert.match(logout, /cookieStore\.delete\(SESSION_COOKIE_NAME\)/);
  assert.match(logout, /PLATFORM_COOKIE_NAME/); // a sessão de plataforma nasce da tenant: sair encerra as duas
  const encerrarSoPlataforma = ler("app/api/plataforma/sessao/route.ts");
  assert.match(encerrarSoPlataforma, /export async function DELETE/);
  assert.doesNotMatch(encerrarSoPlataforma.slice(encerrarSoPlataforma.indexOf("export async function DELETE")), /SESSION_COOKIE_NAME/);
});

// ── layout, shell e plataforma ───────────────────────────────────────────────────────────────────────
test("layout: marca por alvo (slug da rota → cookie com sessão → legado) e identidade neutra na plataforma", () => {
  const layout = ler("app/layout.tsx");
  assert.match(layout, /slugVisual\(\{ slugDaRota: slugRota, slugDoCookie: slugCookie, autenticado \}\)/);
  assert.match(layout, /obterBrandingPublico\(slug \? \{ tipo: "slug", slug \} : \{ tipo: "legado" \}\)/);
  assert.match(layout, /cabecalhos\.get\(HEADER_CONTEXTO\) === "plataforma"/);
  assert.match(layout, /contextoPlataforma\s*\? \{ branding: BRANDING_PADRAO/);
  assert.match(layout, /tenantSlugInicial=\{slugRota \?\? slugCookie\}/);
});

test("AppShell e menu voltam ao login DA EMPRESA; rotas públicas por slug são tratadas como públicas", () => {
  const shell = ler("components/layout/AppShell.tsx");
  assert.match(shell, /router\.replace\(loginHref\)/);
  assert.match(shell, /ehRotaDeLogin\(pathname\)/);
  assert.match(shell, /ehRotaDeRecuperacaoDeSenha\(pathname\)/);
  assert.doesNotMatch(shell, /router\.replace\("\/login"\)/);
  const menu = ler("components/layout/ProfileMenu.tsx");
  assert.match(menu, /const destino = loginHref/);
  assert.match(menu, /router\.replace\(destino\)/);
});

test("branding da empresa: a marca salva não perde o slug; tema por rota pública usa o da empresa", () => {
  const contexto = ler("lib/BrandingContext.tsx");
  assert.match(contexto, /slug: proximo\.slug \?\? branding\.slug/);
  assert.match(contexto, /usaTemaDaEmpresa\(pathname\)/);
});

test("console /plataforma não vira sessão tenant: a empresa em foco é só rótulo e o cache é invalidado ao salvar", () => {
  assert.match(ler("components/plataforma/PlataformaContext.tsx"), /NÃO muda a sessão/);
  const proxy = ler("app/api/plataforma/[...path]/route.ts");
  assert.match(proxy, /invalidarBranding\(\)/);
  assert.doesNotMatch(semComentarios(ler("components/plataforma/PlataformaShell.tsx")), /useBranding|aplicarBranding/);
});

test("login legado: /login continua existindo e usa a empresa padrão do servidor", () => {
  const legado = ler("app/login/page.tsx");
  assert.match(legado, /<LoginView googleClientId=\{GOOGLE_OAUTH_CLIENT_ID\} \/>/);
  assert.doesNotMatch(legado, /slug=/);
  assert.match(ler("app/esqueci-senha/page.tsx"), /<EsqueciSenhaView \/>/);
  assert.match(ler("app/redefinir-senha/page.tsx"), /<RedefinirSenhaView \/>/);
});

test("/e/[slug] sozinho redireciona para o login da empresa", () => {
  assert.match(ler("app/e/[slug]/page.tsx"), /redirect\(hrefLogin\(normalizarSlug/);
});

test("os dois tipos de sessão seguem separados: slug nenhum entra no BFF de plataforma", () => {
  assert.doesNotMatch(semComentarios(ler("app/api/plataforma/[...path]/route.ts")), /empresaSlug|tf_session|SESSION_COOKIE_NAME/);
});
