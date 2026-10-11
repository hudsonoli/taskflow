// Fase 1B — Administração da Plataforma na UI. `npm run test:plataforma` (node --test, sem dependências).
// Lógica pura em `plataforma.ts`; as telas/rotas BFF são lidas como texto (são .tsx/.ts com alias `@/`, que o
// node --test não resolve) para provar as garantias de segurança que não aparecem em tipos: o menu depende do backend,
// o cookie da plataforma é isolado, a senha temporária nunca é persistida e o painel não tem suporte/impersonação.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { erroDoCodigoInterno, erroDoSlug, mensagemDeErroDaApi, separarGestores, sugerirSlug, SLUG_RESERVADOS } from "./plataforma.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");

// Só o código executável: comentários explicam o que NÃO se faz (citam e-mail, perfil...) e não contam como uso.
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

// ── slug / código: espelho amigável das regras do backend ────────────────────────────────────────────
test("slug válido: 3–40, minúsculas, números e hífen, sem hífen nas pontas", () => {
  for (const ok of ["demo", "acme", "acme-ltda", "a1b", "x".repeat(40), "loja-2"]) assert.equal(erroDoSlug(ok), null, ok);
  for (const ruim of ["", "ab", "x".repeat(41), "-acme", "acme-", "com espaço", "com_underscore", "acentuação"]) {
    assert.notEqual(erroDoSlug(ruim), null, ruim);
  }
});

test("slug: a lista de reservados bate com a do backend", () => {
  assert.deepEqual([...SLUG_RESERVADOS].sort(), ["admin", "api", "aprovacao", "e", "gestao", "login", "logout", "plataforma", "suporte"]);
  for (const reservado of SLUG_RESERVADOS) {
    // "e" já cai antes, no tamanho mínimo; os demais são recusados como reservados
    assert.match(erroDoSlug(reservado) ?? "", reservado.length < 3 ? /entre 3 e 40/ : /reservado/);
  }
});

test("sugerirSlug tira acentos e símbolos e respeita o limite", () => {
  assert.equal(sugerirSlug("Ação Única Ltda."), "acao-unica-ltda");
  assert.equal(sugerirSlug("  ACME__Corp "), "acme-corp");
  assert.equal(sugerirSlug("x".repeat(60)).length, 40);
  assert.equal(sugerirSlug("---"), "");
});

test("código interno aceita só letras, números, hífen e sublinhado", () => {
  assert.equal(erroDoCodigoInterno("ACME-01_b"), null);
  assert.notEqual(erroDoCodigoInterno(""), null);
  assert.notEqual(erroDoCodigoInterno("com espaço"), null);
  assert.notEqual(erroDoCodigoInterno("a/b"), null);
});

test("mensagemDeErroDaApi lê detail string, lista de validação e message do BFF", () => {
  assert.equal(mensagemDeErroDaApi({ detail: "slug já cadastrado" }, "x"), "slug já cadastrado");
  assert.equal(mensagemDeErroDaApi({ detail: [{ msg: "Value error, O slug é reservado." }] }, "x"), "O slug é reservado.");
  assert.equal(mensagemDeErroDaApi({ message: "Acesso negado" }, "x"), "Acesso negado");
  assert.equal(mensagemDeErroDaApi({ detail: { message: "outra" } }, "x"), "outra");
  assert.equal(mensagemDeErroDaApi(null, "padrão"), "padrão");
});

