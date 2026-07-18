import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const sourceRoot = path.join(process.cwd(), "src");

async function source(...segments: string[]) {
  return readFile(path.join(sourceRoot, ...segments), "utf8");
}

test("layout instala AuthProvider sem proteção ou redirect", async () => {
  const layout = await source("app", "layout.tsx");
  assert.match(layout, /<AuthProvider>/);
  assert.match(layout, /<Shell>\{children\}<\/Shell>/);
  assert.doesNotMatch(layout, /RequireAuth|redirect\(/);
});

test("UserMenu usa identidade real mínima e logout do Provider", async () => {
  const menu = await source("components", "layout", "UserMenu.tsx");
  assert.match(menu, /useAuth\(\)/);
  assert.match(menu, /adaptCurrentUser\(user\)/);
  assert.match(menu, /getCurrentUserInitials\(displayName\)/);
  assert.match(menu, /await logout\(\)/);
  assert.match(menu, /currentUser\.avatarThumbnail/);
  assert.match(menu, /currentUser\.departamento/);
});

test("Dashboard migra somente o nome da saudação", async () => {
  const dashboard = await source(
    "components",
    "dashboard",
    "useDashboardData.ts",
  );
  assert.match(dashboard, /const \{ user \} = useAuth\(\)/);
  assert.match(dashboard, /currentUserNome: user\?\.nome \?\? currentUser\.nome/);
  assert.match(dashboard, /dashboardKpisMock/);
});

test("alteração de senha atualiza auth em 401 e não recarrega em 204", async () => {
  const password = await source(
    "components",
    "conta",
    "AlterarSenhaView.tsx",
  );
  assert.match(password, /fetch\("\/api\/auth\/alterar-senha"/);
  assert.match(password, /response\.status === 401/);
  assert.match(password, /await refresh\(\)/);
  assert.match(password, /response\.status !== 204/);
  assert.equal((password.match(/await refresh\(\)/g) ?? []).length, 1);
  assert.doesNotMatch(password, /Authorization|Bearer|redirect\(/);
});
