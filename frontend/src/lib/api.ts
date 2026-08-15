import type { SessaoTrabalho, SessaoTrabalhoStatus } from "@/types/sessao-trabalho";
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

// Sem `empresaId`: a empresa vem do token no servidor. Mandá-la do cliente era um convite a
// divergir — o valor em uso era a string mock "empresa-principal", que nem existe no banco.
export interface ListSessoesTrabalhoParams {
  usuarioId?: string;
  departamentoId?: string;
  status?: SessaoTrabalhoStatus;
  dataInicio?: string;
  limit?: number;
}

export async function listSessoesTrabalho(params: ListSessoesTrabalhoParams = {}): Promise<SessaoTrabalho[]> {
  const search = new URLSearchParams();
  if (params.usuarioId) search.set("usuarioId", params.usuarioId);
  if (params.departamentoId) search.set("departamentoId", params.departamentoId);
  if (params.status) search.set("status", params.status);
  if (params.dataInicio) search.set("dataInicio", params.dataInicio);
  search.set("limit", String(params.limit ?? 100));

  const response = await fetch(`${API_PROXY}/sessoes-trabalho?${search.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Falha ao carregar sessões de trabalho");
  }
  return response.json();
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
