import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const frontendRoot = process.cwd();
const sourceRoot = path.join(frontendRoot, "src");
const authRoot = path.join(sourceRoot, "lib", "auth");
const serverOnlyModules = [
  "backend.ts",
  "config.ts",
  "session.ts",
  "origin.ts",
  "errors.ts",
];

async function sourceFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return sourceFiles(target);
      }
      return /\.(ts|tsx)$/.test(entry.name) ? [target] : [];
    }),
  );
  return nested.flat();
}

test("módulos sensíveis possuem marcador server-only", async () => {
  for (const file of serverOnlyModules) {
    const content = await readFile(path.join(authRoot, file), "utf8");
    assert.match(content, /^import "server-only";/);
  }
});

test("session centraliza o nome do cookie no helper compartilhado", async () => {
  const session = await readFile(path.join(authRoot, "session.ts"), "utf8");

  assert.match(session, /import \{ getSessionCookieName \} from "\.\/cookie"/);
  assert.match(session, /name: getSessionCookieName\(config\.production\)/);
  assert.doesNotMatch(session, /taskfloww_session|__Host-taskfloww_session/);
});

test("componentes client-side não importam módulos server-only", async () => {
  const violations: string[] = [];
  for (const file of await sourceFiles(sourceRoot)) {
    const content = await readFile(file, "utf8");
    if (
      /^(["'])use client\1;/m.test(content) &&
      /lib\/auth\/(backend|config|session|origin|errors)/.test(content)
    ) {
      violations.push(path.relative(frontendRoot, file));
    }
  }
  assert.deepEqual(violations, []);
});

test("infraestrutura auth não usa storage do navegador nem segredo JWT", async () => {
  const contents = await Promise.all(
    (await sourceFiles(path.join(sourceRoot, "lib", "auth"))).map((file) =>
      readFile(file, "utf8"),
    ),
  );
  const combined = contents.join("\n");

  assert.equal(combined.includes("localStorage"), false);
  assert.equal(combined.includes("sessionStorage"), false);
  assert.equal(combined.includes("AUTH_SECRET_KEY"), false);
});

test("Route Handler de login não serializa resposta com accessToken", async () => {
  const route = await readFile(
    path.join(sourceRoot, "app", "api", "auth", "login", "route.ts"),
    "utf8",
  );
  assert.match(route, /NextResponse\.json\(currentUser\)/);
  assert.doesNotMatch(route, /NextResponse\.json\([^)]*accessToken/);
  assert.doesNotMatch(route, /NextResponse\.json\(login\)/);
});

test("infraestrutura client auth não expõe JWT nem depende de infraestrutura", async () => {
  const clientFiles = [
    path.join(sourceRoot, "lib", "auth", "client.ts"),
    path.join(sourceRoot, "lib", "auth", "current-user-adapter.ts"),
    path.join(sourceRoot, "types", "session.ts"),
    ...(await sourceFiles(path.join(sourceRoot, "components", "auth"))),
  ];
  const combined = (
    await Promise.all(clientFiles.map((file) => readFile(file, "utf8")))
  ).join("\n");

  for (const forbidden of [
    "localStorage",
    "sessionStorage",
    "accessToken",
    "Authorization",
    "Bearer ",
    "TASKFLOWW_API_INTERNAL_URL",
    "X-Forwarded-Host",
    "X-Forwarded-Proto",
    "CF-IP",
  ]) {
    assert.equal(combined.includes(forbidden), false, forbidden);
  }
  assert.doesNotMatch(combined, /https?:\/\//);
});

test("cliente browser usa somente endpoints BFF permitidos", async () => {
  const client = await readFile(
    path.join(sourceRoot, "lib", "auth", "client.ts"),
    "utf8",
  );
  const endpoints = [...client.matchAll(/["'](\/api\/auth\/[^"']+)["']/g)].map(
    (match) => match[1],
  );

  assert.deepEqual(endpoints.sort(), ["/api/auth/logout", "/api/auth/me"]);
});

test("estado e Context client-side não contêm token", async () => {
  const state = await readFile(
    path.join(sourceRoot, "types", "session.ts"),
    "utf8",
  );
  const context = await readFile(
    path.join(sourceRoot, "components", "auth", "AuthContext.ts"),
    "utf8",
  );

  assert.doesNotMatch(state, /token|accessToken|jwt/i);
  assert.doesNotMatch(context, /token|accessToken|jwt/i);
});
