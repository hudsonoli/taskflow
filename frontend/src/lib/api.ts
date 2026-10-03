import type { TrafegoAgoraPagina, TrafegoCarga, TrafegoIndicadores, TrafegoStatusFiltro } from "@/types/trafego";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { DemandaArquivo } from "@/types/demanda";
import type { EventoApi } from "@/types/acesso";

/**
 * Estas chamadas passaram a ir pelo **proxy autenticado** (`/api/backend/**`), como o resto
 * do app já fazia em `api-backend.ts`.
 *
 * Antes elas falavam direto com o FastAPI (`http://localhost:8010`), sem token nenhum — e era
 * essa a razão de `/eventos`, `/sessoes-trabalho` e os uploads de Demanda terem nascido sem
 * autenticação no backend: nenhum chamador enviava credencial, então exigir uma teria
 * quebrado as telas. Corrigido dos dois lados na mesma entrega.
 *
 * O proxy lê o cookie HttpOnly e injeta `Authorization: Bearer` — o navegador nunca vê o JWT.
 */
const API_PROXY = "/api/backend";

// URL de download/preview de arquivo. Continua apontando para o backend, que serve
// `/uploads/**` como conteúdo estático — ver docs/pendencias-arquiteturais.md, item 9.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export { API_BASE_URL };

export function resolveArquivoUrl(url: string): string {
  return `${API_BASE_URL}${url}`;
}

export async function uploadArquivoDemanda(codigo: string, file: File): Promise<DemandaArquivo> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_PROXY}/demandas/${encodeURIComponent(codigo)}/uploads`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao enviar arquivo");
  }
  return response.json();
}

export async function uploadArquivoFinalDemanda(codigo: string, file: File): Promise<DemandaArquivo> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_PROXY}/demandas/${encodeURIComponent(codigo)}/uploads/final`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao enviar arquivo final");
  }
  return response.json();
}

export async function listarArquivosDemanda(codigo: string): Promise<DemandaArquivo[]> {
  const response = await fetch(`${API_PROXY}/demandas/${encodeURIComponent(codigo)}/uploads`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Falha ao carregar arquivos da tarefa");
  }
  return response.json();
}

export async function excluirArquivoDemanda(codigo: string, nomeArquivo: string, final: boolean): Promise<void> {
  const search = final ? "?final=true" : "";
  const response = await fetch(
    `${API_PROXY}/demandas/${encodeURIComponent(codigo)}/uploads/${encodeURIComponent(nomeArquivo)}${search}`,
    { method: "DELETE" },
  );
  if (!response.ok && response.status !== 204) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao excluir arquivo");
  }
}

export interface AbrirSessaoTrabalhoPayload {
  agenciaId?: string | null;
  demandaId: string;
  workflowEtapaId?: string | null;
  usuarioId?: string | null;
  departamentoId?: string | null;
}

export async function abrirSessaoTrabalho(payload: AbrirSessaoTrabalhoPayload): Promise<SessaoTrabalho> {
  const response = await fetch(`${API_PROXY}/sessoes-trabalho/abrir`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao abrir sessão de trabalho");
  }
  return response.json();
}

export interface ListEventosParams {
  tipo?: string;
  limit?: number;
  offset?: number;
}

export async function listEventos(params: ListEventosParams = {}): Promise<EventoApi[]> {
  const search = new URLSearchParams();
  if (params.tipo) search.set("tipo", params.tipo);
  search.set("limit", String(params.limit ?? 100));
  if (params.offset) search.set("offset", String(params.offset));

  const response = await fetch(`${API_PROXY}/eventos?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Falha ao carregar eventos");
  }
  return response.json();
}

export interface HorasDepartamento {
  departamentoId: string;
  horasConsumidas: number;
  sessoesConsideradas: number;
}

export async function getHorasDepartamento(departamentoId: string): Promise<HorasDepartamento> {
  const search = new URLSearchParams({ departamentoId });
  const response = await fetch(`${API_PROXY}/sessoes-trabalho/horas?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao carregar horas consumidas do departamento");
  }
  return response.json();
}

/**
 * D2-D3B — "Horas executadas" da Central de Tráfego, agregado no servidor sobre o universo
 * INTEGRAL (empresa inteira, sem departamento) — nunca a listagem paginada de
 * `listSessoesTrabalho` (cap de 100). `periodoInicio` é "desde quando", sem teto — mesma
 * semântica de `periodoParaDataInicio` (lib/trafego.ts). Não confundir com
 * `getHorasDepartamento`: escopo, RBAC e período são diferentes.
 */
