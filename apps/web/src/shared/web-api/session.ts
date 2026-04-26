// abstract: Browser adapter for BFF-owned web session state.
// out_of_scope: Logto authorization-code handling and server-side token storage.

import { fetchWebApiJson } from "./client";

export type WebSessionResponse =
  | { readonly status: "anonymous" }
  | {
      readonly status: "authenticated";
      readonly user: {
        readonly email?: string;
        readonly id: string;
        readonly name?: string;
      };
    };

export async function fetchWebSession(): Promise<WebSessionResponse> {
  return await fetchWebApiJson<WebSessionResponse>("/web-api/auth/session");
}
