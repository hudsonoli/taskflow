// Fase 7C — visões operacionais de liderança: Meu Departamento (equipe agora) e Pauta GLOBAL. `npm run test:fase-7c`.
// Lógica pura exercitada de verdade; telas e API (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CAMPO_PAUTA, filtrosPautaParaApi } from "./filtros-pauta.ts";
import { CAMPO_MEU_DEPARTAMENTO } from "./filtros-meu-departamento.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const A = "0b8f7e0e-4c2d-4f0a-9d37-1f2e3a4b5c6d";
const B = "7a1c2d3e-4f50-4617-8899-aabbccddeeff";
const AGORA = new Date(2026, 9, 15, 14, 0);

// ── filtros da Pauta global ─────────────────────────────────────────────────────────────────────────────────────

test("Pauta global: Departamento É filtro (é / é um de, OR) e os demais campos mapeiam como no Meu Departamento", () => {
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is", valores: [A] }]), { departamentoId: A });
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "in", valores: [A, B] }]), { departamentoId: `${A},${B}` });
  const combinado = filtrosPautaParaApi(
    [
      { campo: "departamento", operador: "in", valores: [A, B] },
      { campo: "responsavel", operador: "is", valores: [A] },
      { campo: "equipe", operador: "is_not", valores: [B] },
      { campo: "cliente", operador: "in", valores: [A, B] },
      { campo: "status", operador: "in", valores: ["em_execucao", "pausada"] },
      { campo: "prioridade", operador: "is", valores: ["alta"] },
      { campo: "origem", operador: "is", valores: ["cliente"] },
    ],
    AGORA,
  );
  assert.deepEqual(combinado, {
    departamentoId: `${A},${B}`,
    responsavelId: A,
    equipeIdExcluir: B,
    clienteId: `${A},${B}`,
    status: "em_execucao,pausada",
    prioridade: "alta",
    origem: "cliente",
  });
});

test("departamento 'não é' não vira parâmetro (o servidor não executa); prazo reaproveita a tradução do Meu Departamento", () => {
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is_not", valores: [A] }]), {});
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is", valores: [] }]), {});
  assert.deepEqual(filtrosPautaParaApi([{ campo: "prazo", operador: "is", valores: ["atrasado"] }], AGORA), { atrasada: true });
  const antes = filtrosPautaParaApi([{ campo: "prazo", operador: "before", valores: ["2026-10-20"] }], AGORA);
  assert.equal(new Date(antes.prazoFim!).getTime(), new Date(2026, 9, 20).getTime() - 1);
  assert.deepEqual(filtrosPautaParaApi([]), {});
});

test("o Meu Departamento NÃO ganhou Departamento como filtro; a Pauta ganhou", () => {
  assert.equal("departamento" in CAMPO_MEU_DEPARTAMENTO, false);
  assert.equal(CAMPO_PAUTA.departamento, "departamento");
  assert.doesNotMatch(ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts"), /label: "Departamento"/);
  const defs = ler("components/pauta/useDefinicoesFiltrosPauta.ts");
  for (const campo of Object.keys(CAMPO_PAUTA)) assert.ok(defs.includes(`CAMPO_PAUTA.${campo}`), campo);
  assert.match(defs, /STATUS_DA_FILA/); // a Pauta mostra o que está em andamento
  assert.match(defs, /permiteExcluir: false/);
});

// ── Pauta: modos, autorização e consulta ────────────────────────────────────────────────────────────────────────

test("autorização da Pauta global no cliente espelha a do servidor: admin/gestor, Head ou Atendimento; operador comum não", () => {
  const escopo = semComentarios(ler("lib/escopo-operacional.ts"));
  const corpo = escopo.slice(escopo.indexOf("export function podeAcessarPautaGlobal"), escopo.indexOf("export function podeAcessarMinhasDemandas"));
  assert.match(corpo, /base === "admin" \|\| base === "gestor"/);
  assert.match(corpo, /podeAcessarMeuDepartamento\(usuario, departamentos\) \|\| resolverEhAtendimento\(usuario, departamentos\)/);
  assert.doesNotMatch(corpo, /operador|@|\.com|empresaId/i); // nada hardcoded por e-mail, nome ou tenant
});

test("Pauta GLOBAL: escopo=pauta, só em andamento, prazo até o fim do período (atrasadas entram), mesmos parâmetros em todas as páginas", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /escopo: "pauta" as const, naoFinalizada: true, prazoFim: periodoFim\.toISOString\(\), \.\.\.parametrosFiltros/);
  assert.doesNotMatch(view.slice(view.indexOf("if (modoGlobal) {"), view.indexOf("return { ...base, departamentoId")), /prazoInicio/); // sem teto inferior: atrasadas aparecem
  assert.match(view, /listDemandasReais\(parametrosDaConsulta\(0\)\)/);
  assert.match(view, /listDemandasReais\(parametrosDaConsulta\(demandasPauta\.length\)\)/); // "carregar mais" = mesmos filtros
  assert.doesNotMatch(semComentarios(view), /demandasPauta\.filter\(/); // nunca filtra só o que foi carregado
  assert.match(view, /if \(!pronto\) return;/); // espera os departamentos: não busca no modo errado
});

