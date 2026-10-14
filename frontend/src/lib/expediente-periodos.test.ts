// Expediente (Fase 1) — regras puras da tela de configuração + estrutura (nada de bloqueio/pausa ativos). `npm run test:expediente`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  diaDaSemanaDe,
  diasNormalizados,
  diasParaEnvio,
  errosDaSemana,
  formatarDataIso,
  horasDoDia,
  MAX_PERIODOS_POR_DIA,
  normalizarHora,
  opcoesDeFuso,
  ordenarPeriodos,
  resumoDoDia,
  sugerirNovoPeriodo,
  validarPeriodos,
} from "./expediente-periodos.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const UTIL = [
  { inicio: "08:00", fim: "12:00" },
  { inicio: "13:00", fim: "18:00" },
];

test("horas da API ('HH:MM:SS') viram 'HH:MM'; vazio e lixo viram vazio", () => {
  assert.equal(normalizarHora("09:00:00"), "09:00");
  assert.equal(normalizarHora("9:05"), "09:05");
  assert.equal(normalizarHora("18:30"), "18:30");
  assert.equal(normalizarHora(""), "");
  assert.equal(normalizarHora(null), "");
  assert.equal(normalizarHora("abc"), "");
});

test("períodos são ordenados pelo início, sem alterar a lista original", () => {
  const original = [UTIL[1], UTIL[0]];
  assert.deepEqual(ordenarPeriodos(original), UTIL);
  assert.deepEqual(original, [UTIL[1], UTIL[0]]);
});

test("validação: 0, 1, 2 e 3 períodos válidos; períodos que só se tocam são aceitos", () => {
  assert.equal(validarPeriodos([]), null);
  assert.equal(validarPeriodos([UTIL[0]]), null);
  assert.equal(validarPeriodos(UTIL), null);
  assert.equal(validarPeriodos([...UTIL, { inicio: "19:00", fim: "21:00" }]), null);
  assert.equal(validarPeriodos([{ inicio: "08:00", fim: "12:00" }, { inicio: "12:00", fim: "18:00" }]), null);
});

test("validação: início depois/igual ao fim, atravessar a meia-noite, vazio, sobreposição e excesso", () => {
  assert.match(validarPeriodos([{ inicio: "12:00", fim: "08:00" }]) ?? "", /começar antes de terminar/);
  assert.match(validarPeriodos([{ inicio: "08:00", fim: "08:00" }]) ?? "", /começar antes de terminar/);
  assert.match(validarPeriodos([{ inicio: "22:00", fim: "02:00" }]) ?? "", /meia-noite/);
  assert.match(validarPeriodos([{ inicio: "", fim: "12:00" }]) ?? "", /Preencha/);
  assert.match(validarPeriodos([{ inicio: "08:00", fim: "12:00" }, { inicio: "11:59", fim: "13:00" }]) ?? "", /se sobrepõem/);
  // a lista pode estar fora de ordem: a sobreposição é detectada do mesmo jeito
  assert.match(validarPeriodos([{ inicio: "11:00", fim: "13:00" }, { inicio: "08:00", fim: "12:00" }]) ?? "", /se sobrepõem/);
  const muitos = Array.from({ length: MAX_PERIODOS_POR_DIA + 1 }, (_, i) => ({ inicio: `${String(i).padStart(2, "0")}:00`, fim: `${String(i).padStart(2, "0")}:30` }));
  assert.match(validarPeriodos(muitos) ?? "", /No máximo/);
});

test("erros por dia: só os dias com problema aparecem", () => {
  const erros = errosDaSemana([
    { diaSemana: 0, periodos: UTIL },
    { diaSemana: 1, periodos: [{ inicio: "10:00", fim: "09:00" }] },
    { diaSemana: 5, periodos: [] },
  ]);
  assert.deepEqual(Object.keys(erros), ["1"]);
});

