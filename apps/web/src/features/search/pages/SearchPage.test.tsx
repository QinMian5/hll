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
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { createAppRouter } from "../../../app/router";
import type { SearchResponse } from "../data/searchQueries";

vi.mock("../data/searchQueries", () => ({
  useCreateSuggestedEditMutation: vi.fn(),
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
});

beforeEach(() => {
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
const mockUseCreateSuggestedEditMutation = vi.mocked(
  searchQueries.useCreateSuggestedEditMutation,
);
const mockUseWebSession = vi.mocked(webSession.useWebSession);

function mockSearchQueryResult(
  value: Partial<ReturnType<typeof searchQueries.useSearchQuery>>,
) {
  return value as unknown as ReturnType<typeof searchQueries.useSearchQuery>;
}

describe("SearchPage", () => {
  beforeEach(() => {
    mockUseCreateSuggestedEditMutation.mockReturnValue({
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
    expect(screen.getByText("Search results")).toBeInTheDocument();
    expect(screen.getByText("Related results")).toBeInTheDocument();
    expect(screen.getByDisplayValue("matrix")).toBeInTheDocument();
    expect(screen.getByTestId("search-icon-button")).toBeInTheDocument();
    expect(screen.queryByTestId("search-empty-state")).not.toBeInTheDocument();
    expect(await screen.findByText("Matrix decomposition")).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(await screen.findByText("Returned")).toBeInTheDocument();
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
      "lg:gap-5",
      "lg:px-8",
      "lg:pt-6",
      "lg:pb-8",
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
      "gap-3",
      "lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
      "lg:gap-7",
    );
    expect(screen.getByTestId("search-results-section")).not.toHaveClass(
      "md:flex-row",
      "md:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
      "xl:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]",
    );
    expect(screen.getByTestId("search-results-grid")).toHaveClass(
      "auto-rows-[176px]",
      "grid-cols-1",
      "gap-y-3",
      "sm:grid-cols-2",
      "sm:gap-x-3",
      "lg:grid-cols-2",
      "min-[1680px]:grid-cols-3",
      "lg:auto-rows-[176px]",
      "lg:gap-4",
    );
    expect(screen.getByTestId("search-results-grid")).not.toHaveClass(
      "md:w-[984px]",
      "md:grid-cols-[repeat(3,316px)]",
      "xl:grid-cols-3",
    );
    expect(screen.getByTestId("search-suggestions-panel")).toHaveClass(
      "h-[176px]",
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

  it("submits authenticated suggestion with visible base version", async () => {
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
    mockUseCreateSuggestedEditMutation.mockReturnValue({
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
    fireEvent.change(screen.getByLabelText("Suggested title"), {
      target: { value: "Better title" },
    });
    fireEvent.change(screen.getByLabelText("Suggested content"), {
      target: { value: "Better content." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit suggestion" }));

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        baseVersion: 3,
        nodeId: 10,
        suggestedContent: "Better content.",
        suggestedTitle: "Better title",
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

    const submitButton = screen.getByRole("button", {
      name: "Submit suggestion",
    });
    expect(submitButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Suggested content"), {
      target: { value: "Better content." },
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
    mockUseCreateSuggestedEditMutation.mockReturnValue({
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
    fireEvent.change(screen.getByLabelText("Suggested title"), {
      target: { value: "Better title" },
    });
    fireEvent.change(screen.getByLabelText("Suggested content"), {
      target: { value: "Better content." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit suggestion" }));

    expect(
      await screen.findByText("Could not submit the suggestion. Try again."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("dialog", { name: "Suggest edit" }),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better title")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Better content.")).toBeInTheDocument();
  });
});
