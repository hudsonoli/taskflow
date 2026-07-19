import assert from "node:assert/strict";
import test from "node:test";
import { makeConfig, TEST_TOKEN } from "../auth/helpers.mjs";

const { BackendApiClient } = await import("../../src/lib/api/backend");
const { ApiBffError } = await import("../../src/lib/api/errors");
const {
  UsuariosApi,
  parseUsuarioCreatePayload,
  parseUsuarioListFilters,
  parseUsuarioUpdatePayload,
} = await import("../../src/lib/api/usuarios");

const EMPRESA_ID = "22222222-2222-2222-2222-222222222222";

function usuarioApi() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    empresaId: EMPRESA_ID,
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "gestor",
    acessoSistema: true,
    status: "ativo",
    createdAt: "2026-07-18T12:00:00Z",
    updatedAt: "2026-07-18T12:00:00Z",
    inativadoAt: null,
    inativadoPorUsuarioId: null,
    motivoInativacao: null,
  };
}

test("cliente server-only encaminha Bearer e usa no-store", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json([]);
  };

  await new BackendApiClient(makeConfig(), fetchMock).getJson(
    "/usuarios?empresaId=empresa",
    TEST_TOKEN,
  );

  assert.equal(
    capturedUrl,
    "http://taskfloww_api:8000/usuarios?empresaId=empresa",
  );
  assert.equal(capturedInit?.cache, "no-store");
  assert.equal(
    new Headers(capturedInit?.headers).get("authorization"),
    `Bearer ${TEST_TOKEN}`,
  );
});

test("cliente server-only envia POST com JSON, Bearer e no-store", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json(usuarioApi(), { status: 201 });
  };
  const payload = { nome: "Usuário Teste" };

  await new BackendApiClient(makeConfig(), fetchMock).postJson(
    "/usuarios",
    TEST_TOKEN,
    payload,
  );

  assert.equal(capturedUrl, "http://taskfloww_api:8000/usuarios");
  assert.equal(capturedInit?.method, "POST");
  assert.equal(capturedInit?.cache, "no-store");
  assert.equal(
    new Headers(capturedInit?.headers).get("content-type"),
    "application/json",
  );
  assert.equal(
    new Headers(capturedInit?.headers).get("authorization"),
    `Bearer ${TEST_TOKEN}`,
  );
  assert.deepEqual(JSON.parse(String(capturedInit?.body)), payload);
});

test("cliente server-only envia PATCH com JSON, Bearer e no-store", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json(usuarioApi());
  };
  const payload = { nome: "Nome atualizado" };

  await new BackendApiClient(makeConfig(), fetchMock).patchJson(
    "/usuarios/usuario-id",
    TEST_TOKEN,
    payload,
  );

  assert.equal(
    capturedUrl,
    "http://taskfloww_api:8000/usuarios/usuario-id",
  );
  assert.equal(capturedInit?.method, "PATCH");
  assert.equal(capturedInit?.cache, "no-store");
  assert.equal(
    new Headers(capturedInit?.headers).get("content-type"),
    "application/json",
  );
  assert.equal(
    new Headers(capturedInit?.headers).get("authorization"),
    `Bearer ${TEST_TOKEN}`,
  );
  assert.deepEqual(JSON.parse(String(capturedInit?.body)), payload);
});

test("UsuariosApi cria com empresaId da sessão e mapeia a resposta", async () => {
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (_input, init) => {
    capturedInit = init;
    return Response.json(usuarioApi(), { status: 201 });
  };
  const api = new UsuariosApi(new BackendApiClient(makeConfig(), fetchMock));

  const result = await api.criar(TEST_TOKEN, EMPRESA_ID, {
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "gestor",
    acessoSistema: true,
  });
  const body = JSON.parse(String(capturedInit?.body));

  assert.equal(body.empresaId, EMPRESA_ID);
  assert.equal(body.codigoInterno, "USR-001");
  assert.equal(result.id, usuarioApi().id);
  assert.equal("empresaId" in result, false);
});

test("UsuariosApi atualiza por ID e valida a empresa da resposta", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetchMock: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json({
      ...usuarioApi(),
      nome: "Nome atualizado",
    });
  };
  const api = new UsuariosApi(new BackendApiClient(makeConfig(), fetchMock));

  const result = await api.atualizar(
    TEST_TOKEN,
    EMPRESA_ID,
    "usuario com espaço",
    { nome: "Nome atualizado" },
  );

  assert.equal(
    capturedUrl,
    "http://taskfloww_api:8000/usuarios/usuario%20com%20espa%C3%A7o",
  );
  assert.equal(capturedInit?.method, "PATCH");
  assert.deepEqual(JSON.parse(String(capturedInit?.body)), {
    nome: "Nome atualizado",
  });
  assert.equal(result.nome, "Nome atualizado");
  assert.equal("empresaId" in result, false);
});

