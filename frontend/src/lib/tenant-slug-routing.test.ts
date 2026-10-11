// Fase 9D — URL canônica multiempresa por slug. `npm run test:tenant-slug-routing` (node --test, sem dependências).
// Regra: toda interface de empresa vive em `/e/<slug>/...`. O domínio nu e as rotas de tenant SEM `/e/<slug>` não resolvem empresa nenhuma (404
// neutro, sem redirecionar para BOX, sem seletor de empresas). Lógica pura (tenant.ts) é exercitada de verdade; telas/rotas (alias `@/`, que o
// node --test não resolve) são lidas como texto para provar as garantias que tipos não mostram.
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";
import { linkDeAprovacao } from "./aprovacao-externa.ts";
import {
  caminhoDoTenant,
  caminhoSemTenant,
  ehRotaDaPlataforma,
  ehRotaDeAprovacaoExterna,
  ehRotaDeLogin,
  ehRotaDeRecuperacaoDeSenha,
  ehRotaDeTrocaDeSenhaInicial,
  hrefLogin,
  rotaDoTenant,
  slugDaRota,
  usaTemaDaEmpresa,
} from "./tenant.ts";

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
const relativo = (absoluto: string) => absoluto.replace(/\\/g, "/").split("/src/")[1];
const fontes = arquivos(SRC).map(relativo);

// Módulos de empresa que SÓ podem existir sob `/e/[slug]/`.
const PAGINAS_TENANT = [
  "arquivos", "configuracoes", "meu-departamento", "meu-dia", "minha-conta", "minhas-demandas", "notificacoes", "pauta", "projetos", "relatorios",
  "tarefas", "trafego", "trocar-senha-inicial", "aprovacao",
];

// ── domínio nu e rotas legadas: nenhuma empresa implícita ────────────────────────────────────────────────────

test("/ (domínio nu) não abre BOX nem empresa nenhuma: não há app/page.tsx nem redirect para uma home de tenant", () => {
  assert.equal(existe("app/page.tsx"), false);
  assert.equal(rotaDoTenant("/"), null);
  assert.equal(slugDaRota("/"), null);
  assert.equal(caminhoDoTenant(null, "meu-dia"), "/"); // sem slug o destino é o 404 neutro, nunca uma empresa
});

test("/login (e recuperação de senha) sem slug não existem: não resolvem tenant", () => {
  for (const legado of ["login", "esqueci-senha", "redefinir-senha"]) assert.equal(existe(`app/${legado}/page.tsx`), false, legado);
  for (const p of ["/login", "/esqueci-senha", "/redefinir-senha"]) {
    assert.equal(ehRotaDeLogin(p), false, p);
    assert.equal(ehRotaDeRecuperacaoDeSenha(p), false, p);
    assert.equal(rotaDoTenant(p), null, p);
  }
});

test("/tarefas e todas as rotas de tenant SEM /e/<slug> não existem (404 neutro)", () => {
  for (const modulo of PAGINAS_TENANT) {
    assert.equal(existe(`app/${modulo}/page.tsx`), false, `app/${modulo}/page.tsx não pode existir fora de /e/[slug]`);
    assert.equal(existe(`app/e/[slug]/${modulo}/page.tsx`), true, `app/e/[slug]/${modulo}/page.tsx`);
    assert.equal(rotaDoTenant(`/${modulo}`), null, modulo);
  }
  assert.equal(existe("app/e/[slug]/configuracoes/layout.tsx"), true); // o guard administrativo veio junto
  assert.equal(existe("app/configuracoes/layout.tsx"), false);
});

test("só app/api, app/e e app/plataforma têm páginas/rotas: nenhuma outra pasta serve tenant", () => {
  const raiz = new URL("app/", SRC);
  const pastas = readdirSync(raiz).filter((n) => statSync(new URL(n, raiz)).isDirectory()).sort();
  assert.deepEqual(pastas, ["api", "e", "plataforma"]);
});

