import assert from "node:assert/strict";
import test from "node:test";
import "./helpers.mjs";

const { AuthBffError } = await import("../../src/lib/auth/errors");
const { getAuthBffConfig } = await import("../../src/lib/auth/config");

test("rejeita configuração obrigatória ausente com erro seguro", () => {
  assert.throws(
    () => getAuthBffConfig({ NODE_ENV: "test" }),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 500 &&
      error.code === "CONFIGURATION_ERROR",
  );
});

test("carrega somente as variáveis server-side necessárias", () => {
  const config = getAuthBffConfig({
    NODE_ENV: "production",
    TASKFLOWW_API_INTERNAL_URL: "http://taskfloww_api:8000/",
    TASKFLOWW_AUTH_ALLOWED_ORIGINS:
      "https://app.example.com,http://localhost:3010",
    TASKFLOWW_SESSION_MAX_AGE_SECONDS: "1800",
  });

  assert.equal(config.apiInternalUrl, "http://taskfloww_api:8000");
  assert.deepEqual(
    [...config.allowedOrigins],
    ["https://app.example.com", "http://localhost:3010"],
  );
  assert.equal(config.sessionMaxAgeSeconds, 1800);
  assert.equal(config.production, true);
  assert.equal("AUTH_SECRET_KEY" in config, false);
});

test("rejeita URL interna com credenciais e duração inválida", () => {
  assert.throws(
    () =>
      getAuthBffConfig({
        TASKFLOWW_API_INTERNAL_URL: "http://user:pass@taskfloww_api:8000",
        TASKFLOWW_AUTH_ALLOWED_ORIGINS: "http://localhost:3010",
        TASKFLOWW_SESSION_MAX_AGE_SECONDS: "0",
      }),
    AuthBffError,
  );
});
