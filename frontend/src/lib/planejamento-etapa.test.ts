import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  dataPuraValida,
  erroDaJanela,
  estadoDaJanela,
  estadoDoFormulario,
  formatarDataPlanejada,
  lerPercentualAlocavel,
  percentualAlocavelValido,
  planejamentoDaEtapa,
  resumoDoPlanejamento,
  salvarPlanejamento,
  TEXTO_ERRO_FIM_ANTES_DO_INICIO,
  TEXTO_ERRO_FIM_SEM_INICIO,
  TEXTO_PLANEJAMENTO_INCOMPLETO,
} from "./planejamento-etapa.ts";

const ler = (p: string) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

test("estado da janela é derivado do par: nada, incompleto, planejado; fim sem início é inválido", () => {
  assert.equal(estadoDaJanela(null, null), "nao_planejado");
  assert.equal(estadoDaJanela("", ""), "nao_planejado");
  assert.equal(estadoDaJanela("2026-10-20", null), "incompleto");
  assert.equal(estadoDaJanela("2026-10-20", ""), "incompleto");
  assert.equal(estadoDaJanela("2026-10-20", "2026-10-20"), "planejado");
  assert.equal(estadoDaJanela("2026-10-20", "2026-10-30"), "planejado");
  assert.equal(estadoDaJanela(null, "2026-10-30"), null);
});

test("o par digitado é validado como no servidor: fim exige início e não pode ser anterior", () => {
  assert.equal(erroDaJanela("", ""), null);
  assert.equal(erroDaJanela("2026-10-20", ""), null);
  assert.equal(erroDaJanela("2026-10-20", "2026-10-20"), null);
  assert.equal(erroDaJanela("2026-10-20", "2026-10-30"), null);
  assert.equal(erroDaJanela("", "2026-10-30"), TEXTO_ERRO_FIM_SEM_INICIO);
  assert.equal(erroDaJanela("2026-10-30", "2026-10-20"), TEXTO_ERRO_FIM_ANTES_DO_INICIO);
  assert.match(String(erroDaJanela("2026-02-31", "")), /válida/);
  assert.match(String(erroDaJanela("2026-10-20", "20/10/2026")), /válida/);
});

test("datas puras: formato por texto (sem fuso) e calendário real", () => {
  assert.equal(dataPuraValida("2026-02-28"), true);
  assert.equal(dataPuraValida("2024-02-29"), true);
  assert.equal(dataPuraValida("2026-02-29"), false);
  assert.equal(dataPuraValida("2026-10-20T00:00:00"), false);
  assert.equal(formatarDataPlanejada("2026-10-20"), "20/10/2026");
  assert.equal(formatarDataPlanejada("2026-01-01"), "01/01/2026");
  assert.equal(formatarDataPlanejada(null), "—");
  assert.equal(formatarDataPlanejada("lixo"), "—");
});

test("leitura: sem planejamento não há indicação; incompleto é discreto; planejado mostra a janela", () => {
  assert.equal(resumoDoPlanejamento({ planejadoInicio: null, planejadoFim: null, estado: "nao_planejado" }), null);
  assert.deepEqual(resumoDoPlanejamento({ planejadoInicio: "2026-10-20", planejadoFim: null, estado: "incompleto" }), { texto: "Planejado a partir de 20/10/2026", incompleto: true });
  assert.deepEqual(resumoDoPlanejamento({ planejadoInicio: "2026-10-20", planejadoFim: "2026-10-30", estado: "planejado" }), { texto: "Planejado de 20/10/2026 até 30/10/2026", incompleto: false });
  assert.equal(TEXTO_PLANEJAMENTO_INCOMPLETO, "Planejamento incompleto");
  // etapa sem o campo (resposta anterior ao 11B.2B-A) = não planejada
  assert.deepEqual(planejamentoDaEtapa({}), { planejadoInicio: null, planejadoFim: null, estado: "nao_planejado" });
});

test("o texto de leitura nunca usa a linguagem do prazo", () => {
  for (const planejamento of [
    { planejadoInicio: "2026-10-20", planejadoFim: null, estado: "incompleto" as const },
    { planejadoInicio: "2026-10-20", planejadoFim: "2026-10-30", estado: "planejado" as const },
  ]) {
    assert.doesNotMatch(resumoDoPlanejamento(planejamento)!.texto, /prazo|vence|entrega|deadline/i);
  }
});

