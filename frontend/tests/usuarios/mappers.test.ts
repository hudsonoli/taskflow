import assert from "node:assert/strict";
import test from "node:test";
import "../auth/helpers.mjs";

const {
  mapUsuarioApiListToResult,
  mapUsuarioApiResponseToDomain,
  parseUsuarioDetailResult,
  parseUsuarioListResult,
} = await import("../../src/lib/usuario-api-mappers");

const EMPRESA_ID = "22222222-2222-2222-2222-222222222222";

function usuarioApi(overrides: Record<string, unknown> = {}) {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    empresaId: EMPRESA_ID,
    codigoInterno: "USR-001",
    nome: "Usuário Teste",
    email: "usuario@example.com",
    perfilBase: "admin",
    acessoSistema: true,
    status: "ativo",
    createdAt: "2026-07-18T12:00:00Z",
    updatedAt: "2026-07-18T12:00:00Z",
    inativadoAt: null,
    inativadoPorUsuarioId: null,
    motivoInativacao: null,
    ...overrides,
  };
}

test("mapeia o contrato real para o domínio sem expor empresaId", () => {
  const mapped = mapUsuarioApiResponseToDomain(usuarioApi(), EMPRESA_ID);

  assert.equal(mapped.perfilLabel, "Administrador");
  assert.equal(mapped.statusLabel, "Ativo");
  assert.equal("empresaId" in mapped, false);
  assert.equal("telefone" in mapped, false);
  assert.equal("cargo" in mapped, false);
});

test("mapeia lista vazia para resultado evolutivo", () => {
  assert.deepEqual(mapUsuarioApiListToResult([], EMPRESA_ID), { items: [] });
});

test("preserva campos opcionais nulos e valida a empresa da sessão", () => {
  const mapped = mapUsuarioApiResponseToDomain(
    usuarioApi({
      status: "inativo",
      inativadoAt: "2026-07-18T13:00:00Z",
      inativadoPorUsuarioId: null,
      motivoInativacao: "Desligamento",
    }),
    EMPRESA_ID,
  );

  assert.equal(mapped.statusLabel, "Inativo");
  assert.equal(mapped.motivoInativacao, "Desligamento");
  assert.throws(
    () => mapUsuarioApiResponseToDomain(usuarioApi(), "outra-empresa"),
    /Empresa divergente/,
  );
});

test("rejeita payload incompleto e enums inválidos", () => {
  assert.throws(
    () =>
      mapUsuarioApiResponseToDomain(
        usuarioApi({ perfilBase: "owner" }),
        EMPRESA_ID,
      ),
    /Contrato de usuário inválido/,
  );
  assert.throws(
    () =>
      mapUsuarioApiResponseToDomain(
        usuarioApi({ status: "suspenso" }),
        EMPRESA_ID,
      ),
    /Contrato de usuário inválido/,
  );
  const withoutEmail: Record<string, unknown> = usuarioApi();
  delete withoutEmail.email;
  assert.throws(
    () => mapUsuarioApiResponseToDomain(withoutEmail, EMPRESA_ID),
    /Contrato de usuário inválido/,
  );
});

test("valida os envelopes entregues pelo BFF", () => {
  const usuario = mapUsuarioApiResponseToDomain(usuarioApi(), EMPRESA_ID);

  assert.deepEqual(parseUsuarioListResult({ items: [usuario] }), {
    items: [usuario],
  });
  assert.deepEqual(parseUsuarioDetailResult({ data: usuario }), {
    data: usuario,
  });
  assert.throws(() => parseUsuarioListResult({ data: [] }));
  assert.throws(() =>
    parseUsuarioDetailResult({ data: { ...usuario, empresaId: EMPRESA_ID } }),
  );
});
