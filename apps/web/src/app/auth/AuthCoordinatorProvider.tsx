// abstract: Shared browser auth coordinator for session state and recovery actions.
// out_of_scope: BFF Logto callbacks, feature authorization, and token storage.

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  type PropsWithChildren,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { subscribeToWebAuthErrors } from "../../shared/web-api/errors";
import type { WebSessionResponse } from "../../shared/web-api/session";
import {
  clearAuthenticatedSessionQueries,
  sessionQueryKeys,
  useWebSessionQuery,
  webSessionQueryOptions,
} from "../../shared/web-api/sessionQueries";
import {
  startSilentSignIn,
  submitInteractiveSignIn,
  submitSignOut,
} from "./authTransport";

type AuthenticatedSession = Extract<
  WebSessionResponse,
  { readonly status: "authenticated" }
>;

export type AuthCoordinatorState =
  | { readonly status: "anonymous" }
  | {
      readonly status: "authenticated";
      readonly user: AuthenticatedSession["user"];
    }
  | { readonly status: "checking" }
  | { readonly error: unknown; readonly status: "error" }
  | { readonly status: "expired" }
  | { readonly status: "silent-checking" };

interface AuthCoordinatorActions {
  readonly attemptSilentSignIn: (returnTo: string) => Promise<boolean>;
  readonly beginInteractiveSignIn: (returnTo: string) => void;
  readonly signOut: () => void;
}

export type AuthCoordinatorValue = AuthCoordinatorState &
  AuthCoordinatorActions;

type TransientAuthState =
  | { readonly error: unknown; readonly status: "error" }
  | { readonly status: "expired" }
  | { readonly status: "silent-checking" }
  | null;

const silentAttemptStorageKey = "knowledge.auth.silent-attempted";
const AuthCoordinatorContext = createContext<AuthCoordinatorValue | null>(null);

function readSilentAttempted(): boolean {
  try {
    return window.sessionStorage.getItem(silentAttemptStorageKey) === "1";
  } catch {
    return true;
  }
}

function markSilentAttempted(): void {
  try {
    window.sessionStorage.setItem(silentAttemptStorageKey, "1");
  } catch {
    return;
  }
}

export function AuthCoordinatorProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const sessionQuery = useWebSessionQuery();
  const [transientState, setTransientState] =
    useState<TransientAuthState>(null);
  const silentAttemptRef = useRef<Promise<boolean> | null>(null);
  const interactiveSignInPendingRef = useRef(false);

  useEffect(() => {
    return subscribeToWebAuthErrors((detail) => {
      clearAuthenticatedSessionQueries(queryClient);

      if (detail.code === "session_expired") {
        setTransientState({ status: "expired" });
        return;
      }

      setTransientState(null);
    });
  }, [queryClient]);

  useEffect(() => {
    if (sessionQuery.data?.status === "authenticated") {
      setTransientState(null);
      interactiveSignInPendingRef.current = false;
    }
  }, [sessionQuery.data?.status]);

  const state = useMemo<AuthCoordinatorState>(() => {
    if (sessionQuery.data?.status === "authenticated") {
      return {
        status: "authenticated",
        user: sessionQuery.data.user,
      };
    }

    if (transientState !== null) {
      return transientState;
    }

    if (sessionQuery.isPending) {
      return { status: "checking" };
    }

    if (sessionQuery.isError) {
      return { error: sessionQuery.error, status: "error" };
    }

    return { status: "anonymous" };
  }, [
    sessionQuery.data,
    sessionQuery.error,
    sessionQuery.isError,
    sessionQuery.isPending,
    transientState,
  ]);

  const beginInteractiveSignIn = useCallback((returnTo: string) => {
    if (interactiveSignInPendingRef.current) {
      return;
    }

    interactiveSignInPendingRef.current = true;
    submitInteractiveSignIn(returnTo);
  }, []);

  const attemptSilentSignIn = useCallback(
    async (returnTo: string): Promise<boolean> => {
      if (readSilentAttempted()) {
        return false;
      }

      if (silentAttemptRef.current !== null) {
        return await silentAttemptRef.current;
      }

      markSilentAttempted();
      setTransientState({ status: "silent-checking" });

      const attempt = (async () => {
        const silentResult = await startSilentSignIn({
          returnTo,
          timeoutMs: 10_000,
        });

        if (silentResult !== "success") {
          setTransientState(null);
          return false;
        }

        try {
          const nextSession = await queryClient.fetchQuery({
            ...webSessionQueryOptions(),
            staleTime: 0,
          });

          setTransientState(null);
          return nextSession.status === "authenticated";
        } catch (error) {
          setTransientState({ error, status: "error" });
          return false;
        }
      })();

      silentAttemptRef.current = attempt;

      try {
        return await attempt;
      } finally {
        silentAttemptRef.current = null;
      }
    },
    [queryClient],
  );

  const signOut = useCallback(() => {
    queryClient.setQueryData(sessionQueryKeys.session, { status: "anonymous" });
    submitSignOut();
  }, [queryClient]);

  const value = useMemo<AuthCoordinatorValue>(
    () => ({
      ...state,
      attemptSilentSignIn,
      beginInteractiveSignIn,
      signOut,
    }),
    [attemptSilentSignIn, beginInteractiveSignIn, signOut, state],
  );

  return (
    <AuthCoordinatorContext.Provider value={value}>
      {children}
    </AuthCoordinatorContext.Provider>
  );
}

export function useAuthCoordinator(): AuthCoordinatorValue {
  const value = useContext(AuthCoordinatorContext);

  if (value === null) {
    throw new Error("AuthCoordinatorProvider is required.");
  }

  return value;
}

export function ProtectedRoute({
  children,
  returnTo,
}: {
  readonly children: ReactNode;
  readonly returnTo: string;
}) {
  const auth = useAuthCoordinator();

  useEffect(() => {
    if (auth.status === "anonymous" || auth.status === "expired") {
      auth.beginInteractiveSignIn(returnTo);
    }
  }, [auth, returnTo]);

  if (auth.status === "authenticated") {
    return <>{children}</>;
  }

  if (auth.status === "error") {
    return <div data-testid="auth-protected-route-error" role="status" />;
  }

  return <div data-testid="auth-protected-route-pending" />;
}
