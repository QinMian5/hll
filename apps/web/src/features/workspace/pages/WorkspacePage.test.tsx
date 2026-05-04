// abstract: Route-level tests for current-user Workspace proposal tracking.
// out_of_scope: Backend authorization and proposal review behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CardProposalResponse } from "../data/workspaceQueries";

vi.mock("../../../shared/web-api/useWebSession", () => ({
  useWebSession: vi.fn(),
}));

vi.mock("../data/workspaceQueries", () => ({
  useMyProposalsQuery: vi.fn(),
}));

import * as webSession from "../../../shared/web-api/useWebSession";
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

const mockUseWebSession = vi.mocked(webSession.useWebSession);
const mockUseMyProposalsQuery = vi.mocked(workspaceQueries.useMyProposalsQuery);

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
});

describe("WorkspacePage", () => {
  it("asks anonymous users to sign in before opening proposal workspace", () => {
    mockUseWebSession.mockReturnValue({ status: "anonymous" });

    render(<WorkspacePage />);

    expect(screen.getByText("Sign in to open Workspace.")).toBeInTheDocument();
    expect(mockUseMyProposalsQuery).toHaveBeenCalledWith(false);
  });

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
    expect(screen.queryByLabelText("Rationale")).not.toBeInTheDocument();
    expect(mockUseMyProposalsQuery).toHaveBeenCalledWith(true);
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

    expect(screen.getByText("No proposals submitted yet.")).toBeInTheDocument();
  });
});
