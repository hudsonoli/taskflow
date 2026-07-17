import { registerHooks } from "node:module";

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "server-only") {
      return {
        format: "module",
        shortCircuit: true,
        url: "data:text/javascript,export {};",
      };
    }
    if (specifier === "next/server") {
      return nextResolve("next/server.js", context);
    }
    if (
      (context.parentURL?.includes("/src/") ||
        context.parentURL?.includes("/tests/auth/")) &&
      specifier.startsWith(".") &&
      !/\.[a-z]+$/i.test(specifier)
    ) {
      return nextResolve(`${specifier}.ts`, context);
    }
    return nextResolve(specifier, context);
  },
});

export const TEST_TOKEN = "server-jwt-value";

export const CURRENT_USER = {
  usuarioId: "11111111-1111-1111-1111-111111111111",
  empresaId: "22222222-2222-2222-2222-222222222222",
  nome: "Usuário Teste",
  perfilBase: "admin",
  acessoSistema: true,
  status: "ativo",
};

export function makeConfig(overrides = {}) {
  return {
    apiInternalUrl: "http://taskfloww_api:8000",
    allowedOrigins: new Set(["http://localhost:3010"]),
    sessionMaxAgeSeconds: 1_800,
    backendTimeoutMs: 100,
    production: false,
    ...overrides,
  };
}

export function setValidAuthEnvironment() {
  process.env.TASKFLOWW_API_INTERNAL_URL = "http://taskfloww_api:8000";
  process.env.TASKFLOWW_AUTH_ALLOWED_ORIGINS = "http://localhost:3010";
  process.env.TASKFLOWW_SESSION_MAX_AGE_SECONDS = "1800";
  process.env.NODE_ENV = "test";
}
