import assert from "node:assert/strict";
import test from "node:test";
import {
  CURRENT_USER,
  setValidAuthEnvironment,
  TEST_TOKEN,
} from "./helpers.mjs";

const { NextRequest } = await import("next/server");
const loginRoute = await import("../../src/app/api/auth/login/route");
const meRoute = await import("../../src/app/api/auth/me/route");
const logoutRoute = await import("../../src/app/api/auth/logout/route");
const changePasswordRoute = await import(
  "../../src/app/api/auth/alterar-senha/route"
);

const originalFetch = globalThis.fetch;

function setValidLoginEnvironment() {
  setValidAuthEnvironment();
  process.env.AUTH_DEFAULT_EMPRESA_CODIGO = "EMPRESA_CONFIGURADA";
}

function mutationRequest(path: string, body?: Record<string, unknown>) {
  return new NextRequest(`http://localhost:3010${path}`, {
    method: "POST",
    headers: {
      origin: "http://localhost:3010",
      ...(body ? { "content-type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function withFetchMock<T>(
  fetchMock: typeof fetch,
  callback: () => Promise<T>,
): Promise<T> {
  globalThis.fetch = fetchMock;
  try {
    return await callback();
  } finally {
    globalThis.fetch = originalFetch;
  }
}

test("login válido cria cookie HttpOnly e devolve identidade sem token", async () => {
  setValidLoginEnvironment();
  let call = 0;
  let sentLoginBody = "";
  const fetchMock: typeof fetch = async (_input, init) => {
    call += 1;
    if (call === 1) {
      sentLoginBody = String(init?.body);
      return Response.json({ accessToken: TEST_TOKEN, tokenType: "bearer" });
    }
    return Response.json(CURRENT_USER);
  };

  const response = await withFetchMock(fetchMock, () =>
    loginRoute.POST(
      mutationRequest("/api/auth/login", {
        email: "user@example.com",
        senha: "secret-password",
      }),
    ),
  );
  const body = await response.json();
  const serializedBody = JSON.stringify(body);

  assert.equal(response.status, 200);
  assert.deepEqual(JSON.parse(sentLoginBody), {
    empresaCodigo: "EMPRESA_CONFIGURADA",
    email: "user@example.com",
    senha: "secret-password",
  });
  assert.deepEqual(body, CURRENT_USER);
  assert.equal(serializedBody.includes("accessToken"), false);
  assert.equal(serializedBody.includes(TEST_TOKEN), false);
  assert.match(response.headers.get("set-cookie") ?? "", /HttpOnly/i);
});

test("login parcial não cria cookie quando /auth/me falha", async () => {
  setValidLoginEnvironment();
  let call = 0;
  const fetchMock: typeof fetch = async () => {
    call += 1;
    return call === 1
      ? Response.json({ accessToken: TEST_TOKEN, tokenType: "bearer" })
      : new Response(JSON.stringify({ detail: "internal" }), { status: 502 });
  };

  const response = await withFetchMock(fetchMock, () =>
    loginRoute.POST(
      mutationRequest("/api/auth/login", {
        email: "user@example.com",
        senha: "secret-password",
      }),
    ),
  );

  assert.equal(response.status, 502);
  assert.equal(response.headers.has("set-cookie"), false);
  assert.equal((await response.text()).includes(TEST_TOKEN), false);
});

test("login inválido não cria cookie", async () => {
  setValidLoginEnvironment();
  const fetchMock: typeof fetch = async () =>
    new Response(JSON.stringify({ detail: "Credenciais inválidas" }), {
      status: 401,
    });

  const response = await withFetchMock(fetchMock, () =>
    loginRoute.POST(
      mutationRequest("/api/auth/login", {
        email: "user@example.com",
        senha: "wrong-password",
      }),
    ),
  );

  assert.equal(response.status, 401);
  assert.equal(response.headers.has("set-cookie"), false);
  assert.equal((await response.text()).includes("Credenciais inválidas"), false);
});

test("configuração ausente produz erro seguro", async () => {
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  delete process.env.TASKFLOWW_API_INTERNAL_URL;
  delete process.env.TASKFLOWW_AUTH_ALLOWED_ORIGINS;
  delete process.env.TASKFLOWW_SESSION_MAX_AGE_SECONDS;

  const response = await loginRoute.POST(
    mutationRequest("/api/auth/login", {
      email: "user@example.com",
      senha: "secret-password",
    }),
  );

  assert.equal(response.status, 500);
  assert.deepEqual(await response.json(), {
    error: {
      code: "CONFIGURATION_ERROR",
      message:
        "Configuração obrigatória ausente ou inválida: TASKFLOWW_API_INTERNAL_URL.",
    },
  });
});

test("empresa padrão ausente não chama o FastAPI nem revela configuração", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  let backendCalled = false;
  const fetchMock: typeof fetch = async () => {
    backendCalled = true;
    return Response.json({});
  };

  const response = await withFetchMock(fetchMock, () =>
    loginRoute.POST(
      mutationRequest("/api/auth/login", {
        email: "user@example.com",
        senha: "secret-password",
      }),
    ),
  );

  assert.equal(response.status, 500);
  assert.equal(backendCalled, false);
  assert.deepEqual(await response.json(), {
    error: {
      code: "CONFIGURATION_ERROR",
      message: "Não foi possível concluir a solicitação.",
    },
  });
});

test("/me sem cookie retorna 401", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  const response = await meRoute.GET(
    new NextRequest("http://localhost:3010/api/auth/me"),
  );
  assert.equal(response.status, 401);
});

test("/me envia Bearer e retorna identidade sem token", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  let authorization = "";
  const fetchMock: typeof fetch = async (_input, init) => {
    authorization = new Headers(init?.headers).get("authorization") ?? "";
    return Response.json(CURRENT_USER);
  };
  const request = new NextRequest("http://localhost:3010/api/auth/me", {
    headers: { cookie: `taskfloww_session=${TEST_TOKEN}` },
  });

  const response = await withFetchMock(fetchMock, () => meRoute.GET(request));
  const body = await response.json();

  assert.equal(authorization, `Bearer ${TEST_TOKEN}`);
  assert.deepEqual(body, CURRENT_USER);
  assert.equal(JSON.stringify(body).includes(TEST_TOKEN), false);
});

test("/me limpa cookie quando backend retorna 401", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  const fetchMock: typeof fetch = async () =>
    new Response(JSON.stringify({ detail: "Token inválido" }), { status: 401 });
  const request = new NextRequest("http://localhost:3010/api/auth/me", {
    headers: { cookie: `taskfloww_session=${TEST_TOKEN}` },
  });

  const response = await withFetchMock(fetchMock, () => meRoute.GET(request));

  assert.equal(response.status, 401);
  assert.match(response.headers.get("set-cookie") ?? "", /taskfloww_session=/);
  assert.match(response.headers.get("set-cookie") ?? "", /Max-Age=0/i);
  assert.equal((await response.text()).includes(TEST_TOKEN), false);
});

test("logout limpa o cookie sem chamar o backend", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  const response = await logoutRoute.POST(
    mutationRequest("/api/auth/logout"),
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { success: true });
  assert.match(response.headers.get("set-cookie") ?? "", /Max-Age=0/i);
});

test("alteração de senha envia Bearer e não expõe credenciais", async () => {
  setValidAuthEnvironment();
  delete process.env.AUTH_DEFAULT_EMPRESA_CODIGO;
  let authorization = "";
  let sentBody = "";
  const fetchMock: typeof fetch = async (_input, init) => {
    authorization = new Headers(init?.headers).get("authorization") ?? "";
    sentBody = String(init?.body);
    return new Response(null, { status: 204 });
  };
  const request = mutationRequest("/api/auth/alterar-senha", {
    senhaAtual: "old-password",
    novaSenha: "new-password",
    confirmacaoSenha: "new-password",
  });
  request.cookies.set("taskfloww_session", TEST_TOKEN);

  const response = await withFetchMock(fetchMock, () =>
    changePasswordRoute.POST(request),
  );

  assert.equal(response.status, 204);
  assert.equal(authorization, `Bearer ${TEST_TOKEN}`);
  assert.match(sentBody, /"senhaAtual":"old-password"/);
  assert.equal(await response.text(), "");
  assert.equal(response.headers.has("set-cookie"), false);
});