test("o AppShell NÃO escolhe empresa fora de /e/<slug>: renderiza a página (404) como está, sem redirecionar nem exigir sessão", () => {
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const semEmpresa = slugUrl === null && !plataforma;/);
  assert.match(shell, /if \(semEmpresa\) return <>\{children\}<\/>;/);
  assert.match(shell, /if \(semEmpresa \|\| sessaoCarregando/); // o efeito de redirecionamento nem roda sem empresa
  assert.doesNotMatch(shell, /"\/login"|"\/meu-dia"|"\/trocar-senha-inicial"|loginHref/);
});

// ── /e/<slug>/... funciona ─────────────────────────────────────────────────────────────────────────────────────

test("/e/boxcom/login resolve a empresa pelo slug da URL; /e/boxcom/tarefas exige sessão da própria empresa", () => {
  assert.deepEqual(rotaDoTenant("/e/boxcom/login"), { slug: "boxcom", pagina: "login" });
  assert.equal(ehRotaDeLogin("/e/boxcom/login"), true);
  assert.equal(ehRotaDeLogin("/e/boxcom/tarefas"), false);
  assert.deepEqual(rotaDoTenant("/e/boxcom/tarefas"), { slug: "boxcom", pagina: "tarefas" });
  const pagina = ler("app/e/[slug]/login/page.tsx");
  assert.match(pagina, /empresaDisponivelDaRota\(\(await params\)\.slug\)/);
  assert.match(pagina, /<LoginView[^>]*slug=\{empresa\.slug\}/);
  // /e/<slug>/tarefas NÃO é pública: o AppShell só libera login, recuperação e portal
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const exigeSessao = !rotaLogin && !rotaRecuperacaoSenha && !rotaPortalExterno;/);
  assert.match(shell, /if \(!autenticado && exigeSessao\) \{[\s\S]*?router\.replace\(hrefLogin\(slugUrl\)\)/);
});

test("catálogo público mínimo: login, esqueci/redefinir senha e portal; nenhum outro /e/<slug>/... é público", () => {
  for (const publica of ["/e/boxcom/login", "/e/boxcom/esqueci-senha", "/e/boxcom/redefinir-senha", "/e/boxcom/aprovacao"]) {
    assert.ok(
      ehRotaDeLogin(publica) || ehRotaDeRecuperacaoDeSenha(publica) || ehRotaDeAprovacaoExterna(publica),
      publica,
    );
  }
  for (const privada of ["/e/boxcom", "/e/boxcom/tarefas", "/e/boxcom/meu-dia", "/e/boxcom/configuracoes/usuarios", "/e/boxcom/arquivos", "/e/boxcom/aprovacao/x", "/e/boxcom/loginx"]) {
    assert.ok(!ehRotaDeLogin(privada) && !ehRotaDeRecuperacaoDeSenha(privada) && !ehRotaDeAprovacaoExterna(privada), privada);
  }
  assert.ok(ehRotaDeTrocaDeSenhaInicial("/e/boxcom/trocar-senha-inicial") && !ehRotaDeTrocaDeSenhaInicial("/trocar-senha-inicial"));
  assert.ok(usaTemaDaEmpresa("/e/boxcom/trocar-senha-inicial") && !usaTemaDaEmpresa("/e/boxcom/tarefas"));
});

// ── navegação preserva o slug ──────────────────────────────────────────────────────────────────────────────────

