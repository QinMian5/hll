// abstract: TanStack Query adapter for public repository summary metadata.
// out_of_scope: GitHub API transport and app shell rendering.

import { queryOptions, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "./client";

export interface RepositorySummaryResponse {
  readonly repositoryUrl: string;
  readonly stars: number;
}

export const repositorySummaryQueryKeys = {
  summary: ["repository", "summary"] as const,
};

export async function fetchRepositorySummary(): Promise<RepositorySummaryResponse> {
  return await fetchWebApiJson<RepositorySummaryResponse>(
    "/web-api/repository-summary",
  );
}

export function repositorySummaryQueryOptions() {
  return queryOptions({
    queryFn: fetchRepositorySummary,
    queryKey: repositorySummaryQueryKeys.summary,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRepositorySummaryQuery() {
  return useQuery(repositorySummaryQueryOptions());
}
