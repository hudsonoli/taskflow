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

test("Pauta: universo = TODA demanda em aberto (escopo=pauta + naoFinalizada); prazo NÃO é condição, só filtro opcional de período", () => {
  const view = ler("components/pauta/PautaView.tsx");
  const codigo = semComentarios(view);
  assert.match(codigo, /const prazoDoPeriodo = periodo === "todas" \? \{\} : \{ prazoFim: periodoFim\.toISOString\(\) \};/); // "Todas" não envia prazo
  assert.match(codigo, /escopo: "pauta" as const, naoFinalizada: true, \.\.\.prazoDoPeriodo, \.\.\.parametrosFiltros/);
  assert.doesNotMatch(codigo, /prazoInicio/); // sem piso: atrasadas continuam; sem prazo não é excluída por padrão
  assert.match(codigo, /PERIODOS_VALIDOS\.find\(\(valor\) => valor === param\("periodo"\)\) \?\? "todas"/); // padrão = todas as demandas em aberto
  assert.doesNotMatch(codigo, /\?\? "7d"/);
  assert.match(codigo, /listDemandasReais\(parametrosDaConsulta\(0\)\)/);
  assert.match(codigo, /listDemandasReais\(parametrosDaConsulta\(demandasPauta\.length\)\)/); // "carregar mais" = mesmos filtros
  assert.doesNotMatch(codigo, /demandasPauta\.filter\(/); // nunca filtra só o que foi carregado
  assert.match(codigo, /if \(!pronto\) return;/); // espera papel/departamentos: não busca antes de saber quem é
  const toolbar = semComentarios(ler("components/pauta/PautaToolbar.tsx"));
  assert.match(toolbar, /export type PautaPeriodoFiltro = "todas" \| "hoje" \| "7d" \| "30d"/);
  assert.match(toolbar, /\{ value: "todas" as const, label: "Todas" \}/);
});

test("não existe mais a Pauta legada: sem seletor simples de departamentos, sem consulta por departamento/prazo-janela do operador", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.doesNotMatch(view, /modoGlobal|departamentoIds|departamentoIdsParam|setDepartamentoIds/);
  assert.doesNotMatch(view, /prazoInicio: periodoInicio/);
  const toolbar = semComentarios(ler("components/pauta/PautaToolbar.tsx"));
  assert.doesNotMatch(toolbar, /MultiSelect|useDiretorioDepartamentos/);
  assert.match(toolbar, /filtrosAvancados: ReactNode/); // obrigatório: a Pauta sempre tem os filtros avançados
});

test("operador comum NÃO tem Pauta: some do menu e a rota nega a URL direta (nunca mostra a Pauta antiga)", () => {
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  const base = nav.slice(nav.indexOf("const NAV_ITEMS_BASE"), nav.indexOf("];", nav.indexOf("const NAV_ITEMS_BASE")));
  assert.doesNotMatch(base, /Pauta|\/pauta/); // fora dos itens de qualquer autenticado
  assert.match(nav, /if \(podeAcessarPautaGlobal\(usuarioAtual, departamentos\)\) \{[\s\S]*?label: "Pauta", href: "\/pauta"/); // só com a Pauta global
  assert.match(base, /label: "Meu dia"/); // Meu Dia segue para todos
  assert.match(base, /label: "Tarefas"/);
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(view, /import \{ AcessoNegado \} from "@\/components\/operacional\/AcessoNegado"/);
  assert.match(view, /if \(carregandoDepartamentos\) return/); // espera os departamentos antes de negar (Head/Atendimento dependem deles)
  assert.match(view, /if \(!podeAcessar\) \{[\s\S]*?<AcessoNegado/);
  assert.match(view, /const pronto = Boolean\(usuarioAtual\) && !carregandoDepartamentos && podeAcessar;/); // negado nunca consulta
  const rota = semComentarios(ler("app/pauta/page.tsx"));
  assert.match(rota, /<PautaView \/>/); // a rota só delega: a regra está na view
});

test("Meu Dia segue para todos e Meu Departamento só para o Head (sem regressão do menu)", () => {
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.match(nav, /podeAcessarMeuDepartamento\(usuarioAtual, departamentos\)\) \{\s*items\.splice\(1, 0, \{ label: "Meu Departamento"/);
  assert.match(nav, /\{ label: "Meu dia", href: "\/meu-dia"/);
});

test("estado da Pauta na URL: filtros, busca (q), período e modo; inválido volta ao padrão", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, podeAcessar\)/); // só persiste para quem tem a Pauta
  assert.match(view, /MODOS_VALIDOS\.find\(\(valor\) => valor === param\("modo"\)\) \?\? "gantt"/);
  assert.match(view, /definirParam\("q", texto\)/);
  assert.match(view, /definirParam\("periodo", valor === "todas" \? null : valor\)/); // padrão não suja a URL
});

test("selo 'em execução agora' na Pauta: só ids de demanda (sem pessoa nem tempo); falha não derruba a lista", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /listarDemandasEmExecucaoNaPauta\(\)\.catch\(\(\) => \[\] as string\[\]\)/);
  assert.match(ler("components/pauta/PautaLista.tsx"), /emExecucaoIds\?\.has\(demanda\.id\) && <Badge tone="green">Em execução agora<\/Badge>/);
  assert.match(ler("components/pauta/PautaGantt.tsx"), /aria-label="Em execução agora"/);
  const api = ler("lib/api-backend.ts");
  assert.match(api, /"\/sessoes-trabalho\/pauta\/em-execucao"/);
});

