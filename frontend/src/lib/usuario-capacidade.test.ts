// 11B.2D-B — testes da UI administrativa de Jornada e Ausências. `npm run test:usuario-capacidade` (node --test, sem DOM).
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import { podeEditarUsuario } from "./autoridadeUsuarios.ts";
import { sugerirNovoPeriodo } from "./expediente-periodos.ts";
import {
  AUSENCIA_VAZIA,
  OPCOES_TIPO_AUSENCIA,
  TEXTOS_PROIBIDOS_NA_CAPACIDADE,
  TEXTO_IMPACTO_CARGA,
  corpoDaAusencia,
  corpoDaJornada,
  diasDaAusencia,
  draftDaAusencia,
  errosDaJornada,
  formatarPeriodoAusencia,
  grade,
  horasDaSemana,
  hojeLocalIso,
  jornadaIgual,
  jornadaPendente,
  jornadaTodaFechada,
  mensagemDeErroCapacidade,
  normalizarJornadaDaApi,
  patchDaAusencia,
  podeSalvarJornada,
  resumoDaSemana,
  rotuloDoTipoAusencia,
  rotuloDuracaoAusencia,
  separarAusencias,
  sobrepoeOutraAusencia,
  validarAusencia,
} from "./usuario-capacidade.ts";
import type { AusenciaUsuario, JornadaDiaUsuario, JornadaUsuario } from "../types/usuario-capacidade.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

// ── fixtures ─────────────────────────────────────────────────────────────────────────────────────────────────

const util = [{ inicio: "09:00:00", fim: "12:00:00" }, { inicio: "13:00:00", fim: "18:00:00" }];
const apiDias = (extra: Record<number, Array<{ inicio: string; fim: string }>> = {}) =>
  [0, 1, 2, 3, 4, 5, 6].map((d) => ({ diaSemana: d, periodos: extra[d] ?? (d < 5 ? util : []) }));

const empresa = (): JornadaUsuario => normalizarJornadaDaApi({ usuarioId: "u1", personalizada: false, dias: apiDias(), updatedAt: null });
const propria = (extra: Record<number, Array<{ inicio: string; fim: string }>> = {}): JornadaUsuario =>
  normalizarJornadaDaApi({ usuarioId: "u1", personalizada: true, dias: apiDias({ 0: [{ inicio: "09:00:00", fim: "15:00:00" }], 1: [{ inicio: "09:00:00", fim: "15:00:00" }], 2: [], 3: [], 4: [], ...extra }), updatedAt: "2026-10-21T10:00:00Z" });

const ausencia = (extra: Partial<AusenciaUsuario> = {}): AusenciaUsuario => ({
  id: "a1", usuarioId: "u1", tipo: "ferias", inicio: "2026-11-03", fim: "2026-11-13", observacao: null, createdAt: "2026-10-21T10:00:00Z", updatedAt: "2026-10-21T10:00:00Z", ...extra,
});

// ── jornada: fallback e personalizada ────────────────────────────────────────────────────────────────────────

test("a API devolve HH:MM:SS; a tela trabalha com os 7 dias em HH:MM", () => {
  const j = empresa();
  assert.equal(j.dias.length, 7);
  assert.deepEqual(j.dias[0].periodos, [{ inicio: "09:00", fim: "12:00" }, { inicio: "13:00", fim: "18:00" }]);
  assert.deepEqual(j.dias[5].periodos, []);
  assert.equal(j.personalizada, false);
});

test("fallback da empresa: nenhuma mudança pendente e nada a salvar; o resumo é só leitura", () => {
  const j = empresa();
  assert.equal(jornadaPendente(j, "empresa", grade(j.dias)), false);
  assert.equal(podeSalvarJornada({ servidor: j, modo: "empresa", dias: grade(j.dias), somenteLeitura: false, salvando: false }), false);
  assert.deepEqual(resumoDaSemana(j.dias), [{ dias: "Seg–Sex", texto: "09:00–12:00 · 13:00–18:00" }, { dias: "Sáb–Dom", texto: "Fechado" }]);
});

