// abstract: TanStack Query adapters for taxonomy root/node drill-down view contracts.
// out_of_scope: Frontend renderer selection, viewport ownership, and interaction-state orchestration.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

type TaxonomyRootViewContract =
  components["schemas"]["TaxonomyRootViewResponse"];
type TaxonomyNodeViewContract =
  components["schemas"]["TaxonomyNodeViewResponse"];
export type TaxonomyCardScopeViewContract = Extract<
  TaxonomyNodeViewContract,
  { readonly node_kind: "card_scope" }
>;
export type TaxonomyCardScopeNodeDetailsRequest =
  components["schemas"]["TaxonomyCardScopeNodeDetailsRequest"];
export type TaxonomyCardScopeNodeDetailsResponse =
  components["schemas"]["TaxonomyCardScopeNodeDetailsResponse"];
export type TaxonomyCardScopeNodeDetailRecord =
  TaxonomyCardScopeNodeDetailsResponse["nodes"][number];
export type TaxonomyCardScopeLayoutSliceResponse =
  components["schemas"]["TaxonomyCardScopeLayoutSliceResponse"];
export type TaxonomyCardScopeLayoutNode =
  TaxonomyCardScopeLayoutSliceResponse["nodes"][number];
export type TaxonomyCardScopeNodeTitlesRequest =
  components["schemas"]["TaxonomyCardScopeNodeTitlesRequest"];
export type TaxonomyCardScopeNodeTitlesResponse =
  components["schemas"]["TaxonomyCardScopeNodeTitlesResponse"];
export type TaxonomyCardScopeNodeTitleRecord =
  TaxonomyCardScopeNodeTitlesResponse["nodes"][number];
export type TaxonomyRootView = TaxonomyRootViewContract;
export type TaxonomyCardScopeView = TaxonomyCardScopeViewContract;
export type TaxonomyNodeView = TaxonomyNodeViewContract;
type TaxonomyCardScopeEdgeTuple =
  TaxonomyCardScopeLayoutSliceResponse["edges"][number];
const CARD_SCOPE_LAYOUT_SLICE_STALE_TIME_MS = 5 * 60 * 1000;
const CARD_SCOPE_LAYOUT_SLICE_GC_TIME_MS = 30 * 60 * 1000;

export interface TaxonomyCardScopeLayoutBounds {
  readonly min_x: number;
  readonly min_y: number;
  readonly max_x: number;
  readonly max_y: number;
}

export interface TaxonomyCardScopeLayoutIdentity {
  readonly generatedAt: string;
  readonly layoutVersion: string;
}

type Assert<T extends true> = T;
type HasProperty<
  T,
  PropertyName extends PropertyKey,
> = PropertyName extends keyof T ? true : false;

export type CardScopeLayoutNodeOmitsTitle = Assert<
  HasProperty<TaxonomyCardScopeLayoutNode, "title"> extends false ? true : false
>;
export type CardScopeLayoutNodeOmitsContent = Assert<
  HasProperty<TaxonomyCardScopeLayoutNode, "content"> extends false
    ? true
    : false
>;
export type CardScopeEdgeTupleShape = Assert<
  TaxonomyCardScopeEdgeTuple extends readonly [number, number, number]
    ? true
    : false
>;
export type TaxonomyCardScopeContractChecks = [
  CardScopeLayoutNodeOmitsTitle,
  CardScopeLayoutNodeOmitsContent,
  CardScopeEdgeTupleShape,
];

function normalizeCardScopeEdgeTuple(
  edge: unknown,
): TaxonomyCardScopeEdgeTuple {
  if (!Array.isArray(edge) || edge.length !== 3) {
    throw new Error(
      "Taxonomy card-scope edge payload must contain 3 numeric values.",
    );
  }

  const [sourceNodeId, targetNodeId, strength] = edge;

  if (
    typeof sourceNodeId !== "number" ||
    typeof targetNodeId !== "number" ||
    typeof strength !== "number"
  ) {
    throw new Error(
      "Taxonomy card-scope edge payload must contain 3 numeric values.",
    );
  }

  return [sourceNodeId, targetNodeId, strength];
}

