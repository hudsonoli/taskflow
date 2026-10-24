// P1_DATETIME_FIELD_UX — campo de DATA + HORA do TaskFlow (substitui o datetime-local nativo). `npm run test:datetime-field`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  combinarValor,
  dataExiste,
  formatarDataBr,
  interpretarTextos,
  MENSAGEM_DATA_INVALIDA,
  MENSAGEM_DATA_OBRIGATORIA,
  MENSAGEM_HORA_INVALIDA,
  MENSAGEM_HORA_OBRIGATORIA,
  montarGrade,
  parseDataBr,
  parseHora,
  rotuloDoDia,
  sanitizarData,
  sanitizarHora,
  separarValor,
  somarDias,
  somarMeses,
} from "./data-hora-campo.ts";
import { inputLocalParaIso, isoParaInputLocal } from "./prazo-operacional.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const EXIGE = { exigeHora: true };

test("data DD/MM/AAAA: válida, normaliza, rejeita inexistente e não adivinha sem barras", () => {
  assert.equal(parseDataBr("21/10/2026"), "2026-10-21");
  assert.equal(parseDataBr("1/2/2026"), "2026-02-01");
  assert.equal(parseDataBr(" 29/02/2028 "), "2028-02-29");
  for (const invalida of ["", "31/02/2026", "29/02/2027", "00/10/2026", "21/13/2026", "21/10/26", "21102026", "2026-10-21", "abc", "21/10/20266"]) assert.equal(parseDataBr(invalida), null, invalida);
  assert.equal(formatarDataBr("2026-10-21"), "21/10/2026");
  assert.equal(formatarDataBr(""), "");
  assert.equal(formatarDataBr("2026-02-30"), "");
  assert.equal(dataExiste(2026, 2, 29), false);
});

test("hora HH:MM: 00:00 e 23:59 válidas; 24:00, 12:60, texto e sem dois-pontos (549) NÃO são adivinhados", () => {
  assert.equal(parseHora("00:00"), "00:00");
  assert.equal(parseHora("23:59"), "23:59");
  assert.equal(parseHora("05:49"), "05:49");
  assert.equal(parseHora("5:49"), "05:49"); // inequívoco: só normaliza o zero
  for (const invalida of ["", "24:00", "12:60", "99:99", "549", "0549", "5:4", "ab:cd", "10:3", "10:", "10", "10:300", "-1:00"]) assert.equal(parseHora(invalida), null, invalida);
});

test("sanitização: só dígitos e separadores; colar '05:49 ' ou digitar letra não quebra", () => {
  assert.equal(sanitizarHora("05:49 "), "05:49");
  assert.equal(sanitizarHora("ab1c0:3x0"), "10:30");
  assert.equal(sanitizarHora("123456789"), "12345");
  assert.equal(sanitizarData("21/10/2026 x"), "21/10/2026");
  assert.equal(sanitizarData("21-10-2026"), "21102026");
});

test("valor do contrato: separa e recombina EXATAMENTE o 'YYYY-MM-DDTHH:MM' que o datetime-local entregava", () => {
  assert.deepEqual(separarValor("2026-10-21T05:49"), { data: "2026-10-21", hora: "05:49" });
  assert.deepEqual(separarValor(""), { data: "", hora: "" });
  assert.deepEqual(separarValor(null), { data: "", hora: "" });
  assert.deepEqual(separarValor("2026-10-21T25:00"), { data: "", hora: "" });
  assert.deepEqual(separarValor("2026-02-30T10:00"), { data: "", hora: "" });
  assert.equal(combinarValor("2026-10-21", "05:49"), "2026-10-21T05:49");
  assert.equal(combinarValor("2026-10-21", ""), null); // nunca inventa 00:00
  assert.equal(combinarValor("", "05:49"), null);
  for (const v of ["2026-10-21T00:00", "2026-12-31T23:59", "2028-02-29T12:30"]) {
    const { data, hora } = separarValor(v);
    assert.equal(combinarValor(data, hora), v);
  }
});

