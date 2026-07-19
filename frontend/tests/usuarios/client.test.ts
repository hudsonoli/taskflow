import assert from "node:assert/strict";
import test from "node:test";
import "../auth/helpers.mjs";

const { createUsuariosBrowserClient } = await import(
  "../../src/lib/api/usuarios-client"
);

function usuarioDomain() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "admin",
    perfilLabel: "Administrador",
    acessoSistema: true,
    status: "ativo",
    statusLabel: "Ativo",
    createdAt: "2026-07-18T12:00:00Z",
    updatedAt: "2026-07-18T12:00:00Z",
    inativadoAt: null,
    inativadoPorUsuarioId: null,
    motivoInativacao: null,
  };
}

test("listarUsuarios usa somente BFF same-origin e nunca envia empresaId", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const client = createUsuariosBrowserClient(async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json({ items: [usuarioDomain()] });
  });

  const result = await client.listarUsuarios({
    status: "ativo",
    perfilBase: "admin",
    search: "Usuário",
    limit: 20,
    offset: 0,
  });
  const url = new URL(capturedUrl, "http://local");

  assert.equal(url.pathname, "/api/usuarios");
  assert.equal(url.searchParams.has("empresaId"), false);
  assert.equal(capturedInit?.credentials, "same-origin");
  assert.equal(capturedInit?.cache, "no-store");
  assert.equal(new Headers(capturedInit?.headers).has("authorization"), false);
  assert.equal(result.ok, true);
});

test("obterUsuario codifica o ID e valida o envelope de detalhe", async () => {
  let capturedUrl = "";
  const client = createUsuariosBrowserClient(async (input) => {
    capturedUrl = String(input);
    return Response.json({ data: usuarioDomain() });
  });

  const result = await client.obterUsuario("usuario com espaço");

  assert.equal(capturedUrl, "/api/usuarios/usuario%20com%20espa%C3%A7o");
  assert.equal(result.ok, true);
});

test("criarUsuario envia somente o payload público ao BFF", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const client = createUsuariosBrowserClient(async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return Response.json({ data: usuarioDomain() }, { status: 201 });
  });
  const payload = {
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "admin" as const,
    acessoSistema: true,
  };

  const result = await client.criarUsuario(payload);
  const body = JSON.parse(String(capturedInit?.body));

  assert.equal(capturedUrl, "/api/usuarios");
  assert.equal(capturedInit?.method, "POST");
  assert.equal(capturedInit?.credentials, "same-origin");
  assert.equal(capturedInit?.cache, "no-store");
  assert.equal(
    new Headers(capturedInit?.headers).get("content-type"),
    "application/json",
  );
  assert.equal(new Headers(capturedInit?.headers).has("authorization"), false);
  assert.deepEqual(body, payload);
  assert.equal("empresaId" in body, false);
  assert.equal(result.ok, true);
});

test("criarUsuario preserva conflito seguro do BFF", async () => {
  const client = createUsuariosBrowserClient(async () =>
    Response.json(
      {
        error: {
          code: "CONFLICT",
          message: "Já existe um usuário com os dados informados.",
        },
      },
      { status: 409 },
    ),
  );

  const result = await client.criarUsuario({
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "admin",
  });

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.error.error.code, "CONFLICT");
  }
});

test("aceita lista vazia e normaliza 401, 403 e 404", async () => {
  const empty = createUsuariosBrowserClient(async () =>
    Response.json({ items: [] }),
  );
  assert.deepEqual(await empty.listarUsuarios(), {
    ok: true,
    data: { items: [] },
  });

  for (const [status, code] of [
    [401, "UNAUTHENTICATED"],
    [403, "FORBIDDEN"],
    [404, "NOT_FOUND"],
  ] as const) {
    const client = createUsuariosBrowserClient(async () =>
      Response.json(
        { error: { code, message: "Mensagem segura." } },
        { status },
      ),
    );
    const result = await client.listarUsuarios();
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.error.error.code, code);
  }
});

test("payload e falha de rede são convertidos em erros seguros", async () => {
  const invalid = createUsuariosBrowserClient(async () =>
    Response.json({ items: [{ invalid: true }] }),
  );
  const unavailable = createUsuariosBrowserClient(async () => {
    throw new Error("http://taskfloww_api:8000 secret-token");
  });

  const invalidResult = await invalid.listarUsuarios();
  const unavailableResult = await unavailable.listarUsuarios();
  const serialized = JSON.stringify([invalidResult, unavailableResult]);

  assert.equal(invalidResult.ok, false);
  assert.equal(unavailableResult.ok, false);
  assert.equal(serialized.includes("taskfloww_api"), false);
  assert.equal(serialized.includes("secret-token"), false);
});