test("escolher 'Jornada personalizada' (sem jornada gravada) já é mudança pendente — só vale depois de Salvar; a grade inicial é cópia do expediente, sem tocar o original", () => {
  const j = empresa();
  const dias = grade(j.dias);
  assert.equal(jornadaPendente(j, "personalizada", dias), true);
  assert.equal(podeSalvarJornada({ servidor: j, modo: "personalizada", dias, somenteLeitura: false, salvando: false }), true);
  dias[0] = { ...dias[0], periodos: [] };
  assert.equal(j.dias[0].periodos.length, 2); // o original (expediente da empresa) não foi alterado
});

test("jornada personalizada gravada: só há pendência quando a grade mudou (dirty)", () => {
  const j = propria();
  assert.equal(jornadaPendente(j, "personalizada", grade(j.dias)), false);
  const editada = grade(j.dias).map((d) => (d.diaSemana === 2 ? { ...d, periodos: [{ inicio: "09:00", fim: "13:00" }] } : d));
  assert.equal(jornadaPendente(j, "personalizada", editada), true);
  assert.equal(jornadaIgual(j.dias, editada), false);
  assert.equal(jornadaIgual(j.dias, grade(j.dias)), true);
});

test("dia fechado, múltiplos períodos, adicionar e remover período", () => {
  const j = propria();
  assert.deepEqual(j.dias[2].periodos, []); // quarta fechada
  assert.deepEqual(resumoDaSemana(j.dias).find((l) => l.dias === "Qua–Dom"), { dias: "Qua–Dom", texto: "Fechado" });
  const dia = [{ inicio: "09:00", fim: "12:00" }];
  const sugestao = sugerirNovoPeriodo(dia);
  assert.deepEqual(sugestao, { inicio: "12:00", fim: "16:00" }); // + período logo depois do último
  const com = [...dia, sugestao!];
  assert.equal(com.length, 2);
  assert.equal(com.filter((_, i) => i !== 0).length, 1); // remover
  assert.deepEqual(sugerirNovoPeriodo([]), { inicio: "08:00", fim: "12:00" }); // dia fechado → sugestão padrão
});

test("validação: fim <= início, sobreposição e hora vazia impedem salvar (a mesma lógica do Horário de expediente)", () => {
  const base = propria();
  const comDia = (periodos: Array<{ inicio: string; fim: string }>): JornadaDiaUsuario[] => base.dias.map((d) => (d.diaSemana === 2 ? { ...d, periodos } : d));
  for (const invalido of [[{ inicio: "12:00", fim: "09:00" }], [{ inicio: "09:00", fim: "09:00" }], [{ inicio: "09:00", fim: "12:00" }, { inicio: "11:00", fim: "14:00" }], [{ inicio: "", fim: "12:00" }]]) {
    const dias = comDia(invalido);
    assert.ok(errosDaJornada(dias)[2], JSON.stringify(invalido));
    assert.equal(podeSalvarJornada({ servidor: base, modo: "personalizada", dias, somenteLeitura: false, salvando: false }), false);
  }
  assert.deepEqual(errosDaJornada(comDia([{ inicio: "09:00", fim: "12:00" }, { inicio: "12:00", fim: "14:00" }])), {}); // períodos que só se tocam são válidos
  assert.match(String(errosDaJornada(comDia([{ inicio: "09:00", fim: "12:00" }, { inicio: "11:00", fim: "14:00" }]))[2]), /se sobrepõem/);
});

test("Salvar só habilita com mudança + válido + autoridade + sem salvamento em curso", () => {
  const j = empresa();
  const dias = grade(j.dias);
  const ok = { servidor: j, modo: "personalizada" as const, dias, somenteLeitura: false, salvando: false };
  assert.equal(podeSalvarJornada(ok), true);
  assert.equal(podeSalvarJornada({ ...ok, somenteLeitura: true }), false);
  assert.equal(podeSalvarJornada({ ...ok, salvando: true }), false);
});

test("o PUT leva a grade COMPLETA (7 dias) ordenada, em HH:MM", () => {
  const corpo = corpoDaJornada(propria().dias);
  assert.equal(corpo.length, 7);
  assert.deepEqual(corpo.map((d) => d.diaSemana), [0, 1, 2, 3, 4, 5, 6]);
  assert.deepEqual(corpo[0].periodos, [{ inicio: "09:00", fim: "15:00" }]);
  assert.deepEqual(corpo[2].periodos, []);
  const desordenado = grade(propria().dias).map((d) => (d.diaSemana === 0 ? { ...d, periodos: [{ inicio: "13:00", fim: "17:00" }, { inicio: "09:00", fim: "12:00" }] } : d));
  assert.deepEqual(corpoDaJornada(desordenado)[0].periodos, [{ inicio: "09:00", fim: "12:00" }, { inicio: "13:00", fim: "17:00" }]);
});