test("timezone preservado: o campo não converte fuso; a conversão para a API é a MESMA de antes (inputLocalParaIso/isoParaInputLocal)", () => {
  const valor = interpretarTextos("21/10/2026", "16:30", EXIGE).valor;
  assert.equal(valor, "2026-10-21T16:30"); // relógio local, sem fuso
  assert.equal(inputLocalParaIso(valor), new Date(2026, 9, 21, 16, 30, 0, 0).toISOString()); // mesmo caminho do campo antigo
  const iso = new Date(2026, 9, 21, 16, 30).toISOString();
  const redondo = separarValor(isoParaInputLocal(iso));
  assert.deepEqual(redondo, { data: "2026-10-21", hora: "16:30" }); // API → campo → API não desloca nada
  assert.equal(inputLocalParaIso(combinarValor(redondo.data, redondo.hora)), iso);
});

test("interpretar os dois textos: digitação parcial NÃO emite nem trava; só completo e válido vira valor", () => {
  assert.deepEqual(interpretarTextos("", "", EXIGE), { valor: "", erroData: null, erroHora: null }); // vazio = sem valor
  for (const parcial of ["1", "10", "10:", "10:3"]) {
    const r = interpretarTextos("21/10/2026", parcial, EXIGE);
    assert.equal(r.valor, undefined, parcial);
  }
  assert.equal(interpretarTextos("21/10/2026", "10:30", EXIGE).valor, "2026-10-21T10:30");
  assert.equal(interpretarTextos("21/10", "10:30", EXIGE).valor, undefined);
  assert.equal(interpretarTextos("21/10/2026", "24:00", EXIGE).erroHora, MENSAGEM_HORA_INVALIDA);
  assert.equal(interpretarTextos("21/10/2026", "12:60", EXIGE).erroHora, MENSAGEM_HORA_INVALIDA);
  assert.equal(interpretarTextos("21/10/2026", "texto", EXIGE).erroHora, MENSAGEM_HORA_INVALIDA);
  assert.equal(interpretarTextos("31/02/2026", "10:00", EXIGE).erroData, MENSAGEM_DATA_INVALIDA);
  assert.equal(MENSAGEM_HORA_INVALIDA, "Informe um horário válido entre 00:00 e 23:59.");
});

test("hora sem data é erro; data sem hora é pendência (nunca vira 00:00) e some se o campo não exige hora", () => {
  assert.equal(interpretarTextos("", "10:30", EXIGE).erroData, MENSAGEM_DATA_OBRIGATORIA);
  assert.equal(interpretarTextos("", "10:30", EXIGE).valor, undefined);
  const semHora = interpretarTextos("21/10/2026", "", EXIGE);
  assert.equal(semHora.valor, undefined);
  assert.equal(semHora.erroHora, MENSAGEM_HORA_OBRIGATORIA);
  assert.equal(interpretarTextos("21/10/2026", "", { exigeHora: false }).erroHora, null);
});

test("calendário: grade de domingo a sábado, 5–6 linhas, dias de fora completam as pontas", () => {
  const out2026 = montarGrade(2026, 10); // 1/10/2026 é quinta-feira
  assert.equal(out2026[0][0].iso, "2026-09-27");
  assert.equal(out2026[0][4].iso, "2026-10-01");
  assert.equal(out2026[0][4].doMes, true);
  assert.equal(out2026[0][0].doMes, false);
  assert.ok(out2026.length === 5 || out2026.length === 6);
  assert.ok(out2026.every((semana) => semana.length === 7));
  assert.equal(montarGrade(2026, 2).length, 4); // fevereiro/2026 começa no domingo e tem 28 dias: 4 semanas exatas
  assert.equal(montarGrade(2026, 2)[0][0].iso, "2026-02-01");
  assert.equal(montarGrade(2026, 5).length, 6); // maio/2026 começa na sexta
});

test("navegação do calendário: dias e meses sem 'pular' (31/01 + 1 mês = 28/02), anos bissextos", () => {
  assert.equal(somarDias("2026-10-31", 1), "2026-11-01");
  assert.equal(somarDias("2026-03-01", -1), "2026-02-28");
  assert.equal(somarMeses("2026-01-31", 1), "2026-02-28");
  assert.equal(somarMeses("2028-01-31", 1), "2028-02-29");
  assert.equal(somarMeses("2026-12-15", 1), "2027-01-15");
  assert.equal(somarMeses("2026-01-15", -1), "2025-12-15");
  assert.equal(rotuloDoDia("2026-10-22"), "quinta-feira, 22 de outubro de 2026");
});

