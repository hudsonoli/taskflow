// Fase 7E — auditoria de acesso real (IP original, região, navegador, SO). `npm run test:acessos`.
// Lógica pura exercitada de verdade; telas e rotas (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { TEXTO_DESCONHECIDO, TEXTO_NAO_DISPONIVEL, resolverAcessoLogin, rotuloRegiao } from "./acessos.ts";
import { cabecalhosDoCliente, ipDoCliente, textoDeLocalizacao } from "./server/cliente-http.ts";
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

// ── repasse do IP, região e User-Agent do BFF para a API (Cloudflare → NPM → BFF → API) ────────────────────────────

test("BFF: IP vem de CF-Connecting-IP (Cloudflare) > X-Real-IP (proxy da origem) > ÚLTIMO item do X-Forwarded-For", () => {
  assert.equal(ipDoCliente(cabecalhos({ "cf-connecting-ip": "187.1.2.3", "x-real-ip": "162.158.0.1" })), "187.1.2.3"); // X-Real-IP = borda da Cloudflare
  assert.equal(ipDoCliente(cabecalhos({ "cf-connecting-ip": "2804:14d:1::5" })), "2804:14d:1::5");
  assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": "187.1.2.3" })), "187.1.2.3"); // sem Cloudflare na frente
  // o primeiro item é o que o cliente escreveu; vale o que o proxy acrescentou (o último)
  assert.equal(ipDoCliente(cabecalhos({ "x-forwarded-for": "6.6.6.6, 187.1.2.3" })), "187.1.2.3");
});

test("BFF: texto arbitrário ou lista nunca é repassado como IP (nem o primeiro item)", () => {
  for (const ruim of ["abc", "<script>", "1.2.3", "999.1.1.1", "1.2.3.4, 5.6.7.8", "1.2.3.4, evil", "", "a".repeat(200)]) {
    assert.equal(ipDoCliente(cabecalhos({ "cf-connecting-ip": ruim })), null, ruim);
    assert.equal(ipDoCliente(cabecalhos({ "x-real-ip": ruim })), null, ruim);
  }
  assert.equal(ipDoCliente(cabecalhos({ "cf-connecting-ip": "lixo", "x-real-ip": "187.1.2.3" })), "187.1.2.3"); // inválido cai no próximo
  assert.equal(ipDoCliente(cabecalhos({})), null);
  assert.deepEqual(cabecalhosDoCliente(cabecalhos({ "cf-connecting-ip": "lixo" })), {});
});

test("BFF: com a Cloudflare, repassa só cabeçalhos INTERNOS sanitizados (IP, cidade, região, código, país) e o User-Agent", () => {
  const ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/153.0.0.0 Safari/537.36";
  assert.deepEqual(
    cabecalhosDoCliente(
      cabecalhos({
        "cf-connecting-ip": "187.1.2.3", "cf-ipcity": "Brasília", "cf-region": "Federal District", "cf-region-code": "df", "cf-ipcountry": "br", "user-agent": ua,
      }),
    ),
    {
      "X-Taskflow-Client-IP": "187.1.2.3",
      "X-Taskflow-CF-City": "Bras%C3%ADlia", // ASCII (percent-encoding): seguro como valor de cabeçalho
      "X-Taskflow-CF-Region": "Federal%20District",
      "X-Taskflow-CF-Region-Code": "DF",
      "X-Taskflow-CF-Country": "BR",
      "User-Agent": ua,
    },
  );
  assert.equal(cabecalhosDoCliente(cabecalhos({ "user-agent": "x".repeat(5000) }))["User-Agent"].length, 512);
  assert.deepEqual(cabecalhosDoCliente(cabecalhos({})), {});
});

test("BFF: NÃO encaminha latitude, longitude, CEP, fuso nem nenhum CF-* do navegador como está", () => {
  const saida = cabecalhosDoCliente(
    cabecalhos({
      "cf-connecting-ip": "187.1.2.3", "cf-iplatitude": "-15.78", "cf-iplongitude": "-47.93", "cf-postal-code": "70040", "cf-timezone": "America/Sao_Paulo",
      "cf-ipcity": "Brasília", "cf-ray": "abc-GRU", "x-taskflow-client-ip": "6.6.6.6", "x-taskflow-cf-city": "Paris",
    }),
  );
  assert.deepEqual(Object.keys(saida).sort(), ["X-Taskflow-CF-City", "X-Taskflow-Client-IP"]);
  assert.equal(saida["X-Taskflow-Client-IP"], "187.1.2.3"); // um X-Taskflow-* vindo do navegador é ignorado: o BFF recalcula
  assert.equal(saida["X-Taskflow-CF-City"], "Bras%C3%ADlia");
  assert.doesNotMatch(JSON.stringify(saida), /15\.78|47\.93|70040|Sao_Paulo|abc-GRU|Paris/);
});

