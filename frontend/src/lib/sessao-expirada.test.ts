// Sessão tenant expirada (401) — lógica pura, `fetch` envolvido, coordenação e estrutura. `npm run test:sessao-expirada`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  MENSAGEM_SESSAO_EXPIRADA,
  criarCoordenadorDeSessaoExpirada,
  deveEncerrarPorSessaoExpirada,
  destinoAposLogin,
  ehAreaAutenticadaDoTenant,
  ehChamadaTenantAutenticada,
  envolverFetch,
  hrefLoginPorExpiracao,
  motivoDoLogin,
  proximoSeguro,
} from "./sessao-expirada.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

/** `fetch` falso: responde o status configurado para cada URL (ou 200). */
function fetchFalso(status: number | ((url: string) => number)) {
  const chamadas: string[] = [];
  const falso = (async (entrada: RequestInfo | URL) => {
    const url = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
    chamadas.push(url);
    return new Response(null, { status: typeof status === "number" ? status : status(url) });
  }) as typeof fetch;
  return { falso, chamadas };
}

function montar(status: number | ((url: string) => number), pathname = "/e/boxcom/meu-dia") {
  const { falso, chamadas } = fetchFalso(status);
  const coordenador = criarCoordenadorDeSessaoExpirada();
  let redirects = 0;
  let acionamentos = 0;
  const envolvido = envolverFetch(falso, {
    pathname: () => pathname,
    aoExpirar: () => {
      acionamentos += 1;
      coordenador.disparar(() => {
        redirects += 1;
      });
    },
  });
  return { envolvido, chamadas, coordenador, redirects: () => redirects, acionamentos: () => acionamentos };
}

// A) 401 do proxy tenant → handler acionado
test("A) uma chamada autenticada do tenant que retorna 401 aciona o handler de expiração", async () => {
  const t = montar(401);
  const resposta = await t.envolvido("/api/backend/demandas?limit=50");
  assert.equal(resposta.status, 401); // a resposta segue intacta para quem chamou
  assert.equal(t.acionamentos(), 1);
  assert.equal(t.redirects(), 1);
});

// B) concorrência
test("B) 6 requisições simultâneas com 401 → UM único redirect (e as 6 respostas voltam intactas)", async () => {
  const t = montar(401);
  const respostas = await Promise.all(
    ["/api/backend/demandas", "/api/backend/usuarios/me", "/api/backend/sessoes-trabalho/minhas-ativas", "/api/backend/notificacoes/resumo", "/api/backend/clientes/diretorio", "/api/backend/projetos/diretorio"].map((url) => t.envolvido(url)),
  );
  assert.equal(respostas.length, 6);
  assert.ok(respostas.every((r) => r.status === 401));
  assert.equal(t.acionamentos(), 6); // o interceptor viu os 6…
  assert.equal(t.redirects(), 1); // …mas o coordenador deixou passar só 1
  assert.equal(t.coordenador.totalDisparos(), 1);
});

// C) login com senha errada
test("C) 401 do login / Google / recuperação / senha atual (rotas /api/auth) NÃO é sessão expirada", async () => {
  for (const url of ["/api/auth/login", "/api/auth/google", "/api/auth/password-reset/confirm", "/api/auth/change-password", "/api/auth/definir-senha-inicial", "/api/auth/session"]) {
    const t = montar(401, "/e/boxcom/login");
    await t.envolvido(url);
    assert.equal(t.acionamentos(), 0, url);
    const naAreaInterna = montar(401, "/e/boxcom/minha-conta");
    await naAreaInterna.envolvido(url);
    assert.equal(naAreaInterna.acionamentos(), 0, `${url} (mesmo dentro da área interna)`);
  }
});

// D) /gestao, plataforma, portal
test("D) Gestão, autenticação de plataforma e Portal de Aprovação nunca usam o handler tenant", async () => {
  const gestao = montar(401, "/gestao/empresas");
  await gestao.envolvido("/api/backend/qualquer-coisa"); // até uma chamada ao proxy, na rota de Gestão (sem slug), é ignorada
  await gestao.envolvido("/api/plataforma/empresas");
  assert.equal(gestao.acionamentos(), 0);
  const tenant = montar(401, "/e/boxcom/meu-dia");
  await tenant.envolvido("/api/plataforma/acesso");
  await tenant.envolvido("/api/aprovacao/consultar");
  assert.equal(tenant.acionamentos(), 0);
  const portal = montar(401, "/e/boxcom/aprovacao");
  await portal.envolvido("/api/backend/publico/empresas/boxcom/branding");
  assert.equal(portal.acionamentos(), 0); // Portal Externo: página pública do tenant
  assert.equal(ehAreaAutenticadaDoTenant("/gestao"), false);
  assert.equal(ehAreaAutenticadaDoTenant("/e/boxcom/login"), false);
  assert.equal(ehAreaAutenticadaDoTenant("/e/boxcom/esqueci-senha"), false);
  assert.equal(ehAreaAutenticadaDoTenant("/e/boxcom/redefinir-senha"), false);
  assert.equal(ehAreaAutenticadaDoTenant("/e/boxcom/aprovacao"), false);
  assert.equal(ehAreaAutenticadaDoTenant("/e/boxcom/meu-dia"), true);
  assert.equal(ehAreaAutenticadaDoTenant("/"), false);
});

