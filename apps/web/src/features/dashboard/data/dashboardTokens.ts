// abstract: TanStack Query adapters for dashboard token lifecycle endpoints.
// out_of_scope: Dashboard page rendering and server-side Logto/MCP adapters.

import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";
import type {
  CreateDashboardTokenInput,
  DashboardTokenMutationResponse,
  DashboardTokenRow,
  DashboardTokensResponse,
  DeleteDashboardTokenInput,
  RenameDashboardTokenInput,
} from "../types";

interface DashboardTokenApiRow {
  readonly createdAt: string;
  readonly expiresAt: string | null;
  readonly lastUsedAt: string | null;
  readonly maskedToken: string;
  readonly name: string;
  readonly successfulSearchCount?: number | null;
  readonly tokenValue: string;
  readonly usageCount?: number | null;
}

interface DashboardTokensApiResponse {
  readonly tokens: readonly DashboardTokenApiRow[];
  readonly usageAvailable: boolean;
}

interface DashboardTokenMutationApiResponse {
  readonly token: DashboardTokenApiRow;
  readonly usageAvailable: boolean;
}

const dashboardTokenQueryKeys = {
  tokens: ["dashboard", "tokens"] as const,
};

function normalizeUsageCount(token: DashboardTokenApiRow): number | null {
  if (typeof token.usageCount === "number") {
    return token.usageCount;
  }

  if (typeof token.successfulSearchCount === "number") {
    return token.successfulSearchCount;
  }

  return null;
}

function normalizeTokenRow(token: DashboardTokenApiRow): DashboardTokenRow {
  return {
    createdAt: token.createdAt,
    expiresAt: token.expiresAt,
    lastUsedAt: token.lastUsedAt,
    maskedToken: token.maskedToken,
    name: token.name,
    tokenValue: token.tokenValue,
    usageCount: normalizeUsageCount(token),
  };
}

function normalizeTokensResponse(
  response: DashboardTokensApiResponse,
): DashboardTokensResponse {
  return {
    tokens: response.tokens.map(normalizeTokenRow),
    usageAvailable: response.usageAvailable,
  };
}

function normalizeMutationResponse(
  response: DashboardTokenMutationApiResponse,
): DashboardTokenMutationResponse {
  return {
    token: normalizeTokenRow(response.token),
    usageAvailable: response.usageAvailable,
  };
}

export async function fetchDashboardTokens(): Promise<DashboardTokensResponse> {
  const response = await fetchWebApiJson<DashboardTokensApiResponse>(
    "/web-api/dashboard/tokens",
  );

  return normalizeTokensResponse(response);
}

export async function createDashboardToken(
  input: CreateDashboardTokenInput,
): Promise<DashboardTokenMutationResponse> {
  const response = await fetchWebApiJson<DashboardTokenMutationApiResponse>(
    "/web-api/dashboard/tokens",
    {
      body: input,
      method: "POST",
    },
  );

  return normalizeMutationResponse(response);
}

export async function renameDashboardToken(
  input: RenameDashboardTokenInput,
): Promise<DashboardTokenMutationResponse> {
  const response = await fetchWebApiJson<DashboardTokenMutationApiResponse>(
    "/web-api/dashboard/tokens",
    {
      body: input,
      method: "PATCH",
    },
  );

  return normalizeMutationResponse(response);
}

export async function deleteDashboardToken(
  input: DeleteDashboardTokenInput,
): Promise<void> {
  await fetchWebApiJson<void>("/web-api/dashboard/tokens/delete", {
    body: input,
    method: "POST",
  });
}

export function dashboardTokensQueryOptions() {
  return queryOptions({
    queryFn: fetchDashboardTokens,
    queryKey: dashboardTokenQueryKeys.tokens,
  });
}

export function useDashboardTokensQuery() {
  return useQuery(dashboardTokensQueryOptions());
}

export function useCreateDashboardTokenMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDashboardToken,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dashboardTokenQueryKeys.tokens,
      });
    },
  });
}

export function useRenameDashboardTokenMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: renameDashboardToken,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dashboardTokenQueryKeys.tokens,
      });
    },
  });
}

export function useDeleteDashboardTokenMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDashboardToken,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dashboardTokenQueryKeys.tokens,
      });
    },
  });
}
