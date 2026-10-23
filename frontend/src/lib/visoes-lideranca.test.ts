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

// ── filtros da Pauta global ─────────────────────────────────────────────────────────────────────────────────────

test("Pauta por etapa: Colaborador, Departamento, Cliente, Projeto e Prioridade mapeiam para os parâmetros do servidor (só 'é'/'é um de')", () => {
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is", valores: [A] }]), { departamentoIds: [A] });
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "in", valores: [A, B] }]), { departamentoIds: [A, B] });
  const combinado = filtrosPautaParaApi([
    { campo: "departamento", operador: "in", valores: [A, B] },
    { campo: "responsavel", operador: "is", valores: [A] },
    { campo: "cliente", operador: "in", valores: [A, B] },
    { campo: "projeto", operador: "is", valores: [B] },
    { campo: "prioridade", operador: "is", valores: ["alta"] },
  ]);
  assert.deepEqual(combinado, { departamentoIds: [A, B], usuarioIds: [A], clienteIds: [A, B], projetoIds: [B], prioridades: ["alta"] });
  const rota = semComentarios(ler("app/e/[slug]/pauta/page.tsx"));
  assert.match(rota, /<PautaView \/>/); // a rota só delega: a regra está na view
});

test("'não é', filtro vazio e campos que a Pauta não tem NÃO viram parâmetro (o servidor não os executa)", () => {
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is_not", valores: [A] }]), {});
  assert.deepEqual(filtrosPautaParaApi([{ campo: "departamento", operador: "is", valores: [] }]), {});
  assert.deepEqual(filtrosPautaParaApi([{ campo: "prazo", operador: "is", valores: ["atrasado"] }]), {}); // prazo não é filtro da Pauta por etapa
  assert.deepEqual(filtrosPautaParaApi([{ campo: "status", operador: "in", valores: ["em_execucao"] }]), {});
  assert.deepEqual(filtrosPautaParaApi([]), {});
});

