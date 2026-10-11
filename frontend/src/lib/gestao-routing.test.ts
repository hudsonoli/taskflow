// Fase 10A — Gestão da plataforma em /gestao. `npm run test:gestao-routing` (node --test, sem dependências).
// A interface administrativa saiu de /plataforma e passou para /gestao; as empresas continuam SÓ em /e/<slug>/... A Gestão é transversal: não tem slug, não
// resolve tenant implícito, usa a identidade do produto (TaskFlow) e só abre para o Administrador da Plataforma (autoridade decidida no backend).
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { SLUG_RESERVADOS } from "./plataforma.ts";
import { hrefDaEmpresa } from "./plataformaDashboard.ts";
import { CONTEXTO_GESTAO, ehRotaDeGestao, normalizarSlug, rotaDoTenant, slugDaRota } from "./tenant.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const existe = (caminho: string) => existsSync(new URL(caminho, SRC));
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function arquivos(dir: URL, acumulado: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    const caminho = new URL(nome + (statSync(new URL(nome, dir)).isDirectory() ? "/" : ""), dir);
    if (statSync(caminho).isDirectory()) arquivos(caminho, acumulado);
    else if (/\.(ts|tsx)$/.test(nome) && !/\.test\.ts$/.test(nome)) acumulado.push(caminho.pathname.replace(/^\/([A-Za-z]:)/, "$1"));
  }
  return acumulado;
}
const fontes = arquivos(SRC).map((a) => a.replace(/\\/g, "/").split("/src/")[1]);

// ── rotas ────────────────────────────────────────────────────────────────────────────────────────────────────

test("/gestao e filhas são a Gestão; /plataforma deixou de existir (sem redirect); /e/<slug>/gestao NÃO é a Gestão", () => {
  for (const p of ["/gestao", "/gestao/empresas", "/gestao/empresas/abc-123"]) assert.equal(ehRotaDeGestao(p), true, p);
  for (const p of ["/plataforma", "/plataforma/empresas", "/gestaox", "/e/boxcom/gestao", "/e/boxcom/gestao/empresas", "/gestao-x", "/"]) {
    assert.equal(ehRotaDeGestao(p), false, p);
  }
  // `/e/boxcom/gestao` é só uma página (inexistente) do tenant boxcom — nunca a Gestão
  assert.deepEqual(rotaDoTenant("/e/boxcom/gestao"), { slug: "boxcom", pagina: "gestao" });
  assert.equal(existe("app/e/[slug]/gestao/page.tsx"), false);
  assert.equal(existe("app/gestao/e/[slug]/page.tsx"), false);
  // a interface antiga não é servida em nenhum caminho
  assert.equal(existe("app/plataforma/page.tsx"), false);
  assert.equal(existe("app/plataforma/layout.tsx"), false);
  assert.equal(existe("app/plataforma/empresas/page.tsx"), false);
  const raiz = new URL("app/", SRC);
  assert.deepEqual(readdirSync(raiz).filter((n) => statSync(new URL(n, raiz)).isDirectory()).sort(), ["api", "e", "gestao"]);
});

test("as páginas reais da Gestão existem e só delegam às Views (sem sub-rotas inúteis)", () => {
  assert.match(semComentarios(ler("app/gestao/page.tsx")), /<PlataformaDashboardView \/>/);
  assert.match(semComentarios(ler("app/gestao/empresas/page.tsx")), /<EmpresasPlataformaView \/>/);
  assert.match(semComentarios(ler("app/gestao/empresas/[id]/page.tsx")), /<EmpresaPlataformaView empresaId=\{id\} \/>/);
  const rotas = fontes.filter((f) => f.startsWith("app/gestao/") && f.endsWith("page.tsx")).sort();
  assert.deepEqual(rotas, ["app/gestao/empresas/[id]/page.tsx", "app/gestao/empresas/page.tsx", "app/gestao/page.tsx"]);
});

test("a gestão da empresa vive em /gestao/empresas/<id>: o id é um RECURSO, nunca o tenant da sessão", () => {
  assert.equal(hrefDaEmpresa({ id: "abc-123" }), "/gestao/empresas/abc-123");
  assert.equal(hrefDaEmpresa({ id: "a/b" }), "/gestao/empresas/a%2Fb");
  assert.equal(slugDaRota("/gestao/empresas/abc-123"), null);
  assert.equal(rotaDoTenant("/gestao/empresas/abc-123"), null);
});

