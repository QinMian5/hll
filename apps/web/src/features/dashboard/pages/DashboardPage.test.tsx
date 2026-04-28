// abstract: Route-level tests for the Figma-aligned dashboard token page.
// out_of_scope: Backend token lifecycle integration and AppShell navigation.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DashboardTokensResponse } from "../types";

vi.mock("../data/dashboardTokens", () => ({
  useCreateDashboardTokenMutation: vi.fn(),
  useDashboardTokensQuery: vi.fn(),
  useDeleteDashboardTokenMutation: vi.fn(),
  useRenameDashboardTokenMutation: vi.fn(),
}));

import * as dashboardTokens from "../data/dashboardTokens";
import { DashboardPage } from "./index";

const tokenResponse: DashboardTokensResponse = {
  tokens: [
    {
      createdAt: "2026-04-28T10:00:00.000Z",
      expiresAt: null,
      lastUsedAt: "2026-04-28T11:00:00.000Z",
      maskedToken: "kn_pat_...alpha",
      name: "Research MCP",
      tokenValue: "kn_pat_clear_alpha",
      usageCount: 12400,
    },
  ],
  usageAvailable: true,
};

const mockUseDashboardTokensQuery = vi.mocked(
  dashboardTokens.useDashboardTokensQuery,
);
const mockUseCreateDashboardTokenMutation = vi.mocked(
  dashboardTokens.useCreateDashboardTokenMutation,
);
const mockUseRenameDashboardTokenMutation = vi.mocked(
  dashboardTokens.useRenameDashboardTokenMutation,
);
const mockUseDeleteDashboardTokenMutation = vi.mocked(
  dashboardTokens.useDeleteDashboardTokenMutation,
);

function queryResult(
  value: Partial<ReturnType<typeof dashboardTokens.useDashboardTokensQuery>>,
) {
  return value as ReturnType<typeof dashboardTokens.useDashboardTokensQuery>;
}

function mutationResult<TMutationResult>(
  mutateAsync: (...variables: readonly unknown[]) => Promise<unknown>,
  isPending = false,
) {
  return {
    isPending,
    mutateAsync,
  } as TMutationResult;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: vi.fn(async () => undefined),
    },
  });
  mockUseDashboardTokensQuery.mockReturnValue(
    queryResult({
      data: tokenResponse,
      error: null,
      isError: false,
      isPending: false,
    }),
  );
  mockUseCreateDashboardTokenMutation.mockReturnValue(
    mutationResult<
      ReturnType<typeof dashboardTokens.useCreateDashboardTokenMutation>
    >(vi.fn(async () => undefined)),
  );
  mockUseRenameDashboardTokenMutation.mockReturnValue(
    mutationResult<
      ReturnType<typeof dashboardTokens.useRenameDashboardTokenMutation>
    >(vi.fn(async () => undefined)),
  );
  mockUseDeleteDashboardTokenMutation.mockReturnValue(
    mutationResult<
      ReturnType<typeof dashboardTokens.useDeleteDashboardTokenMutation>
    >(vi.fn(async () => undefined)),
  );
});

describe("DashboardPage", () => {
  it("projects the Figma dashboard content layout inside the existing shell slot", () => {
    render(<DashboardPage />);

    expect(screen.getByTestId("dashboard-route-page")).toHaveClass(
      "gap-4",
      "px-4",
      "py-4",
      "lg:gap-5",
      "lg:px-8",
      "lg:pt-6",
      "lg:pb-8",
    );
    expect(screen.getByTestId("dashboard-page-header")).toHaveClass(
      "h-[52px]",
      "lg:h-16",
    );
    expect(screen.getByTestId("dashboard-token-directory")).toHaveClass(
      "rounded-lg",
      "border-[rgba(214,227,247,0.86)]",
      "bg-[rgba(255,255,255,0.88)]",
      "p-4",
      "lg:p-6",
    );
    expect(screen.getByTestId("dashboard-token-table")).toHaveClass(
      "hidden",
      "lg:block",
    );
    expect(screen.getByTestId("dashboard-mobile-token-list")).toHaveClass(
      "lg:hidden",
    );
  });

  it("renders token rows with copy, rename, and delete lifecycle controls", async () => {
    render(<DashboardPage />);

    expect(screen.getAllByText("Research MCP")).toHaveLength(2);
    expect(screen.getAllByText("kn_pat_...alpha")).toHaveLength(2);
    expect(screen.getAllByText("12.4k")).toHaveLength(2);

    fireEvent.click(
      screen.getAllByRole("button", { name: "Copy Research MCP" })[0],
    );

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "kn_pat_clear_alpha",
      ),
    );
    expect(
      screen.getAllByRole("button", { name: "Rename Research MCP" })[0],
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: "Delete Research MCP" })[0],
    ).toBeInTheDocument();
  });

  it("submits the create token dialog", async () => {
    const mutateAsync = vi.fn(async () => undefined);
    mockUseCreateDashboardTokenMutation.mockReturnValue(
      mutationResult<
        ReturnType<typeof dashboardTokens.useCreateDashboardTokenMutation>
      >(mutateAsync),
    );

    render(<DashboardPage />);

    fireEvent.click(screen.getByRole("button", { name: "Create Token" }));
    fireEvent.change(screen.getByLabelText("Token name"), {
      target: { value: "Research Lab" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Create Token" })[1]);

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ name: "Research Lab" }),
    );
  });

  it("submits the rename token dialog", async () => {
    const mutateAsync = vi.fn(async () => undefined);
    mockUseRenameDashboardTokenMutation.mockReturnValue(
      mutationResult<
        ReturnType<typeof dashboardTokens.useRenameDashboardTokenMutation>
      >(mutateAsync),
    );

    render(<DashboardPage />);

    fireEvent.click(
      screen.getAllByRole("button", { name: "Rename Research MCP" })[0],
    );
    fireEvent.change(screen.getByLabelText("Token name"), {
      target: { value: "Research API" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rename Token" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        currentName: "Research MCP",
        name: "Research API",
      }),
    );
  });

  it("confirms token deletion", async () => {
    const mutateAsync = vi.fn(async () => undefined);
    mockUseDeleteDashboardTokenMutation.mockReturnValue(
      mutationResult<
        ReturnType<typeof dashboardTokens.useDeleteDashboardTokenMutation>
      >(mutateAsync),
    );

    render(<DashboardPage />);

    fireEvent.click(
      screen.getAllByRole("button", { name: "Delete Research MCP" })[0],
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete Token" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ name: "Research MCP" }),
    );
  });
});
