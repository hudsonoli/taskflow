import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const usuariosRoot = path.join(
  process.cwd(),
  "src",
  "components",
  "usuarios",
);

async function usuarioSource(fileName: string) {
  return readFile(path.join(usuariosRoot, fileName), "utf8");
}

test("formulário de criação contém somente o contrato remoto aprovado", async () => {
  const form = await usuarioSource("UsuarioCreateForm.tsx");

  for (const field of [
    "codigoInterno",
    "nome",
    "email",
    "perfilBase",
    "acessoSistema",
  ]) {
    assert.match(form, new RegExp(`name="${field}"`));
  }

  for (const perfil of ["admin", "gestor", "operador"]) {
    assert.match(form, new RegExp(`value: "${perfil}"`));
  }

  assert.doesNotMatch(
    form,
    /empresaId|status|departamento|equipe|permiss|senha|UsuarioDraft|mock/i,
  );
});

test("hook de criação controla somente a mutação remota", async () => {
  const hook = await usuarioSource("useUsuarioCreate.ts");

  assert.match(hook, /usuariosBrowserClient\.criarUsuario\(payload\)/);
  assert.match(hook, /if \(submittingRef\.current\) return false/);
  assert.match(hook, /if \(!mountedRef\.current\) return false/);
  assert.match(hook, /submit,/);
  assert.match(hook, /status: state\.status/);
  assert.match(hook, /error: state\.error/);
  assert.match(hook, /reset,/);
  assert.doesNotMatch(hook, /status: "success"/);
  assert.doesNotMatch(
    hook,
    /EntityDrawer|refreshUsuarios|useUsuariosList|onClose|setDrawerState/,
  );
});

test("UsuariosView mantém criação e Peek exclusivos e refaz a lista", async () => {
  const view = await usuarioSource("UsuariosView.tsx");

  assert.match(view, /type UsuarioDrawerState/);
  assert.match(view, /\{ mode: "closed" \}/);
  assert.match(view, /\{ mode: "peek"; usuarioId: string \}/);
  assert.match(view, /\{ mode: "create" \}/);
  assert.match(view, /const refreshUsuarios = retry/);
  assert.match(view, /refreshUsuarios\(\)/);
  assert.match(view, /formRef\.current\?\.reportValidity\(\)/);
  assert.ok(
    view.indexOf("formRef.current?.reportValidity()") <
      view.indexOf("await submit(value)"),
  );
  assert.match(view, /mode="edit"/);
  assert.match(view, /title="Novo Usuário"/);
  assert.match(view, /onClick=\{\(\) => setDrawerState\(\{ mode: "create" \}\)\}/);
  assert.match(view, /label: "Editar"[\s\S]*?disabled: true/);
  assert.match(view, /<UsuarioPeekDrawer/);
  assert.match(view, /<UsuarioCreateDrawer/);
  assert.doesNotMatch(view, /usuario-mock|UsuarioDraft|useUsuarioDraft/);
});
