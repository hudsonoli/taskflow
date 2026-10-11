// Fase 9B — Portal Externo de Aprovação, lado PÚBLICO. `npm run test:aprovacao-externa-publica`.
// Lógica pura e cliente do BFF exercitados de verdade (fetch injetado); tela, BFF, proxy e layout são lidos como texto.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import {
  DecisaoJaRegistradaError,
  LinkIndisponivelError,
  MENSAGEM_LINK_INDISPONIVEL,
  SemEtapaAnteriorError,
  baixarArtefato,
  baixarLogo,
  consultarAprovacao,
  decidirAprovacao,
  erroDaDecisao,
  erroDoEmail,
  erroDoMotivoDeAjustes,
  erroDoNome,
  extrairTokenDoFragmento,
  montarDecisao,
} from "./aprovacao-externa-publica.ts";
import { ehRotaDeAprovacaoExterna, usaTemaDaEmpresa } from "./tenant.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/ \/\/ .*$/gm, "");

const TOKEN = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdE".slice(0, 43);
const SLUG = "boxcom";

type Chamada = { url: string; init: RequestInit };
function fetchFalso(resposta: Response, chamadas: Chamada[] = []): typeof fetch {
  return (async (url: unknown, init?: RequestInit) => {
    chamadas.push({ url: String(url), init: init ?? {} });
    return resposta;
  }) as typeof fetch;
}
const json = (corpo: unknown, status = 200) => new Response(JSON.stringify(corpo), { status, headers: { "content-type": "application/json" } });

// ── token no fragmento ───────────────────────────────────────────────────────────────────────────────────────

test("o token é lido do FRAGMENTO; sem token, malformado ou em query não vale", () => {
  assert.equal(extrairTokenDoFragmento(`#token=${TOKEN}`), TOKEN);
  assert.equal(extrairTokenDoFragmento(`token=${TOKEN}`), TOKEN);
  assert.equal(extrairTokenDoFragmento(""), null);
  assert.equal(extrairTokenDoFragmento("#token="), null);
  assert.equal(extrairTokenDoFragmento("#token=curto"), null);
  assert.equal(extrairTokenDoFragmento(`#token=${TOKEN}extra`), null); // tamanho exato
  assert.equal(extrairTokenDoFragmento(`#t=${TOKEN}`), null);
  assert.equal(extrairTokenDoFragmento(`#token=${TOKEN.slice(0, 42)}<`), null);
});

// ── validações ───────────────────────────────────────────────────────────────────────────────────────────────

test("nome: obrigatório, 3 a 120, sem HTML", () => {
  assert.match(erroDoNome("") ?? "", /Informe seu nome/);
  assert.match(erroDoNome("ab") ?? "", /ao menos 3/);
  assert.match(erroDoNome("x".repeat(121)) ?? "", /no máximo 120/);
  assert.match(erroDoNome("<b>Maria</b>") ?? "", /HTML/);
  assert.equal(erroDoNome("  Maria   da Silva "), null);
  assert.equal(erroDoNome("Ana"), null);
});

test("e-mail: opcional; se informado, formato válido", () => {
  assert.equal(erroDoEmail(""), null);
  assert.equal(erroDoEmail("   "), null);
  assert.equal(erroDoEmail("maria@cliente.com"), null);
  assert.match(erroDoEmail("sem-arroba") ?? "", /válido/);
  assert.match(erroDoEmail("a@b") ?? "", /válido/);
});

test("motivo dos ajustes: obrigatório só para solicitar ajustes, 3 a 1000, sem HTML", () => {
  assert.match(erroDoMotivoDeAjustes("") ?? "", /Descreva/);
  assert.match(erroDoMotivoDeAjustes("ab") ?? "", /ao menos 3/);
  assert.match(erroDoMotivoDeAjustes("x".repeat(1001)) ?? "", /no máximo 1000/);
  assert.match(erroDoMotivoDeAjustes("<script>x</script>") ?? "", /HTML/);
  assert.equal(erroDoMotivoDeAjustes("Trocar o logotipo"), null);
  assert.equal(erroDaDecisao({ decisao: "aprovar", nome: "Maria", email: "", motivo: "" }), null); // aprovar não exige motivo
  assert.match(erroDaDecisao({ decisao: "solicitar_ajustes", nome: "Maria", email: "", motivo: "" }) ?? "", /Descreva/);
  assert.match(erroDaDecisao({ decisao: "aprovar", nome: "", email: "", motivo: "" }) ?? "", /Informe seu nome/);
});

