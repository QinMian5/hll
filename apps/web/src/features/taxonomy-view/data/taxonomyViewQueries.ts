// abstract: TanStack Query adapters for taxonomy root/node drill-down view contracts.
// out_of_scope: React Flow rendering and interaction-state orchestration.

import type { components } from "@knowledge/contracts/generated/types";
import { queryOptions, useQuery } from "@tanstack/react-query";

import { getContractsClient } from "../../../shared/api/contractsClient";

export type TaxonomyRootView =
  components["schemas"]["TaxonomyRootViewResponse"];
export type TaxonomyNodeView =
  components["schemas"]["TaxonomyNodeViewResponse"];

class TaxonomyViewRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "TaxonomyViewRequestError";
    this.status = status;
  }
}

const taxonomyViewQueryKeys = {
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
