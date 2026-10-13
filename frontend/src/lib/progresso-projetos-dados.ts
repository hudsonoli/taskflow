// Carregamento da visão "Progresso" de Projetos. SOMENTE endpoints que já existem e já respeitam o RBAC do usuário (a tela nunca amplia o que ele pode ver):
//   • GET /projetos                                  → projetos (1 requisição)
//   • GET /demandas?projetoId=<csv>&limit=200        → tarefas dos projetos, em LOTE (etapas, etapa atual, responsáveis e prazo já vêm no payload) — 1 requisição por 200 tarefas
//   • GET /sessoes-trabalho/trafego/agora            → quem trabalha agora (PESSOAS) — só admin/gestor (Central de Tráfego); 1–3 requisições
//   • GET /sessoes-trabalho/pauta/em-execucao        → fallback: só QUAIS tarefas têm alguém trabalhando (Atendimento/Heads/Gestão)
// Nenhuma requisição por linha, por etapa ou por avatar (nomes/avatares vêm do cache de diretórios já usado nas demais telas).
import { getAgoraTrafegoSessoes } from "@/lib/api";
import { listDemandasReais, listProjetosReais, listarDemandasEmExecucaoNaPauta } from "@/lib/api-backend";
import { FILTROS_TRAFEGO_VAZIOS } from "@/lib/filtros-trafego";
import type { TrabalhandoAgora } from "@/lib/projetos-progresso";
import { SEM_TRABALHO_AGORA } from "@/lib/projetos-progresso";
import type { Demanda } from "@/types/demanda";
import type { Projeto } from "@/types/projeto";

/** Projetos por requisição de tarefas (o filtro `projetoId` é uma lista CSV de UUIDs — mantém a URL curta). */
export const PROJETOS_POR_REQUISICAO = 40;
/** O servidor entrega no máximo 200 por página. */
export const TAMANHO_PAGINA_TAREFAS = 200;
/** Teto de segurança da primeira versão: acima disso a tela AVISA que os totais podem estar incompletos (nunca mostra um total falso em silêncio). */
export const MAX_TAREFAS_CARREGADAS = 1000;
const MAX_PAGINAS_SESSOES = 3;

export type DadosProgresso = {
  projetos: Projeto[];
  tarefas: Demanda[];
  /** true = bateu o teto: os totais por projeto podem estar incompletos */
  truncado: boolean;
  agora: TrabalhandoAgora;
  /** quantas requisições a carga fez (auditoria de N+1) */
  requisicoes: number;
};

export async function carregarProgressoProjetos(): Promise<DadosProgresso> {
  let requisicoes = 0;
  const projetos = (await listProjetosReais()).filter((projeto) => projeto.status !== "arquivado");
  requisicoes += 1;

  const tarefas: Demanda[] = [];
  let truncado = false;
  for (let i = 0; i < projetos.length && !truncado; i += PROJETOS_POR_REQUISICAO) {
    const ids = projetos.slice(i, i + PROJETOS_POR_REQUISICAO).map((projeto) => projeto.id).join(",");
    for (let offset = 0; ; offset += TAMANHO_PAGINA_TAREFAS) {
      const pagina = await listDemandasReais({ projetoId: ids, limit: TAMANHO_PAGINA_TAREFAS, offset });
      requisicoes += 1;
      tarefas.push(...pagina);
      if (pagina.length < TAMANHO_PAGINA_TAREFAS) break;
      if (tarefas.length >= MAX_TAREFAS_CARREGADAS) {
        truncado = true;
        break;
      }
    }
  }

  const { agora, requisicoes: reqSessoes } = projetos.length > 0 ? await carregarTrabalhandoAgora() : { agora: SEM_TRABALHO_AGORA, requisicoes: 0 };
  return { projetos, tarefas, truncado, agora, requisicoes: requisicoes + reqSessoes };
}

/**
 * Quem está trabalhando agora, conforme a autoridade de quem olha: PESSOAS (Central de Tráfego: admin/gestor) → senão só as TAREFAS com alguém trabalhando (Pauta global) → senão nada.
 * Qualquer falha de autorização cai para o próximo nível em silêncio: o indicador é complementar e nunca derruba a tela.
 */
export async function carregarTrabalhandoAgora(): Promise<{ agora: TrabalhandoAgora; requisicoes: number }> {
  let requisicoes = 0;
  try {
    const porDemanda: Record<string, string[]> = {};
    for (let pagina = 0; pagina < MAX_PAGINAS_SESSOES; pagina += 1) {
      const resposta = await getAgoraTrafegoSessoes({ ...FILTROS_TRAFEGO_VAZIOS, demandaQuery: "", limit: 200, offset: pagina * 200 });
      requisicoes += 1;
      for (const item of resposta.items) {
        if (!item.usuarioId) continue;
        porDemanda[item.demandaId] = [...(porDemanda[item.demandaId] ?? []), item.usuarioId];
      }
      if ((pagina + 1) * 200 >= resposta.total) break;
    }
    return { agora: { fonte: "pessoas", porDemanda }, requisicoes };
  } catch {
    requisicoes += 1;
  }
  try {
    const ids = await listarDemandasEmExecucaoNaPauta();
    requisicoes += 1;
    return { agora: { fonte: "demandas", demandaIds: new Set(ids) }, requisicoes };
  } catch {
    requisicoes += 1;
    return { agora: SEM_TRABALHO_AGORA, requisicoes };
  }
}
