// abstract: Workspace route for proposal tracking and reviewer queue actions.
// out_of_scope: Admin role-management UI and notification workflows.

import { Check, RotateCcw, X } from "lucide-react";
import { Button, PageHeader } from "../../../shared/ui";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import type { CardProposalResponse } from "../data/workspaceQueries";
import {
  useMyProposalsQuery,
  useProposalActionMutation,
  useReviewQueueQuery,
} from "../data/workspaceQueries";

function ProposalCard({
  proposal,
  reviewerActions,
}: {
  readonly proposal: CardProposalResponse;
  readonly reviewerActions?: {
    readonly onAccept: () => void;
    readonly onReject: () => void;
  };
}) {
  const payload = proposal.payload as Record<string, unknown>;
  const title =
    typeof payload.proposed_title === "string"
      ? payload.proposed_title
      : typeof payload.suggested_title === "string"
        ? payload.suggested_title
        : `Card #${String(payload.target_node_id ?? proposal.id)}`;

  return (
    <article className="flex flex-col gap-3 rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 text-[12px] leading-4 font-medium text-knowledge-text-muted uppercase">
            {proposal.proposal_type} · {proposal.status}
          </p>
          <h3 className="m-0 mt-1 text-knowledge-title font-semibold text-knowledge-text-default">
            {title}
          </h3>
        </div>
        {proposal.status === "pending_review" && reviewerActions ? (
          <div className="flex shrink-0 gap-2">
            <Button
              aria-label={`Accept proposal ${proposal.id}`}
              onClick={reviewerActions.onAccept}
              size="icon"
            >
              <Check aria-hidden="true" className="size-4" />
            </Button>
            <Button
              aria-label={`Reject proposal ${proposal.id}`}
              onClick={reviewerActions.onReject}
              size="icon"
              variant="secondary"
            >
              <X aria-hidden="true" className="size-4" />
            </Button>
          </div>
        ) : null}
      </div>
      {typeof payload.reason === "string" ? (
        <p className="m-0 text-knowledge-body text-knowledge-text-muted">
          {payload.reason}
        </p>
      ) : null}
    </article>
  );
}

function EmptyPanel({ label }: { readonly label: string }) {
  return (
    <div className="flex min-h-[160px] items-center justify-center rounded-knowledge-surface border border-knowledge-border-subtle bg-white/70 px-4 text-knowledge-body text-knowledge-text-muted">
      {label}
    </div>
  );
}

export function WorkspacePage() {
  const session = useWebSession();
  const isAuthenticated = session.status === "authenticated";
  const myProposals = useMyProposalsQuery(isAuthenticated);
  const reviewQueue = useReviewQueueQuery(isAuthenticated);
  const proposalAction = useProposalActionMutation();
  const reviewForbidden =
    reviewQueue.error instanceof WebApiRequestError &&
    reviewQueue.error.status === 403;

  if (!isAuthenticated) {
    return (
      <main className="flex h-full min-h-0 items-center justify-center p-4">
        <EmptyPanel label="Sign in to open Workspace." />
      </main>
    );
  }

  return (
    <main className="flex h-full min-h-0 flex-col gap-4 overflow-hidden p-4 lg:p-6">
      <PageHeader title="Workspace" />
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-hidden xl:grid-cols-2">
        <section className="flex min-h-0 flex-col gap-3 overflow-hidden">
          <h2 className="m-0 text-[16px] leading-6 font-semibold text-knowledge-text-default">
            My proposals
          </h2>
          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {myProposals.data?.proposals.length ? (
              myProposals.data.proposals.map((proposal) => (
                <ProposalCard key={proposal.id} proposal={proposal} />
              ))
            ) : (
              <EmptyPanel label="No proposals submitted yet." />
            )}
          </div>
        </section>
        <section className="flex min-h-0 flex-col gap-3 overflow-hidden">
          <h2 className="m-0 text-[16px] leading-6 font-semibold text-knowledge-text-default">
            Review queue
          </h2>
          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {reviewForbidden ? (
              <EmptyPanel label="Reviewer access is required." />
            ) : reviewQueue.data?.proposals.length ? (
              reviewQueue.data.proposals.map((proposal) => (
                <ProposalCard
                  key={proposal.id}
                  proposal={proposal}
                  reviewerActions={{
                    onAccept: () => {
                      proposalAction.mutate({
                        action: "accept",
                        proposalId: proposal.id,
                      });
                    },
                    onReject: () => {
                      proposalAction.mutate({
                        action: "reject",
                        proposalId: proposal.id,
                      });
                    },
                  }}
                />
              ))
            ) : (
              <EmptyPanel label="No pending proposals." />
            )}
          </div>
        </section>
      </div>
      {proposalAction.isError ? (
        <p className="m-0 flex shrink-0 items-center gap-2 rounded-knowledge-surface bg-knowledge-warning-surface px-3 py-2 text-knowledge-caption font-medium text-knowledge-warning-text">
          <RotateCcw aria-hidden="true" className="size-4" />
          Could not update the proposal. Refresh and retry.
        </p>
      ) : null}
    </main>
  );
}
