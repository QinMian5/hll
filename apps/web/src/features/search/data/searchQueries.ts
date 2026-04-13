// abstract: TanStack Query adapters for the backend-driven search page contract.
// out_of_scope: Search page rendering, ranking semantics, and URL state ownership.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { getContractsClient } from "../../../shared/api/contractsClient";

export type SearchResponse = components["schemas"]["SearchResponse"];

class SearchRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SearchRequestError";
    this.status = status;
  }
}

const searchQueryKeys = {
  query: (query: string) => ["search", query] as const,
};

async function fetchSearchResults(query: string): Promise<SearchResponse> {
  const result = await getContractsClient().GET("/api/v1/search", {
    params: { query: { query } },
  });

  if (!result.response.ok) {
    throw new SearchRequestError(
      `Search request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error("Search response did not include a payload.");
  }

  return result.data;
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
