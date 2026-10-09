// Fase 7E — auditoria de acesso real (IP original, região, navegador, SO). `npm run test:acessos`.
// Lógica pura exercitada de verdade; telas e rotas (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { TEXTO_DESCONHECIDO, TEXTO_NAO_DISPONIVEL, resolverAcessoLogin, rotuloRegiao } from "./acessos.ts";
import { cabecalhosDoCliente, ipDoCliente } from "./server/cliente-http.ts";
import type { EventoApi } from "../types/acesso.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const cabecalhos = (valores: Record<string, string>) => new Headers(valores);

function evento(payload: Record<string, unknown>): EventoApi {
  return {
    id: "e1", empresaId: "emp", agenciaId: null, tipo: "auth.login_sucesso", entidadeTipo: "usuario", entidadeId: "u1",
    usuarioId: "u1", payload, occurredAt: "2026-10-09T12:00:00+00:00", createdAt: "2026-10-09T12:00:00+00:00",
  };
}

// ── o que a tela exibe ──────────────────────────────────────────────────────────────────────────────────────────

test("novo evento: IP, região, navegador e SO vêm resolvidos do servidor", () => {
  const acesso = resolverAcessoLogin(
    evento({ nome: "Maria", ip_address: "187.1.2.3", regiao: "Brasília, DF, Brasil", navegador: "Chrome 153", sistema_operacional: "Windows" }),
  );
  assert.equal(acesso.nome, "Maria");
  assert.equal(acesso.ip, "187.1.2.3");
  assert.equal(acesso.regiao, "Brasília, DF, Brasil");
  assert.equal(acesso.navegador, "Chrome 153");
  assert.equal(acesso.sistemaOperacional, "Windows");
  assert.equal(rotuloRegiao(acesso), "Brasília, DF, Brasil");
});

test("sem região: «Não disponível»; sem navegador/SO: «Desconhecido»; nada é inventado", () => {
  const acesso = resolverAcessoLogin(evento({ nome: "Ana", ip_address: "2804:14d:1::5", regiao: null, navegador: null, sistema_operacional: null }));
  assert.equal(acesso.regiao, null);
  assert.equal(rotuloRegiao(acesso), TEXTO_NAO_DISPONIVEL);
  assert.equal(acesso.navegador, TEXTO_DESCONHECIDO);
  assert.equal(acesso.sistemaOperacional, TEXTO_DESCONHECIDO);
  assert.equal(acesso.ip, "2804:14d:1::5"); // IPv6 mostrado como veio
});

