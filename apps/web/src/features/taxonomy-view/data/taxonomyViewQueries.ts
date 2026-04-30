// abstract: TanStack Query adapters for taxonomy root/node drill-down view contracts.
// out_of_scope: Frontend renderer selection, viewport ownership, and interaction-state orchestration.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

type TaxonomyRootViewContract =
  components["schemas"]["TaxonomyRootViewResponse"];
type TaxonomyNodeViewContract =
  components["schemas"]["TaxonomyNodeViewResponse"];
export type TaxonomyLeafViewContract = Extract<
  TaxonomyNodeViewContract,
  { readonly node_kind: "leaf" }
>;
export type TaxonomyLeafNodeDetailsRequest =
  components["schemas"]["TaxonomyLeafNodeDetailsRequest"];
export type TaxonomyLeafNodeDetailsResponse =
  components["schemas"]["TaxonomyLeafNodeDetailsResponse"];
export type TaxonomyLeafNodeDetailRecord =
  TaxonomyLeafNodeDetailsResponse["nodes"][number];
export type TaxonomyLeafLayoutSliceResponse =
  components["schemas"]["TaxonomyLeafLayoutSliceResponse"];
export type TaxonomyLeafLayoutNode =
  TaxonomyLeafLayoutSliceResponse["nodes"][number];
export type TaxonomyLeafNodeTitlesRequest =
  components["schemas"]["TaxonomyLeafNodeTitlesRequest"];
export type TaxonomyLeafNodeTitlesResponse =
  components["schemas"]["TaxonomyLeafNodeTitlesResponse"];
export type TaxonomyLeafNodeTitleRecord =
  TaxonomyLeafNodeTitlesResponse["nodes"][number];
export type TaxonomyRootView = TaxonomyRootViewContract;
export type TaxonomyLeafView = TaxonomyLeafViewContract;
export type TaxonomyNodeView = TaxonomyNodeViewContract;
type TaxonomyLeafEdgeTuple = TaxonomyLeafLayoutSliceResponse["edges"][number];
const LEAF_LAYOUT_SLICE_STALE_TIME_MS = 5 * 60 * 1000;
const LEAF_LAYOUT_SLICE_GC_TIME_MS = 30 * 60 * 1000;

export interface TaxonomyLeafLayoutBounds {
  readonly min_x: number;
  readonly min_y: number;
  readonly max_x: number;
  readonly max_y: number;
}

export interface TaxonomyLeafLayoutIdentity {
  readonly generatedAt: string;
  readonly layoutVersion: string;
}

type Assert<T extends true> = T;
type HasProperty<
  T,
  PropertyName extends PropertyKey,
> = PropertyName extends keyof T ? true : false;

export type LeafLayoutNodeOmitsTitle = Assert<
  HasProperty<TaxonomyLeafLayoutNode, "title"> extends false ? true : false
>;
export type LeafLayoutNodeOmitsContent = Assert<
  HasProperty<TaxonomyLeafLayoutNode, "content"> extends false ? true : false
>;
export type LeafEdgeTupleShape = Assert<
  TaxonomyLeafEdgeTuple extends readonly [number, number, number] ? true : false
>;
export type TaxonomyLeafContractChecks = [
  LeafLayoutNodeOmitsTitle,
  LeafLayoutNodeOmitsContent,
  LeafEdgeTupleShape,
];

