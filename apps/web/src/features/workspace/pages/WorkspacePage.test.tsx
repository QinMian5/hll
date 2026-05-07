// abstract: Route-level tests for current-user Workspace proposal tracking.
// out_of_scope: Backend authorization and proposal review behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CardProposalResponse } from "../data/workspaceQueries";

vi.mock("../data/workspaceQueries", () => ({
  useMyProposalsQuery: vi.fn(),
  useWithdrawCardProposalMutation: vi.fn(),
}));

import * as workspaceQueries from "../data/workspaceQueries";
import { WorkspacePage } from "./index";

const proposal: CardProposalResponse = {
  created_at: "2026-05-03T10:00:00.000Z",
  id: 42,
  payload: {
    base_version: 2,
    suggested_content: "Updated matrix decomposition content.",
    suggested_title: "Better matrix card",
    target_node_id: 10,
  },
  proposal_type: "edit",
  reason: "Clarifies the linear algebra explanation.",
  review_note: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  status: "pending_review",
  submitted_by_user_id: "user-1",
  updated_at: "2026-05-03T10:00:00.000Z",
};

const mockUseMyProposalsQuery = vi.mocked(workspaceQueries.useMyProposalsQuery);
const mockUseWithdrawCardProposalMutation = vi.mocked(
  workspaceQueries.useWithdrawCardProposalMutation,
);

function queryResult(
  value: Partial<ReturnType<typeof workspaceQueries.useMyProposalsQuery>>,
) {
  return value as ReturnType<typeof workspaceQueries.useMyProposalsQuery>;
}

function mutationResult(
  value: Pick<
    ReturnType<typeof workspaceQueries.useWithdrawCardProposalMutation>,
    "isPending" | "mutate"
  >,
) {
  return value as unknown as ReturnType<
    typeof workspaceQueries.useWithdrawCardProposalMutation
  >;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  mockUseWithdrawCardProposalMutation.mockReturnValue(
    mutationResult({
      isPending: false,
      mutate: vi.fn(),
    }),
  );
  mockUseMyProposalsQuery.mockReturnValue(
    queryResult({
      data: { proposals: [proposal] },
      error: null,
      isError: false,
    }),
  );
});

describe("WorkspacePage", () => {
  it("renders only current-user proposals from the unified proposal model", () => {
    render(<WorkspacePage />);

    expect(
      screen.getByRole("heading", { name: "Workspace" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Proposals" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Proposal Detail" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Review Queue")).not.toBeInTheDocument();
    expect(screen.queryByText("Role Management")).not.toBeInTheDocument();
    expect(screen.getByText("Edit Card")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Pending Review")).toBeInTheDocument();
    expect(screen.getByText("Better matrix card")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better matrix card")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Updated matrix decomposition content."),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Clarifies the linear algebra explanation."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Reason")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cancel Proposal" }),
    ).toBeEnabled();
    expect(screen.queryByLabelText("Rationale")).not.toBeInTheDocument();
    expect(mockUseMyProposalsQuery).toHaveBeenCalledWith(true);
  });

  it("withdraws the selected pending proposal from the fixed action bar", () => {
    const mutate = vi.fn();
    mockUseWithdrawCardProposalMutation.mockReturnValue(
      mutationResult({
        isPending: false,
        mutate,
      }),
    );

    render(<WorkspacePage />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel Proposal" }));

    expect(mutate).toHaveBeenCalledWith(42);
  });

  it("renders delete proposal target card content from the proposal payload", () => {
    mockUseMyProposalsQuery.mockReturnValue(
      queryResult({
        data: {
          proposals: [
            {
              ...proposal,
              id: 43,
              payload: {
                base_version: 1,
                target_content:
                  "Physics studies matter, motion, energy, and force.",
                target_node_id: 450,
                target_title: "Physics",
              },
              proposal_type: "delete",
              reason: "Duplicate card.",
            },
          ],
        },
        error: null,
        isError: false,
      }),
    );

    render(<WorkspacePage />);

    expect(screen.getByDisplayValue("Physics")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue(
        "Physics studies matter, motion, energy, and force.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Card #450")).not.toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("Target card #450"),
    ).not.toBeInTheDocument();
  });

  it("disables proposal cancellation after review is complete", () => {
    mockUseMyProposalsQuery.mockReturnValue(
      queryResult({
        data: {
          proposals: [
            {
              ...proposal,
              status: "accepted_applied",
            },
          ],
        },
        error: null,
        isError: false,
      }),
    );

    render(<WorkspacePage />);

    expect(
      screen.getByRole("button", { name: "Cancel Proposal" }),
    ).toBeDisabled();
  });

  it("renders an empty state when the current user has no proposals", () => {
    mockUseMyProposalsQuery.mockReturnValue(
      queryResult({
        data: { proposals: [] },
        error: null,
        isError: false,
      }),
    );

    render(<WorkspacePage />);

    expect(screen.getByText("No Proposals Yet")).toBeInTheDocument();
    expect(screen.getByText("No Proposal Selected")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancel Proposal" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Proposals from Search will appear here."),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(
        "Proposal details will appear after a proposal is submitted.",
      ),
    ).not.toBeInTheDocument();
  });
});
