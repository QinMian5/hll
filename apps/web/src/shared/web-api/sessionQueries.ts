// abstract: TanStack Query adapters for web session and account profile state.
// out_of_scope: Auth route implementation and settings page composition.

import { queryOptions, useQuery } from "@tanstack/react-query";

import {
  fetchAccountProfile,
  fetchWebSession,
  type WebSessionResponse,
} from "./session";

export const sessionQueryKeys = {
  session: ["auth", "session"] as const,
};

export const accountProfileQueryKeys = {
  profile: ["auth", "profile"] as const,
};

export function webSessionQueryOptions() {
  return queryOptions<WebSessionResponse>({
    queryFn: fetchWebSession,
    queryKey: sessionQueryKeys.session,
  });
}

export function accountProfileQueryOptions() {
  return queryOptions({
    queryFn: fetchAccountProfile,
    queryKey: accountProfileQueryKeys.profile,
  });
}

export function useWebSessionQuery() {
  return useQuery(webSessionQueryOptions());
}

export function useAccountProfileQuery() {
  return useQuery(accountProfileQueryOptions());
}
