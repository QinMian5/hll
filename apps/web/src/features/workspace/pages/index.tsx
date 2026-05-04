// abstract: Workspace route for current-user proposal tracking.
// out_of_scope: Proposal creation forms, reviewer queue actions, and role-management UI.

import {
  CheckCircle2,
  Circle,
  CircleSlash2,
  Clock3,
  type LucideIcon,
  Plus,
  SquarePen,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  FieldControl,
  Input,
  PageHeader,
  ScrollArea,
  Textarea,
} from "../../../shared/ui";
import { cn } from "../../../shared/utils";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import type { CardProposalResponse } from "../data/workspaceQueries";
import { useMyProposalsQuery } from "../data/workspaceQueries";

const scrollAreaTheme =
  "[--scroll-area-padding-right:var(--spacing-docs-scrollbar-width)] [--scroll-area-scrollbar-width:var(--spacing-docs-scrollbar-width)] [--scroll-area-thumb-color:var(--color-docs-scrollbar-thumb)] [--scroll-area-track-color:var(--color-docs-scrollbar-track)]";

const proposalTypeMeta: Record<
  CardProposalResponse["proposal_type"],
  {
    readonly Icon: LucideIcon;
    readonly label: string;
  }
> = {
  create: { Icon: Plus, label: "Add Card" },
  delete: { Icon: Trash2, label: "Delete Card" },
  edit: { Icon: SquarePen, label: "Edit Card" },
};

const proposalStatusMeta: Record<
  CardProposalResponse["status"],
  {
    readonly Icon: LucideIcon;
    readonly dotClassName: string;
    readonly label: string;
  }
> = {
  accepted_applied: {
    Icon: CheckCircle2,
    dotClassName: "bg-knowledge-status-accepted",
    label: "Accepted",
  },
  pending_review: {
    Icon: Clock3,
    dotClassName: "bg-knowledge-status-pending",
    label: "Pending",
  },
  rejected: {
    Icon: CircleSlash2,
    dotClassName: "bg-knowledge-status-rejected",
    label: "Rejected",
  },
  withdrawn: {
    Icon: Circle,
    dotClassName: "bg-knowledge-status-cancelled",
    label: "Cancelled",
  },
};

function readPayloadString(
  payload: Record<string, unknown>,
  keys: readonly string[],
): string | undefined {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim() !== "") {
      return value;
    }
  }

  return undefined;
}

function proposalDisplayTitle(proposal: CardProposalResponse): string {
  const payload = proposal.payload as Record<string, unknown>;
  return (
    readPayloadString(payload, [
      "proposed_title",
      "suggested_title",
      "title",
      "current_title",
    ]) ?? `Card #${String(payload.target_node_id ?? proposal.id)}`
  );
}

function proposalDisplayContent(proposal: CardProposalResponse): string {
  const payload = proposal.payload as Record<string, unknown>;
  return (
    readPayloadString(payload, [
      "proposed_content",
      "suggested_content",
      "content",
      "current_content",
    ]) ?? `Target card #${String(payload.target_node_id ?? proposal.id)}`
  );
}

function proposalDisplayRationale(proposal: CardProposalResponse): string {
  const payload = proposal.payload as Record<string, unknown>;
  return (
    readPayloadString(payload, ["rationale", "reason"]) ??
    proposal.review_note ??
    "No rationale provided."
  );
}

function ProposalStatus({
  status,
}: {
  readonly status: CardProposalResponse["status"];
}) {
  const meta = proposalStatusMeta[status];

  return (
    <span className="flex h-5 items-center gap-knowledge-workspace-proposal-status-gap text-[12px] leading-[18px] font-medium text-knowledge-text-muted">
      <span
        aria-hidden="true"
        className={cn(
          "size-knowledge-workspace-proposal-status-dot rounded-full",
          meta.dotClassName,
        )}
      />
      {meta.label}
    </span>
  );
}

