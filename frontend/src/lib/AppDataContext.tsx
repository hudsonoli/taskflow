"use client";

import { createContext, useContext, useEffect, useRef, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { usePathname } from "next/navigation";
import { useBranding } from "@/lib/BrandingContext";
import { ehRotaDeAprovacaoExterna } from "@/lib/tenant";
import { normalizarPreferencia } from "@/lib/tema";
import { fetchSessao, fetchUsuarioAtualCompleto, logout as logoutRequest } from "@/lib/auth";
import { listDemandasReais } from "@/lib/api-backend";
import { invalidarDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { invalidarDiretorioEquipes } from "@/lib/diretorioEquipes";
import { invalidarDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { REVALIDACAO_PERIODO_MS, contextoOperacionalMudou, podeRevalidar, usuarioMudou } from "@/lib/sessaoUsuario";
import { criarCoordenadorDeSessaoExpirada, envolverFetch, hrefLoginPorExpiracao } from "@/lib/sessao-expirada";
import { bloqueioDoDetalhe, detalheDeForaDoExpediente } from "@/lib/expediente-acesso";
import { storeEstadoExpediente } from "@/lib/estadoExpediente";
import type { Demanda } from "@/types/demanda";
import type { PerfilUsuario, Usuario } from "@/types/usuario";

interface AppDataContextValue {
  /**
   * Demandas REAIS, vindas da API e **já escopadas pelo servidor** (Fase 2E.1).
   *
   * Não há mais fallback para `demandasMock`, e nenhuma demanda é meio-API meio-mock: as
   * cinco coleções sem tabela (`workflowEtapas`, `checklist`, `arquivos`, `comentarios`,
   * `historico`) chegam vazias e assim ficam até 2E.2–2E.4.
   *
   * Com a base nova nascendo vazia, as telas operacionais mostram estado vazio real até que
   * demandas sejam criadas — o mesmo que aconteceu quando Projeto migrou.
   */
  demandas: Demanda[];
  /** Atualização otimista local. Quem escreve de verdade é a API — ver lib/api-backend.ts. */
  setDemandas: Dispatch<SetStateAction<Demanda[]>>;
  demandasCarregando: boolean;
  recarregarDemandas: () => Promise<void>;
  // Intenção de abrir uma tarefa específica (ex.: clique em notificação) — consumida pela tela de Tarefas.
  demandaParaAbrir: { demandaId: string; aba?: string } | null;
  setDemandaParaAbrir: Dispatch<SetStateAction<{ demandaId: string; aba?: string } | null>>;
  // Sessão real (backend) — ver lib/auth.ts. Diretório de usuários (seletores de
  // responsável/membro) agora vem de lib/diretorioUsuarios.ts (cache remoto), não deste
  // contexto — ver docs/padrao-arquivamento.md.
  sessaoCarregando: boolean;
  autenticado: boolean;
  mustChangePassword: boolean;
  usuarioAtual?: Usuario;
  perfilAtual: PerfilUsuario;
  logout: () => Promise<void>;
  recarregarSessao: () => Promise<void>;
  /**
   * Preenchido quando a sessão tenant foi encerrada por 401 (token expirado/inválido): o AppShell leva a pessoa a ESTE destino
   * (`/e/<slug>/login?reason=session_expired&next=…`) em vez do login simples. `null` no logout normal e em sessão válida.
   */
  hrefLoginExpirado: string | null;
}

const AppDataContext = createContext<AppDataContextValue | null>(null);

// Uma única coordenação por página (sobrevive a remontagens do provider): vários 401 simultâneos encerram a sessão UMA vez — ver lib/sessao-expirada.ts.
const coordenadorSessaoExpirada = criarCoordenadorDeSessaoExpirada();

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [demandasCarregando, setDemandasCarregando] = useState(true);
  const [demandaParaAbrir, setDemandaParaAbrir] = useState<{ demandaId: string; aba?: string } | null>(null);

  const [sessaoCarregando, setSessaoCarregando] = useState(true);
  const [autenticado, setAutenticado] = useState(false);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [usuarioAtual, setUsuarioAtual] = useState<Usuario | undefined>(undefined);
  const [hrefLoginExpirado, setHrefLoginExpirado] = useState<string | null>(null);
  const perfilAtual: PerfilUsuario = usuarioAtual?.perfil ?? "operador";
  // `sincronizarSessao` é estável (useCallback sem dependências); fica numa ref para `recarregarSessao` continuar
  // sem dependências de efeito, como antes.
  const { sincronizarSessao } = useBranding();
  const sincronizarSessaoRef = useRef(sincronizarSessao);
  useEffect(() => {
    sincronizarSessaoRef.current = sincronizarSessao;
  }, [sincronizarSessao]);

  async function recarregarSessao() {
    const sessao = await fetchSessao();
    // Tema pessoal: a preferência REAL (banco) chega com a sessão; sem sessão, nenhum override vale.
    sincronizarSessaoRef.current(
      sessao ? { temaPreferencia: normalizarPreferencia(sessao.temaPreferencia), empresaSlug: sessao.empresaSlug ?? null } : null,
    );
    if (!sessao) {
      setAutenticado(false);
      setMustChangePassword(false);
      setUsuarioAtual(undefined);
      setSessaoCarregando(false);
      return;
    }

    // Há sessão válida de novo: a próxima expiração volta a ser tratada (e o destino "expirada" some).
    coordenadorSessaoExpirada.resetar();
    setHrefLoginExpirado(null);
    setAutenticado(true);
    setMustChangePassword(sessao.mustChangePassword);

    if (sessao.mustChangePassword) {
      // Perfil completo só é buscado depois da troca obrigatória — /usuarios/me também
      // fica bloqueado enquanto a senha estiver pendente (ver dependency no backend).
      setUsuarioAtual(undefined);
    } else {
      const completo = await fetchUsuarioAtualCompleto();
      setUsuarioAtual(completo ?? undefined);
    }

    setSessaoCarregando(false);
  }

  async function logout() {
    setHrefLoginExpirado(null);
    storeEstadoExpediente.limpar();
    await logoutRequest();
    sincronizarSessaoRef.current(null);
    setAutenticado(false);
    setMustChangePassword(false);
    setUsuarioAtual(undefined);
  }

  // Portal Externo de Aprovação (Fase 9B): a página do CLIENTE nunca consulta nem usa a sessão do tenant (nem `/usuarios/me`): fica anônima
  // por construção, mesmo que o navegador tenha `tf_session` de um usuário interno.
  const portalExterno = ehRotaDeAprovacaoExterna(usePathname());
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (portalExterno) {
        setSessaoCarregando(false);
        return;
      }
      void recarregarSessao();
    }, 0);
    return () => clearTimeout(timeout);
  }, [portalExterno]);

  // SESSÃO TENANT EXPIRADA (401). Todas as chamadas autenticadas passam pelo proxy `/api/backend/*`; um 401 ali é sessão inválida. Este é o ÚNICO ponto que reage a
  // isso (nenhuma tela trata 401 por conta própria): um `fetch` envolvido uma vez, que dispara o encerramento UMA só vez mesmo com várias respostas simultâneas.
  // Limpa o estado autenticado (o AppShell troca a tela por um estado neutro e leva ao login com o motivo), limpa o cookie HttpOnly inválido pelo mecanismo já
  // existente (`/api/auth/logout`) e nunca olha 403/404/409/5xx nem rotas de login, Portal, Gestão ou plataforma — ver lib/sessao-expirada.ts.
  const autenticadoRef = useRef(false);
  useEffect(() => {
    autenticadoRef.current = autenticado;
  }, [autenticado]);
  const encerrarPorSessaoExpiradaRef = useRef<() => void>(() => undefined);
  useEffect(() => {
    encerrarPorSessaoExpiradaRef.current = () => {
      setHrefLoginExpirado(hrefLoginPorExpiracao(window.location.pathname, window.location.search));
      setAutenticado(false);
      setMustChangePassword(false);
      setUsuarioAtual(undefined);
      setDemandas([]);
      storeEstadoExpediente.limpar();
      sincronizarSessaoRef.current(null);
      void logoutRequest().catch(() => undefined);
    };
  });
  useEffect(() => {
    const original = window.fetch;
    const envolvido = envolverFetch(original, {
      pathname: () => window.location.pathname,
      origem: () => window.location.origin,
      aoExpirar: () => {
        if (!autenticadoRef.current) return; // já estava fora de sessão: nada a encerrar
        coordenadorSessaoExpirada.disparar(() => encerrarPorSessaoExpiradaRef.current());
      },
      // 403 FORA_DO_EXPEDIENTE (Fase Expediente 2): sessão VÁLIDA, política recusa o uso agora → o guarda do AppShell mostra "Fora do horário de expediente". NUNCA login.
      // Qualquer outro 403 (permissão, troca de senha obrigatória...) não é tocado aqui e segue o tratamento normal de cada tela.
      aoRecusar: ({ status, resposta }) => {
        if (status !== 403) return;
        resposta
          .clone()
          .json()
          .then((corpo: unknown) => {
            const detalhe = detalheDeForaDoExpediente(corpo);
            if (detalhe) storeEstadoExpediente.registrarBloqueio(bloqueioDoDetalhe(detalhe));
          })
          .catch(() => undefined);
      },
    });
    window.fetch = envolvido;
    return () => {
      if (window.fetch === envolvido) window.fetch = original;
    };
  }, []);

  // REVALIDAÇÃO DO USUÁRIO ATUAL. Perfil, permissões, departamento e Head são decididos pelo backend a cada requisição, mas
  // `usuarioAtual` era carregado só no login/montagem: promoção ou troca de departamento feita por OUTRA pessoa com a sessão
  // aberta deixava menus, "Meu Departamento" e rótulos no estado antigo. Agora a sessão se atualiza sozinha — ao voltar para a
  // aba (foco/visibilidade) e a cada 2 min com a aba visível — sem logout/login e sem reload. Uma só chamada (`/usuarios/me`);
  // só troca o estado (e descarta os diretórios em cache) se algo relevante mudou. Falha de rede nunca derruba a sessão.
  const usuarioAtualRef = useRef<Usuario | undefined>(usuarioAtual);
  const ultimaRevalidacaoRef = useRef(0);
  useEffect(() => {
    usuarioAtualRef.current = usuarioAtual;
  }, [usuarioAtual]);

  const habilitarRevalidacao = autenticado && !mustChangePassword && usuarioAtual !== undefined;
  useEffect(() => {
    if (!habilitarRevalidacao) return;
    let cancelado = false;

    async function revalidar() {
      const agora = Date.now();
      if (!podeRevalidar(ultimaRevalidacaoRef.current, agora)) return;
      ultimaRevalidacaoRef.current = agora;
      try {
        const completo = await fetchUsuarioAtualCompleto();
        if (cancelado || !completo) return; // 401: o fetch envolvido acima já encerrou a sessão; outro erro (rede/5xx) nunca derruba a sessão
        const anterior = usuarioAtualRef.current;
        if (!usuarioMudou(anterior, completo)) return;
        if (contextoOperacionalMudou(anterior, completo)) {
          // departamento/perfil/Head mudaram: diretórios em cache (departamentos, usuários, equipes) ficaram velhos
          invalidarDiretorioDepartamentos();
          invalidarDiretorioUsuarios();
          invalidarDiretorioEquipes();
        }
        setUsuarioAtual(completo);
      } catch {
        // sem rede/backend fora: mantém o que está em tela
      }
    }

    const aoVoltar = () => {
      if (document.visibilityState === "visible") void revalidar();
    };
    document.addEventListener("visibilitychange", aoVoltar);
    window.addEventListener("focus", aoVoltar);
    const periodico = window.setInterval(aoVoltar, REVALIDACAO_PERIODO_MS);
    return () => {
      cancelado = true;
      document.removeEventListener("visibilitychange", aoVoltar);
      window.removeEventListener("focus", aoVoltar);
      window.clearInterval(periodico);
    };
  }, [habilitarRevalidacao]);

  // A pausa automática por expediente saiu daqui na Fase 2E.1.
  //
  // Ela rodava num setInterval do navegador, mudava `status` para "pausada" e escrevia em
  // `historico[]`. As duas coisas deixaram de existir: `historico` não tem tabela, e o
  // expediente passou a ser validado no servidor — que recusa a ENTRADA em `em_execucao`
  // fora do horário com 409 `FORA_DE_EXPEDIENTE`.
  //
  // Pausar trabalho JÁ EM CURSO é outra coisa, e não pode viver no cliente: só rodaria com
  // alguém logado e a aba aberta. Vira job de backend — ver docs/pendencias-arquiteturais.md.

  useEffect(() => {
    // Demanda é escopada por usuário: só faz sentido carregar depois da sessão resolvida, e
    // recarregar quando ela muda. O setTimeout(0) segue o mesmo padrão do efeito de sessão
    // acima — tira o setState do corpo do efeito e evita a cascata de renders.
    const timeout = setTimeout(() => {
      if (!autenticado || mustChangePassword) {
        setDemandas([]);
        setDemandasCarregando(false);
        return;
      }
      void recarregarDemandas();
    }, 0);
    return () => clearTimeout(timeout);
  }, [autenticado, mustChangePassword]);

  async function recarregarDemandas() {
    setDemandasCarregando(true);
    try {
      setDemandas(await listDemandasReais());
    } catch {
      // Falha de rede não pode virar "não há demandas": mantém o que já estava em tela.
    } finally {
      setDemandasCarregando(false);
    }
  }

  return (
    <AppDataContext.Provider
      value={{
        demandas,
        setDemandas,
        demandasCarregando,
        recarregarDemandas,
        demandaParaAbrir,
        setDemandaParaAbrir,
        sessaoCarregando,
        autenticado,
        mustChangePassword,
        usuarioAtual,
        perfilAtual,
        logout,
        recarregarSessao,
        hrefLoginExpirado,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}

export function useAppData(): AppDataContextValue {
  const context = useContext(AppDataContext);
  if (!context) {
    throw new Error("useAppData precisa ser usado dentro de <AppDataProvider>");
  }
  return context;
}
