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
export type TaxonomyLeafLayoutSliceResponse =
  components["schemas"]["TaxonomyLeafLayoutSliceResponse"];
export type TaxonomyLeafNodeTitlesResponse =
  components["schemas"]["TaxonomyLeafNodeTitlesResponse"];

export interface TaxonomyLeafLayoutBounds {
  readonly min_x: number;
  readonly min_y: number;
  readonly max_x: number;
  readonly max_y: number;
}

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
  readonly getTaxonomyLeafLayoutSlice: (
    leafId: number,
    bounds: TaxonomyLeafLayoutBounds,
  ) => Promise<TaxonomyLeafLayoutSliceResponse>;
  readonly getTaxonomyLeafNodeTitles: (
    leafId: number,
    nodeIds: readonly number[],
  ) => Promise<TaxonomyLeafNodeTitlesResponse>;
  readonly getTaxonomyNode: (
    nodeId: number,
  ) => Promise<TaxonomyNodeViewResponse>;
  readonly getTaxonomyNodeByPath: (
    routePath: string,
  ) => Promise<TaxonomyNodeViewResponse>;
  readonly getTaxonomyRoot: () => Promise<TaxonomyRootViewResponse>;
  readonly search: (query: string) => Promise<SearchResponse>;
}

interface InternalApiResult<TData> {
  readonly data?: TData;
  readonly error?: unknown;
  readonly response: Response;
}

interface InternalApiErrorPayload {
  readonly error?: {
    readonly code?: unknown;
    readonly message?: unknown;
  };
}

function parseInternalApiErrorPayload(payload: unknown):
  | {
      readonly code: string;
      readonly message: string;
    }
  | undefined {
  const error =
    typeof payload === "object" && payload !== null && "error" in payload
      ? (payload as InternalApiErrorPayload).error
      : undefined;

  if (typeof error?.code !== "string" || typeof error.message !== "string") {
    return undefined;
  }

  return {
    code: error.code,
    message: error.message,
  };
}

function unwrapInternalApiData<TData>(result: InternalApiResult<TData>): TData {
  if (!result.response.ok) {
    const payload = parseInternalApiErrorPayload(result.error ?? result.data);
    const shouldExposePayload =
      payload !== undefined &&
      ((result.response.status >= 400 && result.response.status < 500) ||
        (result.response.status === 503 &&
          payload.code === "layout_not_ready"));

    throw new InternalApiError(
      result.response.status,
      `Internal API request failed with status ${result.response.status}.`,
      shouldExposePayload
        ? {
            clientMessage: payload.message,
            code: payload.code,
            retryAfterSeconds: parseRetryAfterSeconds(result.response),
          }
        : undefined,
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

function parseRetryAfterSeconds(response: Response): number | undefined {
  const rawValue = response.headers.get("Retry-After");
  if (rawValue === null) {
    return undefined;
  }

  const parsed = Number(rawValue);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return undefined;
  }
  return parsed;
}

function encodeRoutePath(routePath: string): string {
  return routePath.split("/").map(encodeURIComponent).join("/");
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
    getTaxonomyLeafLayoutSlice: async (leafId, bounds) => {
      const result = await client.GET(
        "/api/v1/taxonomy/view/leaves/{node_id}/layout",
        {
          params: {
            path: { node_id: leafId },
            query: bounds,
          },
        },
      );

      return unwrapInternalApiData<unknown>(
        result,
      ) as TaxonomyLeafLayoutSliceResponse;
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
    getTaxonomyNodeByPath: async (routePath) => {
      const response = await fetch(
        `${config.internalApiBaseUrl}/api/v1/taxonomy/view/path/${encodeRoutePath(routePath)}`,
      );
      const data = response.headers
        .get("content-type")
        ?.includes("application/json")
        ? ((await response.json()) as unknown)
        : undefined;

      return unwrapInternalApiData<unknown>({
        data,
        response,
      }) as TaxonomyNodeViewResponse;
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