function ProposalEntry({
  isSelected,
  onSelect,
  proposal,
}: {
  readonly isSelected: boolean;
  readonly onSelect: () => void;
  readonly proposal: CardProposalResponse;
}) {
  const title = proposalDisplayTitle(proposal);
  const typeMeta = proposalTypeMeta[proposal.proposal_type];
  const Icon = typeMeta.Icon;

  return (
    <button
      aria-pressed={isSelected}
      className={cn(
        "flex w-full shrink-0 items-center justify-center gap-knowledge-workspace-proposal-entry-gap rounded-knowledge-surface border px-knowledge-workspace-proposal-entry-padding-x py-knowledge-workspace-proposal-entry-padding-y text-left transition-colors",
        isSelected
          ? "border-docs-border-accent bg-knowledge-surface-accent-soft"
          : "border-knowledge-border-card bg-knowledge-surface-card hover:border-docs-border-accent hover:bg-knowledge-surface-accent-soft",
      )}
      onClick={onSelect}
      type="button"
    >
      <span className="flex size-knowledge-workspace-proposal-icon-container shrink-0 items-center justify-center text-knowledge-workspace-action-icon">
        <Icon
          aria-hidden="true"
          className="size-knowledge-workspace-proposal-icon"
          strokeWidth={2}
        />
      </span>
      <span className="min-w-0 flex-1 whitespace-normal text-knowledge-workspace-proposal-entry-title font-semibold text-knowledge-text-default">
        {title}
      </span>
      <span className="flex w-knowledge-workspace-proposal-status-slot shrink-0 items-center">
        <ProposalStatus status={proposal.status} />
      </span>
    </button>
  );
}

function EmptyPanel({ label }: { readonly label: string }) {
  return (
    <div className="flex min-h-[160px] items-center justify-center rounded-knowledge-surface border border-knowledge-border-subtle bg-white/70 px-4 text-knowledge-body text-knowledge-text-muted">
      {label}
    </div>
  );
}

function FieldLabel({
  children,
  htmlFor,
}: {
  readonly children: string;
  readonly htmlFor: string;
}) {
  return (
    <label
      className="text-knowledge-dialog-field-label font-medium text-knowledge-text-default"
      htmlFor={htmlFor}
    >
      {children}
    </label>
  );
}

function ReadOnlyField({
  id,
  label,
  multiline = false,
  value,
}: {
  readonly id: string;
  readonly label: string;
  readonly multiline?: boolean;
  readonly value: string;
}) {
  return (
    <div className="flex w-full shrink-0 flex-col gap-knowledge-dialog-field-gap">
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <FieldControl className="flex-col items-start">
        {multiline ? (
          <Textarea id={id} readOnly rows={1} value={value} />
        ) : (
          <Input id={id} readOnly value={value} />
        )}
      </FieldControl>
    </div>
  );
}

function SummaryCell({
  Icon,
  label,
  value,
}: {
  readonly Icon: LucideIcon;
  readonly label: string;
  readonly value: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2 overflow-hidden rounded-knowledge-control bg-knowledge-surface-accent-soft px-knowledge-dialog-input-padding-x py-knowledge-dialog-input-padding-y">
      <span className="flex size-knowledge-workspace-proposal-icon-container shrink-0 items-center justify-center text-knowledge-brand">
        <Icon
          aria-hidden="true"
          className="size-knowledge-workspace-proposal-icon"
          strokeWidth={2}
        />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-knowledge-page-header-title-gap overflow-hidden">
        <span className="min-w-0 text-knowledge-workspace-proposal-summary-label text-knowledge-text-muted">
          {label}
        </span>
        <span className="min-w-0 text-knowledge-workspace-proposal-summary-value font-semibold text-knowledge-text-default">
          {value}
        </span>
      </span>
    </div>
  );
}

