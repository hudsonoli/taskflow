import assert from "node:assert/strict";
import test from "node:test";
import { CURRENT_USER } from "./helpers.mjs";

const { createAuthBrowserClient } = await import("../../src/lib/auth/client");
const {
  getSessionCookieName,
  isDevelopmentCookie,
  isProductionCookie,
} = await import("../../src/lib/auth/cookie");

test("busca identidade uma única vez e usa somente o BFF same-origin", async () => {
  const calls: Array<{ input: string; init?: RequestInit }> = [];
  const fetchMock: typeof fetch = async (input, init) => {
    calls.push({ input: String(input), init });
    return Response.json(CURRENT_USER);
  };
  const client = createAuthBrowserClient(fetchMock);

  const [first, second] = await Promise.all([
    client.getInitialUser(),
    client.getInitialUser(),
  ]);

  assert.equal(calls.length, 1);
  assert.equal(calls[0].input, "/api/auth/me");
  assert.equal(calls[0].init?.method, "GET");
  assert.equal(calls[0].init?.credentials, "same-origin");
  assert.equal(calls[0].init?.cache, "no-store");
  assert.equal(new Headers(calls[0].init?.headers).has("authorization"), false);
  assert.deepEqual(first, { status: "authenticated", user: CURRENT_USER });
  assert.deepEqual(second, first);
});

test("classifica 401 como unauthenticated e 5xx como error", async () => {
  const unauthenticated = createAuthBrowserClient(async () =>
    Response.json(
      { error: { code: "UNAUTHENTICATED", message: "Sessão expirada." } },
      { status: 401 },
    ),
  );
  const unavailable = createAuthBrowserClient(async () =>
    Response.json(
      { error: { code: "BACKEND_UNAVAILABLE", message: "Indisponível." } },
      { status: 502 },
    ),
  );

  assert.equal((await unauthenticated.getInitialUser()).status, "unauthenticated");
  assert.equal((await unavailable.getInitialUser()).status, "error");
});

test("refresh força nova busca e logout usa somente o endpoint local", async () => {
  const calls: Array<{ input: string; init?: RequestInit }> = [];
  const fetchMock: typeof fetch = async (input, init) => {
    calls.push({ input: String(input), init });
    return String(input) === "/api/auth/logout"
      ? Response.json({ success: true })
      : Response.json(CURRENT_USER);
  };
  const client = createAuthBrowserClient(fetchMock);

  await client.getInitialUser();
  await client.refresh();
  const logout = await client.logout();

  assert.deepEqual(calls.map((call) => call.input), [
    "/api/auth/me",
    "/api/auth/me",
    "/api/auth/logout",
  ]);
  assert.equal(calls[2].init?.method, "POST");
  assert.equal(calls[2].init?.credentials, "same-origin");
  assert.equal(calls[2].init?.cache, "no-store");
  assert.equal(new Headers(calls[2].init?.headers).has("authorization"), false);
  assert.deepEqual(logout, { status: "unauthenticated", error: null });
});

test("falhas de rede são seguras e não expõem token", async () => {
  const client = createAuthBrowserClient(async () => {
    throw new Error("internal detail");
  });

  const result = await client.getInitialUser();
  assert.equal(result.status, "error");
  assert.equal(JSON.stringify(result).includes("accessToken"), false);
  assert.equal(JSON.stringify(result).includes("internal detail"), false);
});

test("helper de cookie distingue desenvolvimento e produção", () => {
  assert.equal(getSessionCookieName(false), "taskfloww_session");
  assert.equal(getSessionCookieName(true), "__Host-taskfloww_session");
  assert.equal(isDevelopmentCookie("taskfloww_session"), true);
  assert.equal(isProductionCookie("__Host-taskfloww_session"), true);
  assert.equal(isProductionCookie("taskfloww_session"), false);
});