test("horas da semana e jornada toda fechada (capacidade zero explícita)", () => {
  assert.equal(horasDaSemana(propria().dias), 12);
  const fechada = grade(propria().dias).map((d) => ({ ...d, periodos: [] }));
  assert.equal(jornadaTodaFechada(fechada), true);
  assert.equal(jornadaTodaFechada(propria().dias), false);
  assert.deepEqual(errosDaJornada(fechada), {}); // válida
});

// ── ausências ────────────────────────────────────────────────────────────────────────────────────────────────

test("tipos traduzidos; nunca o enum cru", () => {
  assert.deepEqual(OPCOES_TIPO_AUSENCIA.map((o) => o.label), ["Férias", "Afastamento", "Folga", "Outro"]);
  assert.equal(rotuloDoTipoAusencia("ferias"), "Férias");
  assert.equal(rotuloDoTipoAusencia("afastamento"), "Afastamento");
  assert.equal(rotuloDoTipoAusencia("folga"), "Folga");
  assert.equal(rotuloDoTipoAusencia("outro"), "Outro");
  assert.equal(rotuloDoTipoAusencia("licenca_xyz"), "Outro");
});

test("período: um dia e intervalo; duração inclusiva", () => {
  assert.equal(formatarPeriodoAusencia("2026-11-20", "2026-11-20"), "20/11/2026");
  assert.equal(formatarPeriodoAusencia("2026-11-03", "2026-11-13"), "03/11/2026 – 13/11/2026");
  assert.equal(diasDaAusencia("2026-11-03", "2026-11-13"), 11);
  assert.equal(rotuloDuracaoAusencia("2026-11-20", "2026-11-20"), "1 dia");
  assert.equal(rotuloDuracaoAusencia("2026-10-30", "2026-11-02"), "4 dias"); // atravessa mês
});

test("lista: vazia, uma, várias; atuais/futuras primeiro (mais próxima no topo), passadas depois (mais recente primeiro); nada é escondido", () => {
  assert.deepEqual(separarAusencias([], "2026-11-01"), { proximas: [], passadas: [] });
  const so = ausencia();
  assert.deepEqual(separarAusencias([so], "2026-11-01").proximas.map((a) => a.id), ["a1"]);
  const varias = [
    ausencia({ id: "passada-antiga", inicio: "2026-08-01", fim: "2026-08-05" }),
    ausencia({ id: "futura-longe", inicio: "2026-12-10", fim: "2026-12-20" }),
    ausencia({ id: "atual", inicio: "2026-10-28", fim: "2026-11-01" }), // termina hoje: ainda atual
    ausencia({ id: "passada-recente", inicio: "2026-09-10", fim: "2026-09-12" }),
    ausencia({ id: "futura-perto", inicio: "2026-11-10", fim: "2026-11-11" }),
  ];
  const { proximas, passadas } = separarAusencias(varias, "2026-11-01");
  assert.deepEqual(proximas.map((a) => a.id), ["atual", "futura-perto", "futura-longe"]);
  assert.deepEqual(passadas.map((a) => a.id), ["passada-recente", "passada-antiga"]);
  assert.equal(proximas.length + passadas.length, varias.length);
  assert.match(hojeLocalIso(new Date(2026, 10, 1)), /^2026-11-01$/);
});

test("criar: um dia (início = fim) e intervalo são válidos; observação é opcional e vazia vira null", () => {
  assert.deepEqual(validarAusencia({ ...AUSENCIA_VAZIA, tipo: "folga", inicio: "2026-11-20", fim: "2026-11-20" }), {});
  assert.deepEqual(validarAusencia({ ...AUSENCIA_VAZIA, inicio: "2026-11-03", fim: "2026-11-13" }), {});
  assert.deepEqual(corpoDaAusencia({ tipo: "folga", inicio: "2026-11-20", fim: "2026-11-20", observacao: "   " }), { tipo: "folga", inicio: "2026-11-20", fim: "2026-11-20", observacao: null });
  assert.equal(corpoDaAusencia({ tipo: "ferias", inicio: "2026-11-03", fim: "2026-11-13", observacao: " Viagem " }).observacao, "Viagem");
});

