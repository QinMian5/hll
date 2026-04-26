// abstract: TanStack Query adapters for the backend-driven search page contract.
// out_of_scope: Search page rendering, ranking semantics, and URL state ownership.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

export type SearchResponse = components["schemas"]["SearchResponse"];

const searchQueryKeys = {
  query: (query: string) => ["search", query] as const,
};

async function fetchSearchResults(query: string): Promise<SearchResponse> {
  return await fetchWebApiJson<SearchResponse>(
    `/web-api/search?query=${encodeURIComponent(query)}`,
  );
}

export function searchQueryOptions(query: string) {
  return queryOptions({
    queryFn: () => fetchSearchResults(query),
    queryKey: searchQueryKeys.query(query),
  });
}

export function useSearchQuery(
  query: string,
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...searchQueryOptions(query),
    enabled: options.enabled ?? true,
  });
}