const NADA = { inicio: "", fim: "" };
const SO_INICIO = { inicio: "2026-10-20", fim: "" };
const COMPLETA = { inicio: "2026-10-20", fim: "2026-10-30" };

test("início sem fim é VÁLIDO: sem erro, Salvar habilitado e estado incompleto", () => {
  const f = estadoDoFormulario(NADA, SO_INICIO);
  assert.equal(f.erro, null);
  assert.equal(f.podeSalvar, true);
  assert.equal(f.estado, "incompleto");
  assert.deepEqual(f.corpo, { planejadoInicio: "2026-10-20" }); // o fim NÃO viaja (não alterado)
  assert.equal(erroDaJanela("2026-10-20", ""), null);
  // a mensagem de "fim anterior" nunca aparece sem um fim preenchido
  for (const inicio of ["2026-10-20", "2026-01-01", "2027-12-31"]) assert.notEqual(erroDaJanela(inicio, ""), TEXTO_ERRO_FIM_ANTES_DO_INICIO);
});

test("fim sem início é inválido; fim anterior é inválido; mesma data é válida", () => {
  const semInicio = estadoDoFormulario(NADA, { inicio: "", fim: "2026-10-30" });
  assert.equal(semInicio.erro, TEXTO_ERRO_FIM_SEM_INICIO);
  assert.equal(semInicio.podeSalvar, false);
  assert.equal(semInicio.estado, null);
  const anterior = estadoDoFormulario(SO_INICIO, { inicio: "2026-10-20", fim: "2026-10-15" });
  assert.equal(anterior.erro, TEXTO_ERRO_FIM_ANTES_DO_INICIO);
  assert.equal(anterior.podeSalvar, false);
  const mesmoDia = estadoDoFormulario(SO_INICIO, { inicio: "2026-10-20", fim: "2026-10-20" });
  assert.equal(mesmoDia.erro, null);
  assert.equal(mesmoDia.podeSalvar, true);
  assert.equal(mesmoDia.estado, "planejado");
});

test("A) etapa nula: preencher só o início manda só o início; completar depois manda só o fim", () => {
  assert.deepEqual(estadoDoFormulario(NADA, SO_INICIO).corpo, { planejadoInicio: "2026-10-20" });
  assert.deepEqual(estadoDoFormulario(SO_INICIO, COMPLETA).corpo, { planejadoFim: "2026-10-30" });
  assert.deepEqual(estadoDoFormulario(NADA, COMPLETA).corpo, { planejadoInicio: "2026-10-20", planejadoFim: "2026-10-30" });
});

test("B) limpar SÓ o fim mantendo o início é válido (vira incompleto) e manda fim = null sem tocar no início", () => {
  const f = estadoDoFormulario(COMPLETA, SO_INICIO);
  assert.equal(f.erro, null);
  assert.equal(f.podeSalvar, true);
  assert.equal(f.estado, "incompleto");
  assert.deepEqual(f.corpo, { planejadoFim: null });
  assert.equal("planejadoInicio" in f.corpo!, false);
});

test("C) limpar SÓ o início mantendo o fim é inválido e não envia nada", async () => {
  const f = estadoDoFormulario(COMPLETA, { inicio: "", fim: "2026-10-30" });
  assert.equal(f.erro, TEXTO_ERRO_FIM_SEM_INICIO);
  assert.equal(f.podeSalvar, false);
  let chamadas = 0;
  const r = await salvarPlanejamento(COMPLETA, { inicio: "", fim: "2026-10-30" }, async () => { chamadas++; return 1; });
  assert.deepEqual(r, { ok: false, mensagem: TEXTO_ERRO_FIM_SEM_INICIO });
  assert.equal(chamadas, 0);
});

test("D) limpar ambos é válido e manda os dois como null; limpar uma etapa já vazia não tem o que salvar", () => {
  const f = estadoDoFormulario(COMPLETA, NADA);
  assert.equal(f.erro, null);
  assert.equal(f.podeSalvar, true);
  assert.equal(f.estado, "nao_planejado");
  assert.deepEqual(f.corpo, { planejadoInicio: null, planejadoFim: null });
  const nada = estadoDoFormulario(NADA, NADA);
  assert.equal(nada.erro, null);
  assert.equal(nada.podeSalvar, false); // sem alteração (dirty = false)
  assert.equal(nada.corpo, null);
});

