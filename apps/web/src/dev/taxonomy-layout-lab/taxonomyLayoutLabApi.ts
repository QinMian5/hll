// abstract: HTTP client helpers for the local taxonomy layout tuning server.
// out_of_scope: Production web API transport and React state orchestration.

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import type { TaxonomyLayoutLabParams } from "./taxonomyLayoutLabParams";

export const DEFAULT_LAYOUT_LAB_API_BASE_URL = "http://127.0.0.1:8765";

export interface LayoutLabFixtureSummary {
  readonly name: string;
  readonly node_count: number;
  readonly edge_count: number;
}

export interface LayoutLabApiOptions {
  readonly apiBaseUrl: string;
  readonly signal?: AbortSignal;
}

export async function fetchLayoutLabFixtures(
  options: LayoutLabApiOptions,
): Promise<LayoutLabFixtureSummary[]> {
  return fetchLayoutLabJson<LayoutLabFixtureSummary[]>(
    `${normalizeBaseUrl(options.apiBaseUrl)}/fixtures`,
    { signal: options.signal },
  );
}

export async function fetchLayoutLabDefaultParams(
  options: LayoutLabApiOptions,
): Promise<TaxonomyLayoutLabParams> {
  return fetchLayoutLabJson<TaxonomyLayoutLabParams>(
    `${normalizeBaseUrl(options.apiBaseUrl)}/params/default`,
    { signal: options.signal },
  );
}

export async function solveLayoutLab(options: {
  readonly apiBaseUrl: string;
  readonly fixtureName: string;
  readonly params: Partial<TaxonomyLayoutLabParams>;
  readonly signal?: AbortSignal;
}): Promise<TaxonomyCardScopeLayoutSliceResponse> {
  return fetchLayoutLabJson<TaxonomyCardScopeLayoutSliceResponse>(
    `${normalizeBaseUrl(options.apiBaseUrl)}/solve`,
    {
      body: JSON.stringify({
        fixtureName: options.fixtureName,
        params: options.params,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: options.signal,
    },
  );
}

async function fetchLayoutLabJson<T>(
  url: string,
  init: RequestInit,
): Promise<T> {
  const response = await fetch(url, init);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(extractErrorMessage(data));
  }

  return data as T;
}

function extractErrorMessage(data: unknown): string {
  if (
    typeof data === "object" &&
    data !== null &&
    "detail" in data &&
    typeof data.detail === "string"
  ) {
    return data.detail;
  }

  return "Taxonomy layout lab request failed.";
}

function normalizeBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/+$/, "");
}
