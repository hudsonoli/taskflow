import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import "./helpers.mjs";
import { CURRENT_USER } from "./helpers.mjs";

const {
  completeLogin,
  createLoginRequestBody,
  getSafeReturnTo,
} = await import("../../src/lib/auth/login-flow");

const sourceRoot = path.join(process.cwd(), "src");

async function source(...segments: string[]) {
  return readFile(path.join(sourceRoot, ...segments), "utf8");
}

function loginResponse(
  body: unknown = CURRENT_USER,
  init: ResponseInit = {},
): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json; charset=utf-8" },
    ...init,
  });
}

async function assertLoginRejected(response: Response) {
  let refreshCalled = false;
  let redirectCalled = false;

  const completed = await completeLogin(response, "/dashboard", {
    refresh: async () => {
      refreshCalled = true;
    },
    redirect: () => {
      redirectCalled = true;
    },
  });

  assert.equal(completed, false);
  assert.equal(refreshCalled, false);
  assert.equal(redirectCalled, false);
}

test("página /login usa o formulário sem alterar o layout principal", async () => {
  const page = await source("app", "login", "page.tsx");

  assert.match(page, /<LoginForm returnTo=\{returnTo\} \/>/);
  assert.match(page, /fixed inset-0/);
  assert.doesNotMatch(page, /RequireAuth|ProtectedRoute|redirect\(/);
});

test("payload de login contém somente e-mail normalizado e senha", () => {
  assert.deepEqual(createLoginRequestBody(" user@example.com ", "secret"), {
    email: "user@example.com",
    senha: "secret",
  });
  assert.equal(
    "empresaCodigo" in createLoginRequestBody("user@example.com", "secret"),
    false,
  );
});

test("LoginForm chama somente o BFF same-origin sem token no cliente", async () => {
  const form = await source("components", "auth", "LoginForm.tsx");

  assert.match(form, /fetch\("\/api\/auth\/login"/);
  assert.match(form, /credentials: "same-origin"/);
  assert.match(form, /cache: "no-store"/);
  assert.doesNotMatch(form, /empresaCodigo|Authorization|Bearer|accessToken/);
  assert.doesNotMatch(form, /localStorage|sessionStorage|document\.cookie/);
});

test("contrato válido aguarda refresh antes de redirecionar", async () => {
  const events: string[] = [];
  let notifyRefreshStarted!: () => void;
  let releaseRefresh!: () => void;
  const refreshStarted = new Promise<void>((resolve) => {
    notifyRefreshStarted = resolve;
  });
  const refreshPending = new Promise<void>((resolve) => {
    releaseRefresh = resolve;
  });

  const completion = completeLogin(
    loginResponse(),
    "/projetos?status=ativo",
    {
      refresh: async () => {
        events.push("refresh:start");
        notifyRefreshStarted();
        await refreshPending;
        events.push("refresh:end");
      },
      redirect: (destination) => {
        events.push(`redirect:${destination}`);
      },
    },
  );

  await refreshStarted;
  assert.deepEqual(events, ["refresh:start"]);

  releaseRefresh();
  assert.equal(await completion, true);
  assert.deepEqual(events, [
    "refresh:start",
    "refresh:end",
    "redirect:/projetos?status=ativo",
  ]);
});

test("status 201 e 204 não atualizam identidade nem redirecionam", async () => {
  await assertLoginRejected(
    loginResponse(CURRENT_USER, { status: 201 }),
  );
  await assertLoginRejected(new Response(null, { status: 204 }));
});

test("JSON malformado ou contrato incompatível não concluem o login", async () => {
  await assertLoginRejected(
    new Response("{invalid", {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
  await assertLoginRejected(loginResponse({ success: true }));
  await assertLoginRejected(
    new Response(JSON.stringify(CURRENT_USER), {
      status: 200,
      headers: { "content-type": "text/plain" },
    }),
  );
});

test("erros exibidos pelo formulário permanecem genéricos e seguros", async () => {
  const form = await source("components", "auth", "LoginForm.tsx");

  assert.match(form, /case 401:/);
  assert.match(form, /E-mail ou senha inválidos\./);
  assert.match(form, /case 403:/);
  assert.match(form, /case 422:/);
  assert.match(form, /Verifique sua conexão e tente novamente\./);
  assert.doesNotMatch(form, /internal detail|stack|CONFIGURATION_ERROR/);
});

test("loading bloqueia envio duplicado e desabilita controles", async () => {
  const form = await source("components", "auth", "LoginForm.tsx");

  assert.match(form, /if \(submittingRef\.current\)/);
  assert.match(form, /submittingRef\.current = true/);
  assert.match(form, /disabled=\{submitting\}/);
  assert.match(form, /submitting \? "Entrando\.\.\." : "Entrar"/);
});

test("returnTo aceita caminhos internos seguros", () => {
  for (const value of [
    "/",
    "/dashboard",
    "/projetos?status=ativo",
    "/tarefas#hoje",
  ]) {
    assert.equal(getSafeReturnTo(value), value);
  }
});

test("returnTo rejeita formas literais e codificadas perigosas", () => {
  for (const value of [
    null,
    "",
    "http://evil.example",
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "javascript:alert(1)",
    "data:text/html,test",
    "dashboard",
    "/%2F%2Fevil.example",
    "/%5Cevil.example",
    "/%255Cevil.example",
    "/%09/evil.example",
    "/%E0%A4%A",
    "/dashboard\u0000extra",
  ]) {
    assert.equal(getSafeReturnTo(value), "/", value ?? "null");
  }
});
