// Fase 10A — nome comercial: o produto é "TaskFlow", nunca "TaskFloww". `npm run test:nome-produto` (node --test, sem dependências).
// Separa o que é VISÍVEL (UI, títulos, e-mails, nomes de download, mensagens) do que é TÉCNICO e legítimo (contêineres, bancos locais, e-mails de seed, comentários
// históricos, ids de migration). O nome comercial NÃO justifica renomear infraestrutura: isso é um P3 de nomenclatura técnica.
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";

const FRONT = new URL("../", import.meta.url);
const BACK = new URL("../../../backend/app/", import.meta.url);
const PACKAGE = new URL("../../package.json", import.meta.url);

function arquivos(dir: URL, ext: RegExp, acumulado: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    if (nome === "__pycache__" || nome === "node_modules") continue;
    const caminho = new URL(nome + (statSync(new URL(nome, dir)).isDirectory() ? "/" : ""), dir);
    if (statSync(caminho).isDirectory()) arquivos(caminho, ext, acumulado);
    else if (ext.test(nome) && !/\.test\.ts$/.test(nome)) acumulado.push(caminho.pathname.replace(/^\/([A-Za-z]:)/, "$1"));
  }
  return acumulado;
}
const texto = (arquivo: string) => readFileSync(arquivo, "utf8");

// "Visível" = qualquer grafia de produto com dois W ("TaskFloww", "Taskfloww", "TASKFLOWW", "TaskFlowW") em código OU comentário de produção — como os comentários
// também foram atualizados, o alvo é ZERO em tudo; as grafias técnicas em minúsculas (taskfloww) são listadas à parte.
const VISIVEL = /T[aA][sS][kK][fF][lL][oO][wW]{2}/g;
const TECNICO = /taskfloww/g;

const fontesFront = arquivos(FRONT, /\.(ts|tsx)$/);
const fontesBack = arquivos(BACK, /\.py$/);

test("VISIBLE_TASKFLOWW=0: nenhuma grafia 'TaskFloww' em UI, títulos, mensagens, e-mails ou código de produção (frontend e backend)", () => {
  const achados: string[] = [];
  for (const arquivo of [...fontesFront, ...fontesBack]) {
    for (const m of texto(arquivo).matchAll(VISIVEL)) achados.push(`${arquivo.replace(/\\/g, "/").split(/\/(?:src|app)\//).pop()}: ${m[0]}`);
  }
  assert.deepEqual(achados, []);
});

test("o nome oficial aparece onde o produto é mostrado: título, login neutro, e-mail transacional, download, User-Agent", () => {
  assert.match(texto(new URL("lib/produto.ts", FRONT).pathname.replace(/^\/([A-Za-z]:)/, "$1")), /NOME_PRODUTO = "TaskFlow"/);
  const leitura = (rel: string) => texto(new URL(rel, FRONT).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
  assert.match(leitura("components/auth/EmpresaIndisponivelView.tsx"), /TaskFlow na sua empresa/);
  assert.match(leitura("components/personalizacao/PersonalizacaoView.tsx"), /Restaurar o padrão do TaskFlow\?/);
  assert.match(leitura("components/plataforma/PlataformaGuard.tsx"), /responsável pelo TaskFlow/);
  assert.match(leitura("lib/brasilApi.ts"), /USER_AGENT_CONSULTA = "TaskFlow\/1\.0"/);
  assert.match(leitura("lib/selecao-arquivos.ts"), /padrao = "taskflow-arquivos\.zip"/);
  const auth = texto(new URL("services/auth_service.py", BACK).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
  assert.match(auth, /PASSWORD_RESET_EMAIL_SUBJECT = "Redefinição de senha — TaskFlow"/);
  assert.match(auth, /\(via TaskFlow\)/); // empresa em destaque, produto secundário
  assert.match(texto(new URL("api/routes/root.py", BACK).pathname.replace(/^\/([A-Za-z]:)/, "$1")), /TaskFlow API/);
});

test("TECHNICAL_TASKFLOWW: o que sobra em minúsculas é implementação (seed local, SQLite legado, ids) e NÃO foi renomeado", () => {
  const tecnicos = new Map<string, number>();
  for (const arquivo of [...fontesFront, ...fontesBack]) {
    for (const m of texto(arquivo).matchAll(/[\w@./:-]*taskfloww[\w@./:-]*/g)) {
      tecnicos.set(m[0], (tecnicos.get(m[0]) ?? 0) + 1);
    }
  }
  const permitidos = new Set([
    "hudson@taskfloww.local", "ana.costa@taskfloww.local", "carlos.lima@taskfloww.local", "joao.silva@taskfloww.local", "maria.souza@taskfloww.local", // seed local
    "sqlite:///./taskfloww.db", // URL SQLite padrão de desenvolvimento
  ]);
  const inesperados = [...tecnicos.keys()].filter((t) => !permitidos.has(t));
  assert.deepEqual(inesperados, []);
  assert.ok(TECNICO.source.length > 0);
});

test("INFRA_RENAMED=NÃO: contêineres, volumes, network e diretórios técnicos seguem como estão (compose e scripts não foram tocados)", () => {
  const compose = new URL("../../../docker-compose.yml", import.meta.url);
  if (existsSync(compose)) assert.match(readFileSync(compose, "utf8"), /taskfloww/i);
  const pacote = JSON.parse(readFileSync(PACKAGE, "utf8")) as { name: string };
  assert.equal(pacote.name, "frontend"); // o pacote técnico não foi renomeado
});
