// Tráfego V2 — contratos das métricas OPERACIONAIS (`GET /trafego/operacional/agora` e `/gargalos`). Espelham o OpenAPI publicado (backend/app/schemas/trafego_operacional.py).
//
// TEMPO OPERACIONAL ≠ TEMPO PESSOAL: tudo aqui é o tempo DECORRIDO de Demandas/etapas num estado (`demanda_status_intervalos`). Nenhum campo é "horas trabalhadas"
// e `responsaveis` é ATRIBUIÇÃO — não executor.

export type RefNome = { id: string; nome: string };

export type EtapaAtual = { id: string; nome: string; tipo: string; departamentos: RefNome[] };

export type ResponsavelAtribuido = { usuarioId: string; nome: string };

export type AgoraKpis = {
  emExecucao: number;
  atrasadas: number;
  vencemHoje: number;
  semResponsavel: number;
  semPrazo: number;
  semEtapaAtual: number;
};

export type AgoraDemanda = {
  demandaId: string;
  codigoReferencia: string;
  numeroOperacional: number;
  identificador: string;
  titulo: string;
  projeto: RefNome | null;
  cliente: RefNome | null;
  etapaAtual: EtapaAtual | null;
  responsaveis: ResponsavelAtribuido[];
  origemResponsaveis: "etapa_atual" | "demanda";
  status: string;
  inicioEstadoAtual: string | null;
  idadeEstadoSegundos: number | null;
  prazo: string | null;
  atrasada: boolean;
};

export type TrafegoOperacionalAgora = {
  agoraServidor: string;
  fusoEmpresa: string;
  diaLocal: string;
  hojeInicio: string;
  hojeFim: string;
  escopoStatus: string[];
  kpis: AgoraKpis;
  emExecucao: AgoraDemanda[];
  emExecucaoTotal: number;
  limite: number;
  truncado: boolean;
};

/** Definição de etapa: a identidade agregável (nome normalizado + tipo + conjunto de departamentos). `chave` é opaca — serve de chave de lista, nunca aparece para o usuário. */
export type DefinicaoEtapa = { chave: string; nome: string; tipo: string; departamentos: RefNome[] };

export type GargaloEtapa = {
  definicaoEtapa: DefinicaoEtapa;
  n: number;
  nExecucao: number;
  tempoExecucaoTotalSegundos: number;
  tempoExecucaoMedioSegundos: number | null;
  tempoExecucaoMaiorSegundos: number | null;
  nPausado: number;
  tempoPausadoTotalSegundos: number;
  tempoPausadoMedioSegundos: number | null;
  tempoPausadoMaiorSegundos: number | null;
  nBloqueado: number;
  tempoBloqueadoTotalSegundos: number;
  tempoBloqueadoMedioSegundos: number | null;
  tempoBloqueadoMaiorSegundos: number | null;
  nAguardandoCliente: number;
  tempoAguardandoClienteTotalSegundos: number;
  tempoAguardandoClienteMedioSegundos: number | null;
  tempoAguardandoClienteMaiorSegundos: number | null;
};

export type TempoSemEtapa = {
  n: number;
  nExecucao: number;
  tempoExecucaoTotalSegundos: number;
  tempoExecucaoMedioSegundos: number | null;
  tempoExecucaoMaiorSegundos: number | null;
  nPausado: number;
  tempoPausadoTotalSegundos: number;
  nBloqueado: number;
  tempoBloqueadoTotalSegundos: number;
  nAguardandoCliente: number;
  tempoAguardandoClienteTotalSegundos: number;
};

export type FilaEtapa = {
  definicaoEtapa: DefinicaoEtapa;
  wip: number;
  planejadas: number;
  emExecucao: number;
  pausadas: number;
  bloqueadas: number;
  aguardandoCliente: number;
  maisAntigaDesde: string;
  maisAntigaSegundos: number;
  maisAntigaTruncadaPelaMedicao: boolean;
  idadeEstadoMaisAntigoSegundos: number;
};

export type AtualOperacional = {
  wip: number;
  planejadas: number;
  emExecucao: number;
  pausadas: number;
  bloqueadas: number;
  aguardandoCliente: number;
};

export type TrafegoOperacionalGargalos = {
  agoraServidor: string;
  periodo: { inicio: string; fim: string; fimEfetivo: string };
  filtros: { departamentoId: string | null; clienteId: string | null; projetoId: string | null; workflowEtapaId: string | null };
  medicaoDesde: string | null;
  coberturaParcial: boolean;
  etapas: GargaloEtapa[];
  etapasTotal: number;
  semEtapa: TempoSemEtapa;
  atual: AtualOperacional;
  fila: FilaEtapa[];
  filaTotal: number;
  filaSemEtapa: { workflowConcluido: number; semWorkflow: number };
  limite: number;
};

/** Parâmetros da consulta de gargalos (todos opcionais além do período). */
export type ParametrosGargalosOperacionais = {
  inicio: string;
  fim: string;
  departamentoId?: string | null;
  clienteId?: string | null;
  projetoId?: string | null;
  workflowEtapaId?: string | null;
  limite?: number;
};
