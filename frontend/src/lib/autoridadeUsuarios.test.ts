// Fase 1A — autoridade tenant sobre Usuários na UI: rótulo "Usuário", perfis oferecidos por ator, ações visíveis.
// `npm run test:rbac` (node --test, sem dependências). Lógica pura em `autoridadeUsuarios.ts`; as telas são lidas
// como texto (são .tsx com alias `@/`, que o node --test não resolve) para provar que usam a lógica e não
// reintroduzem as opções antigas.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  opcoesDePerfil,
  perfilTecnico,
  perfisAtribuiveis,
  podeAdministrarAlvo,
  podeCriarUsuario,
  podeEditarUsuario,
  podeGerenciarPermissoesDe,
  podeSuspenderUsuario,
} from "./autoridadeUsuarios.ts";
import { PERFIL_PARA_PERFIL_BASE, perfilUsuarioLabels } from "../types/usuario.ts";
import type { PerfilUsuario } from "../types/usuario.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");

const PERMISSOES_GESTOR = ["usuarios.visualizar", "usuarios.criar", "usuarios.editar", "usuarios.suspender", "permissoes.gerenciar"];
const admin = { id: "a", perfil: "admin" as PerfilUsuario, permissoes: PERMISSOES_GESTOR };
const gestor = { id: "g", perfil: "gestor" as PerfilUsuario, permissoes: PERMISSOES_GESTOR };
const usuarioComum = { id: "u", perfil: "operador" as PerfilUsuario, permissoes: ["demandas.visualizar"] };
const alvoUsuario = { id: "u2", perfil: "operador" as PerfilUsuario };
const alvoGestor = { id: "g2", perfil: "gestor" as PerfilUsuario };
const alvoAdmin = { id: "a2", perfil: "admin" as PerfilUsuario };

test('"operador" é exibido como "Usuário"; o valor técnico não muda', () => {
  assert.equal(perfilUsuarioLabels.operador, "Usuário");
  assert.equal(perfilUsuarioLabels.gestor, "Gestor");
  assert.equal(PERFIL_PARA_PERFIL_BASE.operador, "operador");
  assert.equal(perfilTecnico("operador"), "operador");
});