function normalizeTaxonomyNodeViewPayload(data: unknown): TaxonomyNodeView {
  const nodeView = data as TaxonomyNodeViewContract;

  if (
    typeof nodeView !== "object" ||
    nodeView === null ||
    !("node_kind" in nodeView)
  ) {
    throw new Error("Taxonomy node view response was not a valid payload.");
  }

  if (nodeView.node_kind !== "card_scope") {
    return nodeView;
  }

  return nodeView;
}

function normalizeTaxonomyCardScopeLayoutSlicePayload(
  data: unknown,
): TaxonomyCardScopeLayoutSliceResponse {
  const layoutSlice = data as TaxonomyCardScopeLayoutSliceResponse;

  if (
    typeof layoutSlice !== "object" ||
    layoutSlice === null ||
    !("edges" in layoutSlice)
  ) {
    throw new Error(
      "Taxonomy card-scope layout response was not a valid payload.",
    );
  }

  const rawEdges =
    typeof data === "object" && data !== null && "edges" in data
      ? (data as { readonly edges: readonly unknown[] }).edges
      : [];

  return {
    ...layoutSlice,
    edges: rawEdges.map(normalizeCardScopeEdgeTuple),
  };
}

const taxonomyViewQueryKeys = {
  cardScopeDetails: (routePath: string, nodeIds: readonly number[]) =>
    ["taxonomy-view", "card-scope-details", routePath, ...nodeIds] as const,
  cardScopeLayoutSlice: (
    routePath: string,
    bounds: TaxonomyCardScopeLayoutBounds,
    layoutIdentity: TaxonomyCardScopeLayoutIdentity,
  ) =>
    [
      "taxonomy-view",
      "card-scope-layout",
      routePath,
      layoutIdentity.layoutVersion,
      layoutIdentity.generatedAt,
      bounds.min_x,
      bounds.min_y,
      bounds.max_x,
      bounds.max_y,
    ] as const,
  cardScopeTitles: (routePath: string, nodeIds: readonly number[]) =>
    ["taxonomy-view", "card-scope-titles", routePath, ...nodeIds] as const,
  node: (nodeId: number) => ["taxonomy-view", "node", nodeId] as const,
  path: (routePath: string) => ["taxonomy-view", "path", routePath] as const,
  root: ["taxonomy-view", "root"] as const,
};

async function fetchTaxonomyRootView(): Promise<TaxonomyRootView> {
  return await fetchWebApiJson<TaxonomyRootView>("/web-api/taxonomy/view/root");
}

async function fetchTaxonomyNodeView(
  nodeId: number,
): Promise<TaxonomyNodeView> {
  const result = await fetchWebApiJson<unknown>(
    `/web-api/taxonomy/view/nodes/${nodeId}`,
  );

  return normalizeTaxonomyNodeViewPayload(result);
}

function encodeRoutePath(routePath: string): string {
  return routePath.split("/").map(encodeURIComponent).join("/");
}

async function fetchTaxonomyNodeViewByPath(
  routePath: string,
): Promise<TaxonomyNodeView> {
  const result = await fetchWebApiJson<unknown>(
    `/web-api/taxonomy/view/path/${encodeRoutePath(routePath)}`,
  );

  return normalizeTaxonomyNodeViewPayload(result);
}

function normalizeCardScopeDetailNodeIds(nodeIds: readonly number[]) {
  return [...nodeIds].sort((left, right) => left - right);
}

async function fetchTaxonomyCardScopeNodeDetails(
  routePath: string,
  nodeIds: readonly number[],
): Promise<TaxonomyCardScopeNodeDetailsResponse> {
  const normalizedNodeIds = normalizeCardScopeDetailNodeIds(nodeIds);
  return await fetchWebApiJson<TaxonomyCardScopeNodeDetailsResponse>(
    "/web-api/taxonomy/view/card-scopes/details",
    {
      body: { node_ids: normalizedNodeIds, route_path: routePath },
      method: "POST",
    },
  );
}