test("Pauta LEGADA (operador comum): consulta e filtro de sempre, sem escopo global", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /return \{ \.\.\.base, departamentoId: departamentoIdsParam \|\| undefined, prazoInicio: periodoInicio\.toISOString\(\), prazoFim: periodoFim\.toISOString\(\) \};/);
  const toolbar = ler("components/pauta/PautaToolbar.tsx");
  assert.match(toolbar, /\{filtrosAvancados \?\? \(/); // sem filtros avançados, o seletor simples de departamentos continua
  assert.match(toolbar, /label="Departamento"/);
});

test("estado da Pauta global na URL: filtros, busca (q), período e modo; inválido volta ao padrão", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, modoGlobal\)/); // só persiste no modo global
  assert.match(view, /PERIODOS_VALIDOS\.find\(\(valor\) => valor === param\("periodo"\)\) \?\? "7d"/);
  assert.match(view, /MODOS_VALIDOS\.find\(\(valor\) => valor === param\("modo"\)\) \?\? "gantt"/);
  assert.match(view, /definirParam\("q", texto\)/);
});

test("selo 'em execução agora' na Pauta: só ids de demanda (sem pessoa nem tempo), só no modo global, falha não derruba a lista", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /modoGlobal \? listarDemandasEmExecucaoNaPauta\(\)\.catch\(\(\) => \[\] as string\[\]\)/);
  assert.match(ler("components/pauta/PautaLista.tsx"), /emExecucaoIds\?\.has\(demanda\.id\) && <Badge tone="green">Em execução agora<\/Badge>/);
  assert.match(ler("components/pauta/PautaGantt.tsx"), /aria-label="Em execução agora"/);
  const api = ler("lib/api-backend.ts");
  assert.match(api, /"\/sessoes-trabalho\/pauta\/em-execucao"/);
});

// ── Meu Departamento: quem está trabalhando agora ───────────────────────────────────────────────────────────────

test("Meu Departamento mostra quem está trabalhando e em quê, pela sessão real, sem horário nem 'online'", () => {
  const card = ler("components/meu-departamento/EquipeAgoraCard.tsx");
  const codigo = semComentarios(card);
  assert.match(codigo, /Sem atividade em execução/);
  assert.match(codigo, /Em execução:/);
  assert.doesNotMatch(codigo, /online|offline|ativo agora|última atividade|decorrido|duração|inicioEm|formatHoras/i); // sem presença inventada nem tempo
  assert.match(ler("lib/api-backend.ts"), /\/sessoes-trabalho\/meu-departamento\/agora\?/);
  const view = ler("components/meu-departamento/MeuDepartamentoView.tsx");
  assert.match(view, /<EquipeAgoraCard key=\{departamentoHead\.id\} departamentoId=\{departamentoHead\.id\} \/>/); // recomeça ao trocar de departamento
  assert.match(view, /afetam só a lista/); // KPIs continuam do departamento inteiro (decisão preservada)
});

test("o card da equipe não consulta status de demanda para dizer quem trabalha", () => {
  const codigo = semComentarios(ler("components/meu-departamento/EquipeAgoraCard.tsx"));
  assert.doesNotMatch(codigo, /status/i);
});
