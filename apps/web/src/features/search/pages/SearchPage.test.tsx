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
});