test("o Meu Departamento NÃO ganhou Departamento como filtro; a Pauta tem Colaborador e Departamento sobre a responsabilidade EFETIVA", () => {
  assert.equal("departamento" in CAMPO_MEU_DEPARTAMENTO, false);
  assert.equal(CAMPO_PAUTA.departamento, "departamento");
  assert.doesNotMatch(ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts"), /label: "Departamento"/);
  const defs = ler("components/pauta/useDefinicoesFiltrosPauta.ts");
  for (const campo of Object.keys(CAMPO_PAUTA)) assert.ok(defs.includes(`CAMPO_PAUTA.${campo}`), campo);
  assert.match(defs, /label: "Colaborador"/);
  assert.match(defs, /permiteExcluir: false/);
  assert.doesNotMatch(defs, /STATUS_DA_FILA|CAMPO_PAUTA\.(prazo|origem|status|equipe)/); // a Pauta não é um relatório genérico
});

// ── Pauta: modos, autorização e consulta ────────────────────────────────────────────────────────────────────────

test("autorização da Pauta global no cliente espelha a do servidor: admin/gestor, Head ou Atendimento; operador comum não", () => {
  const escopo = semComentarios(ler("lib/escopo-operacional.ts"));
  const corpo = escopo.slice(escopo.indexOf("export function podeAcessarPautaGlobal"), escopo.indexOf("export function podeAcessarMinhasDemandas"));
  assert.match(corpo, /base === "admin" \|\| base === "gestor"/);
  assert.match(corpo, /podeAcessarMeuDepartamento\(usuario, departamentos\) \|\| resolverEhAtendimento\(usuario, departamentos\)/);
  assert.doesNotMatch(corpo, /operador|@|\.com|empresaId/i); // nada hardcoded por e-mail, nome ou tenant
});

test("Pauta: UMA consulta ao endpoint por etapa (sem lista de Demandas, sem prazo como condição); acesso espera papel/departamentos", () => {
  const codigo = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(codigo, /usePautaOperacional\(parametros, versao\)/);
  assert.doesNotMatch(codigo, /listDemandasReais|prazoFim|prazoInicio|naoFinalizada|carregarMais|Carregar mais/); // sem a lista paginada de Demandas
  assert.match(codigo, /pronto\s*\? \{/); // negado/indeciso nunca consulta
  assert.match(codigo, /const pronto = Boolean\(usuarioAtual\) && !carregandoDepartamentos && podeAcessar;/);
  const api = semComentarios(ler("lib/api.ts"));
  assert.match(api, /`\$\{API_PROXY\}\/pauta\/operacional/);
  assert.doesNotMatch(semComentarios(ler("components/pauta/usePautaOperacional.ts")), /getTrafegoCarga|operacional\/carga/); // a Pauta não reconstrói agenda a partir da Carga
});

test("não existe mais a Pauta legada: sem seletor simples de departamentos, sem Gantt por Demanda com datas da Demanda", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.doesNotMatch(view, /modoGlobal|departamentoIds: |setDepartamentoIds/);
  for (const arquivo of ["PautaGantt", "PautaLista", "pautaContexto"]) {
    assert.doesNotMatch(semComentarios(ler(`components/pauta/${arquivo}.tsx`.replace("pautaContexto.tsx", "pautaContexto.ts"))), /dataFimPrevista|dataInicio\b|prazoEtapaAtual\)|new Date\(/, arquivo);
  }
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
  const rota = semComentarios(ler("app/e/[slug]/pauta/page.tsx"));
  assert.match(rota, /<PautaView \/>/); // a rota só delega: a regra está na view
});

test("Meu Dia segue para todos e Meu Departamento só para o Head (sem regressão do menu)", () => {
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.match(nav, /podeAcessarMeuDepartamento\(usuarioAtual, departamentos\)\) \{\s*items\.splice\(1, 0, \{ label: "Meu Departamento"/);
  assert.match(nav, /\{ label: "Meu dia", href: "\/meu-dia"/);
});

test("estado da Pauta na URL: filtros, busca (q), agrupamento, apresentação e início do período; inválido volta ao padrão", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, podeAcessar\)/); // só persiste para quem tem a Pauta
  assert.match(view, /VISOES_PAUTA\.find\(\(valor\) => valor === param\("visao"\)\) \?\? "colaborador"/); // padrão = Colaborador
  assert.match(view, /MODOS_PAUTA\.find\(\(valor\) => valor === param\("modo"\)\) \?\? "gantt"/);
  assert.match(view, /dataValida\(param\("inicio"\)\)/); // data inválida na URL é ignorada
  assert.match(view, /definirParam\("q", texto\)/);
  assert.match(view, /definirParam\("visao", valor === "colaborador" \? null : valor\)/); // padrão não suja a URL
});

test("selo 'em execução agora' na Pauta: só ids de demanda (sem pessoa nem tempo); falha não derruba a pauta", () => {
  const view = ler("components/pauta/PautaView.tsx");
  assert.match(view, /listarDemandasEmExecucaoNaPauta\(\)\s*\.catch\(\(\) => \[\] as string\[\]\)/);
  assert.match(ler("components/pauta/PautaLista.tsx"), /contexto\.emExecucaoIds\.has\(item\.demandaId\) && <Badge tone="green">Em execução agora<\/Badge>/);
  assert.match(ler("components/pauta/PautaGantt.tsx"), /aria-label="Em execução agora"/);
  const api = ler("lib/api-backend.ts");
  assert.match(api, /"\/sessoes-trabalho\/pauta\/em-execucao"/);
});

test("etapa sem planejamento / com planejamento incompleto aparece na Pauta, sem barra enganosa e sem usar prazo", () => {
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  assert.match(gantt, /Planejamento incompleto \(\$\{incompletas\.length\}\)/);
  assert.match(gantt, /Não planejadas \(\$\{naoPlanejadas\.length\}\)/);
  assert.match(gantt, /Início: \{formatarDiaMes\(planejamento\.inicio\)\} · Fim: não definido/);
  assert.match(gantt, /Sem janela planejada/);
  assert.match(gantt, /posicaoDaJanela\(planejamento\.inicio, planejamento\.fim, periodoInicio, periodoFim\)/); // geometria = só o planejamento
  assert.doesNotMatch(gantt, /prazo/i); // prazo nunca posiciona nada
  assert.match(semComentarios(ler("components/pauta/PautaLista.tsx")), /fim não definido/);
});

// ── Detalhe SOMENTE LEITURA pela Pauta global ───────────────────────────────────────────────────────────────────

test("o cliente de API só envia ?escopo=pauta nas LEITURAS do detalhe; nenhuma escrita carrega o parâmetro", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /export type EscopoLeituraDemanda = "pauta" \| "acompanhamento";/); // acompanhamento: leitura pela AUTORIA (Solicitadas por mim)
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
  assert.match(drawer, /onEdit=\{demanda && !somenteLeitura && !somenteWorkflow \? \(\) => onEdit\(demanda\.id\) : undefined\}/); // sem "Editar tarefa"
  assert.match(drawer, /<fieldset disabled=\{somenteLeitura( \|\| somenteWorkflow)?\}/); // Pauta: continua desabilitado (8C.1 só acrescenta o acesso por Workflow)
  assert.match(drawer, /<LeituraDemandaProvider value=\{modoEfetivo\}>/); // modoEfetivo = modoLeitura (Pauta) ou o sinal de autoria do servidor
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