test("Salvar só fica habilitado com par válido E alteração; nunca envia string vazia", () => {
  for (const [atual, digitado] of [[NADA, SO_INICIO], [SO_INICIO, COMPLETA], [COMPLETA, SO_INICIO], [COMPLETA, NADA]] as const) {
    const { corpo, podeSalvar } = estadoDoFormulario(atual, digitado);
    assert.equal(podeSalvar, true);
    for (const valor of Object.values(corpo!)) assert.ok(valor === null || /^\d{4}-\d{2}-\d{2}$/.test(valor as string));
  }
  assert.equal(estadoDoFormulario(SO_INICIO, SO_INICIO).podeSalvar, false);
  assert.equal(estadoDoFormulario(COMPLETA, COMPLETA).podeSalvar, false);
});

test("salvar envia o PATCH parcial, propaga a mensagem do servidor e não chama a API sem alteração", async () => {
  const enviados: unknown[] = [];
  const salvar = async (corpo: unknown) => { enviados.push(corpo); return { ok: 1 }; };
  assert.deepEqual(await salvarPlanejamento(NADA, SO_INICIO, salvar), { ok: true, valor: { ok: 1 } });
  await salvarPlanejamento(SO_INICIO, COMPLETA, salvar);
  await salvarPlanejamento(COMPLETA, SO_INICIO, salvar);
  await salvarPlanejamento(COMPLETA, NADA, salvar);
  assert.deepEqual(enviados, [
    { planejadoInicio: "2026-10-20" },
    { planejadoFim: "2026-10-30" },
    { planejadoFim: null },
    { planejadoInicio: null, planejadoFim: null },
  ]);
  const antes = enviados.length;
  assert.deepEqual(await salvarPlanejamento(NADA, NADA, salvar), { ok: false, mensagem: "Nenhuma alteração para salvar." });
  assert.deepEqual(await salvarPlanejamento(SO_INICIO, { inicio: "2026-10-20", fim: "2026-10-19" }, salvar), { ok: false, mensagem: TEXTO_ERRO_FIM_ANTES_DO_INICIO });
  assert.equal(enviados.length, antes);
  assert.deepEqual(await salvarPlanejamento(NADA, SO_INICIO, async () => { throw new Error("Você não tem autoridade"); }), { ok: false, mensagem: "Você não tem autoridade" });
  assert.deepEqual(await salvarPlanejamento(NADA, SO_INICIO, async () => { throw new Error(""); }), { ok: false, mensagem: "Não foi possível salvar o planejamento." });
});

test("capacidade alocável: inteiro de 1 a 100, sem corrigir em silêncio", () => {
  for (const valor of [1, 50, 75, 100]) assert.equal(percentualAlocavelValido(valor), true);
  for (const valor of [0, 101, -1, 75.5, NaN, "75", null, undefined, true]) assert.equal(percentualAlocavelValido(valor), false);
  assert.equal(lerPercentualAlocavel("75"), 75);
  assert.equal(lerPercentualAlocavel(" 100 "), 100);
  assert.equal(lerPercentualAlocavel("1"), 1);
  for (const texto of ["", "0", "101", "-5", "7.5", "7,5", "abc", "1000", "1e2"]) assert.equal(lerPercentualAlocavel(texto), null, texto);
});

test("API: PATCH parcial no caminho do planejamento e mapeamento do estado do servidor", () => {
  const api = ler("lib/api-backend.ts");
  assert.match(api, /\/workflow\/etapas\/\$\{etapaId\}\/planejamento/);
  assert.match(api, /export async function ajustarPlanejamentoEtapaReal/);
  assert.match(api, /podeEditarPlanejamento: etapa\.podeEditarPlanejamento === true/);
  assert.match(api, /planejamento: etapa\.planejamento \?\?/);
  // planejamento NÃO é derivado de prazo nem de período da Demanda
  assert.doesNotMatch(api, /planejadoInicio:\s*[^\n]*(prazoEtapaAtual|dataInicio|dataFimPrevista)/);
  assert.doesNotMatch(api, /planejadoFim:\s*[^\n]*(prazoEtapaAtual|dataInicio|dataFimPrevista)/);
});

