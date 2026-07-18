import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import type { AuthCurrentUser } from "../../src/types/auth";
import type { AuthContextValue } from "../../src/types/session";
import { CURRENT_USER } from "./helpers.mjs";

const typedCurrentUser = CURRENT_USER as AuthCurrentUser;

const { authReducer, createAuthOperationSequence, initialAuthState } =
  await import("../../src/types/session");

test("estado inicial é loading sem usuário", () => {
  assert.deepEqual(initialAuthState, {
    status: "loading",
    user: null,
    error: null,
  });
});

test("reducer representa authenticated, unauthenticated e error", () => {
  const authenticated = authReducer(initialAuthState, {
    type: "authenticated",
    user: typedCurrentUser,
  });
  const unauthenticated = authReducer(authenticated, {
    type: "unauthenticated",
  });
  const errorResponse = {
    error: { code: "BACKEND_UNAVAILABLE", message: "Indisponível." },
  } as const;
  const failed = authReducer(unauthenticated, {
    type: "error",
    error: errorResponse,
  });

  assert.deepEqual(authenticated, {
    status: "authenticated",
    user: typedCurrentUser,
    error: null,
  });
  assert.deepEqual(unauthenticated, {
    status: "unauthenticated",
    user: null,
    error: null,
  });
  assert.deepEqual(failed, {
    status: "error",
    user: null,
    error: errorResponse,
  });
});

test("AuthContextValue preserva a correlação entre status e user", () => {
  function narrowedUser(value: AuthContextValue): AuthCurrentUser | null {
    if (value.status === "authenticated") {
      const user: AuthCurrentUser = value.user;
      return user;
    }

    const user: null = value.user;
    return user;
  }

  const actions = {
    refresh: async () => undefined,
    logout: async () => undefined,
  };

  assert.equal(
    narrowedUser({ status: "authenticated", user: typedCurrentUser, ...actions }),
    typedCurrentUser,
  );
  assert.equal(narrowedUser({ status: "loading", user: null, ...actions }), null);
});

test("somente a operação mais recente permanece aplicável", () => {
  const sequence = createAuthOperationSequence();
  const initial = sequence.begin();
  const firstRefresh = sequence.begin();
  const secondRefresh = sequence.begin();

  assert.equal(sequence.isLatest(initial), false);
  assert.equal(sequence.isLatest(firstRefresh), false);
  assert.equal(sequence.isLatest(secondRefresh), true);

  const logout = sequence.begin();
  assert.equal(sequence.isLatest(secondRefresh), false);
  assert.equal(sequence.isLatest(logout), true);

  sequence.invalidate();
  assert.equal(sequence.isLatest(logout), false);
});

test("Provider faz uma carga inicial e cancela atualização após unmount", async () => {
  const provider = await readFile(
    path.join(process.cwd(), "src", "components", "auth", "AuthProvider.tsx"),
    "utf8",
  );

  assert.equal((provider.match(/getInitialUser\(\)/g) ?? []).length, 1);
  assert.match(provider, /let active = true/);
  assert.match(provider, /active = false/);
  assert.match(provider, /mountedRef\.current = false/);
  assert.match(provider, /operationSequence\.isLatest\(operationId\)/);
  assert.match(provider, /operationSequence\.invalidate\(\)/);
  assert.match(provider, /authBrowserClient\.refresh\(\)/);
  assert.match(provider, /authBrowserClient\.logout\(\)/);
  assert.doesNotMatch(provider, /redirect|router|localStorage|sessionStorage/);
});

test("Context expõe somente status, user, refresh e logout", async () => {
  const provider = await readFile(
    path.join(process.cwd(), "src", "components", "auth", "AuthProvider.tsx"),
    "utf8",
  );
  const valueBlock = provider.match(/const value = useMemo\([\s\S]*?\);/g)?.[0] ?? "";

  assert.match(valueBlock, /status: state\.status/);
  assert.match(valueBlock, /user: state\.user/);
  assert.match(valueBlock, /refresh/);
  assert.match(valueBlock, /logout/);
  assert.doesNotMatch(valueBlock, /token|error:/);
});
