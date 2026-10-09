// Fase 7D.1 — numeração configurável de tarefas. `npm run test:numeracao-tarefas`.
// Lógica pura exercitada de verdade; telas e API (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  FORMATO_PADRAO,
  diferencaParaPatch,
  exigeConfirmacao,
  formatarIdentificador,
  minimoProximoNumero,
  validarFormato,
  validarProximoNumero,
} from "./numeracao-tarefas.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

// ── formatter / prévia ──────────────────────────────────────────────────────────────────────────────────────────

test("prévia: padrão histórico, dígitos, prefixo+separador e ano (mesmos exemplos do servidor)", () => {
  assert.equal(formatarIdentificador(FORMATO_PADRAO, 15, 2026), "#15");
  assert.equal(formatarIdentificador({ ...FORMATO_PADRAO, digitos: 5 }, 1, 2026), "#00001");
  assert.equal(formatarIdentificador({ prefixo: "TF", separador: "-", incluirAno: false, digitos: 5 }, 15, 2026), "TF-00015");
  assert.equal(formatarIdentificador({ prefixo: "BOX", separador: "-", incluirAno: true, digitos: 5 }, 15, 2026), "BOX-2026-00015");
  assert.equal(formatarIdentificador({ prefixo: "", separador: "-", incluirAno: true, digitos: 5 }, 15, 2026), "2026-00015");
  assert.equal(formatarIdentificador({ prefixo: "BOX-", separador: "-", incluirAno: true, digitos: 5 }, 15, 2026), "BOX-2026-00015"); // sem "--"
  assert.equal(formatarIdentificador({ prefixo: "#", separador: "", incluirAno: false, digitos: 1 }, 12345, 2026), "#12345");
});

test("o ano só entra no texto: o número NÃO reinicia (não há reinício anual)", () => {
  const formato = { prefixo: "BOX", separador: "-", incluirAno: true, digitos: 5 };
  assert.equal(formatarIdentificador(formato, 999, 2026), "BOX-2026-00999");
  assert.equal(formatarIdentificador(formato, 1000, 2027), "BOX-2027-01000");
});

// ── validação (UX; o servidor revalida) ─────────────────────────────────────────────────────────────────────────

test("validação do formato: limites, caracteres seguros, fronteira ambígua e número puro", () => {
  assert.equal(validarFormato({ prefixo: "BOX", separador: "-", incluirAno: true, digitos: 5 }), null);
  assert.equal(validarFormato(FORMATO_PADRAO), null);
  assert.match(validarFormato({ ...FORMATO_PADRAO, prefixo: "X".repeat(17) }) ?? "", /prefixo/);
  assert.match(validarFormato({ ...FORMATO_PADRAO, separador: "-----" }) ?? "", /separador/);
  assert.match(validarFormato({ ...FORMATO_PADRAO, prefixo: "B O X" }) ?? "", /letras, números/);
  assert.match(validarFormato({ ...FORMATO_PADRAO, digitos: 0 }) ?? "", /dígitos/);
  assert.match(validarFormato({ ...FORMATO_PADRAO, digitos: 11 }) ?? "", /dígitos/);
  assert.match(validarFormato({ ...FORMATO_PADRAO, digitos: Number.NaN }) ?? "", /dígitos/);
  assert.match(validarFormato({ prefixo: "A1", separador: "", incluirAno: false, digitos: 3 }) ?? "", /separador/);
  assert.match(validarFormato({ prefixo: "", separador: "", incluirAno: false, digitos: 1 }) ?? "", /prefixo/);
});

test("próximo número: nunca menor que o maior emitido + 1 (colisão com o histórico)", () => {
  assert.equal(minimoProximoNumero(845), 846);
  assert.equal(minimoProximoNumero(null), 1);
  assert.equal(validarProximoNumero(846, 845), null);
  assert.equal(validarProximoNumero(1000, 845), null);
  assert.match(validarProximoNumero(845, 845) ?? "", /pelo menos 846/);
  assert.match(validarProximoNumero(100, 845) ?? "", /pelo menos 846/);
  assert.equal(validarProximoNumero(5001, null), null); // primeira emissão pode começar alto
  assert.notEqual(validarProximoNumero(0, null), null);
  assert.notEqual(validarProximoNumero(1.5, null), null);
  assert.notEqual(validarProximoNumero(Number.NaN, null), null);
});

test("PATCH só leva o que mudou e nunca reinicioAnual/empresaId; próximo número pede confirmação", () => {
  const atual = { ...FORMATO_PADRAO, proximoNumero: 2 };
  assert.deepEqual(diferencaParaPatch(atual, atual), {});
  const patch = diferencaParaPatch(atual, { prefixo: "BOX", separador: "-", incluirAno: true, digitos: 5, proximoNumero: 2 });
  assert.deepEqual(patch, { prefixo: "BOX", separador: "-", incluirAno: true, digitos: 5 });
  assert.equal(exigeConfirmacao(patch), false); // mudança de formato é cosmética para o histórico: sem modal
  assert.equal(exigeConfirmacao({ proximoNumero: 100 }), true);
  assert.doesNotMatch(Object.keys(patch).join(","), /reinicio|empresa/i);
});

// ── tela e API ──────────────────────────────────────────────────────────────────────────────────────────────────

