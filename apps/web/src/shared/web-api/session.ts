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

export interface AccountProfile {
  readonly email?: string;
  readonly id: string;
  readonly name?: string;
}

export interface UpdateAccountProfileRequest {
  readonly name: string | null;
}

export async function fetchWebSession(): Promise<WebSessionResponse> {
  return await fetchWebApiJson<WebSessionResponse>("/web-api/auth/session");
}

export async function fetchAccountProfile(): Promise<AccountProfile> {
  return await fetchWebApiJson<AccountProfile>("/web-api/auth/profile");
}

export async function updateAccountProfile(
  request: UpdateAccountProfileRequest,
): Promise<AccountProfile> {
  return await fetchWebApiJson<AccountProfile>("/web-api/auth/profile", {
    body: request,
    method: "PATCH",
  });
}
