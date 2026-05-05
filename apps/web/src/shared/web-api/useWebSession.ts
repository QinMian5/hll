// abstract: Legacy browser hook backed by shared web session query state.
// out_of_scope: Server-side Logto SDK integration and token persistence.

import type { WebSessionResponse } from "./session";
import { useWebSessionQuery } from "./sessionQueries";

export type { WebSessionResponse };
export type WebSessionState =
  | WebSessionResponse
  | { readonly error: unknown; readonly status: "error" }
  | { readonly status: "loading" };

export function useWebSession(): WebSessionState {
  const sessionQuery = useWebSessionQuery();

  if (sessionQuery.data !== undefined) {
    return sessionQuery.data;
  }

  if (sessionQuery.isError) {
    return { error: sessionQuery.error, status: "error" };
  }

  return { status: "loading" };
}
