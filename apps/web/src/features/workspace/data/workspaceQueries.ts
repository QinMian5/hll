// abstract: TanStack Query adapters for current-user Workspace proposal tracking.
// out_of_scope: Workspace page rendering, proposal review actions, and role assignment UI.

import type { components } from "@knowledge/contracts/generated/types";
import { useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

export type CardProposalResponse =
  components["schemas"]["CardProposalResponse"];
export type CardProposalListResponse =
  components["schemas"]["CardProposalListResponse"];

const workspaceQueryKeys = {
  myProposals: ["workspace", "my-proposals"] as const,
};

async function fetchMyProposals(): Promise<CardProposalListResponse> {
  return await fetchWebApiJson<CardProposalListResponse>(
    "/web-api/card-proposals/my",
  );
}

export function useMyProposalsQuery(enabled: boolean) {
  return useQuery({
    enabled,
    queryFn: fetchMyProposals,
    queryKey: workspaceQueryKeys.myProposals,
  });
}
