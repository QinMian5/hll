// abstract: TanStack Query adapters for taxonomy root/node drill-down view contracts.
// out_of_scope: React Flow rendering and interaction-state orchestration.

import type { components, paths } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { getContractsClient } from "../../../shared/api/contractsClient";

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
export type LeafDetailPathExists = Assert<
  "/taxonomy/view/leaves/{node_id}/details" extends keyof paths ? true : false
>;
export type TaxonomyLeafContractChecks = [
  LeafSkeletonOmitsTitle,
  LeafSkeletonOmitsContent,
  LeafDetailPathExists,
];

class TaxonomyViewRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "TaxonomyViewRequestError";
    this.status = status;
  }
}

const taxonomyViewQueryKeys = {
  leafDetails: (leafId: number, nodeIds: readonly number[]) =>
    ["taxonomy-view", "leaf-details", leafId, ...nodeIds] as const,
  node: (nodeId: number) => ["taxonomy-view", "node", nodeId] as const,
  root: ["taxonomy-view", "root"] as const,
};

async function fetchTaxonomyRootView(): Promise<TaxonomyRootView> {
  const result = await getContractsClient().GET("/taxonomy/view/root");

  if (!result.response.ok) {
    throw new TaxonomyViewRequestError(
      `Taxonomy root view request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error("Taxonomy root view response did not include a payload.");
  }

  return result.data;
}

async function fetchTaxonomyNodeView(
  nodeId: number,
): Promise<TaxonomyNodeView> {
  const result = await getContractsClient().GET(
    "/taxonomy/view/nodes/{node_id}",
    {
      params: { path: { node_id: nodeId } },
    },
  );

  if (!result.response.ok) {
    throw new TaxonomyViewRequestError(
      `Taxonomy node view request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error("Taxonomy node view response did not include a payload.");
  }

  return result.data;
}

function normalizeLeafDetailNodeIds(nodeIds: readonly number[]) {
  return [...nodeIds].sort((left, right) => left - right);
}

async function fetchTaxonomyLeafNodeDetails(
  leafId: number,
  nodeIds: readonly number[],
): Promise<TaxonomyLeafNodeDetailsResponse> {
  const normalizedNodeIds = normalizeLeafDetailNodeIds(nodeIds);
  const result = await getContractsClient().POST(
    "/taxonomy/view/leaves/{node_id}/details",
    {
      body: { node_ids: normalizedNodeIds },
      params: { path: { node_id: leafId } },
    },
  );

  if (!result.response.ok) {
    throw new TaxonomyViewRequestError(
      `Taxonomy leaf detail request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error("Taxonomy leaf detail response did not include a payload.");
  }

  return result.data;
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
