// P1_GLASS_APP_THEME — auditoria de superfícies do estilo Glass, como DADOS verificáveis. O teste (`estilo-visual.test.ts`) exige que TODA rota de `src/app/**/page.tsx` apareça aqui: rota nova sem
// classificação quebra o teste (nenhuma rota fica "esquecida" em silêncio). O Glass é só material/superfície (tokens + ganchos `data-superficie`); nada aqui muda dados, regras ou geometria.

export type ClasseGlass = "aplicado" | "intencionalmente-inalterado";

export type RotaGlass = {
  /** padrão da rota, relativo a `src/app` ("e/[slug]/tarefas") */
  rota: string;
  shell: "cabecalho-tenant" | "cabecalho-gestao" | "tela-nua";
  /** o que recebe o material Glass nesta rota */
  superficies: string;
  glass: ClasseGlass;
  observacao?: string;
};

const TENANT = "cabecalho-tenant" as const;
const NUA = "tela-nua" as const;

export const AUDITORIA_GLASS: readonly RotaGlass[] = [
  { rota: "e/[slug]", shell: TENANT, superficies: "redireciona para o Meu dia", glass: "aplicado" },
  { rota: "e/[slug]/login", shell: NUA, superficies: "tela própria SEMPRE clara (layout dividido + painel de marca); ignora tema e estilo Glass", glass: "intencionalmente-inalterado", observacao: "decisão de produto: login só em tema claro" },
  { rota: "e/[slug]/esqueci-senha", shell: NUA, superficies: "canvas + cartão central", glass: "aplicado" },
  { rota: "e/[slug]/redefinir-senha", shell: NUA, superficies: "canvas + cartão central", glass: "aplicado" },
  { rota: "e/[slug]/trocar-senha-inicial", shell: NUA, superficies: "canvas + cartão central", glass: "aplicado" },
  { rota: "e/[slug]/aprovacao", shell: NUA, superficies: "canvas (portal externo); conteúdo e cópia intocados", glass: "aplicado", observacao: "portal público por token: só tokens/canvas; layout e fluxo não mudam" },
  { rota: "e/[slug]/meu-dia", shell: TENANT, superficies: "cabeçalho, KPIs/cards, fila, modais", glass: "aplicado" },
  { rota: "e/[slug]/tarefas", shell: TENANT, superficies: "cabeçalho, KPIs, toolbar/filtros, Kanban (colunas leves, cards sem blur), tabela, modais/drawer", glass: "aplicado", observacao: "dnd-kit, auto-collapse e cores de prioridade intocados" },
  { rota: "e/[slug]/minhas-demandas", shell: TENANT, superficies: "cabeçalho, cards/KPIs, tabelas, modais", glass: "aplicado" },
  { rota: "e/[slug]/meu-departamento", shell: TENANT, superficies: "cabeçalho, cards/KPIs, tabelas, modais", glass: "aplicado" },
  { rota: "e/[slug]/projetos", shell: TENANT, superficies: "cabeçalho, tabs, tabela, modais/drawer, Progresso", glass: "aplicado" },
  { rota: "e/[slug]/pauta", shell: TENANT, superficies: "cabeçalho, toolbar/filtros, painel do Gantt; células fixas quase opacas", glass: "aplicado", observacao: "barras/timeline do Gantt e geometria intocadas" },
  { rota: "e/[slug]/trafego", shell: TENANT, superficies: "cabeçalho, tabs, KPIs/painéis, tabelas, tooltips", glass: "aplicado" },
  { rota: "e/[slug]/relatorios", shell: TENANT, superficies: "cabeçalho, cards/gráficos", glass: "aplicado", observacao: "cores dos gráficos (tokens --viz-*) intocadas" },
  { rota: "e/[slug]/arquivos", shell: TENANT, superficies: "cabeçalho, painéis, tabela, barra de seleção (quase opaca)", glass: "aplicado" },
  { rota: "e/[slug]/notificacoes", shell: TENANT, superficies: "cabeçalho, cards/listas", glass: "aplicado" },
  { rota: "e/[slug]/minha-conta", shell: TENANT, superficies: "cabeçalho, painéis/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes", shell: TENANT, superficies: "cabeçalho, hub e navegação interna", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/acessos", shell: TENANT, superficies: "painel, tabela", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/clientes", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/departamentos", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/email", shell: TENANT, superficies: "painéis/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/equipes", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/fornecedores", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/grupos-clientes", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/horario-expediente", shell: TENANT, superficies: "painéis/formulários", glass: "aplicado", observacao: "campos de horário (time-only) intocados" },
  { rota: "e/[slug]/configuracoes/modelos-campanha", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/numeracao-tarefas", shell: TENANT, superficies: "painéis/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/pecas", shell: TENANT, superficies: "painéis/listas", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/permissoes", shell: TENANT, superficies: "painéis/tabela", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/personalizar", shell: TENANT, superficies: "painéis/formulários; o preview de tema da empresa mantém o próprio data-theme", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/sla", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/tipos-tarefa", shell: TENANT, superficies: "tabela, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/usuarios", shell: TENANT, superficies: "tabela compacta, modais/formulários", glass: "aplicado" },
  { rota: "e/[slug]/configuracoes/workflows", shell: TENANT, superficies: "tabela, modais; cor do workflow continua visível", glass: "aplicado" },
  { rota: "gestao", shell: "cabecalho-gestao", superficies: "cabeçalho e painéis (mesmos primitivos); autenticação/RBAC da plataforma intocados", glass: "aplicado" },
  { rota: "gestao/empresas", shell: "cabecalho-gestao", superficies: "cabeçalho, tabela", glass: "aplicado" },
  { rota: "gestao/empresas/[id]", shell: "cabecalho-gestao", superficies: "cabeçalho, painéis/formulários", glass: "aplicado" },
];
