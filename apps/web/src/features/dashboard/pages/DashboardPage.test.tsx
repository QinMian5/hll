// abstract: Route-level tests for the Figma-aligned dashboard token page.
// out_of_scope: Backend token lifecycle integration and AppShell navigation.

import "@testing-library/jest-dom/vitest";

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WebApiRequestError } from "../../../shared/web-api/errors";
import type { DashboardQuotaResponse, DashboardTokensResponse } from "../types";

vi.mock("../data/dashboardTokens", () => ({
  useCreateDashboardTokenMutation: vi.fn(),
  useDashboardTokensQuery: vi.fn(),
  useDeleteDashboardTokenMutation: vi.fn(),
  useRenameDashboardTokenMutation: vi.fn(),
}));
vi.mock("../data/dashboardQuota", () => ({
  useDashboardQuotaQuery: vi.fn(),
}));

import * as dashboardQuota from "../data/dashboardQuota";
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

const quotaResponse: DashboardQuotaResponse = {
  quota: {
    daily: {
      limit: 1000,
      remaining: 963,
      resetAt: "2026-04-29T04:00:00.000Z",
      startedAt: "2026-04-28T10:00:00.000Z",
      used: 37,
      windowSeconds: 86_400,
    },
    weekly: {
      limit: 5000,
      remaining: 4816,
      resetAt: "2026-05-03T10:00:00.000Z",
      startedAt: "2026-04-28T10:00:00.000Z",
      used: 184,
      windowSeconds: 604_800,
    },
  },
  quotaAvailable: true,
};