test("tela da etapa: autoridade vem do servidor, rótulos próprios e separação do prazo", () => {
  const tela = ler("components/demandas/PlanejamentoEtapa.tsx");
  assert.match(tela, /!somenteLeitura && etapa\.podeEditarPlanejamento === true/);
  assert.match(tela, /label="Planejado de"/);
  assert.match(tela, /rotuloAcessivel=\{`Planejado de, etapa \$\{etapa\.nome\}`\}/); // o nome acessível por etapa foi preservado
  assert.match(tela, /label="Planejado até"/);
  assert.match(tela, /Salvar planejamento/);
  assert.match(tela, /TEXTO_PLANEJAMENTO_INCOMPLETO/);
  assert.match(tela, /TEXTO_AJUDA_PLANEJAMENTO/);
  assert.match(tela, /setErro\(resultado\.mensagem\)/);
  // a validação e o "pode salvar" vêm de UMA função da lib — a tela não recompara datas por conta própria
  assert.match(tela, /estadoDoFormulario\(atual, \{ inicio, fim \}\)/);
  assert.match(tela, /disabled=\{salvando \|\| !formulario\.podeSalvar\}/);
  assert.doesNotMatch(semComentarios(tela), /new Date|Date\.parse|inicio\s*[<>]\s*fim|fim\s*[<>]\s*inicio/);
  // as duas datas (DATE puro, sem UTC) agora usam o DateField compartilhado — o mesmo valor "YYYY-MM-DD" ou "" que o input nativo entregava
  assert.equal((tela.match(/<DateField/g) ?? []).length, 2);
  assert.doesNotMatch(tela, /type="date"/);
  // não reaproveita o prazo, nem implementa estados que são da Fase B
  const codigo = semComentarios(tela);
  assert.doesNotMatch(codigo, /prazoEtapaAtual|formatPrazo|semDiaUtil|sem_dia_util|janelaVencida|janela_vencida/);
  assert.match(ler("components/demandas/DemandaFormSections.tsx"), /<PlanejamentoEtapa demandaId=/);
  // o texto de ajuda deixa claro que não é o prazo
  assert.match(ler("lib/planejamento-etapa.ts"), /Não é o prazo da tarefa/);
});

test("template de workflow NÃO recebe janela planejada", () => {
  for (const arquivo of ["components/workflows/WorkflowModeloFormModal.tsx", "types/workflow-modelo.ts"]) {
    assert.doesNotMatch(ler(arquivo), /planejado(Inicio|Fim)|planejamento/i, arquivo);
  }
});

test("Horário de expediente: campo compacto, ajuda, validação e envio do percentual", () => {
  const tela = ler("components/regra-expediente/RegraExpedienteView.tsx");
  assert.match(tela, /label="Capacidade alocável"/);
  assert.match(tela, /TEXTO_AJUDA_CAPACIDADE_ALOCAVEL/);
  assert.match(tela, /lerPercentualAlocavel\(percentualTexto\) === null/);
  assert.match(tela, /percentualCapacidadeAlocavel: regra\.percentualCapacidadeAlocavel \?\? PERCENTUAL_ALOCAVEL_PADRAO/);
  assert.match(tela, /Logout|logout/); // a tela segue com o resto da configuração
  assert.match(ler("lib/planejamento-etapa.ts"), /Percentual do expediente disponível para planejamento de tarefas\./);
  // Carga NÃO existe aqui
  assert.doesNotMatch(semComentarios(tela), /carga|ocupa[cç][aã]o|produtividade/i);
  assert.match(ler("types/regra-expediente.ts"), /percentualCapacidadeAlocavel: number/);
});

test("histórico: o evento de planejamento é descrito com as datas formatadas por texto", () => {
  const historico = ler("lib/historicoDemandaLabels.ts");
  assert.match(historico, /"demanda\.workflow_planejamento_alterado": \(dados\) => descreverPlanejamento\(dados\)/);
  assert.match(historico, /formatarDataPlanejada/);
});
