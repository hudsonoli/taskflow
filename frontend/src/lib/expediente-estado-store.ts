// Store ÚNICO do estado de expediente (Fase Expediente 2) — PURO (sem React; relógio, timers e busca injetáveis). `npm run test:expediente-acesso`.
//
// Substitui o poll "por componente" de `GET /expediente/estado`: agora existe UM temporizador para o app inteiro (~30 s), ativo só enquanto há assinantes (Kanban, Meu
// Departamento, tela de configuração e o guarda do AppShell compartilham o mesmo dado). Não há segundo polling: a tela "Fora do horário de expediente" lê DESTE store.
import type { EstadoExpediente } from "../types/regra-expediente.ts";
import { bloqueioVigente, type BloqueioExpediente } from "./expediente-acesso.ts";

export const INTERVALO_ESTADO_EXPEDIENTE_MS = 30_000;
// Rajada de 403 (várias chamadas paralelas da mesma tela recusadas ao mesmo tempo) vira UMA busca: só o tick de ~30 s ignora este intervalo mínimo.
const INTERVALO_MINIMO_ENTRE_BUSCAS_MS = 2_000;

export type SnapshotEstadoExpediente = {
  estado: EstadoExpediente | null;
  carregando: boolean;
  /** Bloqueio que a tela deve mostrar agora (ou `null`). */
  bloqueio: BloqueioExpediente | null;
};

type Dependencias = {
  buscar: () => Promise<EstadoExpediente>;
  intervaloMs?: number;
  agora?: () => number;
  setIntervalo?: (acao: () => void, ms: number) => unknown;
  limparIntervalo?: (id: unknown) => void;
};

export function criarStoreEstadoExpediente(dep: Dependencias) {
  const agora = dep.agora ?? (() => Date.now());
  const setIntervalo = dep.setIntervalo ?? ((acao, ms) => setInterval(acao, ms));
  const limparIntervalo = dep.limparIntervalo ?? ((id) => clearInterval(id as ReturnType<typeof setInterval>));
  const intervalo = dep.intervaloMs ?? INTERVALO_ESTADO_EXPEDIENTE_MS;

  let estado: EstadoExpediente | null = null;
  let estadoEm = 0;
  let carregando = true;
  let erro: { bloqueio: BloqueioExpediente; em: number } | null = null;
  let timer: unknown = null;
  let emVoo: Promise<void> | null = null;
  let ultimaBusca = 0;
  let snapshot: SnapshotEstadoExpediente = { estado, carregando, bloqueio: null };
  const assinantes = new Set<() => void>();

  function recalcular() {
    const bloqueio = bloqueioVigente(estado, estadoEm, erro);
    // referência estável quando o CONTEÚDO do bloqueio não mudou (useSyncExternalStore)
    const igual = snapshot.bloqueio === bloqueio || (snapshot.bloqueio !== null && bloqueio !== null && JSON.stringify(snapshot.bloqueio) === JSON.stringify(bloqueio));
    if (snapshot.estado === estado && snapshot.carregando === carregando && igual) return;
    snapshot = { estado, carregando, bloqueio: igual ? snapshot.bloqueio : bloqueio };
    assinantes.forEach((ouvinte) => ouvinte());
  }

  function atualizar(forcar = false): Promise<void> {
    if (emVoo) return emVoo;
    if (!forcar && agora() - ultimaBusca < INTERVALO_MINIMO_ENTRE_BUSCAS_MS) return Promise.resolve();
    ultimaBusca = agora();
    emVoo = dep
      .buscar()
      .then((novo) => {
        estado = novo;
        estadoEm = agora();
        carregando = false;
      })
      .catch(() => {
        // falha de rede/5xx: mantém o último estado conhecido; nunca derruba a sessão nem inventa bloqueio
        carregando = false;
      })
      .finally(() => {
        emVoo = null;
        recalcular();
      });
    return emVoo;
  }

  function iniciarTimer() {
    if (timer !== null) return;
    timer = setIntervalo(() => void atualizar(true), intervalo);
  }

  function pararTimer() {
    if (timer === null) return;
    limparIntervalo(timer);
    timer = null;
  }

  return {
    subscribe(ouvinte: () => void) {
      assinantes.add(ouvinte);
      if (assinantes.size === 1) {
        iniciarTimer();
        void atualizar();
      }
      return () => {
        assinantes.delete(ouvinte);
        if (assinantes.size === 0) pararTimer();
      };
    },
    getSnapshot: () => snapshot,
    atualizar,
    /** Um 403 FORA_DO_EXPEDIENTE chegou numa chamada qualquer: mostra o bloqueio JÁ (sem esperar o poll) e confirma com o servidor em seguida. */
    registrarBloqueio(bloqueio: BloqueioExpediente) {
      erro = { bloqueio, em: agora() };
      recalcular();
      void atualizar();
    },
    /** Sessão encerrada (logout/401): nada do usuário anterior pode sobrar. */
    limpar() {
      estado = null;
      estadoEm = 0;
      erro = null;
      carregando = true;
      recalcular();
    },
    totalAssinantes: () => assinantes.size,
    timerAtivo: () => timer !== null,
  };
}

export type StoreEstadoExpediente = ReturnType<typeof criarStoreEstadoExpediente>;
