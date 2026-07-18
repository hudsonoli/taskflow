import assert from "node:assert/strict";
import test from "node:test";
import "./helpers.mjs";

const { AuthBffError } = await import("../../src/lib/auth/errors");
const { getAuthBffConfig, getAuthLoginConfig } = await import(
  "../../src/lib/auth/config"
);

const VALID_COMMON_ENVIRONMENT = {
  NODE_ENV: "production",
  TASKFLOWW_API_INTERNAL_URL: "http://taskfloww_api:8000/",
  TASKFLOWW_AUTH_ALLOWED_ORIGINS:
    "https://app.example.com,http://localhost:3010",
  TASKFLOWW_SESSION_MAX_AGE_SECONDS: "1800",
} as const;

test("rejeita configuração comum obrigatória ausente com erro seguro", () => {
  assert.throws(
    () => getAuthBffConfig({ NODE_ENV: "test" }),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 500 &&
      error.code === "CONFIGURATION_ERROR",
  );
});

test("carrega configuração comum sem depender da empresa padrão", () => {
  const config = getAuthBffConfig(VALID_COMMON_ENVIRONMENT);

  assert.equal(config.apiInternalUrl, "http://taskfloww_api:8000");
  assert.deepEqual(
    [...config.allowedOrigins],
    ["https://app.example.com", "http://localhost:3010"],
  );
  assert.equal(config.sessionMaxAgeSeconds, 1800);
  assert.equal(config.production, true);
  assert.equal("authDefaultEmpresaCodigo" in config, false);
  assert.equal("AUTH_SECRET_KEY" in config, false);
});

test("configuração de login acrescenta a empresa padrão server-side", () => {
  const config = getAuthLoginConfig({
    ...VALID_COMMON_ENVIRONMENT,
    AUTH_DEFAULT_EMPRESA_CODIGO: "  EMPRESA  ",
  });

  assert.equal(config.authDefaultEmpresaCodigo, "EMPRESA");
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

test("login rejeita empresa padrão ausente sem revelar a variável", () => {
  assert.throws(
    () =>
      getAuthLoginConfig({
        ...VALID_COMMON_ENVIRONMENT,
        AUTH_DEFAULT_EMPRESA_CODIGO: "   ",
      }),
    (error: unknown) =>
      error instanceof AuthBffError &&
      error.status === 500 &&
      error.code === "CONFIGURATION_ERROR" &&
      error.safeMessage === "Não foi possível concluir a solicitação." &&
      !error.safeMessage.includes("AUTH_DEFAULT_EMPRESA_CODIGO"),
  );
});