test("corpo da decisão: nome normalizado, e-mail opcional, motivo SÓ nos ajustes", () => {
  assert.deepEqual(montarDecisao({ decisao: "aprovar", nome: "  Maria   Silva ", email: " ", motivo: "ignorado" }), {
    decisao: "aprovar", nome: "Maria Silva", email: null, motivo: null,
  });
  assert.deepEqual(montarDecisao({ decisao: "solicitar_ajustes", nome: "Ana", email: "a@b.co", motivo: "  Trocar a cor  " }), {
    decisao: "solicitar_ajustes", nome: "Ana", email: "a@b.co", motivo: "Trocar a cor",
  });
});

// ── cliente do BFF ───────────────────────────────────────────────────────────────────────────────────────────

test("consultar: POST no BFF dedicado, token só no CORPO, sem cookies nem Referer", async () => {
  const chamadas: Chamada[] = [];
  const dados = { demandaNome: "Campanha", estado: "pendente" };
  const resultado = await consultarAprovacao(SLUG, TOKEN, fetchFalso(json(dados), chamadas));
  assert.deepEqual(resultado, dados);
  const [{ url, init }] = chamadas;
  assert.equal(url, "/api/aprovacao/consultar");
  assert.doesNotMatch(url, new RegExp(TOKEN)); // nunca em path/query
  assert.equal(init.method, "POST");
  assert.equal(init.credentials, "omit");
  assert.equal(init.referrerPolicy, "no-referrer");
  assert.equal(init.cache, "no-store");
  assert.deepEqual(JSON.parse(String(init.body)), { slug: SLUG, token: TOKEN }); // slug só para conferência no servidor
  assert.deepEqual(init.headers, { "Content-Type": "application/json" }); // nenhum header arbitrário nem Authorization
});

test("consultar: 404 vira LinkIndisponivelError neutro; falha de servidor é erro comum", async () => {
  await assert.rejects(() => consultarAprovacao(SLUG, TOKEN, fetchFalso(json({ detail: MENSAGEM_LINK_INDISPONIVEL }, 404))), LinkIndisponivelError);
  await assert.rejects(() => consultarAprovacao(SLUG, TOKEN, fetchFalso(json({}, 502))), (erro: Error) => !(erro instanceof LinkIndisponivelError));
  try {
    await consultarAprovacao(SLUG, TOKEN, fetchFalso(json({}, 404)));
  } catch (erro) {
    assert.equal((erro as Error).message, MENSAGEM_LINK_INDISPONIVEL);
    assert.doesNotMatch((erro as Error).message, new RegExp(TOKEN));
  }
});

test("decidir: sucesso, já decidida (409), sem etapa anterior (409), indisponível (404), validação (422)", async () => {
  const entrada = montarDecisao({ decisao: "aprovar", nome: "Maria", email: "", motivo: "" });
  const chamadas: Chamada[] = [];
  const ok = await decidirAprovacao(SLUG, TOKEN, entrada, fetchFalso(json({ estado: "aprovada", decididaEm: "2026-10-11T10:00:00Z" }), chamadas));
  assert.equal(ok.estado, "aprovada");
  assert.deepEqual(JSON.parse(String(chamadas[0].init.body)), { slug: SLUG, token: TOKEN, ...entrada });
  assert.equal(chamadas[0].url, "/api/aprovacao/decisao");

  await assert.rejects(() => decidirAprovacao(SLUG, TOKEN, entrada, fetchFalso(json({ detail: { code: "APROVACAO_JA_DECIDIDA", message: "x" } }, 409))), DecisaoJaRegistradaError);
  await assert.rejects(() => decidirAprovacao(SLUG, TOKEN, entrada, fetchFalso(json({ detail: { code: "SEM_ETAPA_ANTERIOR", message: "Sem etapa anterior" } }, 409))), SemEtapaAnteriorError);
  await assert.rejects(() => decidirAprovacao(SLUG, TOKEN, entrada, fetchFalso(json({ detail: MENSAGEM_LINK_INDISPONIVEL }, 404))), LinkIndisponivelError);
  await assert.rejects(
    () => decidirAprovacao(SLUG, TOKEN, entrada, fetchFalso(json({ detail: [{ campo: "nome", mensagem: "nome deve ter pelo menos 3 caracteres" }] }, 422))),
    /nome deve ter pelo menos 3/,
  );
});