test("validação: fim < início, datas vazias e observação longa; não existe hora", () => {
  assert.match(validarAusencia({ ...AUSENCIA_VAZIA, inicio: "2026-11-13", fim: "2026-11-03" }).fim ?? "", /anterior/);
  const vazio = validarAusencia(AUSENCIA_VAZIA);
  assert.ok(vazio.inicio && vazio.fim);
  assert.ok(validarAusencia({ ...AUSENCIA_VAZIA, inicio: "2026-11-03", fim: "2026-11-03", observacao: "x".repeat(501) }).observacao);
  assert.deepEqual(Object.keys(corpoDaAusencia({ ...AUSENCIA_VAZIA, inicio: "2026-11-03", fim: "2026-11-03" })).sort(), ["fim", "inicio", "observacao", "tipo"]); // sem hora, sem "diaInteiro"
});

test("editar: o PATCH leva só o que mudou; nada mudou → nenhuma chamada", () => {
  const original = ausencia({ observacao: "Viagem" });
  assert.equal(patchDaAusencia(original, draftDaAusencia(original)), null);
  assert.deepEqual(patchDaAusencia(original, { ...draftDaAusencia(original), fim: "2026-11-10" }), { fim: "2026-11-10" });
  assert.deepEqual(patchDaAusencia(original, { ...draftDaAusencia(original), tipo: "folga", observacao: "" }), { tipo: "folga", observacao: null });
  assert.equal(draftDaAusencia(ausencia({ tipo: "enum_desconhecido" })).tipo, "outro");
});

test("sobreposição: só AVISO (o backend aceita); ignora a própria ausência na edição", () => {
  const existentes = [ausencia({ id: "x", inicio: "2026-11-03", fim: "2026-11-13" })];
  assert.equal(sobrepoeOutraAusencia({ inicio: "2026-11-10", fim: "2026-11-20" }, existentes), true);
  assert.equal(sobrepoeOutraAusencia({ inicio: "2026-11-14", fim: "2026-11-20" }, existentes), false);
  assert.equal(sobrepoeOutraAusencia({ inicio: "2026-11-13", fim: "2026-11-13" }, existentes), true); // o último dia é inclusivo
  assert.equal(sobrepoeOutraAusencia({ inicio: "2026-11-05", fim: "2026-11-06" }, existentes, "x"), false);
  assert.equal(sobrepoeOutraAusencia({ inicio: "", fim: "" }, existentes), false);
  assert.deepEqual(validarAusencia({ ...AUSENCIA_VAZIA, inicio: "2026-11-10", fim: "2026-11-20" }), {}); // não bloqueia
});

test("erros: a mensagem da API (403/404/422) é mostrada; sem mensagem, texto neutro", () => {
  assert.equal(mensagemDeErroCapacidade(new Error("Seu perfil só administra Usuários."), "x"), "Seu perfil só administra Usuários.");
  assert.equal(mensagemDeErroCapacidade(new Error("Erro 500"), "Não foi possível salvar."), "Não foi possível salvar.");
  assert.equal(mensagemDeErroCapacidade("???", "padrão"), "padrão");
});

// ── autoridade (espelha a lista de Usuários; o backend é a barreira) ─────────────────────────────────────────

test("autoridade: reutiliza podeEditarUsuario (usuarios.editar + hierarquia) — gestor edita Usuário, não Gestor nem a si mesmo; sem permissão é só leitura", () => {
  const gestor = { id: "g", perfil: "gestor" as const, permissoes: ["usuarios.editar", "usuarios.visualizar"] };
  assert.equal(podeEditarUsuario(gestor, { id: "u", perfil: "operador" }), true);
  assert.equal(podeEditarUsuario(gestor, { id: "g2", perfil: "gestor" }), false);
  assert.equal(podeEditarUsuario(gestor, { id: "g", perfil: "gestor" }), false);
  assert.equal(podeEditarUsuario({ ...gestor, permissoes: ["usuarios.visualizar"] }, { id: "u", perfil: "operador" }), false);
  const admin = { id: "a", perfil: "admin" as const, permissoes: ["usuarios.editar"] };
  assert.equal(podeEditarUsuario(admin, { id: "g2", perfil: "gestor" }), true);
});