// E/F) outros status
test("E/F) 403, 404, 409, 422 e 5xx NÃO redirecionam para o login", async () => {
  for (const status of [403, 404, 409, 422, 429, 500, 502, 503]) {
    const t = montar(status);
    await t.envolvido("/api/backend/demandas");
    assert.equal(t.acionamentos(), 0, String(status));
    assert.equal(t.redirects(), 0, String(status));
  }
  // o 403 estruturado do futuro expediente nunca é tratado aqui
  assert.equal(deveEncerrarPorSessaoExpirada({ url: "/api/backend/demandas", status: 403, pathname: "/e/boxcom/meu-dia" }), false);
});

test("só o proxy tenant conta: URLs absolutas da mesma origem sim, de outra origem não", () => {
  assert.equal(ehChamadaTenantAutenticada("/api/backend/usuarios/me"), true);
  assert.equal(ehChamadaTenantAutenticada("https://taskflow.exemplo.com/api/backend/usuarios/me?x=1", "https://taskflow.exemplo.com"), true);
  assert.equal(ehChamadaTenantAutenticada("https://outro.com/api/backend/usuarios/me", "https://taskflow.exemplo.com"), false);
  assert.equal(ehChamadaTenantAutenticada("/api/backendx/y"), false);
  assert.equal(ehChamadaTenantAutenticada("/api/auth/login"), false);
});

// G) slug preservado
test("G) o slug real da URL é preservado: /e/boxcom/meu-dia → /e/boxcom/login", () => {
  const href = hrefLoginPorExpiracao("/e/boxcom/meu-dia");
  assert.ok(href?.startsWith("/e/boxcom/login?"));
  assert.match(href ?? "", /reason=session_expired/);
  assert.equal(hrefLoginPorExpiracao("/e/outra-empresa/pauta")?.startsWith("/e/outra-empresa/login?"), true);
  assert.equal(href?.startsWith("/login"), false);
  assert.equal(hrefLoginPorExpiracao("/gestao"), null);
  assert.equal(hrefLoginPorExpiracao("/e/boxcom/login"), null);
  assert.equal(hrefLoginPorExpiracao("/"), null);
});

// return-to
test("return-to: volta ao caminho de origem (com query) e só ao do PRÓPRIO tenant", () => {
  assert.equal(new URL(`http://x${hrefLoginPorExpiracao("/e/boxcom/tarefas", "?busca=a")}`).searchParams.get("next"), "/e/boxcom/tarefas?busca=a");
  assert.equal(proximoSeguro("/e/boxcom/meu-dia", "boxcom"), "/e/boxcom/meu-dia");
  assert.equal(destinoAposLogin("boxcom", "/e/boxcom/pauta", "/e/boxcom/meu-dia"), "/e/boxcom/pauta");
  assert.equal(destinoAposLogin("boxcom", null, "/e/boxcom/meu-dia"), "/e/boxcom/meu-dia");
});

test("return-to: nada de externo, de outro tenant, de esquema perigoso, de travessia ou das telas públicas", () => {
  const perigosos = [
    "https://externo.com/e/boxcom/meu-dia",
    "//externo.com/e/boxcom/x",
    "///externo.com",
    "javascript:alert(1)",
    "/e/outra/meu-dia", // outro tenant
    "/e/boxcom/../outra/meu-dia",
    "/e/boxcom/%2e%2e/outra",
    "/e/boxcom//externo.com",
    "/e/boxcom/meu-dia\\..\\x",
    "/e/boxcom/meu-dia\n",
    "/e/boxcom/login", // laço
    "/e/boxcom/esqueci-senha",
    "/e/boxcom/aprovacao",
    "/e/boxcom/trocar-senha-inicial",
    "/meu-dia", // sem tenant
    "",
    "/e/boxcom/" + "a".repeat(400),
  ];
  for (const valor of perigosos) assert.equal(proximoSeguro(valor, "boxcom"), null, JSON.stringify(valor).slice(0, 60));
  assert.equal(proximoSeguro(undefined, "boxcom"), null);
  assert.equal(proximoSeguro("/e/boxcom/meu-dia", null), null);
  assert.equal(destinoAposLogin("boxcom", "https://externo.com", "/e/boxcom/meu-dia"), "/e/boxcom/meu-dia");
});