test("artefato e logo: bytes por ORDEM (nunca id de arquivo), token no corpo", async () => {
  const chamadas: Chamada[] = [];
  const blob = await baixarArtefato(SLUG, TOKEN, 2, fetchFalso(new Response("bytes", { status: 200 }), chamadas));
  assert.equal(await blob.text(), "bytes");
  assert.equal(chamadas[0].url, "/api/aprovacao/artefato");
  assert.deepEqual(JSON.parse(String(chamadas[0].init.body)), { slug: SLUG, token: TOKEN, ordem: 2 });
  await assert.rejects(() => baixarArtefato(SLUG, TOKEN, 1, fetchFalso(new Response("", { status: 404 }))), LinkIndisponivelError);
  assert.equal(await baixarLogo(SLUG, TOKEN, fetchFalso(new Response("", { status: 404 }))), null); // sem logo: marca padrão, sem erro
  assert.equal(await baixarLogo(SLUG, TOKEN, (async () => { throw new Error("rede"); }) as typeof fetch), null);
});

test("a lib pública não registra nada (console/analytics/storage) e não tem credenciais", () => {
  const lib = semComentarios(ler("lib/aprovacao-externa-publica.ts"));
  assert.doesNotMatch(lib, /console\.|localStorage|sessionStorage|document\.cookie|gtag|analytics|Authorization|tf_session/i);
});

// ── rota pública, shell, proxy, layout ───────────────────────────────────────────────────────────────────────

test("rota /e/<slug>/aprovacao é a ÚNICA pública nua do portal; /aprovacao sem slug deixou de existir", () => {
  assert.equal(ehRotaDeAprovacaoExterna("/e/boxcom/aprovacao"), true);
  assert.equal(ehRotaDeAprovacaoExterna("/e/boxcom/aprovacao/"), true);
  assert.equal(ehRotaDeAprovacaoExterna("/aprovacao"), false);
  assert.equal(ehRotaDeAprovacaoExterna("/aprovacao/"), false);
  assert.equal(ehRotaDeAprovacaoExterna("/e/boxcom/aprovacao/extra"), false);
  assert.equal(ehRotaDeAprovacaoExterna("/e/boxcom/aprovacoes"), false);
  assert.equal(ehRotaDeAprovacaoExterna("/e/boxcom/tarefas"), false);
  assert.equal(ehRotaDeAprovacaoExterna("/e/ab/aprovacao"), false); // slug malformado
  assert.equal(usaTemaDaEmpresa("/e/boxcom/aprovacao"), true);
  assert.equal(usaTemaDaEmpresa("/aprovacao"), false);
  assert.equal(existsSync(new URL("../app/aprovacao/page.tsx", import.meta.url)), false); // nenhuma página serve o portal sem slug
  assert.equal(existsSync(new URL("../app/e/[slug]/aprovacao/page.tsx", import.meta.url)), true);
});

test("AppShell: o portal é tela nua — sem TopNav, sem redirecionar para login nem para a home do tenant", () => {
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /const rotaPortalExterno = ehRotaDeAprovacaoExterna\(pathname\)/);
  assert.match(shell, /rotaRecuperacaoSenha \|\| rotaPortalExterno \|\| sessaoDeOutraEmpresa\) return;/);
  assert.match(shell, /if \(rotaLogin \|\| rotaTrocaSenha \|\| rotaRecuperacaoSenha \|\| rotaPortalExterno\) \{\s*return <>\{children\}<\/>;/);
  // a sessão de OUTRA empresa nunca derruba o portal em "sessão de outra empresa": o catálogo público é checado antes (exigeSessao)
  assert.match(shell, /const exigeSessao = !rotaLogin && !rotaRecuperacaoSenha && !rotaPortalExterno;/);
});

