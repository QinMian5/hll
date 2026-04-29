// abstract: Typed Docker-internal FastAPI client for the web BFF.
// out_of_scope: Browser fetch adapters and feature route validation.

import type { components, paths } from "@knowledge/contracts/generated/types";
import createClient from "openapi-fetch";

import type { WebServerConfig } from "../config.js";
import { InternalApiError } from "./errors.js";

export type SearchResponse = components["schemas"]["SearchResponse"];
export type TaxonomyRootViewResponse =
  components["schemas"]["TaxonomyRootViewResponse"];
export type SuggestedEditCreateRequest =
  components["schemas"]["SuggestedEditCreateRequest"];
export type SuggestedEditCreateResponse =
  components["schemas"]["SuggestedEditCreateResponse"];
export type TaxonomyNodeViewResponse =
  components["schemas"]["TaxonomyNodeViewResponse"];
export type TaxonomyLeafNodeDetailsResponse =
  components["schemas"]["TaxonomyLeafNodeDetailsResponse"];
export type TaxonomyLeafNodeTitlesResponse =
  components["schemas"]["TaxonomyLeafNodeTitlesResponse"];

export interface InternalApiClient {
  readonly createSuggestedEdit: (
    nodeId: number,
    payload: SuggestedEditCreateRequest,
    suggestedByUserId: string,
  ) => Promise<SuggestedEditCreateResponse>;
  readonly getTaxonomyLeafNodeDetails: (
    leafId: number,
    nodeIds: readonly number[],
  ) => Promise<TaxonomyLeafNodeDetailsResponse>;
  readonly getTaxonomyLeafNodeTitles: (
    leafId: number,
    nodeIds: readonly number[],
  ) => Promise<TaxonomyLeafNodeTitlesResponse>;
  readonly getTaxonomyNode: (
    nodeId: number,
  ) => Promise<TaxonomyNodeViewResponse>;
  readonly getTaxonomyRoot: () => Promise<TaxonomyRootViewResponse>;
  readonly search: (query: string) => Promise<SearchResponse>;
}

interface InternalApiResult<TData> {
  readonly data?: TData;
  readonly response: Response;
}

function unwrapInternalApiData<TData>(result: InternalApiResult<TData>): TData {
  if (!result.response.ok) {
    throw new InternalApiError(
      result.response.status,
      `Internal API request failed with status ${result.response.status}.`,
    );
  }

  if (result.data === undefined) {
    throw new InternalApiError(
      502,
      "Internal API response did not include a payload.",
    );
  }

  return result.data;
}

export function createInternalApiClient(
  config: WebServerConfig,
): InternalApiClient {
  const client = createClient<paths>({
    baseUrl: config.internalApiBaseUrl,
  });

  return {
    createSuggestedEdit: async (nodeId, payload, suggestedByUserId) => {
      const result = await client.POST(
        "/api/v1/cards/{node_id}/suggested-edits",
        {
          body: payload,
          params: {
            header: {
              "X-Knowledge-Suggested-By-User-Id": suggestedByUserId,
            },
            path: { node_id: nodeId },
          },
        },
      );

      return unwrapInternalApiData<SuggestedEditCreateResponse>(result);
    },
    getTaxonomyLeafNodeDetails: async (leafId, nodeIds) => {
      const result = await client.POST(
        "/api/v1/taxonomy/view/leaves/{node_id}/details",
        {
          body: { node_ids: [...nodeIds] },
          params: { path: { node_id: leafId } },
        },
      );

      return unwrapInternalApiData<TaxonomyLeafNodeDetailsResponse>(result);
    },
    getTaxonomyLeafNodeTitles: async (leafId, nodeIds) => {
      const result = await client.POST(
        "/api/v1/taxonomy/view/leaves/{node_id}/titles",
        {
          body: { node_ids: [...nodeIds] },
          params: { path: { node_id: leafId } },
        },
      );

      return unwrapInternalApiData<TaxonomyLeafNodeTitlesResponse>(result);
    },
    getTaxonomyNode: async (nodeId) => {
      const result = await client.GET("/api/v1/taxonomy/view/nodes/{node_id}", {
        params: { path: { node_id: nodeId } },
      });

      return unwrapInternalApiData<unknown>(result) as TaxonomyNodeViewResponse;
    },
    getTaxonomyRoot: async () => {
      const result = await client.GET("/api/v1/taxonomy/view/root");

      return unwrapInternalApiData<TaxonomyRootViewResponse>(result);
    },
    search: async (query) => {
      const result = await client.GET("/api/v1/search", {
        params: { query: { query } },
      });

      return unwrapInternalApiData<SearchResponse>(result);
    },
  };
}