test("BFF: valores de localização inválidos são descartados; UTF-8 lido como latin1 é reparado", () => {
  // `Headers` recusaria NUL/CRLF; um stub simula o pior caso que um cabeçalho de verdade nunca chegaria a ter
  const valores: Record<string, string> = { "cf-connecting-ip": "187.1.2.3", "cf-ipcity": "<script>" + String.fromCharCode(0, 13, 10), "cf-region": "   ", "cf-region-code": "!!!", "cf-ipcountry": "BRA" };
  const ruim = cabecalhosDoCliente({ get: (nome: string) => valores[nome] ?? null });

  assert.equal(ruim["X-Taskflow-CF-Region"], undefined);
  assert.equal(ruim["X-Taskflow-CF-Region-Code"], undefined); // código de região inválido
  assert.equal(ruim["X-Taskflow-CF-Country"], undefined); // país com 3 letras
  assert.equal(decodeURIComponent(ruim["X-Taskflow-CF-City"]), "script"); // sem <>/controle
  assert.equal(textoDeLocalizacao("BrasÃ­lia"), "Brasília"); // o Node lê o UTF-8 cru como latin1
  assert.equal(textoDeLocalizacao("Bras%C3%ADlia"), "Brasília");
  assert.equal(textoDeLocalizacao("São Paulo"), "São Paulo");
  assert.equal(textoDeLocalizacao("x".repeat(500))?.length, 80);
  assert.equal(textoDeLocalizacao("%E0%A4%A"), "%E0%A4%A"); // percent inválido: segue como texto, sem exceção
  assert.equal(textoDeLocalizacao(null), null);
});

test("as rotas de login (local e Google) repassam IP, região e User-Agent à API; a empresa continua vindo do servidor", () => {
  for (const rota of ["app/api/auth/login/route.ts", "app/api/auth/google/route.ts"]) {
    const codigo = semComentarios(ler(rota));
    assert.match(codigo, /import \{ cabecalhosDoCliente \} from "@\/lib\/server\/cliente-http"/, rota);
    assert.match(codigo, /headers: \{ "Content-Type": "application\/json", \.\.\.cabecalhosDoCliente\(request\.headers\) \}/, rota);
    assert.doesNotMatch(codigo, /empresaId|ip_address|userAgent|regiao/, rota); // nada do navegador no corpo
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

test("região formatada (Cloudflare, Fase 7E.2) cabe na célula: texto normal, sem truncar nem esconder, e a mais longa quebra de linha", () => {
  const regioes = ["Brasília, DF, Brasil", "São Paulo, SP, Brasil", "Lisboa, Portugal", "Seattle, Washington, Estados Unidos"];
  for (const regiao of regioes) {
    const acesso = resolverAcessoLogin(evento({ nome: "Maria", ip_address: "8.8.8.8", regiao }));
    assert.equal(acesso.regiao, regiao);
    assert.equal(rotuloRegiao(acesso), regiao);
  }
  const codigo = semComentarios(ler("components/acessos/AcessosView.tsx"));
  const celula = codigo.slice(codigo.indexOf("{evento.regiao ? ("), codigo.indexOf("rotuloRegiao(evento)"));
  assert.doesNotMatch(celula, /truncate|whitespace-nowrap|overflow-hidden|text-ellipsis/); // a região inteira fica visível
  assert.match(celula, /<span className="text-zinc-600 dark:text-zinc-300">\{evento\.regiao\}<\/span>/);
});

test("o proxy genérico da API não repassa cabeçalho algum do navegador (X-Taskflow-* só existe no login)", () => {
  const proxy = semComentarios(ler("app/api/backend/[...path]/route.ts"));
  assert.doesNotMatch(proxy, /request\.headers\.(get|forEach|entries)\((?!"content-type")/i);
  assert.doesNotMatch(proxy, /x-taskflow|cf-/i);
});

test("não há mais MaxMind/GeoIP local no frontend nem na tela de Acesso", () => {
  const view = ler("components/acessos/AcessosView.tsx");
  assert.doesNotMatch(view, /MaxMind|GeoIP|mmdb|base local|serviço externo/i);
  assert.match(view, /Região aproximada com base no IP da conexão/);
});
