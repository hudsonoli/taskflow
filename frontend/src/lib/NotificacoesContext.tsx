"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { obterResumoNotificacoes } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { RESUMO_VAZIO, type NotificacoesResumo } from "@/types/notificacoes";

// Estado ÚNICO do badge de notificações: o menu do avatar, o sino e a página leem a MESMA contagem (uma consulta,
// `GET /notificacoes/resumo`) — nenhuma consulta independente para a mesma informação. Reconcilia quando a
// sessão carrega, quando a aba volta a ficar visível (sem polling) e sempre que alguém marca como lida (a API já
// devolve o resumo atualizado, que entra aqui por `aplicarResumo`).

type NotificacoesContextValue = {
  resumo: NotificacoesResumo;
  recarregar: () => Promise<void>;
  aplicarResumo: (resumo: NotificacoesResumo) => void;
};

const NotificacoesContext = createContext<NotificacoesContextValue>({
  resumo: RESUMO_VAZIO,
  recarregar: async () => {},
  aplicarResumo: () => {},
});

export function NotificacoesProvider({ children }: { children: ReactNode }) {
  const { autenticado, mustChangePassword } = useAppData();
  const ativo = autenticado && !mustChangePassword;
  const [resumo, setResumo] = useState<NotificacoesResumo>(RESUMO_VAZIO);

  const recarregar = useCallback(async () => {
    try {
      setResumo(await obterResumoNotificacoes());
    } catch {
      // Falha de rede não derruba a navbar: mantém o último valor conhecido.
    }
  }, []);

  useEffect(() => {
    // setTimeout(0): mesmo padrão do AppDataContext (tira o setState síncrono do corpo do efeito).
    const timeout = setTimeout(() => {
      if (ativo) void recarregar();
      else setResumo(RESUMO_VAZIO); // logout: nada do usuário anterior fica na tela
    }, 0);
    return () => clearTimeout(timeout);
  }, [ativo, recarregar]);

  useEffect(() => {
    if (!ativo) return;
    function aoVoltar() {
      if (document.visibilityState === "visible") void recarregar();
    }
    document.addEventListener("visibilitychange", aoVoltar);
    return () => document.removeEventListener("visibilitychange", aoVoltar);
  }, [ativo, recarregar]);

  const valor = useMemo(() => ({ resumo, recarregar, aplicarResumo: setResumo }), [resumo, recarregar]);
  return <NotificacoesContext.Provider value={valor}>{children}</NotificacoesContext.Provider>;
}

export function useNotificacoes() {
  return useContext(NotificacoesContext);
}