test("caminhoDoTenant/caminhoSemTenant: preservam o slug e nunca produzem caminho sem /e/<slug> para uma empresa", () => {
  assert.equal(caminhoDoTenant("boxcom", "tarefas"), "/e/boxcom/tarefas");
  assert.equal(caminhoDoTenant("boxcom", "/tarefas"), "/e/boxcom/tarefas");
  assert.equal(caminhoDoTenant("BoxCom", "/configuracoes/usuarios"), "/e/boxcom/configuracoes/usuarios");
  assert.equal(caminhoDoTenant("boxcom", ""), "/e/boxcom");
  assert.equal(hrefLogin("boxcom"), "/e/boxcom/login");
  for (const ruim of [null, undefined, "", "a", "plataforma", "login", "../x", "com espaço"]) {
    assert.equal(caminhoDoTenant(ruim as string | null | undefined, "tarefas"), "/", String(ruim));
  }
  assert.equal(caminhoSemTenant("/e/boxcom/tarefas"), "/tarefas");
  assert.equal(caminhoSemTenant("/e/boxcom/configuracoes/usuarios"), "/configuracoes/usuarios");
  assert.equal(caminhoSemTenant("/e/boxcom"), "/");
  assert.equal(caminhoSemTenant("/tarefas"), null);
});

