// abstract: TanStack Query adapters for Workspace card proposal workflows.
// out_of_scope: Workspace page rendering and reviewer role assignment UI.

import type { components } from "@knowledge/contracts/generated/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";

export type CardProposalResponse =
  components["schemas"]["CardProposalResponse"];
export type CardProposalListResponse =
  components["schemas"]["CardProposalListResponse"];
export type CardProposalReviewRequest =
  components["schemas"]["CardProposalReviewRequest"];

const workspaceQueryKeys = {
  myProposals: ["workspace", "my-proposals"] as const,
  reviewQueue: ["workspace", "review-queue"] as const,
};

async function fetchMyProposals(): Promise<CardProposalListResponse> {
  return await fetchWebApiJson<CardProposalListResponse>(
    "/web-api/card-proposals/my",
  );
}

async function fetchReviewQueue(): Promise<CardProposalListResponse> {
  return await fetchWebApiJson<CardProposalListResponse>(
    "/web-api/card-proposals/review-queue",
  );
}

async function postProposalAction(
  proposalId: number,
  action: "accept" | "reject" | "withdraw",
  payload?: CardProposalReviewRequest,
): Promise<CardProposalResponse> {
  return await fetchWebApiJson<CardProposalResponse>(
    `/web-api/card-proposals/${proposalId}/${action}`,
    {
      body: payload,
      method: "POST",
    },
  );
}

export function useMyProposalsQuery(enabled: boolean) {
  return useQuery({
    enabled,
    queryFn: fetchMyProposals,
    queryKey: workspaceQueryKeys.myProposals,
  });
}

export function useReviewQueueQuery(enabled: boolean) {
  return useQuery({
    enabled,
    queryFn: fetchReviewQueue,
    queryKey: workspaceQueryKeys.reviewQueue,
    retry: false,
  });
}

export function useProposalActionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      readonly action: "accept" | "reject" | "withdraw";
      readonly proposalId: number;
      readonly reviewNote?: string;
    }) =>
      await postProposalAction(input.proposalId, input.action, {
        review_note: input.reviewNote,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceQueryKeys.myProposals,
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceQueryKeys.reviewQueue,
      });
    },
  });
}