export async function getResumoTrafegoSessoes(periodoInicio: string): Promise<{ horasExecutadas: number }> {
  const search = new URLSearchParams({ periodoInicio });
  const response = await fetch(`${API_PROXY}/sessoes-trabalho/trafego/resumo?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao carregar horas executadas do Tráfego");
  }
  return response.json();
}

/**
 * D2-D3C1 — métricas de `TrafegoResumoCards`/`TempoOperacionalCard`, agregadas no servidor
 * sobre o universo INTEGRAL (nunca a lista de `listSessoesTrabalho`, com `limit=100`). Os
 * filtros são os da própria tela: o servidor aplica a mesma regra que `filterSessoes` aplicava
 * aqui. `demandaQuery` vai como digitada (a regra de casamento não apara).
 */
export async function getIndicadoresTrafegoSessoes(filtros: {
  periodoInicio: string;
  status: TrafegoStatusFiltro;
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
}): Promise<TrafegoIndicadores> {
  const search = new URLSearchParams({ periodoInicio: filtros.periodoInicio, status: filtros.status });
  if (filtros.usuarioIds.length > 0) search.set("usuarioIds", filtros.usuarioIds.join(","));
  if (filtros.departamentoIds.length > 0) search.set("departamentoIds", filtros.departamentoIds.join(","));
  if (filtros.demandaQuery.trim()) search.set("demandaQuery", filtros.demandaQuery);

  const response = await fetch(`${API_PROXY}/sessoes-trabalho/trafego/indicadores?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(typeof detail?.detail === "string" ? detail.detail : "Falha ao carregar os indicadores do Tráfego");
  }
  return response.json();
}

/**
 * D2-D3C2 — "Carga por usuário/departamento/equipe", agregada no servidor sobre TODAS as
 * sessões ativas (nunca a lista de `listSessoesTrabalho`, com `limit=100`). Só os filtros que
 * sempre afetaram esses rankings (usuários, departamentos, busca de demanda): período e status
 * da tela nunca os mudaram, então não são enviados.
 */
export async function getCargaTrafegoSessoes(filtros: {
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
}): Promise<TrafegoCarga> {
  const search = new URLSearchParams();
  if (filtros.usuarioIds.length > 0) search.set("usuarioIds", filtros.usuarioIds.join(","));
  if (filtros.departamentoIds.length > 0) search.set("departamentoIds", filtros.departamentoIds.join(","));
  if (filtros.demandaQuery.trim()) search.set("demandaQuery", filtros.demandaQuery);

  const consulta = search.toString();
  const response = await fetch(`${API_PROXY}/sessoes-trabalho/trafego/carga${consulta ? `?${consulta}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(typeof detail?.detail === "string" ? detail.detail : "Falha ao carregar a carga do Tráfego");
  }
  return response.json();
}

/**
 * D2-D3C3 — "Quem está trabalhando agora", paginado no servidor (`limit`/`offset`, com `total`) e
 * já com nomes de usuário/departamento/Demanda — nunca a lista de `listSessoesTrabalho` (cap de
 * 100) nem diretórios do cliente. Só os filtros que sempre afetaram a tabela (usuários,
 * departamentos, busca de demanda); período e status da tela nunca a mudaram.
 */
export async function getAgoraTrafegoSessoes(filtros: {
  usuarioIds: string[];
  departamentoIds: string[];
  demandaQuery: string;
  limit: number;
  offset: number;
}): Promise<TrafegoAgoraPagina> {
  const search = new URLSearchParams({ limit: String(filtros.limit), offset: String(filtros.offset) });
  if (filtros.usuarioIds.length > 0) search.set("usuarioIds", filtros.usuarioIds.join(","));
  if (filtros.departamentoIds.length > 0) search.set("departamentoIds", filtros.departamentoIds.join(","));
  if (filtros.demandaQuery.trim()) search.set("demandaQuery", filtros.demandaQuery);

  const response = await fetch(`${API_PROXY}/sessoes-trabalho/trafego/agora?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(typeof detail?.detail === "string" ? detail.detail : "Falha ao carregar as sessões em execução");
  }
  return response.json();
}

export async function fecharSessaoTrabalho(sessaoId: string, motivoEncerramento: string): Promise<SessaoTrabalho> {
  const response = await fetch(`${API_PROXY}/sessoes-trabalho/${sessaoId}/fechar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivoEncerramento }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Falha ao fechar sessão de trabalho");
  }
  return response.json();
}
