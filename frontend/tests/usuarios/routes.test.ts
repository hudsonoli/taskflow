import assert from "node:assert/strict";
import test from "node:test";
import {
  CURRENT_USER,
  setValidAuthEnvironment,
  TEST_TOKEN,
} from "../auth/helpers.mjs";

const { NextRequest } = await import("next/server");
const listRoute = await import("../../src/app/api/usuarios/route");
const detailRoute = await import(
  "../../src/app/api/usuarios/[usuarioId]/route"
);

const originalFetch = globalThis.fetch;

function usuarioApi() {
  return {
    id: "33333333-3333-3333-3333-333333333333",
    empresaId: CURRENT_USER.empresaId,
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "operador",
    acessoSistema: true,
    status: "ativo",
    createdAt: "2026-07-18T12:00:00Z",
    updatedAt: "2026-07-18T12:00:00Z",
    inativadoAt: null,
    inativadoPorUsuarioId: null,
    motivoInativacao: null,
  };
}

function authenticatedRequest(path: string) {
  return new NextRequest(`http://localhost:3010${path}`, {
    headers: { cookie: `taskfloww_session=${TEST_TOKEN}` },
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

test("lista resolve empresa pela sessão e não a expõe ao browser", async () => {
  setValidAuthEnvironment();
  const calls: Array<{ url: string; authorization: string }> = [];
  const fetchMock: typeof fetch = async (input, init) => {
    calls.push({
      url: String(input),
      authorization:
        new Headers(init?.headers).get("authorization") ?? "",
    });
    return calls.length === 1
      ? Response.json(CURRENT_USER)
      : Response.json([usuarioApi()]);
  };

  const response = await withFetchMock(fetchMock, () =>
    listRoute.GET(
      authenticatedRequest(
        "/api/usuarios?status=ativo&perfilBase=operador&limit=20&offset=0",
      ),
    ),
  );
  const body = await response.json();
  const backendUrl = new URL(calls[1].url);

  assert.equal(response.status, 200);
  assert.equal(calls.length, 2);
  assert.equal(backendUrl.pathname, "/usuarios");
  assert.equal(
    backendUrl.searchParams.get("empresaId"),
    CURRENT_USER.empresaId,
  );
  assert.equal(calls[1].authorization, `Bearer ${TEST_TOKEN}`);
  assert.equal(JSON.stringify(body).includes(CURRENT_USER.empresaId), false);
  assert.equal(JSON.stringify(body).includes(TEST_TOKEN), false);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("empresaId enviado pelo browser é recusado e não chega à listagem", async () => {
  setValidAuthEnvironment();
  let calls = 0;
  const fetchMock: typeof fetch = async () => {
    calls += 1;
    return Response.json(CURRENT_USER);
  };

  const response = await withFetchMock(fetchMock, () =>
    listRoute.GET(
      authenticatedRequest("/api/usuarios?empresaId=empresa-injetada"),
    ),
  );
  const body = await response.json();

  assert.equal(response.status, 400);
  assert.equal(calls, 1);
  assert.equal(JSON.stringify(body).includes("empresa-injetada"), false);
});

test("sem sessão retorna 401 sem acessar o FastAPI", async () => {
  setValidAuthEnvironment();
  let called = false;
  const response = await withFetchMock(
    async () => {
      called = true;
      return Response.json({});
    },
    () =>
      listRoute.GET(
        new NextRequest("http://localhost:3010/api/usuarios"),
      ),
  );

  assert.equal(response.status, 401);
  assert.equal(called, false);
});

test("detalhe usa rota interna e devolve envelope data sem empresa", async () => {
  setValidAuthEnvironment();
  const urls: string[] = [];
  const fetchMock: typeof fetch = async (input) => {
    urls.push(String(input));
    return urls.length === 1
      ? Response.json(CURRENT_USER)
      : Response.json(usuarioApi());
  };

  const response = await withFetchMock(fetchMock, () =>
    detailRoute.GET(
      authenticatedRequest(`/api/usuarios/${usuarioApi().id}`),
      { params: Promise.resolve({ usuarioId: usuarioApi().id }) },
    ),
  );
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(new URL(urls[1]).pathname, `/usuarios/${usuarioApi().id}`);
  assert.equal(body.data.id, usuarioApi().id);
  assert.equal("empresaId" in body.data, false);
});

test("normaliza 403 e 404 do FastAPI sem propagar detail", async () => {
  setValidAuthEnvironment();

  for (const [status, code] of [
    [403, "FORBIDDEN"],
    [404, "NOT_FOUND"],
  ] as const) {
    let call = 0;
    const response = await withFetchMock(
      async () => {
        call += 1;
        return call === 1
          ? Response.json(CURRENT_USER)
          : Response.json({ detail: "detalhe interno" }, { status });
      },
      () =>
        detailRoute.GET(
          authenticatedRequest("/api/usuarios/id"),
          { params: Promise.resolve({ usuarioId: "id" }) },
        ),
    );
    const body = await response.json();

    assert.equal(response.status, status);
    assert.equal(body.error.code, code);
    assert.equal(JSON.stringify(body).includes("detalhe interno"), false);
  }
});
