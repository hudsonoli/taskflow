import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import "./helpers.mjs";

const { NextRequest } = await import("next/server");
const { config, proxy } = await import("../../src/proxy");
const { getSessionCookieName } = await import("../../src/lib/auth/cookie");
const {
  buildReturnTo,
  decideRouteProtection,
  hasSessionCookie,
  isPublicRoute,
} = await import("../../src/lib/auth/route-protection");

const PUBLIC_PATHS = [
  "/login",
  "/login/",
  "/api/auth",
  "/api/auth/me",
  "/_next",
  "/_next/static/chunks/app.js",
  "/_next/image",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
  "/manifest.webmanifest",
  "/file.svg",
  "/globe.svg",
  "/next.svg",
  "/vercel.svg",
  "/window.svg",
];

const PRIVATE_PATHS = [
  "/",
  "/clientes",
  "/login-admin",
  "/api/authenticacao",
  "/api/authx",
  "/favicon.ico-admin",
  "/arquivo.sem-extensao",
  "/api/private/report.csv",
  "/relatorios/v1.2",
];

function decision(
  pathname: string,
  search = "",
  sessionCookiePresent = false,
) {
  return decideRouteProtection({ pathname, search, sessionCookiePresent });
}

function cookieReader(expectedName: string, value?: string) {
  return {
    get(name: string) {
      return name === expectedName && value !== undefined ? { value } : undefined;
    },
  };
}

test("libera somente as rotas públicas explícitas sem cookie", () => {
  for (const pathname of PUBLIC_PATHS) {
    assert.equal(isPublicRoute(pathname), true, pathname);
    assert.deepEqual(
      decision(pathname),
      { action: "allow", reason: "public-route" },
      pathname,
    );
  }
});

test("mantém páginas e APIs não listadas privadas por padrão", () => {
  for (const pathname of PRIVATE_PATHS) {
    assert.equal(isPublicRoute(pathname), false, pathname);
    assert.deepEqual(
      decision(pathname),
      { action: "redirect", returnTo: pathname },
      pathname,
    );
  }
});

test("/login e /login/ permanecem públicas com ou sem cookie", () => {
  for (const pathname of ["/login", "/login/"]) {
    assert.deepEqual(decision(pathname, "", true), {
      action: "allow",
      reason: "public-route",
    });
    assert.deepEqual(decision(pathname), {
      action: "allow",
      reason: "public-route",
    });
  }
});

test("returnTo preserva pathname, query, Unicode e percent-encoding", () => {
  for (const [search, expected] of [
    ["", "/clientes"],
    ["?status=ativo", "/clientes?status=ativo"],
    [
      "?status=ativo&ordem=nome",
      "/clientes?status=ativo&ordem=nome",
    ],
    ["?nome=João", "/clientes?nome=João"],
    ["?nome=Jo%C3%A3o", "/clientes?nome=Jo%C3%A3o"],
    ["?destino=%2Fprojetos", "/clientes?destino=%2Fprojetos"],
  ]) {
    assert.equal(buildReturnTo("/clientes", search), expected);
  }
});

test("aceita somente cookie esperado com valor não vazio", () => {
  const developmentName = getSessionCookieName(false);
  const productionName = getSessionCookieName(true);

  assert.equal(developmentName, "taskfloww_session");
  assert.equal(productionName, "__Host-taskfloww_session");
  assert.equal(
    hasSessionCookie(cookieReader(developmentName, "valor-opaco"), false),
    true,
  );
  assert.equal(
    hasSessionCookie(cookieReader("outro_cookie", "valor-opaco"), false),
    false,
  );
  assert.equal(hasSessionCookie(cookieReader(developmentName, ""), false), false);
  assert.equal(
    hasSessionCookie(cookieReader(developmentName, "   "), false),
    false,
  );
  assert.equal(
    hasSessionCookie(cookieReader(productionName, "valor-opaco"), true),
    true,
  );
});

test("proxy redireciona com 307 e returnTo sem host ou origem", () => {
  const response = proxy(
    new NextRequest("https://app.example.com/clientes?status=ativo&ordem=nome"),
  );
  const location = new URL(response.headers.get("location") ?? "");

  assert.equal(response.status, 307);
  assert.equal(location.origin, "https://app.example.com");
  assert.equal(location.pathname, "/login");
  assert.equal(
    location.searchParams.get("returnTo"),
    "/clientes?status=ativo&ordem=nome",
  );
  assert.equal(
    location.searchParams.get("returnTo")?.includes("app.example.com"),
    false,
  );
});

test("proxy preserva Unicode e query percent-encoded sem dupla codificação", () => {
  const response = proxy(
    new NextRequest(
      "https://app.example.com/clientes?nome=Jo%C3%A3o&destino=%2Fprojetos",
    ),
  );
  const location = new URL(response.headers.get("location") ?? "");

  assert.equal(
    location.searchParams.get("returnTo"),
    "/clientes?nome=Jo%C3%A3o&destino=%2Fprojetos",
  );
});

test("proxy permite cookie útil e rejeita cookie errado, vazio ou com espaços", () => {
  const cookieName = getSessionCookieName(false);
  const cases = [
    { cookie: `${cookieName}=valor-opaco`, allowed: true },
    { cookie: "outro_cookie=valor-opaco", allowed: false },
    { cookie: `${cookieName}=`, allowed: false },
    { cookie: `${cookieName}=%20%20%20`, allowed: false },
  ];

  for (const { cookie, allowed } of cases) {
    const response = proxy(
      new NextRequest("http://localhost:3010/clientes", {
        headers: { cookie },
      }),
    );

    assert.equal(response.headers.get("x-middleware-next") === "1", allowed);
    assert.equal(response.status, allowed ? 200 : 307);
  }
});

test("matcher exclui somente recursos internos inequívocos do Next", () => {
  assert.equal(config.matcher.length, 1);
  const matcher = new RegExp(`^${config.matcher[0]}$`);

  for (const url of ["/_next/static/chunks/app.js", "/_next/image"]) {
    assert.equal(matcher.test(url), false, url);
  }

  for (const url of [
    "/_next/staticx",
    "/_next/image-cache",
    "/file.svg",
    "/favicon.ico",
    "/api/private/report.csv",
    "/relatorios/v1.2",
  ]) {
    assert.equal(matcher.test(url), true, url);
  }
});

test("proxy não consulta serviços nem tenta validar JWT", async () => {
  const proxySource = await readFile(
    path.join(process.cwd(), "src", "proxy.ts"),
    "utf8",
  );
  const protectionSource = await readFile(
    path.join(process.cwd(), "src", "lib", "auth", "route-protection.ts"),
    "utf8",
  );
  const source = `${proxySource}\n${protectionSource}`;

  assert.doesNotMatch(source, /fetch\(|Authorization|Bearer|FastAPI|accessToken/);
  assert.doesNotMatch(source, /lib\/auth\/session/);
  assert.doesNotMatch(source, /\.\*\\\\\.\[\^\/\]\+\$/);
  assert.match(proxySource, /hasSessionCookie\(request\.cookies\)/);
});