test("UsuariosApi injeta empresaId da sessão e preserva filtros reais", async () => {
  let capturedUrl = "";
  const fetchMock: typeof fetch = async (input) => {
    capturedUrl = String(input);
    return Response.json([usuarioApi()]);
  };
  const api = new UsuariosApi(new BackendApiClient(makeConfig(), fetchMock));

  const result = await api.listar(TEST_TOKEN, EMPRESA_ID, {
    status: "ativo",
    perfilBase: "gestor",
    search: "Teste",
    limit: 25,
    offset: 50,
  });
  const url = new URL(capturedUrl);

  assert.equal(url.pathname, "/usuarios");
  assert.equal(url.searchParams.get("empresaId"), EMPRESA_ID);
  assert.equal(url.searchParams.get("status"), "ativo");
  assert.equal(url.searchParams.get("perfilBase"), "gestor");
  assert.equal(url.searchParams.get("search"), "Teste");
  assert.equal(url.searchParams.get("limit"), "25");
  assert.equal(url.searchParams.get("offset"), "50");
  assert.equal("empresaId" in result.items[0], false);
});

test("parser de criação aceita somente o contrato público", () => {
  assert.deepEqual(
    parseUsuarioCreatePayload({
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "  usuario@example.com  ",
      perfilBase: "operador",
    }),
    {
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "usuario@example.com",
      perfilBase: "operador",
    },
  );

  for (const body of [
    {
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "   ",
      perfilBase: "operador",
    },
    {
      empresaId: EMPRESA_ID,
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "usuario@example.com",
      perfilBase: "operador",
    },
    {
      codigoInterno: "",
      nome: "Usuário Teste",
      email: "usuario@example.com",
      perfilBase: "operador",
    },
    {
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "usuario@example.com",
      perfilBase: "owner",
    },
    {
      codigoInterno: "USR-001",
      nome: "Usuário Teste",
      email: "usuario@example.com",
      perfilBase: "operador",
      acessoSistema: "sim",
    },
  ]) {
    assert.throws(
      () => parseUsuarioCreatePayload(body),
      (error: unknown) =>
        error instanceof ApiBffError &&
        error.status === 400 &&
        error.code === "INVALID_REQUEST",
    );
  }
});

test("parser de atualização aceita campos parciais e recusa campos externos", () => {
  assert.deepEqual(parseUsuarioUpdatePayload({}), {});
  assert.deepEqual(
    parseUsuarioUpdatePayload({
      nome: "Nome atualizado",
      email: "  atualizado@example.com  ",
      acessoSistema: false,
    }),
    {
      nome: "Nome atualizado",
      email: "atualizado@example.com",
      acessoSistema: false,
    },
  );

  for (const body of [
    { empresaId: EMPRESA_ID },
    { status: "inativo" },
    { perfilBase: "owner" },
    { acessoSistema: "não" },
    { email: "   " },
  ]) {
    assert.throws(
      () => parseUsuarioUpdatePayload(body),
      (error: unknown) =>
        error instanceof ApiBffError &&
        error.status === 400 &&
        error.code === "INVALID_REQUEST",
    );
  }
});

test("parser do BFF recusa empresaId e parâmetros inválidos do browser", () => {
  assert.throws(
    () => parseUsuarioListFilters(new URLSearchParams({ empresaId: "x" })),
    (error: unknown) =>
      error instanceof ApiBffError &&
      error.status === 400 &&
      error.code === "INVALID_REQUEST",
  );
  assert.throws(() =>
    parseUsuarioListFilters(new URLSearchParams({ perfilBase: "owner" })),
  );
  assert.throws(() =>
    parseUsuarioListFilters(new URLSearchParams({ limit: "201" })),
  );
});

test("mapeia erros do backend e resposta inválida sem expor detalhes", async () => {
  for (const [status, code] of [
    [401, "UNAUTHENTICATED"],
    [403, "FORBIDDEN"],
    [404, "NOT_FOUND"],
    [409, "CONFLICT"],
    [422, "VALIDATION_ERROR"],
  ] as const) {
    const client = new BackendApiClient(makeConfig(), async () =>
      Response.json({ detail: "segredo interno" }, { status }),
    );
    await assert.rejects(
      client.getJson("/usuarios", TEST_TOKEN),
      (error: unknown) =>
        error instanceof ApiBffError &&
        error.code === code &&
        !error.safeMessage.includes("segredo"),
    );
  }

  const invalid = new UsuariosApi(
    new BackendApiClient(makeConfig(), async () =>
      Response.json({ unexpected: true }),
    ),
  );
  await assert.rejects(
    invalid.listar(TEST_TOKEN, EMPRESA_ID, {}),
    (error: unknown) =>
      error instanceof ApiBffError &&
      error.code === "INVALID_BACKEND_RESPONSE",
  );
});
