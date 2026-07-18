"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  authBrowserClient,
  type AuthClientResult,
} from "../../lib/auth/client";
import {
  authReducer,
  createAuthOperationSequence,
  initialAuthState,
} from "../../types/session";
import { AuthContext } from "./AuthContext";

function resultToAction(result: AuthClientResult) {
  switch (result.status) {
    case "authenticated":
      return { type: "authenticated", user: result.user } as const;
    case "unauthenticated":
      return {
        type: "unauthenticated",
        ...(result.error ? { error: result.error } : {}),
      } as const;
    case "error":
      return { type: "error", error: result.error } as const;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialAuthState);
  const mountedRef = useRef(false);
  const [operationSequence] = useState(createAuthOperationSequence);

  const applyResult = useCallback(
    (operationId: number, result: AuthClientResult) => {
      if (
        mountedRef.current &&
        operationSequence.isLatest(operationId)
      ) {
        dispatch(resultToAction(result));
      }
    },
    [operationSequence],
  );

  useEffect(() => {
    mountedRef.current = true;
    let active = true;
    const operationId = operationSequence.begin();

    void authBrowserClient.getInitialUser().then((result) => {
      if (active) {
        applyResult(operationId, result);
      }
    });

    return () => {
      active = false;
      mountedRef.current = false;
      operationSequence.invalidate();
    };
  }, [applyResult, operationSequence]);

  const refresh = useCallback(async () => {
    const operationId = operationSequence.begin();
    if (mountedRef.current) {
      dispatch({ type: "loading" });
    }
    applyResult(operationId, await authBrowserClient.refresh());
  }, [applyResult, operationSequence]);

  const logout = useCallback(async () => {
    const operationId = operationSequence.begin();
    applyResult(operationId, await authBrowserClient.logout());
  }, [applyResult, operationSequence]);

  const value = useMemo(() => {
    const actions = { refresh, logout };

    switch (state.status) {
      case "loading":
        return { status: state.status, user: state.user, ...actions };
      case "authenticated":
        return { status: state.status, user: state.user, ...actions };
      case "unauthenticated":
        return { status: state.status, user: state.user, ...actions };
      case "error":
        return { status: state.status, user: state.user, ...actions };
    }
  }, [state, refresh, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