test("evento ANTIGO (User-Agent guardado, sem campos novos): continua legível, sem reconstruir o IP perdido", () => {
  const antigo = resolverAcessoLogin(
    evento({ nome: "João", ip_address: "172.18.0.4", user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150.0.0.0 Safari/537.36" }),
  );
  assert.equal(antigo.ip, "172.18.0.4"); // não é "corrigido": a informação original foi perdida
  assert.equal(antigo.navegador, "Chrome");
  assert.equal(antigo.sistemaOperacional, "Windows");
  assert.equal(antigo.regiao, null);
  const semNada = resolverAcessoLogin(evento({ ip_address: "172.18.0.4", user_agent: "node" }));
  assert.equal(semNada.navegador, TEXTO_DESCONHECIDO);
  assert.equal(semNada.nome, "Usuário desconhecido");
});

test("payload ausente ou com tipos errados não derruba a tela", () => {
  const acesso = resolverAcessoLogin({ ...evento({}), payload: undefined as unknown as Record<string, unknown> });
  assert.equal(acesso.ip, null);
  const torto = resolverAcessoLogin(evento({ ip_address: 123, regiao: {}, navegador: [], nome: "" }));
  assert.equal(torto.ip, null);
  assert.equal(torto.regiao, null);
  assert.equal(torto.navegador, TEXTO_DESCONHECIDO);
});

// ── repasse do IP/User-Agent do BFF para a API ──────────────────────────────────────────────────────────────────

test("BFF: IP do cliente vem de X-Real-IP (definido pelo proxy) ou do ÚLTIMO item do X-Forwarded-For", () => {
  assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": "187.1.2.3" })), "187.1.2.3");
  assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": "2804:14d:1::5" })), "2804:14d:1::5");
  // o primeiro item é o que o cliente escreveu; vale o que o proxy acrescentou (o último)
  assert.equal(ipDoCliente(cabecalhos({ "x-forwarded-for": "6.6.6.6, 187.1.2.3" })), "187.1.2.3");
  assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": "187.1.2.3", "x-forwarded-for": "6.6.6.6" })), "187.1.2.3");
});

test("BFF: texto arbitrário nunca é repassado como IP", () => {
  for (const ruim of ["abc", "<script>", "1.2.3", "999.1.1.1", "1.2.3.4, evil", "", "a".repeat(200)]) {
    assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": ruim })), null, ruim);
  }
  assert.equal(ipDoCliente(cabecalhos({})), null);
  assert.deepEqual(cabecalhosDoCliente(cabecalhos({ "x-real-ip": "lixo" })), {});
});

test("BFF: repassa X-Forwarded-For (só o IP) e o User-Agent do navegador, limitado", () => {
  const ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/153.0.0.0 Safari/537.36";
  assert.deepEqual(cabecalhosDoCliente(cabecalhos({ "x-real-ip": "187.1.2.3", "x-forwarded-for": "6.6.6.6, 187.1.2.3", "user-agent": ua })), {
    "X-Forwarded-For": "187.1.2.3",
    "User-Agent": ua,
  });
  assert.equal(cabecalhosDoCliente(cabecalhos({ "user-agent": "x".repeat(5000) }))["User-Agent"].length, 512);
  assert.deepEqual(cabecalhosDoCliente(cabecalhos({})), {});
});

test("as rotas de login (local e Google) repassam IP e User-Agent à API; a empresa continua vindo do servidor", () => {
  for (const rota of ["app/api/auth/login/route.ts", "app/api/auth/google/route.ts"]) {
    const codigo = semComentarios(ler(rota));
    assert.match(codigo, /import \{ cabecalhosDoCliente \} from "@\/lib\/server\/cliente-http"/, rota);
    assert.match(codigo, /headers: \{ "Content-Type": "application\/json", \.\.\.cabecalhosDoCliente\(request\.headers\) \}/, rota);
    assert.doesNotMatch(codigo, /empresaId|ip_address|userAgent/, rota); // nada do navegador no corpo
  }
});

// ── tela ────────────────────────────────────────────────────────────────────────────────────────────────────────

test("tela de Acesso: colunas, região, estados e escopo da empresa (sem aviso obsoleto)", () => {
  const view = ler("components/acessos/AcessosView.tsx");
  const codigo = semComentarios(view);
  for (const coluna of ["Usuário", "Data/hora", "IP", "Região do IP", "Navegador", "Sistema operacional"]) {
    assert.ok(codigo.includes(`>${coluna}</th>`), coluna);
  }
  assert.match(codigo, /setEventos\(resultado\.map\(resolverAcessoLogin\)\)/); // o servidor é a fonte
  assert.match(codigo, /evento\.regiao \?/);
  assert.match(codigo, /rotuloRegiao\(evento\)/);
  assert.match(codigo, /<EstadoCarregando/); // loading
  assert.match(codigo, /<EstadoErro mensagem=\{erro\} onRetry=\{carregar\}/); // erro + retry
  assert.match(codigo, /Nenhum login registrado/); // vazio
  // aviso antigo removido: o login real existe e a lista é da empresa da sessão (o servidor filtra)
  assert.doesNotMatch(view, /usuário simulado|não filtra por\s+empresa|serviço externo de geolocalização|fora do escopo do\s+protótipo/);
  // tenant-safe: a consulta nunca escolhe empresa (o servidor usa a do token)
  assert.match(codigo, /listEventos\(\{ tipo: TIPO_LOGIN_SUCESSO, limit: 100 \}\)/);
  assert.doesNotMatch(codigo, /empresaId/);
  // acesso administrativo mantido
  assert.match(codigo, /podeAcessarAcessos\(usuarioAtual\)/);
  assert.match(codigo, /overflow-x-auto/); // responsivo: a tabela rola no celular
});

test("a tela não analisa mais o User-Agent do evento por conta própria (só o fallback de eventos antigos, em lib/acessos)", () => {
  assert.doesNotMatch(semComentarios(ler("components/acessos/AcessosView.tsx")), /user-agent|parseNavegador|parseSistemaOperacional/);
  assert.match(semComentarios(ler("lib/acessos.ts")), /parseNavegador\(userAgentLegado\)/);
});