// H) reason + mensagem
test("H) reason=session_expired liga a mensagem discreta; qualquer outro valor é ignorado", () => {
  assert.equal(MENSAGEM_SESSAO_EXPIRADA, "Sua sessão expirou. Entre novamente.");
  assert.equal(motivoDoLogin("session_expired"), "session_expired");
  assert.equal(motivoDoLogin(["session_expired", "x"]), "session_expired");
  assert.equal(motivoDoLogin("<script>"), null);
  assert.equal(motivoDoLogin(undefined), null);
  const login = ler("components/auth/LoginView.tsx");
  assert.match(login, /sessaoExpirada && \(/);
  assert.match(login, /MENSAGEM_SESSAO_EXPIRADA/);
  assert.equal((login.match(/MENSAGEM_SESSAO_EXPIRADA/g) ?? []).length, 2); // import + uma única exibição
  const bloco = login.slice(login.indexOf("sessaoExpirada && ("), login.indexOf("<form onSubmit"));
  assert.equal(/red-|erro/i.test(bloco), false); // sem vermelho/erro crítico
  const pagina = semComentarios(ler("app/e/[slug]/login/page.tsx"));
  assert.match(pagina, /motivoDoLogin\(consulta\.reason\)/);
  assert.match(pagina, /proximoSeguro\(/);
});

// I) idempotência
test("I) handler repetido depois de já iniciada a navegação é no-op; resetar (nova sessão) o rearma", () => {
  const c = criarCoordenadorDeSessaoExpirada();
  let execucoes = 0;
  assert.equal(c.disparar(() => (execucoes += 1)), true);
  assert.equal(c.disparar(() => (execucoes += 1)), false);
  assert.equal(c.disparar(() => (execucoes += 1)), false);
  assert.equal(execucoes, 1);
  c.resetar();
  assert.equal(c.disparar(() => (execucoes += 1)), true);
  assert.equal(execucoes, 2);
});

test("o fetch só é envolvido uma vez (idempotente) e a resposta/erros do original passam intactos", async () => {
  const { falso } = fetchFalso(200);
  const opcoes = { aoExpirar: () => undefined, pathname: () => "/e/boxcom/meu-dia" };
  const uma = envolverFetch(falso, opcoes);
  assert.notEqual(uma, falso);
  assert.equal(envolverFetch(uma, opcoes), uma);
  const quebrado = envolverFetch((async () => { throw new TypeError("rede"); }) as typeof fetch, opcoes);
  await assert.rejects(() => quebrado("/api/backend/x"), TypeError);
});

// ── estrutura ────────────────────────────────────────────────────────────────────────────────────────────────

test("uma única fonte de verdade: só o AppDataProvider instala o handler; nenhuma tela trata 401 por conta própria", () => {
  const contexto = semComentarios(ler("lib/AppDataContext.tsx"));
  assert.equal((contexto.match(/envolverFetch\(/g) ?? []).length, 1);
  assert.match(contexto, /coordenadorSessaoExpirada\.disparar\(/);
  assert.match(contexto, /logoutRequest\(\)/); // limpa o cookie HttpOnly pelo mecanismo existente
  assert.match(contexto, /hrefLoginPorExpiracao\(window\.location\.pathname, window\.location\.search\)/);
  // o revalidar() deixou de depender de "o fluxo normal cuida" sem fazer nada
  assert.equal(contexto.includes("o fluxo normal de sessão cuida"), false);
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /hrefLoginExpirado \?\? hrefLogin\(slugUrl\)/);
  // nenhum redirect por 401 espalhado nas telas
  const espalhado = ["components/dashboard/DashboardView.tsx", "components/pauta/PautaView.tsx", "components/projetos/ProjetosView.tsx", "components/trafego/TrafegoView.tsx", "components/minhas-demandas/MinhasDemandasView.tsx"];
  for (const arquivo of espalhado) assert.equal(/=== 401|status\s*===\s*401/.test(semComentarios(ler(arquivo))), false, arquivo);
});

test("o handler de sessão expirada em si não tem logout por horário, bloqueio de expediente nem polling (isso vive em lib/expediente-*)", () => {
  const lib = semComentarios(ler("lib/sessao-expirada.ts"));
  assert.equal(/FORA_DO_EXPEDIENTE|setInterval|setTimeout|agendar/i.test(lib), false);
  const contexto = semComentarios(ler("lib/AppDataContext.tsx"));
  assert.equal((contexto.match(/setInterval/g) ?? []).length, 1); // só o da revalidação de 2 min que já existia
});
