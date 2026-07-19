"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usuariosBrowserClient } from "@/lib/api/usuarios-client";
import type { Usuario } from "@/types/usuario-domain";

const UNEXPECTED_ERROR_MESSAGE =
  "Não foi possível carregar o usuário. Tente novamente.";

type UsuarioDetailState =
  | { status: "loading"; usuario: null; error: null }
  | { status: "success"; usuario: Usuario; error: null }
  | { status: "error"; usuario: null; error: string };

export function useUsuarioDetail(usuarioId: string) {
  const [state, setState] = useState<UsuarioDetailState>({
    status: "loading",
    usuario: null,
    error: null,
  });
  const latestRequestIdRef = useRef(0);

  const requestUsuario = useCallback(async (id: string) => {
    const requestId = latestRequestIdRef.current + 1;
    latestRequestIdRef.current = requestId;

    try {
      const result = await usuariosBrowserClient.obterUsuario(id);

      if (requestId !== latestRequestIdRef.current) return;

      if (!result.ok) {
        setState({
          status: "error",
          usuario: null,
          error: result.error.error.message,
        });
        return;
      }

      setState({
        status: "success",
        usuario: result.data.data,
        error: null,
      });
    } catch {
      if (requestId !== latestRequestIdRef.current) return;

      setState({
        status: "error",
        usuario: null,
        error: UNEXPECTED_ERROR_MESSAGE,
      });
    }
  }, []);

  useEffect(() => {
    // O agendamento permite que o cleanup do Strict Mode cancele a primeira
    // montagem de desenvolvimento antes que ela dispare um GET duplicado.
    const timeoutId = window.setTimeout(() => {
      void requestUsuario(usuarioId);
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      latestRequestIdRef.current += 1;
    };
  }, [requestUsuario, usuarioId]);

  const retry = useCallback(() => {
    setState({
      status: "loading",
      usuario: null,
      error: null,
    });
    void requestUsuario(usuarioId);
  }, [requestUsuario, usuarioId]);

  return {
    ...state,
    retry,
  };
}
