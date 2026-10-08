// Fase 6 — filtros avançados de TRÁFEGO: tradução para os parâmetros do servidor e ligação com a tela. `npm run test:filtros-trafego`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CAMPO_TRAFEGO, FILTROS_TRAFEGO_VAZIOS, filtrosTrafegoParaApi, parametrosFiltrosTrafego } from "./filtros-trafego.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const A = "0b8f7e0e-4c2d-4f0a-9d37-1f2e3a4b5c6d";
const B = "7a1c2d3e-4f50-4617-8899-aabbccddeeff";
const AGORA = new Date(2026, 9, 8, 15, 30);
const consulta = (filtros: FiltroAtivo[]) => Object.fromEntries(parametrosFiltrosTrafego(filtrosTrafegoParaApi(filtros, AGORA)));

test("sem filtros: nenhum parâmetro estruturado e status 'todos'", () => {
  assert.deepEqual(consulta([]), {});
  assert.deepEqual(filtrosTrafegoParaApi([], AGORA), FILTROS_TRAFEGO_VAZIOS);
});

test("usuário (responsável da sessão): 'é um de' e 'não é'", () => {
  assert.deepEqual(consulta([{ campo: "usuario", operador: "in", valores: [A, B] }]), { usuarioIds: `${A},${B}` });
  assert.deepEqual(consulta([{ campo: "usuario", operador: "is_not", valores: [A] }]), { usuarioIdsExcluir: A });
});

test("departamento, cliente, projeto e prioridade: cada um no seu par incluir/excluir", () => {
  assert.deepEqual(consulta([{ campo: "departamento", operador: "is", valores: [A] }]), { departamentoIds: A });
  assert.deepEqual(consulta([{ campo: "departamento", operador: "not_in", valores: [A, B] }]), { departamentoIdsExcluir: `${A},${B}` });
  assert.deepEqual(consulta([{ campo: "cliente", operador: "in", valores: [A, B] }]), { clienteIds: `${A},${B}` });
  assert.deepEqual(consulta([{ campo: "cliente", operador: "is_not", valores: [A] }]), { clienteIdsExcluir: A });
  assert.deepEqual(consulta([{ campo: "projeto", operador: "is", valores: [A] }]), { projetoIds: A });
  assert.deepEqual(consulta([{ campo: "prioridade", operador: "in", valores: ["alta", "media"] }]), { prioridades: "alta,media" });
  assert.deepEqual(consulta([{ campo: "prioridade", operador: "is_not", valores: ["baixa"] }]), { prioridadesExcluir: "baixa" });
});

test("prazo da demanda: data real e atalhos viram prazoInicio/prazoFim (ISO com timezone)", () => {
  const antes = filtrosTrafegoParaApi([{ campo: "prazo", operador: "before", valores: ["2026-10-15"] }], AGORA);
  assert.equal(antes.prazoInicio, undefined);
  assert.equal(new Date(antes.prazoFim!).getTime(), new Date(2026, 9, 15).getTime() - 1);
  const depois = filtrosTrafegoParaApi([{ campo: "prazo", operador: "after", valores: ["2026-10-15"] }], AGORA);
  assert.equal(new Date(depois.prazoInicio!).getTime(), new Date(2026, 9, 16).getTime());
  assert.equal(depois.prazoFim, undefined);
  const atrasado = filtrosTrafegoParaApi([{ campo: "prazo", operador: "is", valores: ["atrasado"] }], AGORA);
  assert.equal(new Date(atrasado.prazoFim!).getTime(), AGORA.getTime() - 1);
  assert.match(atrasado.prazoFim!, /Z$/);
  const amanha = consulta([{ campo: "prazo", operador: "is", valores: ["amanha"] }]);
  assert.equal(new Date(amanha.prazoInicio).getDate(), 9);
  assert.equal(new Date(amanha.prazoFim).getDate(), 9);
});

