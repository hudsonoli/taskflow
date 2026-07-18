import assert from "node:assert/strict";
import test from "node:test";
import type { AuthCurrentUser } from "../../src/types/auth";
import { CURRENT_USER } from "./helpers.mjs";

const typedCurrentUser = CURRENT_USER as AuthCurrentUser;

const { adaptCurrentUser } = await import(
  "../../src/lib/auth/current-user-adapter"
);

test("adapta somente o contrato mínimo de apresentação", () => {
  assert.deepEqual(adaptCurrentUser(typedCurrentUser), {
    id: CURRENT_USER.usuarioId,
    nome: CURRENT_USER.nome,
    perfilBase: "admin",
    perfilLabel: "Administrador",
  });
});

test("mapeia labels sem inventar dados de perfil", () => {
  const labels = [
    ["admin", "Administrador"],
    ["gestor", "Gestor"],
    ["operador", "Operador"],
  ] as const;

  for (const [perfilBase, perfilLabel] of labels) {
    const adapted = adaptCurrentUser({ ...typedCurrentUser, perfilBase });
    assert.equal(adapted.perfilLabel, perfilLabel);
    assert.equal("telefone" in adapted, false);
    assert.equal("cargo" in adapted, false);
    assert.equal("departamento" in adapted, false);
    assert.equal("preferencias" in adapted, false);
    assert.equal("ultimoAcesso" in adapted, false);
  }
});
