import assert from "node:assert/strict";
import test from "node:test";
import { CURRENT_USER, makeConfig, TEST_TOKEN } from "./helpers.mjs";

const { AuthBackendClient } = await import("../../src/lib/auth/backend");
const { AuthBffError } = await import("../../src/lib/auth/errors");

test("login usa endpoint fechado e valida o contrato do token", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json({ accessToken: TEST_TOKEN, tokenType: "bearer" });
  };

  const response = await new AuthBackendClient(makeConfig(), fetchMock).login({
    empresaCodigo: "EMPRESA",
    email: "user@example.com",
    senha: "secret-password",
  });

  assert.equal(capturedUrl, "http://taskfloww_api:8000/auth/login");
  assert.equal(capturedInit?.method, "POST");
  assert.equal(response.accessToken, TEST_TOKEN);
});

test("me envia Bearer server-side e retorna identidade validada", async () => {
  let authorization = "";
  const fetchMock: typeof fetch = async (_input, init) => {
    authorization = new Headers(init?.headers).get("authorization") ?? "";
    return Response.json(CURRENT_USER);
  };

  const user = await new AuthBackendClient(makeConfig(), fetchMock).me(
    TEST_TOKEN,
  );

  assert.equal(authorization, `Bearer ${TEST_TOKEN}`);
  assert.deepEqual(user, CURRENT_USER);
});

test("alteração de senha aceita 204 sem tentar ler JSON", async () => {
  let authorization = "";
  const fetchMock: typeof fetch = async (_input, init) => {
    authorization = new Headers(init?.headers).get("authorization") ?? "";
    return new Response(null, { status: 204 });
  };

  await new AuthBackendClient(makeConfig(), fetchMock).changePassword(
    TEST_TOKEN,
    {
      senhaAtual: "old-password",
      novaSenha: "new-password",
      confirmacaoSenha: "new-password",
    },
  );
  assert.equal(authorization, `Bearer ${TEST_TOKEN}`);
});

test("mapeia timeout e indisponibilidade sem expor detalhes", async () => {
  const timeoutFetch: typeof fetch = async (_input, init) =>
    new Promise((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new Error("token-secret")));
    });
  const unavailableFetch: typeof fetch = async () => {
    throw new TypeError("internal backend URL");
  };

  await assert.rejects(
    new AuthBackendClient(
      makeConfig({ backendTimeoutMs: 5 }),
      timeoutFetch,
    ).me(TEST_TOKEN),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 504 &&
      error.code === "BACKEND_TIMEOUT" &&
      !error.safeMessage.includes(TEST_TOKEN),
  );
  await assert.rejects(
    new AuthBackendClient(makeConfig(), unavailableFetch).me(TEST_TOKEN),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 502 &&
      error.code === "BACKEND_UNAVAILABLE",
  );
});

test("rejeita JSON inválido do backend", async () => {
  const fetchMock: typeof fetch = async () =>
    new Response("not-json", {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  await assert.rejects(
    new AuthBackendClient(makeConfig(), fetchMock).me(TEST_TOKEN),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 502 &&
      error.code === "INVALID_BACKEND_RESPONSE",
  );
});