function normalizeLeafEdgeTuple(edge: unknown): TaxonomyLeafEdgeTuple {
  if (!Array.isArray(edge) || edge.length !== 3) {
    throw new Error(
      "Taxonomy leaf edge payload must contain 3 numeric values.",
    );
  }

  const [sourceNodeId, targetNodeId, strength] = edge;

  if (
    typeof sourceNodeId !== "number" ||
    typeof targetNodeId !== "number" ||
    typeof strength !== "number"
  ) {
    throw new Error(
      "Taxonomy leaf edge payload must contain 3 numeric values.",
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

  if (nodeView.node_kind !== "leaf") {
    return nodeView;
  }

  return nodeView;
}

function normalizeTaxonomyLeafLayoutSlicePayload(
  data: unknown,
): TaxonomyLeafLayoutSliceResponse {
  const layoutSlice = data as TaxonomyLeafLayoutSliceResponse;

  if (
    typeof layoutSlice !== "object" ||
    layoutSlice === null ||
    !("edges" in layoutSlice)
  ) {
    throw new Error("Taxonomy leaf layout response was not a valid payload.");
  }

  const rawEdges =
    typeof data === "object" && data !== null && "edges" in data
      ? (data as { readonly edges: readonly unknown[] }).edges
      : [];

  return {
    ...layoutSlice,
    edges: rawEdges.map(normalizeLeafEdgeTuple),
  };
}

const taxonomyViewQueryKeys = {
  leafDetails: (leafId: number, nodeIds: readonly number[]) =>
    ["taxonomy-view", "leaf-details", leafId, ...nodeIds] as const,
  leafLayoutSlice: (
    leafId: number,
    bounds: TaxonomyLeafLayoutBounds,
    layoutIdentity: TaxonomyLeafLayoutIdentity,
  ) =>
    [
      "taxonomy-view",
      "leaf-layout",
      leafId,
      layoutIdentity.layoutVersion,
      layoutIdentity.generatedAt,
      bounds.min_x,
      bounds.min_y,
      bounds.max_x,
      bounds.max_y,
    ] as const,
  leafTitles: (leafId: number, nodeIds: readonly number[]) =>
    ["taxonomy-view", "leaf-titles", leafId, ...nodeIds] as const,
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

function normalizeLeafDetailNodeIds(nodeIds: readonly number[]) {
  return [...nodeIds].sort((left, right) => left - right);
}

async function fetchTaxonomyLeafNodeDetails(
  leafId: number,
  nodeIds: readonly number[],
): Promise<TaxonomyLeafNodeDetailsResponse> {
  const normalizedNodeIds = normalizeLeafDetailNodeIds(nodeIds);
  return await fetchWebApiJson<TaxonomyLeafNodeDetailsResponse>(
    `/web-api/taxonomy/view/leaves/${leafId}/details`,
    {
      body: { node_ids: normalizedNodeIds },
      method: "POST",
    },
  );
}

async function fetchTaxonomyLeafLayoutSlice(
  leafId: number,
  bounds: TaxonomyLeafLayoutBounds,
): Promise<TaxonomyLeafLayoutSliceResponse> {
  const searchParams = new URLSearchParams({
    min_x: String(bounds.min_x),
    min_y: String(bounds.min_y),
    max_x: String(bounds.max_x),
    max_y: String(bounds.max_y),
  });

  const result = await fetchWebApiJson<unknown>(
    `/web-api/taxonomy/view/leaves/${leafId}/layout?${searchParams.toString()}`,
  );

  return normalizeTaxonomyLeafLayoutSlicePayload(result);
}

async function fetchTaxonomyLeafNodeTitles(
  leafId: number,
  nodeIds: readonly number[],
): Promise<TaxonomyLeafNodeTitlesResponse> {
  const normalizedNodeIds = normalizeLeafDetailNodeIds(nodeIds);
  return await fetchWebApiJson<TaxonomyLeafNodeTitlesResponse>(
    `/web-api/taxonomy/view/leaves/${leafId}/titles`,
    {
      body: { node_ids: normalizedNodeIds },
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

export function taxonomyLeafNodeDetailsQueryOptions(
  leafId: number,
  nodeIds: readonly number[],
) {
  const normalizedNodeIds = normalizeLeafDetailNodeIds(nodeIds);

  return queryOptions({
    queryFn: () => fetchTaxonomyLeafNodeDetails(leafId, normalizedNodeIds),
    queryKey: taxonomyViewQueryKeys.leafDetails(leafId, normalizedNodeIds),
  });
}

export function taxonomyLeafLayoutSliceQueryOptions(
  leafId: number,
  bounds: TaxonomyLeafLayoutBounds,
  layoutIdentity: TaxonomyLeafLayoutIdentity,
) {
  return queryOptions({
    gcTime: LEAF_LAYOUT_SLICE_GC_TIME_MS,
    placeholderData: (previousData) => previousData,
    queryFn: () => fetchTaxonomyLeafLayoutSlice(leafId, bounds),
    queryKey: taxonomyViewQueryKeys.leafLayoutSlice(
      leafId,
      bounds,
      layoutIdentity,
    ),
    staleTime: LEAF_LAYOUT_SLICE_STALE_TIME_MS,
  });
}

export function taxonomyLeafNodeTitlesQueryOptions(
  leafId: number,
  nodeIds: readonly number[],
) {
  const normalizedNodeIds = normalizeLeafDetailNodeIds(nodeIds);

  return queryOptions({
    queryFn: () => fetchTaxonomyLeafNodeTitles(leafId, normalizedNodeIds),
    queryKey: taxonomyViewQueryKeys.leafTitles(leafId, normalizedNodeIds),
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

export function useTaxonomyLeafNodeDetailsQuery(
  leafId: number,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyLeafNodeDetailsQueryOptions(leafId, nodeIds),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyLeafLayoutSliceQuery(
  leafId: number,
  bounds: TaxonomyLeafLayoutBounds,
  layoutIdentity: TaxonomyLeafLayoutIdentity,
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyLeafLayoutSliceQueryOptions(leafId, bounds, layoutIdentity),
    enabled: options.enabled ?? true,
  });
}

export function useTaxonomyLeafNodeTitlesQuery(
  leafId: number,
  nodeIds: readonly number[],
  options: { readonly enabled?: boolean },
) {
  return useQuery({
    ...taxonomyLeafNodeTitlesQueryOptions(leafId, nodeIds),
    enabled: options.enabled ?? true,
  });
}