test("+ período: sugere 08–12 no dia fechado, 4 h depois do último e nada quando não há espaço", () => {
  assert.deepEqual(sugerirNovoPeriodo([]), { inicio: "08:00", fim: "12:00" });
  assert.deepEqual(sugerirNovoPeriodo([{ inicio: "08:00", fim: "12:00" }]), { inicio: "12:00", fim: "16:00" });
  assert.deepEqual(sugerirNovoPeriodo(UTIL), { inicio: "18:00", fim: "22:00" });
  assert.deepEqual(sugerirNovoPeriodo([{ inicio: "08:00", fim: "21:00" }]), { inicio: "21:00", fim: "23:59" });
  assert.equal(sugerirNovoPeriodo([{ inicio: "08:00", fim: "23:30" }]), null);
  const cheio = Array.from({ length: MAX_PERIODOS_POR_DIA }, (_, i) => ({ inicio: `${String(i).padStart(2, "0")}:00`, fim: `${String(i).padStart(2, "0")}:30` }));
  assert.equal(sugerirNovoPeriodo(cheio), null);
});

test("resumo e horas do dia", () => {
  assert.equal(resumoDoDia([]), "Fechado");
  assert.equal(resumoDoDia([UTIL[1], UTIL[0]]), "08:00–12:00 · 13:00–18:00");
  assert.equal(horasDoDia(UTIL), 9);
  assert.equal(horasDoDia([{ inicio: "08:00", fim: "12:30" }]), 4.5);
  assert.equal(horasDoDia([]), 0);
});

test("os 7 dias são sempre completos, em ordem, normalizados e ordenados; o envio não leva campos legados", () => {
  const dias = diasNormalizados([
    { diaSemana: 2, periodos: [{ inicio: "13:00:00", fim: "18:00:00" }, { inicio: "08:00:00", fim: "12:00:00" }] },
    { diaSemana: 0, periodos: [] },
  ]);
  assert.deepEqual(dias.map((d) => d.diaSemana), [0, 1, 2, 3, 4, 5, 6]);
  assert.deepEqual(dias[2].periodos, UTIL);
  assert.deepEqual(dias[6].periodos, []);
  for (const dia of diasParaEnvio(dias)) {
    assert.deepEqual(Object.keys(dia).sort(), ["diaSemana", "periodos"]);
  }
});

test("datas: dia da semana e formatação independem do fuso do navegador", () => {
  assert.equal(diaDaSemanaDe("2026-10-12"), 0); // segunda
  assert.equal(diaDaSemanaDe("2026-10-17"), 5); // sábado
  assert.equal(diaDaSemanaDe("2026-10-18"), 6); // domingo
  assert.equal(formatarDataIso("2026-10-12"), "12/10/2026");
});

test("o fuso atual da empresa sempre aparece nas opções", () => {
  assert.equal(opcoesDeFuso("America/Sao_Paulo")[0].value, "America/Sao_Paulo");
  assert.equal(opcoesDeFuso("Asia/Tokyo")[0].value, "Asia/Tokyo");
  assert.ok(opcoesDeFuso("Asia/Tokyo").some((o) => o.value === "America/Manaus"));
});

// ── estrutura: nada de bloqueio/pausa ativos nesta fase ──────────────────────────────────────────────────────────

test("a tela envia o bloqueio e o logout automático (Fase 2), mas NUNCA a pausa automática nem feriados automáticos", () => {
  const view = semComentarios(ler("components/regra-expediente/RegraExpedienteView.tsx"));
  const envio = view.slice(view.indexOf("atualizarRegraExpedienteReal({"), view.indexOf("});", view.indexOf("atualizarRegraExpedienteReal({")));
  for (const chave of ["ativo", "toleranciaRetomadaMinutos", "antecedenciaAcessoMinutos", "timezone", "dias", "bloquearForaExpediente", "logoutAutomaticoAtivo", "logoutHorario"]) assert.ok(envio.includes(chave), chave);
  for (const proibida of ["pausarNoFimPeriodo", "feriadosAutomaticos"]) assert.equal(envio.includes(proibida), false, proibida);
  // só o interruptor de PAUSA continua travado e avisa que fica para a próxima etapa
  assert.equal((view.match(/checked=\{false\}\s+disabled/g) ?? []).length, 1);
  assert.ok((view.match(/Será ativado em uma próxima etapa/g) ?? []).length >= 1);
  // a antiga promessa de pausa automática não pode voltar a aparecer
  assert.equal(/pausadas automaticamente|pausas automáticas ativas/i.test(view), false);
});