// ── apresentação (source-scan): o que não dá para provar só com a lógica pura ──────────────────────────────────────

test("nenhuma superfície migrada usa datetime-local nativo: Prazo atual, Prazo (criação) e Retorno até usam o DateTimeField", () => {
  for (const arquivo of ["components/demandas/DemandaFormSections.tsx", "components/demandas/NovaDemandaModal.tsx", "components/demandas/EnvioClienteCard.tsx"]) {
    const codigo = semComentarios(ler(arquivo));
    assert.doesNotMatch(codigo, /type="datetime-local"/, arquivo);
    assert.match(codigo, /<DateTimeField/, arquivo);
  }
  assert.match(semComentarios(ler("components/demandas/DemandaFormSections.tsx")), /label="Prazo atual \(data e horário\)"/);
  assert.match(semComentarios(ler("components/demandas/EnvioClienteCard.tsx")), /label="Retorno até"/);
});

test("o contrato dos formulários NÃO mudou: mesmo valor local sem fuso, mesma conversão para a API, mesmo payload", () => {
  const form = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  assert.match(form, /inputLocalParaIso\(valor\)/); // prazo atual continua indo como instante ISO
  assert.match(form, /if \(valor === isoParaInputLocal\(demanda\.prazoEtapaAtual\)\) return;/);
  assert.match(form, /onCommit=\{\(valor\) => void salvarPrazo\(valor\)\}/);
  const envio = semComentarios(ler("components/demandas/EnvioClienteCard.tsx"));
  assert.match(envio, /prazoRetornoCliente: prazoRetorno,/); // retorno continua enviando o valor local, como antes
  const nova = semComentarios(ler("components/demandas/NovaDemandaModal.tsx"));
  assert.match(nova, /dataFimPrevista: dataDoInputLocal\(valor\)/);
  const campo = semComentarios(ler("components/ui/DateTimeField.tsx"));
  assert.doesNotMatch(campo, /toISOString|getTimezoneOffset|new Date\(/); // o campo não converte fuso
});

test("o campo não usa listas/spinners de hora e o calendário é só data", () => {
  const campo = semComentarios(ler("components/ui/DateTimeField.tsx"));
  assert.doesNotMatch(campo, /type="time"|type="datetime-local"|type="number"|<select|<Select/);
  assert.match(campo, /inputMode="numeric"/);
  assert.match(campo, /placeholder="HH:MM"/);
  assert.match(campo, /placeholder="DD\/MM\/AAAA"/);
  const calendario = semComentarios(ler("components/ui/Calendario.tsx"));
  assert.doesNotMatch(calendario, /(?<![-\w])(horas?|minutos?)(?![-\w])|<select|spinner/i); // (o caminho "data-hora-campo" do import não conta)
  assert.match(calendario, /aria-current=\{ehHoje \? "date" : undefined\}/);
  assert.match(calendario, /aria-selected=\{escolhido\}/);
  assert.match(calendario, /Hoje/);
  assert.match(calendario, /Limpar/);
  assert.match(calendario, /PageUp/);
});

test("popover reaproveita o primitive existente (portal fixo com colisão) e sem tema Glass nem dependência nova", () => {
  const campo = semComentarios(ler("components/ui/DateTimeField.tsx"));
  assert.match(campo, /import \{ PainelFlutuante \} from "@\/components\/filtros\/PainelFlutuante";/);
  for (const arquivo of ["components/ui/DateTimeField.tsx", "components/ui/Calendario.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /backdrop-blur|glass|bg-gradient/i, arquivo);
  }
  const pacote = JSON.parse(readFileSync(new URL("../../package.json", import.meta.url), "utf8")) as { dependencies: Record<string, string> };
  for (const proibida of ["date-fns", "dayjs", "react-day-picker", "react-datepicker", "luxon", "moment"]) assert.equal(proibida in pacote.dependencies, false, proibida);
});
