// abstract: TanStack Query adapters for the backend-driven search page contract.
// out_of_scope: Search page rendering, ranking semantics, and URL state ownership.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useMutation, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

export type SearchResponse = components["schemas"]["SearchResponse"];
export type SuggestedEditCreateResponse =
  components["schemas"]["SuggestedEditCreateResponse"];

export interface CreateSuggestedEditPayload {
  readonly baseVersion: number;
  readonly nodeId: number;
  readonly suggestedContent: string;
  readonly suggestedTitle: string;
}

const searchQueryKeys = {
  query: (query: string) => ["search", query] as const,
};

async function fetchSearchResults(query: string): Promise<SearchResponse> {
  return await fetchWebApiJson<SearchResponse>(
    `/web-api/search?query=${encodeURIComponent(query)}`,
  );
}

export async function createSuggestedEdit(
  payload: CreateSuggestedEditPayload,
): Promise<SuggestedEditCreateResponse> {
  return await fetchWebApiJson<SuggestedEditCreateResponse>(
    `/web-api/cards/${payload.nodeId}/suggested-edits`,
    {
      body: {
        base_version: payload.baseVersion,
        suggested_content: payload.suggestedContent,
        suggested_title: payload.suggestedTitle,
      },
      method: "POST",
    },
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

export function useCreateSuggestedEditMutation() {
  return useMutation({
    mutationFn: createSuggestedEdit,
  });
}