const mockUseDashboardTokensQuery = vi.mocked(
  dashboardTokens.useDashboardTokensQuery,
);
const mockUseDashboardQuotaQuery = vi.mocked(
  dashboardQuota.useDashboardQuotaQuery,
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

function quotaQueryResult(
  value: Partial<ReturnType<typeof dashboardQuota.useDashboardQuotaQuery>>,
) {
  return value as ReturnType<typeof dashboardQuota.useDashboardQuotaQuery>;
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
  mockUseDashboardQuotaQuery.mockReturnValue(
    quotaQueryResult({
      data: quotaResponse,
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
      "gap-knowledge-dashboard-page-gap",
      "px-knowledge-dashboard-page-padding-x",
      "pt-knowledge-dashboard-page-padding-top",
      "pb-knowledge-dashboard-page-padding-bottom",
      "lg:gap-knowledge-dashboard-page-gap-desktop",
      "lg:px-knowledge-dashboard-page-padding-x-desktop",
      "lg:pt-knowledge-dashboard-page-padding-top-desktop",
      "lg:pb-knowledge-dashboard-page-padding-bottom-desktop",
    );
    expect(screen.getByTestId("dashboard-page-header")).toHaveClass(
      "h-knowledge-dashboard-page-header",
    );
    expect(screen.getByTestId("dashboard-quota-summary")).toHaveClass(
      "rounded-knowledge-surface",
      "border-knowledge-border-card",
      "bg-knowledge-surface-card",
      "p-knowledge-dashboard-surface-padding",
    );
    expect(screen.getByTestId("dashboard-token-directory")).toHaveClass(
      "rounded-knowledge-surface",
      "border-knowledge-border-card",
      "bg-knowledge-surface-card",
      "p-knowledge-dashboard-surface-padding",
    );
    expect(screen.getByTestId("dashboard-token-table")).toHaveClass(
      "h-knowledge-dashboard-table-height",
      "lg:h-knowledge-dashboard-table-height-desktop",
    );
    expect(
      screen.getByTestId("dashboard-token-table-fixed-header"),
    ).toHaveClass(
      "h-knowledge-dashboard-table-header-height",
      "lg:h-knowledge-dashboard-table-header-height-desktop",
    );
    expect(
      screen.getByTestId("dashboard-token-table-scrollbar-gutter"),
    ).toHaveClass("w-knowledge-dashboard-scrollbar-width");
    expect(screen.getByTestId("dashboard-token-table-scroll-area")).toHaveClass(
      "flex-1",
      "min-h-0",
    );
  });

  it("renders quota above tokens with Daily and Weekly account limits", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-28T10:00:00.000Z"));

    try {
      render(<DashboardPage />);

      const quota = screen.getByTestId("dashboard-quota-summary");
      const directory = screen.getByTestId("dashboard-token-directory");

      expect(
        quota.compareDocumentPosition(directory) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
      expect(screen.getByText("Quota")).toBeInTheDocument();
      expect(screen.getByText("Daily")).toBeInTheDocument();
      expect(screen.getByText("37 / 1,000")).toBeInTheDocument();
      expect(screen.getByText("Weekly")).toBeInTheDocument();
      expect(screen.getByText("184 / 5,000")).toBeInTheDocument();
      expect(screen.getByText("resets in 18h")).toBeInTheDocument();
      expect(screen.getByText("resets in 5d")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("omits reset copy for inactive quota windows", () => {
    mockUseDashboardQuotaQuery.mockReturnValue(
      quotaQueryResult({
        data: {
          quota: {
            daily: {
              limit: 1000,
              remaining: 1000,
              resetAt: null,
              startedAt: null,
              used: 0,
              windowSeconds: 86_400,
            },
            weekly: {
              limit: 5000,
              remaining: 5000,
              resetAt: null,
              startedAt: null,
              used: 0,
              windowSeconds: 604_800,
            },
          },
          quotaAvailable: true,
        },
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    render(<DashboardPage />);

    expect(screen.getByText("0 / 1,000")).toBeInTheDocument();
    expect(screen.getByText("0 / 5,000")).toBeInTheDocument();
    expect(screen.queryByText("starts on first use")).not.toBeInTheDocument();
  });

  it("renders token rows with copy, rename, and delete lifecycle controls", async () => {
    render(<DashboardPage />);

    expect(screen.getByText("Research MCP")).toBeInTheDocument();
    expect(screen.getByText("kn_pat_...alpha")).toBeInTheDocument();
    expect(screen.getByText("12.4k")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Copy Research MCP" }));

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "kn_pat_clear_alpha",
      ),
    );
    expect(
      screen.getByRole("button", { name: "Rename Research MCP" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Delete Research MCP" }),
    ).toBeInTheDocument();
  });

  it("shows copied feedback for three seconds after clipboard copy succeeds", async () => {
    vi.useFakeTimers();

    try {
      render(<DashboardPage />);

      await act(async () => {
        fireEvent.click(
          screen.getByRole("button", { name: "Copy Research MCP" }),
        );
        await Promise.resolve();
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "kn_pat_clear_alpha",
      );
      expect(
        screen.getByRole("button", { name: "Copied Research MCP" }),
      ).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(2999);
      });

      expect(
        screen.getByRole("button", { name: "Copied Research MCP" }),
      ).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(1);
      });

      expect(
        screen.getByRole("button", { name: "Copy Research MCP" }),
      ).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
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
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Research Lab" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Create Token" })[1]);

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ name: "Research Lab" }),
    );
  });

  it("shows a duplicate token name error with actionable dialog copy", async () => {
    const mutateAsync = vi.fn(async () => {
      throw new WebApiRequestError({
        code: "dashboard_token_name_conflict",
        message: "Dashboard dependency unavailable.",
        status: 409,
      });
    });
    mockUseCreateDashboardTokenMutation.mockReturnValue(
      mutationResult<
        ReturnType<typeof dashboardTokens.useCreateDashboardTokenMutation>
      >(mutateAsync),
    );

    render(<DashboardPage />);

    fireEvent.click(screen.getByRole("button", { name: "Create Token" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Research MCP" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Create Token" })[1]);

    expect(
      await screen.findByText(
        'A token named "Research MCP" already exists. Use a different name.',
      ),
    ).toBeInTheDocument();
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
      screen.getByRole("button", { name: "Rename Research MCP" }),
    );
    fireEvent.change(screen.getByLabelText("Name"), {
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

  it("uses tokenized dashboard button styles for the create dialog", () => {
    render(<DashboardPage />);

    const trigger = screen.getByRole("button", { name: "Create Token" });
    expect(trigger).toHaveClass(
      "bg-knowledge-brand",
      "h-knowledge-control",
      "rounded-knowledge-control",
      "text-knowledge-button",
      "whitespace-nowrap",
    );

    fireEvent.click(trigger);

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    const createButtons = screen.getAllByRole("button", {
      name: "Create Token",
    });

    expect(cancelButton).toHaveClass(
      "bg-knowledge-surface-control",
      "text-knowledge-text-default",
      "w-full",
    );
    expect(cancelButton.className).not.toContain("bg-[#171717]");
    expect(createButtons[1]).toHaveClass("bg-knowledge-brand", "w-full");
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
      screen.getByRole("button", { name: "Delete Research MCP" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete Token" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({ name: "Research MCP" }),
    );
  });
});
