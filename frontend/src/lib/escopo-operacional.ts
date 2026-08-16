// Camada única de regras de escopo, status, atraso, estimativa e capacidade das visões
// operacionais (Meu Dia, Meu Departamento, Minhas Demandas, Central de Tráfego).
//
// Fase 0 (mock): nenhuma tela deve reimplementar estas regras — sempre importar daqui.
// Autorização nesta fase é SOMENTE UX (ver funções podeAcessar*). Esconder um item de menu
// ou bloquear uma rota no cliente NÃO é segurança: qualquer usuário ainda pode navegar
// diretamente para a URL e o estado React continua acessível no navegador. A aplicação real
// dessas regras (limitando a consulta na origem dos dados) só existirá quando Tarefa,
// Departamento, Equipe e permissões forem portados para o backend — nesta fase, esse
// domínio inteiro ainda é `useState` local (`AppDataContext`), sem tabela nem API própria.
// As assinaturas abaixo foram desenhadas para virarem, sem mudar a UI, uma chamada de API
// (ex.: `classificarTarefa` -> campo calculado vindo do backend; `podeAcessar*` -> claim do
// token; `horasExecutadasPorEscopo` -> agregação SQL).

import { elapsedSeconds } from "@/lib/trafego";
import { demandaTemResponsavel, normalizarUsuarioId } from "@/lib/demandas";
import { isDentroExpediente } from "@/lib/regra-expediente-mock";
import { correspondeDepartamento, resolverDepartamentoPorReferencia } from "@/lib/referencias";
import { converterQuantidadeEmHoras } from "@/lib/workflow-modelo";
import { perfisComAcessoAdministrativo, perfisComAcessoFinanceiro } from "@/types/usuario";
import { PERFIL_PARA_PERFIL_BASE } from "@/lib/api-backend";
import type { ClienteDiretorioItem, DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { Demanda } from "@/types/demanda";
import type { RegraExpediente } from "@/types/regra-expediente";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { Usuario } from "@/types/usuario";

// ---------------------------------------------------------------------------------
// Datas auxiliares (únicas do módulo — reaproveitar em vez de recriar em cada tela)
// ---------------------------------------------------------------------------------

export function mesmoDia(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function inicioDaSemana(data: Date): Date {
  const dia = data.getDay();
  const diffAteSegunda = dia === 0 ? 6 : dia - 1;
  const inicio = new Date(data);
  inicio.setDate(data.getDate() - diffAteSegunda);
  inicio.setHours(0, 0, 0, 0);
  return inicio;
}

export function fimDaSemana(data: Date): Date {
  const fim = inicioDaSemana(data);
  fim.setDate(fim.getDate() + 6);
  fim.setHours(23, 59, 59, 999);
  return fim;
}

function dentroDaSemana(data: Date, referencia: Date): boolean {
  return data.getTime() >= inicioDaSemana(referencia).getTime() && data.getTime() <= fimDaSemana(referencia).getTime();
}

// ---------------------------------------------------------------------------------
// classificarTarefa — definição única de "nova", "atrasada", "prevista hoje/semana" etc.
// ---------------------------------------------------------------------------------

export type OrigemDemanda = "interna" | "cliente";

export type ClassificacaoTarefa = {
  /** rascunho ou planejada — ainda não iniciada. */
  nova: boolean;
  /** status em_execucao. */
  emAndamento: boolean;
  /** status pausada ou bloqueada (mesmo agrupamento já usado no restante do app). */
  pausada: boolean;
  /** status aguardando_cliente. */
  aguardando: boolean;
  concluida: boolean;
  cancelada: boolean;
  /** Prazo da etapa atual já passou e a tarefa não foi concluída/cancelada. */
  atrasada: boolean;
  /** Prazo da etapa atual cai no dia corrente. */
  previstaHoje: boolean;
  /** Prazo da etapa atual cai na semana corrente (segunda a domingo). */
  previstaSemana: boolean;
  /** Nenhum usuário responsável atribuído. */
  semResponsavel: boolean;
  /** interna quando não há clienteId vinculado; cliente caso contrário. */
  origem: OrigemDemanda;
};

export function classificarTarefa(demanda: Demanda, agora: Date = new Date()): ClassificacaoTarefa {
  const concluida = demanda.status === "concluida";
  const cancelada = demanda.status === "cancelada";
  const finalizada = concluida || cancelada;

  const prazo = demanda.prazoEtapaAtual ? new Date(demanda.prazoEtapaAtual) : null;
  const prazoValido = prazo !== null && !Number.isNaN(prazo.getTime());

  return {
    nova: demanda.status === "rascunho" || demanda.status === "planejada",
    emAndamento: demanda.status === "em_execucao",
    pausada: demanda.status === "pausada" || demanda.status === "bloqueada",
    aguardando: demanda.status === "aguardando_cliente",
    concluida,
    cancelada,
    atrasada: !finalizada && prazoValido && (prazo as Date).getTime() < agora.getTime(),
    previstaHoje: !finalizada && prazoValido && mesmoDia(prazo as Date, agora),
    previstaSemana: !finalizada && prazoValido && dentroDaSemana(prazo as Date, agora),
    semResponsavel: demanda.usuarioResponsavelIds.length === 0,
    origem: demanda.clienteId ? "cliente" : "interna",
  };
}

/**
 * Usuário que criou a tarefa. Até a Fase 2E.4 isto era resolvido varrendo `historico[]` por
 * um evento com "criada" na ação — `criadoPorUsuarioId` já é a mesma informação, real e
 * direta no próprio objeto, sem precisar do histórico (que agora é buscado à parte, por
 * Demanda, não mais embutido em toda listagem — ver DemandaHistoricoEvento).
 */
export function autorDemanda(demanda: Demanda): string | undefined {
  return demanda.criadoPorUsuarioId ?? undefined;
}

// ---------------------------------------------------------------------------------
// Autorização de tela (UX apenas — ver aviso no topo do arquivo)
// ---------------------------------------------------------------------------------

/**
 * REGRA TRANSITÓRIA (D3-A). Enquanto não existir permissão granular real, "ser do
 * Atendimento" é inferido pelo NOME do departamento. Limites que valem sempre:
 *
 * - é **classificação de UX**, nunca identidade de relacionamento — o vínculo do usuário
 *   com o departamento é o UUID, resolvido antes desta checagem;
 * - nome **nunca** é aceito em payload: a API rejeita `departamentoId` textual com 422;
 * - existe só aqui e em `podeCriarDemanda` (types/usuario.ts) — nenhuma tela pode repetir
 *   a comparação por conta própria;
 * - sai quando o módulo de permissões substituir a inferência por concessão explícita.
 */
const NOME_DEPARTAMENTO_ATENDIMENTO = "atendimento";

/**
 * Head de um departamento nesta fase = dono formal (`Departamento.responsavelId`) OU
 * marcado como líder (`Usuario.liderDepartamento`) dentro do próprio departamento —
 * união das duas regras já existentes no app (cadastro de departamento e permissão de
 * criar tarefa), para não divergir de comportamento já aprovado.
 */
export function resolverHeadDepartamento(usuario: Usuario, departamentos: DepartamentoDiretorioItem[]): DepartamentoDiretorioItem | undefined {
  return departamentos.find(
    (departamento) =>
      departamento.responsavelUsuarioId === usuario.id ||
      (usuario.liderDepartamento && correspondeDepartamento(usuario.departamentoId, departamento)),
  );
}

/**
 * Atendimento nesta fase = usuário pertence ao departamento cujo nome é "Atendimento".
 *
 * O **vínculo** é resolvido pelo identificador, na camada central; só o departamento já
 * resolvido tem o nome consultado para classificar a regra. O nome nunca decide a quem o
 * usuário pertence — ver NOME_DEPARTAMENTO_ATENDIMENTO acima.
 */
export function resolverEhAtendimento(usuario: Usuario, departamentos: DepartamentoDiretorioItem[]): boolean {
  const departamento = resolverDepartamentoPorReferencia(usuario.departamentoId, departamentos);
  return departamento?.nome.trim().toLowerCase() === NOME_DEPARTAMENTO_ATENDIMENTO;
}

export function podeAcessarMeuDepartamento(usuario: Usuario, departamentos: DepartamentoDiretorioItem[]): boolean {
  return resolverHeadDepartamento(usuario, departamentos) !== undefined;
}

export function podeAcessarMinhasDemandas(usuario: Usuario, departamentos: DepartamentoDiretorioItem[]): boolean {
  return resolverEhAtendimento(usuario, departamentos);
}

/**
 * "Gestor autorizado" nesta fase reaproveita `perfisComAcessoFinanceiro` (só usado
 * internamente aqui — nenhuma tela deve checar perfil diretamente). Uma concessão
 * explícita por pessoa é trabalho de fase futura, quando existir permissão granular real.
 */
export function podeAcessarCentralTrafego(usuario: Usuario): boolean {
  return perfisComAcessoFinanceiro.includes(usuario.perfil);
}

/**
 * Módulo administrativo "Acesso" (histórico de login: hora, IP, navegador, sistema
 * operacional) — restrito a Admin, Gestor, Diretoria (e SuperAdmin, acima de Admin na
 * hierarquia de perfis). Mesma ressalva: nesta fase é só UX, ver aviso no topo do arquivo.
 */
export function podeAcessarAcessos(usuario: Usuario): boolean {
  return perfisComAcessoAdministrativo.includes(usuario.perfil);
}

/**
 * Áreas administrativas: Configurações, Projetos e Relatórios.
 *
 * Espelha a autorização REAL do backend — `GET /projetos`, `/clientes`, `/fornecedores`,
 * `/departamentos`, `/equipes`, `/grupos-cliente` e `/usuarios` devolvem **403** para
 * operador. Enquanto isso valer, exibir o item no menu só produz "Acesso negado" como se
 * fosse navegação normal.
 *
 * A regra: o menu não oferece caminho que a API recusa. Quando algum desses domínios abrir
 * para mais perfis, muda-se aqui **depois** de mudar o backend — nunca antes, e nunca só
 * aqui para "fazer a tela aparecer".
 *
 * Head e Atendimento não entram: são atributos operacionais (`liderDepartamento`, nome do
 * departamento), não concessão administrativa. Head tem Meu Departamento; Atendimento tem
 * Minhas Demandas.
 *
 * Derivado de `PERFIL_PARA_PERFIL_BASE`, e não de uma lista escrita à mão: o backend só
 * conhece três perfis (`admin`/`gestor`/`operador`), e é o mapeamento que decide quem recebe
 * 403. Uma lista paralela poderia divergir dele em silêncio.
 */
export function podeAcessarAreaAdministrativa(usuario: Usuario): boolean {
  return PERFIL_PARA_PERFIL_BASE[usuario.perfil] !== "operador";
}

// ---------------------------------------------------------------------------------
// Expediente — o que a operação pode fazer fora do horário
// ---------------------------------------------------------------------------------

export const MOTIVO_ARRASTAR_FORA_EXPEDIENTE =
  "Fora do horário de expediente as tarefas não podem ser movidas no quadro.";

export const MOTIVO_INICIAR_FORA_EXPEDIENTE =
  "Fora do horário de expediente uma tarefa não pode ser iniciada.";

export type PermissoesExpediente = {
  dentroExpediente: boolean;
  /** Arrastar cards no Kanban — bloqueado fora do expediente. */
  podeArrastar: boolean;
  /** Mover para "Em execução" (iniciar) — bloqueado fora do expediente. */
  podeIniciar: boolean;
  /** Texto pronto para tooltip/aviso quando algo está bloqueado. */
  motivoBloqueio?: string;
};

/**
 * Regra operacional de expediente (pedido do time):
 * - fora do expediente nenhum card pode ser arrastado no Kanban;
 * - iniciar (mover para "Em execução") é bloqueado fora do expediente, sempre;
 * - CRIAR tarefa continua liberado fora do expediente para quem já tem permissão —
 *   Atendimento, heads e gestão (ver `podeCriarDemanda` em types/usuario.ts). Criar não é
 *   iniciar: a tarefa entra como rascunho/planejada e só roda no próximo turno.
 *
 * Mesma ressalva do topo do arquivo: nesta fase isto é UX/estado local. A regra definitiva
 * precisa ser reaplicada no backend quando Tarefa virar domínio real.
 */
export function avaliarExpedienteOperacional(regra: RegraExpediente, agora: Date): PermissoesExpediente {
  const dentroExpediente = isDentroExpediente(agora, regra);
  return {
    dentroExpediente,
    podeArrastar: dentroExpediente,
    podeIniciar: dentroExpediente,
    motivoBloqueio: dentroExpediente ? undefined : MOTIVO_ARRASTAR_FORA_EXPEDIENTE,
  };
}

// ---------------------------------------------------------------------------------
// Filtros de escopo (quem vê o quê)
// ---------------------------------------------------------------------------------

export function tarefasDoUsuario(demandas: Demanda[], usuarioId: string, diretorio: UsuarioDiretorioItem[]): Demanda[] {
  return demandas.filter((demanda) => demandaTemResponsavel(demanda, usuarioId, diretorio));
}

export function tarefasDoDepartamento(demandas: Demanda[], departamentoId: string): Demanda[] {
  return demandas.filter((demanda) => demanda.departamentoResponsavelIds.includes(departamentoId));
}

/**
 * Escopo do Atendimento: tarefas criadas pelo usuário, pelas quais é responsável, ou de
 * clientes sob sua responsabilidade comercial (`Cliente.responsavelComercialId`, regra já
 * existente no cadastro de clientes).
 */
export function tarefasDoAtendimento(demandas: Demanda[], usuario: Usuario, clientes: ClienteDiretorioItem[], diretorio: UsuarioDiretorioItem[]): Demanda[] {
  const clienteIds = new Set(
    clientes.filter((cliente) => cliente.responsavelComercialId === usuario.id).map((cliente) => cliente.id),
  );

  return demandas.filter((demanda) => {
    const criador = autorDemanda(demanda);
    return (
      criador === usuario.id ||
      demandaTemResponsavel(demanda, usuario.id, diretorio) ||
      (demanda.clienteId ? clienteIds.has(demanda.clienteId) : false)
    );
  });
}

// ---------------------------------------------------------------------------------
// Horas e capacidade (aproximações — ver comentários de cada função e rotular na UI)
// ---------------------------------------------------------------------------------

/**
 * Horas estimadas derivadas: soma do prazo relativo (`quantidadeAntesDeadline`/`unidadePrazo`)
 * de cada etapa de workflow materializada na tarefa, convertido pra horas. Aproximação — não
 * existe hoje um campo dedicado de estimativa por tarefa.
 */
export function horasEstimadasDemanda(demanda: Demanda): number {
  return demanda.workflowEtapas.reduce(
    (total, etapa) => total + converterQuantidadeEmHoras(etapa.quantidadeAntesDeadline, etapa.unidadePrazo),
    0,
  );
}

export type EscopoHoras = { usuarioIds?: string[]; departamentoIds?: string[] };

/**
 * Horas executadas no escopo informado, a partir de `SessaoTrabalho` reais (API). Sessões
 * ativas contam o tempo decorrido até `agora`. IDs de usuário são normalizados com a mesma
 * ponte usada em `demandaTemResponsavel` (famílias históricas `user-N` / `usuario-N`). Quando
 * nenhum filtro é informado (nem `usuarioIds` nem `departamentoIds`), soma todas as sessões
 * recebidas — útil para totais de empresa (Central de Tráfego).
 */
export function horasExecutadasPorEscopo(sessoes: SessaoTrabalho[], escopo: EscopoHoras, agora: Date = new Date()): number {
  const usuarioIdsNormalizados = escopo.usuarioIds?.map(normalizarUsuarioId);
  const semFiltro = escopo.usuarioIds === undefined && escopo.departamentoIds === undefined;

  const segundos = sessoes.reduce((total, sessao) => {
    const usuarioCombina =
      !!usuarioIdsNormalizados && !!sessao.usuarioId && usuarioIdsNormalizados.includes(normalizarUsuarioId(sessao.usuarioId));
    const departamentoCombina =
      !!escopo.departamentoIds && !!sessao.departamentoId && escopo.departamentoIds.includes(sessao.departamentoId);
    if (!semFiltro && !usuarioCombina && !departamentoCombina) return total;
    return total + elapsedSeconds(sessao, agora);
  }, 0);

  return segundos / 3600;
}

const HORAS_PADRAO_SEM_REGRA_EXPEDIENTE = 8;

function paraMinutos(horaMinuto: string): number {
  const [horas, minutos] = horaMinuto.split(":").map(Number);
  return horas * 60 + minutos;
}

/**
 * Capacidade aproximada (horas) = duração dos turnos de `RegraExpediente` (única regra de
 * horário hoje, por empresa — não por pessoa) × número de pessoas × dias do período. Se a
 * regra estiver desativada, assume um padrão comercial de 8h/dia como aproximação — rotular
 * sempre como "capacidade aproximada" na UI, nunca como dado oficial.
 */
export function capacidadeAproximada(regraExpediente: RegraExpediente, pessoas: number, dias = 1): number {
  if (pessoas <= 0 || dias <= 0) return 0;
  if (!regraExpediente.ativo) return HORAS_PADRAO_SEM_REGRA_EXPEDIENTE * pessoas * dias;

  const minutosManha = Math.max(0, paraMinutos(regraExpediente.manhaFim) - paraMinutos(regraExpediente.manhaInicio));
  const minutosTarde = Math.max(0, paraMinutos(regraExpediente.tardeFim) - paraMinutos(regraExpediente.tardeInicio));
  const horasDiaPorPessoa = (minutosManha + minutosTarde) / 60;
  return horasDiaPorPessoa * pessoas * dias;
}

export type SobrecargaEstimada = {
  sobrecarregado: boolean;
  /** 0–100+ — percentual de ocupação da capacidade aproximada. */
  percentualOcupacao: number;
};

/** Sobrecarga estimada = horas estimadas atribuídas acima da capacidade aproximada do período. */
export function detectarSobrecargaEstimada(horasEstimadas: number, capacidade: number): SobrecargaEstimada {
  if (capacidade <= 0) {
    return { sobrecarregado: horasEstimadas > 0, percentualOcupacao: horasEstimadas > 0 ? 100 : 0 };
  }
  const percentualOcupacao = (horasEstimadas / capacidade) * 100;
  return { sobrecarregado: percentualOcupacao > 100, percentualOcupacao };
}

/** Formatação única de horas (decimais) em "Xh Ymin" — usar em qualquer indicador de horas. */
export function formatHoras(horas: number): string {
  if (horas <= 0) return "0h";
  const horasInteiras = Math.floor(horas);
  const minutos = Math.round((horas - horasInteiras) * 60);
  return minutos > 0 ? `${horasInteiras}h ${minutos}min` : `${horasInteiras}h`;
}
