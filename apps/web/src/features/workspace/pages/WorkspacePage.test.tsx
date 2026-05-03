// abstract: Route-level tests for Workspace proposal lists and reviewer actions.
// out_of_scope: Backend authorization and card proposal application behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WebApiRequestError } from "../../../shared/web-api/errors";
import type { CardProposalResponse } from "../data/workspaceQueries";

vi.mock("../../../shared/web-api/useWebSession", () => ({
  useWebSession: vi.fn(),
}));

vi.mock("../data/workspaceQueries", () => ({
  useMyProposalsQuery: vi.fn(),
  useProposalActionMutation: vi.fn(),
  useReviewQueueQuery: vi.fn(),
}));

import * as webSession from "../../../shared/web-api/useWebSession";
import * as workspaceQueries from "../data/workspaceQueries";
import { WorkspacePage } from "./index";

const proposal: CardProposalResponse = {
  created_at: "2026-05-03T10:00:00.000Z",
  id: 42,
  payload: {
    base_version: 2,
    suggested_title: "Better matrix card",
    target_node_id: 10,
  },
  proposal_type: "edit",
  review_note: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  status: "pending_review",
  submitted_by_user_id: "user-1",
  updated_at: "2026-05-03T10:00:00.000Z",
};

const mockUseWebSession = vi.mocked(webSession.useWebSession);
const mockUseMyProposalsQuery = vi.mocked(workspaceQueries.useMyProposalsQuery);
const mockUseReviewQueueQuery = vi.mocked(workspaceQueries.useReviewQueueQuery);
const mockUseProposalActionMutation = vi.mocked(
  workspaceQueries.useProposalActionMutation,
);

function queryResult(
  value: Partial<ReturnType<typeof workspaceQueries.useMyProposalsQuery>>,
) {
  return value as ReturnType<typeof workspaceQueries.useMyProposalsQuery>;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  mockUseWebSession.mockReturnValue({
    status: "authenticated",
    user: {
      email: "ada@example.com",
      id: "user-1",
      name: "Ada Lovelace",
    },
  });
  mockUseMyProposalsQuery.mockReturnValue(
    queryResult({
      data: { proposals: [proposal] },
      error: null,
      isError: false,
    }),
  );
  mockUseReviewQueueQuery.mockReturnValue(
    queryResult({
      data: { proposals: [proposal] },
      error: null,
      isError: false,
    }),
  );
  mockUseProposalActionMutation.mockReturnValue({
    isError: false,
    mutate: vi.fn(),
  } as never);
});

describe("WorkspacePage", () => {
  it("asks anonymous users to sign in before opening proposal workspace", () => {
    mockUseWebSession.mockReturnValue({ status: "anonymous" });

    render(<WorkspacePage />);

    expect(screen.getByText("Sign in to open Workspace.")).toBeInTheDocument();
    expect(mockUseMyProposalsQuery).toHaveBeenCalledWith(false);
    expect(mockUseReviewQueueQuery).toHaveBeenCalledWith(false);
  });

  it("renders My proposals and Review queue from the unified proposal model", () => {
    render(<WorkspacePage />);

    expect(
      screen.getByRole("heading", { name: "Workspace" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "My proposals" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Review queue" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("edit · pending_review")).toHaveLength(2);
    expect(screen.getAllByText("Better matrix card")).toHaveLength(2);
    expect(mockUseMyProposalsQuery).toHaveBeenCalledWith(true);
    expect(mockUseReviewQueueQuery).toHaveBeenCalledWith(true);
  });

  it("submits reviewer accept and reject actions from the review queue", () => {
    const mutate = vi.fn();
    mockUseProposalActionMutation.mockReturnValue({
      isError: false,
      mutate,
    } as never);

    render(<WorkspacePage />);

    fireEvent.click(screen.getByRole("button", { name: "Accept proposal 42" }));
    fireEvent.click(screen.getByRole("button", { name: "Reject proposal 42" }));

    expect(mutate).toHaveBeenCalledWith({ action: "accept", proposalId: 42 });
    expect(mutate).toHaveBeenCalledWith({ action: "reject", proposalId: 42 });
  });

  it("keeps reviewer-only access distinct from contributor proposal tracking", () => {
    mockUseReviewQueueQuery.mockReturnValue(
      queryResult({
        data: undefined,
        error: new WebApiRequestError({
          code: "DOMAIN_KNOWLEDGE_PERMISSION_DENIED",
          message: "Reviewer role is required.",
          status: 403,
        }),
        isError: true,
      }),
    );

    render(<WorkspacePage />);

    expect(screen.getByText("Better matrix card")).toBeInTheDocument();
    expect(
      screen.getByText("Reviewer access is required."),
    ).toBeInTheDocument();
  });
});