// ── código: onde está, o que chama, o que não faz ────────────────────────────────────────────────────────────

const ARQUIVOS = readdirSync(new URL("components/usuarios/capacidade/", SRC)).map((nome) => `components/usuarios/capacidade/${nome}`);

test("localização: aba 'Jornada e ausências' no formulário de edição do Usuário (só ao editar), sem tela global nem Tráfego/Financeiro", () => {
  const modal = semComentarios(ler("components/usuarios/UsuarioFormModal.tsx"));
  assert.match(modal, /usuario \? \[\{ id: "jornada", label: TITULO_SECAO \}\] : \[\]/);
  assert.match(modal, /<UsuarioCapacidadeSection usuarioId=\{usuario\.id\} somenteLeitura=\{usuarioAtual \? !podeEditarUsuario\(usuarioAtual, usuario\) : true\} \/>/);
  assert.match(modal, /effectiveTab !== "jornada" &&/); // a aba salva por conta própria: o "Salvar alterações" dos dados não aparece nela
  assert.match(modal, /podeVerFinanceiro \? \[\{ id: "financeiro", label: "Financeiro" \}\] : \[\]/); // restrição de Financeiro/Salários intacta
  assert.ok(ARQUIVOS.length >= 6);
  for (const arquivo of ARQUIVOS) assert.doesNotMatch(semComentarios(ler(arquivo)), /components\/trafego|@\/lib\/trafego/, arquivo);
});