// ── menu: depende do backend, nunca de e-mail / perfil / conta de sistema ────────────────────────────
test("entrada do menu vem de GET /plataforma/acesso e não de e-mail, perfil ou conta de sistema", () => {
  const hook = ler("lib/usePlataformaAcesso.ts");
  const menu = ler("components/layout/ProfileMenu.tsx");
  assert.match(hook, /consultarAcessoPlataforma/);
  assert.match(menu, /usePlataformaAcesso\(usuarioAtual\?\.id\)/);
  assert.match(menu, /administradorPlataforma && !emGestao && \(/);
  const rota = ler("app/api/plataforma/acesso/route.ts");
  assert.match(rota, /\/plataforma\/acesso/);
  for (const arquivo of [hook, rota, ler("components/plataforma/PlataformaGuard.tsx")].map(semComentarios)) {
    assert.doesNotMatch(arquivo, /perfilBase|perfil_base|isSystemAccount|is_system_account|contaSistema|\.email\b/);
  }
  assert.doesNotMatch(ler("components/layout/TopNav.tsx"), /plataforma/i); // a entrada vive no menu do perfil, não na navegação operacional
});

test("o guard de /gestao fica no layout e só abre a sessão depois de o backend confirmar a autoridade", () => {
  assert.match(ler("app/gestao/layout.tsx"), /<PlataformaGuard>/);
  const guard = ler("components/plataforma/PlataformaGuard.tsx");
  assert.ok(guard.indexOf("consultarAcessoPlataforma()") < guard.indexOf("abrirSessaoPlataforma()"));
  assert.match(guard, /negado/);
});

// ── BFF: cookie separado, sem misturar tokens ────────────────────────────────────────────────────────
test("cookie tf_platform: HttpOnly, SameSite estrito, escopo de caminho próprio e diferente de tf_session", () => {
  const backend = ler("lib/server/backend.ts");
  assert.match(backend, /PLATFORM_COOKIE_NAME = "tf_platform"/);
  assert.match(backend, /SESSION_COOKIE_NAME = "tf_session"/);
  assert.match(backend, /PLATFORM_COOKIE_PATH = "\/api\/plataforma"/);
  const opcoes = backend.slice(backend.indexOf("export function platformCookieOptions"));
  assert.match(opcoes, /httpOnly: true/);
  assert.match(opcoes, /secure: process\.env\.NODE_ENV === "production"/);
  assert.match(opcoes, /sameSite: "strict"/);
  assert.match(opcoes, /path: PLATFORM_COOKIE_PATH/);
});

test("o proxy da plataforma usa só tf_platform; o proxy tenant nunca alcança /plataforma com tf_session", () => {
  const proxyPlataforma = ler("app/api/plataforma/[...path]/route.ts");
  assert.match(proxyPlataforma, /PLATFORM_COOKIE_NAME/);
  assert.doesNotMatch(proxyPlataforma, /SESSION_COOKIE_NAME/);
  assert.match(proxyPlataforma, /\/plataforma\//);
  // 401/403 derrubam o cookie da plataforma (autoridade revogada ou token vencido)
  assert.match(proxyPlataforma, /resposta\.status === 401 \|\| resposta\.status === 403/);
  const sessao = ler("app/api/plataforma/sessao/route.ts");
  assert.match(sessao, /SESSION_COOKIE_NAME/); // a sessão de plataforma nasce da sessão tenant
  assert.doesNotMatch(sessao, /NextResponse\.json\(\{[^}]*accessToken/); // o token nunca volta no corpo
});

test("sair do sistema também encerra a sessão de plataforma", () => {
  const logout = ler("app/api/auth/logout/route.ts");
  assert.match(logout, /PLATFORM_COOKIE_NAME/);
  assert.match(logout, /PLATFORM_COOKIE_PATH/);
});

// ── senha temporária: exibida uma vez, nunca persistida ──────────────────────────────────────────────
test("a senha temporária não é gravada em storage, URL, console ou rota", () => {
  const modal = ler("components/plataforma/DefinirGestorModal.tsx");
  const api = ler("lib/plataforma-api.ts");
  for (const arquivo of [modal, api, ler("components/plataforma/EmpresaUsuariosSection.tsx")]) {
    assert.doesNotMatch(arquivo, /localStorage|sessionStorage|indexedDB|document\.cookie|console\.(log|info|debug|warn|error)/);
  }
  assert.doesNotMatch(modal, /router\.(push|replace)|location\./);
  // fechar descarta o resultado (a senha) e o formulário
  const fechar = modal.slice(modal.indexOf("function fechar()"), modal.indexOf("async function enviar"));
  assert.match(fechar, /setCriado\(null\)/);
  assert.match(modal, /uma única vez/);
});

test("criar Gestor não oferece escolha de perfil nem de senha", () => {
  const modal = ler("components/plataforma/DefinirGestorModal.tsx");
  assert.doesNotMatch(modal, /<Select|type="password"|perfilBase/);
  const tipos = ler("types/plataforma.ts");
  assert.match(tipos, /PlataformaGestorCreate = \{ nome: string; email: string \}/);
});

// ── escopo: sem suporte/impersonação, sem exclusão de empresa, sem dado interno ──────────────────────
test("suporte é só um marcador 'Em breve' (sem rota, sem cookie de suporte, sem impersonação)", () => {
  const shell = ler("components/plataforma/PlataformaShell.tsx");
  assert.match(shell, /Em breve/);
  assert.match(shell, /aria-disabled="true"/);
  const tudo = [
    shell,
    ler("lib/plataforma-api.ts"),
    ler("app/api/plataforma/[...path]/route.ts"),
    ler("app/api/plataforma/sessao/route.ts"),
    ler("lib/server/backend.ts"),
  ].join("\n");
  assert.doesNotMatch(tudo, /tf_support|sessaoSuporte|iniciarImpersonacao|\/suporte\//i);
});

test("a API de empresas da plataforma não tem exclusão de empresa", () => {
  const api = ler("lib/plataforma-api.ts");
  const delecoes = [...api.matchAll(/method: "DELETE"/g)].length;
  assert.equal(delecoes, 3); // restaurar branding, remover logo e encerrar a sessão de plataforma — nunca a empresa
  assert.doesNotMatch(api, /method: "DELETE"[^)]*\/empresas\/\$\{encodeURIComponent\(id\)\}`/);
  assert.doesNotMatch(api, /excluirEmpresa|deletarEmpresa|removerEmpresa/);
});

test("a lista de usuários mostra só metadados (sem hash, senha ou token)", () => {
  const tipos = ler("types/plataforma.ts");
  const bloco = tipos.slice(tipos.indexOf("export type PlataformaUsuario"), tipos.indexOf("export type PlataformaGestorCreate"));
  assert.doesNotMatch(bloco, /senha|hash|token|credencial|isSystemAccount/i);
});

test("salvar a personalização de outra empresa não altera o branding de quem edita", () => {
  const secao = ler("components/plataforma/EmpresaPersonalizacaoSection.tsx");
  assert.doesNotMatch(secao, /useBranding|aplicarBranding/);
  assert.match(secao, /urlLogoEmpresa\(empresa\.id/);
  assert.match(secao, /logoAtualSrc=\{logoSalvoSrc\}/); // nunca cai no logo da própria empresa
});

test("rotas e componentes obrigatórios do módulo existem", () => {
  for (const caminho of [
    "app/gestao/page.tsx",
    "app/gestao/empresas/page.tsx",
    "app/gestao/empresas/[id]/page.tsx",
    "components/plataforma/PlataformaShell.tsx",
    "components/plataforma/EmpresasPlataformaView.tsx",
    "components/plataforma/EmpresaPlataformaView.tsx",
  ]) {
    assert.ok(ler(caminho).length > 0, caminho);
  }
  // page.tsx não carrega regra de negócio: só renderiza a View
  assert.match(ler("app/gestao/empresas/page.tsx"), /<EmpresasPlataformaView \/>/);
  assert.match(ler("components/plataforma/EmpresaPlataformaView.tsx"), /Dados[\s\S]*Personalização[\s\S]*Usuários/);
  assert.match(ler("components/plataforma/PlataformaShell.tsx"), /Empresa em foco/);
});

// ── Gestores da empresa: o Gestor é o próprio usuário com perfil Gestor (sem cadastro paralelo) ──────────
const u = (nome: string, perfilBase: string) => ({ id: nome, nome, perfilBase });

test("separarGestores: zero, um e vários Gestores; Usuário e Admin legado nunca contam como Gestor", () => {
  const zero = separarGestores([u("Ana", "operador"), u("Beto", "admin")]);
  assert.equal(zero.gestores.length, 0);
  assert.equal(zero.demais.length, 2);

  const um = separarGestores([u("Ana", "operador"), u("Carla", "gestor")]);
  assert.deepEqual(um.gestores.map((g) => g.nome), ["Carla"]);
  assert.deepEqual(um.demais.map((g) => g.nome), ["Ana"]);

  const varios = separarGestores([u("Zeca", "gestor"), u("Ana", "operador"), u("Bia", "gestor"), u("Ciro", "gestor"), u("Beto", "admin")]);
  assert.deepEqual(varios.gestores.map((g) => g.nome), ["Bia", "Ciro", "Zeca"]); // todos, ordem estável por nome
  assert.deepEqual(varios.demais.map((g) => g.nome), ["Ana", "Beto"]);
  // adicionar mais um Gestor não remove nem altera os existentes
  const mais = separarGestores([...[u("Zeca", "gestor"), u("Bia", "gestor"), u("Ciro", "gestor")], u("Dora", "gestor")]);
  assert.deepEqual(mais.gestores.map((g) => g.nome), ["Bia", "Ciro", "Dora", "Zeca"]);
  assert.deepEqual(separarGestores([]), { gestores: [], demais: [] });
});

test("aba Usuários: bloco 'Gestores da empresa · N' com os próprios usuários, ação conforme a quantidade e recarga imediata", () => {
  const secao = ler("components/plataforma/EmpresaUsuariosSection.tsx");
  assert.match(secao, /separarGestores\(usuarios\)/); // a lista de Gestores sai da mesma lista de usuários (sem cadastro à parte)
  assert.match(secao, /Gestores da empresa · \{usuarios \? gestores\.length : "…"\}/);
  assert.match(secao, /semGestor \? "Definir Gestor" : "Adicionar Gestor"/);
  assert.match(secao, /quantidade = usuarios \? gestores\.length : empresa\.gestoresAtivos/);
  assert.match(secao, /Demais usuários · \{demais\.length\}/);
  // promover/criar → recarrega a lista na hora (e a contagem da empresa), sem reload manual
  assert.match(secao, /onDefinido=\{\(\) => \{\s*void carregar\(\);\s*onMudou\(\);/);
  // o perfil técnico "operador" nunca é exibido: o rótulo vem de perfilUsuarioLabels ("Usuário")
  assert.match(secao, /operador: perfilUsuarioLabels\.operador/);
  assert.doesNotMatch(secao.replace(/operador: perfilUsuarioLabels\.operador/, ""), />\s*operador\s*</i);
  // nenhum limite de um Gestor / "principal" na UI
  assert.doesNotMatch(secao, /principal|único Gestor|apenas um Gestor/i);
});