test("nenhum link/navegação da interface aponta para /plataforma; a API segue em /api/plataforma", () => {
  const achados: string[] = [];
  for (const arquivo of fontes) {
    if (arquivo.startsWith("app/api/")) continue;
    const texto = semComentarios(ler(arquivo));
    for (const m of texto.matchAll(/(?:href=\{?["'`]|router\.(?:push|replace)\(\s*["'`]|redirect\(\s*["'`]|href: ["'`])(\/plataforma[^"'`]*)/g)) achados.push(`${arquivo}: ${m[1]}`);
  }
  assert.deepEqual(achados, []);
  // BFF/API mantidos (o requisito é a URL da interface)
  for (const rota of ["app/api/plataforma/[...path]/route.ts", "app/api/plataforma/acesso/route.ts", "app/api/plataforma/sessao/route.ts"]) assert.ok(existe(rota), rota);
  assert.match(ler("lib/plataforma-api.ts"), /\/api\/plataforma/);
});

// ── autoridade ───────────────────────────────────────────────────────────────────────────────────────────────

test("/gestao é EXCLUSIVA do Administrador da Plataforma: o guard fica no layout e a decisão vem do backend, nunca de perfil tenant", () => {
  assert.match(ler("app/gestao/layout.tsx"), /<PlataformaGuard>/);
  const guard = semComentarios(ler("components/plataforma/PlataformaGuard.tsx"));
  assert.match(guard, /consultarAcessoPlataforma\(\)/);
  assert.match(guard, /if \(!ehAdministrador\) return cancelado \? undefined : setEstado\("negado"\)/); // gestor/operador/admin tenant: negado
  assert.match(guard, /<AcessoNegado/);
  assert.doesNotMatch(guard, /perfilBase|perfil\b|"gestor"|"admin"|"operador"|isSystemAccount|\.email\b/); // nada de perfil tenant decidindo
  // a entrada do menu também depende do backend e só existe fora da Gestão
  const menu = semComentarios(ler("components/layout/ProfileMenu.tsx"));
  assert.match(menu, /usePlataformaAcesso\(usuarioAtual\?\.id\)/);
  assert.match(menu, /administradorPlataforma && !emGestao && \(\s*<Link href="\/gestao"/);
  // a navegação operacional do tenant nunca lista a Gestão
  assert.doesNotMatch(ler("components/layout/TopNav.tsx"), /gestao|plataforma/i);
});

test("o Administrador da Plataforma NÃO vira membro implícito de tenant: sem empresa em contexto na Gestão", () => {
  // proxy: na Gestão só há o contexto `gestao` — nunca o header de slug
  const proxy = semComentarios(ler("proxy.ts"));
  assert.match(proxy, /if \(ehRotaDeGestao\(pathname\)\) headers\.set\(HEADER_CONTEXTO, CONTEXTO_GESTAO\)/);
  assert.equal(CONTEXTO_GESTAO, "gestao");
  // AppShell: Gestão sem sessão = mensagem única, sem empresa para devolver ao login; fora de /e/<slug> e /gestao nada é tenant
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const semEmpresa = slugUrl === null && !gestao;/);
  assert.match(shell, /\{gestao \? <GestaoTopBar \/> : <TopNav \/>\}/);
  assert.match(shell, /Acesso restrito\. Entre pelo endereço de acesso da sua empresa\./);
  // a Gestão não escolhe empresa: a barra não usa nada de tenant
  const barra = semComentarios(ler("components/layout/GestaoTopBar.tsx"));
  assert.doesNotMatch(barra, /useTenantPath|TopNav|useBranding|tenantSlug|sessaoSlug|loginHref/);
  // "empresa em foco" segue sendo só um rótulo (não cria sessão tenant)
  assert.match(ler("components/plataforma/PlataformaContext.tsx"), /NÃO muda a sessão/);
  assert.doesNotMatch(semComentarios(ler("components/plataforma/PlataformaShell.tsx")), /useBranding|aplicarBranding|useTenantPath/);
});

test("no menu do perfil, dentro da Gestão não há itens de tenant; voltar à empresa é um link EXPLÍCITO /e/<slug>/...", () => {
  const menu = semComentarios(ler("components/layout/ProfileMenu.tsx"));
  assert.match(menu, /const emGestao = ehRotaDeGestao\(usePathname\(\)\)/);
  assert.match(menu, /\{emGestao \? \(/);
  assert.match(menu, /tp\("meu-dia"\) !== "\/" && \(\s*<Link href=\{tp\("meu-dia"\)\}/);
  assert.match(menu, /Voltar à minha empresa/);
});

// ── identidade: Gestão = produto ─────────────────────────────────────────────────────────────────────────────

test("a Gestão usa a identidade do PRODUTO (TaskFlow): sem logo/nome de empresa, sem BOX, sem depender de slug", () => {
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.match(layout, /const contextoPlataforma = cabecalhos\.get\(HEADER_CONTEXTO\) === CONTEXTO_GESTAO;/);
  assert.match(layout, /contextoPlataforma\s*\? \{ branding: BRANDING_PADRAO, disponivel: true, nome: null \}/);
  // no cliente: entrar na Gestão por navegação troca a marca efetiva para a padrão (não herda o último tenant)
  const contexto = semComentarios(ler("lib/BrandingContext.tsx"));
  assert.match(contexto, /const emGestao = ehRotaDeGestao\(pathname\);/);
  assert.match(contexto, /const branding = emGestao \? BRANDING_PADRAO : brandingTenant;/);
  assert.match(semComentarios(ler("app/gestao/layout.tsx")), /title: "Gestão"/);
  for (const arquivo of fontes.filter((f) => f.startsWith("app/gestao/") || f.startsWith("components/plataforma/") || f === "components/layout/GestaoTopBar.tsx")) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /\bboxcom\b|\bBOX\b/i, arquivo);
  }
});

// ── slugs reservados ─────────────────────────────────────────────────────────────────────────────────────────

test("slugs reservados incluem as rotas globais: gestao, api, e, aprovacao, plataforma, login…", () => {
  for (const r of ["gestao", "api", "e", "aprovacao", "plataforma", "login", "logout", "admin", "suporte"]) {
    assert.ok((SLUG_RESERVADOS as readonly string[]).includes(r), r);
    assert.equal(normalizarSlug(r), null, r); // nunca vira empresa em /e/<slug>
  }
  assert.equal(normalizarSlug("boxcom"), "boxcom");
  assert.equal(slugDaRota("/e/gestao/login"), null);
  assert.equal(slugDaRota("/e/aprovacao/login"), null);
});
