// abstract: Route-level tests for the Figma-aligned Search page states.
// out_of_scope: Backend search integration and ranking semantics.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../../../app/router";
import type { SearchResponse } from "../data/searchQueries";

vi.mock("../data/searchQueries", () => ({
  useSearchQuery: vi.fn(),
}));

import * as searchQueries from "../data/searchQueries";

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  window.scrollTo = vi.fn();
});

function renderSearchRoute(pathname: string) {
  const router = createAppRouter({
    initialEntries: [pathname],
  });

  render(<RouterProvider router={router} />);

  return { router };
}

const mockUseSearchQuery = vi.mocked(searchQueries.useSearchQuery);

function mockSearchQueryResult(
  value: Partial<ReturnType<typeof searchQueries.useSearchQuery>>,
) {
  return value as unknown as ReturnType<typeof searchQueries.useSearchQuery>;
}

describe("SearchPage", () => {
  beforeEach(() => {
    mockUseSearchQuery.mockReturnValue(
      mockSearchQueryResult({
        data: undefined,
        error: null,
        isError: false,
        isPending: false,
      }),
    );
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
    expect(screen.getByDisplayValue("matrix")).toBeInTheDocument();
    expect(screen.getByTestId("search-icon-button")).toBeInTheDocument();
    expect(screen.queryByTestId("search-empty-state")).not.toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(screen.getByText("Matrix decomposition")).toBeInTheDocument();
    expect(screen.getByText("Returned")).toBeInTheDocument();
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
      "gap-3",
      "px-4",
      "py-[18px]",
      "md:gap-5",
      "md:px-[34px]",
      "md:pt-6",
      "md:pb-9",
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
    );
    expect(screen.getByTestId("search-results-grid")).toHaveClass(
      "auto-rows-[220px]",
      "grid-cols-1",
      "gap-y-3",
      "sm:grid-cols-[repeat(auto-fit,minmax(18rem,1fr))]",
      "md:auto-rows-[300px]",
      "lg:auto-rows-[379px]",
      "lg:gap-[18px]",
    );
    expect(screen.getByTestId("search-results-grid")).not.toHaveClass(
      "md:w-[984px]",
      "md:grid-cols-[repeat(3,316px)]",
    );
    expect(screen.getByTestId("search-suggestions-panel")).toHaveClass(
      "h-[176px]",
      "lg:h-full",
      "min-w-0",
    );
    expect(screen.getByTestId("search-suggestions-panel")).not.toHaveClass(
      "md:w-[324px]",
    );
  });
});