test("tela: carrega, mostra prévia em tempo real, avisa que só vale para novas tarefas e salva por PATCH", () => {
  const view = ler("components/configuracao-numeracao-tarefa/ConfiguracaoNumeracaoTarefaView.tsx");
  const codigo = semComentarios(view);
  assert.match(codigo, /obterNumeracaoTarefaReal\(\)/);
  assert.match(codigo, /atualizarNumeracaoTarefaReal\(patch\)/);
  assert.match(codigo, /Formato das próximas tarefas/);
  assert.match(view, /As alterações serão aplicadas somente às novas tarefas\. Tarefas já emitidas mantêm sua identificação\./);
  assert.match(codigo, /label="Prefixo"/);
  assert.match(codigo, /label="Separador"/);
  assert.match(codigo, /label="Quantidade mínima de dígitos"/);
  assert.match(codigo, /label="Próximo número"/);
  assert.match(codigo, /label="Incluir ano"/);
  assert.match(codigo, /formatarIdentificador\(draft, draft\.proximoNumero/); // prévia ao vivo, sem consumir número
  assert.match(codigo, /Prévia da próxima tarefa/);
  assert.match(codigo, /Salvar configuração/);
  assert.match(codigo, /if \(exigeConfirmacao\(patch\) && !confirmando\)/); // confirmação só para o próximo número
  assert.match(codigo, /setErroSalvar\(error instanceof Error/); // erro do servidor (ex.: próximo número inválido) aparece
});

test("tela: NÃO existe toggle de reinício anual (recurso inexistente não é prometido)", () => {
  const codigo = semComentarios(ler("components/configuracao-numeracao-tarefa/ConfiguracaoNumeracaoTarefaView.tsx"));
  assert.doesNotMatch(codigo, /label="[^"]*([Rr]einici|anual)/); // nenhum controle de reinício
  assert.doesNotMatch(codigo, /reinicioAnual|reiniciar/i);
  assert.doesNotMatch(semComentarios(ler("lib/numeracao-tarefas.ts")), /reinicio/i);
  assert.doesNotMatch(semComentarios(ler("types/configuracao-numeracao-tarefa.ts")), /reinicio/i);
});

test("API: PATCH em /configuracoes/numeracao-tarefas; sem empresaId nem reinício no cliente", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  const inicio = api.indexOf("export async function atualizarNumeracaoTarefaReal");
  const corpo = api.slice(inicio, api.indexOf("\n}\n", inicio));
  assert.match(corpo, /"\/configuracoes\/numeracao-tarefas"/);
  assert.match(corpo, /method: "PATCH"/);
  assert.doesNotMatch(corpo, /empresaId|reinicio/i);
});

// ── identificador emitido nas superfícies ───────────────────────────────────────────────────────────────────────

test("rotuloDemanda exibe o identificador EMITIDO; fallback só para resposta legada e nunca usa a configuração atual", () => {
  const ref = semComentarios(ler("lib/referencias.ts"));
  const inicio = ref.indexOf("export function rotuloDemanda");
  const corpo = ref.slice(inicio, ref.indexOf("\n}\n", inicio));
  assert.match(corpo, /if \(demanda\.identificador\) return demanda\.identificador;/);
  assert.match(corpo, /`#\$\{demanda\.numeroOperacional\}`/); // formato histórico, não a config atual
  assert.doesNotMatch(corpo, /formatarIdentificador|numeracao|prefixo/i);
});

test("nenhuma superfície monta `#<número>` por conta própria: todas passam por rotuloDemanda", () => {
  const superficies = [
    "components/arquivos/ArquivoCard.tsx",
    "components/arquivos/ArquivoPreviewModal.tsx",
    "components/arquivos/ArquivoUploadModal.tsx",
    "components/arquivos/useDefinicoesFiltrosArquivos.ts",
    "components/trafego/TrafegoIniciarSessao.tsx",
    "components/trafego/TrafegoAgoraTable.tsx",
    "components/meu-departamento/EquipeAgoraCard.tsx",
    "components/relatorios/AnalisePecasReport.tsx",
    "components/demandas/DemandaKanbanCard.tsx",
    "components/demandas/DemandasTable.tsx",
    "components/demandas/DemandaDetailsDrawer.tsx",
    "components/pauta/PautaLista.tsx",
    "components/operacional/TarefasLista.tsx",
    "components/minhas-demandas/MinhasDemandasView.tsx",
    "components/layout/NotificationBell.tsx",
    "components/dashboard/DashboardView.tsx",
    "components/projetos/ProjetoDemandasSection.tsx",
    "components/notificacoes/PrazosEquipeLista.tsx",
  ];
  for (const caminho of superficies) {
    const codigo = semComentarios(ler(caminho));
    assert.match(codigo, /rotuloDemanda/, `${caminho} deve usar rotuloDemanda`);
    assert.doesNotMatch(codigo, /`#\$\{[^}]*(numero|Numero)[^}]*\}/, `${caminho} montou #<número> à mão`);
    assert.doesNotMatch(codigo, /#\{[A-Za-z.]*(numero|Numero)/, `${caminho} montou #<número> à mão (JSX)`);
  }
});

test("DTOs do cliente carregam o identificador emitido (demanda, diretório, arquivos, relatório, equipe agora, tráfego)", () => {
  assert.match(semComentarios(ler("types/demanda.ts")), /identificador: string;/);
  assert.match(semComentarios(ler("lib/api-backend.ts")), /identificador: data\.identificador,/);
  assert.match(semComentarios(ler("types/arquivo.ts")), /identificador: string;/);
  assert.match(semComentarios(ler("types/relatorios.ts")), /identificador: string;/);
  assert.match(semComentarios(ler("types/trafego.ts")), /demandaIdentificador\?: string \| null;/);
  assert.match(semComentarios(ler("lib/api-backend.ts")), /emExecucao: Array<\{ demandaId: string; numeroOperacional: number \| null; identificador: string \| null;/);
});
