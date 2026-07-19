"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usuariosBrowserClient } from "@/lib/api/usuarios-client";
import type { Usuario } from "@/types/usuario-domain";

const SEARCH_DEBOUNCE_MS = 300;
const UNEXPECTED_ERROR_MESSAGE =
  "Não foi possível carregar os usuários. Tente novamente.";

type UsuariosListState =
  | { status: "loading"; usuarios: Usuario[]; error: null }
  | { status: "success"; usuarios: Usuario[]; error: null }
  | { status: "empty"; usuarios: Usuario[]; error: null }
  | { status: "error"; usuarios: Usuario[]; error: string };

export function useUsuariosList(search: string) {
  const [state, setState] = useState<UsuariosListState>({
    status: "loading",
    usuarios: [],
    error: null,
  });
  const latestRequestIdRef = useRef(0);

  const requestUsuarios = useCallback(async (searchValue: string) => {
    const requestId = latestRequestIdRef.current + 1;
    latestRequestIdRef.current = requestId;

    setState((current) => ({
      status: "loading",
      usuarios: current.usuarios,
      error: null,
    }));

    try {
      const result = await usuariosBrowserClient.listarUsuarios({
        search: searchValue.trim() || undefined,
        limit: 50,
        offset: 0,
      });

      if (requestId !== latestRequestIdRef.current) return;

      if (!result.ok) {
        setState({
          status: "error",
          usuarios: [],
          error: result.error.error.message,
        });
        return;
      }

      setState({
        status: result.data.items.length === 0 ? "empty" : "success",
        usuarios: result.data.items,
        error: null,
      });
    } catch {
      if (requestId !== latestRequestIdRef.current) return;

      setState({
        status: "error",
        usuarios: [],
        error: UNEXPECTED_ERROR_MESSAGE,
      });
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void requestUsuarios(search);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeoutId);
      latestRequestIdRef.current += 1;
    };
  }, [requestUsuarios, search]);

  const retry = useCallback(() => {
    void requestUsuarios(search);
  }, [requestUsuarios, search]);

  return {
    ...state,
    retry,
  };
}
