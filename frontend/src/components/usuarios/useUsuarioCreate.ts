"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usuariosBrowserClient } from "@/lib/api/usuarios-client";
import type {
  UsuarioCreatePayload,
  UsuarioErrorCode,
} from "@/types/usuario-api";

const UNEXPECTED_ERROR_MESSAGE =
  "Não foi possível criar o usuário. Tente novamente.";

type UsuarioCreateState =
  | { status: "idle"; error: null }
  | { status: "submitting"; error: null }
  | { status: "error"; error: string };

function usuarioCreateErrorMessage(code: UsuarioErrorCode): string {
  switch (code) {
    case "CONFLICT":
      return "Já existe um usuário com os dados informados.";
    case "INVALID_REQUEST":
    case "VALIDATION_ERROR":
      return "Revise os dados informados e tente novamente.";
    case "FORBIDDEN":
      return "Você não tem permissão para criar usuários.";
    case "UNAUTHENTICATED":
      return "Sua sessão expirou. Entre novamente.";
    case "BACKEND_UNAVAILABLE":
    case "BACKEND_TIMEOUT":
      return "O serviço de usuários está indisponível. Tente novamente.";
    default:
      return UNEXPECTED_ERROR_MESSAGE;
  }
}

export function useUsuarioCreate() {
  const [state, setState] = useState<UsuarioCreateState>({
    status: "idle",
    error: null,
  });
  const mountedRef = useRef(true);
  const submittingRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const submit = useCallback(
    async (payload: UsuarioCreatePayload): Promise<boolean> => {
      if (submittingRef.current) return false;

      submittingRef.current = true;
      setState({ status: "submitting", error: null });

      try {
        const result = await usuariosBrowserClient.criarUsuario(payload);
        if (!mountedRef.current) return false;

        if (!result.ok) {
          setState({
            status: "error",
            error: usuarioCreateErrorMessage(result.error.error.code),
          });
          return false;
        }

        setState({ status: "idle", error: null });
        return true;
      } catch {
        if (!mountedRef.current) return false;

        setState({
          status: "error",
          error: UNEXPECTED_ERROR_MESSAGE,
        });
        return false;
      } finally {
        submittingRef.current = false;
      }
    },
    [],
  );

  const reset = useCallback(() => {
    if (submittingRef.current) return;
    setState({ status: "idle", error: null });
  }, []);

  return {
    submit,
    status: state.status,
    error: state.error,
    reset,
  };
}
