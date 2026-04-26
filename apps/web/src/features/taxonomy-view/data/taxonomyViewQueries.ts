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
export type TaxonomyLeafSkeletonNode =
  TaxonomyLeafViewContract["nodes"][number];
export type TaxonomyLeafNodeDetailsRequest =
  components["schemas"]["TaxonomyLeafNodeDetailsRequest"];
export type TaxonomyLeafNodeDetailsResponse =
  components["schemas"]["TaxonomyLeafNodeDetailsResponse"];
export type TaxonomyLeafNodeDetailRecord =
  TaxonomyLeafNodeDetailsResponse["nodes"][number];
export type TaxonomyRootView = TaxonomyRootViewContract;
export type TaxonomyLeafView = TaxonomyLeafViewContract;
export type TaxonomyNodeView = TaxonomyNodeViewContract;
type TaxonomyLeafEdgeTuple = TaxonomyLeafViewContract["edges"][number];

type Assert<T extends true> = T;
type HasProperty<
  T,
  PropertyName extends PropertyKey,
> = PropertyName extends keyof T ? true : false;

export type LeafSkeletonOmitsTitle = Assert<
  HasProperty<TaxonomyLeafSkeletonNode, "title"> extends false ? true : false
>;
export type LeafSkeletonOmitsContent = Assert<
  HasProperty<TaxonomyLeafSkeletonNode, "content"> extends false ? true : false
>;
export type LeafEdgeTupleShape = Assert<
  TaxonomyLeafEdgeTuple extends readonly [number, number, number] ? true : false
>;
export type TaxonomyLeafContractChecks = [
  LeafSkeletonOmitsTitle,
  LeafSkeletonOmitsContent,
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

  const rawEdges =
    typeof data === "object" && data !== null && "edges" in data
      ? (data as { readonly edges: readonly unknown[] }).edges
      : [];

  return {
    ...nodeView,
    edges: rawEdges.map(normalizeLeafEdgeTuple),
  };
}

const taxonomyViewQueryKeys = {
  leafDetails: (leafId: number, nodeIds: readonly number[]) =>
    ["taxonomy-view", "leaf-details", leafId, ...nodeIds] as const,
  node: (nodeId: number) => ["taxonomy-view", "node", nodeId] as const,
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
