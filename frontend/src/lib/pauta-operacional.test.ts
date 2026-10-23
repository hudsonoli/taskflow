import assert from "node:assert/strict";
import test from "node:test";
import {
  adicionarDias,
  agruparPorColaborador,
  agruparPorProjeto,
  consultaDaPauta,
  diferencaEmDias,
  formatarDiaMes,
  idsDasEtapas,
  listarDiasDoPeriodo,
  manterColaboradoresFiltrados,
  ordenarItens,
  posicaoDaJanela,
  separarPorPlanejamento,
} from "./pauta-operacional.ts";
import type { PautaItem } from "../types/pauta-operacional.ts";

let seq = 0;
function item(parcial: Partial<PautaItem> & { usuarios?: string[]; departamentos?: string[]; inicio?: string | null; fim?: string | null }): PautaItem {
  seq += 1;
  const { usuarios = [], departamentos = [], inicio = "2026-10-22", fim = "2026-10-25", ...resto } = parcial;
  const estado = inicio === null ? "nao_planejado" : fim === null ? "incompleto" : "planejado";
  return {
    etapaId: `e${seq}`, etapaNome: "Etapa", etapaTipo: "execucao", etapaOrdem: 1, etapaStatus: "pendente", etapaAtual: true,
    demandaId: `d${seq}`, demandaIdentificador: `#${seq}`, demandaNome: `Demanda ${seq}`, demandaStatus: "planejada", prioridade: "media",
    clienteId: null, projetoId: null, prazoEtapaAtual: null,
    planejamento: { inicio, fim, estado, invalido: false },
    responsabilidadeEfetiva: { origem: usuarios.length || departamentos.length ? "etapa" : "nenhuma", usuarioIds: usuarios, departamentoIds: departamentos },
    ...resto,
  };
}

const PESSOAS = [{ id: "u-raquel", nome: "Raquel" }, { id: "u-joao", nome: "João" }, { id: "u-ana", nome: "Ana" }];

test("datas puras: aritmética sem fuso e formatação sem deslocar o dia", () => {
  assert.equal(adicionarDias("2026-10-31", 1), "2026-11-01");
  assert.equal(adicionarDias("2026-03-01", -1), "2026-02-28");
  assert.equal(diferencaEmDias("2026-10-19", "2026-11-15"), 27);
  assert.equal(listarDiasDoPeriodo("2026-10-19", "2026-11-15").length, 28);
  assert.deepEqual(listarDiasDoPeriodo("2026-10-20", "2026-10-19"), []);
  assert.equal(formatarDiaMes("2026-10-22"), "22/10");
  assert.equal(formatarDiaMes(null), "—");
});

test("geometria: só a janela PLANEJADA posiciona a barra; incompleta e fora do período não desenham", () => {
  const dias = ["2026-10-19", "2026-11-15"] as const;
  assert.deepEqual(posicaoDaJanela("2026-10-22", "2026-10-25", ...dias), { colunaInicio: 4, colunaFim: 8, cortadaAntes: false, cortadaDepois: false });
  assert.deepEqual(posicaoDaJanela("2026-10-22", "2026-10-22", ...dias), { colunaInicio: 4, colunaFim: 5, cortadaAntes: false, cortadaDepois: false }); // um dia = uma coluna
  assert.equal(posicaoDaJanela("2026-10-22", null, ...dias), null); // incompleta: nunca inventa fim
  assert.equal(posicaoDaJanela(null, null, ...dias), null);
  assert.equal(posicaoDaJanela("2026-10-01", "2026-10-10", ...dias), null);
  assert.equal(posicaoDaJanela("2026-12-01", "2026-12-03", ...dias), null);
  assert.deepEqual(posicaoDaJanela("2026-10-10", "2026-10-21", ...dias), { colunaInicio: 1, colunaFim: 4, cortadaAntes: true, cortadaDepois: false });
  assert.deepEqual(posicaoDaJanela("2026-11-10", "2026-12-01", ...dias), { colunaInicio: 23, colunaFim: 29, cortadaAntes: false, cortadaDepois: true });
  assert.equal(posicaoDaJanela("2026-10-25", "2026-10-22", ...dias), null); // invertida: não desenha
});

test("colaborador: um grupo por pessoa (por nome), multi-responsável aparece nos dois e a janela NÃO é dividida", () => {
  const compartilhada = item({ usuarios: ["u-raquel", "u-joao"], inicio: "2026-10-22", fim: "2026-10-25" });
  const propria = item({ usuarios: ["u-joao"] });
  const grupos = agruparPorColaborador([compartilhada, propria], PESSOAS);
  assert.deepEqual(grupos.map((g) => g.titulo), ["João", "Raquel"]);
  assert.deepEqual(grupos[0].itens.map((i) => i.etapaId).sort(), [compartilhada.etapaId, propria.etapaId].sort());
  assert.deepEqual(grupos[1].itens.map((i) => i.etapaId), [compartilhada.etapaId]);
  for (const grupo of grupos) for (const i of grupo.itens) assert.deepEqual([i.planejamento.inicio, i.planejamento.fim], ["2026-10-22", "2026-10-25"]); // a janela é a mesma nos dois grupos
});

