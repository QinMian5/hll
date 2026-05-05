// abstract: Route-level tests for the Figma-aligned Search page states.
// out_of_scope: Backend search integration and ranking semantics.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { createAppRouter } from "../../../app/router";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import type { SearchResponse } from "../data/searchQueries";

vi.mock("../../../app/auth/authTransport", () => ({
  startSilentSignIn: vi.fn(async () => "failed"),
  submitInteractiveSignIn: vi.fn(),
  submitSignOut: vi.fn(),
}));

vi.mock("../data/searchQueries", () => ({
  useCreateCardProposalMutation: vi.fn(),
  useSearchQuery: vi.fn(),
}));

vi.mock("../../../shared/web-api/useWebSession", () => ({
  useWebSession: vi.fn(),
}));

import * as webSession from "../../../shared/web-api/useWebSession";
import * as searchQueries from "../data/searchQueries";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "__KNOWLEDGE_RUNTIME_CONFIG__");
});

beforeEach(() => {
  Object.defineProperty(window, "__KNOWLEDGE_RUNTIME_CONFIG__", {
    configurable: true,
    value: {
      mcpPublicBaseUrl: "http://localhost:8002/mcp",
      searchMaxConnected: 9,
      searchMaxMatched: 4,
    },
  });
  window.scrollTo = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ status: "anonymous" }), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
    ),
  );
});

