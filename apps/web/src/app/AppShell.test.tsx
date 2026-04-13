// abstract: Route-shell tests for the shared app navigation and root redirect behavior.
// out_of_scope: Feature-specific page content behavior and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "./router";

vi.mock("../features/taxonomy-view/page/TaxonomyViewPage", () => ({
  TaxonomyViewPage: () => <div data-testid="mock-graph-page">Graph page</div>,
}));

function renderWithRoute(pathname: string) {
  const router = createAppRouter({
    initialEntries: [pathname],
  });

  render(<RouterProvider router={router} />);

  return { router };
}

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  window.scrollTo = vi.fn();
});

describe("AppShell", () => {
  it("redirects the root route to overview and highlights only overview", async () => {
    const { router } = renderWithRoute("/");

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/overview"),
    );

    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "inactive",
    );
    expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute(
      "data-nav-state",
      "inactive",
    );
  });

  it("renders the shared top navigation with disabled actions", async () => {
    renderWithRoute("/graph");

    await waitFor(() =>
      expect(screen.getByText("Knowledge Graph")).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(screen.getByRole("link", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GitHub" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Login" })).toBeDisabled();
  });
});
