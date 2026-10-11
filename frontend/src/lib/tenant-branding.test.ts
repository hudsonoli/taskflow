// Fase 10A — marca do tenant: a EMPRESA contratante é a identidade principal dentro de /e/<slug>/...; o produto TaskFlow é secundário.
// `npm run test:tenant-branding` (node --test, sem dependências). Duas empresas sintéticas (BOX e OUTRA) provam que nome/logo/título nunca vazam entre tenants.
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { BRANDING_PADRAO, normalizarBranding, srcDoLogo } from "./branding.ts";
import { criarCachePorChave, resolverComCache } from "./branding-cache.ts";
import { NOME_PRODUTO, tituloDaPagina } from "./produto.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
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

// Duas empresas SINTÉTICAS (o que o servidor devolveria em /publico/empresas/<slug>/branding)
const API = {
  boxcom: { corPrimaria: "#ff7a00", corSecundaria: "#0891b2", tema: "escuro", logoDisponivel: true, logoVersao: "a1b2c3d4e5f60718", padrao: false, disponivel: true, nomeExibicao: "BOX Comunicação" },
  outra: { corPrimaria: "#16a34a", corSecundaria: "#9333ea", tema: "claro", logoDisponivel: true, logoVersao: "99887766aabbccdd", padrao: false, disponivel: true, nomeExibicao: "OUTRA EMPRESA" },
  semlogo: { corPrimaria: "#2563eb", corSecundaria: "#7c3aed", tema: "claro", logoDisponivel: false, logoVersao: null, padrao: false, disponivel: true, nomeExibicao: "Sem Logo Ltda" },
} as const;
const marca = (slug: keyof typeof API) => ({ ...normalizarBranding(API[slug]), slug });

// ── título da aba ────────────────────────────────────────────────────────────────────────────────────────────

test("título: tenant = '<Empresa> | TaskFlow'; sem empresa (Gestão, telas neutras) = 'TaskFlow'; nunca um nome fixo", () => {
  assert.equal(NOME_PRODUTO, "TaskFlow");
  assert.equal(tituloDaPagina("BOX Comunicação"), "BOX Comunicação | TaskFlow");
  assert.equal(tituloDaPagina("OUTRA EMPRESA"), "OUTRA EMPRESA | TaskFlow");
  assert.equal(tituloDaPagina("  Empresa   com   espaços "), "Empresa com espaços | TaskFlow");
  for (const sem of [null, undefined, "", "   "]) assert.equal(tituloDaPagina(sem as string | null | undefined), "TaskFlow");
  assert.equal(tituloDaPagina("x".repeat(300)).length, 120 + " | TaskFlow".length);
  assert.doesNotMatch(semComentarios(ler("lib/produto.ts")), /BOX|boxcom/i);
});

test("layout: o título vem de generateMetadata (nome público da empresa do SLUG DA ROTA); Gestão e portal ficam neutros", () => {
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.match(layout, /export async function generateMetadata\(\): Promise<Metadata>/);
  assert.match(layout, /contexto === CONTEXTO_APROVACAO \|\| contexto === CONTEXTO_GESTAO \? null : normalizarSlug\(cabecalhos\.get\(HEADER_TENANT_SLUG\)\)/);
  assert.match(layout, /tituloDaPagina\(publico\?\.disponivel \? publico\.nome : null\)/);
  assert.match(layout, /template: `%s \| \$\{NOME_PRODUTO\}`/);
  assert.doesNotMatch(layout, /title: "Taskfloww"|title: "TaskFloww"|\bBOX\b|boxcom/);
  assert.match(semComentarios(ler("app/gestao/layout.tsx")), /title: "Gestão"/); // → "Gestão | TaskFlow"
  assert.match(semComentarios(ler("app/e/[slug]/aprovacao/page.tsx")), /title: "Aprovação"/); // → "Aprovação | TaskFlow"
});

// ── marca: nome e logo da PRÓPRIA empresa ────────────────────────────────────────────────────────────────────

test("o nome público acompanha a marca; empresas diferentes nunca compartilham nome nem logo", () => {
  const box = marca("boxcom");
  const outra = marca("outra");
  assert.equal(box.nome, "BOX Comunicação");
  assert.equal(outra.nome, "OUTRA EMPRESA");
  assert.notEqual(srcDoLogo(box), srcDoLogo(outra));
  assert.equal(srcDoLogo(box), "/api/branding/logo?slug=boxcom&v=a1b2c3d4e5f60718");
  assert.equal(srcDoLogo(outra), "/api/branding/logo?slug=outra&v=99887766aabbccdd");
  assert.ok(!srcDoLogo(outra)!.includes("boxcom") && !srcDoLogo(box)!.includes("outra"));
  assert.notEqual(box.corPrimaria, outra.corPrimaria);
});

test("sem logo configurado não se inventa logo: usa o nome da empresa; sem nome nem logo, o produto (padrão seguro)", () => {
  const semLogo = marca("semlogo");
  assert.equal(srcDoLogo(semLogo), null);
  assert.equal(semLogo.nome, "Sem Logo Ltda");
  assert.equal(BRANDING_PADRAO.nome, undefined);
  assert.equal(srcDoLogo(BRANDING_PADRAO), null);
  assert.equal(normalizarBranding({ ...API.boxcom, nomeExibicao: 42 }).nome, undefined); // valor inválido não vira nome
  assert.equal(normalizarBranding({ ...API.boxcom, nomeExibicao: "   " }).nome, undefined);
  assert.equal(normalizarBranding(null), BRANDING_PADRAO);
  assert.equal(normalizarBranding({ ...API.boxcom, nomeExibicao: "N".repeat(500) }).nome?.length, 120);
});