test("demanda SEM PRAZO aparece na Pauta: na Lista em 'Sem prazo definido' e no Gantt como aviso (sem barra enganosa)", () => {
  assert.match(ler("components/pauta/PautaLista.tsx"), /Sem prazo definido/);
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  assert.match(gantt, /const semPrazo = !fimValido;/);
  assert.match(gantt, /semPrazo \? \(/);
  assert.match(gantt, /Sem prazo definido/);
});

// ── Detalhe SOMENTE LEITURA pela Pauta global ───────────────────────────────────────────────────────────────────

test("o cliente de API só envia ?escopo=pauta nas LEITURAS do detalhe; nenhuma escrita carrega o parâmetro", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /export type EscopoLeituraDemanda = "pauta";/);
  for (const fn of ["getDemandaReal", "listChecklistDemanda", "listArquivosDemanda", "listComentariosDemanda", "listHistoricoDemanda"]) {
    assert.match(api, new RegExp(`export async function ${fn}\\(demandaId: string, escopo\\?: EscopoLeituraDemanda\\)`), fn);
  }
  assert.match(api, /export function urlDownloadArquivoDemanda\(demandaId: string, arquivoId: string, escopo\?: EscopoLeituraDemanda\)/);
  // escritas: nunca usam o sufixo
  for (const fn of ["patchDemandaReal", "criarItemChecklist", "criarComentarioDemanda", "uploadArquivoDemanda", "criarLinkArquivoDemanda", "excluirArquivoDemanda", "registrarAjusteDemanda"]) {
    const inicio = api.indexOf(`export async function ${fn}(`);
    assert.ok(inicio >= 0, fn);
    const corpo = api.slice(inicio, api.indexOf("\nexport ", inicio + 10));
    assert.doesNotMatch(corpo, /sufixoEscopoLeitura|escopo=/, fn);
  }
});

test("drawer aberto pela Pauta: modo leitura (fieldset desabilitado, sem Editar, aviso) e subrecursos consultados com o escopo", () => {
  const drawer = semComentarios(ler("components/demandas/DemandaDetailsDrawer.tsx"));
  assert.match(drawer, /modoLeitura\?: EscopoLeituraDemanda/);
  assert.match(drawer, /onEdit=\{demanda && !somenteLeitura \? \(\) => onEdit\(demanda\.id\) : undefined\}/); // sem "Editar tarefa"
  assert.match(drawer, /<fieldset disabled=\{somenteLeitura\}/);
  assert.match(drawer, /<LeituraDemandaProvider value=\{modoLeitura\}>/);
  assert.match(drawer, /Visualização somente leitura/);
  assert.match(drawer, /somenteLeitura \? \([\s\S]*?\) : \(\s*<DemandaConclusaoBanner/); // sem ação de conclusão por e-mail
  const atividade = semComentarios(ler("components/demandas/AtividadeDemandaSection.tsx"));
  assert.match(atividade, /listComentariosDemanda\(demanda\.id, escopoLeitura\)/);
  assert.match(atividade, /\{!somenteLeitura && \(\s*<div className="flex items-start gap-2">/); // sem caixa de comentar
  const checklist = semComentarios(ler("components/demandas/DemandaChecklistCard.tsx"));
  assert.match(checklist, /listChecklistDemanda\(demandaId, escopoLeitura\)/);
  assert.match(checklist, /disabled=\{somenteLeitura \|\| processandoId === item\.id\}/);
  const arquivos = semComentarios(ler("components/demandas/DemandaArquivosCard.tsx"));
  assert.match(arquivos, /listArquivosDemanda\(demandaId, escopoLeitura\)/);
  assert.match(arquivos, /urlDownloadArquivoDemanda\(demandaId, arquivo\.id, escopoLeitura\)/); // download pela Pauta, no mesmo tenant
  assert.match(arquivos, /\{!somenteLeitura && \(\s*<>\s*<div className="mt-3 flex items-center gap-1\.5">/); // sem enviar/link
  const secoes = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  assert.match(secoes, /listHistoricoDemanda\(demanda\.id, escopoLeitura\)/);
  assert.match(secoes, /\{!somenteLeitura && \(\s*<div className="mt-4 flex flex-col gap-3">\s*<EnvioClienteCard/); // sem enviar ao cliente / ajuste
  assert.match(secoes, /readOnly=\{somenteLeitura\}/); // briefing não editável
  assert.match(semComentarios(ler("components/ui/RichTextEditor.tsx")), /contentEditable=\{!readOnly\}/);
});

test("PautaView: o drawer é leitura por padrão e só edita se a demanda também está no escopo-BASE (sonda sem escopo)", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(view, /getDemandaReal\(selectedDemandId\)\s*\.then\(\(\) => \{\s*if \(!cancelado\) setAcessoEscrita\(\{ demandaId: selectedDemandId, editavel: true \}\)/);
  assert.match(view, /\.catch\(\(\) => \{\s*if \(!cancelado\) setAcessoEscrita\(\{ demandaId: selectedDemandId, editavel: false \}\)/);
  assert.match(view, /acessoEscrita\?\.demandaId === selectedDemandId && acessoEscrita\.editavel \? undefined : "pauta"/);
  assert.match(view, /getDemandaReal\(selectedDemandId, "pauta"\)/); // demanda fora da página carregada: lida pela Pauta
  assert.match(view, /modoLeitura=\{modoLeitura\}/);
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