test("a tela mantém os controles prometidos: ativar controle, antecedência, fuso, períodos por dia e dias especiais", () => {
  const view = semComentarios(ler("components/regra-expediente/RegraExpedienteView.tsx"));
  for (const texto of ["Ativar controle de expediente", "Bloquear usuários fora do expediente", "Pausar atividades ao final dos períodos", "Antecedência para acesso", "Fuso horário da empresa", "Horário semanal"]) {
    assert.ok(view.includes(texto), texto);
  }
  assert.match(view, /<PeriodosDoDia/);
  assert.match(view, /<DiasEspeciaisSection/);
  const periodos = semComentarios(ler("components/regra-expediente/PeriodosDoDia.tsx"));
  assert.match(periodos, /aria-label=\{`\$\{nome\}: remover período/); // remover período, acessível
  assert.match(periodos, /período\s*<\/button>/); // botão "+ período"
});

test("dias especiais: cadastro manual sem enviar a origem, e a importação automática não existe", () => {
  const secao = semComentarios(ler("components/regra-expediente/DiasEspeciaisSection.tsx"));
  assert.match(secao, /criarDiaEspecialReal\(\{ data, nome: nome\.trim\(\), tipo, ativo: true/);
  assert.equal(/origem\s*:/.test(secao.slice(secao.indexOf("criarDiaEspecialReal({"), secao.indexOf("criarDiaEspecialReal({") + 220)), false);
  const api = ler("lib/api-backend.ts");
  assert.equal(/brasilapi\.com\.br\/api\/feriados/i.test(api), false);
  assert.equal(/feriados\/v1/i.test(api), false);
});

test("usuário: o campo de isenção existe no tipo, no payload e no formulário (só para o usuário comum)", () => {
  assert.match(ler("types/usuario.ts"), /acessoForaExpediente: boolean/);
  const api = ler("lib/api-backend.ts");
  assert.match(api, /acessoForaExpediente: draft\.acessoForaExpediente/);
  assert.match(api, /acessoForaExpediente: data\.acessoForaExpediente \?\? false/);
  const form = semComentarios(ler("components/usuarios/UsuarioFormModal.tsx"));
  assert.match(form, /Permitir acesso fora do expediente/);
  assert.match(form, /perfilTecnico\(draft\.perfil\) === "operador"/);
});

test("o 403 FORA_DO_EXPEDIENTE é tratado SÓ nos módulos centrais (expediente-acesso) — telas e cliente HTTP não o conhecem", () => {
  assert.equal(ler("lib/expediente-acesso.ts").includes("FORA_DO_EXPEDIENTE"), true);
  for (const arquivo of ["lib/api-backend.ts", "components/layout/AppShell.tsx", "lib/api.ts", "lib/sessao-expirada.ts"]) {
    assert.equal(semComentarios(ler(arquivo)).includes("FORA_DO_EXPEDIENTE"), false, arquivo);
  }
});

test("dias especiais: aviso claro de que, até o novo controle, dias ativos já afetam dias úteis, entrada em execução e prazos", () => {
  const secao = semComentarios(ler("components/regra-expediente/DiasEspeciaisSection.tsx"));
  assert.match(secao, /role="note"/);
  assert.match(secao, /enquanto o novo controle de expediente não estiver ativado/);
  assert.match(secao, /já afetam/);
  assert.match(secao, /entrada em execução/);
  assert.match(secao, /cálculos de prazo \(SLA\)/);
});
