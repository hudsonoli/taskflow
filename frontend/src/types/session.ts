import type { AuthCurrentUser, AuthErrorResponse } from "./auth";

export type AuthState =
  | { status: "loading"; user: null; error: null }
  | { status: "authenticated"; user: AuthCurrentUser; error: null }
  | {
      status: "unauthenticated";
      user: null;
      error: AuthErrorResponse | null;
    }
  | { status: "error"; user: null; error: AuthErrorResponse };

export type AuthAction =
  | { type: "loading" }
  | { type: "authenticated"; user: AuthCurrentUser }
  | { type: "unauthenticated"; error?: AuthErrorResponse }
  | { type: "error"; error: AuthErrorResponse };

type AuthContextState<State extends AuthState = AuthState> =
  State extends AuthState ? Pick<State, "status" | "user"> : never;

export type AuthContextValue = AuthContextState & {
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

export type AuthOperationSequence = {
  begin: () => number;
  invalidate: () => void;
  isLatest: (operationId: number) => boolean;
};

export function createAuthOperationSequence(): AuthOperationSequence {
  let latestOperationId = 0;

  return {
    begin() {
      latestOperationId += 1;
      return latestOperationId;
    },
    invalidate() {
      latestOperationId += 1;
    },
    isLatest(operationId) {
      return operationId === latestOperationId;
    },
  };
}

export const initialAuthState: AuthState = {
  status: "loading",
  user: null,
  error: null,
};

export function authReducer(_state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "loading":
      return initialAuthState;
    case "authenticated":
      return {
        status: "authenticated",
        user: action.user,
        error: null,
      };
    case "unauthenticated":
      return {
        status: "unauthenticated",
        user: null,
        error: action.error ?? null,
      };
    case "error":
      return {
        status: "error",
        user: null,
        error: action.error,
      };
  }
}