test("requisições: ao abrir 2 GET em paralelo (jornada e ausências); mutations usam a resposta da API; nada por dia; client centralizado", () => {
  const hook = semComentarios(ler("components/usuarios/capacidade/useCapacidadeDoUsuario.ts"));
  assert.match(hook, /Promise\.all\(\[getJornadaUsuario\(usuarioId\), listarAusenciasUsuario\(usuarioId\)\]\)/);
  assert.equal((hook.match(/getJornadaUsuario\(/g) ?? []).length, 1);
  for (const arquivo of ARQUIVOS) {
    const fonte = semComentarios(ler(arquivo));
    assert.doesNotMatch(fonte, /\bfetch\(/, arquivo); // nenhum fetch direto nos componentes
    assert.doesNotMatch(fonte, /:\s*any\b|\bas any\b/, arquivo);
    assert.doesNotMatch(fonte, /location\.reload|router\.refresh|window\.location/, arquivo); // sem refetch global do aplicativo
  }
  const api = ler("lib/api-backend.ts");
  for (const trecho of ["`/usuarios/${usuarioId}/jornada`", "{ method: \"PUT\"", "{ method: \"DELETE\" }", "`/usuarios/${usuarioId}/ausencias`", "`/usuarios/${usuarioId}/ausencias/${ausenciaId}`", "{ method: \"PATCH\""]) {
    assert.ok(api.includes(trecho), trecho);
  }
});

test("Voltar ao padrão: confirmação curta + DELETE; sem copiar períodos; escolher 'personalizada' não grava nada sozinho", () => {
  const editor = semComentarios(ler("components/usuarios/capacidade/UsuarioJornadaEditor.tsx"));
  assert.match(editor, /usarExpedienteDaEmpresa\(usuarioId\)/);
  assert.match(editor, /setConfirmarVoltar\(true\)/);
  assert.match(editor, /<ConfirmacaoCurta/);
  // as únicas gravações da jornada são `salvarJornadaUsuario` (botão Salvar) e `usarExpedienteDaEmpresa` (confirmado)
  assert.equal((editor.match(/salvarJornadaUsuario\(/g) ?? []).length, 1);
  assert.equal((editor.match(/usarExpedienteDaEmpresa\(/g) ?? []).length, 1);
  const escolher = editor.slice(editor.indexOf("function escolherPersonalizada"), editor.indexOf("function descartar"));
  assert.doesNotMatch(escolher, /salvarJornadaUsuario|usarExpedienteDaEmpresa/);
  assert.match(semComentarios(ler("lib/usuario-capacidade.ts")), /TEXTO_CONFIRMAR_VOLTAR_EMPRESA/);
  assert.match(ler("lib/usuario-capacidade.ts"), /Remover a jornada personalizada deste usuário\? Ele voltará a usar o expediente da empresa\./);
});

test("reuso: o editor usa o PeriodosDoDia e a validação do Horário de expediente (sem algoritmo paralelo)", () => {
  const editor = semComentarios(ler("components/usuarios/capacidade/UsuarioJornadaEditor.tsx"));
  assert.match(editor, /import \{ PeriodosDoDia \} from "@\/components\/regra-expediente\/PeriodosDoDia"/);
  const lib = semComentarios(ler("lib/usuario-capacidade.ts"));
  assert.match(lib, /errosDaSemana\(dias\)/);
  assert.doesNotMatch(lib, /function validarPeriodos|function ordenarPeriodos/);
});

test("somente leitura: o editor desabilita campos/remoção/adição e a lista esconde editar/remover; a tabela oferece 'Jornada' só a quem não pode editar", () => {
  const dia = semComentarios(ler("components/regra-expediente/PeriodosDoDia.tsx"));
  assert.match(dia, /somenteLeitura = false/);
  assert.match(dia, /disabled=\{somenteLeitura\}/);
  assert.match(dia, /\{!somenteLeitura && \(/);
  const lista = semComentarios(ler("components/usuarios/capacidade/UsuarioAusenciasLista.tsx"));
  assert.match(lista, /\{!somenteLeitura && \(/);
  const tabela = semComentarios(ler("components/usuarios/UsuariosTable.tsx"));
  assert.match(tabela, /\{!podeEditar\(usuario\) && \(/);
  const modalLeitura = semComentarios(ler("components/usuarios/capacidade/UsuarioCapacidadeModal.tsx"));
  assert.match(modalLeitura, /<UsuarioCapacidadeSection usuarioId=\{usuarioId\} somenteLeitura \/>/);
});

test("não cria RBAC novo nem recalcula capacidade no cliente; sem fator individual; sem calendário de dias especiais", () => {
  for (const arquivo of [...ARQUIVOS, "lib/usuario-capacidade.ts"]) {
    const fonte = semComentarios(ler(arquivo));
    assert.doesNotMatch(fonte, /perfil_base|perfilBase|ensure_pode_administrar_alvo|perfisAtribuiveis/, arquivo); // a hierarquia fica em autoridadeUsuarios + backend
    assert.doesNotMatch(fonte, /percentual|fator|capacidadeAlocavel|alocavel/i, arquivo); // sem percentual individual nem cálculo de capacidade
  }
  assert.doesNotMatch(semComentarios(ler("components/usuarios/capacidade/UsuarioCapacidadeSection.tsx")), /RegraExpediente|dias-especiais/);
});

test("texto: avisa o impacto na Carga e nunca fala em horas trabalhadas, produtividade, banco de horas ou 'descontado'", () => {
  assert.equal(TEXTO_IMPACTO_CARGA, "As jornadas e ausências alteram a capacidade exibida em Tráfego → Carga.");
  for (const arquivo of [...ARQUIVOS, "lib/usuario-capacidade.ts"]) {
    const visivel = semComentarios(ler(arquivo));
    for (const proibido of TEXTOS_PROIBIDOS_NA_CAPACIDADE) {
      if (arquivo === "lib/usuario-capacidade.ts") continue; // a lista de proibidos mora aqui
      assert.doesNotMatch(visivel, proibido, `${arquivo}: ${proibido}`);
    }
  }
  assert.doesNotMatch(TEXTO_IMPACTO_CARGA, /estimativa|planejamento|prazo|horas trabalhadas/i);
});

test("regressão: Agora/Gargalos/Tempo pessoal/Clientes não foram tocados e o cadastro de Usuários segue com Dados/Endereço/Contatos", () => {
  const modal = semComentarios(ler("components/usuarios/UsuarioFormModal.tsx"));
  for (const aba of ['{ id: "dados", label: "Dados" }', '{ id: "endereco", label: "Endereço" }', '{ id: "contatos", label: "Contatos" }']) assert.ok(modal.includes(aba), aba);
  assert.match(modal, /effectiveTab === "financeiro" && podeVerFinanceiro/);
  for (const arquivo of ["components/trafego/TrafegoAgoraVisao.tsx", "components/trafego/TrafegoGargalosVisao.tsx", "components/trafego/TrafegoTempoPessoalView.tsx"]) {
    assert.doesNotMatch(ler(arquivo), /usuario-capacidade|jornada|ausencia/i, arquivo);
  }
});