function ProposalDetail({
  proposal,
}: {
  readonly proposal: CardProposalResponse | undefined;
}) {
  if (!proposal) {
    return <EmptyPanel label="Select a proposal to view details." />;
  }

  const typeMeta = proposalTypeMeta[proposal.proposal_type];
  const statusMeta = proposalStatusMeta[proposal.status];

  return (
    <div className="flex min-h-0 w-full flex-1 items-start gap-knowledge-dialog-form-scrollbar-gap overflow-hidden rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-knowledge-dialog-padding">
      <ScrollArea
        className={cn("h-full min-w-0 flex-1", scrollAreaTheme)}
        viewportClassName="flex h-full flex-col gap-knowledge-dialog-form-gap overflow-y-auto overflow-x-clip"
      >
        <div className="grid w-full shrink-0 grid-cols-2 gap-2 overflow-hidden">
          <SummaryCell
            Icon={typeMeta.Icon}
            label="Proposal Type"
            value={typeMeta.label}
          />
          <SummaryCell
            Icon={statusMeta.Icon}
            label="Status"
            value={
              proposal.status === "pending_review"
                ? "Pending Review"
                : statusMeta.label
            }
          />
        </div>
        <ReadOnlyField
          id="workspace-proposal-title"
          label="Title"
          value={proposalDisplayTitle(proposal)}
        />
        <ReadOnlyField
          id="workspace-proposal-content"
          label="Content"
          multiline
          value={proposalDisplayContent(proposal)}
        />
        <ReadOnlyField
          id="workspace-proposal-rationale"
          label="Rationale"
          multiline
          value={proposalDisplayRationale(proposal)}
        />
      </ScrollArea>
    </div>
  );
}

export function WorkspacePage() {
  const session = useWebSession();
  const isAuthenticated = session.status === "authenticated";
  const myProposals = useMyProposalsQuery(isAuthenticated);
  const proposals = useMemo(
    () => myProposals.data?.proposals ?? [],
    [myProposals.data?.proposals],
  );
  const [selectedProposalId, setSelectedProposalId] = useState<
    number | undefined
  >();
  const selectedProposal =
    proposals.find((proposal) => proposal.id === selectedProposalId) ??
    proposals[0];

  useEffect(() => {
    if (
      proposals.length > 0 &&
      !proposals.some((proposal) => proposal.id === selectedProposalId)
    ) {
      setSelectedProposalId(proposals[0]?.id);
    }
  }, [proposals, selectedProposalId]);

  if (!isAuthenticated) {
    return (
      <main className="flex h-full min-h-0 items-center justify-center p-4">
        <EmptyPanel label="Sign in to open Workspace." />
      </main>
    );
  }

  return (
    <main className="flex h-full min-h-0 flex-col gap-knowledge-page-content-gap overflow-hidden px-knowledge-page-padding-x pt-knowledge-page-padding-top pb-knowledge-page-padding-bottom lg:px-knowledge-page-padding-x-desktop lg:pt-knowledge-page-padding-top-desktop lg:pb-knowledge-page-padding-bottom-desktop">
      <PageHeader title="Workspace" />
      <div className="grid min-h-0 w-full flex-1 grid-cols-1 grid-rows-[minmax(0,1fr)_minmax(0,2fr)] gap-y-knowledge-split-view-section-gap overflow-hidden lg:flex lg:items-start lg:gap-knowledge-split-view-section-gap">
        <section className="flex min-h-0 flex-col gap-knowledge-split-view-section-gap overflow-hidden lg:h-full lg:w-knowledge-split-view-rail-width lg:shrink-0">
          <h2 className="m-0 h-knowledge-split-view-panel-title w-full shrink-0 text-knowledge-split-view-panel-title font-semibold text-knowledge-text-default">
            Proposals
          </h2>
          <ScrollArea
            className={cn("w-full flex-1", scrollAreaTheme)}
            viewportClassName="flex h-full flex-col gap-knowledge-workspace-proposal-list-gap overflow-y-auto overflow-x-clip"
          >
            {proposals.length ? (
              proposals.map((proposal) => (
                <ProposalEntry
                  isSelected={proposal.id === selectedProposal?.id}
                  key={proposal.id}
                  onSelect={() => {
                    setSelectedProposalId(proposal.id);
                  }}
                  proposal={proposal}
                />
              ))
            ) : (
              <EmptyPanel label="No proposals submitted yet." />
            )}
          </ScrollArea>
        </section>
        <section className="flex min-h-0 flex-col gap-knowledge-split-view-section-gap overflow-hidden lg:h-full lg:min-w-0 lg:flex-1">
          <h2 className="m-0 h-knowledge-split-view-panel-title w-full shrink-0 text-knowledge-split-view-panel-title font-semibold text-knowledge-text-default">
            Proposal Detail
          </h2>
          <ProposalDetail proposal={selectedProposal} />
        </section>
      </div>
    </main>
  );
}
