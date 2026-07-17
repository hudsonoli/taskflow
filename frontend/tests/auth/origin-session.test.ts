import assert from "node:assert/strict";
import test from "node:test";
import { makeConfig, TEST_TOKEN } from "./helpers.mjs";

const { NextRequest, NextResponse } = await import("next/server");
const { AuthBffError } = await import("../../src/lib/auth/errors");
const { assertValidMutationOrigin } = await import(
  "../../src/lib/auth/origin"
);
const {
  clearSessionCookie,
  getSessionCookiePolicy,
  readSessionToken,
  setSessionCookie,
} = await import("../../src/lib/auth/session");

test("aceita origem direta presente na allowlist", () => {
  const request = new Request("http://localhost:3010/api/auth/login", {
    method: "POST",
    headers: { origin: "http://localhost:3010" },
  });
  assert.doesNotThrow(() => assertValidMutationOrigin(request, makeConfig()));
});

test("aceita origem encaminhada somente quando explicitamente autorizada", () => {
  const config = makeConfig({
    allowedOrigins: new Set(["https://app.example.com"]),
  });
  const request = new Request("http://taskfloww_front:3000/api/auth/login", {
    method: "POST",
    headers: {
      host: "taskfloww_front:3000",
      origin: "https://app.example.com",
      "x-forwarded-host": "app.example.com",
      "x-forwarded-proto": "https",
    },
  });
  assert.doesNotThrow(() => assertValidMutationOrigin(request, config));
});

test("rejeita origem ausente, divergente, múltipla ou malformada", () => {
  const headersList: HeadersInit[] = [
    {},
    { origin: "https://evil.example" },
    {
      origin: "https://app.example.com",
      "x-forwarded-host": "app.example.com, proxy.internal",
      "x-forwarded-proto": "https",
    },
    { origin: "not-an-origin" },
  ];

  for (const headers of headersList) {
    const request = new Request("http://localhost:3010/api/auth/login", {
      method: "POST",
      headers,
    });
    assert.throws(
      () => assertValidMutationOrigin(request, makeConfig()),
      (error: unknown) =>
        error instanceof AuthBffError && error.code === "INVALID_ORIGIN",
    );
  }
});

test("rejeita headers de proxy múltiplos ou malformados mesmo com origin autorizada", () => {
  const config = makeConfig({
    allowedOrigins: new Set(["https://app.example.com"]),
  });
  const forwardedHeaders = [
    {
      origin: "https://app.example.com",
      "x-forwarded-host": "app.example.com, proxy.internal",
      "x-forwarded-proto": "https",
    },
    {
      origin: "https://app.example.com",
      "x-forwarded-host": "app.example.com",
      "x-forwarded-proto": "javascript",
    },
  ];

  for (const headers of forwardedHeaders) {
    const request = new Request(
      "http://taskfloww_front:3000/api/auth/login",
      { method: "POST", headers },
    );
    assert.throws(
      () => assertValidMutationOrigin(request, config),
      (error: unknown) =>
        error instanceof AuthBffError && error.code === "INVALID_ORIGIN",
    );
  }
});

test("criação e remoção usam a mesma política em desenvolvimento", () => {
  const config = makeConfig();
  const policy = getSessionCookiePolicy(config);
  const created = NextResponse.json({ ok: true });
  const removed = NextResponse.json({ ok: true });

  setSessionCookie(created, TEST_TOKEN, config);
  clearSessionCookie(removed, config);

  assert.equal(policy.name, "taskfloww_session");
  assert.equal(policy.secure, false);
  assert.match(created.headers.get("set-cookie") ?? "", /taskfloww_session=/);
  assert.match(created.headers.get("set-cookie") ?? "", /HttpOnly/i);
  assert.match(created.headers.get("set-cookie") ?? "", /SameSite=lax/i);
  assert.match(created.headers.get("set-cookie") ?? "", /Path=\//);
  assert.match(created.headers.get("set-cookie") ?? "", /Max-Age=1800/i);
  assert.match(removed.headers.get("set-cookie") ?? "", /taskfloww_session=/);
  assert.match(removed.headers.get("set-cookie") ?? "", /Max-Age=0/i);
});

test("criação e remoção usam __Host e Secure em produção", () => {
  const config = makeConfig({ production: true });
  const policy = getSessionCookiePolicy(config);
  const created = NextResponse.json({ ok: true });
  const removed = NextResponse.json({ ok: true });

  setSessionCookie(created, TEST_TOKEN, config);
  clearSessionCookie(removed, config);

  assert.equal(policy.name, "__Host-taskfloww_session");
  assert.equal(policy.secure, true);
  assert.match(created.headers.get("set-cookie") ?? "", /Secure/i);
  assert.match(created.headers.get("set-cookie") ?? "", /Path=\//);
  assert.doesNotMatch(created.headers.get("set-cookie") ?? "", /Domain=/i);
  assert.match(removed.headers.get("set-cookie") ?? "", /__Host-taskfloww_session=/);
  assert.match(removed.headers.get("set-cookie") ?? "", /Secure/i);
  assert.match(removed.headers.get("set-cookie") ?? "", /Max-Age=0/i);
});

test("lê o token somente pelo cookie correspondente ao ambiente", () => {
  const request = new NextRequest("http://localhost:3010/api/auth/me", {
    headers: { cookie: `taskfloww_session=${TEST_TOKEN}` },
  });
  assert.equal(readSessionToken(request, makeConfig()), TEST_TOKEN);
  assert.equal(
    readSessionToken(request, makeConfig({ production: true })),
    null,
  );
});