async function fetchTaxonomyCardScopeLayoutSlice(
  routePath: string,
  bounds: TaxonomyCardScopeLayoutBounds,
): Promise<TaxonomyCardScopeLayoutSliceResponse> {
  const searchParams = new URLSearchParams({
    max_x: String(bounds.max_x),
    max_y: String(bounds.max_y),
    min_x: String(bounds.min_x),
    min_y: String(bounds.min_y),
    route_path: routePath,
  });

  const result = await fetchWebApiJson<unknown>(
    `/web-api/taxonomy/view/card-scopes/layout?${searchParams.toString()}`,
  );

  return normalizeTaxonomyCardScopeLayoutSlicePayload(result);
}

async function fetchTaxonomyCardScopeNodeTitles(
  routePath: string,
  nodeIds: readonly number[],
): Promise<TaxonomyCardScopeNodeTitlesResponse> {
  const normalizedNodeIds = normalizeCardScopeDetailNodeIds(nodeIds);
  return await fetchWebApiJson<TaxonomyCardScopeNodeTitlesResponse>(
    "/web-api/taxonomy/view/card-scopes/titles",
    {
      body: { node_ids: normalizedNodeIds, route_path: routePath },
      method: "POST",
    },
  );
}

export function taxonomyRootViewQueryOptions() {
  return queryOptions({
    queryFn: fetchTaxonomyRootView,
    queryKey: taxonomyViewQueryKeys.root,
  });
}

export function taxonomyNodeViewQueryOptions(nodeId: number) {
  return queryOptions({
    queryFn: () => fetchTaxonomyNodeView(nodeId),
    queryKey: taxonomyViewQueryKeys.node(nodeId),
  });
}

export function taxonomyNodeViewByPathQueryOptions(routePath: string) {
  return queryOptions({
    queryFn: () => fetchTaxonomyNodeViewByPath(routePath),
    queryKey: taxonomyViewQueryKeys.path(routePath),
  });
}

export function taxonomyCardScopeNodeDetailsQueryOptions(
  routePath: string,
  nodeIds: readonly number[],
) {
  const normalizedNodeIds = normalizeCardScopeDetailNodeIds(nodeIds);

  return queryOptions({
    queryFn: () =>
      fetchTaxonomyCardScopeNodeDetails(routePath, normalizedNodeIds),
    queryKey: taxonomyViewQueryKeys.cardScopeDetails(
      routePath,
      normalizedNodeIds,
    ),
  });
}

export function taxonomyCardScopeLayoutSliceQueryOptions(
  routePath: string,
  bounds: TaxonomyCardScopeLayoutBounds,
  layoutIdentity: TaxonomyCardScopeLayoutIdentity,
) {
  return queryOptions({
    gcTime: CARD_SCOPE_LAYOUT_SLICE_GC_TIME_MS,
    placeholderData: (previousData) => previousData,
    queryFn: () => fetchTaxonomyCardScopeLayoutSlice(routePath, bounds),
    queryKey: taxonomyViewQueryKeys.cardScopeLayoutSlice(
      routePath,
      bounds,
      layoutIdentity,
    ),
    staleTime: CARD_SCOPE_LAYOUT_SLICE_STALE_TIME_MS,
  });
}

export function taxonomyCardScopeNodeTitlesQueryOptions(
  routePath: string,
  nodeIds: readonly number[],
) {
  const normalizedNodeIds = normalizeCardScopeDetailNodeIds(nodeIds);

  return queryOptions({
    queryFn: () =>
      fetchTaxonomyCardScopeNodeTitles(routePath, normalizedNodeIds),
    queryKey: taxonomyViewQueryKeys.cardScopeTitles(
      routePath,
      normalizedNodeIds,
    ),
  });
}