test("sessão do tenant é ignorada: o provider nem consulta /auth/session no portal", () => {
  const dados = semComentarios(ler("lib/AppDataContext.tsx"));
  assert.match(dados, /const portalExterno = ehRotaDeAprovacaoExterna\(usePathname\(\)\)/);
  assert.match(dados, /if \(portalExterno\) \{\s*setSessaoCarregando\(false\);\s*return;\s*\}/);
});

test("proxy: contexto 'aprovacao' (apagado do navegador), no-store, no-referrer e noindex", () => {
  const proxy = semComentarios(ler("proxy.ts"));
  assert.match(proxy, /headers\.delete\(HEADER_CONTEXTO\)/);
  assert.match(proxy, /if \(portal\) headers\.set\(HEADER_CONTEXTO, CONTEXTO_APROVACAO\)/);
  assert.match(proxy, /const slug = portal \? null : slugDaRota\(pathname\)/); // o portal não recebe header de slug: a empresa é a do token
  assert.match(proxy, /"Cache-Control", "no-store"/);
  assert.match(proxy, /"Referrer-Policy", "no-referrer"/);
  assert.match(proxy, /noindex/);
});

test("layout: no portal o HTML inicial sai com marca neutra e SEM sessão/cookie de tenant", () => {
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.match(layout, /const contextoAprovacao = cabecalhos\.get\(HEADER_CONTEXTO\) === CONTEXTO_APROVACAO/);
  assert.match(layout, /const autenticado = !contextoAprovacao && Boolean\(cookieStore\.get\(SESSION_COOKIE_NAME\)\?\.value\)/);
  assert.match(layout, /: contextoAprovacao\s*\? \{ branding: BRANDING_PADRAO/); // marca neutra, como o console da plataforma
});

test("página /e/[slug]/aprovacao: noindex + no-referrer, sem regra de negócio", () => {
  const pagina = semComentarios(ler("app/e/[slug]/aprovacao/page.tsx"));
  assert.match(pagina, /robots: \{ index: false, follow: false \}/);
  assert.match(pagina, /referrer: "no-referrer"/);
  assert.match(pagina, /<AprovacaoPublicaView \/>/);
  assert.doesNotMatch(pagina, /fetch\(|useState|token/);
});

// ── BFF dedicado ─────────────────────────────────────────────────────────────────────────────────────────────

test("BFF /api/aprovacao: namespace próprio, só POST, 4 ações, sem sessão, sem headers arbitrários, token só no corpo", () => {
  assert.equal(existsSync(new URL("../app/api/aprovacao/[acao]/route.ts", import.meta.url)), true);
  const bff = semComentarios(ler("app/api/aprovacao/[acao]/route.ts"));
  assert.match(bff, /const ACOES = \["consultar", "decisao", "artefato", "logo"\]/);
  assert.match(bff, /export async function POST/);
  assert.doesNotMatch(bff, /export async function (GET|PUT|PATCH|DELETE)/);
  assert.doesNotMatch(bff, /cookies\(|SESSION_COOKIE_NAME|tf_session|Authorization|request\.headers|nextUrl|searchParams/); // nada de sessão/headers/query
  assert.match(bff, /headers: \{ "Content-Type": "application\/json" \}/);
  assert.match(bff, /\$\{BACKEND_URL\}\/publico\/aprovacoes\/\$\{acao\}/);
  assert.doesNotMatch(bff, /console\./);
  assert.match(bff, /"Cache-Control": "no-store"/);
  assert.match(bff, /redirect: "error"/);
  assert.match(bff, /TOKEN = \/\^\[A-Za-z0-9_-\]\{43\}\$\//);
  // Fase 9D: o slug da URL segue junto (conferido no backend contra a empresa do token); sem slug válido = link inexistente
  assert.match(bff, /const slug = normalizarSlug\(bruto\.slug\);\s*if \(!slug\) return null;/);
  assert.match(bff, /return \{ slug, token \}/);
});

test("o BFF genérico /api/backend continua exigindo sessão e NÃO serve o portal", () => {
  const generico = semComentarios(ler("app/api/backend/[...path]/route.ts"));
  assert.match(generico, /SESSION_COOKIE_NAME/);
  assert.doesNotMatch(generico, /publico\/aprovacoes/);
});

// ── tela pública ─────────────────────────────────────────────────────────────────────────────────────────────

const tela = semComentarios(ler("components/aprovacao/AprovacaoPublicaView.tsx"));

test("tela: mostra identificador, nome da tarefa, instrução, artefatos, validade e o formulário (Nome*, e-mail opcional, Aprovar, Solicitar ajustes)", () => {
  assert.match(tela, /dados\.demandaIdentificador/);
  assert.match(tela, /dados\.demandaNome/);
  assert.match(tela, /dados\.instrucao/);
  assert.match(tela, /Seu nome \*/);
  assert.match(tela, /Seu e-mail \(opcional\)/);
  assert.match(tela, />\s*\{enviando \? "Enviando…" : "Aprovar"\}/);
  assert.match(tela, /Solicitar ajustes/);
  assert.match(tela, /Quais ajustes são necessários\? \*/);
  assert.match(tela, /Link válido até/);
});

test("tela: 'Solicitar ajustes' só quando o servidor permite (há etapa anterior)", () => {
  assert.match(tela, /dados\.podeSolicitarAjustes && modo !== "solicitar_ajustes"/);
});

test("tela: depois de decidir é somente leitura ('Aprovado em…' / 'Ajustes solicitados em…'), sem nova decisão", () => {
  assert.match(tela, /Aprovado em/);
  assert.match(tela, /Ajustes solicitados em/);
  assert.match(tela, /decidido && dados\.decisao \?/);
});

test("tela: link indisponível usa a mensagem neutra e não distingue o motivo", () => {
  assert.match(tela, /MENSAGEM_LINK_INDISPONIVEL/);
  assert.doesNotMatch(tela, /revogad|expirad|obsolet/i);
});

test("tela: imagem via fetch+Blob, PDF só download (nunca inline), sem iframe/embed/object", () => {
  assert.match(tela, /URL\.createObjectURL\(blob\)/);
  assert.match(tela, /ancora\.download = artefato\.nome/);
  assert.match(tela, /Baixar PDF/);
  assert.doesNotMatch(tela, /<iframe|<embed|<object/);
});

test("tela: texto sempre como TEXTO (sem dangerouslySetInnerHTML), sem log/storage/analytics e sem poluir a URL com o token", () => {
  assert.doesNotMatch(tela, /dangerouslySetInnerHTML|innerHTML/);
  assert.doesNotMatch(tela, /console\.|localStorage|sessionStorage|document\.cookie|gtag|analytics/);
  assert.doesNotMatch(tela, /router\.(push|replace)|location\.(href|assign|replace) *=/);
  assert.match(tela, /extrairTokenDoFragmento\(window\.location\.hash\)/);
});

test("tela: logo e marca vêm do TOKEN (blob do BFF), nunca de cookie/sessão; o slug da URL só segue como CONFERÊNCIA", () => {
  assert.match(tela, /baixarLogo\(slug, doFragmento\)/);
  assert.match(tela, /<BrandLogo variant="auth" srcOverride=\{logo\} \/>/);
  assert.match(tela, /aplicarBrandingRef\.current\(normalizarBranding\(dados\.empresa\)\)/);
  assert.match(tela, /const slug = slugDaRota\(usePathname\(\)\)/);
  assert.match(tela, /consultarAprovacao\(slug \?\? "", token\)/);
  assert.doesNotMatch(tela, /tenantSlug|loginHref|useTenantPath|sessaoSlug|useAppData/);
});

test("tela: mobile-first (coluna única, alvos de toque altos)", () => {
  assert.match(tela, /max-w-xl/);
  assert.match(tela, /min-h-11/);
  assert.match(tela, /flex-col gap-2 sm:flex-row/);
});