test("nenhum componente navega para rota de tenant sem slug (router.push/replace, <Link>, redirect, window.location)", () => {
  const permitidas = /^\/(plataforma|api)(\/|$|#)/;
  const achados: string[] = [];
  for (const arquivo of fontes) {
    if (arquivo.startsWith("app/api/")) continue;
    const texto = semComentarios(ler(arquivo));
    const padroes = [
      /router\.(?:push|replace|prefetch)\(\s*["'`](\/[^"'`]*)["'`]/g,
      /<Link[^>]*\bhref=["'](\/[^"']*)["']/g,
      /\bhref=\{?["'`](\/[^"'`]*)["'`]\}?/g,
      /\bredirect\(\s*["'`](\/[^"'`]*)["'`]/g,
      /window\.location\.(?:href|assign|replace)\s*=?\s*\(?["'`](\/[^"'`]*)["'`]/g,
    ];
    for (const padrao of padroes) {
      for (const m of texto.matchAll(padrao)) if (!permitidas.test(m[1])) achados.push(`${arquivo}: ${m[1]}`);
    }
  }
  assert.deepEqual([...new Set(achados)].sort(), []);
});

test("os itens de menu (TopNav, Configurações) usam caminhos relativos do módulo e SEMPRE passam por tp() = /e/<slug>/...", () => {
  const topnav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.match(topnav, /useTenantPath\(\)/);
  assert.equal((topnav.match(/href=\{tp\(item\.href\)\}/g) ?? []).length, 2); // desktop + mobile
  assert.match(topnav, /isItemActive\(pathname, tp\(item\.href\)\)/);
  assert.match(topnav, /<Link href=\{tp\("meu-dia"\)\}/); // o logo leva à home DA empresa, não a "/"
  const config = semComentarios(ler("components/configuracoes/ConfiguracoesSidebarNav.tsx"));
  assert.match(config, /href=\{tp\(item\.href\)\}/);
  assert.match(config, /pathname === tp\(item\.href\)/);
});

test("Header/perfil, sino de notificações, listas e Pauta/Arquivos/Minhas Demandas preservam o slug", () => {
  const perfil = semComentarios(ler("components/layout/ProfileMenu.tsx"));
  assert.match(perfil, /href=\{tp\("minha-conta"\)\}/);
  assert.match(perfil, /href=\{tp\("notificacoes"\)\}/);
  assert.match(perfil, /`\$\{tp\("minha-conta"\)\}#seguranca`/);
  const sino = semComentarios(ler("components/layout/NotificationBell.tsx"));
  assert.match(sino, /router\.push\(tp\("tarefas"\)\)/);
  assert.match(sino, /href=\{tp\("notificacoes"\)\}/);
  for (const [arquivo, quantidade] of [
    ["components/notificacoes/NotificacoesView.tsx", 1],
    ["components/pauta/PautaView.tsx", 1],
    ["components/minhas-demandas/MinhasDemandasView.tsx", 1],
    ["components/arquivos/ArquivoPreviewModal.tsx", 1],
  ] as const) {
    const texto = semComentarios(ler(arquivo));
    assert.equal((texto.match(/router\.push\(tp\("tarefas"\)\)/g) ?? []).length, quantidade, arquivo);
  }
});

test("a tela inicial pós-login e a troca de senha inicial usam o slug (LoginView e AppShell)", () => {
  const login = semComentarios(ler("components/auth/LoginView.tsx"));
  assert.equal((login.match(/router\.replace\(caminhoDoTenant\(slug, mustChangePassword \? "trocar-senha-inicial" : "meu-dia"\)\)/g) ?? []).length, 2); // senha + Google
  assert.match(semComentarios(ler("components/auth/TrocarSenhaInicialView.tsx")), /router\.replace\(tp\("meu-dia"\)\)/);
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /caminhoDoTenant\(slugUrl, "trocar-senha-inicial"\)/);
  assert.match(shell, /caminhoDoTenant\(slugUrl, "meu-dia"\)/);
});

test("a página lembra o slug no refresh: o contexto vem do PATHNAME (slugDaRota), nunca de cookie, storage ou empresa padrão", () => {
  const contexto = semComentarios(ler("lib/BrandingContext.tsx"));
  assert.match(contexto, /const tenantSlug = slugDaRota\(pathname\) \?\? sessaoSlug \?\? tenantSlugInicial;/);
  assert.match(contexto, /const loginHref = hrefLogin\(tenantSlug\);/);
  for (const arquivo of fontes) {
    const texto = semComentarios(ler(arquivo));
    assert.doesNotMatch(texto, /localStorage\.[a-z]+\([^)]*(slug|tenant|empresa)/i, arquivo);
  }
});

// ── logout, sessão × slug, notificações ───────────────────────────────────────────────────────────────────────

test("logout vai para /e/<slug>/login da empresa da URL/sessão — nunca para um login fixo (BOX)", () => {
  const perfil = semComentarios(ler("components/layout/ProfileMenu.tsx"));
  assert.match(perfil, /const destino = loginHref/);
  assert.match(perfil, /router\.replace\(destino\)/);
  assert.equal(hrefLogin("boxcom"), "/e/boxcom/login");
  assert.equal(hrefLogin("outra"), "/e/outra/login");
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /router\.replace\(slugUrl \? hrefLogin\(slugUrl\) : "\/"\)/);
});

test("nenhum slug de empresa fixo no código (nem 'boxcom'): a empresa só vem da URL, do servidor (criação do link) ou da sessão", () => {
  for (const arquivo of fontes) assert.doesNotMatch(semComentarios(ler(arquivo)), /["'`]boxcom["'`]|\/e\/boxcom/i, arquivo);
});

test("sessão × slug divergentes: nada da URL é carregado, a URL NUNCA troca a empresa da sessão e há saída segura", () => {
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const sessaoDeOutraEmpresa = slugUrl !== null && autenticado && sessaoSlug !== null && sessaoSlug !== slugUrl;/);
  assert.match(shell, /if \(sessaoDeOutraEmpresa && sessaoSlug && exigeSessao\) \{\s*return <SessaoOutraEmpresaView/);
  assert.match(shell, /sessaoDeOutraEmpresa\) return;/); // nenhum redirecionamento automático nesse estado
  const tela = semComentarios(ler("components/layout/SessaoOutraEmpresaView.tsx"));
  assert.match(tela, /caminhoDoTenant\(slugDaSessao, "meu-dia"\)/); // volta à PRÓPRIA empresa
  assert.doesNotMatch(tela, /slugDaUrl|slugUrl|nomeEmpresa|branding/); // não nomeia nenhuma das duas empresas
  // a empresa dos dados nunca vem da URL: o BFF de dados só autoriza pelo token da sessão
  const dados = ler("app/api/backend/[...path]/route.ts");
  assert.match(dados, /SESSION_COOKIE_NAME/);
  assert.doesNotMatch(semComentarios(dados), /slug|x-tf-/);
});

test("slug inválido/inexistente/inativo: uma mensagem neutra, sem cair em outra empresa nem sugerir login padrão", () => {
  const vista = semComentarios(ler("components/auth/EmpresaIndisponivelView.tsx"));
  assert.match(vista, /Empresa não encontrada ou indisponível/);
  assert.doesNotMatch(vista, /href=|Link|\/login|boxcom/i);
  assert.match(semComentarios(ler("app/e/[slug]/page.tsx")), /if \(!slug\) notFound\(\)/);
  const tenant = semComentarios(ler("lib/server/tenant-pagina.ts"));
  assert.match(tenant, /if \(!slug\) return null;/);
  assert.match(tenant, /publico\.disponivel \? \{ slug, nome: publico\.nome \} : null/);
});

test("nenhum fallback por EMPRESA_CODIGO/cookie/empresa padrão: layout, branding, logo e BFFs exigem o slug", () => {
  for (const arquivo of fontes) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /EMPRESA_CODIGO/, arquivo);
  }
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.doesNotMatch(layout, /legado|slugCookie|COOKIE_TENANT_SLUG/);
  assert.match(layout, /: \{ branding: BRANDING_PADRAO, disponivel: false, nome: null \}/); // sem slug → identidade neutra do TaskFloww
  assert.doesNotMatch(semComentarios(ler("lib/server/branding.ts")), /legado/);
});

// ── plataforma e portal ────────────────────────────────────────────────────────────────────────────────────────

test("a plataforma continua em /plataforma, fora dos tenants; sem sessão não há empresa para devolver ao login", () => {
  assert.equal(ehRotaDaPlataforma("/plataforma"), true);
  assert.equal(ehRotaDaPlataforma("/plataforma/empresas/abc"), true);
  assert.equal(rotaDoTenant("/plataforma/empresas"), null);
  assert.equal(slugDaRota("/e/plataforma/login"), null); // 'plataforma' é slug reservado
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /Acesso restrito\. Entre pelo endereço de acesso da sua empresa\./);
  assert.match(shell, /if \(slugUrl\) router\.replace\(hrefLogin\(slugUrl\)\);/);
});

test("Portal 9B/9D: o link gerado é /e/<slug>/aprovacao#token=… (slug do servidor), nunca ?token= nem /aprovacao sem slug", () => {
  const token = "A".repeat(43);
  const link = linkDeAprovacao("https://app.exemplo.com", "boxcom", token);
  assert.equal(link, `https://app.exemplo.com/e/boxcom/aprovacao#token=${token}`);
  assert.doesNotMatch(link, /\?token=|\.com\/aprovacao/);
  const bloco = semComentarios(ler("components/demandas/AprovacaoExternaBloco.tsx"));
  assert.match(bloco, /linkDeAprovacao\(window\.location\.origin, resultado\.criada\.empresaSlug, resultado\.criada\.token\)/);
});

test("senha: redefinir-senha segue por slug (/e/<slug>/redefinir-senha#token=) e os BFFs não têm rota sem slug", () => {
  assert.equal(existe("app/e/[slug]/redefinir-senha/page.tsx"), true);
  assert.equal(existe("app/e/[slug]/esqueci-senha/page.tsx"), true);
  assert.equal(existe("app/redefinir-senha/page.tsx"), false);
  assert.match(semComentarios(ler("components/auth/RedefinirSenhaView.tsx")), /confirmarRedefinicaoSenha\(token, novaSenha, confirmacao, slug\)/);
});

test("Google: o callback usa o slug da URL de login (nenhum retorno fixo) e o BFF exige o slug", () => {
  const login = semComentarios(ler("components/auth/LoginView.tsx"));
  assert.match(login, /loginGoogle\(email, idToken, slug\)/);
  const google = semComentarios(ler("app/api/auth/google/route.ts"));
  assert.match(google, /normalizarSlug\(body\?\.empresaSlug\)/);
  assert.match(google, /if \(!slug\) \{/);
});
