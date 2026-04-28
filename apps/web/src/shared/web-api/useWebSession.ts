// abstract: Browser hook for shared web session state.
// out_of_scope: Server-side Logto SDK integration and token persistence.

import { useEffect, useState } from "react";

import { fetchWebSession, type WebSessionResponse } from "./session";

export type { WebSessionResponse };
export type WebSessionState =
  | WebSessionResponse
  | { readonly status: "loading" };

export function useWebSession(): WebSessionState {
  const [session, setSession] = useState<WebSessionState>({
    status: "loading",
  });

  useEffect(() => {
    let isMounted = true;

    fetchWebSession()
      .then((nextSession) => {
        if (isMounted) {
          setSession(nextSession);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSession({ status: "anonymous" });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return session;
}