function renderSearchRoute(pathname: string) {
  const router = createAppRouter({
    initialEntries: [pathname],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );

  return { router };
}

const mockUseSearchQuery = vi.mocked(searchQueries.useSearchQuery);
const mockUseCreateCardProposalMutation = vi.mocked(
  searchQueries.useCreateCardProposalMutation,
);
const mockUseWebSession = vi.mocked(webSession.useWebSession);

function mockSearchQueryResult(
  value: Partial<ReturnType<typeof searchQueries.useSearchQuery>>,
) {
  return value as unknown as ReturnType<typeof searchQueries.useSearchQuery>;
}

describe("SearchPage", () => {
  beforeEach(() => {
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync: vi.fn(),
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: undefined,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({ status: "anonymous" });
  });

  it("renders the empty search state when no effective query exists", async () => {
    renderSearchRoute("/search");

    await waitFor(() =>
      expect(screen.getByTestId("search-route-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("search-empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("search-input")).toBeInTheDocument();
    expect(screen.queryByTestId("search-results-grid")).not.toBeInTheDocument();
  });

  it("renders backend search results and connected titles from URL query state", async () => {
    const payload: SearchResponse = {
      connected_titles: ["Adjacency matrix", "Matrix norm"],
      matched_cards: [
        {
          content:
            "*Returned* by the backend search API.\n\n- diagonalizable\n\n`rank`",
          current_version: 2,
          node_id: 10,
          title: "Matrix decomposition \\(A=PDP^{-1}\\)",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    await waitFor(() =>
      expect(screen.getByTestId("search-results-grid")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("search-suggestions-panel")).toBeInTheDocument();
    expect(screen.getByText("Search Results")).toBeInTheDocument();
    const addCardButton = screen.getByRole("button", { name: "Add Card" });
    expect(addCardButton).toBeInTheDocument();
    expect(addCardButton).toHaveClass(
      "h-knowledge-control",
      "px-knowledge-action-button-x",
      "whitespace-nowrap",
    );
    expect(addCardButton.className).not.toContain("w-[116px]");
    expect(addCardButton.className).not.toContain("px-[14px]");
    expect(screen.getByText("Related Results")).toBeInTheDocument();
    expect(screen.getByDisplayValue("matrix")).toBeInTheDocument();
    expect(screen.getByTestId("search-icon-button")).toBeInTheDocument();
    expect(screen.queryByTestId("search-empty-state")).not.toBeInTheDocument();
    expect(
      await screen.findByRole(
        "link",
        { name: /Search for Matrix decomposition/ },
        { timeout: 5_000 },
      ),
    ).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(
      await screen.findByText("Returned", {}, { timeout: 5_000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.getByText("rank").tagName).toBe("CODE");
    expect(
      screen.getByRole("button", { name: "Adjacency matrix" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Matrix norm" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Spectral theorem" }),
    ).not.toBeInTheDocument();
  });

  it("uses the single Figma loading skeleton state while search is fetching", async () => {
    const stalePayload: SearchResponse = {
      connected_titles: ["Existing related result"],
      matched_cards: [
        {
          content: "Existing result body.",
          current_version: 1,
          node_id: 10,
          title: "Existing result",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: stalePayload,
        error: null,
        isError: false,
        isFetching: true,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    await waitFor(() =>
      expect(screen.getByTestId("search-results-grid")).toBeInTheDocument(),
    );

    const addCardButton = screen.getByRole("button", { name: "Add Card" });
    expect(addCardButton).toBeDisabled();
    expect(addCardButton).toHaveClass(
      "disabled:bg-knowledge-brand-disabled",
      "disabled:hover:bg-knowledge-brand-disabled",
    );
    expect(screen.getAllByTestId("search-result-card-skeleton")).toHaveLength(
      4,
    );
    expect(screen.getAllByTestId("related-result-item-skeleton")).toHaveLength(
      9,
    );
    expect(screen.getAllByTestId("search-result-card-skeleton")[0]).toHaveClass(
      "h-search-result-card-height",
    );
    expect(
      screen.getAllByTestId("search-result-card-skeleton")[0],
    ).not.toHaveClass("h-[200px]");
    expect(
      screen.getAllByTestId("related-result-item-skeleton")[0],
    ).toHaveClass("min-h-search-related-result-height");
    expect(
      screen.getAllByTestId("related-result-item-skeleton")[0],
    ).not.toHaveClass("h-10");
    expect(screen.queryByText("Existing result")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Existing related result" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Searching Knowledge Cards"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Updating Results")).not.toBeInTheDocument();
  });

  it("shows a quota-specific error when search is rate limited", async () => {
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: undefined,
        error: new WebApiRequestError({
          code: "quota_exceeded",
          message: "Rate limit exceeded.",
          status: 429,
        }),
        isError: true,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    expect(await screen.findByTestId("search-error-state")).toHaveTextContent(
      "Too many searches",
    );
    expect(screen.getByTestId("search-error-state")).toHaveTextContent(
      "Try again shortly.",
    );
  });

  it("projects the latest Figma responsive results layout", async () => {
    const payload: SearchResponse = {
      connected_titles: ["Adjacency matrix"],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: "Matrix decomposition",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    await waitFor(() =>
      expect(screen.getByTestId("search-results-grid")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("search-results-frame")).toHaveClass(
      "gap-4",
      "px-4",
      "py-4",
      "lg:p-6",
    );
    expect(screen.getByTestId("search-results-state")).toHaveClass("h-12");
    expect(screen.getByTestId("search-input").parentElement).toHaveClass(
      "h-12",
      "rounded-lg",
      "px-4",
    );
    expect(screen.getByTestId("search-results-section")).toHaveClass(
      "grid",
      "grid-cols-1",
      "gap-2",
      "lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
      "lg:gap-4",
    );
    expect(screen.getByTestId("search-results-section")).not.toHaveClass(
      "md:flex-row",
      "md:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
      "xl:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
    );
    expect(screen.getByTestId("search-results-header")).toHaveClass(
      "h-12",
      "justify-between",
    );
    expect(screen.getByTestId("search-results-header")).not.toHaveClass(
      "bg-white",
    );
    expect(screen.getByText("Search Results")).toHaveClass(
      "text-knowledge-search-section-title",
      "lg:text-knowledge-search-section-title-desktop",
    );
    expect(screen.getByText("Search Results")).not.toHaveClass(
      "text-knowledge-search-results-title",
      "lg:text-knowledge-search-results-title-desktop",
    );
    expect(screen.getByText("Related Results")).toHaveClass(
      "text-knowledge-search-section-title",
      "lg:text-knowledge-search-section-title-desktop",
    );
    expect(screen.getByTestId("search-results-grid")).toHaveClass(
      "group/search-results-grid",
      "auto-rows-[var(--spacing-search-result-card-height)]",
      "grid-cols-1",
      "gap-2",
      "sm:grid-cols-2",
      "lg:grid-cols-2",
      "min-[1680px]:grid-cols-3",
      "lg:auto-rows-[var(--spacing-search-result-card-height)]",
      "lg:gap-4",
    );
    expect(screen.getByTestId("search-results-scroll-area")).toHaveClass(
      "pt-4",
      "pr-4",
      "pl-2",
    );
    expect(screen.getByTestId("search-results-grid")).toHaveClass("pb-1");
    expect(screen.getByTestId("search-results-grid")).not.toHaveClass(
      "auto-rows-[200px]",
      "lg:auto-rows-[200px]",
      "md:w-[984px]",
      "md:grid-cols-[repeat(3,316px)]",
      "xl:grid-cols-3",
    );
    expect(screen.getByTestId("search-suggestions-panel")).toHaveClass(
      "h-[200px]",
      "lg:h-full",
      "min-h-0",
      "min-w-0",
    );
    expect(screen.getByTestId("search-suggestions-panel")).not.toHaveClass(
      "md:w-[324px]",
    );
    expect(
      Array.from(
        screen.getByTestId("search-results-scroll-area").children,
      ).some((child) => child.getAttribute("aria-hidden") === "true"),
    ).toBe(false);
    expect(
      Array.from(
        screen.getByTestId("search-suggestions-scroll-area").children,
      ).some((child) => child.getAttribute("aria-hidden") === "true"),
    ).toBe(false);
    expect(screen.getByTestId("search-suggestions-scroll-area")).toHaveClass(
      "group/search-suggestions-list",
      "gap-2",
      "pt-1",
      "pr-1",
      "pl-px",
    );
    expect(
      screen.getByRole("button", { name: "Adjacency matrix" }),
    ).toHaveClass(
      "items-center",
      "min-h-search-related-result-height",
      "px-search-related-result-padding-x",
      "py-search-related-result-padding-y",
      "hover:-translate-y-0.5",
      "hover:scale-[var(--scale-search-related-result-hover)]",
      "group-hover/search-suggestions-list:opacity-80",
      "hover:border-[#006bff]/40",
    );
    expect(
      within(
        screen.getByRole("button", { name: "Adjacency matrix" }),
      ).getByTestId("related-result-item-title"),
    ).toHaveClass("whitespace-normal", "break-words");
  });

  it("wraps long result card titles and lets the header grow", async () => {
    const longTitle =
      "Singular value decomposition for exceptionally long matrix factorization titles";
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: longTitle,
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    expect(await screen.findByText(longTitle)).toBeInTheDocument();

    const titleHeader = screen.getByTestId("search-result-card-header");
    const titleArea = screen.getByTestId("search-result-card-title-area");
    const titleTrack = screen.getByTestId("search-result-card-title-track");

    expect(titleHeader).toHaveClass("min-h-10");
    expect(titleHeader).toHaveClass("md:min-h-6");
    expect(titleHeader).not.toHaveClass("h-10");
    expect(titleHeader).not.toHaveClass("md:h-6");
    expect(titleArea).toHaveClass("whitespace-normal");
    expect(titleArea).toHaveClass("break-words");
    expect(titleArea).not.toHaveClass("overflow-x-auto");
    expect(titleArea).not.toHaveClass("overflow-y-hidden");
    expect(titleTrack).toHaveClass("whitespace-normal");
    expect(titleTrack).toHaveClass("break-words");
    expect(titleTrack).not.toHaveClass("whitespace-nowrap");

    fireEvent.click(
      screen.getByRole("link", { name: `Search for ${longTitle}` }),
    );

    await waitFor(() =>
      expect(screen.getByDisplayValue(longTitle)).toBeInTheDocument(),
    );
  });

  it("wraps long related result titles and keeps the icon slot centered", async () => {
    const longRelatedTitle =
      "Principal component analysis with especially long related result labels";
    const payload: SearchResponse = {
      connected_titles: [longRelatedTitle],
      matched_cards: [],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    const relatedItem = await screen.findByRole("button", {
      name: longRelatedTitle,
    });
    const relatedTitle = within(relatedItem).getByTestId(
      "related-result-item-title",
    );
    const iconSlot = within(relatedItem).getByTestId(
      "related-result-item-icon",
    );

    expect(relatedItem).toHaveClass("items-center");
    expect(relatedItem).not.toHaveClass(
      "h-search-related-result-height",
      "h-10",
      "h-[38px]",
      "md:h-[42px]",
      "overflow-hidden",
    );
    expect(relatedItem).toHaveClass("min-h-search-related-result-height");
    expect(relatedTitle).toHaveClass("whitespace-normal", "break-words");
    expect(relatedTitle).not.toHaveClass("truncate", "whitespace-nowrap");
    expect(iconSlot).toHaveClass(
      "size-search-related-result-icon-size",
      "items-center",
      "justify-center",
    );
  });

  it("opens sign-in-required dialog when anonymous user clicks edit", async () => {
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: "Matrix decomposition",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Suggest edit for Matrix decomposition",
      }),
    );

    expect(
      screen.getByRole("dialog", { name: "Sign in to suggest edits" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sign in to suggest changes and help improve this knowledge card.",
      ),
    ).toBeInTheDocument();
    const dialog = screen.getByRole("dialog", {
      name: "Sign in to suggest edits",
    });

    expect(
      within(dialog).getByRole("button", { name: "Sign in" }).closest("form"),
    ).toHaveFormValues({
      return_to: "/search?q=matrix",
    });
  });

  it("navigates to a result card title when the card search affordance is activated", async () => {
    const payload: SearchResponse = {
      connected_titles: ["Adjacency matrix"],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: "Singular value decomposition",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("link", {
        name: "Search for Singular value decomposition",
      }),
    );

    await waitFor(() =>
      expect(
        screen.getByDisplayValue("Singular value decomposition"),
      ).toBeInTheDocument(),
    );
  });

  it("keeps result card edit activation separate from title search navigation", async () => {
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: "Singular value decomposition",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Suggest edit for Singular value decomposition",
      }),
    );

    expect(screen.getByDisplayValue("matrix")).toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("Singular value decomposition"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Sign in to suggest edits" }),
    ).toBeInTheDocument();
  });

  it("does not show anonymous sign-in dialog while session is still loading", async () => {
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "A result body.",
          current_version: 1,
          node_id: 10,
          title: "Matrix decomposition",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({ status: "loading" });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Suggest edit for Matrix decomposition",
      }),
    );

    expect(
      screen.queryByRole("dialog", { name: "Sign in to suggest edits" }),
    ).not.toBeInTheDocument();
  });

  it("submits authenticated edit proposal with visible base version", async () => {
    const mutateAsync = vi.fn(async () => ({
      base_version: 3,
      created_at: "2026-04-28T18:00:00Z",
      id: 99,
      node_id: 10,
      status: "pending",
    }));
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "Old content.",
          current_version: 3,
          node_id: 10,
          title: "Old title",
        },
      ],
    };
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync,
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", { name: "Suggest edit for Old title" }),
    );
    expect(
      screen.getByRole("dialog", { name: "Card Proposal" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Better title" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Better content." },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This improves the visible explanation." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        base_version: 3,
        proposal_type: "edit",
        reason: "This improves the visible explanation.",
        suggested_content: "Better content.",
        suggested_title: "Better title",
        target_node_id: 10,
      }),
    );
  });

  it("submits authenticated add-card proposal with a required reason", async () => {
    const mutateAsync = vi.fn(async () => ({
      created_at: "2026-04-28T18:00:00Z",
      id: 100,
      payload: {
        proposed_content: "New card content.",
        proposed_title: "New card",
      },
      proposal_type: "create",
      reason: "This fills a missing concept.",
      reviewed_at: null,
      reviewed_by_user_id: null,
      review_note: null,
      status: "pending_review",
      submitted_by_user_id: "logto-user-123",
      updated_at: "2026-04-28T18:00:00Z",
    }));
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [],
    };
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync,
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(await screen.findByRole("button", { name: "Add Card" }));
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "New card" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "New card content." },
    });
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This fills a missing concept." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        proposal_type: "create",
        proposed_content: "New card content.",
        proposed_title: "New card",
        reason: "This fills a missing concept.",
      }),
    );
  });

  it("disables authenticated suggestion submission until the draft changes", async () => {
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "Old content.",
          current_version: 3,
          node_id: 10,
          title: "Old title",
        },
      ],
    };
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", { name: "Suggest edit for Old title" }),
    );

    const submitButton = screen.getByRole("button", { name: "Submit" });
    expect(submitButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Better content." },
    });

    expect(submitButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "The current card is missing this detail." },
    });

    expect(submitButton).not.toBeDisabled();
  });

  it("keeps authenticated suggestion draft open and shows submission errors", async () => {
    const mutateAsync = vi.fn(async () => {
      throw new Error("backend unavailable");
    });
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "Old content.",
          current_version: 3,
          node_id: 10,
          title: "Old title",
        },
      ],
    };
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync,
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", { name: "Suggest edit for Old title" }),
    );
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Better title" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Better content." },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This clarifies the current card." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    expect(
      await screen.findByText("Could not submit the suggestion. Try again."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Card Proposal" }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better title")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better content.")).toBeInTheDocument();
  });

  it("keeps proposal drafts mounted and opens sign-in recovery on expired sessions", async () => {
    const mutateAsync = vi.fn(async () => {
      throw new WebApiRequestError({
        code: "session_expired",
        message: "Session expired.",
        status: 401,
      });
    });
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "Old content.",
          current_version: 3,
          node_id: 10,
          title: "Old title",
        },
      ],
    };
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync,
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", { name: "Suggest edit for Old title" }),
    );
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Better title" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Better content." },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This clarifies the current card." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    expect(
      await screen.findByText("Session expired. Sign in again."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Card Proposal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Sign in to suggest edits" }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better title")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better content.")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("This clarifies the current card."),
    ).toBeInTheDocument();
  });

  it("shows actionable copy for known suggested edit rule violations", async () => {
    const mutateAsync = vi.fn(async () => {
      throw new WebApiRequestError({
        code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
        message: "Suggested edit must change the card title or content.",
        status: 422,
      });
    });
    const payload: SearchResponse = {
      connected_titles: [],
      matched_cards: [
        {
          content: "Old content.",
          current_version: 3,
          node_id: 10,
          title: "Old title",
        },
      ],
    };
    mockUseCreateCardProposalMutation.mockReturnValue({
      error: null,
      isPending: false,
      mutateAsync,
    } as never);
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: payload,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
    mockUseWebSession.mockReturnValue({
      status: "authenticated",
      user: { id: "logto-user-123" },
    });

    renderSearchRoute("/search?q=matrix");

    fireEvent.click(
      await screen.findByRole("button", { name: "Suggest edit for Old title" }),
    );
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Better content." },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This clarifies the current card." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    expect(
      await screen.findByText("Change the title or content before submitting."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Card Proposal" }),
    ).toBeInTheDocument();
  });
});
