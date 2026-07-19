"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usuariosBrowserClient } from "@/lib/api/usuarios-client";
import type {
  UsuarioErrorCode,
  UsuarioUpdatePayload,
} from "@/types/usuario-api";

const UNEXPECTED_ERROR_MESSAGE =
  "Não foi possível atualizar o usuário. Tente novamente.";

type UsuarioUpdateState =
  | { status: "idle"; error: null }
  | { status: "submitting"; error: null }
  | { status: "error"; error: string };

function usuarioUpdateErrorMessage(code: UsuarioErrorCode): string {
  switch (code) {
    case "CONFLICT":
      return "Já existe um usuário com os dados informados.";
    case "INVALID_REQUEST":
    case "VALIDATION_ERROR":
      return "Revise os dados informados e tente novamente.";
    case "NOT_FOUND":
      return "O usuário não foi encontrado.";
    case "FORBIDDEN":
      return "Você não tem permissão para editar usuários.";
    case "UNAUTHENTICATED":
      return "Sua sessão expirou. Entre novamente.";
    case "BACKEND_UNAVAILABLE":
    case "BACKEND_TIMEOUT":
      return "O serviço de usuários está indisponível. Tente novamente.";
    default:
      return UNEXPECTED_ERROR_MESSAGE;
  }
}

export function useUsuarioUpdate() {
  const [state, setState] = useState<UsuarioUpdateState>({
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
    async (
      usuarioId: string,
      payload: UsuarioUpdatePayload,
    ): Promise<boolean> => {
      if (submittingRef.current) return false;

      submittingRef.current = true;
      setState({ status: "submitting", error: null });

      try {
        const result = await usuariosBrowserClient.atualizarUsuario(
          usuarioId,
          payload,
        );
        if (!mountedRef.current) return false;

        if (!result.ok) {
          setState({
            status: "error",
            error: usuarioUpdateErrorMessage(result.error.error.code),
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