test("status da sessão: só 'ativa'/'encerrada' valem; é do indicador e não vira parâmetro estruturado", () => {
  assert.equal(filtrosTrafegoParaApi([{ campo: "status", operador: "is", valores: ["encerrada"] }], AGORA).status, "encerrada");
  assert.equal(filtrosTrafegoParaApi([{ campo: "status", operador: "is", valores: ["inventado"] }], AGORA).status, "todos");
  assert.deepEqual(consulta([{ campo: "status", operador: "is", valores: ["ativa"] }]), {}); // vai por `status` nos indicadores
});

test("múltiplos filtros simultâneos: todos presentes (AND no servidor), na mesma consulta de indicadores/carga/agora", () => {
  const filtros: FiltroAtivo[] = [
    { campo: "usuario", operador: "in", valores: [A, B] },
    { campo: "cliente", operador: "is", valores: [A] },
    { campo: "prioridade", operador: "is", valores: ["alta"] },
    { campo: "prazo", operador: "before", valores: ["2026-10-15"] },
  ];
  const c = consulta(filtros);
  assert.deepEqual(Object.keys(c).sort(), ["clienteIds", "prazoFim", "prioridades", "usuarioIds"]);
});

test("campo desconhecido e filtro sem valores são ignorados", () => {
  assert.deepEqual(consulta([{ campo: "inventado", operador: "is", valores: [A] }, { campo: "cliente", operador: "is", valores: [] }]), {});
});

test("tela de Tráfego: filtros vão ao servidor nas TRÊS consultas (indicadores, carga e agora) e na paginação", () => {
  const view = ler("components/trafego/TrafegoView.tsx");
  assert.match(view, /getIndicadoresTrafegoSessoes\(\{\s*\.\.\.filtrosApi,/);
  assert.match(view, /getCargaTrafegoSessoes\(\{ \.\.\.filtrosApi, demandaQuery \}\)/);
  assert.equal((view.match(/getAgoraTrafegoSessoes\(\{\s*\.\.\.filtrosApi,/g) ?? []).length, 2); // 1ª página e "carregar mais"
  assert.match(view, /offset: agora\.linhas\.length/);
  assert.match(view, /chaveAgoraRef\.current = JSON\.stringify\(\[filtrosApi, demandaQuery, versaoIndicadores\]\)/); // página antiga é descartada
  assert.doesNotMatch(view, /linhas\.filter\(/); // nunca filtra só a página carregada
});

test("estado na URL: filtros, período e busca de demanda; período inválido volta ao padrão", () => {
  const view = ler("components/trafego/TrafegoView.tsx");
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, true\)/);
  assert.match(view, /PERIODOS_VALIDOS\.find\(\(periodo\) => periodo === valor\) \?\? PERIODO_PADRAO/);
  assert.match(view, /definirParam\("periodo", proximo === PERIODO_PADRAO \? null : proximo\)/);
  assert.match(view, /definirParam\("q", texto\)/);
});

test("campos oferecidos refletem o domínio real (sessão → demanda); status/prioridade reais; sem dados da referência", () => {
  const defs = ler("components/trafego/useDefinicoesFiltrosTrafego.ts");
  for (const campo of Object.keys(CAMPO_TRAFEGO)) assert.ok(defs.includes(`CAMPO_TRAFEGO.${campo}`), campo);
  assert.match(defs, /prioridadeDemandaLabels/);
  assert.match(defs, /permiteExcluir: false/); // status da sessão: sem "não é" (semântica dos indicadores)
  assert.match(defs, /buscarOpcoes: async/); // usuário: busca no servidor
  assert.doesNotMatch(defs, /Backlog|In Review|Andrew|Hotfix/);
});

test("API: o cliente HTTP envia os filtros avançados às três rotas e nenhuma ganha parâmetro de outra", () => {
  const api = ler("lib/api.ts");
  assert.equal((api.match(/parametrosFiltrosTrafego\(filtros\)/g) ?? []).length, 3);
  const bff = ler("lib/filtros-trafego.ts");
  for (const nome of ["usuarioIdsExcluir", "departamentoIdsExcluir", "clienteIds", "clienteIdsExcluir", "projetoIds", "projetoIdsExcluir", "prioridades", "prioridadesExcluir", "prazoInicio", "prazoFim"]) {
    assert.ok(bff.includes(`"${nome}"`), nome);
  }
});
