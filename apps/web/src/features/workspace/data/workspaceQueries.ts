// abstract: TanStack Query adapters for current-user Workspace proposal tracking and withdrawal.
// out_of_scope: Workspace page rendering, reviewer queue actions, and role assignment UI.

import type { components } from "@knowledge/contracts/generated/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

async function withdrawCardProposal(
  proposalId: number,
): Promise<CardProposalResponse> {
  return await fetchWebApiJson<CardProposalResponse>(
    `/web-api/card-proposals/${proposalId}/withdraw`,
    { method: "POST" },
  );
}

export function useMyProposalsQuery(enabled: boolean) {
  return useQuery({
    enabled,
    queryFn: fetchMyProposals,
    queryKey: workspaceQueryKeys.myProposals,
  });
}

export function useWithdrawCardProposalMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: withdrawCardProposal,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceQueryKeys.myProposals,
      });
    },
  });
}