test("grupos especiais ficam no fim e são distintos: só departamento ≠ ninguém; nada é escolhido por conta própria", () => {
  const pessoa = item({ usuarios: ["u-ana"] });
  const soDepartamento = item({ departamentos: ["dep-criacao"] });
  const ninguem = item({});
  const grupos = agruparPorColaborador([ninguem, soDepartamento, pessoa], PESSOAS);
  assert.deepEqual(grupos.map((g) => [g.tipo, g.titulo]), [["colaborador", "Ana"], ["sem-individual", "Sem responsável individual"], ["sem-responsavel", "Sem responsável"]]);
  assert.deepEqual(grupos[1].itens, [soDepartamento]);
  assert.deepEqual(grupos[2].itens, [ninguem]);
  assert.deepEqual(agruparPorColaborador([], PESSOAS), []);
});

test("pessoa fora do catálogo não some (rótulo neutro) e vai por último entre os colaboradores", () => {
  const grupos = agruparPorColaborador([item({ usuarios: ["u-desconhecido"] }), item({ usuarios: ["u-ana"] })], PESSOAS);
  assert.deepEqual(grupos.map((g) => g.titulo), ["Ana", "Usuário indisponível"]);
});

test("projeto: cada item aparece UMA vez e 'Sem projeto' fecha a lista", () => {
  const a = item({ usuarios: ["u-raquel", "u-joao"], projetoId: "p-b" });
  const b = item({ projetoId: "p-a" });
  const c = item({});
  const nomes: Record<string, string> = { "p-a": "Alfa", "p-b": "Beta" };
  const grupos = agruparPorProjeto([a, b, c], (id) => nomes[id]);
  assert.deepEqual(grupos.map((g) => g.titulo), ["Alfa", "Beta", "Sem projeto"]);
  assert.equal(grupos.flatMap((g) => g.itens).filter((i) => i.etapaId === a.etapaId).length, 1); // multi-responsável não duplica
});

test("a troca Colaborador ⇄ Projeto não muda o conjunto de etapas (só o agrupamento)", () => {
  const itens = [
    item({ usuarios: ["u-raquel", "u-joao"], projetoId: "p-a" }),
    item({ usuarios: ["u-joao"] }),
    item({ departamentos: ["dep-x"], projetoId: "p-b" }),
    item({ inicio: null, fim: null }),
    item({ inicio: "2026-10-22", fim: null, usuarios: ["u-ana"] }),
  ];
  const porColaborador = idsDasEtapas(agruparPorColaborador(itens, PESSOAS));
  const porProjeto = idsDasEtapas(agruparPorProjeto(itens, (id) => id));
  assert.deepEqual(porColaborador, porProjeto);
  assert.equal(porColaborador.length, itens.length);
});

test("planejamento: planejadas desenham; incompletas e não planejadas ficam em seções próprias (nunca escondidas)", () => {
  const plan = item({});
  const inc = item({ inicio: "2026-10-22", fim: null });
  const nao = item({ inicio: null, fim: null });
  assert.deepEqual(separarPorPlanejamento([nao, inc, plan]), { planejadas: [plan], incompletas: [inc], naoPlanejadas: [nao] });
});

test("ordem determinística: início, fim, demanda, etapa; sem janela por último", () => {
  const tarde = item({ inicio: "2026-10-26", fim: "2026-10-27" });
  const cedo = item({ inicio: "2026-10-20", fim: "2026-10-21" });
  const semJanela = item({ inicio: null, fim: null });
  assert.deepEqual(ordenarItens([semJanela, tarde, cedo]).map((i) => i.etapaId), [cedo.etapaId, tarde.etapaId, semJanela.etapaId]);
});

test("consulta: só envia o que tem valor, listas em CSV", () => {
  assert.deepEqual(consultaDaPauta({}), []);
  assert.deepEqual(
    consultaDaPauta({ inicio: "2026-10-19", fim: "2026-11-15", usuarioIds: ["a", "b"], projetoIds: [], prioridades: ["alta"], busca: "  verão " }),
    [["inicio", "2026-10-19"], ["fim", "2026-11-15"], ["usuarioIds", "a,b"], ["prioridades", "alta"], ["busca", "verão"]],
  );
});

test("filtro Colaborador: a visão por colaborador mostra só os filtrados (a co-responsável da etapa compartilhada não ganha grupo à parte)", () => {
  const compartilhada = item({ usuarios: ["u-raquel", "u-joao"] });
  const propria = item({ usuarios: ["u-raquel"] });
  const todos = agruparPorColaborador([compartilhada, propria], PESSOAS);
  assert.deepEqual(todos.map((g) => g.titulo), ["João", "Raquel"]);
  assert.deepEqual(manterColaboradoresFiltrados(todos, ["u-raquel"]).map((g) => g.titulo), ["Raquel"]);
  assert.deepEqual(manterColaboradoresFiltrados(todos, ["u-raquel", "u-joao"]).map((g) => g.titulo), ["João", "Raquel"]);
  assert.equal(manterColaboradoresFiltrados(todos, []).length, 2);
  assert.equal(manterColaboradoresFiltrados(todos, undefined).length, 2);
});
