import type { ProjetoModeloCampanhaItem } from "@/types/projeto";

/**
 * Restos de mock que sobreviveram à migração de Projeto (Fase 2D).
 *
 * Este arquivo é **transitório por definição**. Ele existe porque `lib/projetos-mock.ts`
 * acumulava duas coisas — a entidade Projeto e listas de referência compartilhadas — e a
 * segunda parte ainda é consumida por três domínios que não migraram: Demandas, Relatórios
 * e Central de Tráfego.
 *
 * Nada aqui é dado real. Cada bloco sai quando o domínio que o consome migrar, e o arquivo
 * inteiro deve desaparecer junto com o último deles.
 *
 * Nenhuma tela já migrada importa daqui. Se isso acontecer, é regressão.
 */

// ======================================================================================
// Listas de referência — vinham de projetos-mock.ts
// ======================================================================================

/** Consumida por `lib/relatorios.ts`. Não são clientes reais: a base tem 126 outros. */
export const clientesProjetoDisponiveis = [
  { id: "cliente-1", nome: "Cliente Exemplo" },
  { id: "cliente-2", nome: "Clínica Clare" },
  { id: "cliente-3", nome: "Loja Boxx" },
];

/** Consumida por `lib/relatorios.ts`, `lib/trafego.ts` e `lib/demandas.ts`. */
export const responsaveisProjetoDisponiveis = [
  { id: "user-1", nome: "Hudson Cunha" },
  { id: "user-2", nome: "Ana Costa" },
  { id: "user-3", nome: "Carlos Lima" },
  { id: "user-4", nome: "João Silva" },
  { id: "user-5", nome: "Maria Souza" },
];

/** Consumida por `lib/trafego.ts` e `lib/demandas.ts`. */
export const departamentosProjetoDisponiveis = [
  { id: "dep-atendimento", nome: "Atendimento" },
  { id: "dep-criacao", nome: "Criação" },
  { id: "dep-midia", nome: "Mídia" },
  { id: "dep-trafego", nome: "Tráfego" },
  { id: "dep-conteudo", nome: "Conteúdo" },
];

/** TipoTarefa ainda não tem tabela — some quando o domínio migrar. */
export const tiposTarefaProjetoDisponiveis = [
  { id: "tipo-post", nome: "Post social" },
  { id: "tipo-landing-page", nome: "Landing page" },
  { id: "tipo-email", nome: "E-mail marketing" },
  { id: "tipo-anuncio", nome: "Anúncio" },
  { id: "tipo-relatorio", nome: "Relatório" },
];

/** Workflow ainda não tem tabela — some quando o domínio migrar. */
export const workflowsProjetoDisponiveis = [
  { id: "workflow-criacao", nome: "Criação padrão" },
  { id: "workflow-midia", nome: "Mídia paga" },
  { id: "workflow-conteudo", nome: "Conteúdo e revisão" },
];

// ======================================================================================
// Projeção legada dos 3 projetos fictícios
// ======================================================================================

/**
 * **Não é um Projeto.** Tipo próprio, de propósito: sem `codigoReferencia`, sem
 * `codigoInterno`, sem status nem arquivamento. Um `Projeto` real tem tudo isso e vem da
 * API; confundir os dois é exatamente o que este tipo separado impede.
 */
export type ProjetoLegado = {
  id: string;
  nome: string;
  clienteId: string;
  resumo: string;
  modeloCampanha: ProjetoModeloCampanhaItem[];
};

function criarModeloCampanha(seed: string): ProjetoModeloCampanhaItem[] {
  return [
    {
      id: `modelo-item-${seed}-1`,
      nomeDemanda: "Posts de lançamento",
      tipoTarefaId: "tipo-post",
      tipoTarefaNome: "Post social",
      briefingBase: "Criar peças para divulgação da campanha nas redes sociais.",
      prioridadePadrao: "media",
      workflowSugeridoId: "workflow-criacao",
      workflowSugeridoNome: "Criação padrão",
      responsavelOuSetorSugeridoId: "dep-criacao",
      responsavelOuSetorSugeridoNome: "Criação",
    },
    {
      id: `modelo-item-${seed}-2`,
      nomeDemanda: "Plano de mídia",
      tipoTarefaId: "tipo-anuncio",
      tipoTarefaNome: "Anúncio",
      briefingBase: "Definir segmentação, verba e canais de mídia paga.",
      prioridadePadrao: "alta",
      workflowSugeridoId: "workflow-midia",
      workflowSugeridoNome: "Mídia paga",
      responsavelOuSetorSugeridoId: "dep-midia",
      responsavelOuSetorSugeridoNome: "Mídia",
    },
  ];
}

/**
 * Os 3 projetos que existiam em `projetosMock`, reduzidos aos **cinco campos** que os
 * consumidores ainda mockados leem de fato (`id`, `nome`, `clienteId` diretamente; `resumo`
 * e `modeloCampanha` pelas funções de resolução de `lib/demandas.ts`).
 *
 * Eles **não** entram no banco, **não** aparecem em `ProjetosView` e **não** são Projeto
 * real para efeito nenhum. Existem por um motivo só: `lib/demandas.ts` referencia
 * `projeto-1/2/3`, e a Fase 2D nasce com seed vazio — nenhum projeto real carrega esses
 * ids. Sem esta projeção, as demandas mostrariam o id cru no lugar do nome.
 *
 * Remover junto com a migração de Demanda.
 */
export const projetosLegado: ProjetoLegado[] = [
  {
    id: "projeto-1",
    nome: "Reposicionamento institucional",
    clienteId: "cliente-1",
    resumo:
      "Campanha focada em consolidar mensagens-chave, revisar materiais institucionais e organizar entregas recorrentes para redes sociais.",
    modeloCampanha: criarModeloCampanha("p1"),
  },
  {
    id: "projeto-2",
    nome: "Campanha de captação",
    clienteId: "cliente-2",
    resumo: "Planejamento inicial de peças, mídia paga e cadência de conteúdo.",
    modeloCampanha: criarModeloCampanha("p2").slice(0, 1),
  },
  {
    id: "projeto-3",
    nome: "Calendário promocional",
    clienteId: "cliente-3",
    resumo: "Projeto concluído com entregas de calendário, peças base e ajustes finais aprovados.",
    modeloCampanha: [],
  },
];

// ======================================================================================
// Resolvedores — vinham de projetos-mock.ts
// ======================================================================================

export function resolveClienteProjetoNome(clienteId: string | null | undefined): string {
  if (!clienteId) return "Sem cliente (sem projeto vinculado)";
  return clientesProjetoDisponiveis.find((cliente) => cliente.id === clienteId)?.nome ?? clienteId;
}

export function resolveResponsaveisProjetoNomes(ids: string[]): string {
  if (ids.length === 0) return "-";
  return ids
    .map((id) => responsaveisProjetoDisponiveis.find((responsavel) => responsavel.id === id)?.nome ?? id)
    .join(", ");
}

export function resolveDepartamentosProjetoNomes(ids: string[]): string {
  if (ids.length === 0) return "-";
  return ids
    .map((id) => departamentosProjetoDisponiveis.find((departamento) => departamento.id === id)?.nome ?? id)
    .join(", ");
}