test("cache por tenant: BOX → OUTRA → BOX devolve sempre nome E logo da própria empresa (sem vazamento)", async () => {
  const cache = criarCachePorChave<ReturnType<typeof marca>>(100);
  const buscas: string[] = [];
  const obter = (slug: keyof typeof API) =>
    resolverComCache(cache, `slug:${slug}`, () => 1_000, async () => {
      buscas.push(slug);
      return { valor: marca(slug), ttlMs: 30_000 };
    });
  for (const slug of ["boxcom", "outra", "boxcom", "outra", "semlogo", "boxcom"] as const) {
    const m = await obter(slug);
    assert.equal(m.nome, API[slug].nomeExibicao, slug);
    assert.equal(m.slug, slug);
  }
  assert.deepEqual(buscas, ["boxcom", "outra", "semlogo"]);
});

// ── onde a marca aparece ─────────────────────────────────────────────────────────────────────────────────────

test("o layout monta a marca do tenant SÓ a partir do slug da rota e carrega o nome público junto", () => {
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.match(layout, /const branding = slug && publico\.disponivel \? \{ \.\.\.publico\.branding, nome: publico\.nome \} : publico\.branding;/);
  assert.match(layout, /slugVisual\(\{ slugDaRota: slugRota \}\)/);
  assert.doesNotMatch(layout, /EMPRESA_CODIGO|legado|COOKIE_TENANT_SLUG/);
  assert.match(semComentarios(ler("lib/server/branding.ts")), /\{ \.\.\.normalizarBranding\(dados\), slug: alvo\.slug \}/);
});

test("cabeçalho/menu do tenant: logo da empresa; sem logo, o NOME da empresa (TaskFlow só fora de um ambiente de empresa)", () => {
  const logo = semComentarios(ler("components/branding/BrandLogo.tsx"));
  assert.match(logo, /\{branding\.nome \?\? NOME_PRODUTO\}/);
  assert.match(logo, /alt=\{branding\.nome \? `Logo de \$\{branding\.nome\}` : "Logo da empresa"\}/);
  assert.doesNotMatch(logo, /BOX|boxcom/i);
  assert.match(semComentarios(ler("components/layout/TopNav.tsx")), /<BrandLogo variant="header" \/>/);
  assert.match(semComentarios(ler("components/layout/GestaoTopBar.tsx")), /<BrandLogo variant="header" \/>/); // na Gestão a marca efetiva é a do produto
});

test("login tenant: empresa é a identidade PRINCIPAL (logo + nome do slug), TaskFlow é secundário; sem empresa padrão", () => {
  const login = semComentarios(ler("components/auth/LoginView.tsx"));
  assert.match(login, /<BrandLogo variant="auth" className="mb-3" \/>/);
  assert.match(login, /\{nomeEmpresa \?\? `Entrar no \$\{NOME_PRODUTO\}`\}/);
  assert.match(login, /\{nomeEmpresa && <p[^>]*>Entrar no \{NOME_PRODUTO\}<\/p>\}/);
  assert.doesNotMatch(login, /EMPRESA_CODIGO|BOX|boxcom/i);
  const pagina = semComentarios(ler("app/e/[slug]/login/page.tsx"));
  assert.match(pagina, /nomeEmpresa=\{empresa\.nome\}/);
  assert.match(pagina, /slug=\{empresa\.slug\}/);
  const indisponivel = semComentarios(ler("components/auth/EmpresaIndisponivelView.tsx"));
  assert.match(indisponivel, /<BrandLogo variant="auth" \/>/); // slug inexistente: identidade neutra do produto
  assert.doesNotMatch(indisponivel, /BOX|boxcom/i);
});

test("portal externo: a empresa do TOKEN é a marca principal (logo/nome do servidor); o produto não a substitui", () => {
  const tela = semComentarios(ler("components/aprovacao/AprovacaoPublicaView.tsx"));
  assert.match(tela, /aplicarBrandingRef\.current\(normalizarBranding\(dados\.empresa\)\)/);
  assert.match(tela, /<BrandLogo variant="auth" srcOverride=\{logo\} \/>/);
  assert.doesNotMatch(tela, /BOX|boxcom/i);
  // o nome público da empresa do token chega à marca (nomeExibicao) — o portal não decide empresa pelo slug/cookie
  assert.equal(normalizarBranding({ ...API.outra }).nome, "OUTRA EMPRESA");
});

test("sessão de OUTRA empresa: a tela de incompatibilidade não rebrandeia nem nomeia empresa", () => {
  const tela = semComentarios(ler("components/layout/SessaoOutraEmpresaView.tsx"));
  assert.doesNotMatch(tela, /useBranding|aplicarBranding|BrandLogo|nomeEmpresa|branding/);
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const sessaoDeOutraEmpresa = slugUrl !== null && autenticado && sessaoSlug !== null && sessaoSlug !== slugUrl;/);
});

test("o nome da marca só vem do servidor: nenhum nome/slug de empresa fixo no código de produção", () => {
  for (const arquivo of fontes) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /["'`](?:BOX Comunicação|OUTRA EMPRESA)["'`]/, arquivo);
    assert.doesNotMatch(semComentarios(ler(arquivo)), /["'`]boxcom["'`]/i, arquivo);
  }
});