test("o rótulo central chega a todas as telas que o usam (Minha Conta, menu do perfil, tabela, formulário)", () => {
  for (const arquivo of [
    "components/conta/MinhaContaView.tsx",
    "components/layout/ProfileMenu.tsx",
    "components/usuarios/UsuariosTable.tsx",
    "components/usuarios/UsuarioFormModal.tsx",
  ]) {
    assert.match(ler(arquivo), /perfilUsuarioLabels/, `${arquivo} deveria usar o rótulo central`);
  }
  // Nenhuma tela escreve o texto antigo à mão.
  for (const arquivo of ["components/usuarios/UsuarioFormModal.tsx", "components/usuarios/UsuariosTable.tsx", "components/conta/MinhaContaView.tsx"]) {
    assert.doesNotMatch(ler(arquivo), /["'>]Operador["'<]/);
  }
});

test("formulário: admin legado oferece Gestor e Usuário; Gestor oferece só Usuário; nunca Admin", () => {
  assert.deepEqual(opcoesDePerfil(admin), [
    { value: "gestor", label: "Gestor" },
    { value: "operador", label: "Usuário" },
  ]);
  assert.deepEqual(opcoesDePerfil(gestor), [{ value: "operador", label: "Usuário" }]);
  assert.deepEqual(opcoesDePerfil(usuarioComum), [{ value: "operador", label: "Usuário" }]);
  for (const ator of [admin, gestor, usuarioComum]) {
    assert.ok(!perfisAtribuiveis(ator).includes("admin"));
  }
});

test("o seletor não oferece mais SuperAdmin, Admin, Diretoria, Financeiro, Operador nem Cliente", () => {
  const rotulos = [...opcoesDePerfil(admin), ...opcoesDePerfil(gestor)].map((o) => o.label);
  for (const antigo of ["SuperAdmin", "Admin", "Diretoria", "Financeiro", "Operador", "Cliente"]) {
    assert.ok(!rotulos.includes(antigo), `${antigo} não deveria ser oferecido`);
  }
  const modal = ler("components/usuarios/UsuarioFormModal.tsx");
  assert.match(modal, /opcoesDePerfil\(/);
  assert.doesNotMatch(modal, /Object\.entries\(perfilUsuarioLabels\)/);
  assert.doesNotMatch(modal, /Nesta fase, o backend só tem 3 níveis/);
});

test('botão "Nova pessoa": só com usuarios.criar na sessão (fail-closed sem permissões)', () => {
  assert.equal(podeCriarUsuario(gestor), true);
  assert.equal(podeCriarUsuario(admin), true);
  assert.equal(podeCriarUsuario(usuarioComum), false);
  assert.equal(podeCriarUsuario({}), false); // sessão ainda sem permissões
  const toolbar = ler("components/usuarios/UsuariosToolbar.tsx");
  assert.match(toolbar, /podeCriar && \(\s*<Button onClick=\{onNewUsuario\}/);
  assert.match(ler("components/usuarios/UsuariosView.tsx"), /podeCriarUsuario\(usuarioAtual\)/);
});

test("ações de linha: o Gestor só age sobre Usuário; nunca sobre Gestor, admin legado ou ele mesmo", () => {
  assert.equal(podeEditarUsuario(gestor, alvoUsuario), true);
  assert.equal(podeSuspenderUsuario(gestor, alvoUsuario), true);
  for (const alvo of [alvoGestor, alvoAdmin]) {
    assert.equal(podeEditarUsuario(gestor, alvo), false);
    assert.equal(podeSuspenderUsuario(gestor, alvo), false);
    assert.equal(podeGerenciarPermissoesDe(gestor, alvo), false);
  }
  // si mesmo
  assert.equal(podeSuspenderUsuario(gestor, { id: "g", perfil: "gestor" }), false);
  assert.equal(podeGerenciarPermissoesDe(gestor, { id: "g", perfil: "gestor" }), false);
  // admin legado administra Gestor e Usuário
  assert.equal(podeAdministrarAlvo(admin, alvoGestor), true);
  assert.equal(podeEditarUsuario(admin, alvoGestor), true);
  assert.equal(podeSuspenderUsuario(admin, alvoUsuario), true);
  assert.equal(podeSuspenderUsuario(admin, { id: "a", perfil: "admin" }), false); // nunca a si mesmo
  // Usuário comum sem concessão não administra nada
  assert.equal(podeEditarUsuario(usuarioComum, alvoUsuario), false);
  assert.equal(podeSuspenderUsuario(usuarioComum, alvoUsuario), false);
  const tabela = ler("components/usuarios/UsuariosTable.tsx");
  assert.match(tabela, /podeEditar\(usuario\) &&/);
  assert.match(tabela, /podeExcluir\(usuario\) &&/);
});

test("permissões individuais: área liberada ao Gestor, mas só sobre Usuários", () => {
  assert.equal(podeGerenciarPermissoesDe(gestor, alvoUsuario), true);
  assert.equal(podeGerenciarPermissoesDe(usuarioComum, alvoUsuario), false);
  // `podeGerenciarPermissoes` (menu/área) já não exige perfil admin — mesmo piso do backend: admin legado ou Gestor.
  const escopo = ler("lib/escopo-operacional.ts");
  assert.match(escopo, /PERFIL_PARA_PERFIL_BASE\[usuario\.perfil\] !== "operador" && \(usuario\.permissoes\?\.includes\("permissoes\.gerenciar"\)/);
  // O seletor da tela só oferece Usuários a quem não é admin legado.
  const tela = ler("components/permissoes/PermissoesUsuarioView.tsx");
  assert.match(tela, /perfilBase: "operador"/);
});

test("o PATCH só leva perfilBase quando o perfil mudou (admin legado nunca é reenviado)", () => {
  const api = ler("lib/api-backend.ts");
  assert.match(api, /perfilBaseAnterior !== undefined && perfilBaseAnterior === perfilBase \? resto : \{ perfilBase, \.\.\.resto \}/);
  assert.match(ler("components/usuarios/UsuariosView.tsx"), /perfilTecnico\(anterior\.perfil\)/);
});