export function useTaxonomyRootViewQuery(options: {
  readonly enabled?: boolean;
}) {
  return useQuery({
    ...taxonomyRootViewQueryOptions(),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyNodeViewQuery(
  nodeId: number,
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyNodeViewQueryOptions(nodeId),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyNodeViewByPathQuery(
  routePath: string,
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyNodeViewByPathQueryOptions(routePath),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyCardScopeNodeDetailsQuery(
  routePath: string,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyCardScopeNodeDetailsQueryOptions(routePath, nodeIds),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyCardScopeLayoutSliceQuery(
  routePath: string,
  bounds: TaxonomyCardScopeLayoutBounds,
  layoutIdentity: TaxonomyCardScopeLayoutIdentity,
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyCardScopeLayoutSliceQueryOptions(
      routePath,
      bounds,
      layoutIdentity,
    ),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyCardScopeNodeTitlesQuery(
  routePath: string,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyCardScopeNodeTitlesQueryOptions(routePath, nodeIds),
    enabled: options.enabled ?? true,
  });
}

export type TaxonomyLeafView = TaxonomyCardScopeView;
export type TaxonomyLeafLayoutBounds = TaxonomyCardScopeLayoutBounds;
export type TaxonomyLeafLayoutIdentity = TaxonomyCardScopeLayoutIdentity;
export type TaxonomyLeafLayoutSliceResponse =
  TaxonomyCardScopeLayoutSliceResponse;
export type TaxonomyLeafLayoutNode = TaxonomyCardScopeLayoutNode;
export type TaxonomyLeafNodeDetailsRequest =
  TaxonomyCardScopeNodeDetailsRequest;
export type TaxonomyLeafNodeDetailsResponse =
  TaxonomyCardScopeNodeDetailsResponse;
export type TaxonomyLeafNodeDetailRecord = TaxonomyCardScopeNodeDetailRecord;
export type TaxonomyLeafNodeTitlesRequest = TaxonomyCardScopeNodeTitlesRequest;
export type TaxonomyLeafNodeTitlesResponse =
  TaxonomyCardScopeNodeTitlesResponse;
export type TaxonomyLeafNodeTitleRecord = TaxonomyCardScopeNodeTitleRecord;

export function taxonomyLeafNodeDetailsQueryOptions(
  routePath: number | string,
  nodeIds: readonly number[],
) {
  return taxonomyCardScopeNodeDetailsQueryOptions(String(routePath), nodeIds);
}

export function taxonomyLeafLayoutSliceQueryOptions(
  routePath: number | string,
  bounds: TaxonomyCardScopeLayoutBounds,
  layoutIdentity: TaxonomyCardScopeLayoutIdentity,
) {
  return taxonomyCardScopeLayoutSliceQueryOptions(
    String(routePath),
    bounds,
    layoutIdentity,
  );
}

export function taxonomyLeafNodeTitlesQueryOptions(
  routePath: number | string,
  nodeIds: readonly number[],
) {
  return taxonomyCardScopeNodeTitlesQueryOptions(String(routePath), nodeIds);
}

export function useTaxonomyLeafNodeDetailsQuery(
  routePath: number | string,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useTaxonomyCardScopeNodeDetailsQuery(
    String(routePath),
    nodeIds,
    options,
  );
}

export function useTaxonomyLeafLayoutSliceQuery(
  routePath: number | string,
  bounds: TaxonomyCardScopeLayoutBounds,
  layoutIdentity: TaxonomyCardScopeLayoutIdentity,
  options: { readonly enabled?: boolean },
) {
  return useTaxonomyCardScopeLayoutSliceQuery(
    String(routePath),
    bounds,
    layoutIdentity,
    options,
  );
}

export function useTaxonomyLeafNodeTitlesQuery(
  routePath: number | string,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useTaxonomyCardScopeNodeTitlesQuery(
    String(routePath),
    nodeIds,
    options,
  );
}
